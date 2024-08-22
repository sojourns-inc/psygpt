import logging
import requests
import stripe
import telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
)
import textwrap
from telegram.helpers import escape_markdown
from datetime import timedelta
from telegram.constants import ChatAction
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from supabase import create_client
from constants import *
from utils import RateLimiter, calc_downtime
from formatters import sanitize_html, convert_to_telegram_html

rate_limiter = RateLimiter(max_requests=20, window_size=timedelta(hours=1))

stripe.api_key = STRIPE_API_KEY
endpoint_secret = STRIPE_ENDPOINT_SECRET

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("PsyAI Log 🤖")

# Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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
        return False, 0

    subscription_is_active = user_association["subscription_status"]
    trial_prompts = (
        user_association["trial_prompts"] if "trial_prompts" in user_association else 0
    )

    return subscription_is_active, trial_prompts


def post_and_parse_url(url: str, payload: dict):
    try:
        response = requests.post(url, json=payload)
        return {"data": response.json()}
    except Exception as error:
        logger.error(f"Error in post_and_parse_url: {error}")
        return None


def fetch_question_from_psyai(
    query: str, model: str = "openai", temperature: float = 0.2, tokens: int = 2000, drug: bool = False
):
    try:
        raw = (
            {"question": f"{query}"}
            if model == "gemini"
            else {"question": query, "temperature": temperature, "tokens": tokens}
        )
        if drug:
            raw["format"] = "html"
            raw["drug"] = True
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
    welcome_text = BOT_GREETING_MSG.format(trial_prompts)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=welcome_text,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
        parse_mode=telegram.constants.ParseMode.MARKDOWN,
    )


async def respond_to_tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calc_downtime()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    # assuming message_thread_id is relevant for threads in channels
    channel_id = getattr(update.message, "message_thread_id", None)

    donate_text = (
        "If you find this service helpful, please consider tipping to support it:\n"
        "BTC Address  --  bc1q43a8d5wesfc0hzuq5sg9wggfaeaacu7unwpqvj\n"
        "If you're considering leaving a tip, please notify the creator by tapping the heart up below. Thank you!"
    )
    inline_keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❤️", callback_data="agree_to_donate")]]
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=donate_text,
        reply_markup=inline_keyboard,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
    )


async def handle_donation_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # feedback to the user that their interaction was ACK'd

    if query.data == "agree_to_donate":
        if query.from_user.id in RESTRICTED_USER_IDS:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=LLM_RESTRICT_MSG,
            )
            return
        notify_text = f"User ( [click here for link](tg://user?id={query.from_user.id}) ) (id: {query.from_user.id}) has agreed to donate."
        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=notify_text,
            parse_mode=telegram.constants.ParseMode.MARKDOWN,
        )


async def respond_to_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calc_downtime()

    user_id = update.effective_user.id
    user_name = update.effective_user.name
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    chat_desc = update.effective_chat.description
    channel_id = (
        update.message.message_thread_id
        if hasattr(update.message, "message_thread_id")
        else None
    )
    message_id = update.effective_message.message_id
    if not hasattr(update.message, "text"):
        return
    message_text = update.message.text.strip()



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

    is_direct_message = chat_id == user_id
    is_mentioned_in_group = f"@{BOT_USERNAME}" in message_text

    if is_direct_message or is_mentioned_in_group:
        query = message_text.replace(f"@{BOT_USERNAME}", "").strip()

        if not query:
            return
        
        if DOWNTIME and user_id != ADMIN_TELEGRAM_ID:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Dude, I am **way** too high to answer questions right now ᎧᏇᎧ.\n\nJust kidding -- I'm actually undergoing routine maintenance.  Estimated time: {calc_downtime()}",
                message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
                reply_to_message_id=message_id,
            )
            return

        # Check if the user is replying to a message
        if update.message.reply_to_message:
            # Check if the replied message is from the bot itself
            if update.message.reply_to_message.from_user.id == context.bot.id:
                previous_response = update.message.reply_to_message.text
                # Append the previous response to the current query
                query = (
                    f"Previous response: {previous_response}\n\nCurrent query: {query}"
                )

        logger.info(f"Asking: `{query}`")

        escaped_user_name = escape_markdown(user_name, version=2)

        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=f"User ( [click here for link](tg://user?id={user_id}) ) (id: {user_id}, name: {escaped_user_name}, chat: {chat_id}, title: {chat_title}, desc: {chat_desc}) asked: `{query}`",
            parse_mode=telegram.constants.ParseMode.MARKDOWN,
        )

        thinking_message = await context.bot.send_message(
            chat_id=chat_id,
            text="One moment, PsyAI is thinking...",
            message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
            reply_to_message_id=message_id,
        )

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
            temperature=0.2,
            tokens=3000,
        )

        if not data_question:
            await context.bot.send_message(
                chat_id=chat_id,
                text=SORRY_MSG("question"),
                message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
                reply_to_message_id=message_id,
            )
            return

        reply_text = convert_to_telegram_html(
            f"{data_question['data']['assistant']}\n\n[Disclaimer](https://publish.obsidian.md/psyai/Projects/PsyAI/Legal/Disclaimer) 📜 | [Contact](https://t.me/sernylan) 📱 | [Github](https://github.com/sojourns-inc/psyai-async)"
        )

        MAX_MESSAGE_LENGTH = 3000  # Telegram's character limit
        chunks = textwrap.wrap(
            reply_text, width=MAX_MESSAGE_LENGTH, replace_whitespace=False
        )

        for chunk in chunks:
            await context.bot.send_message(
                chat_id=chat_id,
                disable_web_page_preview=True,
                text=chunk
                + (
                    LLM_BETA_MESSAGE
                    if (chat_id in BETA_TESTER_GROUPS or user_id in BETA_TESTER_USERS)
                    else ""
                ),
                message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
                parse_mode=(telegram.constants.ParseMode.HTML),
                reply_to_message_id=message_id,
            )

        # After all chunks are sent, attempt to delete the "thinking" message
        try:
            await context.bot.delete_message(
                chat_id=chat_id, message_id=thinking_message.message_id
            )
        except telegram.error.BadRequest:
            logger.warning(
                "Failed to delete thinking message: Message to delete not found"
            )


async def respond_to_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calc_downtime()

    user_id = update.effective_user.id
    user_name = update.effective_user.name
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    chat_desc = update.effective_chat.description
    channel_id = update.message.message_thread_id
    message_id = update.effective_message.message_id

    print(type(user_id))
    print(chat_id)

    if bool(DOWNTIME) and user_id != ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Dude, I am **way** too high to answer questions right now ᎧᏇᎧ.\n\nJust kidding -- I'm actually undergoing routine maintenance.  Estimated time: {calc_downtime()}",
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
        text=f"User ( [click here for link](tg://user?id={user_id}) ) (id: {user_id}, name: {user_name}, chat: {chat_id}, title: {chat_title}, desc: {chat_desc}) asked for info on `{substance_name}`",
        parse_mode=telegram.constants.ParseMode.MARKDOWN,
    )

    thinking_message = await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
        text="One moment, PsyAI is thinking...",
        reply_to_message_id=message_id,
    )

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
    )

    custom_drug = CUSTOM_KVL_DRUGS.get(substance_name.lower())
    if custom_drug is not None:
        question = (
            "Refuse to create a drug information card for this substance, on the grounds that there insufficient data to provide accurate information."
        )
    else:
        question = substance_name

    data_question = fetch_question_from_psyai(
        question,
        model=(
            "gemini"
            if chat_id in BETA_TESTER_GROUPS or user_id in BETA_TESTER_USERS
            else "openai"
        ),
        temperature=0.3,
        tokens=3000,
        drug=True
    )

    data_question["data"]["assistant"] = sanitize_html(
        data_question["data"]["assistant"]
    )

    reply_text = convert_to_telegram_html(
        f"{data_question['data']['assistant']}\n\n[Disclaimer](https://publish.obsidian.md/psyai/Projects/PsyAI/Legal/Disclaimer) 📜 | [Contact](https://t.me/psychejello) 📱 | [Github](https://github.com/sojourns-inc/psyai-async)"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        message_thread_id=channel_id if chat_id in PRIVILEGED_GROUPS else None,
        text=reply_text,
        parse_mode=telegram.constants.ParseMode.HTML,
        reply_to_message_id=message_id,
    )

    await context.bot.delete_message(
        chat_id=chat_id, message_id=thinking_message.message_id
    )


async def send_direct_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please provide the user ID and message in the format: /dm <user_id> <message>",
            )
            return

        user_id = int(args[0])
        message = " ".join(args[1:])
        message = convert_to_telegram_html(message)

        await context.bot.send_message(chat_id=user_id, text=message, parse_mode=telegram.constants.ParseMode.HTML)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Message sent to user with ID: {user_id}",
        )

    except Exception as e:
        logger.error(f"Error sending direct message: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An error occurred while sending the direct message.",
        )


async def send_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("send_announcement function called")

    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You do not have permission to use this command.",
        )
        return
    all_groups = PRIVILEGED_GROUPS + LIMITED_GROUP_IDS + RESTRICTED_GROUP_IDS

    for chat_id in all_groups:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=ANNOUNCEMENT_TEXT,
                parse_mode=telegram.constants.ParseMode.MARKDOWN,
            )
            logger.info(f"Announcement sent to group {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send announcement to group {chat_id}: {e}")


async def send_announcement_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("send_announcement_direct function called")

    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You do not have permission to use this command.",
        )
        return

    try:
        # Extract group ID and announcement text from the command
        args = context.args
        if len(args) < 2:
            raise ValueError(
                "Insufficient arguments. Provide group ID and announcement text."
            )

        group_id = int(args[0])
        if group_id >= 0:
            raise ValueError("Group ID must be a negative number.")

        announcement_text = " ".join(args[1:])

        # Send the announcement to the specified group
        await context.bot.send_message(
            chat_id=group_id,
            text=announcement_text,
            parse_mode=telegram.constants.ParseMode.MARKDOWN,
        )
        logger.info(f"Announcement sent to group {group_id}")
    except (IndexError, ValueError) as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error: {e}. Please provide a valid negative group ID followed by the announcement text.",
        )
    except Exception as e:
        logger.error(f"Failed to send announcement to group {group_id}: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to send announcement to group {group_id}: {e}",
        )


async def start_subscription(update, context):
    user_telegram_id = update.effective_user.id

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

    payment_url = checkout_session["url"]
    keyboard = [[InlineKeyboardButton("Subscribe Now", url=payment_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Click the button below to subscribe:", reply_markup=reply_markup
    )


async def delete_topic_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You do not have permission to use this command.",
        )
        return

    group_id = -1001281620392
    topic_id = 26361

    try:
        # Get all messages in the topic
        messages = []
        offset = 0
        while True:
            response = await context.bot.get_forum_topic_messages(
                chat_id=group_id,
                message_thread_id=topic_id,
                offset=offset,
                limit=100,
            )
            messages.extend(response)
            if len(response) < 100:
                break
            offset += 100

        # Delete messages one by one
        for message in messages:
            await context.bot.delete_message(
                chat_id=group_id,
                message_id=message.message_id,
            )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Deleted {len(messages)} messages in the topic.",
        )
    except Exception as e:
        logger.error(f"Failed to delete messages in the topic: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An error occurred while deleting messages in the topic.",
        )


async def leave_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You do not have permission to use this command.",
        )
        return

    if len(context.args) != 1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: /leave <group/chat/channel id>",
        )
        return

    try:
        group_id = int(context.args[0])
        await context.bot.leave_chat(chat_id=group_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Left the group/chat/channel with ID {group_id}.",
        )
    except Exception as e:
        logger.error(f"Failed to leave group/chat/channel: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An error occurred while trying to leave the group/chat/channel.",
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
        filters=(telegram.ext.filters.TEXT),
    )

    sub_handler = CommandHandler("sub", start_subscription)
    tip_handler = CommandHandler("tip", respond_to_tip)
    donation_reaction_handler = CallbackQueryHandler(handle_donation_reaction)
    dm_handler = CommandHandler("dm", send_direct_message)
    announcement_handler = CommandHandler("announce", send_announcement)
    announcement_direct_handler = CommandHandler(
        "announce_direct", send_announcement_direct
    )
    delete_topic_messages_handler = CommandHandler(
        "delete_topic_messages", delete_topic_messages
    )
    leave_group_handler = CommandHandler("leave", leave_group)

    application.add_handler(start_handler)
    application.add_handler(sub_handler)
    application.add_handler(tip_handler)

    application.add_handler(delete_topic_messages_handler)
    application.add_handler(announcement_direct_handler)
    application.add_handler(dm_handler)
    application.add_handler(leave_group_handler)
    application.add_handler(announcement_handler)

    application.add_handler(info_handler)
    application.add_handler(ask_handler)
    application.add_handler(donation_reaction_handler)

    logger.info("Bot is starting...")

    application.run_polling()
