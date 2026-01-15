"""Check positions"""
import os, time, hmac, hashlib, base64, requests
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
    return {'ACCESS-KEY': API_KEY, 'ACCESS-SIGN': sig, 'ACCESS-TIMESTAMP': ts, 'ACCESS-PASSPHRASE': PASSPHRASE}

symbols = ['cmt_solusdt', 'cmt_bnbusdt', 'cmt_btcusdt']

print("=== POSICIONES ABIERTAS ===")
for symbol in symbols:
    try:
        path = '/capi/v2/position/singlePosition'
        query = f'?symbol={symbol}&marginCoin=USDT'
        ts, sig = sign('GET', path, query)
        resp = requests.get(f'{BASE_URL}{path}{query}', headers=headers(ts, sig), timeout=10)
        
        if resp.text:
            data = resp.json()
        else:
            data = []
        
        coin = symbol.replace('cmt_', '').replace('usdt', '').upper()
        
        if isinstance(data, list):
            for pos in data:
                total = float(pos.get('total', 0))
                if total > 0:
                    side = pos.get('holdSide', '')
                    entry = pos.get('averageOpenPrice', 0)
                    pnl = pos.get('unrealizedPL', 0)
                    margin = pos.get('margin', 0)
                    liq = pos.get('liquidationPrice', 0)
                    print(f"{coin}: {side.upper()} x{total}")
                    print(f"    Entry: ${float(entry):,.4f}")
                    print(f"    P&L: ${float(pnl):+,.4f}")
                    print(f"    Margin: ${float(margin):,.2f}")
                    print(f"    Liquidation: ${float(liq):,.4f}")
                    print()
    except Exception as e:
        print(f"Error checking {symbol}: {e}")

# Check orders
print("\n=== ÓRDENES RECIENTES ===")
for symbol in ['cmt_solusdt', 'cmt_bnbusdt']:
    path = '/capi/v2/order/history'
    query = f'?symbol={symbol}&pageSize=3'
    ts, sig = sign('GET', path, query)
    resp = requests.get(f'{BASE_URL}{path}{query}', headers=headers(ts, sig), timeout=10)
    data = resp.json()
    coin = symbol.replace('cmt_', '').replace('usdt', '').upper()
    print(f"\n{coin}:")
    if isinstance(data, list):
        for o in data[:2]:
            print(f"  {o.get('type')} | Status: {o.get('status')} | Price: ${float(o.get('price_avg', 0)):,.4f} | Size: {o.get('size')}")

# Balance
print("\n=== BALANCE ===")
path = '/capi/v2/account/assets'
ts, sig = sign('GET', path)
resp = requests.get(f'{BASE_URL}{path}', headers=headers(ts, sig), timeout=10)
data = resp.json()
if isinstance(data, list):
    for a in data:
        if a.get('coinName') == 'USDT':
            print(f"Equity: ${float(a.get('equity', 0)):,.2f}")
            print(f"Available: ${float(a.get('available', 0)):,.2f}")
            print(f"Frozen: ${float(a.get('frozen', 0)):,.2f}")
