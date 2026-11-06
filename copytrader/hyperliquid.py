"""Read-only helpers for Hyperliquid's public info API.

Invo (Involio) runs its copy trading on Hyperliquid, and every Hyperliquid
wallet's trades are public. That means a trader's real record can be checked
from their wallet address instead of trusting win-rate screenshots on X.

Nothing here signs transactions, holds keys or places orders.
"""
import json
import urllib.request

API = "https://api.hyperliquid.xyz/info"


def post(payload, timeout=20):
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "paper-copytrader/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def all_mids():
    """{coin: mid price in USD} for every perp market."""
    return {k: float(v) for k, v in post({"type": "allMids"}).items()}


def user_fills(address, start_ms=0):
    """Fills for a wallet since start_ms (oldest first). The API returns up to
    2000 per call, so page forward until it runs out."""
    out, seen = [], set()
    while True:
        batch = post({"type": "userFillsByTime", "user": address,
                      "startTime": int(start_ms), "aggregateByTime": True})
        new = [f for f in batch if f.get("tid") not in seen]
        if not new:
            break
        for f in new:
            seen.add(f.get("tid"))
        out.extend(new)
        if len(batch) < 2000:
            break
        start_ms = max(f["time"] for f in batch) + 1
    return sorted(out, key=lambda f: f["time"])


def account_state(address):
    return post({"type": "clearinghouseState", "user": address})


# ------------------------------------------------------------- analysis ---

def analyze(fills, account_value=None):
    """Score a trader from their fills.

    Each closing fill (dir starting 'Close', or a flip) counts as one trade
    outcome: closedPnl minus fees. Partial closes count separately, which
    tends to *inflate* win rate slightly, so read it as an upper bound.
    """
    trades = []
    total_fees = closing_fees = 0.0
    for f in fills:
        fee = float(f.get("fee", 0) or 0)
        total_fees += fee
        d = f.get("dir", "")
        if d.startswith("Close") or ">" in d or d in ("Liquidation",):
            net = float(f.get("closedPnl", 0) or 0) - fee
            closing_fees += fee
            trades.append({"time": f["time"], "coin": f.get("coin"), "pnl": net,
                           "liquidation": bool(f.get("liquidation"))})

    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] <= 0]
    eq = peak = 0.0
    max_dd_usd = 0.0
    for t in trades:
        eq += t["pnl"]
        peak = max(peak, eq)
        max_dd_usd = max(max_dd_usd, peak - eq)
    base = account_value if account_value and account_value > 0 else None
    span_days = (fills[-1]["time"] - fills[0]["time"]) / 86_400_000 if len(fills) > 1 else 0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    return {
        "fills": len(fills),
        "trades": len(trades),
        "days": span_days,
        "win_rate": 100 * len(wins) / len(trades) if trades else 0.0,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "biggest_loss": min(losses) if losses else 0.0,
        "profit_factor": (sum(wins) / -sum(losses)) if sum(losses) < 0 else (float("inf") if wins else 0.0),
        # trade pnl already has closing fees off; also take off opening fees
        "net_pnl": sum(t["pnl"] for t in trades) - (total_fees - closing_fees),
        "fees": total_fees,
        "max_drawdown_usd": max_dd_usd,
        "max_drawdown_pct": 100 * max_dd_usd / base if base else None,
        "liquidations": sum(1 for t in trades if t["liquidation"]),
    }


CRITERIA = [
    ("At least 30 closed trades", lambda s: s["trades"] >= 30),
    ("At least 60 days of history", lambda s: s["days"] >= 60),
    ("Profit factor above 1.3", lambda s: s["profit_factor"] > 1.3),
    ("Average win at least half the average loss",
     lambda s: s["avg_loss"] == 0 or s["avg_win"] >= 0.5 * abs(s["avg_loss"])),
    ("No liquidations", lambda s: s["liquidations"] == 0),
    ("Max drawdown under 20% of account",
     lambda s: s["max_drawdown_pct"] is not None and s["max_drawdown_pct"] < 20),
    ("Net profitable after fees", lambda s: s["net_pnl"] > 0),
]


def verdict(stats):
    results = [(name, bool(test(stats))) for name, test in CRITERIA]
    return all(ok for _, ok in results), results
