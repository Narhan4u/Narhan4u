#!/usr/bin/env python3
"""Paper copy-trader with risk controls.

PAPER TRADING ONLY. This script never connects to an exchange, never holds
keys and never moves real money. It copies trade signals you paste into
signals.csv using fake money, applies the risk rules in config.json and keeps
running until you create a file called STOP in this folder (or press Ctrl+C).

Signals come from two places:
  * signals.csv - trades you type in from a trader's posts on X
  * follow_wallets in config.json - Hyperliquid wallets (the exchange Invo
    uses) whose new trades are copied automatically from public data

Usage:
    python3 copytrader.py              # run until STOP file appears
    python3 copytrader.py --sim        # offline: simulated random-walk prices
    python3 copytrader.py --report     # print stats and exit
    python3 copytrader.py --reset      # wipe paper account back to start
"""
import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.request

import hyperliquid as hl
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
SIGNALS = os.path.join(HERE, "signals.csv")
STATE = os.path.join(HERE, "state.json")
LOG = os.path.join(HERE, "trades.log")
STOP = os.path.join(HERE, "STOP")


def now():
    return datetime.now(timezone.utc)


def log(msg):
    line = f"{now().strftime('%Y-%m-%d %H:%M:%S')}Z  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_state(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE)


def fresh_state(cfg):
    return {
        "cash": cfg["starting_balance_gbp"],
        "locked_profit": 0.0,           # paper "withdrawn" money, never traded again
        "peak_equity": cfg["starting_balance_gbp"],
        "open": [],
        "closed": [],
        "seen_signals": [],
        "dropped_traders": [],
        "paused_until": None,
        "halted": False,
        "day": now().strftime("%Y-%m-%d"),
        "day_start_equity": cfg["starting_balance_gbp"],
        "consecutive_losses": 0,
        "sim_prices": {},
        "follow_cursor": {},
        "last_tick": None,
    }


# ---------------------------------------------------------------- prices ---

class Prices:
    def __init__(self, cfg, sim, state):
        self.cfg, self.sim, self.state = cfg, sim, state

    def get(self, symbols):
        symbols = sorted(set(s.upper() for s in symbols))
        if not symbols:
            return {}
        if self.sim:
            return self._sim(symbols)
        if self.cfg["price_source"] == "hyperliquid":
            return self._hyperliquid(symbols)
        return self._coingecko(symbols)

    def _hyperliquid(self, symbols):
        try:
            mids = hl.all_mids()
        except Exception as e:
            log(f"WARN price fetch failed: {e}")
            return {}
        for s in symbols:
            if s not in mids:
                log(f"WARN {s} is not a Hyperliquid market")
        return {s: mids[s] for s in symbols if s in mids}

    def _sim(self, symbols):
        out = {}
        p = self.state["sim_prices"]
        for s in symbols:
            last = p.get(s, 100.0)
            last *= 1 + random.gauss(0.0003, 0.01)
            p[s] = last
            out[s] = last
        return out

    def _coingecko(self, symbols):
        ids = self.cfg["coingecko_ids"]
        wanted = {ids[s]: s for s in symbols if s in ids}
        for s in symbols:
            if s not in ids:
                log(f"WARN no coingecko id for {s}; add it to coingecko_ids in config.json")
        if not wanted:
            return {}
        url = ("https://api.coingecko.com/api/v3/simple/price?vs_currencies=gbp&ids="
               + ",".join(wanted))
        req = urllib.request.Request(url, headers={"User-Agent": "paper-copytrader/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.load(r)
        except Exception as e:  # network hiccup: skip this tick
            log(f"WARN price fetch failed: {e}")
            return {}
        return {wanted[i]: v["gbp"] for i, v in data.items() if "gbp" in v}


# ------------------------------------------------------------- the engine ---

class Engine:
    def __init__(self, cfg, state, prices):
        self.cfg, self.s, self.prices = cfg, state, prices

    # equity = cash + value of open positions (excludes locked profit)
    def equity(self, px):
        eq = self.s["cash"]
        for p in self.s["open"]:
            price = px.get(p["symbol"], p["last_price"])
            eq += p["margin"] + self.pnl(p, price)
        return eq

    def pnl(self, p, price):
        direction = 1 if p["side"] == "long" else -1
        return direction * (price - p["entry"]) / p["entry"] * p["notional"]

    def fee(self, notional):
        return notional * self.cfg["fee_pct_per_side"] / 100

    def read_signals(self):
        if not os.path.exists(SIGNALS):
            return []
        with open(SIGNALS, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get("id")]
        return [r for r in rows if r["id"] not in self.s["seen_signals"]]

    def follow_wallets(self):
        """Turn new fills from followed Hyperliquid wallets into signals.

        On the first run for a wallet we start from *now*, so old trades are
        never copied late at stale prices."""
        opens, closes = [], []
        cur = self.s.setdefault("follow_cursor", {})
        for name, addr in self.cfg.get("follow_wallets", {}).items():
            if not addr or not addr.startswith("0x"):
                continue
            if addr not in cur:
                cur[addr] = int(now().timestamp() * 1000)
                log(f"FOLLOW {name} ({addr[:6]}...{addr[-4:]}): copying trades from now on")
                continue
            try:
                fills = hl.user_fills(addr, cur[addr] + 1)
            except Exception as e:
                log(f"WARN could not read fills for {name}: {e}")
                continue
            for f in fills:
                cur[addr] = max(cur[addr], f["time"])
                d = f.get("dir", "")
                coin = f.get("coin", "")
                if coin.startswith("@") or ":" in coin:   # spot / other dex: skip
                    continue
                if d.startswith("Close") or ">" in d:
                    closes.append((name, coin.upper()))
                if d.startswith("Open") or ">" in d:
                    side = "long" if ("Long" in d.split(">")[-1]) else "short"
                    opens.append({"id": f"hl-{f.get('tid')}", "trader": name,
                                  "symbol": coin.upper(), "side": side,
                                  "stop_loss": "", "take_profit": "", "note": d})
        return opens, closes

    def apply_trader_closes(self, closes, px):
        for trader, sym in closes:
            for p in list(self.s["open"]):
                if p["trader"] == trader and p["symbol"] == sym:
                    price = px.get(sym, p["last_price"])
                    self.close_position(p, price, f"{trader} closed")

    def charge_funding(self):
        rate = self.cfg.get("funding_pct_per_hour", 0) / 100
        t = now().timestamp()
        last = self.s.get("last_tick") or t
        hours = max(0.0, (t - last) / 3600)
        self.s["last_tick"] = t
        if not rate or not hours:
            return
        for p in self.s["open"]:
            cost = p["notional"] * rate * hours
            p["fees"] += cost
            self.s["cash"] -= cost

    def trader_stats(self, trader=None):
        trades = [t for t in self.s["closed"] if trader is None or t["trader"] == trader]
        wins = [t["pnl"] for t in trades if t["pnl"] > 0]
        losses = [t["pnl"] for t in trades if t["pnl"] <= 0]
        eq, peak, mdd = 0.0, 0.0, 0.0
        base = self.cfg["starting_balance_gbp"]
        for t in trades:
            eq += t["pnl"]
            peak = max(peak, eq)
            mdd = max(mdd, (peak - eq) / base * 100)
        return {
            "trades": len(trades),
            "win_rate": 100 * len(wins) / len(trades) if trades else 0.0,
            "avg_win": sum(wins) / len(wins) if wins else 0.0,
            "avg_loss": sum(losses) / len(losses) if losses else 0.0,
            "profit_factor": (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else float("inf") if wins else 0.0,
            "net": sum(t["pnl"] for t in trades),
            "max_drawdown_pct": mdd,
        }

    # -- risk gates --------------------------------------------------------

    def can_open(self, sig):
        if self.s["halted"]:
            return "account halted (hit account stop)"
        if self.s["paused_until"] and now().isoformat() < self.s["paused_until"]:
            return f"paused until {self.s['paused_until']}"
        if sig["trader"] in self.s["dropped_traders"]:
            return f"trader {sig['trader']} was dropped for bad drawdown"
        if any(p["trader"] == sig["trader"] and p["symbol"] == sig["symbol"].upper()
               for p in self.s["open"]):
            return "already copying this trader on this coin"
        if len(self.s["open"]) >= self.cfg["max_open_positions"]:
            return "max open positions reached"
        if sig["side"] not in ("long", "short"):
            return f"bad side '{sig['side']}' (use long/short)"
        return None

    def open_position(self, sig, px):
        sym = sig["symbol"].upper()
        price = px.get(sym)
        if price is None:
            return False  # retry next tick
        reason = self.can_open(sig)
        if reason:
            log(f"SKIP signal {sig['id']} {sym} {sig['side']}: {reason}")
            return True
        eq = self.equity(px)
        long_ = sig["side"] == "long"
        sl = float(sig["stop_loss"]) if sig.get("stop_loss") else \
            price * (1 - self.cfg["default_stop_loss_pct"] / 100 * (1 if long_ else -1))
        tp = float(sig["take_profit"]) if sig.get("take_profit") else \
            price * (1 + self.cfg["default_take_profit_pct"] / 100 * (1 if long_ else -1))
        if (long_ and not (sl < price < tp)) or (not long_ and not (tp < price < sl)):
            log(f"SKIP signal {sig['id']} {sym}: stop/target on wrong side of price {price:.4f}")
            return True
        stop_dist = abs(price - sl) / price
        risk_gbp = eq * self.cfg["risk_per_trade_pct"] / 100
        # leverage capped (default 1x = none); account shared between slots
        lev = max(1.0, float(self.cfg.get("max_leverage", 1)))
        notional = min(risk_gbp / stop_dist,
                       eq * lev / self.cfg["max_open_positions"],
                       self.s["cash"] * 0.95 * lev)
        if notional < 1:
            log(f"SKIP signal {sig['id']} {sym}: position would be under £1")
            return True
        fee = self.fee(notional)
        margin = notional / lev
        self.s["cash"] -= margin + fee
        pos = {
            "id": sig["id"], "trader": sig["trader"], "symbol": sym, "side": sig["side"],
            "entry": price, "stop": sl, "target": tp, "initial_stop": sl,
            "notional": notional, "margin": margin, "fees": fee,
            "opened": now().isoformat(), "last_price": price,
        }
        self.s["open"].append(pos)
        log(f"OPEN  {sym} {sig['side']} £{notional:.2f} @ {price:.4f}  SL {sl:.4f}  TP {tp:.4f}  "
            f"(risking £{risk_gbp:.2f}, copying {sig['trader']})")
        return True

    def close_position(self, p, price, why):
        fee = self.fee(p["notional"])
        pnl = self.pnl(p, price) - p["fees"] - fee
        self.s["cash"] += p["margin"] + self.pnl(p, price) - fee
        self.s["open"].remove(p)
        self.s["closed"].append({
            "id": p["id"], "trader": p["trader"], "symbol": p["symbol"], "side": p["side"],
            "entry": p["entry"], "exit": price, "pnl": round(pnl, 4), "why": why,
            "opened": p["opened"], "closed": now().isoformat(),
        })
        self.s["consecutive_losses"] = 0 if pnl > 0 else self.s["consecutive_losses"] + 1
        log(f"CLOSE {p['symbol']} {p['side']} @ {price:.4f}  {why}  P/L £{pnl:+.2f}  "
            f"cash £{self.s['cash']:.2f}")
        self.check_trader(p["trader"])

    def check_trader(self, trader):
        st = self.trader_stats(trader)
        if (st["trades"] >= self.cfg["drop_trader_min_trades"]
                and st["max_drawdown_pct"] >= self.cfg["drop_trader_if_drawdown_pct"]
                and trader not in self.s["dropped_traders"]):
            self.s["dropped_traders"].append(trader)
            log(f"DROP  trader {trader}: drawdown {st['max_drawdown_pct']:.1f}% over "
                f"{st['trades']} trades - no longer copying")

    def manage(self, px):
        be_r = self.cfg["move_stop_to_breakeven_at_r"]
        for p in list(self.s["open"]):
            price = px.get(p["symbol"])
            if price is None:
                continue
            p["last_price"] = price
            long_ = p["side"] == "long"
            hit_sl = price <= p["stop"] if long_ else price >= p["stop"]
            hit_tp = price >= p["target"] if long_ else price <= p["target"]
            if hit_sl:
                self.close_position(p, price, "stop-loss" if p["stop"] == p["initial_stop"] else "breakeven stop")
                continue
            if hit_tp:
                self.close_position(p, price, "take-profit")
                continue
            r = abs(p["entry"] - p["initial_stop"])
            gained = (price - p["entry"]) if long_ else (p["entry"] - price)
            if be_r and p["stop"] == p["initial_stop"] and gained >= be_r * r:
                p["stop"] = p["entry"]
                log(f"MOVE  {p['symbol']} stop to breakeven {p['entry']:.4f}")

    def account_rules(self, px):
        cfg, s = self.cfg, self.s
        today = now().strftime("%Y-%m-%d")
        eq = self.equity(px)
        if s["day"] != today:
            s["day"], s["day_start_equity"] = today, eq
        s["peak_equity"] = max(s["peak_equity"], eq)

        stop_level = s.get("stop_level", cfg["account_stop_gbp"])
        if not s["halted"] and eq <= stop_level:
            for p in list(s["open"]):
                self.close_position(p, px.get(p["symbol"], p["last_price"]), "account stop")
            s["halted"] = True
            log(f"HALT  equity £{eq:.2f} hit account stop £{stop_level:.2f}. "
                f"No new trades. Review, then run --reset to start over.")
            return

        if (s["locked_profit"] == 0 and cfg["lock_in_profit_at_gbp"]
                and eq >= cfg["lock_in_profit_at_gbp"]
                and s["cash"] >= cfg["starting_balance_gbp"]):
            lock = cfg["starting_balance_gbp"]
            s["cash"] -= lock
            s["locked_profit"] = lock
            # keep the same maximum % loss on the smaller, profit-only balance
            ratio = cfg["account_stop_gbp"] / cfg["starting_balance_gbp"]
            s["stop_level"] = (eq - lock) * ratio
            s["day_start_equity"] -= lock
            s["peak_equity"] -= lock
            eq -= lock
            log(f"LOCK  equity £{eq + lock:.2f}: £{lock:.2f} (your original stake) set aside. "
                f"Now trading with profit only (£{eq:.2f}), "
                f"new account stop £{s['stop_level']:.2f}.")

        day_loss = (s["day_start_equity"] - eq) / s["day_start_equity"] * 100 if s["day_start_equity"] else 0
        if day_loss >= cfg["daily_loss_limit_pct"] and not self._paused():
            self._pause(f"daily loss {day_loss:.1f}% >= {cfg['daily_loss_limit_pct']}%")
        if s["consecutive_losses"] >= cfg["pause_after_consecutive_losses"] and not self._paused():
            self._pause(f"{s['consecutive_losses']} losses in a row")
            s["consecutive_losses"] = 0

    def _paused(self):
        return self.s["paused_until"] and now().isoformat() < self.s["paused_until"]

    def _pause(self, why):
        until = datetime.fromtimestamp(now().timestamp() + self.cfg["pause_hours"] * 3600, timezone.utc)
        self.s["paused_until"] = until.isoformat()
        log(f"PAUSE {why}. No new trades until {until.strftime('%Y-%m-%d %H:%M')}Z "
            f"(open trades still managed).")

    def tick(self):
        new = self.read_signals()
        hl_opens, hl_closes = self.follow_wallets()
        new += hl_opens
        symbols = ([p["symbol"] for p in self.s["open"]] + [n["symbol"] for n in new]
                   + [c[1] for c in hl_closes])
        px = self.prices.get(symbols)
        self.charge_funding()
        self.apply_trader_closes(hl_closes, px)
        self.manage(px)
        for sig in new:
            sig["side"] = sig["side"].strip().lower()
            if self.open_position(sig, px):
                self.s["seen_signals"].append(sig["id"])
        self.account_rules(px)
        return px

    def report(self, px=None):
        px = px or {}
        st = self.trader_stats()
        eq = self.equity(px)
        lines = [
            "=" * 60,
            f"PAPER ACCOUNT  equity £{eq:.2f}  cash £{self.s['cash']:.2f}  "
            f"locked £{self.s['locked_profit']:.2f}",
            f"total value £{eq + self.s['locked_profit']:.2f} "
            f"(started £{self.cfg['starting_balance_gbp']:.2f})  "
            f"{'HALTED' if self.s['halted'] else 'PAUSED' if self._paused() else 'ACTIVE'}",
            f"trades {st['trades']}  win rate {st['win_rate']:.0f}%  avg win £{st['avg_win']:.2f}  "
            f"avg loss £{st['avg_loss']:.2f}  profit factor {st['profit_factor']:.2f}  "
            f"max DD {st['max_drawdown_pct']:.1f}%",
        ]
        for t in sorted({c["trader"] for c in self.s["closed"]}):
            ts = self.trader_stats(t)
            flag = " [DROPPED]" if t in self.s["dropped_traders"] else ""
            lines.append(f"  {t}{flag}: {ts['trades']} trades, {ts['win_rate']:.0f}% wins, "
                         f"net £{ts['net']:+.2f}, DD {ts['max_drawdown_pct']:.1f}%")
        for p in self.s["open"]:
            lines.append(f"  open {p['symbol']} {p['side']} £{p['notional']:.2f} @ {p['entry']:.4f} "
                         f"now {p['last_price']:.4f}")
        lines.append("=" * 60)
        for l in lines:
            log(l)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sim", action="store_true", help="use simulated prices (offline testing)")
    ap.add_argument("--report", action="store_true", help="print stats and exit")
    ap.add_argument("--reset", action="store_true", help="reset the paper account")
    ap.add_argument("--max-ticks", type=int, default=0, help="stop after N ticks (testing)")
    ap.add_argument("--poll", type=float, help="override poll_seconds")
    args = ap.parse_args()

    cfg = load_json(CONFIG, None)
    if cfg is None:
        sys.exit("config.json missing or invalid")
    if args.reset:
        save_state(fresh_state(cfg))
        print("Paper account reset.")
        return
    state = load_json(STATE, None) or fresh_state(cfg)
    eng = Engine(cfg, state, Prices(cfg, args.sim, state))
    if args.report:
        eng.report()
        return

    poll = args.poll if args.poll is not None else cfg["poll_seconds"]
    log(f"START paper copy-trader ({'simulated' if args.sim else cfg['price_source']} prices, "
        f"every {poll}s). Create a file named STOP here to stop.")
    ticks = 0
    last_report = 0.0
    try:
        while not os.path.exists(STOP):
            px = eng.tick()
            save_state(state)
            ticks += 1
            if time.time() - last_report > 3600 or (args.max_ticks and ticks >= args.max_ticks):
                eng.report(px)
                last_report = time.time()
            if args.max_ticks and ticks >= args.max_ticks:
                break
            time.sleep(poll)
    except KeyboardInterrupt:
        pass
    save_state(state)
    log("STOP  copy-trader stopped. Open paper positions are kept and resume next run.")


if __name__ == "__main__":
    main()
