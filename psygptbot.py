import logging
import os
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
)
from telegram.constants import ParseMode, ChatAction
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client
from algoliasearch.search_client import SearchClient


load_dotenv()


# Constants
def create_drug_info_card(drug_name):
    drug_name_upper = drug_name.upper()
    search_url = f"https://psychonautwiki.org/w/index.php?search={drug_name}&title=Special%3ASearch&go=Go"
    info_card = f"""{drug_name_upper}

🔭 *Class*
- ✴️ *Chemical:* ➡️ Gabapentinoids
- ✴️ *Psychoactive:* ➡️ Depressant

⚖️ *Dosages*
- ✴️ *ORAL* ✴️
  - *Threshold:* 200mg
  - *Light:* 200 - 600mg
  - *Common:* 600 - 900mg
  - *Strong:* 900 - 1200mg
  - *Heavy:* 1200mg

⏱️ *Duration:*
- ✴️ *ORAL* ✴️
  - *Onset:* 30 - 90 minutes
  - *Total:* 5 - 8 hours

⚠️ *Addiction Potential* ⚠️
- No addiction potential information.

🧠 *Subjective Effects*
  - *Focus enhancement*
  - *Euphoria*

📈 *Tolerance:*
  - *Full:* with prolonged continuous usage
  - *Baseline:* 7-14 days
"""
    return info_card




# Env constants
BASE_URL = os.getenv("BASE_URL")
APPLICATION_ID = os.getenv("ALGO_APP_ID")
API_KEY = os.getenv("ALGO_API_KEY")
INDEX_NAME = os.getenv("ALGO_INDEX")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TELETOKEN = os.getenv("TELETOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

stripe.api_key = os.getenv("STRIPE_API_KEY")
endpoint_secret = os.getenv("STRIPE_ENDPOINT_SECRET")
STRIPE_PLAN_ID = os.getenv("STRIPE_PLAN_ID")

# Text & info message parsing
SORRY_MSG = lambda x: f"Sorry, I couldn't fetch the {x}. Please try again later."
ESCAPE_TEXT = lambda text: text
# ESCAPE_TEXT = lambda text: re.sub(r"([_\*\[\]\(\)~`>\#\+\-=\|{}\.!])", r"\\1", text)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("PsyAI Log 🤖")

# Algolia
client = SearchClient.create(APPLICATION_ID, API_KEY)
index = client.init_index(INDEX_NAME)

# Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#\+=-|{}.!'
    return ''.join('\\' + char if char in escape_chars else char for char in text)

def check_stripe_sub(telegram_user_id):
    user_associations = supabase.table("user_association").select("*").execute()
    user_association = None

    for association in user_associations.data:
        if association["telegram_id"] == telegram_user_id:
            user_association = association

    if not user_association:
        return False

    subscription_is_active = user_association["subscription_status"]

    return subscription_is_active


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


def fetch_new_chat_id_from_psygpt(query: str):
    try:
        raw = {"name": f"Card => {query}"}
        return post_and_parse_url(f" {BASE_URL}/chat", raw)
    except Exception as error:
        logger.error(f"Error in fetch_new_chat_id_from_psygpt: {error}")
        return None


def fetch_dose_card_from_psygpt(substance_name: str, chat_id: str):
    try:
        raw = {
            "model": LLM_MODEL_ID,
            "question": f"Write a drug information card for {substance_name}.\n\n Example drug information card:\n\n"
            + create_drug_info_card(substance_name)
            + "\n\nNote: Not every section from the example dose card is required, and you may add additional sections if needed. Please keep the formatting compact and uniform using Markdown, and maintain one newline between each bullet point.",
            "temperature": "0.1",
            "max_tokens": 10000,
        }
        return post_and_parse_url(f"{BASE_URL}/chat/{chat_id}/question", raw)
    except Exception as error:
        logger.error(f"Error in fetch_question_from_psygpt: {error}")
        return None


def fetch_question_from_psygpt(query: str, chat_id: str):
    try:
        raw = {
            "model": LLM_MODEL_ID,
            "question": f"{query}\n\n(Please respond in a conversational manner. If the context doesn't have specific information about the query, you can say something like 'I'm not sure, but...' or 'I don't have that information, however...'. Please limit your response to 30000 characters max.)",
            "temperature": "0.6",
            "max_tokens": 10000,
        }
        return post_and_parse_url(f"{BASE_URL}/chat/{chat_id}/question", raw)
    except Exception as error:
        logger.error(f"Error in fetch_question_from_psygpt: {error}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    welcome_text = "Welcome to PsyAI Bot! If you aren't subbed, type /sub to do so. Type /info [Drug Name] to request info about a particular substance. You can also ask me general questions about substances by typing /ask [Your question here]."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text,  # reply_markup=reply_markup
    )


async def respond_to_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_stripe_sub(update.effective_user.id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You must have an active subscription to use this command.",
        )
        return

    query = update.message.text.split("/ask ")[1]
    logger.info(f"Asking: `{query}`")
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    data_chat = fetch_new_chat_id_from_psygpt(query)
    if not data_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=SORRY_MSG("chat ID"),
        )
        return
    data_question = fetch_question_from_psygpt(query, data_chat["data"]["chat_id"])
    if not data_question:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=SORRY_MSG("question"),
        )
        return
    reply_text = ESCAPE_TEXT(f"{data_question['data']['assistant']}\n")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=reply_text,
    )


async def respond_to_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_stripe_sub(update.effective_user.id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You must have an active subscription to use this command.",
        )
        return

    substance_name = update.message.text.split("/info ")[1]
    logger.info(f"Info: `{substance_name}`")
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    data_chat = fetch_new_chat_id_from_psygpt(substance_name)
    if not data_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=SORRY_MSG("chat ID"),
        )
        return

    data_question = fetch_dose_card_from_psygpt(
        substance_name, data_chat["data"]["chat_id"]
    )
    if not data_question:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=SORRY_MSG("question"),
        )
        return

    # Format the reply
    reply_text = escape_markdown_v2(f"{data_question['data']['assistant']}\n\nContact: Email: `0@sernyl.dev`")
    print(reply_text)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=reply_text,
        parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
    )

async def respond_to_fx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    substance_name = update.message.text.lower().split("/fx ")[1]
    logger.info(f"FX: `{substance_name}`")
    substance_name_cap = substance_name.capitalize()
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    try:
        results = index.search(substance_name)["hits"]
        if not results:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, I couldn't fetch the effects. Please try again later.",
            )
            return

        effects = "\n\n".join(
            [
                f"* {hit['effect']} : {hit['detail']}"
                if hit["detail"]
                else f"* {hit['effect']}"
                for hit in results[:8]
            ]
        )

        reply_text = ESCAPE_TEXT(
            f"{substance_name_cap} - User-Reported Effects\n\n{effects}\n\nContact: Email: `0@sernyl.dev`"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=reply_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as error:
        print(f"Error in respond_to_fx: {str(error)}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. Please try again later.",
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
        success_url="https://psyai-patreon-linker-97bd2997eae8.herokuapp.com/success",
        cancel_url="https://psyai-patreon-linker-97bd2997eae8.herokuapp.com/cancel",
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
    fx_handler = MessageHandler(
        callback=respond_to_fx,
        filters=(
            telegram.ext.filters.COMMAND
            & telegram.ext.filters.TEXT
            & telegram.ext.filters.Regex(r"^/fx")
        ),
    )

    # Create the subscription command handler
    sub_handler = CommandHandler("sub", start_subscription)

    # Add the handler to the application
    application.add_handler(sub_handler)
    application.add_handler(ask_handler)
    application.add_handler(start_handler)
    application.add_handler(info_handler)
    application.add_handler(fx_handler)

    application.run_polling()
