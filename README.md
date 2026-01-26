# Protocol-14 WEEX AI Trading Bot enero 2026

<p align="center">
  <b>AI-Powered Algorithmic Trading System for WEEX Futures</b><br>
  <i>Built for WEEX AI Trading Hackathon 2026</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Platform-WEEX-orange.svg" alt="WEEX">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen.svg" alt="Status">
</p>

---

## Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Trading Strategies](#-trading-strategies)
- [Utilities](#-utilities)
- [API Reference](#-api-reference)
- [Running the Bot](#-running-the-bot)
- [Dashboard](#-dashboard)
- [Risk Management](#-risk-management)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

Protocol-14 is a sophisticated AI-powered trading bot designed for the WEEX cryptocurrency futures exchange. It combines technical analysis, AI sentiment analysis, and multiple trading strategies to execute automated trades with robust risk management.

### Key Highlights

- **Multi-Strategy Architecture**: Supports Grid Trading, Peak Hunter, and more
- **AI Integration**: DeepSeek AI for market sentiment analysis
- **Real-Time Monitoring**: Live dashboard with trade alerts
- **Risk Controls**: Built-in position limits, stop-loss, and daily loss caps
- **Telegram Notifications**: Real-time trade alerts to your phone

---

## Features

### Trading Strategies
| Strategy | Description | Best For |
|----------|-------------|----------|
| **Grid Trading** | Places orders at fixed intervals to profit from volatility | Sideways/ranging markets |
| **Peak Hunter** | Detects overbought/oversold conditions for reversals | Volatile coins (DOGE, SOL) |
| **Momentum Scalper** | Quick trades based on short-term momentum | Fast-moving markets |

### Technical Indicators
- **RSI** (Relative Strength Index) - Overbought/Oversold detection
- **MACD** (Moving Average Convergence Divergence) - Trend and momentum
- **SMA/EMA** - Trend direction analysis
- **Volume Analysis** - Unusual activity detection

### AI Features
- **DeepSeek Sentiment Analysis** - Analyzes market news and social sentiment
- **Contrarian Signals** - Identifies potential reversal opportunities
- **Confidence Scoring** - AI-powered trade confidence levels

---

## Architecture

```
protocol-14-weex/
├── main.py                    # Entry point - API connectivity test
├── weex_client.py             # WEEX API client with HMAC authentication
├── dashboard.py               # Real-time monitoring dashboard
├── run_grid_bot.py            # Grid Trading launcher
├── run_peak_hunter.py         # Peak Hunter launcher
├── momentum_scalper.py        # Momentum Scalper strategy
├── check_ip.py                # IP whitelist verification
├── check_positions.py         # Position monitoring
│
├── strategies/                # Trading strategies
│   ├── __init__.py
│   ├── base_strategy.py       # Abstract base class
│   ├── grid_trading.py        # Grid Trading strategy
│   └── peak_hunter.py         # Peak Hunter strategy
│
├── utils/                     # Utility modules
│   ├── __init__.py
│   ├── indicators.py          # Technical indicators (RSI, MACD)
│   ├── risk_manager.py        # Risk management system
│   ├── sentiment.py           # DeepSeek AI integration
│   └── telegram_notifier.py   # Telegram alerts
│
├── tests/                     # Test suite
│   ├── __init__.py
│   └── api_test.py            # API tests
│
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker deployment
├── fly.toml                   # Fly.io deployment config
└── .env                       # API credentials (create this)
```

---

## Installation

### Prerequisites

- Python 3.12 or higher
- WEEX API credentials (with IP whitelist)
- (Optional) DeepSeek API key for AI features
- (Optional) Telegram Bot for notifications

### Step 1: Clone the Repository

```bash
git clone https://github.com/protocol-14-weex/protocol-14-weex.git
cd protocol-14-weex
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy example and edit with your credentials
cp .env.example .env
```

---

## ⚙️ Configuration

Create a `.env` file in the project root with your credentials:

```env
# ===== WEEX API Credentials (REQUIRED) =====
WEEX_API_KEY=your_api_key_here
WEEX_SECRET_KEY=your_secret_key_here
WEEX_PASSPHRASE=your_passphrase_here

# ===== DeepSeek AI (OPTIONAL) =====
DEEPSEEK_API_KEY=your_deepseek_key_here

# ===== Telegram Notifications (OPTIONAL) =====
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=your_chat_id
```

### WEEX API Setup

1. Log in to [WEEX Exchange](https://www.weex.com/)
2. Go to **API Management**
3. Create a new API key with:
   - ✅ Trade permissions
   - ✅ Read permissions
4. **IMPORTANT**: Add your IP to the whitelist
5. Copy the API Key, Secret Key, and Passphrase

### Verify IP Whitelist

```bash
python check_ip.py
```

Expected output when IP is whitelisted:
```
🌐 Your Current Public IP: x.x.x.x
🔐 Testing Private API (Account Assets)...
✅ Status: 200 - IP is whitelisted!
```

---

## 📈 Trading Strategies

### 1. Conservative Grid Bot (Scalper V2)

This is the main strategy (`conservative_grid.py`) designed for the Hackathon. It is a **Hybrid Mean Reversion** bot.

**Core Logic:**
- **Entry**: Uses **Bollinger Bands (2.0 std)** + **RSI (14)**.
    -   *Short Signal*: Price breaks ABOVE Upper Band AND RSI > 65 (Overbought).
    -   *Long Signal*: Price breaks BELOW Lower Band AND RSI < 35 (Oversold).
- **Exit**: Dynamic Take Profit and Stop Loss based on **ATR (Average True Range)**.
    -   Stop Loss = 2x ATR (Wider stops during high volatility).
    -   Take Profit = 1.5x ATR.

**Safety Features:**
- **State Sync**: Automatically detects open positions on startup.
- **Trend Filter**: Checks 15m trend to avoid trading against strong momentum.
- **Daily Limits**: Stops trading if daily loss limit is hit.

**Run this bot:**
```bash
python conservative_grid.py
```

### 2. Grid Trading Strategy (Legacy)

Classic grid trading that places orders at fixed intervals. Good for sideways markets but riskier in trends.

```python
python run_grid_bot.py
```

### 3. Peak Hunter Strategy

Detects extreme overbought/oversold conditions on volatile coins (DOGE, SOL, PEPE).

```bash
python run_peak_hunter.py
```

---

## 🔧 Utilities

### Technical Indicators (`utils/indicators.py`)

```python
from utils.indicators import TechnicalIndicators

indicators = TechnicalIndicators(client, "cmt_btcusdt")

# Get RSI
rsi = indicators.calculate_rsi()
print(f"RSI: {rsi.value} - {rsi.signal}")

# Get combined signal
signals = indicators.get_combined_signal()
```

**Available Indicators:**
- `calculate_rsi(period=14)` - Relative Strength Index
- `calculate_macd()` - MACD with signal line
- `get_combined_signal()` - Aggregated signal

---

### Risk Manager (`utils/risk_manager.py`)

```python
from utils.risk_manager import RiskManager, RiskLimits

limits = RiskLimits(
    max_position_size_usd=100,    # Max per position
    max_total_exposure_usd=500,   # Max total exposure
    max_leverage=5,                # Max leverage
    max_daily_loss_usd=50,        # Stop if daily loss exceeds
    max_daily_trades=50,           # Max trades per day
    stop_loss_percent=2.0,        # Default SL
    take_profit_percent=3.0       # Default TP
)

risk_manager = RiskManager(limits)

# Check if can trade
can_trade, reason = risk_manager.can_open_position(size_usd=20, symbol="btc")
```

---

### Telegram Notifier (`utils/telegram_notifier.py`)

```python
from utils.telegram_notifier import TelegramNotifier

notifier = TelegramNotifier()
notifier.send_trade_alert(
    action="BUY",
    symbol="BTCUSDT",
    price=95000,
    size=0.001,
    profit=None
)
```

**Setup Telegram:**
1. Message @BotFather on Telegram
2. Create new bot with `/newbot`
3. Get your chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Add to `.env` file

---

### DeepSeek Sentiment (`utils/sentiment.py`)

```python
from utils.sentiment import DeepSeekSentiment

sentiment = DeepSeekSentiment()
result = sentiment.get_signal("BTC")

print(f"Sentiment: {result['sentiment']}")  # bullish/bearish/neutral
print(f"Confidence: {result['confidence']}%")
```

---

## 📡 API Reference

### WeexClient Methods

```python
from weex_client import WeexClient

client = WeexClient()

# Market Data
client.get_ticker("cmt_btcusdt")       # Current price
client.get_candles(symbol, "5m", 50)   # Candlestick data
client.get_orderbook("cmt_btcusdt")    # Order book

# Account
client.get_account_assets()             # Balance and equity
client.get_positions()                  # Open positions
client.get_open_orders()                # Pending orders

# Trading
client.place_order(
    symbol="cmt_btcusdt",
    side="buy",                         # buy/sell
    order_type="limit",                 # limit/market
    size=0.001,
    price=95000,
    leverage=5
)

client.cancel_order(order_id, symbol)   # Cancel single order
client.cancel_all_orders(symbol)        # Cancel all orders

# Connectivity
client.test_connectivity()              # Test API connection
```

---

## Running the Bot

### Quick Start

```bash
# 1. Test connectivity
python main.py

# 2. Check positions
python check_positions.py

# 3. Run dashboard (monitoring)
python dashboard.py

# 4. Run a strategy
python run_grid_bot.py    # Grid Trading
python run_peak_hunter.py # Peak Hunter
```

### Production Mode

```bash
# Run with logging
python run_grid_bot.py >> bot.log 2>&1

# Run in background (Linux)
nohup python run_grid_bot.py &
```

---

## 📊 Dashboard

The live dashboard provides real-time monitoring of:

- 💰 Account balance and equity
- 📈 Current prices and 24h changes
- 📋 Open positions and orders
- 🎯 Peak Hunter signals
- 💹 P&L tracking

```bash
python dashboard.py
```

**Dashboard Output:**
```
╔══════════════════════════════════════════════════════════════╗
║              📊 WEEX TRADING DASHBOARD                       ║
╠══════════════════════════════════════════════════════════════╣
║  💰 Balance: $1,000.00 USDT                                  ║
║  📈 BTC: $95,142.90 (+2.3%)                                  ║
║  📊 Open Positions: 0                                         ║
║  📋 Pending Orders: 0                                         ║
╚══════════════════════════════════════════════════════════════╝
```

---

## ⚠️ Risk Management

### Built-in Safety Features

| Feature | Default | Description |
|---------|---------|-------------|
| Max Position Size | $100 | Maximum per single position |
| Max Total Exposure | $500 | Maximum across all positions |
| Max Leverage | 5x | Maximum leverage allowed |
| Daily Loss Limit | $50 | Stop trading if exceeded |
| Max Daily Trades | 50 | Prevent overtrading |
| Default Stop Loss | 2% | Automatic SL on positions |
| Default Take Profit | 3% | Automatic TP on positions |

### Best Practices

1. **Start Small**: Test with minimum position sizes first
2. **Monitor Closely**: Use the dashboard during initial runs
3. **Check Logs**: Review trade history regularly
4. **Adjust Limits**: Tune risk parameters based on performance

---

## 🐳 Deployment

### Docker

```bash
# Build image
docker build -t protocol-14-weex .

# Run container
docker run -d --env-file .env protocol-14-weex
```

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
fly deploy

# Set secrets
fly secrets set WEEX_API_KEY=xxx WEEX_SECRET_KEY=xxx WEEX_PASSPHRASE=xxx
```

---

## 🔧 Troubleshooting

### Error 521: IP Not Whitelisted

```
❌ ERROR 521: IP NOT WHITELISTED!
```

**Solution:**
1. Run `python check_ip.py` to see your current IP
2. Add the IP to your WEEX API whitelist
3. Wait 5-10 minutes for propagation
4. Try again

### Error 403: Invalid Signature

```
❌ Error 403: Signature verification failed
```

**Solution:**
1. Verify API Key, Secret, and Passphrase in `.env`
2. Ensure no extra spaces or line breaks
3. Check that system time is synchronized

### Module Not Found

```
ModuleNotFoundError: No module named 'xxx'
```

**Solution:**
```bash
pip install -r requirements.txt
```

### Connection Timeout

```
❌ Connection timeout
```

**Solution:**
1. Check internet connection
2. Try a VPN if WEEX is blocked in your region
3. Verify API endpoint is correct

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**This software is for educational purposes only. Cryptocurrency trading involves substantial risk of loss. Never trade with money you cannot afford to lose. The authors are not responsible for any financial losses incurred from using this software.**

---

<p align="center">
  <b>Protocol-14 for WEEX AI Trading Hackathon 2026</b>
</p>
