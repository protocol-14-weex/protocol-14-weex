"""
🦎 CoinGecko Market Intelligence
Detecta oportunidades usando datos de mercado globales

Features:
- Trending coins (memecoins antes de pump)
- Volumen global y cambios 24h
- Fear & Greed Index
- Top gainers/losers
"""

import os
import time
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


@dataclass
class MarketOpportunity:
    """Oportunidad de mercado detectada"""
    coin_id: str
    symbol: str
    name: str
    signal_type: str  # 'trending', 'volume_spike', 'momentum', 'reversal'
    strength: float   # 0-100
    price: float
    change_24h: float
    change_1h: float
    volume_24h: float
    volume_change: float
    market_cap_rank: int
    reason: str


class CoinGeckoIntel:
    """
    Market Intelligence usando CoinGecko API
    
    Detecta:
    - Trending coins (antes del pump)
    - Volume spikes (ballenas entrando)
    - Momentum extremo
    - Reversiones potenciales
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    PRO_URL = "https://pro-api.coingecko.com/api/v3"
    
    # Mapping CoinGecko ID -> WEEX symbol
    WEEX_MAPPING = {
        'bitcoin': 'cmt_btcusdt',
        'ethereum': 'cmt_ethusdt',
        'solana': 'cmt_solusdt',
        'binancecoin': 'cmt_bnbusdt',
        'dogecoin': 'cmt_dogeusdt',
        'cardano': 'cmt_adausdt',
        'ripple': 'cmt_xrpusdt',
        'litecoin': 'cmt_ltcusdt',
        'avalanche-2': 'cmt_avaxusdt',
        'polkadot': 'cmt_dotusdt',
        'chainlink': 'cmt_linkusdt',
        'near': 'cmt_nearusdt',
        'uniswap': 'cmt_uniusdt',
        'pepe': 'cmt_pepeusdt',
        'shiba-inu': 'cmt_shibusdt',
        'sui': 'cmt_suiusdt',
        'aptos': 'cmt_aptusdt',
        'arbitrum': 'cmt_arbusdt',
    }
    
    def __init__(self, api_key: str = None):
        """
        Initialize CoinGecko client
        
        Args:
            api_key: CoinGecko Pro API key (optional for basic usage)
        """
        self.api_key = api_key or os.getenv("COINGECKO_API_KEY", "CG-Eu1NbbK2sLt64PhW8TFY8Hor")
        self.session = requests.Session()
        
        # Cache to avoid rate limits
        self.cache = {}
        self.cache_ttl = 60  # 60 seconds cache
        
        # Rate limiting
        self.last_call = 0
        self.min_interval = 1.5  # 1.5 seconds between calls (free tier limit)
        
        if self.api_key:
            self.session.headers.update({
                'x-cg-pro-api-key': self.api_key,
                'accept': 'application/json'
            })
            self.base_url = self.PRO_URL
            self.min_interval = 0.5  # Pro tier is faster
            print("✅ CoinGecko Pro initialized")
        else:
            self.base_url = self.BASE_URL
            print("⚠️ CoinGecko Free tier (limited requests)")
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
    
    def _get_cached(self, key: str):
        """Get from cache if valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Store in cache"""
        self.cache[key] = (data, time.time())
    
    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with caching"""
        cache_key = f"{endpoint}:{str(params)}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        self._rate_limit()
        
        try:
            url = f"{self.base_url}{endpoint}"
            resp = self.session.get(url, params=params, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json()
                self._set_cache(cache_key, data)
                return data
            elif resp.status_code == 429:
                print("⚠️ CoinGecko rate limit hit, waiting...")
                time.sleep(30)
                return None
            else:
                print(f"❌ CoinGecko API error: {resp.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ CoinGecko request failed: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # MARKET DATA
    # ═══════════════════════════════════════════════════════════════
    
    def get_trending(self) -> List[Dict]:
        """
        Get trending coins (7 most searched)
        
        These coins often pump after trending!
        
        Returns:
            List of trending coins
        """
        data = self._request("/search/trending")
        if not data or 'coins' not in data:
            return []
        
        trending = []
        for item in data['coins'][:10]:
            coin = item.get('item', {})
            trending.append({
                'id': coin.get('id'),
                'symbol': coin.get('symbol', '').upper(),
                'name': coin.get('name'),
                'market_cap_rank': coin.get('market_cap_rank'),
                'price_btc': coin.get('price_btc'),
                'score': coin.get('score', 0),
            })
        
        return trending
    
    def get_global_market(self) -> Dict:
        """
        Get global market stats
        
        Returns:
            Dict with market cap, volume, BTC dominance, fear/greed
        """
        data = self._request("/global")
        if not data or 'data' not in data:
            return {}
        
        d = data['data']
        return {
            'total_market_cap_usd': d.get('total_market_cap', {}).get('usd', 0),
            'total_volume_24h': d.get('total_volume', {}).get('usd', 0),
            'btc_dominance': d.get('market_cap_percentage', {}).get('btc', 0),
            'eth_dominance': d.get('market_cap_percentage', {}).get('eth', 0),
            'market_cap_change_24h': d.get('market_cap_change_percentage_24h_usd', 0),
            'active_cryptocurrencies': d.get('active_cryptocurrencies', 0),
        }
    
    def get_fear_greed_index(self) -> Dict:
        """
        Get Fear & Greed Index from alternative.me
        
        0-24: Extreme Fear (potential buy)
        25-49: Fear
        50-74: Greed
        75-100: Extreme Greed (potential sell)
        """
        try:
            resp = requests.get(
                "https://api.alternative.me/fng/",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('data'):
                    fng = data['data'][0]
                    value = int(fng.get('value', 50))
                    return {
                        'value': value,
                        'classification': fng.get('value_classification', 'Neutral'),
                        'signal': 'buy' if value < 30 else ('sell' if value > 70 else 'neutral'),
                        'timestamp': fng.get('timestamp')
                    }
        except:
            pass
        
        return {'value': 50, 'classification': 'Neutral', 'signal': 'neutral'}
    
    def get_top_coins(self, limit: int = 50) -> List[Dict]:
        """
        Get top coins by market cap with full data
        
        Args:
            limit: Number of coins to fetch
            
        Returns:
            List of coins with price, volume, changes
        """
        data = self._request("/coins/markets", params={
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': 'false',
            'price_change_percentage': '1h,24h,7d'
        })
        
        if not data:
            return []
        
        return data
    
    def get_top_gainers_losers(self, limit: int = 20) -> Dict[str, List[Dict]]:
        """
        Get top gainers and losers in 24h
        
        Returns:
            Dict with 'gainers' and 'losers' lists
        """
        coins = self.get_top_coins(100)
        if not coins:
            return {'gainers': [], 'losers': []}
        
        # Filter coins available on WEEX
        weex_coins = [c for c in coins if c.get('id') in self.WEEX_MAPPING]
        
        # Sort by 24h change
        sorted_coins = sorted(weex_coins, key=lambda x: x.get('price_change_percentage_24h', 0) or 0, reverse=True)
        
        gainers = sorted_coins[:limit]
        losers = sorted_coins[-limit:][::-1]
        
        return {
            'gainers': gainers,
            'losers': losers
        }
    
    def get_volume_spikes(self, threshold: float = 2.0) -> List[Dict]:
        """
        Detect coins with abnormal volume (potential whale activity)
        
        Args:
            threshold: Volume multiplier vs average (2.0 = 2x normal volume)
            
        Returns:
            List of coins with volume spikes
        """
        coins = self.get_top_coins(100)
        if not coins:
            return []
        
        spikes = []
        for coin in coins:
            if coin.get('id') not in self.WEEX_MAPPING:
                continue
            
            # Calculate volume to market cap ratio
            volume = coin.get('total_volume', 0)
            market_cap = coin.get('market_cap', 1)
            
            if market_cap > 0:
                vol_ratio = volume / market_cap
                
                # High volume relative to market cap = unusual activity
                # Normal is about 0.02-0.05 (2-5%)
                if vol_ratio > 0.08:  # >8% is high
                    spikes.append({
                        'id': coin.get('id'),
                        'symbol': coin.get('symbol', '').upper(),
                        'name': coin.get('name'),
                        'price': coin.get('current_price'),
                        'volume_24h': volume,
                        'market_cap': market_cap,
                        'volume_ratio': vol_ratio,
                        'change_24h': coin.get('price_change_percentage_24h', 0),
                        'weex_symbol': self.WEEX_MAPPING.get(coin.get('id')),
                        'signal': 'high_activity'
                    })
        
        # Sort by volume ratio
        return sorted(spikes, key=lambda x: x['volume_ratio'], reverse=True)
    
    # ═══════════════════════════════════════════════════════════════
    # OPPORTUNITY DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def find_opportunities(self) -> List[MarketOpportunity]:
        """
        Comprehensive opportunity scanner
        
        Combines:
        - Trending coins
        - Volume spikes
        - Extreme movers (reversal candidates)
        - Fear/greed extremes
        
        Returns:
            List of MarketOpportunity sorted by strength
        """
        opportunities = []
        
        # 1. Check trending coins
        print("🔍 Scanning trending coins...")
        trending = self.get_trending()
        for coin in trending:
            if coin['id'] in self.WEEX_MAPPING:
                opportunities.append(MarketOpportunity(
                    coin_id=coin['id'],
                    symbol=coin['symbol'],
                    name=coin['name'],
                    signal_type='trending',
                    strength=70 + (10 - coin.get('score', 5)) * 3,  # Higher score for lower rank
                    price=0,  # Will be filled later
                    change_24h=0,
                    change_1h=0,
                    volume_24h=0,
                    volume_change=0,
                    market_cap_rank=coin.get('market_cap_rank', 999),
                    reason=f"🔥 Trending #{coin.get('score', 0)+1} - high search volume"
                ))
        
        # 2. Check top movers
        print("🔍 Scanning top gainers/losers...")
        movers = self.get_top_gainers_losers(10)
        
        # Gainers with extreme moves might reverse
        for coin in movers['gainers'][:5]:
            change = coin.get('price_change_percentage_24h', 0) or 0
            if change > 10:  # >10% up - potential short
                opportunities.append(MarketOpportunity(
                    coin_id=coin['id'],
                    symbol=coin['symbol'].upper(),
                    name=coin['name'],
                    signal_type='reversal',
                    strength=min(95, 50 + change * 2),
                    price=coin.get('current_price', 0),
                    change_24h=change,
                    change_1h=coin.get('price_change_percentage_1h_in_currency', 0) or 0,
                    volume_24h=coin.get('total_volume', 0),
                    volume_change=0,
                    market_cap_rank=coin.get('market_cap_rank', 999),
                    reason=f"📈 +{change:.1f}% en 24h - potencial SHORT (reversión)"
                ))
        
        # Losers might bounce
        for coin in movers['losers'][:5]:
            change = coin.get('price_change_percentage_24h', 0) or 0
            if change < -10:  # >10% down - potential long
                opportunities.append(MarketOpportunity(
                    coin_id=coin['id'],
                    symbol=coin['symbol'].upper(),
                    name=coin['name'],
                    signal_type='reversal',
                    strength=min(95, 50 + abs(change) * 2),
                    price=coin.get('current_price', 0),
                    change_24h=change,
                    change_1h=coin.get('price_change_percentage_1h_in_currency', 0) or 0,
                    volume_24h=coin.get('total_volume', 0),
                    volume_change=0,
                    market_cap_rank=coin.get('market_cap_rank', 999),
                    reason=f"📉 {change:.1f}% en 24h - potencial LONG (rebote)"
                ))
        
        # 3. Check volume spikes
        print("🔍 Scanning volume spikes (whale activity)...")
        spikes = self.get_volume_spikes()
        for coin in spikes[:5]:
            opportunities.append(MarketOpportunity(
                coin_id=coin['id'],
                symbol=coin['symbol'],
                name=coin['name'],
                signal_type='volume_spike',
                strength=min(90, 60 + coin['volume_ratio'] * 100),
                price=coin['price'],
                change_24h=coin['change_24h'],
                change_1h=0,
                volume_24h=coin['volume_24h'],
                volume_change=coin['volume_ratio'] * 100,
                market_cap_rank=999,
                reason=f"🐋 Volumen anormal: {coin['volume_ratio']*100:.1f}% del market cap"
            ))
        
        # 4. Check Fear & Greed
        fng = self.get_fear_greed_index()
        print(f"📊 Fear & Greed Index: {fng['value']} ({fng['classification']})")
        
        # Sort by strength
        opportunities.sort(key=lambda x: x.strength, reverse=True)
        
        return opportunities
    
    def get_weex_symbol(self, coingecko_id: str) -> Optional[str]:
        """Convert CoinGecko ID to WEEX symbol"""
        return self.WEEX_MAPPING.get(coingecko_id)
    
    def get_coin_signals(self, coin_id: str) -> Dict:
        """
        Get detailed signals for a specific coin
        
        Args:
            coin_id: CoinGecko coin ID
            
        Returns:
            Dict with all signals for the coin
        """
        data = self._request(f"/coins/{coin_id}", params={
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'true',
            'developer_data': 'false',
            'sparkline': 'false'
        })
        
        if not data:
            return {}
        
        market = data.get('market_data', {})
        
        # Calculate signals
        change_1h = market.get('price_change_percentage_1h_in_currency', {}).get('usd', 0) or 0
        change_24h = market.get('price_change_percentage_24h', 0) or 0
        change_7d = market.get('price_change_percentage_7d', 0) or 0
        
        # Determine trend
        if change_24h > 5 and change_1h > 0:
            trend = 'strong_bullish'
        elif change_24h > 0:
            trend = 'bullish'
        elif change_24h < -5 and change_1h < 0:
            trend = 'strong_bearish'
        elif change_24h < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        return {
            'coin_id': coin_id,
            'symbol': data.get('symbol', '').upper(),
            'name': data.get('name'),
            'current_price': market.get('current_price', {}).get('usd', 0),
            'change_1h': change_1h,
            'change_24h': change_24h,
            'change_7d': change_7d,
            'volume_24h': market.get('total_volume', {}).get('usd', 0),
            'market_cap': market.get('market_cap', {}).get('usd', 0),
            'ath': market.get('ath', {}).get('usd', 0),
            'ath_change': market.get('ath_change_percentage', {}).get('usd', 0),
            'trend': trend,
            'weex_symbol': self.WEEX_MAPPING.get(coin_id),
            'community_score': data.get('community_score', 0),
            'liquidity_score': data.get('liquidity_score', 0),
        }


# ═══════════════════════════════════════════════════════════════
# STANDALONE SCANNER
# ═══════════════════════════════════════════════════════════════

def main():
    """Run standalone market scanner"""
    print("="*60)
    print("🦎 COINGECKO MARKET INTELLIGENCE SCANNER")
    print("="*60)
    
    intel = CoinGeckoIntel()
    
    # Global market
    print("\n📊 GLOBAL MARKET:")
    global_data = intel.get_global_market()
    if global_data:
        print(f"   Total Market Cap: ${global_data['total_market_cap_usd']/1e9:.1f}B")
        print(f"   24h Volume: ${global_data['total_volume_24h']/1e9:.1f}B")
        print(f"   BTC Dominance: {global_data['btc_dominance']:.1f}%")
        print(f"   24h Change: {global_data['market_cap_change_24h']:.2f}%")
    
    # Fear & Greed
    print("\n😱 FEAR & GREED INDEX:")
    fng = intel.get_fear_greed_index()
    emoji = "😱" if fng['value'] < 30 else ("🤑" if fng['value'] > 70 else "😐")
    print(f"   {emoji} {fng['value']} - {fng['classification']}")
    print(f"   Signal: {fng['signal'].upper()}")
    
    # Find opportunities
    print("\n🎯 SCANNING OPPORTUNITIES...")
    opportunities = intel.find_opportunities()
    
    if opportunities:
        print(f"\n🔥 TOP {min(10, len(opportunities))} OPPORTUNITIES:")
        for i, opp in enumerate(opportunities[:10], 1):
            weex = intel.get_weex_symbol(opp.coin_id)
            weex_str = f" [{weex}]" if weex else " [NOT ON WEEX]"
            print(f"\n   {i}. {opp.symbol} ({opp.name}){weex_str}")
            print(f"      Type: {opp.signal_type} | Strength: {opp.strength:.0f}/100")
            print(f"      {opp.reason}")
            if opp.change_24h:
                print(f"      24h: {opp.change_24h:+.1f}%")
    else:
        print("   No significant opportunities found")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
