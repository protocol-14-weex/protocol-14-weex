"""
🤖 DeepSeek AI Sentiment Analysis
Analyzes crypto news and social sentiment for trading signals
"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    sentiment: str  # 'bullish', 'bearish', 'neutral'
    score: float    # -100 to 100
    confidence: float  # 0-100
    summary: str
    factors: List[str]
    timestamp: datetime


class DeepSeekSentiment:
    """
    DeepSeek AI Sentiment Analyzer
    
    Uses DeepSeek API to analyze:
    - Crypto news headlines
    - Market conditions
    - Trading recommendations
    """
    
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    def __init__(self, api_key: str = None):
        """
        Initialize DeepSeek client
        
        Args:
            api_key: DeepSeek API key (loads from .env if not provided)
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        if not self.api_key:
            print("⚠️ DeepSeek API key not found. Sentiment analysis disabled.")
            self.enabled = False
        else:
            self.enabled = True
            print("✅ DeepSeek AI initialized")
        
        # Cache for rate limiting
        self.last_call = None
        self.min_interval = 2  # Minimum seconds between calls
        self.cache: Dict[str, SentimentResult] = {}
        self.cache_ttl = 300  # 5 minutes cache
    
    def _call_api(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """
        Call DeepSeek API
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            
        Returns:
            AI response text or None on error
        """
        if not self.enabled:
            return None
        
        # Rate limiting
        import time
        if self.last_call:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.3,  # Lower for more consistent analysis
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            self.last_call = time.time()
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                print(f"❌ DeepSeek API error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ DeepSeek request failed: {e}")
            return None
    
    def analyze_market_sentiment(self, symbol: str = "BTC", 
                                 context: str = None) -> SentimentResult:
        """
        Analyze overall market sentiment for a crypto asset
        
        Args:
            symbol: Crypto symbol (BTC, ETH, etc.)
            context: Additional context (news, price action, etc.)
            
        Returns:
            SentimentResult with analysis
        """
        # Check cache
        cache_key = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        system_prompt = """You are a crypto market analyst AI. Analyze market sentiment and provide trading signals.
        
Your response MUST be valid JSON with this exact format:
{
    "sentiment": "bullish" | "bearish" | "neutral",
    "score": -100 to 100,
    "confidence": 0 to 100,
    "summary": "Brief 1-2 sentence summary",
    "factors": ["factor1", "factor2", "factor3"]
}

Be concise and data-driven. Consider technical and fundamental factors."""
        
        prompt = f"""Analyze the current market sentiment for {symbol}/USDT.

Current context:
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
- Market: Crypto futures trading
{f'- Additional info: {context}' if context else ''}

Provide your sentiment analysis in JSON format."""
        
        response = self._call_api(prompt, system_prompt)
        
        if response:
            try:
                # Parse JSON from response
                # Handle markdown code blocks
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0]
                
                data = json.loads(response.strip())
                
                result = SentimentResult(
                    sentiment=data.get('sentiment', 'neutral'),
                    score=float(data.get('score', 0)),
                    confidence=float(data.get('confidence', 50)),
                    summary=data.get('summary', 'Analysis unavailable'),
                    factors=data.get('factors', []),
                    timestamp=datetime.now()
                )
                
                # Cache result
                self.cache[cache_key] = result
                return result
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Failed to parse AI response: {e}")
                print(f"   Raw response: {response[:200]}")
        
        # Default neutral response
        return SentimentResult(
            sentiment="neutral",
            score=0,
            confidence=0,
            summary="Unable to analyze sentiment",
            factors=["API error or no data"],
            timestamp=datetime.now()
        )
    
    def analyze_trade_opportunity(self, symbol: str, current_price: float,
                                  rsi: float = None, macd_signal: str = None,
                                  trend: str = None) -> Dict[str, Any]:
        """
        Analyze if current conditions present a good trade opportunity
        
        Args:
            symbol: Trading pair
            current_price: Current price
            rsi: Current RSI value
            macd_signal: MACD signal (buy/sell/neutral)
            trend: Current trend
            
        Returns:
            Dict with recommendation
        """
        system_prompt = """You are a crypto trading assistant. Analyze the given market conditions and provide a trading recommendation.

Your response MUST be valid JSON:
{
    "action": "buy" | "sell" | "hold",
    "confidence": 0 to 100,
    "reason": "Brief explanation",
    "risk_level": "low" | "medium" | "high",
    "suggested_sl_percent": 1.0 to 5.0,
    "suggested_tp_percent": 1.0 to 10.0
}

Be conservative. When in doubt, recommend "hold"."""
        
        prompt = f"""Analyze this trading opportunity:

Symbol: {symbol}
Current Price: ${current_price:,.2f}
RSI: {rsi if rsi else 'N/A'}
MACD Signal: {macd_signal if macd_signal else 'N/A'}
Trend: {trend if trend else 'N/A'}

Should I enter a trade? Provide JSON recommendation."""
        
        response = self._call_api(prompt, system_prompt)
        
        if response:
            try:
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0]
                
                return json.loads(response.strip())
                
            except json.JSONDecodeError:
                pass
        
        # Default conservative response
        return {
            "action": "hold",
            "confidence": 0,
            "reason": "Unable to analyze - holding position",
            "risk_level": "high",
            "suggested_sl_percent": 2.0,
            "suggested_tp_percent": 3.0
        }
    
    def get_signal(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        Get a quick trading signal based on sentiment
        
        Args:
            symbol: Crypto symbol
            
        Returns:
            Dict with signal info
        """
        sentiment = self.analyze_market_sentiment(symbol)
        
        # Convert sentiment to trading signal
        if sentiment.sentiment == "bullish" and sentiment.confidence >= 60:
            signal = "buy"
        elif sentiment.sentiment == "bearish" and sentiment.confidence >= 60:
            signal = "sell"
        else:
            signal = "neutral"
        
        return {
            'signal': signal,
            'sentiment': sentiment.sentiment,
            'score': sentiment.score,
            'confidence': sentiment.confidence,
            'summary': sentiment.summary,
            'factors': sentiment.factors
        }


# Quick test
if __name__ == "__main__":
    print("\n🤖 Testing DeepSeek Sentiment Analysis")
    print("="*50)
    
    ai = DeepSeekSentiment()
    
    if ai.enabled:
        print("\n📊 Analyzing BTC sentiment...")
        result = ai.get_signal("BTC")
        
        print(f"\n🎯 Signal: {result['signal'].upper()}")
        print(f"📈 Sentiment: {result['sentiment']} (score: {result['score']})")
        print(f"💪 Confidence: {result['confidence']}%")
        print(f"📝 Summary: {result['summary']}")
        print(f"🔍 Factors: {', '.join(result['factors'])}")
    else:
        print("⚠️ DeepSeek API key not configured")
        print("   Add DEEPSEEK_API_KEY to your .env file")
