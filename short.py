import ccxt
import pandas as pd

# ==========================
# 설정
# ==========================
LOOKBACK = 70

ex = ccxt.binanceusdm({"enableRateLimit": True})
ex.options["defaultType"] = "future"

# ==========================
# 거래량순 티커 가져오기
# ==========================
markets = ex.load_markets()
tickers = ex.fetch_tickers()

EXCLUDE_KEYWORDS = [
    "UP","DOWN","BULL","BEAR",
    "AAPL","TSLA","AMZN","GOOGL","MSFT","NVDA","META","NFLX",
    "BABA","COIN","SAMSUNG","SKHYNIX","HYUNDAI","SNDK","AMD","INTC",
]

symbols = []

for symbol, ticker in tickers.items():

    if not symbol.endswith(":USDT"):
        continue

    market = markets.get(symbol, {})

    if not market.get("active", False):
        continue

    if market.get("type") != "swap":
        continue

    if not market.get("linear"):
        continue

    info = market.get("info", {})

    if info.get("underlyingType", "") not in ("", "COIN"):
        continue

    base = market.get("base", "")

    if any(k in base.upper() for k in EXCLUDE_KEYWORDS):
        continue

    if len(base) > 10:
        continue

    vol = ticker.get("quoteVolume") or 0
    symbols.append((symbol, vol))

symbols.sort(key=lambda x: x[1], reverse=True)
symbols = [s for s, _ in symbols]

# ==========================
# 최근 LOOKBACK시간의 24시간 상승률 계산
# ==========================
results = []

need_candle = LOOKBACK + 25

for symbol in symbols:

    try:

        data = ex.fetch_ohlcv(symbol, timeframe="1h", limit=need_candle)

        if len(data) < need_candle:
            continue

        df = pd.DataFrame(
            data,
            columns=["time","open","high","low","close","volume"]
        )

        close = df["close"]

        row = {"Symbol": symbol}

        for shift in range(LOOKBACK):

            now = close.iloc[-1-shift]
            past = close.iloc[-25-shift]

            pct = (now-past)/past*100

            row[shift] = pct

        results.append(row)

    except:
        continue

result_df = pd.DataFrame(results)

# ==========================
# 최근 LOOKBACK시간 Top3 티커 추출
# ==========================
top3_info = {}

for shift in range(LOOKBACK):

    top3 = result_df.nlargest(3, shift)[["Symbol", shift]]

    for rank, (_, r) in enumerate(top3.iterrows(), start=1):

        symbol = r["Symbol"]

        if symbol not in top3_info:
            top3_info[symbol] = {
                "best_rank": rank,
                "best_shift": shift
            }

        else:

            if rank < top3_info[symbol]["best_rank"]:

                top3_info[symbol]["best_rank"] = rank
                top3_info[symbol]["best_shift"] = shift

            elif (
                rank == top3_info[symbol]["best_rank"]
                and shift < top3_info[symbol]["best_shift"]
            ):
                top3_info[symbol]["best_shift"] = shift

# ==========================
# 최고점 대비 -10% + 5MA<20MA
# ==========================
print("="*80)
print("조건 만족 티커")
print("="*80)

k = "1h"
for symbol, info in sorted(
    top3_info.items(),
    key=lambda x: (x[1]["best_shift"], x[1]["best_rank"])
):

    try:
        print(symbol)
        # MA 계산을 위해 20개 이상 필요
        data = ex.fetch_ohlcv(symbol, timeframe=k, limit=LOOKBACK+20)

        if len(data) < LOOKBACK+20:
            continue

        df = pd.DataFrame(
            data,
            columns=["time","open","high","low","close","volume"]
        )

        close = df["close"]

        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]

        current = close.iloc[-1]

        # 최근 LOOKBACK시간 최고가
        highest = df["high"].iloc[-LOOKBACK:].max()

        drawdown = (current-highest)/highest*100

        if drawdown <= -10 or ma5 < ma20:
            print(f"{symbol:20}")

    except:
        continue
