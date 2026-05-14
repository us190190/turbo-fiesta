import pandas as pd
from config import SMA_FAST, SMA_SLOW, VOLUME_SPIKE_FACTOR


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add SMA20, SMA50 and crossover signal columns to df."""
    df = df.copy()
    df["sma_fast"] = df["close"].rolling(SMA_FAST).mean()
    df["sma_slow"] = df["close"].rolling(SMA_SLOW).mean()
    df["above"] = (df["sma_fast"] > df["sma_slow"]).astype(int)
    df["signal"] = df["above"].diff()
    # signal == 1 → bullish crossover (BUY)
    # signal == -1 → bearish crossover (SELL / exit)
    return df.dropna(subset=["sma_fast", "sma_slow"])


def get_latest_signal(df: pd.DataFrame) -> dict | None:
    """Return the latest signal on the most recent candle, or None."""
    latest = df.iloc[-1]
    if latest["signal"] not in (1.0, -1.0):
        return None

    action = "BUY" if latest["signal"] == 1.0 else "SELL"

    avg_vol = df["volume"].iloc[-(SMA_FAST + 1):-1].mean()
    vol_spike = latest["volume"] > avg_vol * VOLUME_SPIKE_FACTOR if avg_vol > 0 else False

    return {
        "action": action,
        "price": latest["close"],
        "date": str(latest["date"].date()),
        "sma_fast": latest["sma_fast"],
        "sma_slow": latest["sma_slow"],
        "volume": latest["volume"],
        "avg_volume": avg_vol,
        "vol_spike": vol_spike,
    }
