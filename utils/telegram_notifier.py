"""
📱 Telegram Notifications for Trading Bot

SETUP:
1. Open Telegram and search for @BotFather
2. Send /newbot and follow instructions
3. Copy the token (looks like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
4. Start a chat with your new bot
5. Get your chat ID by visiting: https://api.telegram.org/bot<TOKEN>/getUpdates
6. Add both to your .env file:
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class TelegramNotifier:
    """
    Send trading alerts via Telegram
    """
    
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)
        
        if self.enabled:
            print("✅ Telegram notifications enabled")
        else:
            print("⚠️ Telegram not configured (optional)")
    
    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message via Telegram
        
        Args:
            message: Message text (supports HTML formatting)
            parse_mode: "HTML" or "Markdown"
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Telegram error: {e}")
            return False
    
    # ==================== Pre-formatted Messages ====================
    
    def notify_grid_placed(self, symbol: str, buy_levels: list, sell_levels: list):
        """Notify when grid is placed"""
        msg = f"""
🎯 <b>GRID PLACED</b>

📊 Symbol: {symbol.upper()}
⏰ Time: {datetime.now().strftime('%H:%M:%S')}

🟢 <b>Buy Levels:</b>
{chr(10).join([f'  • ${p:,.2f}' for p in buy_levels])}

🔴 <b>Sell Levels:</b>
{chr(10).join([f'  • ${p:,.2f}' for p in sell_levels])}
"""
        return self.send(msg)
    
    def notify_order_filled(self, symbol: str, side: str, price: float, 
                           size: str, pnl: float = None):
        """Notify when order is filled"""
        emoji = "🟢" if side.lower() == "buy" else "🔴"
        pnl_text = f"\n💰 P&L: ${pnl:+,.2f}" if pnl else ""
        
        msg = f"""
{emoji} <b>ORDER FILLED</b>

📊 {symbol.upper()}
📈 Side: {side.upper()}
💵 Price: ${price:,.2f}
📦 Size: {size}
⏰ Time: {datetime.now().strftime('%H:%M:%S')}{pnl_text}
"""
        return self.send(msg)
    
    def notify_balance_update(self, equity: float, pnl: float, pnl_percent: float):
        """Notify balance update"""
        emoji = "📈" if pnl >= 0 else "📉"
        
        msg = f"""
{emoji} <b>BALANCE UPDATE</b>

💰 Equity: ${equity:,.2f}
📊 P&L: ${pnl:+,.2f} ({pnl_percent:+.2f}%)
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send(msg)
    
    def notify_warning(self, message: str):
        """Send warning notification"""
        msg = f"""
⚠️ <b>WARNING</b>

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send(msg)
    
    def notify_error(self, error: str):
        """Send error notification"""
        msg = f"""
🚨 <b>ERROR</b>

{error}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send(msg)
    
    def notify_daily_summary(self, equity: float, pnl: float, trades: int, 
                            win_rate: float):
        """Send daily summary"""
        emoji = "🏆" if pnl >= 0 else "📉"
        
        msg = f"""
{emoji} <b>DAILY SUMMARY</b>

💰 Equity: ${equity:,.2f}
📊 Today's P&L: ${pnl:+,.2f}
🔢 Trades: {trades}
🎯 Win Rate: {win_rate:.1f}%

📅 {datetime.now().strftime('%Y-%m-%d')}
"""
        return self.send(msg)
    
    def test_connection(self) -> bool:
        """Test if Telegram is working"""
        if not self.enabled:
            print("❌ Telegram not configured")
            return False
        
        msg = f"""
✅ <b>Bot Connected!</b>

🤖 WEEX Hackathon Trading Bot
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Your trading alerts will appear here.
"""
        success = self.send(msg)
        if success:
            print("✅ Telegram test message sent!")
        else:
            print("❌ Failed to send test message")
        return success


# Quick setup guide
def setup_guide():
    """Print setup instructions"""
    print("""
╔════════════════════════════════════════════════════════════╗
║           📱 TELEGRAM SETUP GUIDE                          ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  1️⃣  Open Telegram and search for @BotFather               ║
║                                                            ║
║  2️⃣  Send: /newbot                                         ║
║      - Choose a name (e.g., "WEEX Trading Bot")            ║
║      - Choose a username (e.g., "weex_trade_bot")          ║
║                                                            ║
║  3️⃣  Copy the API token BotFather gives you               ║
║      (looks like: 123456789:ABCdefGHI...)                  ║
║                                                            ║
║  4️⃣  Start a chat with your new bot                       ║
║      (search for @your_bot_username and click Start)       ║
║                                                            ║
║  5️⃣  Get your Chat ID:                                    ║
║      Visit: https://api.telegram.org/bot<TOKEN>/getUpdates ║
║      Find "chat":{"id": 123456789} - that's your ID        ║
║                                                            ║
║  6️⃣  Add to your .env file:                               ║
║      TELEGRAM_BOT_TOKEN=your_token_here                    ║
║      TELEGRAM_CHAT_ID=your_chat_id_here                    ║
║                                                            ║
║  7️⃣  Test: python utils/telegram_notifier.py              ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        setup_guide()
    else:
        # Test connection
        notifier = TelegramNotifier()
        
        if notifier.enabled:
            print("\nSending test message...")
            notifier.test_connection()
        else:
            print("\n⚠️ Telegram not configured yet.")
            setup_guide()
