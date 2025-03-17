import telebot
import openai
import json
import os
from flask import Flask, request
from datetime import datetime, timedelta

# Load tokens from environment
TOKEN = os.getenv("BOT_TOKEN")  # Fetch from Render environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Fetch from Render environment

bot = telebot.TeleBot(TOKEN)
openai.api_key = OPENAI_API_KEY

MEMORY_FILE = "memory.json"
MAX_MEMORY_SIZE = 10  # Keep only the last 10 messages per user
RATE_LIMIT_SECONDS = 5  # 5-second cooldown between messages

# Load and save memory functions
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as file:
        json.dump(memory, file)

memory = load_memory()

# Rate limiting dictionary
user_limits = {}

def is_rate_limited(user_id):
    now = datetime.now()
    if user_id in user_limits:
        last_message_time = user_limits[user_id]
        if now - last_message_time < timedelta(seconds=RATE_LIMIT_SECONDS):
            return True
    user_limits[user_id] = now
    return False

def trim_memory(memory, user_id):
    if user_id in memory and len(memory[user_id]) > MAX_MEMORY_SIZE:
        memory[user_id] = memory[user_id][-MAX_MEMORY_SIZE:]
    return memory

# Flask setup
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "Ajura AI Bot is Live!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if update:
        bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "OK", 200

# Handle start/help command
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(message, "Welcome to Ajura AI! Send me a message and I'll respond.")

# Handle normal messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = str(message.chat.id)
    user_input = message.text

    if is_rate_limited(user_id):
        bot.reply_to(message, "Please wait a few seconds before sending another message.")
        return

    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append({"role": "user", "content": user_input})
    memory = trim_memory(memory, user_id)
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=memory[user_id]
        )
        reply = response["choices"][0]["message"]["content"]
        memory[user_id].append({"role": "assistant", "content": reply})
        save_memory(memory)
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"Sorry, something went wrong: {str(e)}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
