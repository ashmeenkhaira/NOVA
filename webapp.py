"""The page Google sends people back to after they approve access.

The flow, end to end:

  1. /connect in Telegram  -> links.create() makes a random state
  2. the user taps the link -> Google's consent screen
  3. they press Allow       -> Google redirects their browser here, carrying
                               "code" (one-time) and "state" (ours)
  4. this file              -> checks the state, swaps the code for a token,
                               saves it against the right chat, shows a page

Serves plain HTTP on 127.0.0.1 only. In a public deployment a reverse proxy
terminates https in front of it, so nothing here deals with certificates.

Run it on its own to test the page:  python webapp.py
"""
import html
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import config
import google_auth
import links
import tokens

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOVA</title><style>
body{{font-family:system-ui,sans-serif;margin:0;display:grid;place-items:center;
min-height:100vh;background:#f5f7fa;color:#1a2230;padding:16px}}
.card{{background:#fff;padding:32px;border-radius:12px;max-width:420px;
box-shadow:0 2px 16px rgba(0,0,0,.08);text-align:center}}
h1{{margin:0 0 12px;font-size:1.4rem}} p{{margin:0;line-height:1.5;color:#55607a}}
</style></head>
<body><div class="card"><h1>{title}</h1><p>{message}</p></div></body></html>"""


def handle_callback(query):
    """Decide what one callback means. Returns (title, message).

    Separated from the HTTP plumbing so it can be tested without a browser.
    """
    def first(name):
        return (query.get(name) or [""])[0]

    # The user pressed Cancel, or Google refused.
    if first("error"):
        return "Not connected", f"Google reported: {first('error')}. You can close this tab."

    # claim() removes the state, so this URL cannot be used twice.
    chat_id = links.claim(first("state"))
    if chat_id is None:
        return "Link expired", "That link has already been used or has timed out. Send /connect in Telegram for a new one."

    try:
        creds = google_auth.exchange_code(first("state"), first("code"))
    except Exception as error:
        print(f"[error] token exchange failed: {error!r}")
        return "Something went wrong", "Could not finish linking. Send /connect in Telegram to try again."

    tokens.save_token(chat_id, creds.to_json())
    print(f"[debug] linked a Google account for chat {chat_id}")
    return "Connected", "NOVA can now use your Google account. You can close this tab and go back to Telegram."


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != google_auth.CALLBACK_PATH:
            self.send_error(404)
            return

        title, message = handle_callback(parse_qs(parsed.query))
        # escape() because anything from the query string is outside our
        # control and must never be dropped into HTML as-is.
        body = PAGE.format(title=html.escape(title), message=html.escape(message)).encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        """Quieter than the default, and never prints the query string."""
        print(f"[debug] callback server: {self.command} {urlparse(self.path).path}")


def start_in_background():
    """Run the callback server in a thread beside the bot. Returns the server."""
    server = ThreadingHTTPServer(("127.0.0.1", config.OAUTH_PORT), Handler)
    # daemon=True so Ctrl+C on the bot does not leave this thread running.
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[debug] callback server listening on 127.0.0.1:{config.OAUTH_PORT}, "
          f"expecting {config.PUBLIC_BASE_URL}{google_auth.CALLBACK_PATH}")
    return server


if __name__ == "__main__":
    start_in_background()
    print("Serving. Press Ctrl+C to stop.")
    threading.Event().wait()
