"""
Cancel all pending orders to free up margin
"""

import os
import time
import hmac
import hashlib
import base64
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WEEX_API_KEY")
SECRET_KEY = os.getenv("WEEX_SECRET_KEY")
PASSPHRASE = os.getenv("WEEX_PASSPHRASE")
BASE_URL = "https://api-contract.weex.com"


def timestamp():
    return str(int(time.time() * 1000))


def sign(ts, method, path, body=""):
    msg = ts + method + path + body
    sig = hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def headers(sig, ts):
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sig,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json",
        "locale": "en-US"
    }


def get_open_orders(symbol="cmt_btcusdt"):
    """Get all open orders"""
    path = "/capi/v2/order/current"
    query = f"?symbol={symbol}"
    ts = timestamp()
    sig = sign(ts, "GET", path, query)
    
    resp = requests.get(f"{BASE_URL}{path}{query}", headers=headers(sig, ts), timeout=30)
    return resp.json()


def cancel_order(symbol="cmt_btcusdt", order_id=None):
    """Cancel a single order"""
    path = "/capi/v2/order/cancel"
    ts = timestamp()
    body = json.dumps({"symbol": symbol, "orderId": str(order_id)})
    sig = sign(ts, "POST", path, body)
    
    resp = requests.post(f"{BASE_URL}{path}", headers=headers(sig, ts), data=body, timeout=30)
    return resp.json()


def cancel_all_orders(symbol="cmt_btcusdt"):
    """Cancel all orders for a symbol by iterating through them"""
    orders = get_open_orders(symbol)
    
    if not isinstance(orders, list) or len(orders) == 0:
        return {"msg": "No orders to cancel"}
    
    results = []
    for order in orders:
        # Try different order ID field names
        order_id = order.get('orderId') or order.get('order_id') or order.get('id')
        if order_id:
            result = cancel_order(symbol, order_id)
            results.append(result)
    
    return results


def main():
    print("\n" + "="*50)
    print("🗑️  CANCEL PENDING ORDERS")
    print("="*50)
    
    symbols = ["cmt_btcusdt", "cmt_ethusdt", "cmt_solusdt"]
    
    for symbol in symbols:
        print(f"\n📊 Checking {symbol}...")
        
        # Get open orders
        orders = get_open_orders(symbol)
        
        if isinstance(orders, list) and len(orders) > 0:
            print(f"   Found {len(orders)} open order(s)")
            for order in orders:
                print(f"      - Price: {order.get('price')}, Size: {order.get('size')}")
            
            # Cancel all
            print(f"   🗑️ Cancelling all orders for {symbol}...")
            result = cancel_all_orders(symbol)
            print(f"   Result: {result}")
        else:
            print(f"   ✅ No open orders")
    
    # Final check
    print("\n" + "="*50)
    print("📊 FINAL STATUS")
    print("="*50)
    
    for symbol in symbols:
        orders = get_open_orders(symbol)
        count = len(orders) if isinstance(orders, list) else 0
        status = "✅ Clear" if count == 0 else f"⚠️ {count} remaining"
        print(f"   {symbol}: {status}")
    
    print("\n✅ Done! Margin should be freed up now.\n")


if __name__ == "__main__":
    main()
