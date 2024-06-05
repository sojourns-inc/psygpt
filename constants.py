from dotenv import load_dotenv
import os

load_dotenv()

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
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PATREON_LINKER_SUCCESS_URL = os.getenv("PATREON_LINKER_SUCCESS_URL")
PATREON_LINKER_CANCEL_URL = os.getenv("PATREON_LINKER_CANCEL_URL")
ANNOUNCEMENT_TEXT = os.getenv("ANNOUNCEMENT_TEXT")

# Text & info message parsing
SORRY_MSG = lambda x: f"Sorry, I couldn't fetch the {x}. Please try again later."
ESCAPE_TEXT = lambda text: text

RESTRICTED_USER_IDS = [
    # 1747495744,
    # 5414139998,
    # 1283495860,
    # 6001084110,
    # 6600777358,
    # 6230702325,
    # 6404147085,
    # 6525300419,
    # 2122471064,
    # 7195883821,
    # 1083132520,
    # 165302673,
    6674207752,
    1735952560,
    6604560047,
    1883984096,
    1982640077,    
]
LIMITED_GROUP_IDS = [-1002129246518]
RESTRICTED_GROUP_IDS = [
    # -1002129246518
    -1001315238422,
    # -1001991737696,
    
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
    -945013291,
    # -1002129246518,
    # -1001945911327,
]
BETA_TESTER_USERS = [
    # ADMIN_TELEGRAM_ID,
    5273774476,
    7139449177
]

BOT_USERNAME = "PsyGPTDrugInfoBot"

# Custom Dose Cards
CUSTOM_DOSE_CARD_DMXE = """
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
CUSTOM_DOSE_CARD_FXE = """
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
CUSTOM_DOSE_CARD_3_FL_PCP = """
🔭 **Class**
- ✴️ **Chemical:** ➡️ Arylcyclohexylamine
- ✴️ **Psychoactive:** ➡️ Dissociative

⚖️ **Dosages**
- Threshold: 0-5 mg
- Light: 10-25 mg
- Moderate: 25-50 mg
- Strong: 50-75 mg
- Heavy: 75+ mg

⏱️ **Duration**
- **Onset**:
  - Oral: 30 to 45 minutes
  - Sublingual: 20 to 30 minutes
  - Vaping: Immediate to a few minutes
- **Peak**: 1 to 2 hours after onset
- **Duration**: 4 to 6 hours, with lingering after-effects

⚠️ **Addiction Potential** ⚠️
- Moderate to high potential for psychological dependence with frequent use.

🚫 **Interactions** 🚫
- Avoid mixing with other stimulants or depressants.
- Be cautious of combining with other psychoactive substances.

**Notes**
- Always test substances for purity using reagent test kits.
- Use in a safe, controlled environment, especially for initial experiences.
- Have a sober sitter if using higher doses or combining substances.
- Allow several days between uses to avoid tolerance and dependence.
- Be cautious if you have a history of mental health issues.

🧠 **Subjective Effects**
- Euphoria
- Dissociation
- Stimulation or sedation (depending on the dose)
- Potential for psychosis at high doses

📈 **Tolerance**
- Tolerance builds quickly with frequent use.
- Recommended to space out use to maintain effectiveness and reduce risk.

🕒 **Half-life**
- Not specifically documented for 3-FL-PCP, but similar compounds suggest a range of several hours.

"""