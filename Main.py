import os
import telebot
from flask import Flask, request
from openai import OpenAI

# 1. Load Environment Variables
bot_token = os.environ.get("bot_token")
hf_token = os.environ.get("hf_token")

if not bot_token or not hf_token:
    raise ValueError("Missing environment variables. Please set 'bot_token' and 'hf_token'.")

# 2. Initialize Telegram Bot & Flask App
bot = telebot.TeleBot(bot_token)
app = Flask(__name__)

# 3. Initialize OpenAI Client (pointing to Hugging Face Router)
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=hf_token,
)

# 4. Automatically Set Webhook for Render
# Render automatically provides RENDER_EXTERNAL_URL to web services
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
if RENDER_URL:
    bot.remove_webhook()
    # Set the webhook to point to our Flask route below
    bot.set_webhook(url=f"{RENDER_URL}/{bot_token}")

# 5. Define Bot Commands & Message Handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am an AI chatbot. Ask me anything!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Request to HuggingFace Router using OpenAI SDK
        chat_completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V4-Pro:novita",
            messages=[
                {
                    "role": "user",
                    "content": message.text,
                }
            ],
        )
        
        # Extract and send the response text
        reply = chat_completion.choices[0].message.content
        bot.reply_to(message, reply)
        
    except Exception as e:
        bot.reply_to(message, "Sorry, I encountered an error while thinking.")
        print(f"Error: {e}")

# 6. Flask Webhook Routes
@app.route(f'/{bot_token}', methods=['POST'])
def receive_update():
    """Receive incoming webhook updates from Telegram."""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route('/')
def index():
    """Health check route for Render."""
    return "Bot is successfully running online!", 200

# 7. Fallback for Local Testing
if __name__ == '__main__':
    if not RENDER_URL:
        # If running locally (not on Render), use polling instead of webhooks
        print("Starting bot in polling mode...")
        bot.remove_webhook()
        bot.infinity_polling()
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
