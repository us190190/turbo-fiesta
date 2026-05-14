import logging

from notifier import _estimate_charges
from config import TRADE_QUANTITY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def validate_trade_update_ledger(signal: dict, ledger_store: dict) -> bool:
    action = signal["action"]
    price = signal["price"]
    trade_qty = TRADE_QUANTITY if action == "BUY" else ledger_store['TOTAL_EQUITY']
    charges = _estimate_charges(price, action, trade_qty)
    if action == "BUY":
        funds_needed = charges['total'] + (price * TRADE_QUANTITY)
        if ledger_store['TOTAL_FUNDS'] >= funds_needed:
            ledger_store['TOTAL_FUNDS'] -= funds_needed
            ledger_store['TOTAL_EQUITY'] += TRADE_QUANTITY
            ledger_store['TOTAL_VALUE'] = ledger_store['TOTAL_FUNDS'] + (ledger_store['TOTAL_EQUITY']*price)
        else:
            log.warning(f"Insufficient funds in the account to cover the transaction. Funds needed: {funds_needed}, Funds available: {ledger_store['TOTAL_FUNDS']}")
            return False
    else:
        if trade_qty:
            ledger_store['TOTAL_EQUITY'] -= trade_qty
            ledger_store['TOTAL_FUNDS'] += (price * trade_qty) - charges['total']
            ledger_store['TOTAL_VALUE'] = ledger_store['TOTAL_FUNDS'] + (ledger_store['TOTAL_EQUITY'] * price)
        else:
            log.warning(f"Insufficient equity in the account to cover the transaction. Equity needed: {trade_qty}, Equity available: {ledger_store['TOTAL_EQUITY']}")
            return False

    return True