"""
📊 WEEX Hackathon - Live Dashboard
Monitor your trading bot in real-time
"""

import os
import sys
import time
import json
import hmac
import hashlib
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# API Config
API_KEY = os.getenv("WEEX_API_KEY")
SECRET_KEY = os.getenv("WEEX_SECRET_KEY")
PASSPHRASE = os.getenv("WEEX_PASSPHRASE")
BASE_URL = "https://api-contract.weex.com"

# Starting balance for hackathon
STARTING_BALANCE = 1000.0


def sign_request(method, path, query="", body=""):
    """Sign API request"""
    ts = str(int(time.time() * 1000))
    msg = ts + method + path + query + body
    sig = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    return ts, sig


def get_headers(ts, sig):
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sig,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }


def get_balance():
    """Get current USDT balance"""
    path = "/capi/v2/account/assets"
    ts, sig = sign_request("GET", path)
    resp = requests.get(f"{BASE_URL}{path}", headers=get_headers(ts, sig), timeout=10)
    data = resp.json()
    
    if isinstance(data, list):
        for asset in data:
            if asset.get('coinName') == 'USDT':
                return {
                    'available': float(asset.get('available', 0)),
                    'equity': float(asset.get('equity', 0)),
                    'frozen': float(asset.get('frozen', 0))
                }
    return {'available': 0, 'equity': 0, 'frozen': 0}


def get_price(symbol="cmt_btcusdt"):
    """Get current price"""
    resp = requests.get(f"{BASE_URL}/capi/v2/market/ticker?symbol={symbol}", timeout=10)
    data = resp.json()
    return {
        'price': float(data.get('last', 0)),
        'high_24h': float(data.get('high_24h', 0)),
        'low_24h': float(data.get('low_24h', 0)),
        'change_24h': float(data.get('change_24h', 0)) if data.get('change_24h') else 0
    }


def get_open_orders(symbol="cmt_btcusdt"):
    """Get open orders"""
    path = "/capi/v2/order/current"
    query = f"?symbol={symbol}"
    ts, sig = sign_request("GET", path, query)
    resp = requests.get(f"{BASE_URL}{path}{query}", headers=get_headers(ts, sig), timeout=10)
    data = resp.json()
    return data if isinstance(data, list) else []


def get_positions(symbol="cmt_btcusdt"):
    """Get open positions"""
    try:
        path = "/capi/v2/position/singlePosition"
        query = f"?symbol={symbol}&marginCoin=USDT"
        ts, sig = sign_request("GET", path, query)
        resp = requests.get(f"{BASE_URL}{path}{query}", headers=get_headers(ts, sig), timeout=10)
        if resp.text:
            return resp.json()
        return []
    except:
        return []


def get_trade_history(symbol="cmt_btcusdt"):
    """Get recent trades"""
    path = "/capi/v2/order/history"
    query = f"?symbol={symbol}&pageSize=10"
    ts, sig = sign_request("GET", path, query)
    resp = requests.get(f"{BASE_URL}{path}{query}", headers=get_headers(ts, sig), timeout=10)
    data = resp.json()
    
    if isinstance(data, dict) and 'list' in data:
        return data['list']
    return data if isinstance(data, list) else []


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_dashboard():
    """Display the dashboard"""
    clear_screen()
    
    # Get all data
    balance = get_balance()
    btc = get_price("cmt_btcusdt")
    orders = get_open_orders()
    positions = get_positions()
    trades = get_trade_history()
    
    # Calculate P&L
    pnl = balance['equity'] - STARTING_BALANCE
    pnl_percent = (pnl / STARTING_BALANCE) * 100
    
    # Header
    print("\n" + "═"*70)
    print("  📊 WEEX HACKATHON DASHBOARD - LIVE MONITORING")
    print("═"*70)
    print(f"  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═"*70)
    
    # Balance Section
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│                        💰 ACCOUNT                               │")
    print("├─────────────────────────────────────────────────────────────────┤")
    
    equity_str = f"${balance['equity']:,.2f}"
    available_str = f"${balance['available']:,.2f}"
    frozen_str = f"${balance['frozen']:,.2f}"
    
    pnl_emoji = "📈" if pnl >= 0 else "📉"
    pnl_color = "+" if pnl >= 0 else ""
    
    print(f"│  Equity:     {equity_str:>15}                               │")
    print(f"│  Available:  {available_str:>15}                               │")
    print(f"│  Frozen:     {frozen_str:>15}                               │")
    print(f"│                                                                 │")
    print(f"│  {pnl_emoji} P&L:       {pnl_color}${pnl:,.2f} ({pnl_color}{pnl_percent:.2f}%)                        │")
    print("└─────────────────────────────────────────────────────────────────┘")
    
    # Market Section
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│                        📈 BTC/USDT                              │")
    print("├─────────────────────────────────────────────────────────────────┤")
    print(f"│  Price:      ${btc['price']:>12,.2f}                              │")
    print(f"│  24h High:   ${btc['high_24h']:>12,.2f}                              │")
    print(f"│  24h Low:    ${btc['low_24h']:>12,.2f}                              │")
    print("└─────────────────────────────────────────────────────────────────┘")
    
    # Orders Section
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print(f"│                    📋 OPEN ORDERS ({len(orders)})                          │")
    print("├─────────────────────────────────────────────────────────────────┤")
    
    if orders:
        # Group by type
        buys = [o for o in orders if 'long' in o.get('type', '').lower()]
        sells = [o for o in orders if 'short' in o.get('type', '').lower()]
        
        print(f"│  Buy Orders:  {len(buys)}                                              │")
        for o in buys[:3]:
            price = float(o.get('price', 0))
            size = o.get('size', '0')
            print(f"│    🟢 ${price:,.2f} x {size} BTC                                 │")
        
        print(f"│                                                                 │")
        print(f"│  Sell Orders: {len(sells)}                                             │")
        for o in sells[:3]:
            price = float(o.get('price', 0))
            size = o.get('size', '0')
            print(f"│    🔴 ${price:,.2f} x {size} BTC                                 │")
    else:
        print("│  No open orders                                                 │")
    
    print("└─────────────────────────────────────────────────────────────────┘")
    
    # Positions Section
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│                      📊 POSITIONS                               │")
    print("├─────────────────────────────────────────────────────────────────┤")
    
    if isinstance(positions, list) and positions:
        for pos in positions:
            side = pos.get('holdSide', 'N/A')
            size = pos.get('total', '0')
            entry = float(pos.get('averageOpenPrice', 0))
            pnl_pos = float(pos.get('unrealizedPL', 0))
            print(f"│  {side.upper():>6}: {size} @ ${entry:,.2f}  P&L: ${pnl_pos:+,.2f}        │")
    else:
        print("│  No open positions                                              │")
    
    print("└─────────────────────────────────────────────────────────────────┘")
    
    # Recent Trades
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│                    📜 RECENT TRADES                             │")
    print("├─────────────────────────────────────────────────────────────────┤")
    
    if trades:
        for trade in trades[:5]:
            order_type = trade.get('type', 'N/A')
            price = float(trade.get('price_avg', 0) or trade.get('price', 0))
            size = trade.get('filled_qty', trade.get('size', '0'))
            status = trade.get('status', 'N/A')
            emoji = "🟢" if 'long' in order_type.lower() else "🔴"
            print(f"│  {emoji} {order_type[:12]:<12} ${price:>10,.2f} x {str(size):<8} {status:<8} │")
    else:
        print("│  No recent trades                                               │")
    
    print("└─────────────────────────────────────────────────────────────────┘")
    
    # Competition Status
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│                    🏆 COMPETITION STATUS                        │")
    print("├─────────────────────────────────────────────────────────────────┤")
    
    if balance['equity'] >= 2000:
        status = "🥇 TOP PERFORMER - On track to win!"
    elif balance['equity'] >= 1500:
        status = "🥈 DOING GREAT - Strong position!"
    elif balance['equity'] >= 1000:
        status = "⚖️  STABLE - Breaking even"
    elif balance['equity'] >= 500:
        status = "⚠️  CAUTION - Need recovery"
    else:
        status = "🚨 DANGER - High risk zone"
    
    print(f"│  {status:<60} │")
    print(f"│                                                                 │")
    print(f"│  Target: $2,000+ to compete with leaders                        │")
    print(f"│  Current: ${balance['equity']:,.2f} ({pnl_percent:+.1f}% from start)                     │")
    print("└─────────────────────────────────────────────────────────────────┘")
    
    print("\n  Press Ctrl+C to exit | Refreshing every 30 seconds...")


def run_dashboard(refresh_interval=30):
    """Run dashboard in loop"""
    print("🚀 Starting Live Dashboard...")
    
    try:
        while True:
            try:
                display_dashboard()
                time.sleep(refresh_interval)
            except requests.exceptions.RequestException as e:
                print(f"\n❌ Connection error: {e}")
                print("Retrying in 10 seconds...")
                time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard stopped. Good luck with the hackathon!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='WEEX Trading Dashboard')
    parser.add_argument('--refresh', type=int, default=30, help='Refresh interval in seconds')
    parser.add_argument('--once', action='store_true', help='Display once and exit')
    
    args = parser.parse_args()
    
    if args.once:
        display_dashboard()
    else:
        run_dashboard(args.refresh)
