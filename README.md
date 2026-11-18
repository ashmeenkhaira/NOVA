# NOVA

A personal AI assistant on Telegram that can search the web, remember facts about
you, read and add to your Google Calendar, and read your Gmail and write drafts.
The agent loop, tools, memory and safety layer are written from scratch in Python,
with no agent framework. Everything runs on free services.

## What it can do

| Ask NOVA... | What happens |
|---|---|
| "What's the latest news on the IPL?" | searches the web (DuckDuckGo) |
| "I'm preparing for AI engineer interviews." | decides on its own to save that fact, and remembers it after restarts |
| "What do I have tomorrow?" | reads your Google Calendar |
| "Add gym tomorrow at 7am" | **proposes** the event. Nothing is created until you reply `yes`. |
| "Any unread emails from today?" | searches Gmail and reads emails |
| "Draft a reply saying I'll be late" | saves a draft in Gmail. It never sends. |

Telegram commands: `/connect` links a Google account to the chat and `/disconnect`
unlinks it, `/memories` lists stored facts, `/forget <n>` deletes one, and `/reset`
clears the conversation.

## How it works

```
Telegram ──▶ bot.py ──▶ agent.py: run_agent()  ◀── the agent loop
 (polling)   per-chat      │  system prompt + remembered facts + history
             history       │  ──▶ Groq (gpt-oss-120b, OpenAI-compatible API)
             approvals     │  ◀── the model asks for tools
                           ▼
                        tools.py: registry ──▶ memory.py (SQLite)
                                           ──▶ gcal.py / gmail.py ──▶ google_auth.py (OAuth)
                                           ──▶ ddgs (web search)
                                           ──▶ approvals.py (write actions wait for "yes")

/connect ──▶ links.py (single-use state) ──▶ Google ──▶ webapp.py (callback)
                                                         └─▶ tokens.py (one token per chat)

mcp_server.py ──▶ the same tools.py registry, served over MCP to other agents
```

- **The agent loop** (`agent.py`): send the conversation plus a menu of tools. While
  the model asks for tool calls, run them and send the results back, up to 5 round trips.
- **The tool registry** (`tools.py`): each tool is a Python function plus a JSON
  schema in one dictionary. Adding a tool never touches the loop.
- **Memory:** short-term memory is the per-chat history, trimmed to 20 messages.
  Long-term memory is facts in SQLite, saved by the model itself through
  `remember_fact` and loaded into the system prompt on every message.
- **Linking a Google account** (`links.py`, `webapp.py`, `tokens.py`): `/connect` mints a
  random single-use `state` that expires in 10 minutes and sends back a Google sign-in
  link. Google redirects to a small callback server, which checks the `state` to learn
  which chat asked, swaps the code for a token, and stores it against that chat. Each
  chat therefore uses its own Google account.
- **MCP** (`mcp_server.py`): the same registry is exposed as an MCP server, so
  Claude Code or any MCP client can use NOVA's tools.

## Security design

Agents that can act on your accounts need guarantees enforced in code, not just
instructions in a prompt:

- **Write actions need approval enforced in code.** `create_event` never touches
  Google. It stores a pending action, and the bot shows a code-written description
  (`⚠️ Waiting for approval: ...`). The action runs only if your next message is
  exactly `yes`. The model takes no part in the approval. In testing, the model's
  own chat reply once got the year wrong, while the code-written approval line was
  correct.
- **The model never chooses whose data it touches.** `chat_id` comes from Telegram
  and is injected by `run_tool`. If the model supplies its own `chat_id`, it is
  overwritten.
- **Access follows the linked account, not ownership.** Every calendar and Gmail tool acts as
  the Google account linked to the asking chat, and refuses any chat that has linked none.
  Owning the bot grants no access to anyone else's data, and the owner is not special either.
- **Prompt-injection defence in layers:** email content is labelled as untrusted
  third-party text, and anything an injected instruction could trigger still needs
  your `yes`. In testing, a planted instruction in an email was ignored.
- **Least privilege:** `gmail.readonly` for reading, and drafts are never sent
  (there is no send code path). Calendar scope is limited to events.
- **Secrets never reach git:** keys live in `.env`, loaded by `config.py`.
  `credentials.json`, `credentials_web.json`, `token.json` and `*.db` are all in
  `.gitignore`.

## Project layout

| File | Job |
|---|---|
| `bot.py` | Telegram front end: polling, per-chat history, commands, approvals |
| `agent.py` | the agent loop, plus a terminal chat (`python agent.py`) |
| `tools.py` | tool functions and the registry |
| `approvals.py` | the confirmation step for write actions |
| `memory.py` | SQLite store of facts per chat |
| `tokens.py` | SQLite store of one Google token per chat |
| `google_auth.py` | Google OAuth: scopes, token refresh, both sign-in flows |
| `links.py` | single-use, expiring `state` values for `/connect` |
| `webapp.py` | the callback page Google redirects to after sign-in |
| `gcal.py` / `gmail.py` | Google Calendar and Gmail API calls |
| `mcp_server.py` | the tools as an MCP server |
| `config.py` | loads and validates `.env` |
| `tests/` | 54 offline tests (`python -m pytest`) |
| `deploy/` | systemd service and VM guide |

## Setup (Windows, PowerShell)

```powershell
py -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env      # then fill in the values (see comments inside)
```

You need:
- a **Groq** API key (console.groq.com, free)
- a **Telegram bot token** (@BotFather)
- your **Telegram chat id** (run the bot, message it, read the `[debug]` line)

**Google (calendar and Gmail):** in Google Cloud Console, create a project and
enable the Calendar API and the Gmail API. Configure the OAuth consent screen as
External / Testing, and add yourself as a test user. Create a **Desktop app**
client, download its JSON as `credentials.json` into this folder, then sign in once:

```powershell
python google_auth.py             # links the owner's chat
python google_auth.py 5551234     # links someone else's chat id, by hand
```

**Letting other people link their own account (optional):** `/connect` needs a second
OAuth client, of type **Web application**, because a Desktop client can only redirect to
`localhost`. Register `<your public address>/connected` as its redirect URI, save its JSON
as `credentials_web.json`, and set `PUBLIC_BASE_URL` in `.env`. Without that file the
feature is simply off, and `/connect` falls back to asking the owner to link by hand.

## Running

```powershell
python bot.py          # the Telegram bot
python agent.py        # chat in the terminal (shares memory with your Telegram chat)
python -m pytest       # run the tests (no network, no real data)
```

To use NOVA's tools from Claude Code over MCP:

```powershell
claude mcp add nova -- D:\nova\venv\Scripts\python.exe D:\nova\mcp_server.py
```

## Deployment

See [deploy/DEPLOY.md](deploy/DEPLOY.md): it runs on a free Linux VM as a systemd
service. On the server, an expired Google sign-in reports a clear error instead of
waiting for a browser.

## Known limitations

- Google sign-in expires every 7 days while the Cloud app is in Testing mode.
- Every saved fact is sent with every message. This is fine for hundreds of facts;
  beyond that, it needs semantic search (embeddings).
- Conversation history, pending approvals and half-finished `/connect` links are held in
  memory, so a restart clears them. Facts and Google tokens are kept on disk.
- Google tokens are stored as plain text, like the facts. That is acceptable while only the
  owner connects, on a machine only they can reach; the column needs encrypting before
  other people link their own accounts from their own devices.
- Only one write action can wait for approval per chat at a time, and it never expires.
- Text only: there are no voice notes.
