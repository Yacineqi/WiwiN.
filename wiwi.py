pip install python-telegram-bot
import logging
import sys
import threading
import time
import requests
from telegram import ParseMode, Update
from telegram.ext import CallbackContext, CommandHandler, Updater
from web3 import Web3

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# معلومات البوت
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
ADMIN_CHAT_ID = 749342823
POLYGON_RPC = 'https://polygon-rpc.com/'
MIN_PRICE_DIFFERENCE = 0.5

# عناوين العقود
PLATFORM_ADDRESSES = {
    'ParaSwap V5': '0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57',
    'Uniswap V3': '0xE592427A0AEce92De3Edee1F18E0157C05861564'
}

TOKENS = {
    'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
}

class DexPriceBot:
    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
        self.session = requests.Session()
        self.last_notification_time = {}
        self.is_running = False
        self.updater = Updater(TELEGRAM_BOT_TOKEN)
        self.setup_handlers()

    def setup_handlers(self):
        dp = self.updater.dispatcher
        dp.add_handler(CommandHandler("start", self.cmd_start))

    def get_token_price(self, platform: str, token_address: str) -> float:
        try:
            url = f"https://api.1inch.io/v5.0/137/quote?fromTokenAddress={token_address}&toTokenAddress={TOKENS['USDT']}&amount=1000000000000000000"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                return float(data['toTokenAmount']) / 1e6
            return 0
        except Exception as e:
            logger.error(f"خطأ في الحصول على السعر من {platform}: {e}")
            return 0

    def check_prices(self):
        while self.is_running:
            try:
                for token_symbol, token_address in TOKENS.items():
                    prices = {}
                    for platform_name in PLATFORM_ADDRESSES.keys():
                        price = self.get_token_price(platform_name, token_address)
                        if price > 0:
                            prices[platform_name] = price

                    if len(prices) >= 2:
                        min_price = min(prices.values())
                        max_price = max(prices.values())
                        price_diff = ((max_price - min_price) / min_price) * 100

                        if price_diff >= MIN_PRICE_DIFFERENCE:
                            self.notify_price_difference(token_symbol, prices, price_diff)

                time.sleep(30)
            except Exception as e:
                logger.error(f"خطأ في فحص الأسعار: {e}")
                time.sleep(60)

    def notify_price_difference(self, token_symbol: str, prices: dict, diff_percentage: float):
        now = time.time()
        if token_symbol in self.last_notification_time:
            if now - self.last_notification_time[token_symbol] < 300:
                return

        self.last_notification_time[token_symbol] = now

        message = f" <b>فرصة تداول محتملة!</b>\n\n"
        message += f" العملة: {token_symbol}\n"
        message += f" فرق السعر: {diff_percentage:.2f}%\n\n"
        message += "<b>الأسعار:</b>\n"

        for platform, price in prices.items():
            message += f"• {platform}: ${price:.4f}\n"

        for user_id in [ADMIN_CHAT_ID]:
            try:
                self.updater.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"فشل إرسال الإشعار للمستخدم {user_id}: {e}")

    def cmd_start(self, update: Update, context: CallbackContext) -> None:
        message ="مرحباً بك في بوت مراقبة أسعار DeFi!"
        update.message.reply_text(message)

    def run(self):
        self.is_running = True
        price_thread = threading.Thread(target=self.check_prices)
        price_thread.start()
        
        logger.info("تم بدء تشغيل البوت")
        self.updater.start_polling()
        self.updater.idle()
        self.is_running = False
        logger.info("تم إيقاف البوت")

if __name__ == "__main__":
    bot = DexPriceBot()
    bot.run()