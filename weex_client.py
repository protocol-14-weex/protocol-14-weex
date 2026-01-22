"""
WEEX API Client for AI Trading Hackathon
Implements secure authentication with HMAC SHA256 signature
Based on official WEEX API documentation
"""

import os
import time
import hmac
import hashlib
import base64
import json
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv


class WeexClient:
    """
    WEEX Exchange API Client for Futures Trading
    Supports REST API with HMAC SHA256 authentication
    """
    
    # WEEX API Base URL for Contract Trading
    BASE_URL = "https://api-contract.weex.com"
    
    def __init__(self, api_key: str = None, secret_key: str = None, passphrase: str = None):
        """
        Initialize WEEX Client with API credentials
        
        Args:
            api_key: WEEX API Key (loads from .env if not provided)
            secret_key: WEEX Secret Key (loads from .env if not provided)
            passphrase: WEEX Passphrase (loads from .env if not provided)
        """
        # Load environment variables
        load_dotenv()
        
        self.api_key = api_key or os.getenv("WEEX_API_KEY")
        self.secret_key = secret_key or os.getenv("WEEX_SECRET_KEY")
        self.passphrase = passphrase or os.getenv("WEEX_PASSPHRASE")
        
        # Validate credentials
        if not all([self.api_key, self.secret_key, self.passphrase]):
            raise ValueError(
                "Missing API credentials. Please set WEEX_API_KEY, "
                "WEEX_SECRET_KEY, and WEEX_PASSPHRASE in your .env file"
            )
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "locale": "en-US",
            "User-Agent": "WEEX-Hackathon-Bot/1.0",
        })
        
        print("✅ WeexClient initialized successfully")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in milliseconds"""
        return str(int(time.time() * 1000))
    
    def _generate_signature(self, timestamp: str, method: str, 
                           request_path: str, query_string: str = "", 
                           body: str = "") -> str:
        """
        Generate HMAC SHA256 signature for API authentication
        
        For GET: signature = Base64(HMAC_SHA256(timestamp + method + requestPath + queryString, secretKey))
        For POST: signature = Base64(HMAC_SHA256(timestamp + method + requestPath + queryString + body, secretKey))
        
        Args:
            timestamp: Current timestamp in milliseconds
            method: HTTP method (GET, POST, DELETE)
            request_path: API endpoint path (e.g., /capi/v2/account/assets)
            query_string: Query string for GET requests (e.g., ?symbol=xxx)
            body: Request body for POST requests
            
        Returns:
            Base64 encoded signature string
        """
        # Build the prehash string based on method
        if method.upper() == "GET":
            prehash_string = timestamp + method.upper() + request_path + query_string
        else:
            prehash_string = timestamp + method.upper() + request_path + query_string + body
        
        # Create HMAC SHA256 signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            prehash_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Return Base64 encoded signature
        return base64.b64encode(signature).decode('utf-8')
    
    def _request(self, method: str, endpoint: str, params: Dict = None, 
                 data: Dict = None) -> Dict[str, Any]:
        """
        Make authenticated request to WEEX API
        
        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., /capi/v2/account/assets)
            params: Query parameters for GET requests
            data: Request body data for POST requests
            
        Returns:
            JSON response from API
        """
        timestamp = self._get_timestamp()
        
        # Build query string for GET requests
        query_string = ""
        if params:
            query_string = "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        # Body for POST requests
        body = ""
        if data:
            body = json.dumps(data)
        
        # Generate signature
        signature = self._generate_signature(
            timestamp, method, endpoint, query_string, body
        )
        
        # Build headers
        headers = {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "locale": "en-US",
        }
        
        # Build URL
        url = f"{self.BASE_URL}{endpoint}{query_string}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, data=body, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Try to parse JSON response
            try:
                result = response.json()
            except json.JSONDecodeError:
                result = {"raw": response.text, "status_code": response.status_code, "error": "Invalid JSON response"}
            except Exception as e:
                result = {"raw": response.text, "status_code": response.status_code, "error": str(e)}
            
            # Check for API errors
            if response.status_code != 200:
                print(f"❌ API Error [{response.status_code}]: {result}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise
    
    # ==================== PUBLIC ENDPOINTS ====================
    
    def get_server_time(self) -> Dict[str, Any]:
        """
        Get server time (public endpoint - no auth required)
        
        Returns:
            Server time response
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/capi/v2/time",
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get server time: {e}")
            raise
    
    def get_ticker(self, symbol: str = "cmt_btcusdt") -> Dict[str, Any]:
        """
        Get ticker information for a symbol (public endpoint)
        
        Args:
            symbol: Trading pair symbol (e.g., "cmt_btcusdt")
            
        Returns:
            Ticker data with price info
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/capi/v2/market/ticker?symbol={symbol}",
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get ticker: {e}")
            raise
    
    def get_candles(self, symbol: str = "cmt_btcusdt", granularity: str = "1m", limit: int = 100) -> Dict[str, Any]:
        """
        Get candlestick/kline data (public endpoint)
        
        Args:
            symbol: Trading pair (e.g., "cmt_btcusdt")
            granularity: Candle interval (1m, 5m, 15m, 30m, 1H, 4H, 1D, 1W)
            limit: Number of candles (max 1000)
            
        Returns:
            Candlestick data with [timestamp, open, high, low, close, volume]
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/capi/v2/market/candles",
                params={
                    "symbol": symbol,
                    "granularity": granularity,
                    "limit": limit
                },
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get candles: {e}")
            raise
    
    def get_contracts(self) -> Dict[str, Any]:
        """
        Get available contracts/trading pairs (public endpoint)
        
        Returns:
            List of available contracts
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/capi/v2/market/contracts",
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get contracts: {e}")
            raise
    
    # ==================== PRIVATE ENDPOINTS ====================
    
    def get_account_assets(self) -> Dict[str, Any]:
        """
        Get account assets/balance (private endpoint)
        
        Returns:
            Account assets information with available, frozen, equity
        """
        return self._request("GET", "/capi/v2/account/assets")
    
    def get_single_account(self, symbol: str = "cmt_btcusdt", 
                           margin_coin: str = "USDT") -> Dict[str, Any]:
        """
        Get single account information
        
        Args:
            symbol: Trading pair symbol
            margin_coin: Margin coin (USDT)
            
        Returns:
            Single account info
        """
        return self._request("GET", "/capi/v2/account/singleAccount", {
            "symbol": symbol,
            "marginCoin": margin_coin
        })
    
    def get_positions(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get current open positions
        
        Args:
            symbol: Trading pair (optional, all if not specified)
            
        Returns:
            List of open positions
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/capi/v2/position/singlePosition", params)
    
    def get_all_positions(self) -> Dict[str, Any]:
        """
        Get all positions
        
        Returns:
            All positions
        """
        return self._request("GET", "/capi/v2/position/allPosition")
    
    def set_leverage(self, symbol: str, leverage: int, 
                     margin_coin: str = "USDT") -> Dict[str, Any]:
        """
        Set leverage for a trading pair
        
        Args:
            symbol: Trading pair symbol (e.g., "cmt_btcusdt")
            leverage: Leverage multiplier (1-125)
            margin_coin: Margin coin
            
        Returns:
            Leverage setting response
        """
        return self._request("POST", "/capi/v2/account/setLeverage", data={
            "symbol": symbol,
            "marginCoin": margin_coin,
            "leverage": str(leverage)
        })
    
    def place_order(self, symbol: str, side: str, order_type: str,
                    size: str, price: str = None, 
                    margin_coin: str = "USDT",
                    trade_side: str = "open",
                    client_oid: str = None) -> Dict[str, Any]:
        """
        Place a new order
        
        Args:
            symbol: Trading pair (e.g., "cmt_btcusdt")
            side: Order side ("open_long", "open_short", "close_long", "close_short")
                  or simple ("buy", "sell") with trade_side
            order_type: Order type ("limit" or "market")
            size: Order size/quantity
            price: Order price (required for limit orders)
            margin_coin: Margin coin
            trade_side: "open" for opening position, "close" for closing
            client_oid: Client order ID (optional)
            
        Returns:
            Order response with order ID
        """
        import uuid
        import time
        
        # Generar client_oid si no se proporciona (requerido por WEEX)
        if not client_oid:
            client_oid = f"scalper_{int(time.time())}"
        
        # Mapear side a type numérico
        # 1 = open_long, 2 = open_short, 3 = close_long, 4 = close_short
        type_map = {
            'open_long': '1',
            'open_short': '2', 
            'close_long': '3',
            'close_short': '4',
        }
        order_type_num = type_map.get(side, '1')
        
        order_data = {
            "symbol": symbol,
            "client_oid": client_oid,
            "size": size,
            "type": order_type_num,
            "order_type": "0",     # Normal order
            "match_price": "1",    # Market order (1 = use market price)
        }
        
        return self._request("POST", "/capi/v2/order/placeOrder", data=order_data)
    
    def cancel_order(self, symbol: str, order_id: str = None,
                     client_oid: str = None,
                     margin_coin: str = "USDT") -> Dict[str, Any]:
        """
        Cancel an existing order
        
        Args:
            symbol: Trading pair
            order_id: Order ID to cancel
            client_oid: Client order ID (alternative to order_id)
            margin_coin: Margin coin
            
        Returns:
            Cancellation response
        """
        cancel_data = {
            "symbol": symbol,
            "marginCoin": margin_coin,
        }
        
        if order_id:
            cancel_data["orderId"] = order_id
        if client_oid:
            cancel_data["clientOid"] = client_oid
        
        return self._request("POST", "/capi/v2/order/cancel_order", data=cancel_data)
    
    def cancel_all_orders(self, symbol: str, 
                          margin_coin: str = "USDT") -> Dict[str, Any]:
        """
        Cancel all open orders for a symbol
        
        Args:
            symbol: Trading pair
            margin_coin: Margin coin
            
        Returns:
            Cancellation response
        """
        return self._request("POST", "/capi/v2/order/cancel_all_order", data={
            "symbol": symbol,
            "marginCoin": margin_coin,
        })
    
    def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get all open/pending orders
        
        Args:
            symbol: Trading pair (optional)
            
        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/capi/v2/order/current", params)
    
    def get_order_detail(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order details
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            
        Returns:
            Order details
        """
        return self._request("GET", "/capi/v2/order/detail", {
            "symbol": symbol,
            "orderId": order_id
        })
    
    def get_order_history(self, symbol: str, 
                          start_time: int = None,
                          end_time: int = None,
                          page_size: int = 20) -> Dict[str, Any]:
        """
        Get order history
        
        Args:
            symbol: Trading pair
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)
            page_size: Number of records
            
        Returns:
            Order history
        """
        params = {"symbol": symbol, "pageSize": page_size}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return self._request("GET", "/capi/v2/order/history", params)
    
    def get_trade_fills(self, symbol: str,
                        start_time: int = None,
                        end_time: int = None) -> Dict[str, Any]:
        """
        Get trade fill details
        
        Args:
            symbol: Trading pair
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)
            
        Returns:
            Trade fill records
        """
        params = {"symbol": symbol}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return self._request("GET", "/capi/v2/order/fills", params)
    
    # ==================== CONNECTIVITY TEST ====================
    
    def test_connectivity(self) -> bool:
        """
        Test API connectivity and authentication
        
        Performs multiple checks:
        1. Server time (public endpoint)
        2. Ticker price (public endpoint)
        3. Account balance (private endpoint - validates auth)
        
        Returns:
            True if all tests pass, False otherwise
        """
        print("\n" + "="*60)
        print("🔍 WEEX API CONNECTIVITY TEST")
        print("="*60)
        
        # Test 1: Server connectivity with ticker
        print("\n📡 Test 1: Market Ticker (Public Endpoint)")
        try:
            ticker = self.get_ticker("cmt_btcusdt")
            if ticker:
                print(f"   ✅ BTC/USDT Price: ${ticker.get('last', 'N/A')}")
                print(f"   📊 24h High: ${ticker.get('high_24h', 'N/A')}")
                print(f"   📊 24h Low: ${ticker.get('low_24h', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
        
        # Test 2: Account Assets (Private - Auth Required)
        print("\n🔐 Test 2: Account Assets (Private Endpoint)")
        try:
            assets = self.get_account_assets()
            if isinstance(assets, list) and len(assets) > 0:
                print(f"   ✅ Authentication Successful!")
                for asset in assets:
                    coin = asset.get('coinName', 'N/A')
                    available = asset.get('available', '0')
                    equity = asset.get('equity', '0')
                    print(f"   💰 {coin}: Available={available}, Equity={equity}")
            elif isinstance(assets, dict) and 'code' in assets:
                print(f"   ⚠️ API Response: {assets}")
                if assets.get('code') == '00000':
                    print(f"   ✅ Authentication Successful!")
            else:
                print(f"   ✅ Response: {assets}")
        except Exception as e:
            print(f"   ❌ Authentication Failed: {e}")
            return False
        
        # Test 3: Get Available Contracts
        print("\n📈 Test 3: Available Contracts")
        try:
            contracts = self.get_contracts()
            if isinstance(contracts, list):
                symbols = [c.get('symbol', 'N/A') for c in contracts[:5]]
                print(f"   ✅ Found {len(contracts)} contracts")
                print(f"   📋 Sample: {symbols}")
            elif isinstance(contracts, dict) and contracts.get('data'):
                data = contracts['data']
                if isinstance(data, list):
                    symbols = [c.get('symbol', 'N/A') for c in data[:5]]
                    print(f"   ✅ Found {len(data)} contracts")
                    print(f"   📋 Sample: {symbols}")
        except Exception as e:
            print(f"   ⚠️ Warning: {e}")
        
        print("\n" + "="*60)
        print("✅ ALL CONNECTIVITY TESTS PASSED!")
        print("="*60 + "\n")
        
        return True


# Alias for convenience
Client = WeexClient
