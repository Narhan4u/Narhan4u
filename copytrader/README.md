# Paper Copy-Trader (£20, risk-managed)

**Paper trading only.** This tool never connects to an exchange, never holds
API keys and never moves real money. It copies the trades of a trader you
choose using a fake £20 balance. Run it for a few weeks to see whether copying
that trader *actually* makes money once losses and fees are counted, **before**
you risk real money.

## Why paper-trade first
A "93% win rate" claim on X tells you almost nothing. A trader can win 93% of
trades and still lose money if the 7% of losses are big. This tool records the
numbers that matter: **average win vs. average loss, profit factor (total wins ÷
total losses, which must be above 1.0 to make money) and maximum drawdown
(the biggest fall from a peak)**.

## Quick start
```bash
cd copytrader
python3 copytrader.py --sim --poll 1   # try it offline with fake prices
python3 copytrader.py --reset          # then wipe the test account
python3 copytrader.py                  # real prices (CoinGecko), runs until stopped
```
Requires only Python 3 (no packages to install).

## Feeding it a trader's calls
Each time the trader you follow posts a trade, add a row to `signals.csv`:

```csv
id,trader,symbol,side,stop_loss,take_profit,note
1,@sometrader,BTC,long,,,"tweet 5 Nov"
2,@sometrader,ETH,short,2650,2400,
```
- `id` must be unique. `side` is `long` or `short`.
- Leave `stop_loss` / `take_profit` blank to use the defaults (3% / 6%).
- Prices are in GBP. To add more coins, put their CoinGecko id in
  `coingecko_ids` in `config.json`.

The running bot checks the file every `poll_seconds`, so you can add rows while
it runs.

## Runs by itself until you say stop
```bash
nohup python3 copytrader.py > /dev/null 2>&1 &   # keeps running after you log out
tail -f trades.log                               # watch it
python3 copytrader.py --report                   # stats at any time
touch STOP                                       # <- the "stop" command
rm STOP                                          # remove before starting again
```
State is saved to `state.json` after every check, so stopping and restarting
loses nothing. A full report is written to `trades.log` every hour.

## The risk plan (all set in `config.json`)
| Rule | Default | What it does |
|---|---|---|
| Risk per trade | 3% | Position size is set so hitting the stop loses only about £0.60 on £20 |
| Max open trades | 3 | The balance is shared between at most 3 positions. No leverage. |
| Stop-loss / take-profit | 3% / 6% | Every trade has a stop. Each win is set to be about twice the size of each loss. |
| Breakeven stop | at +1R | Once a trade has gained as much as it risked (1R), its stop moves to the entry price so it can no longer lose |
| Daily loss limit | 10% | Stops new trades for 24 hours if the day goes badly |
| Losing streak | 3 in a row | Pauses for 24 hours. This prevents chasing losses. |
| Account stop | £15 | Closes everything and halts at 25% down |
| Lock in profit | at £30 | Sets your original £20 aside and continues with profit only (the account stop scales down too) |
| Drop a trader | 20% drawdown after 10 trades | Stops copying a trader whose record goes bad |
| Fees | 0.1% per side | Taken off every trade, so results are realistic |

## When to consider real money
Only if, after **at least 30 paper trades over 4+ weeks**:
- profit factor is above 1.3,
- maximum drawdown is below 20%, and
- the account never hit the account stop.

Even then, use only a regulated platform (check the FCA Register) and money you
can afford to lose. Never send funds to a trader, a "manager" or a wallet
someone gives you on X.
