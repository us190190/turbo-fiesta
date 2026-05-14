# Market SMA Swing Trader

A Dockerised Python service that:
1. Checks market daily candles for configurable SMA crossover signals (EOD, Mon–Fri at 15:35 IST)
2. Sends ntfy notifications with signal details + one-click confirm/reject action buttons
3. Computes estimated trading charges (brokerage, STT, taxes, DP fees)
4. Places orders on Zerodha Kite Connect **only after you click Confirm**
5. Tracks ledger with equity, funds, and total portfolio value

---

## Project Structure

```
market-trader/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── SECURITY.md
├── README.md
└── app/
    ├── config.py              # All env var configuration + SMA periods, charges
    ├── kite_client.py         # Zerodha Kite Connect session manager
    ├── market_data.py         # Fetch historical daily OHLCV data
    ├── strategy.py            # SMA crossover logic + volume spike detection
    ├── notifier.py            # ntfy notification + charge estimation
    ├── order_executor.py      # Place orders via Kite Connect
    ├── ledger.py              # Track portfolio equity, funds, and total value
    └── main.py                # FastAPI app + APScheduler for daily signals
```

---

## Quick Start

### 1. Prerequisites
- Zerodha Kite Connect API subscription (₹2000/month or free tier)
- ntfy server (self-hosted or public ntfy.sh)
- Docker & Docker Compose

### 2. Configure Environment
```bash
cp .env.example .env
# Fill in all values:
# - KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN
# - NTFY_SERVER, NTFY_TOPIC, NTFY_TOKEN (optional for private topics)
# - APP_BASE_URL (e.g., https://your-domain.com)
# - CONFIRMATION_SECRET (any long random string)
# - Charge rates (brokerage, STT, ETC, SEBI, IPFT, GST, stamp, DP)
```

### 3. Daily Kite Access Token Refresh
Kite access tokens expire daily. You need to manually refresh or automate:

**Manual Method:**
- Open `https://kite.trade/connect/login?api_key=YOUR_API_KEY`
- Login and grab the `request_token` from the redirect URL
- Run:
  ```python
  from kiteconnect import KiteConnect
  kite = KiteConnect(api_key="YOUR_API_KEY")
  data = kite.generate_session("REQUEST_TOKEN", api_secret="YOUR_SECRET")
  print(data["access_token"])  # Copy this to .env as KITE_ACCESS_TOKEN
  ```
- Update `.env` and restart: `docker compose up -d`

> 💡 **Automation:** Use a headless browser (Selenium/Playwright) + a morning cron job to auto-refresh tokens daily.

### 4. Run the Service
```bash
docker compose up -d
```

### 5. Make App Publicly Accessible
The notification action buttons must point to a publicly reachable URL. Options:
- **VPS Deployment:** DigitalOcean, Hetzner, AWS EC2
- **Local Testing:** Use ngrok: `ngrok http 8000` → set `APP_BASE_URL` to the ngrok URL
- **Reverse Proxy:** Caddy / nginx with Let's Encrypt (HTTPS recommended)

---

## How the Signal Flow Works

```
15:35 IST (Mon–Fri, ~09:05 UTC)
       │
       ▼
fetch_daily_ohlcv()          ← Kite historical_data API, last 200 candles
       │
       ▼
compute_signals()            ← Calculate SMA Fast (default 3), SMA Slow (default 8)
       │                      ← Detect crossovers + volume spike
       │
       ▼
get_latest_signal()          ← Check for crossover on latest candle
       │
    signal?
     /   \
   YES    NO → done
    │
    ▼
validate_trade_update_ledger()  ← Check if sufficient funds/equity
    │
   PASS?
    /  \
  YES   NO → skip signal
   │
   ▼
send_signal_notification()   ← ntfy → your device
    │
    ▼
ntfy notification with:
   📱 Confirm [action] ─→ POST /confirm?signal_id=...&token=...
   ❌ Reject / Skip ────→ POST /reject?signal_id=...&token=...
    │
    ├─ You click ✅ → place_order() via Kite Connect
    └─ You click ❌ → signal marked rejected, no order placed
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/confirm?signal_id=&token=` | Confirm signal and place order |
| GET | `/reject?signal_id=&token=` | Reject signal (no order) |
| GET | `/health` | Health check (used in ntfy actions) |
| GET | `/update_instrument?name=NIFTY50&exchange=NSE` | Change trading instrument at runtime |
| GET | `/check_now` | Run signal check for a date range (for backtesting) |

---

## Customisation

| Feature | Configuration |
|---------|----------------|
| Change SMA periods | `app/config.py` → `SMA_FAST`, `SMA_SLOW` (default: 3, 8) |
| Change trade quantity | `app/config.py` → `TRADE_QUANTITY` (default: 15) |
| Adjust volume spike threshold | `app/config.py` → `VOLUME_SPIKE_FACTOR` (default: 1.5x avg) |
| Change scheduling time | `app/main.py` → `scheduler.add_job(..., hour=9, minute=5)` |
| Modify charge rates | `app/config.py` → `CHARGE_*` environment variables |
| Add additional filters | `app/strategy.py` → extend `get_latest_signal()` |
| Switch order type (CNC ↔ MIS) | `app/order_executor.py` → adjust `product=` parameter |
| Add stop-loss / take-profit | `app/order_executor.py` → use `trigger_price`, `stop_loss` in `place_order()` |
| Persist signals across restarts | Replace `PENDING` dict in `app/main.py` with SQLite / Redis |

---

## Security Notes
- ✅ Never commit `.env` to git — add it to `.gitignore`
- ✅ Confirmation tokens are HMAC-SHA256, cannot be guessed
- ✅ Each signal can only be confirmed/rejected once (idempotent)
- ✅ Use HTTPS in production (Caddy, nginx + Let's Encrypt)
- ✅ Keep `CONFIRMATION_SECRET` private and strong
- ✅ Token-based access only for ntfy notifications

See [SECURITY.md](./SECURITY.md) for additional security guidelines.

---

## Configuration Reference

### Environment Variables

```
# Zerodha Kite Connect
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=your_access_token  # Refresh daily

# ntfy Server
NTFY_SERVER=https://ntfy.sh           # or your self-hosted server
NTFY_TOPIC=my-trading-alerts          # Topic name
NTFY_TOKEN=optional_bearer_token      # For private topics

# App Configuration
APP_BASE_URL=https://your-domain.com  # Must be publicly accessible
CONFIRMATION_SECRET=any_random_long_string  # For HMAC token generation

# Instrument (default: BANKNIFTY, NSE)
INSTRUMENT_NAME=BANKNIFTY
INSTRUMENT_EXCHANGE=NSE

# Charge Rates (INR, equity delivery NSE — as of May 2026)
CHARGE_BROKERAGE=20                   # ₹/order flat
CHARGE_STT_RATE=0.001                 # 0.1% both buy & sell
CHARGE_ETC_RATE=0.0000322             # 0.00322% NSE turnover
CHARGE_SEBI_RATE=0.000001              # ₹10/crore
CHARGE_IPFT_RATE=0.000001              # ₹10/crore NSE IPFT
CHARGE_GST_RATE=0.18                  # 18% on brokerage+ETC+SEBI+IPFT
CHARGE_STAMP_RATE=0.00015             # 0.015% on buy side only
CHARGE_DP_FLAT=15.34                  # ₹/scrip on sell (CDSL+broker+GST)
```

---

## Monitoring & Debugging

### View Logs
```bash
docker logs -f market-trader
```

### Check Service Status
```bash
curl http://localhost:18000/health
```

### Test Instrument Change
```bash
curl "http://localhost:18000/update_instrument?name=INFY&exchange=NSE"
```

### Backtest Historical Signals
```bash
curl "http://localhost:18000/check_now"
```
(Runs signal detection for the last 300 days, simulating trades and tracking ledger)

---

## Dependencies

- **FastAPI** — Web framework for HTTP endpoints
- **uvicorn** — ASGI server
- **yfinance** — Fetch historical market data
- **pandas** — Data manipulation and SMA calculation
- **APScheduler** — Schedule daily EOD checks
- **kiteconnect** — Zerodha Kite API client

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `signal not found` on confirm/reject | Signal was already actioned or expired (handled by PENDING dict) |
| `Kite access token expired` | Refresh token daily (see Quick Start step 3) |
| No signals detected | Check SMA periods, volume requirements, and market conditions |
| ntfy notifications not received | Verify `NTFY_SERVER`, `NTFY_TOPIC`, and bearer token (if private) |
| App not reachable for action buttons | Ensure `APP_BASE_URL` is correct and publicly accessible |
| Charges seem incorrect | Review charge rates in `.env` and calculation in `app/notifier.py` |

---

## License

Refer to [SECURITY.md](./SECURITY.md) for licensing and legal information.

---

## Contributing

Pull requests welcome! Please ensure:
- Code follows existing style
- SMA/strategy logic is well-documented
- Charge calculations are accurate for your exchange/region
