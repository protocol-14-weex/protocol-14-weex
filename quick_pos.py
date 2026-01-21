#!/usr/bin/env python3
"""Quick position check"""
import os
import time
import hmac
import hashlib
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('WEEX_API_KEY')
SECRET_KEY = os.getenv('WEEX_SECRET_KEY')
PASSPHRASE = os.getenv('WEEX_PASSPHRASE')
BASE_URL = 'https://api-contract.weex.com'

def sign(method, path, query=''):
    ts = str(int(time.time() * 1000))
    msg = ts + method + path + query
    sig = base64.b64encode(hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()).decode()
    return ts, sig

def headers(ts, sig):
    return {'ACCESS-KEY': API_KEY, 'ACCESS-SIGN': sig, 'ACCESS-TIMESTAMP': ts, 'ACCESS-PASSPHRASE': PASSPHRASE, 'Content-Type': 'application/json'}

# Get all positions using allPosition endpoint
path = '/capi/v2/position/allPosition'
query = '?productType=umcbl&marginCoin=USDT'
ts, sig = sign('GET', path, query)
resp = requests.get(f'{BASE_URL}{path}{query}', headers=headers(ts, sig), timeout=10)

print("=== ALL POSITIONS (v2/allPosition) ===")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:1000] if resp.text else 'empty'}")

# Also try getting open orders
symbols = ['cmt_dogeusdt', 'cmt_btcusdt', 'cmt_ethusdt']
print("\n=== PENDING ORDERS ===")
for symbol in symbols:
    path = '/capi/v2/order/pending'
    query = f'?symbol={symbol}&marginCoin=USDT'
    ts, sig = sign('GET', path, query)
    resp = requests.get(f'{BASE_URL}{path}{query}', headers=headers(ts, sig), timeout=10)
    if resp.status_code == 200 and resp.text:
        data = resp.json()
        if data and len(data) > 0:
            print(f"{symbol}: {len(data)} pending orders")
            for o in data[:3]:
                print(f"  - {o.get('side', '?')} size={o.get('size', 0)} price={o.get('price', 0)}")
    else:
        print(f"{symbol}: No pending orders")

# Get account info
path = '/capi/v2/account/accounts'
query = '?productType=umcbl'
ts, sig = sign('GET', path, query)
resp = requests.get(f'{BASE_URL}{path}{query}', headers=headers(ts, sig), timeout=10)
print("\n=== ACCOUNT ===")
if resp.status_code == 200:
    for acc in resp.json():
        if acc.get('marginCoin') == 'USDT':
            print(f"Equity: ${float(acc.get('usdtEquity', 0)):.2f}")
            print(f"Available: ${float(acc.get('available', 0)):.2f}")
            print(f"Frozen: ${float(acc.get('frozen', 0)):.2f}")
            print(f"Unrealized: ${float(acc.get('unrealizedPL', 0)):.2f}")
            print(f"Cross Max Available: ${float(acc.get('crossMaxAvailable', 0)):.2f}")
