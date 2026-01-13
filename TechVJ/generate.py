import traceback
import logging
from pyrogram.types import Message
from pyrogram import Client, filters
from asyncio.exceptions import TimeoutError
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid
)
from config import API_ID, API_HASH
from database.db import db

# Standard size for a Pyrogram session string
SESSION_STRING_SIZE = 351

@Client.on_message(filters.private & ~filters.forwarded & filters.command(["logout"]))
async def logout(client, message):
    user_data = await db.get_session(message.from_user.id)  
    if user_data is None:
        await message.reply("<b>⚠️ You are not currently logged in.</b>")
        return 
    
    await db.set_session(message.from_user.id, session=None)  
    await message.reply("<b>✅ Successfully Logged Out!</b> 👋✨")

@Client.on_message(filters.private & ~filters.forwarded & filters.command(["login"]))
async def main(bot: Client, message: Message):
    user_id = int(message.from_user.id)
    user_data = await db.get_session(user_id)
    
    if user_data is not None:
        await message.reply(
            "<b>⚠️ Alert: Already Logged In!</b>\n\n"
            "You have an active session. Please use /logout first if you wish to link a new account. 🔄"
        )
        return 

    # --- Step 1: API ID ---
    api_id_msg = await bot.ask(
        user_id, 
        "<b>Step 1: Provide API ID</b> 🆔\n\n"
        "Click /skip to use the default system credentials.\n\n"
        "<i>Note: Using your own API ID reduces the risk of account restrictions.</i> 🛡️", 
        filters=filters.text
    )
    
    if api_id_msg.text == "/skip":
        api_id = API_ID
        api_hash = API_HASH
    else:
        try:
            api_id = int(api_id_msg.text)
        except ValueError:
            await api_id_msg.reply("<b>❌ Error:</b> API ID must be an integer. Please restart the process with /login. ⚠️")
            return
        
        # --- Step 2: API HASH ---
        api_hash_msg = await bot.ask(user_id, "<b>Step 2: Provide API HASH</b> 🔑", filters=filters.text)
        api_hash = api_hash_msg.text
        
    # --- Step 3: Phone Number ---
    phone_number_msg = await bot.ask(
        chat_id=user_id, 
        text="<b>Step 3: Phone Number</b> 📱\n\n"
        "Please send your phone number including the country code.\n"
        "Example: <code>+919876543210</code>\n\n"
        "Send /cancel to abort the process. ❌"
    )
    
    if phone_number_msg.text == '/cancel':
        return await phone_number_msg.reply('<b>🚫 Process Cancelled.</b>')
        
    phone_number = phone_number_msg.text
    client = Client(":memory:", api_id, api_hash)
    
    await client.connect()
    await phone_number_msg.reply("<b>📡 Requesting OTP... Please wait.</b>")
    
    try:
        code = await client.send_code(phone_number)
        
        # --- Step 4: OTP ---
        phone_code_msg = await bot.ask(
            user_id, 
            "<b>Step 4: Enter OTP</b> 💬\n\n"
            "Check your official Telegram account for the code.\n\n"
            "⚠️ <b>Format:</b> Send the code with spaces. If the OTP is <code>12345</code>, send it as <code>1 2 3 4 5</code>.\n\n"
            "Send /cancel to abort. ❌", 
            filters=filters.text, 
            timeout=600
        )
    except PhoneNumberInvalid:
        await phone_number_msg.reply('<b>❌ Error:</b> The phone number provided is invalid.')
        return
    except Exception as e:
        await phone_number_msg.reply(f'<b>❌ Unexpected Error:</b> <code>{e}</code>')
        return

    if phone_code_msg.text == '/cancel':
        return await phone_code_msg.reply('<b>🚫 Process Cancelled.</b>')

    try:
        phone_code = phone_code_msg.text.replace(" ", "")
        await client.sign_in(phone_number, code.phone_code_hash, phone_code)
        
    except PhoneCodeInvalid:
        await phone_code_msg.reply('<b>❌ Error:</b> The OTP is incorrect.')
        return
    except PhoneCodeExpired:
        await phone_code_msg.reply('<b>❌ Error:</b> The OTP has expired.')
        return
    except SessionPasswordNeeded:
        # --- Step 5: 2FA Password ---
        two_step_msg = await bot.ask(
            user_id, 
            '<b>Step 5: Two-Step Verification</b> 🔐\n\n'
            'Your account has 2FA enabled. Please enter your password.\n\n'
            'Send /cancel to abort. ❌', 
            filters=filters.text, 
            timeout=300
        )
        
        if two_step_msg.text == '/cancel':
            return await two_step_msg.reply('<b>🚫 Process Cancelled.</b>')
            
        try:
            password = two_step_msg.text
            await client.check_password(password=password)
        except PasswordHashInvalid:
            await two_step_msg.reply('<b>❌ Error:</b> Invalid password provided.')
            return

    # --- Step 6: Session Generation & Save ---
    string_session = await client.export_session_string()
    await client.disconnect()
    
    if len(string_session) < SESSION_STRING_SIZE:
        return await message.reply('<b>❌ Error:</b> Generated session string is invalid.')

    try:
        await db.set_session(message.from_user.id, session=string_session)
        await db.set_api_id(message.from_user.id, api_id=api_id)
        await db.set_api_hash(message.from_user.id, api_hash=api_hash)
        
    except Exception as e:
        return await message.reply_text(f"<b>❌ Database Error:</b> <code>{e}</code>")

    await bot.send_message(
        message.from_user.id, 
        "<b>✨ Account Successfully Authenticated!</b>\n\n"
        "Your session is now securely saved. If you encounter any authentication errors in the future, please /logout and login again. 🚀"
    )
