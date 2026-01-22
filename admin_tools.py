#!/usr/bin/env python3
"""
🛠️ ADMIN TOOLS
Consolidated tools for managing Weex account.
Includes:
- Check Status: Positions, Balance, Open Orders
- Cancel All Orders: Cancel pending orders for all symbols
- Close All Positions: Panic button to close everything
"""

import sys
import time
import argparse
from typing import List
from weex_client import WeexClient

# List of symbols to manage
SYMBOLS = [
    'cmt_btcusdt', 'cmt_ethusdt', 'cmt_solusdt', 'cmt_bnbusdt', 
    'cmt_adausdt', 'cmt_dogeusdt', 'cmt_ltcusdt', 'cmt_xrpusdt', 
    'cmt_avaxusdt'
]

def check_status(client: WeexClient):
    """Print current account status"""
    print("\n" + "="*60)
    print("📊 ACCOUNT STATUS")
    print("="*60)
    
    # 1. Balance
    try:
        assets = client.get_account_assets()
        if isinstance(assets, list):
            found = False
            for a in assets:
                if a.get('coinName') == 'USDT':
                    found = True
                    equity = float(a.get('equity', 0))
                    available = float(a.get('available', 0))
                    unrealized = float(a.get('unrealizePnl', 0))
                    msg = f"   💰 USDT: Equity ${equity:,.2f} | Available ${available:,.2f}"
                    if unrealized != 0:
                        msg += f" | PnL ${unrealized:+.2f}"
                    print(msg)
            if not found:
                print("   💰 USDT: No assets found")
        else:
            print(f"   ❌ Error checking balance: {assets}")
    except Exception as e:
        print(f"   ❌ Balance Check Failed: {e}")

    # 2. Positions
    print("\n📍 POSITIONS:")
    positions_found = False
    try:
        # Check all symbols (Weex requires checking individually or getting all)
        # We try get_all_positions first if supported by client wrapper, else loop
        all_positions = client.get_all_positions()
        
        # Handle different response formats
        pos_list = []
        if isinstance(all_positions, list):
            pos_list = all_positions
        elif isinstance(all_positions, dict) and 'data' in all_positions:
            pos_list = all_positions['data']
            
        for pos in pos_list:
            size_str = pos.get('total', '0') # Some APIs return string
            size = float(size_str) if size_str else 0
            
            if size > 0:
                positions_found = True
                symbol = pos.get('symbol', 'unknown')
                side = pos.get('holdSide', 'unknown').upper()
                entry = float(pos.get('averageOpenPrice', 0))
                pnl = float(pos.get('unrealizedPL', 0))
                margin = float(pos.get('margin', 0))
                
                print(f"   • {symbol:12} {side:5} x{size:<8} Entry: ${entry:,.4f} | PnL: ${pnl:+.2f}")
    except Exception as e:
        print(f"   ⚠️ Error checking positions: {e}")
        
    if not positions_found:
        print("   (No open positions)")

    # 3. Open Orders
    print("\n📝 OPEN ORDERS (First 5 per symbol):")
    orders_found = False
    for symbol in SYMBOLS[:3]: # Check top 3 just for quick status, or user can request deep scan
        try:
            orders = client.get_open_orders(symbol)
            if isinstance(orders, dict) and 'data' in orders:
                orders = orders['data']
                
            if isinstance(orders, list) and len(orders) > 0:
                orders_found = True
                print(f"   {symbol}: {len(orders)} orders")
        except:
            pass
            
    if not orders_found:
        print("   (No open orders detected in top pairs)")
    print("="*60 + "\n")

def cancel_all(client: WeexClient):
    """Cancel all pending orders for all symbols"""
    print("\n" + "="*60)
    print("🗑️ CANCELING ALL ORDERS")
    print("="*60)
    
    for symbol in SYMBOLS:
        print(f"   Processing {symbol}...", end='\r')
        try:
            # 1. Cancel Regular Orders
            client.cancel_all_orders(symbol)
            
            # 2. Cancel Plan Orders (if separate endpoint needed)
            # The previous script used /capi/v2/order/cancelPlan
            # We add a raw request here since it's missing in client wrapper methods
            client._request("POST", "/capi/v2/order/cancelPlan", data={
                "symbol": symbol,
                "marginCoin": "USDT"
            })
            
            # 3. Cancel Trigger/STOP Orders
            # Previous script used /capi/v2/order/cancelAllTrigger
            client._request("POST", "/capi/v2/order/cancelAllTrigger", data={
                "symbol": symbol,
                "marginCoin": "USDT"
            })
            
        except Exception as e:
            print(f"   ❌ Error {symbol}: {e}")
            
    print("   ✅ Done.                               ")
    time.sleep(1)
    check_status(client)

def close_all(client: WeexClient):
    """Close all positions immediately"""
    print("\n" + "="*60)
    print("🔥 CLOSING ALL POSITIONS")
    print("="*60)
    
    # 1. Get all positions first
    positions_to_close = []
    try:
        all_positions = client.get_all_positions()
        pos_list = []
        if isinstance(all_positions, list):
            pos_list = all_positions
        elif isinstance(all_positions, dict) and 'data' in all_positions:
            pos_list = all_positions['data']
            
        for pos in pos_list:
            size = float(pos.get('total', 0))
            if size > 0:
                positions_to_close.append(pos)
                
    except Exception as e:
        print(f"   ❌ Error fetching positions: {e}")
        return

    if not positions_to_close:
        print("   ✅ No positions to close.")
        return

    # 2. Close them
    print(f"   Found {len(positions_to_close)} positions to close...")
    for pos in positions_to_close:
        symbol = pos.get('symbol')
        side = pos.get('holdSide') # 'long' or 'short' (usually lowercase from API)
        size = pos.get('total')
        
        # Map holdSide to close side
        # holdSide is usually 1=long, 2=short OR string 'long'/'short' depending on API version
        # WeexClient.place_order expects 'buy'/'sell' or 'close_long'/'close_short'
        
        # Safe mapping attempt
        close_side = ""
        if str(side).lower() == 'long':
            close_side = 'close_long'
        elif str(side).lower() == 'short':
            close_side = 'close_short'
        else:
            # Fallback if specific side unknown, try both? No, too risky. Skip.
            print(f"   ⚠️ Unknown side {side} for {symbol}, skipping.")
            continue
            
        print(f"   Closing {symbol} ({side})...")
        try:
            client.place_order(
                symbol=symbol,
                side=close_side,
                size=str(size),
                order_type='market',
                trade_side='close'
            )
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ Failed to close {symbol}: {e}")
            
    print("   ✅ Close sequence finished.")
    time.sleep(1)
    check_status(client)

def main():
    parser = argparse.ArgumentParser(description="Weex Admin Tools")
    parser.add_argument('--status', action='store_true', help="Check account status")
    parser.add_argument('--cancel', action='store_true', help="Cancel ALL orders")
    parser.add_argument('--close', action='store_true', help="Close ALL positions")
    parser.add_argument('--check', action='store_true', help="Alias for status")
    
    args = parser.parse_args()
    
    # Default to status if no args
    if not (args.cancel or args.close):
        args.status = True
        
    try:
        client = WeexClient()
        # Verify connection first
        client.get_server_time()
    except Exception as e:
        print(f"\n⚠️ WARNING: Issues connecting to Weex API. Check network/VPN/IP.")
        print(f"   Error: {e}")
        print("   Attempting to proceed anyway...")
        
    if args.cancel:
        cancel_all(client)
        
    if args.close:
        close_all(client)
        
    if args.status or args.check:
        check_status(client)

if __name__ == "__main__":
    main()
