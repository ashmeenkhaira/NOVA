# Deploying NOVA to a Linux VM

Runs `bot.py` around the clock on a small free cloud VM, as a systemd service.
About an hour the first time.

**Why a VM and not Vercel/Render free tiers:** the bot polls Telegram nonstop
and keeps `memory.db` on disk. Serverless and sleeping free tiers stop the
polling and wipe the disk.

## 0. Before you start

- [ ] The bot works on your laptop, including calendar and Gmail.
- [ ] `python google_auth.py` has been run on the laptop recently - the server
      reuses that `token.json`, because it has no browser to sign in with.
- [ ] Your code is on GitHub in a **private** repository. Before every push, run
      `git status` and check that `.env`, `credentials.json`, `token.json` and
      `*.db` are NOT listed.

## 1. Create the VM

Any of these works: Oracle Cloud "Always Free", Google Cloud e2-micro (free in
some US regions), or AWS EC2 (free credits that run out). Check the provider's
current free-tier terms first.

- Image: **Ubuntu 24.04** (or the newest Ubuntu LTS offered)
- Smallest free size; 1 GB RAM is enough
- Allow SSH (port 22). No other ports are needed - polling only connects outwards.
- **Set a budget alert** (e.g. email me above $1) before creating anything.

## 2. Connect and install

```bash
ssh YOUR_USER@VM_IP_ADDRESS

sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/YOUR_GITHUB_NAME/nova.git
cd nova
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## 3. Copy the secret files (never through git)

From your **laptop**, in PowerShell, in `D:\nova`:

```powershell
scp .env credentials.json token.json YOUR_USER@VM_IP_ADDRESS:~/nova/
scp memory.db YOUR_USER@VM_IP_ADDRESS:~/nova/     # optional: keep your memories
```

On the VM, make them readable by you only:

```bash
chmod 600 ~/nova/.env ~/nova/credentials.json ~/nova/token.json
```

## 4. Stop the laptop bot

Telegram allows only one copy polling per token. Press Ctrl+C on the laptop,
or you will see `Conflict: terminated by other getUpdates request`.

## 5. Run it as a service

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

Then message the bot from your phone.

## Everyday operations

| Task | Command (on the VM) |
|---|---|
| See logs | `journalctl -u nova -f` |
| Restart | `sudo systemctl restart nova` |
| Stop | `sudo systemctl stop nova` |
| Update code | `cd ~/nova && git pull && venv/bin/pip install -r requirements.txt && sudo systemctl restart nova` |

## The weekly Google sign-in

While the Google Cloud app is in **Testing** mode, Google expires the sign-in
after 7 days. On the server, calendar and email requests then answer with
"Google sign-in needed" instead of hanging. To fix it:

```powershell
# on the laptop, in D:\nova
python google_auth.py
scp token.json YOUR_USER@VM_IP_ADDRESS:~/nova/
```

No restart needed - the next request reads the new token. (Publishing the app
to Production removes the 7-day limit, but Gmail's scopes then require Google's
app verification.)
