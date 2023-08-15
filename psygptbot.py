import logging
from telegram import Update
import os
import telegram
import requests
import re
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
)
from telegram.constants import ParseMode, ChatAction
from algoliasearch.search_client import SearchClient
from dotenv import load_dotenv

load_dotenv()

# Constants
DOSECARD_EXAMPLE = ".\n\nExample (drug information card for Gabapentin):\n\n\n\n```\n\n\n\n\uD83D\uDD2D Class\n\n\n\n* Chemical \u27A1\uFE0F Gabapentinoids\n\n* Psychoactive \u27A1\uFE0F Depressant\n\n\n\n\n\n\u2696\uFE0F Dosages\n\n\n\n* \u2734\uFE0F ORAL \u2734\uFE0F\n\n   - Threshold: 200mg\n\n   - Light: 200 - 600mg\n\n   - Common: 600 - 900mg\n\n   - Strong: 900 - 1200mg\n\n   - Heavy: 1200mg\n\n\n\n\n\n\uD83D\uDD70\uFE0F Duration\n\n\n\n* \u2734\uFE0F ORAL \u2734\uFE0F\n\n   - Onset: 30 - 90 minutes\n\n   - Total: 5 - 8 hours\n\n\n\n\n\n\u26A0\uFE0F Addiction potential \u26A0\uFE0F\n\n\n\nNo addiction potential information.\n\n\n\n\uD83E\uDDE0 Subjective Effects \uD83E\uDDE0\n\n\n\n* Focus enhancement\n\n* Euphoria\n\n\n\n\uD83D\uDCC8 Tolerance\n\n* Full: with prolonged continuous usage\n\n* Baseline: 7-14 days\n\n```"
BASE_URL = "https://api.dose.tips"

# Env constants
APPLICATION_ID = os.getenv("ALGO_APP_ID")
API_KEY = os.getenv("ALGO_API_KEY")
INDEX_NAME = os.getenv("ALGO_INDEX")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TELETOKEN = os.getenv("TELETOKEN")

# Text & info message parsing
SORRY_MSG = lambda x: f"Sorry, I couldn't fetch the {x}. Please try again later."
ESCAPE_TEXT = lambda text: text
# ESCAPE_TEXT = lambda text: re.sub(r"([_\*\[\]\(\)~`>\#\+\-=\|{}\.!])", r"\\1", text)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("PsyGPT Log 🤖")

# Algolia
client = SearchClient.create(APPLICATION_ID, API_KEY)
index = client.init_index(INDEX_NAME)


def post_and_parse_url(url: str, payload: dict):
    try:
        headers = {
            "Openai-Api-Key": OPENAI_API_KEY,
            "Authorization": f"Bearer {BEARER_TOKEN}",
        }
        response = requests.post(url, json=payload, headers=headers)
        return {"data": response.json()}
    except Exception as error:
        logger.error(f"Error in post_and_parse_url: {error}")
        return None


def fetch_dose_card_from_psygpt(substance_name: str, chat_id: str):
    try:
        raw = {
            "model": "gpt-4-32k",
            "question": f"Write a drug information card for {substance_name}.\n\n"
            + DOSECARD_EXAMPLE,
            "temperature": "0.0",
            "max_tokens": 6000,
        }
        return post_and_parse_url(f"{BASE_URL}/chat/{chat_id}/question", raw)
    except Exception as error:
        logger.error(f"Error in fetch_question_from_psygpt: {error}")
        return None


def fetch_question_from_psygpt(query: str, chat_id: str):
    try:
        raw = {
            "model": "gpt-4-32k",
            "question": f"{query}\n\n(Please limit your response to 10000 characters max.)",
            "temperature": "0.5",
            "max_tokens": 6000,
        }
        return post_and_parse_url(f"{BASE_URL}/chat/{chat_id}/question", raw)
    except Exception as error:
        logger.error(f"Error in fetch_question_from_psygpt: {error}")
        return None


def fetch_new_chat_id_from_psygpt(query: str):
    try:
        raw = {"name": f"Card => {query}"}
        return post_and_parse_url(f"{BASE_URL}/chat", raw)
    except Exception as error:
        logger.error(f"Error in fetch_new_chat_id_from_psygpt: {error}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


async def respond_to_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    substance_name = update.message.text.lower().split("/info ")[1]
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
    reply_text = ESCAPE_TEXT(
        f"{substance_name}\n\n{data_question['data']['assistant']}\n\nContact: Email: `0@sernyl.dev` // [Website](https://sojourns.io)"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=reply_text,
        parse_mode=ParseMode.MARKDOWN,
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
            f"{substance_name_cap} - User-Reported Effects\n\n{effects}\n\nContact: Email: `0@sernyl.dev` // [Website](https://sojourns.io)"
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
    application.add_handler(ask_handler)
    application.add_handler(start_handler)
    application.add_handler(info_handler)
    application.add_handler(fx_handler)

    application.run_polling()
