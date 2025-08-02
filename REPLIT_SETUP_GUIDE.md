# 🚀 Replit Setup Guide - Telegram Drive Bot

## Step 1: Create Files

Create these files in your Replit project:

1. **main.py** - Bot main code (rename from bot.py)
2. **requirements.txt** - Python dependencies
3. **replit.nix** - System dependencies
4. **.replit** - Replit configuration
5. **pyproject.toml** - Project configuration

## Step 2: Environment Variables (Secrets)

Go to Replit's **Secrets** tab (🔒 icon in sidebar) and add:

```
BOT_TOKEN = 8490099725:AAHB7RzCZMCGmRd0kknZIpb078RHbf9Nm9Q
API_ID = 3576094
API_HASH = c3be836efce12c191d48fec44d0d99e3
RCLONE_REMOTE = TelegramUploads:
RCLONE_CONFIG = [Your rclone config content - see below]
```

## Step 3: Get RCLONE_CONFIG Content

### Method 1: Local Computer
1. Install rclone locally: `curl https://rclone.org/install.sh | bash`
2. Run: `rclone config`
3. Choose Google Drive
4. Name it "TelegramUploads"
5. Complete authentication
6. Copy content from `~/.config/rclone/rclone.conf`
7. Paste in RCLONE_CONFIG secret

### Method 2: Replit Shell
1. Open Replit Shell tab
2. Run: `rclone config`
3. Follow Google Drive setup
4. Copy config content: `cat ~/.config/rclone/rclone.conf`
5. Add to RCLONE_CONFIG secret

## Step 4: Run the Bot

1. Click **Run** button in Replit
2. Bot will start automatically
3. Check console for status messages
4. Bot will be live 24/7 on Replit!

## Troubleshooting

### Bot Not Starting?
- Check all files are created correctly
- Verify all secrets are set
- Check console for error messages

### Rclone Errors?
- Use `/config` command in bot
- Check RCLONE_CONFIG secret is set
- Verify Google Drive authentication

### Upload Failures?
- Use `/status` command to check rclone
- Ensure Google Drive has space
- Check internet connectivity

## Features

✅ **Real-time progress tracking**
✅ **Cancel uploads anytime**  
✅ **File renaming**
✅ **Public/Private links**
✅ **Delete from Drive**
✅ **24/7 uptime on Replit**
✅ **Keep-alive web server**

## Commands

- `/start` - Welcome message
- `/help` - Detailed help
- `/status` - Bot status
- `/config` - Rclone setup help

## Support

If you face issues:
1. Check console logs
2. Verify all secrets are set
3. Use `/status` command
4. Use `/config` for rclone help

---
🎉 **Your bot is now ready for Replit deployment!**
