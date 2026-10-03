# OmniAgent

A personal AI assistant you talk to through Telegram. It answers questions using a
free Groq-hosted language model, can call tools (time, web search, and later your
calendar), understands voice notes, and remembers facts about you in a local SQLite
database. Everything runs on your own laptop on free services. Built step by step as
a learning project.

## Setup (Windows, PowerShell)

1. Install Python 3.11+ and Git.
2. Open a terminal in the project folder:
   ```
   cd D:\nova
   ```
3. Create and activate the virtual environment:
   ```
   py -m venv venv
   venv\Scripts\Activate.ps1
   ```
   Your prompt should now start with `(venv)`.
4. Install the libraries:
   ```
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and fill in your real keys:
   ```
   copy .env.example .env
   ```
6. Check the keys load:
   ```
   python -c "import config; print('config OK')"
   ```
