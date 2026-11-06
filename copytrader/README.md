# Paper Copy-Trader for Invo / Hyperliquid (£20, risk-managed)

**Paper trading only.** This tool never connects to an exchange account, never
holds keys and never moves real money. It copies a trader's moves using a
fake £20 balance, so you can see whether copying them *actually* makes money
once losses, fees and funding are counted, **before** risking real money.

Read **[ANALYSIS.md](ANALYSIS.md)** first. It covers what Invo is, why a "93% win
rate" can still lose money, and the full plan.

Requires only Python 3 (no packages to install).

## Step 1: verify the trader
Invo trades on Hyperliquid, where every wallet's trades are public. Get the
trader's wallet address from their Invo profile, then run:
```bash
python3 trader_check.py 0xTHEIR_WALLET --days 180
```
You get their real win rate, average win vs. average loss, profit factor
(total wins ÷ total losses), max drawdown (biggest fall from a peak),
liquidations and a PASS/FAIL verdict. **Don't copy anyone who fails.**

## Step 2: copy them on paper, automatically
Put the wallet in `config.json`:
```json
"follow_wallets": { "eianlu": "0xTHEIR_WALLET" }
```
Then start the bot:
```bash
nohup python3 copytrader.py > /dev/null 2>&1 &   # runs in the background
tail -f trades.log                               # watch it
python3 copytrader.py --report                   # stats any time
touch STOP                                       # <- the "stop" command
rm STOP                                          # remove before starting again
```
Every `poll_seconds` (default 60) it:
- reads the trader's new fills from Hyperliquid,
- opens a paper copy when they open a position,
- closes the copy when they close theirs.

Old trades are never copied late. Following starts from the moment you add the
wallet. Progress is saved after every check and a report is written hourly.

You can also type trades in by hand from X posts, by adding rows to
`signals.csv`:
```csv
id,trader,symbol,side,stop_loss,take_profit,note
1,eianlu,BTC,long,,,"from tweet 6 Nov"
```
Leave stop/target blank to use the defaults. Symbols are Hyperliquid tickers
(BTC, ETH, SOL, HYPE...).

Try it offline first with `python3 copytrader.py --sim --poll 1`, then run
`--reset`.

## The risk plan (`config.json`)
| Rule | Default | What it does |
|---|---|---|
| Risk per trade | 3% | Hitting the stop costs only about £0.60 |
| Max leverage | 1× | No leverage. On perps, a high-leverage copy can be wiped out by a 2–10% move. |
| Max open trades | 3 | Splits the balance between at most 3 copies |
| Stop-loss / take-profit | 3% / 6% | Every copy has a stop. Each win is set to be about twice each loss. |
| Breakeven stop | at +1R | Once a copy has gained as much as it risked, its stop moves to the entry price so it can't turn into a loss |
| Trader closes | follow | When the trader exits, the copy exits too |
| Fees / funding | 0.07% per side, 0.00125%/hour | Realistic Hyperliquid and Invo costs |
| Daily loss limit | 10% | No new trades for 24 hours |
| Losing streak | 3 in a row | 24-hour pause, so no chasing losses |
| Account stop | £15 | Closes everything and halts at 25% down |
| Lock in profit | at £30 | Sets your £20 aside and trades profit only |
| Drop a trader | 20% drawdown after 10 trades | Stops copying them |

## When to consider real money
Only after **30+ paper trades over 4+ weeks**, with profit factor above 1.3,
drawdown under 20% and the account stop never hit. Even then:
- Hyperliquid is unregulated and has **no FCA protection**.
- Use 1–2× leverage at most.
- Never share your seed phrase.
- Never send money to a trader or "account manager" from X.
