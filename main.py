import telebot
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Get bot token from environment variables
    API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not API_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    # Initialize bot
    bot = telebot.TeleBot(token=API_TOKEN)
    
    # Handle /start command
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.reply_to(message, "Hello! I'm your bot. Send me a message to get your chat ID.")
    
    # Handle all other messages
    @bot.message_handler(func=lambda message: True)
    def echo_all(message):
        chat_id = message.chat.id
        bot.reply_to(message, f"Your chat ID is: {chat_id}\n\nTo use this chat ID, add it to your .env file:\nTELEGRAM_CHAT_ID={chat_id}")
    
    # Start the bot
    print("Bot is running...")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
