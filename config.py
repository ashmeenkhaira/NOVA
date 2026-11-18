"""Loads the secret keys from .env so every other file can import them.

Other files use it like this:
    from config import GROQ_API_KEY
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# The .env file sits in the same folder as this config.py file.
ENV_FILE = Path(__file__).parent / ".env"

# Read every NAME=value line from .env into the environment (os.environ).
load_dotenv(ENV_FILE)


def require(name):
    """Return the value of one key, or stop with a clear message if it is missing."""
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"{name} is missing. Add a line {name}=... to {ENV_FILE} "
            f"(see .env.example for the names)."
        )

    # Catch the common mistake of copying .env.example without editing it.
    if value.startswith("your-"):
        raise RuntimeError(
            f"{name} still has the placeholder value from .env.example. "
            f"Replace it with your real key in {ENV_FILE}."
        )

    return value


def optional(name, default):
    """Return a setting, or the default if it is missing or still a placeholder.

    Used for features that are nice to have rather than required, so the bot
    still runs on a .env written before the feature existed.
    """
    value = os.environ.get(name)
    if not value or value.startswith("your-"):
        return default
    return value


GROQ_API_KEY = require("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = require("TELEGRAM_BOT_TOKEN")

# Everything in .env is text, but chat ids are numbers - convert it.
try:
    MY_CHAT_ID = int(require("MY_CHAT_ID"))
except ValueError:
    raise RuntimeError(f"MY_CHAT_ID in {ENV_FILE} must be a whole number, e.g. MY_CHAT_ID=5551234")

# Path to the Google OAuth client file, relative to the project folder.
GOOGLE_CREDENTIALS_FILE = Path(__file__).parent / require("GOOGLE_CREDENTIALS_FILE")

# --- Letting other people link their own Google account (optional) ----------
# A second OAuth client, of type "Web application", because a Desktop client
# cannot redirect to a public address. If this file is absent the feature is
# simply off and /connect falls back to manual linking by the owner.
GOOGLE_WEB_CREDENTIALS_FILE = Path(__file__).parent / optional(
    "GOOGLE_WEB_CREDENTIALS_FILE", "credentials_web.json"
)

# The address Google sends people back to. http://localhost works for testing
# on your own machine; a public deployment needs an https address.
PUBLIC_BASE_URL = optional("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

# The port the callback server listens on. Behind a reverse proxy this stays
# a plain local port while the proxy handles https on 443.
OAUTH_PORT = int(optional("OAUTH_PORT", "8000"))
