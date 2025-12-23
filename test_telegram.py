import asyncio
import os
from dotenv import load_dotenv
from infrastructure.telegram_alerts import TelegramAlerter, Alert, AlertLevel

# Load .env
load_dotenv()

async def test_alerts():
    print("Testing Telegram Alerts...")
    alerter = TelegramAlerter()
    
    if not alerter._enabled:
        print("❌ Telegram NOT configured. Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env")
        return

    # Send a heartbeat
    success = await alerter.send_startup()
    if success:
        print("✅ Startup alert sent successfully!")
    else:
        print("❌ Failed to send startup alert.")

    await alerter.close()

if __name__ == "__main__":
    asyncio.run(test_alerts())
