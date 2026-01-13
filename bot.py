# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM
from flask import Flask
from threading import Thread
import os
import logging

# Logging setup (Errors check karne ke liye)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FLASK SERVER START ---
app = Flask('')

@app.route('/')
def home():
    # Jab UptimeRobot is link par aayega, usse ye message milega
    return "Bot is Online and Running Safely!"

def run_flask():
    try:
        # Render ka PORT environment variable use karna zaroori hai
        port = int(os.environ.get("PORT", 8080))
        logger.info(f"Starting Flask on port {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error starting Flask: {e}")

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True # Isse Flask background mein chalta rahega
    t.start()
# --- FLASK SERVER END ---

# Userbot Client Setup
TechVJUser = None
if STRING_SESSION and not LOGIN_SYSTEM:
    try:
        TechVJUser = Client(
            "TechVJ", 
            api_id=API_ID, 
            api_hash=API_HASH, 
            session_string=STRING_SESSION
        )
    except Exception as e:
        logger.error(f"Userbot error: {e}")

class Bot(Client):
    def __init__(self):
        super().__init__(
            "techvj login",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="TechVJ"),
            workers=150,
            sleep_threshold=15 # Restricted content ke liye thoda zyada threshold behtar hai
        )

    async def start(self):
        await super().start()
        # Agar Userbot setup hai toh usse bhi start karein
        if TechVJUser:
            try:
                await TechVJUser.start()
                logger.info("Userbot Started!")
            except Exception as e:
                logger.error(f"Failed to start Userbot: {e}")
        logger.info('Bot Started Powered By @VJ_Bots')

    async def stop(self, *args):
        await super().stop()
        if TechVJUser:
            await TechVJUser.stop()
        logger.info('Bot Stopped Bye')

if __name__ == "__main__":
    # 1. Sabse pehle Flask start karein taaki Render ko signal mil jaye
    keep_alive() 
    
    # 2. Phir Bot start karein
    try:
        bot = Bot()
        bot.run()
    except Exception as e:
        logger.error(f"Main Bot Crash: {e}")
