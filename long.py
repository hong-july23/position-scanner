import ccxt
import pandas as pd

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

    # 활성 종목
    if not market.get("active", False):
        continue

    # USDT 무기한 선물만
    if market.get("type") != "swap":
        continue

    if not market.get("linear"):
        continue

    # 주식 선물 제거
    info = market.get("info", {})
    if info.get("underlyingType", "") not in ("", "COIN"):
        continue

    base = market.get("base", "")

    # 레버리지 토큰 및 주식 토큰 제거
    if any(k in base.upper() for k in EXCLUDE_KEYWORDS):
        continue

    # 이상한 긴 심볼 제거
    if len(base) > 10:
        continue

    vol = ticker.get("quoteVolume") or 0
    symbols.append((symbol, vol))

# 거래량순 정렬
symbols.sort(key=lambda x: x[1], reverse=True)
symbols = [s for s, _ in symbols]


results = []

print("start")
for symbol in symbols:
    data = ex.fetch_ohlcv(symbol, timeframe="4h", limit=500)
    
    df = pd.DataFrame(
        data,
        columns=["time", "open", "high", "low", "close", "volume"]
    )

    current_high = df["high"].iloc[-1]
    candle_count = len(df)

    # 기본값
    highest_count = candle_count

    for i in range(2, candle_count + 1):
        if df["high"].iloc[-i] > current_high:
            highest_count = i - 1
            break

    if candle_count < 500 and current_high >= df["high"].max():
        highest_count = 500

    results.append({
        "symbol": symbol,
        "highest_count": highest_count,
        "high": current_high
    })

results.sort(key=lambda x: x["highest_count"], reverse=True)

print("=" * 45)
print(f"{'Symbol':18} {'Highest':>8}")
print("=" * 45)

found = False

for r in results:
    if r["highest_count"] >= 120:
        found = True
        print(f"{r['symbol']:18}")

if not found:
    print("조건을 만족하는 티커가 없습니다.")

print("=" * 45)
