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

# MongoDB setup
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["91club_bot"]
users_collection = db["users"]

app = Client("91club_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# States for conversation handling
CONNECT_ACCOUNT_STATES = {}

def get_start_menu(user_id):
    user = users_collection.find_one({"user_id": user_id})
    welcome_text = "**Welcome to 91Club Bot!**\n\n"
    if user and user.get("logged_in"):
        welcome_text += f"Logged in as **\"{user['name']}\"**"
    else:
        welcome_text += "Please choose an option below:"

    buttons = [
        [InlineKeyboardButton("Buy Subscription", callback_data="buy_sub")],
        [InlineKeyboardButton("Connect Account", callback_data="connect_account")] 
        if not (user and user.get("logged_in")) else 
        [InlineKeyboardButton("Logout", callback_data="logout")],
        [InlineKeyboardButton("Get Live Signal", callback_data="live_signal")]
    ]
    return welcome_text, InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    welcome_text, reply_markup = get_start_menu(user_id)
    await message.reply_text(welcome_text, reply_markup=reply_markup)

@app.on_callback_query(filters.create(lambda _, __, query: query.data == "buy_sub"))
async def buy_subscription(client: Client, callback_query: CallbackQuery):
    price_text = """**Subscription Plans:**
- 1 Month: $10
- 3 Months: $25
- 6 Months: $40
- 1 Year: $70"""

    contact_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("Contact Admin", url=f"tg://user?id={ADMIN_ID}")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ])

    await callback_query.message.edit_text(
        price_text,
        reply_markup=contact_button
    )

# Add this new handler for main menu
@app.on_callback_query(filters.create(lambda _, __, query: query.data == "main_menu"))
async def main_menu(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    welcome_text, reply_markup = get_start_menu(user_id)
    await callback_query.message.edit_text(welcome_text, reply_markup=reply_markup)


@app.on_callback_query(filters.create(lambda _, __, query: query.data == "connect_account"))
async def connect_account(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    CONNECT_ACCOUNT_STATES[user_id] = "awaiting_name"
    
    await callback_query.message.edit_text(
        "Please enter your 91Club account name:"
    )

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
        
        del CONNECT_ACCOUNT_STATES[user_id]
        await message.reply_text("✅ Successfully logged in!")

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
