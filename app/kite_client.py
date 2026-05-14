from kiteconnect import KiteConnect
from config import KITE_API_KEY, KITE_ACCESS_TOKEN


def get_kite() -> KiteConnect:
    kite = KiteConnect(api_key=KITE_API_KEY)
    kite.set_access_token(KITE_ACCESS_TOKEN)
    return kite
