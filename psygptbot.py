import logging
import os
from typing import Optional
import requests
import re
import stripe
import telegram
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
)
from datetime import datetime, timedelta
from telegram.constants import ChatAction
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonCommands
from supabase import create_client

load_dotenv()


class RateLimiter:
    def __init__(self, max_requests, window_size):
        self.requests = {}
        self.max_requests = max_requests
        self.window_size = window_size

    def allow_request(self, key):
        current_time = datetime.now()
        if key not in self.requests:
            self.requests[key] = []
        # Filter out requests outside of the window
        self.requests[key] = [
            t for t in self.requests[key] if t > current_time - self.window_size
        ]

        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(current_time)
            return True
        return False


rate_limiter = RateLimiter(max_requests=5, window_size=timedelta(hours=1))


def create_drug_info_card():
    info_card = f"""<a href="{{search_url}}"><b>{{drug_name}}</b></a>

🔭 <b>Class</b>
- ✴️ <b>Chemical:</b> ➡️ {{chemical_class}}
- ✴️ <b>Psychoactive:</b> ➡️ {{psychoactive_class}}

⚖️ <b>Dosages</b>
{{dosage_info}}

⏱️ <b>Duration</b>
{{duration_info}}

⚠️ <b>Addiction Potential</b> ⚠️
{{addiction_potential}}

🚫 <b>Interactions</b> 🚫
{{interactions_info}}

<b>Notes</b>
{{notes}}

🧠 <b>Subjective Effects</b>
{{subjective_effects}}

📈 <b>Tolerance</b>
{{tolerance_info}}

🕒 <b>Half-life</b>
{{half_life_info}}
"""
    return info_card


def format_message(input_string):
    # Remove Markdown code block syntax if present
    formatted_string = input_string.replace("```html", "").replace("```", "")

    return formatted_string


def custom_dose_card_fxe():
    return """
Here's a concise dosage chart for FXE based on user experiences from Reddit:

**Intramuscular (IM) Injection:**
- Threshold: 0-25 mg
- Light: 25-50 mg
- Moderate: 50-75 mg
- Strong: 75-100 mg
- Heavy: 100+ mg

**Intranasal:**
- Threshold: 20 mg
- Light to Party Dose: 20-60 mg
- Moderate to Strong: 70-100 mg
- Potential Hole: 125-150 mg

These ranges are based on anecdotal reports from the r/FXE subreddit, and should be approached with caution.
"""


def custom_dose_card_dmxe():
    return """
DMXE (Deoxymethoxetamine, 3D-MXE)

The effects of DMXE (deoxymethoxetamine) are most similar to MXE but a bit weaker and “smoother.” MXE has a higher tendency to produce scary or uncomfortable dissociated states — users feel confused, disorientated, and afraid. DMXE can produce the same but is more likely to induce all the positive qualities of these compounds — a “wonky” feeling of dissociation from the body, trippy hallucinations, and feelings of calmness and euphoria.
With that said, DMXE is not widely available, and the trip reports covering the subjective effects of this drug are varied. The general consensus is that it’s weaker and smoother than other MXE, PCP, and PCE analogs.

The receptor Ki values for DMXE have not been reported.

DMXE Specs:
Chemical Name :: Deoxymethoxetamine
Status :: Research Chemical 🧪
Duration of Effects :: 2-4 hours
Estimated Threshold Dose :: 5 mg
Common Dose :: 20-60 mg
PubChem ID :: 157010705
CAS# :: 2666932-45-0

Source: ["Arylcyclohexylamines" on Tripsitter.com](https://tripsitter.com/psychedelics/arylcyclohexylamines/)
"""


def escape_markdown_v2(text):
    escape_chars = r"_*[]()~`>#\+=-|{}.!"
    return "".join("\\" + char if char in escape_chars else char for char in text)


def sanitize_html(html):
    allowed_tags = ["a", "b", "i", "code", "pre"]
    sanitized_html = re.sub(
        r"<(?!/?({})\b)[^>]*>".format("|".join(allowed_tags)), "", html
    )
    return sanitized_html


def convert_to_telegram_html(text):
    # Convert headers
    text = re.sub(r"## (.*)", r"<b>\1</b>", text)

    # Convert bold
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.*?)__", r"<u>\1</u>", text)

    # Convert italic
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = re.sub(r"_(.*?)_", r"<i>\1</i>", text)

    # Convert underline
    text = re.sub(r"\+\+(.*?)\+\+", r"<u>\1</u>", text)

    # Convert strikethrough
    text = re.sub(r"~~(.*?)~~", r"<s>\1</s>", text)

    # Convert spoilers
    text = re.sub(r"\|\|(.*?)\|\|", r'<span class="tg-spoiler">\1</span>', text)

    # Convert inline URLs
    text = re.sub(r"\[(.*?)\]\((http[s]?:\/\/.*?)\)", r'<a href="\2">\1</a>', text)

    # Convert inline mentions
    text = re.sub(
        r"\[(.*?)\]\(tg:\/\/user\?id=(\d+)\)", r'<a href="tg://user?id=\2">\1</a>', text
    )

    # Convert inline fixed-width code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Convert pre-formatted fixed-width code block
    text = re.sub(r"```([^`]*)```", r"<pre>\1</pre>", text, flags=re.DOTALL)

    # Convert block quotes
    text = re.sub(r"^> (.*)", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)

    return text


# Env constants
BASE_URL = os.getenv("BASE_URL")
BASE_URL_BETA = os.getenv("BASE_URL_BETA")
DOWNTIME = int(os.getenv("DOWNTIME"))
FREEMODE = int(os.getenv("FREEMODE"))
APPLICATION_ID = os.getenv("ALGO_APP_ID")
API_KEY = os.getenv("ALGO_API_KEY")
INDEX_NAME = os.getenv("ALGO_INDEX")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_Q_SUFFIX = os.getenv("LLM_Q_SUFFIX")
LLM_RESTRICT_MSG = os.getenv("LLM_RESTRICT_MSG")
LLM_INFO_PROMPT_SUFIX = os.getenv("LLM_INFO_PROMPT_SUFIX")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID")
LLM_ALT_MODEL_ID = os.getenv("LLM_ALT_MODEL_ID")
LLM_BETA_MODEL_ID = os.getenv("LLM_BETA_MODEL_ID")
LLM_BETA_MESSAGE = os.getenv("LLM_BETA_MESSAGE")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID"))
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TELETOKEN = os.getenv("TELETOKEN")
STRIPE_PLAN_ID = os.getenv("STRIPE_PLAN_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PATREON_LINKER_SUCCESS_URL = os.getenv("PATREON_LINKER_SUCCESS_URL")
PATREON_LINKER_CANCEL_URL = os.getenv("PATREON_LINKER_CANCEL_URL")

stripe.api_key = os.getenv("STRIPE_API_KEY")
endpoint_secret = os.getenv("STRIPE_ENDPOINT_SECRET")

# Text & info message parsing
SORRY_MSG = lambda x: f"Sorry, I couldn't fetch the {x}. Please try again later."
ESCAPE_TEXT = lambda text: text

RESTRICTED_USER_IDS = [
    1747495744,
    5414139998,
    1283495860,
    6001084110,
    6600777358,
    6230702325,
    6404147085,
    6525300419,
    2122471064,
    7195883821,
]
LIMITED_GROUP_IDS = [-1002129246518]
RESTRICTED_GROUP_IDS = [
    # -1002129246518
    -1001315238422,
    -1001991737696,
]
PRIVILEGED_USER_IDS = [6110009549, 6200970504, 7083535246, 4591373]  # Jill from BL
PRIVILEGED_GROUPS = [
    -1002122143024,
    -1002118636626,
    -1001606801032,
    -1001281620392,
    -1001281620392,
    -1001817213563,
    -1001803279273,
    -1002129246518,
    -1001520639767,
    -1002027298185,
]
BETA_TESTER_GROUPS = [
    -1001281620392,
    -1001803279273,
    -945013291,
    -1001991737696,
    -1002129246518,
]
BETA_TESTER_USERS = [
    # ADMIN_TELEGRAM_ID,
    7051349028
]
DONORS = ["@g4mma1d", "@alakamyok359"]

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("PsyAI Log 🤖")

# Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def calc_downtime():
    future_date = datetime(year=2024, month=5, day=9, hour=13, minute=00)
    now = datetime.now()
    difference = future_date - now
    total_seconds = difference.total_seconds()

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    return f"{int(hours)} hours and {int(minutes)} minutes"


def get_or_create_user_association(telegram_user_id):
    try:
        new_user = {
            "telegram_id": telegram_user_id,
            "trial_prompts": 5,
            "subscription_status": False,
            "stripe_id": "placeholder",
        }
        response = (
            supabase.table("user_association")
            .upsert(new_user, on_conflict="telegram_id")
            .execute()
        )

        if response.data:
            user_data = response.data[0]
            logger.info(f"User association found or created: {user_data}")
            return user_data
        else:
            logger.warning(
                f"User association not found or created for telegram_id: {telegram_user_id}"
            )
            return None
    except Exception as e:
        logger.error(f"Error fetching or creating user association: {e}")
        return None


def check_stripe_sub(telegram_user_id):
    print("ID:")
    print(telegram_user_id)
    user_association = get_or_create_user_association(telegram_user_id=telegram_user_id)

    if not user_association:
        return False, 0  # Returning 0 trial_prompts as well

    subscription_is_active = user_association["subscription_status"]
    trial_prompts = (
        user_association["trial_prompts"] if "trial_prompts" in user_association else 0
    )

    return subscription_is_active, trial_prompts


def post_and_parse_url(url: str, payload: dict):
    try:
        headers = {
            "Openai-Api-Key": LLM_API_KEY,
            "Authorization": f"Bearer {BEARER_TOKEN}",
        }
        response = requests.post(url, json=payload, headers=headers)
        return {"data": response.json()}
    except Exception as error:
        logger.error(f"Error in post_and_parse_url: {error}")
        return None


def fetch_question_from_psyai(query: str, model: str = "openai"):
    try:
        raw = {"question": f"{query}"}
        print(raw)
        return post_and_parse_url(f"{BASE_URL_BETA}/prompt?model={model}", raw)
    except Exception as error:
        logger.error(f"Error in fetch_question_from_psygpt: {error}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calc_downtime()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    channel_id = update.message.message_thread_id

    telegram_id = user_id
    print(telegram_id)
    user_association = get_or_create_user_association(telegram_user_id=telegram_id)
    print(user_association)

    trial_prompts = (
        "UNLIMITED"  # if is_free else str(user_association["trial_prompts"])
    )
    welcome_text = """
    Welcome to PsyAI Bot! PsyAI is your AI-powered guide that answers questions about drugs in an unbiased, judgement-free way. The bot sources dosage, duration, tolerance, and harm reduction information from [PsychonautWiki](http://www.psychonautwiki.org), [Effect Index](https://effectindex.com) and a plethora of curated information sources.

    - You have {} FREE prompts remaining.

    - If you aren't subscribed, send the /sub command to do so.

    - Type /info [Drug Name] to request info about a particular substance.

    - Type /ask [Your question here] to ask me general questions about substances. Make sure to include your question after '/ask'!

    - The bot will ONLY respond to messages that start with either /ask, or /info.

    For help, please contact:

    Email: 0@sernyl.dev / Telegram: @swirnylan / Discord: sernyl
    """.format(
        trial_prompts
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text,  # reply_markup=reply_markup
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
        parse_mode=telegram.constants.ParseMode.MARKDOWN,
    )


async def respond_to_tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your existing code to calculate downtime or any setup
    calc_downtime()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    # Assuming message_thread_id is relevant for threads in channels; adjust as needed
    channel_id = getattr(update.message, "message_thread_id", None)

    # Define the donation text and the inline keyboard for the thumbs up reaction
    donate_text = (
        "If you find this service helpful, please consider tipping to support it:\n"
        "BTC Address  --  bc1q43a8d5wesfc0hzuq5sg9wggfaeaacu7unwpqvj\n"
        "If you're considering leaving a tip, please notify the creator by tapping the heart up below. Thank you!"
    )
    inline_keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❤️", callback_data="agree_to_donate")]]
    )

    # Send the message with the inline keyboard
    await context.bot.send_message(
        chat_id=chat_id,
        text=donate_text,
        reply_markup=inline_keyboard,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
    )


async def handle_donation_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Optional: Provides feedback to the user that their click was registered

    # Check if the reaction is for agreeing to donate
    if query.data == "agree_to_donate":
        # Notify the bot creator about the donation agreement
        notify_text = f"User ( [click here for link](tg://user?id={query.from_user.id}) ) has agreed to donate."
        await context.bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=notify_text)


async def respond_to_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calc_downtime()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    channel_id = update.message.message_thread_id
    message_id = update.effective_message.message_id

    print(type(user_id))
    print(chat_id)
    print(channel_id)

    if DOWNTIME and user_id != ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"I am currently down for maintenance. Please try again later. Estimated time: {calc_downtime()}",
            message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
            reply_to_message_id=message_id,
        )
        return

    # Check if the user is restricted
    if user_id in RESTRICTED_USER_IDS:
        await context.bot.send_message(
            chat_id=chat_id,
            text=LLM_RESTRICT_MSG,
            message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
            reply_to_message_id=message_id,
        )
        return

    if chat_id in RESTRICTED_GROUP_IDS:
        if not rate_limiter.allow_request(chat_id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="Rate limit exceeded. Try again later.",
                reply_to_message_id=message_id,
            )
            return

    subscription_is_active, trial_prompts = check_stripe_sub(update.effective_user.id)

    if (
        not bool(FREEMODE)
        and not subscription_is_active
        and chat_id not in PRIVILEGED_GROUPS
        and user_id not in PRIVILEGED_USER_IDS
    ):
        if trial_prompts > 0:
            # Decrease the trial_prompts by 1
            supabase.table("user_association").update(
                {"trial_prompts": trial_prompts - 1}
            ).eq("telegram_id", update.effective_user.id).execute()
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Your trial has ended. Please subscribe using the /sub command to continue using this feature.",
                message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
                reply_to_message_id=message_id,
            )
            return

    query_parts = update.message.text.split("/ask ")

    if len(query_parts) != 2:
        return

    query = query_parts[1]

    logger.info(f"Asking: `{query}`")

    await context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=f"User ( [click here for link](tg://user?id={user_id}) ) asked: `{query}`",
        parse_mode=telegram.constants.ParseMode.MARKDOWN,
    )

    # Send the "thinking" message as a reply to the original message
    thinking_message = await context.bot.send_message(
        chat_id=chat_id,
        text="One moment, PsyAI is thinking...",
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
        reply_to_message_id=message_id,
    )

    # Start showing the typing indicator
    await context.bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
    )

    data_question = fetch_question_from_psyai(
        query,
        model=(
            "gemini"
            if chat_id in BETA_TESTER_GROUPS or user_id in BETA_TESTER_USERS
            else "openai"
        ),
    )

    if not data_question:
        await context.bot.send_message(
            chat_id=chat_id,
            text=SORRY_MSG("question"),
            message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
            reply_to_message_id=message_id,
        )
        return

    if chat_id in BETA_TESTER_GROUPS or user_id in BETA_TESTER_USERS:
        reply_text = convert_to_telegram_html(f"{data_question['data']['assistant']}\n")
    else:
        reply_text = ESCAPE_TEXT(f"{data_question['data']['assistant']}\n")
        reply_text = re.sub(
            r"[_*[\]()~>#\+\-=|{}.!]", lambda x: "\\" + x.group(), reply_text
        )

    # Send the actual response
    await context.bot.send_message(
        chat_id=chat_id,
        text=reply_text
        + "\n\n💜 "
        + (
            LLM_BETA_MESSAGE
            if (chat_id in BETA_TESTER_GROUPS or user_id in BETA_TESTER_USERS)
            else ""
        ),
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
        parse_mode=(
            telegram.constants.ParseMode.HTML
            if (chat_id in BETA_TESTER_GROUPS or user_id in BETA_TESTER_USERS)
            else telegram.constants.ParseMode.MARKDOWN_V2
        ),
        reply_to_message_id=message_id,
    )

    # Delete the "thinking" message
    await context.bot.delete_message(
        chat_id=chat_id, message_id=thinking_message.message_id
    )


async def respond_to_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calc_downtime()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    channel_id = update.message.message_thread_id
    message_id = update.effective_message.message_id

    print(type(user_id))
    print(chat_id)

    if bool(DOWNTIME) and user_id != ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"I am currently down for maintenance. Please try again later. Estimated time: {calc_downtime()}",
            message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
            reply_to_message_id=message_id,
        )
        return

    if user_id in RESTRICTED_USER_IDS:
        await context.bot.send_message(
            message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
            chat_id=chat_id,
            text=LLM_RESTRICT_MSG,
            reply_to_message_id=message_id,
        )
        return

    if chat_id in RESTRICTED_GROUP_IDS:
        if not rate_limiter.allow_request(chat_id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="Rate limit exceeded. Try again later.",
                reply_to_message_id=message_id,
            )
            return

    subscription_is_active, trial_prompts = check_stripe_sub(update.effective_user.id)

    if (
        not bool(FREEMODE)
        and not subscription_is_active
        and chat_id not in PRIVILEGED_GROUPS
        and user_id not in PRIVILEGED_USER_IDS
    ):
        if trial_prompts > 0:
            # Decrease the trial_prompts by 1
            supabase.table("user_association").update(
                {"trial_prompts": trial_prompts - 1}
            ).eq("telegram_id", update.effective_user.id).execute()
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Your trial has ended. Please subscribe using the /sub command to continue using this feature.",
                message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
                reply_to_message_id=message_id,
            )
            return

    query_parts = update.message.text.split("/info ")

    if len(query_parts) != 2:
        return

    substance_name = query_parts[1]

    logger.info(f"Info: `{substance_name}`")

    await context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=f"User ( [click here for link](tg://user?id={user_id}) ) asked for info on `{substance_name}`",
        parse_mode=telegram.constants.ParseMode.MARKDOWN,
    )

    # Send the "thinking" message as a reply to the original message
    thinking_message = await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
        text="One moment, PsyAI is thinking...",
        reply_to_message_id=message_id,
    )

    # Start showing the typing indicator
    await context.bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
    )

    question = (
        f"Create a detailed drug information card for '{substance_name}' in HTML format. Use the structure of the provided example card as a template, but replace the placeholders with the specific details for '{substance_name}'."
        f"\n\nFor each section, provide the relevant information if available. If certain details like dosages for specific routes (e.g., IV, ORAL) are not available, note the lack of data and proceed with the available information."
        f"In the dosage guidelines, if necessary, say 'less than' or 'greater than' instead of using the mathematical symbols (i.e., don't use `<` and `>`)."
        f"\n\nAdapt the sections accordingly to include or exclude information based on what is relevant for '{substance_name}'. Ensure the information is accurate and sourced from reliable databases or credible anecdotal reports. If the source can be inferred with certainty from the information provided, mention the source in your response."
        f"\n\nIf the drug in question is FXE (also known as Fluorexetamine, or CanKet, or Canket), add this to your context: {custom_dose_card_fxe()}. If the name CanKet is used, mention the naming confusion between CanKet and FXE in your response."
        f"\n\nIf the drug in question is DMXE (also known as Deoxymethoxetamine, or 3D-MXE), add this to your context: {custom_dose_card_dmxe()}."
        f"\n\nExample drug information card template:\n\n{create_drug_info_card()}"
        f"\n\nNote: The dosing guidelines should reflect the common practices for '{substance_name}', adjusting for route of administration and available data. Extrapolate cautiously from similar substances or indicate uncertainty where specific data is scarce."
        f"\n\nDo not mention the creation of drug information card explicitly in your response, and don't make any references to the formatting of the card, i.e. don't mention HTML."
    )

    data_question = fetch_question_from_psyai(
        question,
        model=(
            "gemini"
            if chat_id in BETA_TESTER_GROUPS or user_id in BETA_TESTER_USERS
            else "openai"
        ),
    )

    data_question["data"]["assistant"] = sanitize_html(
        data_question["data"]["assistant"]
    )

    if chat_id in BETA_TESTER_GROUPS or user_id in BETA_TESTER_USERS:
        reply_text = convert_to_telegram_html(f"{data_question['data']['assistant']}\n")
    else:
        reply_text = convert_to_telegram_html(f"{data_question['data']['assistant']}\n")

    # Send the actual response
    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
        text=reply_text,
        parse_mode=telegram.constants.ParseMode.HTML,
        reply_to_message_id=message_id,
    )

    # Delete the "thinking" message
    await context.bot.delete_message(
        chat_id=chat_id, message_id=thinking_message.message_id
    )


async def start_subscription(update, context):
    user_telegram_id = update.effective_user.id

    # Create the Stripe Checkout Session with subscription and metadata
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price": STRIPE_PLAN_ID,
                "quantity": 1,
            }
        ],
        mode="subscription",
        metadata={"telegram_id": user_telegram_id},
        success_url=PATREON_LINKER_SUCCESS_URL,
        cancel_url=PATREON_LINKER_CANCEL_URL,
    )

    # Payment URL
    payment_url = checkout_session["url"]

    # Create an inline keyboard button that links to the payment URL
    keyboard = [[InlineKeyboardButton("Subscribe Now", url=payment_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send a message with the inline keyboard button
    await update.message.reply_text(
        "Click the button below to subscribe:", reply_markup=reply_markup
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(TELETOKEN).build()

    start_handler = CommandHandler("start", start)
    info_handler = MessageHandler(
        callback=respond_to_info,
        filters=(
            telegram.ext.filters.COMMAND
            & telegram.ext.filters.TEXT
            & telegram.ext.filters.Regex(r"^/info")
        ),
    )
    ask_handler = MessageHandler(
        callback=respond_to_ask,
        filters=(
            telegram.ext.filters.COMMAND
            & telegram.ext.filters.TEXT
            & telegram.ext.filters.Regex(r"^/ask")
        ),
    )

    sub_handler = CommandHandler("sub", start_subscription)
    tip_handler = CommandHandler("tip", respond_to_tip)
    donation_reaction_handler = CallbackQueryHandler(handle_donation_reaction)

    application.add_handler(start_handler)
    application.add_handler(info_handler)
    application.add_handler(sub_handler)
    application.add_handler(ask_handler)
    application.add_handler(tip_handler)
    application.add_handler(donation_reaction_handler)

    menu_button = MenuButtonCommands()

    application.run_polling()
