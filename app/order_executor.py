from kiteconnect import KiteConnect
from kite_client import get_kite
from config import TRADE_QUANTITY

import pandas as pd

df = pd.read_csv("https://api.kite.trade/instruments", low_memory=False)

def _find_instrument(company_name: str, exchange: str):
    """Search by company name (partial match) and exchange."""
    filtered = df[
        (df["exchange"] == exchange.upper()) &
        (df["name"].str.contains(company_name, case=False, na=False)) &
        (df["instrument_type"] == "EQ")  # Only equity, not derivatives
    ]
    results = filtered[["tradingsymbol", "name", "exchange", "instrument_token"]]
    if results.empty:
        raise ValueError(f"No Kite instrument found for {company_name} on {exchange}")
    row = results.iloc[0]
    return {
        "tradingsymbol": row["tradingsymbol"],  # e.g. "RELIANCE"
        "exchange_symbol": f"{row['exchange']}:{row['tradingsymbol']}",  # "NSE:RELIANCE"
        "instrument_token": int(row["instrument_token"])  # 738561
    }

def place_order(action: str, price: float, company_name: str, exchange: str) -> str:
    """Place a market order for the given instrument. Returns the order_id."""
    kite_instrument = _find_instrument(company_name, exchange)
    kite_exchange, kite_symbol = exchange.upper(), kite_instrument["tradingsymbol"]

    kite = get_kite()
    stop_price = price * 0.98 # TODO: find the back tested value

    transaction_type = (
        KiteConnect.TRANSACTION_TYPE_BUY
        if action == "BUY"
        else KiteConnect.TRANSACTION_TYPE_SELL
    )

    # Documentation: https://rdrr.io/github/prodipta/kiteconnect3/man/place_order.html
    order_id = kite.place_order(
        variety=KiteConnect.VARIETY_REGULAR,
        exchange=kite_exchange,
        tradingsymbol=kite_symbol,
        transaction_type=transaction_type,
        quantity=TRADE_QUANTITY,                # TODO: check this for both buy and sell orders
        product=KiteConnect.PRODUCT_CNC,       # change to MIS for intraday
        order_type=KiteConnect.ORDER_TYPE_MARKET,
        trigger_price=stop_price,                   # set this to add stop loss/take profit
    )
    return str(order_id)
