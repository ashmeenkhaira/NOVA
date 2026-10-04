# Deploying NOVA to Google Cloud (free e2-micro VM)

Runs `bot.py` around the clock on Google Cloud's always-free e2-micro VM, as a
systemd service. About an hour the first time. Everything happens in the
browser - no extra tools to install on your laptop.

**Why a VM and not Vercel/Render free tiers:** the bot polls Telegram nonstop
and keeps `memory.db` on disk. Serverless and sleeping free tiers stop the
polling and wipe the disk.

## 0. Before you start

- [ ] The bot works on your laptop, including calendar and Gmail.
- [ ] You ran `python google_auth.py` on the laptop recently. The server reuses
      that `token.json`, because it has no browser to sign in with.
- [ ] Everything is committed (`git status` shows nothing).

## 1. Put the code on GitHub (private)

1. On github.com: **New repository** → name `nova` → **Private** → don't add a
   README → **Create**.
2. On your laptop, in `D:\nova`:

   ```powershell
   git status          # .env, credentials.json, token.json, memory.db must NOT be listed
   git remote add origin https://github.com/YOUR_GITHUB_NAME/nova.git
   git push -u origin main
   ```
3. Make a **read-only key** so the server can download the code: GitHub →
   Settings → Developer settings → **Fine-grained personal access tokens** →
   Generate. Repository access: **only `nova`**. Permissions: **Contents: Read-only**.
   Copy the token (starts with `github_pat_`) - you need it once, in step 5.

## 2. Turn on a budget alert (do this first)

Creating a VM needs a billing account (a card), even for the free one.

1. Console → search **Billing** → link or create a billing account for the
   OmniAgent project.
2. Billing → **Budgets & alerts** → **Create budget** → amount **$1** → alerts at
   50% / 90% / 100% → email to you.

If you ever get an email, something is outside the free tier - check it the same day.

## 3. Create the VM

Console → search **Compute Engine** → **Enable** the API (first time only) →
**VM instances** → **Create instance**:

| Setting | Choose | Why |
|---|---|---|
| Name | `nova` | |
| Region | **us-central1 (Iowa)**, us-west1 or us-east1 | the free tier only applies in these three |
| Machine type | E2 → **e2-micro** | the free size |
| Boot disk → Change | **Ubuntu 24.04 LTS (x86/64)** | |
| Boot disk type | **Standard persistent disk**, 30 GB | the default "Balanced" disk is **not** free |
| Firewall | leave HTTP / HTTPS **unticked** | the bot only connects outwards |

Click **Create**. The cost estimate on the page may not show the free-tier
discount - your budget alert is the real check.

## 4. Connect

In the VM list, click **SSH** next to `nova`. A terminal opens in your browser -
you are now typing on the server.

## 5. Install

In the browser SSH window:

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://YOUR_GITHUB_NAME:YOUR_TOKEN@github.com/YOUR_GITHUB_NAME/nova.git
cd nova
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

(Replace `YOUR_TOKEN` with the `github_pat_...` token from step 1. It stays saved
in `~/nova/.git/config` so `git pull` keeps working - acceptable because it can
only read this one repo, and you can revoke it on GitHub at any time.)

## 6. Upload the secret files (never through git)

In the SSH window, click **Upload file** (top right) and upload these from
`D:\nova`, one at a time: `.env`, `credentials.json`, `token.json`, and
optionally `memory.db` to keep your memories. They land in your home folder;
move them into the project and lock them down:

```bash
mv ~/.env ~/credentials.json ~/token.json ~/nova/
mv ~/memory.db ~/nova/ 2>/dev/null    # only if you uploaded it
chmod 600 ~/nova/.env ~/nova/credentials.json ~/nova/token.json
```

Windows hides files starting with a dot in some upload dialogs - if `.env` is
not shown, type its full path `D:\nova\.env` into the file name box.

## 7. Stop the laptop bot

Telegram allows only one copy polling per token. Press Ctrl+C on the laptop,
or you will see `Conflict: terminated by other getUpdates request`.

## 8. Run it as a service

The service file sets the bot's timezone to India (`TZ=Asia/Kolkata`) because
cloud servers run on UTC - edit `deploy/nova.service` first if you are elsewhere.

```bash
cd ~/nova
sed -i "s/YOUR_USER/$(whoami)/g" deploy/nova.service
sudo cp deploy/nova.service /etc/systemd/system/nova.service
sudo systemctl daemon-reload
sudo systemctl enable --now nova
```

Check it:

```bash
systemctl status nova        # should say "active (running)"
journalctl -u nova -f        # live logs - message the bot and watch (Ctrl+C to stop)
```

Then message the bot from your phone, and ask "what time is it?" to confirm the timezone.

## Everyday operations

| Task | Command (in the SSH window) |
|---|---|
| See logs | `journalctl -u nova -f` |
| Restart | `sudo systemctl restart nova` |
| Stop | `sudo systemctl stop nova` |
| Update code | `cd ~/nova && git pull && venv/bin/pip install -r requirements.txt && sudo systemctl restart nova` |

## The weekly Google sign-in

While the Google Cloud app is in **Testing** mode, Google expires the sign-in
after 7 days. On the server, calendar and email requests then answer with
"Google sign-in needed" instead of hanging. To fix it:

1. On the laptop, in `D:\nova`: `python google_auth.py`
2. In the VM's SSH window: **Upload file** → `token.json`, then
   `mv ~/token.json ~/nova/ && chmod 600 ~/nova/token.json`

No restart needed - the next request reads the new token. (Publishing the app
to Production removes the 7-day limit, but Gmail's scopes then require Google's
app verification.)
