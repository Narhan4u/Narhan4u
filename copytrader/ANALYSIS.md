# Analysis: copying an X trader on Invo with £20

*Prepared 6 Nov 2026. Not financial advice.*

## 1. The X post
Link given: `x.com/eianlu/status/2118317430665613741`

**I could not read it.** X blocks automated access, and web searches for
"eianlu" found no public record (no profile, track record, press or
Hyperliquid leaderboard entry). So nothing about this trader is verified:
not the win rate, not the profit, not whether they even trade on Invo.

To make the claim checkable, get **the trader's Hyperliquid wallet address**
(shown on their Invo profile, or ask them) and run:

```bash
python3 trader_check.py 0xTHEIR_WALLET --days 180
```

That reads their **real** trades from Hyperliquid's public data. If they won't
share a wallet, treat the claim as unverified and don't copy.

## 2. What Invo actually is
- **Invo (Involio)** is a social copy-trading app. It runs on **Hyperliquid**, a
  crypto *perpetual futures* exchange (leveraged long/short contracts on
  coins, not buying the coins themselves).
  ([Crypto Briefing](https://cryptobriefing.com/invoxyz-surpasses-trust-wallet-hyperliquid-volume/),
  [App Store](https://apps.apple.com/in/app/invo-where-traders-are-made/id1601301148))
- It is large: reported as #2 by "builder code" volume on Hyperliquid, about
  $1.49bn of trading in 30 days from about 40,000 traders. That shows the app
  is busy. It doesn't show that the traders on it make money.
- **Costs on top of the trade:**
  - Hyperliquid trading fees.
  - Invo's own builder fee.
  - **Funding charged every hour** while a position is open. Guides report it
    can eat a meaningful share of margin on crowded trades held for days.

  ([Cipher](https://cipher-intelligence.io/blog/hyperliquid-copy-trading/),
  [FOMOBYTE review](https://fomobyte.com/invo-app-review/))
- **Regulation:**
  - Hyperliquid is an unregulated, decentralised exchange
    ([DayTrading.com review](https://www.daytrading.com/hyperliquid)).
  - In the UK, the FCA bans firms from selling crypto derivatives to retail
    customers. Using an offshore decentralised exchange means **no FCA
    protection and no Financial Ombudsman** if something goes wrong.
- **User reports** include deposits failing and settings not saving
  (Google Play and Trustpilot reviews). These are anecdotes, but worth
  knowing with any amount of money.

## 3. Why "93% win rate" is the wrong thing to chase
Win rate counts how *often* someone wins, not how *much*. The repo includes a
worked example (`trader_check.py` on a synthetic record):

| | |
|---|---|
| Win rate | **93.3%** |
| Average win | $7.50 |
| Average loss | **-$150.50** |
| Profit factor | 0.70 (below 1.0 = losing money) |
| Net after fees | **-$530** |
| Max drawdown | 28% |

A record like that looks amazing in a screenshot and still loses money. It is
also the typical pattern of very high win rates on leveraged perps: take small
profits quickly, and hold losers hoping they come back, until one liquidation
wipes out months. Partial closes also inflate the win rate, so the reported
number is often higher than the real one.

**What to look for instead** (these are the checks `trader_check.py` runs):
- 30+ closed trades over 60+ days.
- Profit factor (total wins ÷ total losses) above 1.3.
- Average win at least half the size of the average loss.
- Zero liquidations.
- Max drawdown (biggest fall from a peak) under 20%.
- Profitable after fees.

## 4. What £20 means here
- Copied positions are tiny, so fees and funding take a much bigger
  percentage bite.
- Lead traders often use 10–50× leverage. A copier at the same leverage can
  be **liquidated in one move of 2–10%**, losing the whole £20 instantly.
  The bot is set to `max_leverage: 1` for this reason.
- Some copy apps have minimum sizes per copied trade. With £20 split three
  ways, some trades may not copy at all.

## 5. The plan (what the repo now does)
1. **Verify** the trader with `trader_check.py`. Stop here if the verdict is
   DO NOT COPY.
2. **Paper-copy automatically.** Put their wallet in `follow_wallets` in
   `config.json`. The bot watches their public Hyperliquid trades every
   minute:
   - When they open a position, it opens a paper copy, sized by the risk
     rules.
   - When they close, it closes the copy.

   It runs until you create a `STOP` file.
3. **Risk rules on every copy:**
   - Risk 3% per trade, with a 3% stop-loss and 6% take-profit.
   - Once a trade is up by the amount it risked, its stop moves to the entry
     price so it can't turn into a loss.
   - Max 3 open trades, and no leverage.
   - Hourly funding and fees are charged so results are realistic.
4. **Account-level brakes:**
   - A 10% loss in a day, or 3 losses in a row, pauses new trades for 24 hours.
   - At £15, everything closes and trading halts.
   - At £30, your original £20 is set aside and only profit keeps trading.
   - Copying stops automatically if the trader's drawdown passes 20%.
5. **Decide after 4+ weeks and 30+ paper trades.** Only consider real money
   if profit factor is above 1.3, drawdown stayed under 20% and the account
   stop never triggered. If you do go live, place trades yourself in Invo
   with 1–2× leverage at most. Never give anyone your seed phrase or send
   money to a trader.

## 6. What I could not do
- **Read the X post**, or confirm who "eianlu" is or their stats.
- **Reach Hyperliquid from this cloud session**, so live tests were done
  against a simulated API. It works the same way on your computer, which has
  normal internet.
- **Open an Invo account or trade real money.** That needs you, your identity
  and your wallet, and I won't take custody of funds or place live trades for
  you.
