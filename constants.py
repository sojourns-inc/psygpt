from dotenv import load_dotenv
import os
import base64
from utils import RateLimiter, MultiKeyDict

load_dotenv()

# Env constants
BASE_URL = os.getenv("BASE_URL")
BASE_URL_BETA = os.getenv("BASE_URL_BETA")
DOWNTIME = int(os.getenv("DOWNTIME"))
FREEMODE = int(os.getenv("FREEMODE"))
APPLICATION_ID = os.getenv("ALGO_APP_ID")
API_KEY = os.getenv("ALGO_API_KEY")
INDEX_NAME = os.getenv("ALGO_INDEX")
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
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PATREON_LINKER_SUCCESS_URL = os.getenv("PATREON_LINKER_SUCCESS_URL")
PATREON_LINKER_CANCEL_URL = os.getenv("PATREON_LINKER_CANCEL_URL")
ANNOUNCEMENT_TEXT = os.getenv("ANNOUNCEMENT_TEXT")
RESTRICTED_USER_IDS = os.getenv("RESTRICTED_USER_IDS")
PRIVILEGED_USER_IDS = os.getenv("PRIVILEGED_USER_IDS")
RESTRICTED_GROUP_IDS = os.getenv("RESTRICTED_GROUP_IDS")
LIMITED_GROUP_IDS=  os.getenv("LIMITED_GROUP_IDS")
PRIVILEGED_GROUPS = os.getenv("PRIVILEGED_GROUPS")
BETA_TESTER_GROUPS = os.getenv("BETA_TESTER_GROUPS")
BETA_TESTER_USERS = os.getenv("BETA_TESTER_USERS")
BOT_GREETING_MSG = base64.b64decode(os.getenv("BOT_GREETING_MSG")).decode("utf-8")

print(RESTRICTED_USER_IDS)
# Text & info message parsing
SORRY_MSG = lambda x: f"Sorry, I couldn't fetch the {x}. Please try again later."
ESCAPE_TEXT = lambda text: text

RESTRICTED_USER_IDS = [int(id) for id in RESTRICTED_USER_IDS.split(",") if id] if "," in RESTRICTED_USER_IDS else [int(RESTRICTED_USER_IDS)]
PRIVILEGED_USER_IDS = [int(id) for id in PRIVILEGED_USER_IDS.split(",") if id] if "," in PRIVILEGED_USER_IDS else [int(PRIVILEGED_USER_IDS)]
RESTRICTED_GROUP_IDS = [int(id) for id in RESTRICTED_GROUP_IDS.split(",") if id] if "," in RESTRICTED_GROUP_IDS else [int(RESTRICTED_GROUP_IDS)]
LIMITED_GROUP_IDS = [int(id) for id in LIMITED_GROUP_IDS.split(",") if id] if "," in LIMITED_GROUP_IDS else [int(LIMITED_GROUP_IDS)]
PRIVILEGED_GROUPS = [int(id) for id in PRIVILEGED_GROUPS.split(",") if id] if "," in PRIVILEGED_GROUPS else [int(PRIVILEGED_GROUPS)]
BETA_TESTER_GROUPS = [int(id) for id in BETA_TESTER_GROUPS.split(",") if id] if "," in BETA_TESTER_GROUPS else [int(BETA_TESTER_GROUPS)]
BETA_TESTER_USERS = [int(id) for id in BETA_TESTER_USERS.split(",") if id] if "," in BETA_TESTER_USERS else [int(BETA_TESTER_USERS)]

BOT_USERNAME = os.getenv("BOT_USERNAME")

# Custom Dose Cards
CUSTOM_DOSE_CARD_DMXE = os.getenv("CUSTOM_DOSE_CARD_DMXE", "DMXE dose information")
CUSTOM_DOSE_CARD_FXE = os.getenv("CUSTOM_DOSE_CARD_FXE", "FXE dose information")
CUSTOM_DOSE_CARD_3_FL_PCP = os.getenv("CUSTOM_DOSE_CARD_3_FL_PCP", "3-FL-PCP dose information")
CUSTOM_KVL_DRUGS_PHENETHYLMETHADONE = os.getenv("CUSTOM_KVL_DRUGS_PHENETHYLMETHADONE", "phenethylmethadone, pmh")
CUSTOM_KVL_DRUGS_NORPHENADOXONE = os.getenv("CUSTOM_KVL_DRUGS_NORPHENADOXONE", "norphenadoxone, n-pdx")

CUSTOM_KVL_DRUGS = MultiKeyDict()
CUSTOM_KVL_DRUGS.add(["phenethylmethadone", "pmh"], CUSTOM_KVL_DRUGS_PHENETHYLMETHADONE)
CUSTOM_KVL_DRUGS.add(["norphenadoxone", "n-pdx"], CUSTOM_KVL_DRUGS_NORPHENADOXONE)