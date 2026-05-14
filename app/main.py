"""
MARKET 20/50 SMA Swing Trader
---------------------------------
* FastAPI handles /confirm and /reject endpoints (ntfy confirmation links).
* APScheduler runs a daily EOD check for new crossover signals.
* On signal → ntfy notification sent with confirm/reject action buttons.
* On /confirm hit → order placed via Kite Connect.
"""
import time
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager

from anyio import sleep
from fastapi import FastAPI, HTTPException, Query
from apscheduler.schedulers.background import BackgroundScheduler

from market_data import fetch_daily_ohlcv
from strategy import compute_signals, get_latest_signal
from notifier import send_signal_notification, _make_token
from ledger import validate_trade_update_ledger
from order_executor import place_order
from config import INSTRUMENT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# In-memory store: {signal_id: {signal, token, executed}}
PENDING: dict = {}
LEDGER: dict = {'TOTAL_EQUITY': 0, 'TOTAL_FUNDS': 1000000, 'TOTAL_VALUE': 1000000}


def daily_check(today: datetime = None):
    """Fetch data, compute signals, send WhatsApp if new crossover detected."""
    log.info(f"Running daily market SMA check for {INSTRUMENT['name']} on {INSTRUMENT['exchange']} ...")
    try:
        today = datetime.today() if today is None else today
        df = fetch_daily_ohlcv(INSTRUMENT["name"], INSTRUMENT["exchange"], today)
        df = compute_signals(df)
        signal = get_latest_signal(df)
        log.info(f"Signal computed: {signal}")

        if signal:
            go_ahead = validate_trade_update_ledger(signal, LEDGER)
            if not go_ahead:
                log.info("Ledger validation failed. Skipping signal.")
                return
            log.info(f"Signal detected: {signal}")
            sid = send_signal_notification(signal, PENDING, INSTRUMENT["name"], LEDGER)
            log.info(f"ntfy notification sent. signal_id={sid}")
        else:
            log.info("No crossover signal today.")
    except Exception as e:
        log.error(f"daily_check error: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    # Run Mon-Fri at 15:35 IST (09:05 UTC) — just after market close
    scheduler.add_job(daily_check, "cron", day_of_week="mon-fri", hour=9, minute=5)
    scheduler.start()
    log.info("Scheduler started.")
    yield
    scheduler.shutdown()


app = FastAPI(title="Market SMA Trader", lifespan=lifespan)


def _validate(signal_id: str, token: str):
    entry = PENDING.get(signal_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Signal not found or already actioned.")
    if entry["executed"]:
        raise HTTPException(status_code=409, detail="Signal already executed.")
    expected = _make_token(signal_id)
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid token.")
    return entry


@app.get("/confirm")
def confirm_trade(signal_id: str = Query(...), token: str = Query(...)):
    entry = _validate(signal_id, token)
    signal = entry["signal"]

    order_id = place_order(signal["action"], signal["price"], INSTRUMENT["name"], INSTRUMENT["exchange"])
    entry["executed"] = True

    log.info(f"Order placed: {signal['action']} {INSTRUMENT['name']} | order_id={order_id}")
    return {
        "status": "Order placed ✅",
        "action": signal["action"],
        "order_id": order_id,
    }


@app.get("/reject")
def reject_trade(signal_id: str = Query(...), token: str = Query(...)):
    entry = _validate(signal_id, token)
    entry["executed"] = True   # mark done so it can't be reused
    log.info(f"Signal {signal_id} rejected by user.")
    return {"status": "Signal rejected ❌", "signal_id": signal_id}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/check_now")
def check_now():
    try:
        INSTRUMENT["name"] = "SNP 500"
        INSTRUMENT["exchange"] = "NSE"
        today = datetime.today()
        start = today - timedelta(days=300)
        end = today - timedelta(days=15)
        details = []
        while start <= end:
            daily_check(start)
            start += timedelta(days=1)
            entry = f"Date: {start.strftime('%Y-%m-%d')}, Total Equity: {LEDGER['TOTAL_EQUITY']}, Total Funds: {LEDGER['TOTAL_FUNDS']}, Total Value: {LEDGER['TOTAL_VALUE']}"
            log.info(entry)
            details.append(entry)
            time.sleep(1)
        return {"status": "ok", "ledger": details}
    except Exception as e:
        log.error(f"daily_check error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# http://localhost:18000/update_instrument?name=BANKNIFTY&exchange=NSE
# http://localhost:18000/update_instrument?name=RELIANCE industries&exchange=NSE

@app.get("/update_instrument")
def update_instrument(
    name: str = Query(None, description="Instrument name, e.g. NIFTY50"),
    exchange: str = Query(None, description="Exchange, e.g. NSE"),
):
    updated = {}

    if name is not None:
        INSTRUMENT["name"] = name.title()
        updated["name"] = name.title()
    if exchange is not None:
        INSTRUMENT["exchange"] = exchange.upper()
        updated["exchange"] = exchange.upper()

    if not updated:
        raise HTTPException(status_code=400, detail="No parameters provided.")

    log.info(f"Instrument updated: {updated}")
    return {"status": "updated ✅", "updated": updated, "current": INSTRUMENT}
