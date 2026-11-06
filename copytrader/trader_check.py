#!/usr/bin/env python3
"""Check a Hyperliquid / Invo trader's REAL record from their wallet address.

    python3 trader_check.py 0xWALLET                # last 180 days
    python3 trader_check.py 0xWALLET --days 365
    python3 trader_check.py --file fills.json       # offline: saved userFills JSON

Where to get the wallet: open the trader's profile in the Invo app, or ask them.
A trader who won't share a wallet can't be verified, so don't copy them.
"""
import argparse
import json
import sys
import time

import hyperliquid as hl


def fmt_money(x):
    return f"${x:,.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("address", nargs="?")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--file", help="analyse a saved JSON list of fills instead of calling the API")
    ap.add_argument("--account-value", type=float, help="account size in USD (for drawdown %%)")
    a = ap.parse_args()

    account_value = a.account_value
    if a.file:
        with open(a.file) as f:
            fills = sorted(json.load(f), key=lambda x: x["time"])
    elif a.address:
        start = int((time.time() - a.days * 86400) * 1000)
        try:
            fills = hl.user_fills(a.address, start)
            if account_value is None:
                st = hl.account_state(a.address)
                account_value = float(st["marginSummary"]["accountValue"])
                lev = [(p["position"]["coin"], p["position"]["leverage"]["value"])
                       for p in st.get("assetPositions", [])]
                if lev:
                    print("Open positions (coin, leverage):", lev)
        except Exception as e:
            sys.exit(f"Could not reach Hyperliquid API: {e}")
    else:
        ap.error("give a wallet address or --file")

    if not fills:
        sys.exit("No trades found for that wallet in this period.")

    s = hl.analyze(fills, account_value)
    ok, results = hl.verdict(s)
    dd = f"{s['max_drawdown_pct']:.1f}%" if s["max_drawdown_pct"] is not None else "unknown (no account value)"
    print(f"""
Trader record ({s['days']:.0f} days, {s['trades']} closed trades, {s['fills']} fills)
  Win rate ........... {s['win_rate']:.1f}%   (upper bound: partial closes count as wins)
  Average win ........ {fmt_money(s['avg_win'])}
  Average loss ....... {fmt_money(s['avg_loss'])}
  Biggest loss ....... {fmt_money(s['biggest_loss'])}
  Profit factor ...... {s['profit_factor']:.2f}   (needs > 1.0 to make money at all)
  Net P/L after fees . {fmt_money(s['net_pnl'])}   (fees paid {fmt_money(s['fees'])})
  Max drawdown ....... {fmt_money(s['max_drawdown_usd'])}  = {dd}
  Liquidations ....... {s['liquidations']}
""")
    for name, passed in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    if s["win_rate"] >= 90 and s["profit_factor"] < 1.5:
        print("\n  WARNING: very high win rate with a weak profit factor usually means small, "
              "frequent wins and rare large losses. One bad trade can wipe out months.")
    print("\nVERDICT:", "OK to PAPER-copy (still not proof for real money)" if ok
          else "DO NOT COPY - fails the checks above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
