import hmac
import hashlib
import uuid
import urllib.request
from config import (
    NTFY_SERVER, NTFY_TOPIC, NTFY_TOKEN,
    APP_BASE_URL, CONFIRMATION_SECRET,
    SMA_FAST, SMA_SLOW, TRADE_QUANTITY,
    CHARGE_BROKERAGE, CHARGE_STT_RATE, CHARGE_ETC_RATE,
    CHARGE_SEBI_RATE, CHARGE_IPFT_RATE, CHARGE_GST_RATE,
    CHARGE_STAMP_RATE, CHARGE_DP_FLAT,
)


def _make_token(signal_id: str) -> str:
    return hmac.new(
        CONFIRMATION_SECRET.encode(),
        signal_id.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]


def _estimate_charges(price: float, action: str, trade_qty: float) -> dict:
    turnover = price * trade_qty
    stt    = round(turnover * CHARGE_STT_RATE, 2)                                        # both sides
    etc    = round(turnover * CHARGE_ETC_RATE, 2)
    sebi   = round(turnover * CHARGE_SEBI_RATE, 2)
    ipft   = round(turnover * CHARGE_IPFT_RATE, 2)
    gst    = round((CHARGE_BROKERAGE + etc + sebi + ipft) * CHARGE_GST_RATE, 2)
    stamp  = round(turnover * CHARGE_STAMP_RATE, 2) if action == "BUY" else 0.0
    dp     = round(CHARGE_DP_FLAT, 2)                if action == "SELL" else 0.0
    total  = round(CHARGE_BROKERAGE + stt + etc + sebi + ipft + gst + stamp + dp, 2)
    return {
        "brokerage": CHARGE_BROKERAGE,
        "stt": stt,
        "etc": etc,
        "sebi": sebi,
        "ipft": ipft,
        "gst": gst,
        "stamp": stamp,
        "dp": dp,
        "total": total,
    }


def send_signal_notification(signal: dict, pending_store: dict, instrument_name: str, ledger_store: dict) -> str:
    """
    Send a ntfy notification with one-click confirm/reject action buttons.
    Returns the generated signal_id.
    """
    signal_id = str(uuid.uuid4())
    token = _make_token(signal_id)
    pending_store[signal_id] = {"signal": signal, "token": token, "executed": False}

    confirm_url = f"{APP_BASE_URL}/confirm?signal_id={signal_id}&token={token}"
    reject_url = f"{APP_BASE_URL}/reject?signal_id={signal_id}&token={token}"
    health_url = f"{APP_BASE_URL}/health"

    action = signal["action"]
    price = signal["price"]
    date = signal["date"]
    sma_fast = signal.get("sma_fast", 0)
    sma_slow = signal.get("sma_slow", 0)
    vol_spike = signal.get("vol_spike", False)
    volume = signal.get("volume", 0)
    avg_volume = signal.get("avg_volume", 0)

    cross_type = "Golden Cross" if action == "BUY" else "Death Cross"
    momentum = "bullish" if action == "BUY" else "bearish"
    price_relation = "above" if action == "BUY" else "below"
    trade_qty = TRADE_QUANTITY if action == "BUY" else ledger_store['TOTAL_EQUITY']

    charges = _estimate_charges(price, action, trade_qty)

    body = (
        f"Trade Decision: {action} {instrument_name}\n\n"
        f"Observation & Rationale\n"
        f"A swing trade opportunity has been identified on {instrument_name} based on the following technical signals:\n\n"
        f"* {SMA_FAST} SMA has crossed {price_relation} the {SMA_SLOW} SMA ({cross_type}), indicating a {momentum} momentum shift\n"
        f"* Price is trading {price_relation} both {SMA_FAST} SMA (INR {sma_fast:,.0f}) and {SMA_SLOW} SMA (INR {sma_slow:,.0f})\n"
        f"* Recent pullback to the {SMA_FAST} SMA provided a low-risk entry zone\n"
    )
    if vol_spike:
        body += f"* Volume spike observed on breakout candle ({volume:,.0f} vs avg {avg_volume:,.0f}), validating the move\n"

    body += (
        f"\nSignal Date: {date} | Entry Price (approx): INR {price:,.2f}\n\n"
        f"Charges & Taxes (qty: {trade_qty})\n"
        f"Brokerage:  INR {charges['brokerage']:.2f} (flat)\n"
        f"STT:        INR {charges['stt']:.2f} (0.1% both sides)\n"
        f"ETC:        INR {charges['etc']:.2f} (0.00322% NSE turnover)\n"
        f"SEBI:       INR {charges['sebi']:.2f} (10/crore)\n"
        f"IPFT:       INR {charges['ipft']:.2f} (10/crore NSE)\n"
        f"GST:        INR {charges['gst']:.2f} (18% on brokerage+ETC+SEBI+IPFT)\n"
        f"Stamp Duty: INR {charges['stamp']:.2f} (0.015% buy side)\n"
        f"DP Charges: INR {charges['dp']:.2f} (sell side per scrip)\n"
        f"Est. Total: ~INR {charges['total']:.2f}\n\n"
        f"Est. Grand Total: ~INR {charges['total']+(price*trade_qty):.2f}\n\n"
        f"Charges are approximate. Final values will reflect in the contract note."
    )

    headers = {
        "Title": f"Trade Signal: {action} {instrument_name} - Swing Trade Confirmation Required",
        "Priority": "high",
        "Tags": "chart_with_upwards_trend" if action == "BUY" else "chart_with_downwards_trend",
        "Actions": f"view, Confirm {action}, {confirm_url}; view, Reject / Skip, {reject_url}; view, App Health Check, {health_url}",
        "Content-Type": "text/plain",
    }
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"

    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    urllib.request.urlopen(req, timeout=10)
    return signal_id
