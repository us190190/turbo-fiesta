import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import CANDLES_TO_FETCH

def _find_ticker(company_name: str, exchange: str) -> str | None:
    search = yf.Search(f"{company_name}", max_results=10)
    exchange_map = {"NSE": "NSI", "BSE": "BSE"}  # Yahoo's internal exchange codes
    target = exchange_map.get(exchange.upper())
    for quote in search.quotes:
        if quote.get("exchange") == target:
            return quote["symbol"]
    return None

def fetch_daily_ohlcv(company_name: str, exchange: str, to_date: datetime = None) -> pd.DataFrame:
    """Fetch last CANDLES_TO_FETCH daily candles for the given Yahoo Finance ticker."""
    yf_ticker = _find_ticker(company_name, exchange) if to_date is None else "^GSPC"  # TODO: remove after back testing
    if not yf_ticker:
        raise ValueError(f"Yahoo Ticker not found for {company_name} on {exchange}")
    to_date = datetime.today() if to_date is None else to_date
    from_date = to_date - timedelta(days=int(CANDLES_TO_FETCH * 1.5))

    ticker = yf.Ticker(yf_ticker)
    df = ticker.history(
        start=from_date.strftime("%Y-%m-%d"),
        end=to_date.strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=True,
    )

    df = df.reset_index()
    df = df.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("date").reset_index(drop=True)
    return df.tail(CANDLES_TO_FETCH)
