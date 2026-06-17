import yfinance as yf
import pandas as pd

ticker = yf.Ticker("AAPL")

# 1. Test history
try:
    hist = ticker.history(period="1d")
    if not hist.empty:
        print("Latest price from history:", hist['Close'].iloc[-1])
    else:
        print("History empty")
except Exception as e:
    print("Error getting history:", e)

# 2. Test dividends
try:
    divs = ticker.dividends
    print("Dividends type:", type(divs))
    if not divs.empty:
        print("Latest dividend payments:")
        print(divs.tail(5))
        # Sum of last year
        last_year = divs[divs.index > (divs.index[-1] - pd.Timedelta(days=365))]
        print("Sum of last year dividends:", last_year.sum())
    else:
        print("Dividends series is empty")
except Exception as e:
    print("Error getting dividends:", e)

# 3. Test cashflow index (to see where Depreciation & Amortization is)
try:
    cf = ticker.cashflow
    print("Cashflow index items:")
    for item in cf.index:
        print(f"  {item}")
except Exception as e:
    print("Error getting cashflow:", e)
