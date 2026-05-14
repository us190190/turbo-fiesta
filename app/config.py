import os

KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")

NTFY_SERVER = os.getenv("NTFY_SERVER")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
NTFY_TOKEN = os.getenv("NTFY_TOKEN")  # optional Bearer token for private topics

APP_BASE_URL = os.getenv("APP_BASE_URL")
CONFIRMATION_SECRET = os.getenv("CONFIRMATION_SECRET")

# Instrument configuration (overridable at runtime via POST /set_instrument)
INSTRUMENT = {
    "name": os.getenv("INSTRUMENT_NAME", "BANKNIFTY"),
    "exchange": os.getenv("INSTRUMENT_EXCHANGE", "NSE"),
}

# Quantity per trade (lot size or units)
TRADE_QUANTITY = 15

# SMA periods
SMA_FAST = 3 # 20
SMA_SLOW = 8 # 50

# Volume spike detection: candle volume must exceed this multiple of the SMA_FAST-period average
VOLUME_SPIKE_FACTOR = 1.5

# Per-order charge rates (equity delivery, NSE — updated May 2026)
CHARGE_BROKERAGE     = float(os.getenv("CHARGE_BROKERAGE",     "20"))        # flat ₹ per order
CHARGE_STT_RATE      = float(os.getenv("CHARGE_STT_RATE",      "0.001"))     # 0.1% on buy & sell
CHARGE_ETC_RATE      = float(os.getenv("CHARGE_ETC_RATE",      "0.0000322")) # 0.00322% NSE turnover (revised 2026)
CHARGE_SEBI_RATE     = float(os.getenv("CHARGE_SEBI_RATE",     "0.000001"))  # ₹10 per crore
CHARGE_IPFT_RATE     = float(os.getenv("CHARGE_IPFT_RATE",     "0.000001"))  # ₹10 per crore (NSE IPFT)
CHARGE_GST_RATE      = float(os.getenv("CHARGE_GST_RATE",      "0.18"))      # 18% on brokerage+ETC+SEBI+IPFT
CHARGE_STAMP_RATE    = float(os.getenv("CHARGE_STAMP_RATE",    "0.00015"))   # 0.015% buy side only
CHARGE_DP_FLAT       = float(os.getenv("CHARGE_DP_FLAT",       "15.34"))     # ₹/scrip on sell (CDSL+broker+GST)

# Number of daily candles to fetch
CANDLES_TO_FETCH = 200
