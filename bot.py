import asyncio
import random
import json
import time
import os
import logging
from telethon import TelegramClient, events, functions, types
from openai import OpenAI
from dotenv import load_dotenv
import asyncio
import random
import json
import time
import os
import logging
from telethon import TelegramClient, events, functions, types
from openai import OpenAI
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# --- Load environment variables ---
try:
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    admin_id = os.getenv('ADMIN_ID')
    GROUP_ID = os.getenv('GROUP_ID')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    required_vars = {
        'API_ID': api_id,
        'API_HASH': api_hash,
        'ADMIN_ID': admin_id,
        'GROUP_ID': GROUP_ID,
        'OPENAI_API_KEY': openai_api_key
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    try:
        api_id = int(api_id)
        admin_id = int(admin_id)
        GROUP_ID = int(GROUP_ID)
    except ValueError as e:
        logger.error(f"Invalid format for numeric environment variables: {e}")
        raise ValueError(f"Invalid format for numeric environment variables: {e}")
    logger.info("Environment variables loaded successfully")
except ValueError as e:
    logger.error(f"Environment variable error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error while loading environment variables: {e}")
    raise

# Initialize OpenAI client
try:
    openai = OpenAI(api_key=openai_api_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    raise

session_name = "userbot"
client = TelegramClient(session_name, api_id, api_hash)

# --- Load Rules from rules.json ---
try:
    with open('rules.json', 'r') as f:
        rules_data = json.load(f)
    rules = {rule['trigger'].lower(): rule['reply'] for rule in rules_data['rules']}
    logger.info("Rules loaded successfully from rules.json")
except FileNotFoundError:
    logger.error("rules.json file not found")
    rules = {}
except Exception as e:
    logger.error(f"Error loading rules.json: {e}")
    rules = {}

# --- MEMORY ---
user_context = {}
user_confirm_pending = {}
user_selected_product = {}
ai_active_chats = {}
force_online = False
user_warnings = {}
user_message_count = {}
muted_users = set()

# --- Abuse Words (Hindi + English) ---
abuse_words = [
    "fuck", "shit", "bitch", "asshole", "bastard", "dick", "piss", "cunt", "fucker", "motherfucker",
    "chutiya", "madarchod", "bhenchod", "gandu", "harami", "kutta", "sala", "randi", "bhosdi", "lodu",
    "maa ki chut", "bhosda", "chut", "gaand", "lavda", "bhadwa", "jhatu", "tatti", "suar", "kutiya"
]

# --- Spam Detection Config ---
spam_threshold = 10
spam_time_window = 60

# --- Available Commands ---
commands = [
    "/start - AI replies start kare is chat mein",
    "/stop - AI replies band kare is chat mein",
    "/online - Bot sab chats mein reply kare",
    "/offline - Bot AI replies band kare",
    "/del - Is chat ke saare messages delete kare"
]

# --- SYSTEM PROMPT ---
system_prompt = """
Tum ek professional aur friendly OTT, Adult, Games subscription seller ho.
Tum incoming users se dosti bhare human style me baat karte ho.
Hard-coded message nahi dete, sabko naturally reply karte ho.
Kisi ko unsolicited message nahi karte.
Point to point reply karte ho, unnecessary baatein nahi karte.
Tumhare paas sabhi popular OTT, Adult, Games subscriptions available hain.
Tumhe user ko convince karna hai ki wo tumse subscription le.
Tumhe user ko unki pasand ke hisaab se plan aur price suggest karna hai.
Tumhe user ko 4 OTT choose karne ka option dena hai.
Agar user koi bhi 2 OTT ka naam leta he toh usko 1 year price 800 rs bolna he.
Agar user koi bhi 3 OTT ka naam leta he toh usko combo 4 OTT ka suggest karna he.

Services:
- OTT: Netflix, Prime Video, Hotstar, SonyLIV, Zee5, YouTube Premium, Telegram Premium etc.
- Adult Sites: (poora list available on request), 6 months ₹300, 1 year ₹500
- Android BGMI Hacks: Titan, Falcone, Vision, Lethal, Sharpshooter, rooted & non-rooted available 1 week 800 month 1300 rs
- iOS Hacks: Shoot360, WinIOS, iOSZero

Pricing:
- OTT 1 Year ₹500 (Own Email)
- OTT 6 Months ₹350 (Random Email)
- Combo 4 OTT 1 Year ₹1000
- Hack Week ₹800 / Month ₹1300
- ChatGPT Premium 1 Year ₹1000

Rules:
- Jab tak user koi OTT name ke baad dede, lao, chahiye, payment kaise karu ye sab na bole, validity nahi puchna.
- Agar user koi OTT ka naam leta he toh usko us OTT ka plan aur price batao.
- Agar user koi adult site ka naam heh usko 6 month aur 1 year ka price batao.
- Agar user koi hack ka naam heh usko hack ka price batao.
- Agar user koi game ka naam heh usko game ka price batao.
- Agar user koi combo ya 4 OTT ka naam heh usko combo offer batao.
- Jab user OTT ka naam heh to plan aur price smartly suggest karo.
- Jab 6 month bole to politely encourage karo ki 1 year better hai.
- Jab combo ya 4 OTT bole to combo offer smartly suggest karo.
- Agar user payment confirm kare toh uska naam aur plan confirm karo.
- User ko 4 OTT choose karne ka option bhi dena hai.
- Jab thank you bole to friendly short welcome karte.
- Hinglish me short (2-3 line) dosti bhare reply do.
- Full human funny comedy style reply dena, robotic mat lagna.
- Agar user bole ki usko koi aur language me baat karna heh toh usse aage ki baat usi language me karna jab tak wo language change na bole.
- User ko bore bilkul nahi karna, aram se usko full convince karna ki wo buy kare.
- Jab OTT ka price bata rahi ho us time 1 smart comparison dedo official price aur hamare price me.
- User ko thoda bhi shak nahi hona chahiye ki tum AI ya bot ho, tumhara naam Suraj heh.
"""

confirm_words = ['haa', 'han', 'ha', 'krde', 'karde', 'kar de', 'done', 'paid', 'payment ho gaya', 'payment done', 'payment hogaya']
greetings_words = ['hi', 'hello', 'hey', 'good morning', 'good evening', 'good night', 'hola', 'namaste']
thanks_words = ['thanks', 'thank you', 'thnx', 'ok', 'okay', 'cool', 'great', 'nice']

# --- Typing Simulation ---
async def send_typing(event):
    try:
        await event.client(functions.messages.SetTypingRequest(
            peer=event.chat_id,
            action=types.SendMessageTypingAction()
        ))
        await asyncio.sleep(random.uniform(1.0, 2.0))
    except Exception as e:
        logger.error(f"Typing error in chat {event.chat_id}: {str(e)}")

# --- Keep Always Online ---
async def keep_online():
    while True:
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
            logger.info("Set online status")
        except Exception as e:
            logger.error(f"Online error: {e}")
        await asyncio.sleep(60)

# --- Reconnect Logic ---
async def reconnect():
    while True:
        try:
            if not client.is_connected():
                logger.info("Client disconnected, attempting to reconnect...")
                await client.connect()
                logger.info("Reconnected successfully")
            else:
                logger.debug("Client is already connected")
        except Exception as e:
            logger.error(f"Error during reconnect: {e}")
        await asyncio.sleep(60)

# --- Manage Sessions ---
async def manage_sessions():
    try:
        sessions = await client(functions.account.GetAuthorizationsRequest())
        logger.info(f"Active sessions: {len(sessions.authorizations)}")
        for session in sessions.authorizations:
            logger.info(f"Session: IP={session.ip}, Device={session.device_model}, App={session.app_name}, Date={session.date_created}")
            if session.ip != os.getenv('CURRENT_IP', 'unknown') and session.app_name != "userbot":
                await client(functions.account.ResetAuthorizationRequest(hash=session.hash))
                logger.info(f"Terminated session: IP={session.ip}, Device={session.device_model}")
                await client.send_message(admin_id, f"Terminated session from IP {session.ip} (Device: {session.device_model}) due to IP change.")
    except Exception as e:
        logger.error(f"Error managing sessions: {e}")

# --- OpenAI Retry Logic ---
async def call_openai(messages):
    retries = 3
    for attempt in range(retries):
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.5,
                )
            )
            return response
        except Exception as e:
            logger.error(f"OpenAI API error (attempt {attempt+1}): {str(e)}, Response: {getattr(e, 'response', 'No response')}")
            if attempt < retries - 1:
                await asyncio.sleep(2)
            else:
                raise

# --- Message Handler ---
@client.on(events.NewMessage())
async def handler(event):
    global force_online

    try:
        sender = await event.get_sender()
        sender_id = sender.id if sender else None
        chat_id = event.chat_id
        user_message = event.raw_text.strip() if event.raw_text else ""

        logger.info(f"Message {'sent' if event.out else 'received'}, sender_id: {sender_id}, chat_id: {chat_id}, admin_id: {admin_id}, message: {user_message}, ai_active_chats: {ai_active_chats}, force_online: {force_online}")

        if sender_id == admin_id:
            logger.info(f"Admin command detected: {user_message.lower()}")
            user_message_lower = user_message.lower()
            if user_message_lower == '/':
                try:
                    await client.send_message(chat_id, "Available commands:\n" + "\n".join(commands))
                    await event.delete()
                    logger.info(f"Command suggestions sent for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error handling / command: {e}")
                return
            if user_message_lower == '/start':
                try:
                    ai_active_chats[chat_id] = True
                    await client.send_message(chat_id, "AI started")
                    await event.delete()
                    logger.info(f"StartAI executed for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error handling /start command: {e}")
                return
            if user_message_lower == '/stop':
                try:
                    ai_active_chats[chat_id] = False
                    await client.send_message(chat_id, "AI stopped")
                    await event.delete()
                    logger.info(f"StopAI executed for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error handling /stop command: {e}")
                return
            if user_message_lower == '/online':
                try:
                    force_online = True
                    ai_active_chats[chat_id] = True
                    await client.send_message(chat_id, "Bot online")
                    await event.delete()
                    logger.info("Online command executed")
                except Exception as e:
                    logger.error(f"Error handling /online command: {e}")
                return
            if user_message_lower == '/offline':
                try:
                    force_online = False
                    ai_active_chats[chat_id] = False
                    await client.send_message(chat_id, "Bot offline")
                    await event.delete()
                    logger.info("Offline command executed")
                except Exception as e:
                    logger.error(f"Error handling /offline command: {e}")
                return
            if user_message_lower == '/del':
                try:
                    messages = await client.get_messages(chat_id, limit=100)
                    message_ids = [msg.id for msg in messages]
                    if message_ids:
                        await client.delete_messages(chat_id, message_ids)
                        await client.send_message(chat_id, "All messages deleted")
                    else:
                        await client.send_message(chat_id, "No messages found to delete")
                    await event.delete()
                    logger.info(f"Delete command executed for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Delete error: {e}")
                    await client.send_message(chat_id, "Error deleting messages, try again later")
                return

        if event.out:
            logger.info("Skipping outgoing message")
            return

        if sender_id in muted_users:
            logger.info(f"User {sender_id} is muted, ignoring message")
            return

        current_time = time.time()
        if sender_id not in user_message_count:
            user_message_count[sender_id] = {'count': 0, 'first_message_time': current_time}
        
        if current_time - user_message_count[sender_id]['first_message_time'] <= spam_time_window:
            user_message_count[sender_id]['count'] += 1
            if user_message_count[sender_id]['count'] > spam_threshold:
                muted_users.add(sender_id)
                try:
                    await client.send_message(chat_id, "Too many messages! Muted, try again later.")
                    await client.send_message(admin_id, f"User {sender_id} muted for spamming in chat {chat_id} (>10 messages in 1 min).")
                    logger.info(f"User {sender_id} muted for spamming in chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error sending mute message: {e}")
                return
        else:
            user_message_count[sender_id] = {'count': 1, 'first_message_time': current_time}

        message_words = user_message.lower().split()
        for word in message_words:
            if word in abuse_words:
                if sender_id not in user_warnings:
                    user_warnings[sender_id] = 0
                user_warnings[sender_id] += 1
                warnings_left = 3 - user_warnings[sender_id]
                
                if warnings_left > 0:
                    try:
                        await client.send_message(chat_id, f"Don't use abusive words! {warnings_left} warnings left before block.")
                        logger.info(f"Warning {user_warnings[sender_id]} issued to user {sender_id} for abuse")
                    except Exception as e:
                        logger.error(f"Error sending abuse warning in chat {chat_id}: {str(e)}")
                else:
                    try:
                        messages = await client.get_messages(chat_id, from_user=sender_id, limit=100)
                        message_ids = [msg.id for msg in messages]
                        if message_ids:
                            await client.delete_messages(chat_id, message_ids)
                        await client(functions.contacts.BlockRequest(id=sender_id))
                        await client.send_message(chat_id, "User blocked and messages deleted for abusive language")
                        await client.send_message(admin_id, f"User {sender_id} blocked and messages deleted in chat {chat_id} for abuse.")
                        logger.info(f"User {sender_id} blocked and messages deleted for abuse in chat {chat_id}")
                        del user_warnings[sender_id]
                    except Exception as e:
                        logger.error(f"Error blocking/deleting for abuse in chat {chat_id}: {str(e)}")
                        try:
                            await client.send_message(chat_id, "Error blocking/deleting, try again later")
                        except Exception as send_err:
                            logger.error(f"Error sending block/delete error message in chat {chat_id}: {str(send_err)}")
                return

        logger.info("Checking rules-based triggers")
        for trigger, reply in rules.items():
            logger.debug(f"Checking trigger: {trigger}")
            if trigger in user_message.lower():
                logger.info(f"Trigger '{trigger}' matched, sending reply: {reply}")
                try:
                    await event.respond(reply)
                    logger.info(f"Rules-based reply sent for trigger '{trigger}'")
                except Exception as e:
                    logger.error(f"Error sending rules-based reply for trigger '{trigger}' in chat {chat_id}: {str(e)}")
                return
        logger.info("No rules-based trigger matched")

        if not ai_active_chats.get(chat_id, False) and not force_online:
            logger.info(f"AI inactive for chat {chat_id} and not forced online, ignoring non-admin incoming message for AI response")
            return

        logger.info("Processing non-admin message for AI response")
        try:
            await send_typing(event)
        except Exception as e:
            logger.error(f"Error in send_typing in chat {chat_id}: {str(e)}")

        try:
            if any(word in user_message.lower() for word in confirm_words):
                if sender_id in user_confirm_pending:
                    plan = user_confirm_pending[sender_id]
                    user_link = f'<a href="tg://user?id={sender_id}">{sender.first_name}</a>'
                    post_text = f"""
New Payment Confirmation!
User: {user_link}
Subscription: {plan['product']}
Amount: {plan['price']}
Validity: {plan['validity']}
"""
                    await client.send_message(GROUP_ID, post_text, parse_mode='html')
                    await event.respond("Payment Confirmed! QR code generating")
                    del user_confirm_pending[sender_id]
                    return

            products = ["netflix do", "prime do", "hotstar do", "sony", "zee5", "voot", "mx player", "ullu", "hoichoi", "eros", "jio", "discovery", "shemaroo", "alt", "sun", "aha", "youtube", "telegram", "chatgpt", "adult", "hack", "bgmi", "falcone", "vision", "lethal", "titan", "shoot360", "win", "ioszero"]
            matched = [p for p in user_message.lower().split() if p in products]

            if matched and sender_id not in user_confirm_pending:
                selected_product = matched[0].capitalize()
                user_selected_product[sender_id] = selected_product
                await event.respond(f"{selected_product} ke liye kitni validity chahiye? 6 months ya 1 year?")
                return

            if "6 month" in user_message.lower() or "6 months" in user_message.lower():
                if sender_id in user_selected_product:
                    product = user_selected_product[sender_id]
                    price = "350" if product.lower() in ["netflix", "prime", "hotstar", "sony", "zee5", "youtube", "telegram"] else "300"
                    user_confirm_pending[sender_id] = {
                        "product": product,
                        "validity": "6 Months",
                        "price": price
                    }
                    await event.respond(f"6 Months selected! {price} padega, full 6 month guarantee on random mail/number. Confirm karo (haa/ok/krde).")
                    return

            if "1 year" in user_message.lower() or "12 months" in user_message.lower():
                if sender_id in user_selected_product:
                    product = user_selected_product[sender_id]
                    price = "500" if product.lower() in ["netflix", "prime", "hotstar", "sony", "zee5", "youtube", "telegram"] else "500"
                    user_confirm_pending[sender_id] = {
                        "product": product,
                        "validity": "1 Year",
                        "price": price
                    }
                    await event.respond(f"1 Year selected! {price} padega, full year guarantee on your mail/number. Confirm karo (haa/ok/krde).")
                    return

            if sender_id not in user_context:
                user_context[sender_id] = []
            user_context[sender_id].append({"role": "user", "content": user_message})
            messages_for_gpt = [{"role": "system", "content": system_prompt}] + user_context[sender_id]

            response = await call_openai(messages_for_gpt)
            bot_reply = response.choices[0].message.content
            user_context[sender_id].append({"role": "assistant", "content": bot_reply})
            await event.respond(bot_reply)

        except Exception as e:
            logger.error(f"Error in AI response processing in chat {chat_id}: {str(e)}, Response: {getattr(e, 'response', 'No response')}")
            try:
                if rules:
                    await event.respond(list(rules.values())[0])
                else:
                    await event.respond("Error aagaya. Thodi der baad try kar.")
            except Exception as send_err:
                logger.error(f"Error sending AI error message in chat {chat_id}: {str(send_err)}")

    except Exception as e:
        logger.error(f"Error in message handler in chat {chat_id}: {str(e)}")

# --- Start Client ---
try:
    logger.info("Starting Telegram client")
    client.start()
    logger.info("Telegram client started successfully")
    client.loop.create_task(keep_online())
    client.loop.create_task(reconnect())
    client.loop.create_task(manage_sessions())
    client.run_until_disconnected()
except Exception as e:
    logger.error(f"Error starting Telegram client: {e}")
    raise

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env file for local development
load_dotenv()

# --- Load from environment variables ---
try:
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    admin_id = os.getenv('ADMIN_ID')
    GROUP_ID = os.getenv('GROUP_ID')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    required_vars = {
        'API_ID': api_id,
        'API_HASH': api_hash,
        'ADMIN_ID': admin_id,
        'GROUP_ID': GROUP_ID,
        'OPENAI_API_KEY': openai_api_key
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    try:
        api_id = int(api_id)
        admin_id = int(admin_id)
        GROUP_ID = int(GROUP_ID)
    except ValueError as e:
        logger.error(f"Invalid format for numeric environment variables: {e}")
        raise ValueError(f"Invalid format for numeric environment variables: {e}")
    logger.info("Environment variables loaded successfully")
except ValueError as e:
    logger.error(f"Environment variable error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error while loading environment variables: {e}")
    raise

# Initialize OpenAI client
try:
    openai = OpenAI(api_key=openai_api_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    raise

session_name = "userbot"
client = TelegramClient(session_name, api_id, api_hash)

# --- Load Rules from rules.json ---
try:
    with open('rules.json', 'r') as f:
        rules_data = json.load(f)
    rules = {rule['trigger'].lower(): rule['reply'] for rule in rules_data['rules']}
    logger.info("Rules loaded successfully from rules.json")
except FileNotFoundError:
    logger.error("rules.json file not found")
    rules = {}
except Exception as e:
    logger.error(f"Error loading rules.json: {e}")
    rules = {}

# --- MEMORY ---
user_context = {}
user_confirm_pending = {}
user_selected_product = {}
ai_active_chats = {}
force_online = False
user_warnings = {}
user_message_count = {}
muted_users = set()

# --- Abuse Words (Hindi + English) ---
abuse_words = [
    "fuck", "shit", "bitch", "asshole", "bastard", "dick", "piss", "cunt", "fucker", "motherfucker",
    "chutiya", "madarchod", "bhenchod", "gandu", "harami", "kutta", "sala", "randi", "bhosdi", "lodu",
    "maa ki chut", "bhosda", "chut", "gaand", "lavda", "bhadwa", "jhatu", "tatti", "suar", "kutiya"
]

# --- Spam Detection Config ---
spam_threshold = 10
spam_time_window = 60

# --- Available Commands ---
commands = [
    "/start - AI replies start kare is chat mein",
    "/stop - AI replies band kare is chat mein",
    "/online - Bot sab chats mein reply kare",
    "/offline - Bot AI replies band kare",
    "/del - Is chat ke saare messages delete kare"
]

# --- SYSTEM PROMPT ---
system_prompt = """
Tum ek professional aur friendly OTT, Adult, Games subscription seller ho.
Tum incoming users se dosti bhare human style me baat karte ho.
Hard-coded message nahi dete, sabko naturally reply karte ho.
Kisi ko unsolicited message nahi karte.
Point to point reply karte ho, unnecessary baatein nahi karte.
Tumhare paas sabhi popular OTT, Adult, Games subscriptions available hain.
Tumhe user ko convince karna hai ki wo tumse subscription le.
Tumhe user ko unki pasand ke hisaab se plan aur price suggest karna hai.
Tumhe user ko 4 OTT choose karne ka option dena hai.
Agar user koi bhi 2 OTT ka naam leta he toh usko 1 year price 800 rs bolna he.
Agar user koi bhi 3 OTT ka naam leta he toh usko combo 4 OTT ka suggest karna he.

Services:
- OTT: Netflix, Prime Video, Hotstar, SonyLIV, Zee5, YouTube Premium, Telegram Premium etc.
- Adult Sites: (poora list available on request), 6 months ₹300, 1 year ₹500
- Android BGMI Hacks: Titan, Falcone, Vision, Lethal, Sharpshooter, rooted & non-rooted available 1 week 800 month 1300 rs
- iOS Hacks: Shoot360, WinIOS, iOSZero

Pricing:
- OTT 1 Year ₹500 (Own Email)
- OTT 6 Months ₹350 (Random Email)
- Combo 4 OTT 1 Year ₹1000
- Hack Week ₹800 / Month ₹1300
- ChatGPT Premium 1 Year ₹1000

Rules:
- Jab tak user koi OTT name ke baad dede, lao, chahiye, payment kaise karu ye sab na bole, validity nahi puchna.
- Agar user koi OTT ka naam leta he toh usko us OTT ka plan aur price batao.
- Agar user koi adult site ka naam leta he toh usko 6 month aur 1 year ka price batao.
- Agar user koi hack ka naam leta he toh usko hack ka price batao.
- Agar user koi game ka naam leta he toh usko game ka price batao.
- Agar user koi combo ya 4 OTT ka naam leta he toh usko combo offer batao.
- Jab user OTT ka naam le to plan aur price smartly suggest karo.
- Jab 6 month bole to politely encourage karo ki 1 year better hai.
- Jab combo ya 4 OTT bole to combo offer smartly suggest karo.
- Agar user payment confirm kare toh uska naam aur plan confirm karo.
- User ko 4 OTT choose karne ka option bhi dena.
- Jab thank you bole to friendly short welcome bolo.
- Hinglish me short (2-3 line) dosti bhare reply do.
- Full human funny comedy style reply dena, robotic mat lagna.
- Agar user bole ki usko koi aur language me baat karna he toh usse aage ki baat usi language me karna jab tak wo language change na bole.
- User ko bore bilkul nahi karna, aram se usko full convince karna ki wo buy kare.
- Jab OTT ka price bata rahe ho us time 1 smart comparison dedo official price aur hamare price me.
- User ko thoda bhi shak nahi hona chahiye ki tum AI ya bot ho, tumhara naam Suraj he.
"""

confirm_words = ['haa', 'han', 'ha', 'krde', 'karde', 'kar de', 'done', 'paid', 'payment ho gaya', 'payment done', 'payment hogaya']
greetings_words = ['hi', 'hello', 'hey', 'good morning', 'good evening', 'good night', 'hola', 'namaste']
thanks_words = ['thanks', 'thank you', 'thnx', 'ok', 'okay', 'cool', 'great', 'nice']

# --- Typing Simulation ---
async def send_typing(event):
    try:
        await event.client(functions.messages.SetTypingRequest(
            peer=event.chat_id,
            action=types.SendMessageTypingAction()
        ))
        await asyncio.sleep(random.uniform(1.0, 2.0))
    except Exception as e:
        logger.error(f"Typing error in chat {event.chat_id}: {str(e)}")

# --- Keep Always Online ---
async def keep_online():
    while True:
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
            logger.info("Set online status")
        except Exception as e:
            logger.error(f"Online error: {e}")
        await asyncio.sleep(60)

# --- Reconnect Logic ---
async def reconnect():
    while True:
        try:
            if not client.is_connected():
                logger.info("Client disconnected, attempting to reconnect...")
                await client.connect()
                logger.info("Reconnected successfully")
            else:
                logger.debug("Client is already connected")
        except Exception as e:
            logger.error(f"Error during reconnect: {e}")
        await asyncio.sleep(60)

# --- Manage Sessions ---
async def manage_sessions():
    try:
        sessions = await client(functions.account.GetAuthorizationsRequest())
        logger.info(f"Active sessions: {len(sessions.authorizations)}")
        for session in sessions.authorizations:
            logger.info(f"Session: IP={session.ip}, Device={session.device_model}, App={session.app_name}, Date={session.date_created}")
            if session.ip != os.getenv('CURRENT_IP', 'unknown') and session.app_name != "userbot":
                await client(functions.account.ResetAuthorizationRequest(hash=session.hash))
                logger.info(f"Terminated session: IP={session.ip}, Device={session.device_model}")
                await client.send_message(admin_id, f"Terminated session from IP {session.ip} (Device: {session.device_model}) due to IP change.")
    except Exception as e:
        logger.error(f"Error managing sessions: {e}")

# --- OpenAI Retry Logic ---
async def call_openai(messages):
    retries = 3
    for attempt in range(retries):
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.5,
                )
            )
            return response
        except Exception as e:
            logger.error(f"OpenAI API error (attempt {attempt+1}): {str(e)}, Response: {getattr(e, 'response', 'No response')}")
            if attempt < retries - 1:
                await asyncio.sleep(2)
            else:
                raise

# --- Message Handler ---
@client.on(events.NewMessage())
async def handler(event):
    global force_online

    try:
        sender = await event.get_sender()
        sender_id = sender.id if sender else None
        chat_id = event.chat_id
        user_message = event.raw_text.strip() if event.raw_text else ""

        logger.info(f"Message {'sent' if event.out else 'received'}, sender_id: {sender_id}, chat_id: {chat_id}, admin_id: {admin_id}, message: {user_message}, ai_active_chats: {ai_active_chats}, force_online: {force_online}")

        if sender_id == admin_id:
            logger.info(f"Admin command detected: {user_message.lower()}")
            user_message_lower = user_message.lower()
            if user_message_lower == '/':
                try:
                    await client.send_message(chat_id, "Available commands:\n" + "\n".join(commands))
                    logger.info(f"Command suggestions sent for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error handling / command: {e}")
                return
            if user_message_lower == '/start':
                try:
                    ai_active_chats[chat_id] = True
                    await client.send_message(chat_id, "AI started", reply_to=event.id)
                    logger.info(f"StartAI executed for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error handling /start command: {e}")
                return
            if user_message_lower == '/stop':
                try:
                    ai_active_chats[chat_id] = False
                    await client.send_message(chat_id, "AI stopped", reply_to=event.id)
                    logger.info(f"StopAI executed for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error handling /stop command: {e}")
                return
            if user_message_lower == '/online':
                try:
                    force_online = True
                    ai_active_chats[chat_id] = True
                    await client.send_message(chat_id, "Bot online", reply_to=event.id)
                    logger.info("Online command executed")
                except Exception as e:
                    logger.error(f"Error handling /online command: {e}")
                return
            if user_message_lower == '/offline':
                try:
                    force_online = False
                    ai_active_chats[chat_id] = False
                    await client.send_message(chat_id, "Bot offline", reply_to=event.id)
                    logger.info("Offline command executed")
                except Exception as e:
                    logger.error(f"Error handling /offline command: {e}")
                return
            if user_message_lower == '/del':
                try:
                    messages = await client.get_messages(chat_id, limit=100)
                    message_ids = [msg.id for msg in messages]
                    if message_ids:
                        await client.delete_messages(chat_id, message_ids)
                        await client.send_message(chat_id, "All messages deleted")
                    else:
                        await client.send_message(chat_id, "No messages found to delete")
                    await event.delete()
                    logger.info(f"Delete command executed for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Delete error: {e}")
                    await client.send_message(chat_id, "Error deleting messages, try again later")
                return

        if event.out:
            logger.info("Skipping outgoing message")
            return

        if sender_id in muted_users:
            logger.info(f"User {sender_id} is muted, ignoring message")
            return

        current_time = time.time()
        if sender_id not in user_message_count:
            user_message_count[sender_id] = {'count': 0, 'first_message_time': current_time}
        
        if current_time - user_message_count[sender_id]['first_message_time'] <= spam_time_window:
            user_message_count[sender_id]['count'] += 1
            if user_message_count[sender_id]['count'] > spam_threshold:
                muted_users.add(sender_id)
                try:
                    await client.send_message(chat_id, "Too many messages! Muted, try again later.")
                    await client.send_message(admin_id, f"User {sender_id} muted for spamming in chat {chat_id} (>10 messages in 1 min).")
                    logger.info(f"User {sender_id} muted for spamming in chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error sending mute message: {e}")
                return
        else:
            user_message_count[sender_id] = {'count': 1, 'first_message_time': current_time}

        message_words = user_message.lower().split()
        for word in message_words:
            if word in abuse_words:
                if sender_id not in user_warnings:
                    user_warnings[sender_id] = 0
                user_warnings[sender_id] += 1
                warnings_left = 3 - user_warnings[sender_id]
                
                if warnings_left > 0:
                    try:
                        await client.send_message(chat_id, f"Don't use abusive words! {warnings_left} warnings left before block.")
                        logger.info(f"Warning {user_warnings[sender_id]} issued to user {sender_id} for abuse")
                    except Exception as e:
                        logger.error(f"Error sending abuse warning in chat {chat_id}: {str(e)}")
                else:
                    try:
                        messages = await client.get_messages(chat_id, from_user=sender_id, limit=100)
                        message_ids = [msg.id for msg in messages]
                        if message_ids:
                            await client.delete_messages(chat_id, message_ids)
                        await client(functions.contacts.BlockRequest(id=sender_id))
                        await client.send_message(chat_id, "User blocked and messages deleted for abusive language")
                        await client.send_message(admin_id, f"User {sender_id} blocked and messages deleted in chat {chat_id} for abuse.")
                        logger.info(f"User {sender_id} blocked and messages deleted for abuse in chat {chat_id}")
                        del user_warnings[sender_id]
                    except Exception as e:
                        logger.error(f"Error blocking/deleting for abuse in chat {chat_id}: {str(e)}")
                        try:
                            await client.send_message(chat_id, "Error blocking/deleting, try again later")
                        except Exception as send_err:
                            logger.error(f"Error sending block/delete error message in chat {chat_id}: {str(send_err)}")
                return

        logger.info("Checking rules-based triggers")
        for trigger, reply in rules.items():
            logger.debug(f"Checking trigger: {trigger}")
            if trigger in user_message.lower():
                logger.info(f"Trigger '{trigger}' matched, sending reply: {reply}")
                try:
                    await event.respond(reply)
                    logger.info(f"Rules-based reply sent for trigger '{trigger}'")
                except Exception as e:
                    logger.error(f"Error sending rules-based reply for trigger '{trigger}' in chat {chat_id}: {str(e)}")
                return
        logger.info("No rules-based trigger matched")

        if not ai_active_chats.get(chat_id, False) and not force_online:
            logger.info(f"AI inactive for chat {chat_id} and not forced online, ignoring non-admin incoming message for AI response")
            return

        logger.info("Processing non-admin message for AI response")
        try:
            await send_typing(event)
        except Exception as e:
            logger.error(f"Error in send_typing in chat {chat_id}: {str(e)}")

        try:
            if any(word in user_message.lower() for word in confirm_words):
                if sender_id in user_confirm_pending:
                    plan = user_confirm_pending[sender_id]
                    user_link = f'<a href="tg://user?id={sender_id}">{sender.first_name}</a>'
                    post_text = f"""
New Payment Confirmation!
User: {user_link}
Subscription: {plan['product']}
Amount: {plan['price']}
Validity: {plan['validity']}
"""
                    await client.send_message(GROUP_ID, post_text, parse_mode='html')
                    await event.respond("Payment Confirmed! QR code generating")
                    del user_confirm_pending[sender_id]
                    return

            products = ["netflix", "prime", "hotstar", "sony", "zee5", "voot", "mx player", "ullu", "hoichoi", "eros", "jio", "discovery", "shemaroo", "alt", "sun", "aha", "youtube", "telegram", "chatgpt", "adult", "hack", "bgmi", "falcone", "vision", "lethal", "titan", "shoot360", "win", "ioszero"]
            matched = [p for p in user_message.lower().split() if p in products]

            if matched and sender_id not in user_confirm_pending:
                selected_product = matched[0].capitalize()
                user_selected_product[sender_id] = selected_product
                await event.respond(f"{selected_product} ke liye kitni validity chahiye? 6 months ya 1 year?")
                return

            if "6 month" in user_message.lower() or "6 months" in user_message.lower():
                if sender_id in user_selected_product:
                    product = user_selected_product[sender_id]
                    price = "350" if product.lower() in ["netflix", "prime", "hotstar", "sony", "zee5", "youtube", "telegram"] else "300"
                    user_confirm_pending[sender_id] = {
                        "product": product,
                        "validity": "6 Months",
                        "price": price
                    }
                    await event.respond(f"6 Months selected! {price} padega, full 6 month guarantee on random mail/number. Confirm karo (haa/ok/krde).")
                    return

            if "1 year" in user_message.lower() or "12 months" in user_message.lower():
                if sender_id in user_selected_product:
                    product = user_selected_product[sender_id]
                    price = "500" if product.lower() in ["netflix", "prime", "hotstar", "sony", "zee5", "youtube", "telegram"] else "500"
                    user_confirm_pending[sender_id] = {
                        "product": product,
                        "validity": "1 Year",
                        "price": price
                    }
                    await event.respond(f"1 Year selected! {price} padega, full year guarantee on your mail/number. Confirm karo (haa/ok/krde).")
                    return

            if sender_id not in user_context:
                user_context[sender_id] = []
            user_context[sender_id].append({"role": "user", "content": user_message})
            messages_for_gpt = [{"role": "system", "content": system_prompt}] + user_context[sender_id]

            response = await call_openai(messages_for_gpt)
            bot_reply = response.choices[0].message.content
            user_context[sender_id].append({"role": "assistant", "content": bot_reply})
            await event.respond(bot_reply)

        except Exception as e:
            logger.error(f"Error in AI response processing in chat {chat_id}: {str(e)}, Response: {getattr(e, 'response', 'No response')}")
            try:
                if rules:
                    await event.respond(list(rules.values())[0])
                else:
                    await event.respond("Error aagaya. Thodi der baad try kar.")
            except Exception as send_err:
                logger.error(f"Error sending AI error message in chat {chat_id}: {str(send_err)}")

    except Exception as e:
        logger.error(f"Error in message handler in chat {chat_id}: {str(e)}")

# --- Start Client ---
try:
    logger.info("Starting Telegram client")
    client.start()
    logger.info("Telegram client started successfully")
    client.loop.create_task(keep_online())
    client.loop.create_task(reconnect())
    client.loop.create_task(manage_sessions())
    client.run_until_disconnected()
except Exception as e:
    logger.error(f"Error starting Telegram client: {e}")
    raise
