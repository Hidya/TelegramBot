# ==================== main.py ====================
import os
import time
import asyncio
import aiohttp
import subprocess
import json
import re
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests
from threading import Thread
import tempfile
import shutil

# Bot Configuration - Replit Environment Variables
API_ID = int(os.getenv('API_ID', '3576094'))
API_HASH = os.getenv('API_HASH', 'c3be836efce12c191d48fec44d0d99e3')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8490099725:AAHB7RzCZMCGmRd0kknZIpb078RHbf9Nm9Q')
RCLONE_REMOTE = os.getenv('RCLONE_REMOTE', 'TelegramUploads:')

# Global variables
upload_tasks = {}

class UploadProgress:
    def __init__(self, chat_id, message_id, filename, total_size=0):
        self.chat_id = chat_id
        self.message_id = message_id
        self.filename = filename
        self.total_size = total_size
        self.uploaded = 0
        self.start_time = time.time()
        self.cancelled = False
        self.file_id = None
        
    def update_progress(self, uploaded_bytes):
        self.uploaded = uploaded_bytes
        
    def get_progress_text(self):
        if self.total_size == 0:
            return f"📤 **Uploading: {self.filename}**\n\n⏳ Processing..."
            
        percentage = (self.uploaded / self.total_size) * 100
        elapsed_time = time.time() - self.start_time
        
        if elapsed_time > 0 and self.uploaded > 0:
            speed = self.uploaded / elapsed_time
            eta = (self.total_size - self.uploaded) / speed if speed > 0 else 0
            speed_text = self.format_size(speed) + "/s"
            eta_text = self.format_time(eta)
        else:
            speed_text = "Calculating..."
            eta_text = "Calculating..."
            
        progress_bar = "█" * int(percentage // 5) + "░" * (20 - int(percentage // 5))
        
        return f"""📤 **Uploading: {self.filename}**

📊 Progress: {percentage:.1f}%
{progress_bar}

📦 Size: {self.format_size(self.uploaded)} / {self.format_size(self.total_size)}
⚡ Speed: {speed_text}
⏱️ ETA: {eta_text}"""

    @staticmethod
    def format_size(bytes_size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
    
    @staticmethod
    def format_time(seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds//60)}m {int(seconds%60)}s"
        else:
            return f"{int(seconds//3600)}h {int((seconds%3600)//60)}m"

def setup_rclone():
    """Setup rclone configuration for Replit"""
    # Create rclone config directory
    config_dir = os.path.expanduser('~/.config/rclone')
    os.makedirs(config_dir, exist_ok=True)
    
    config_file = os.path.join(config_dir, 'rclone.conf')
    
    # Check if RCLONE_CONFIG environment variable exists
    rclone_config = os.getenv('RCLONE_CONFIG')
    if rclone_config:
        with open(config_file, 'w') as f:
            f.write(rclone_config)
        print("✅ Rclone config loaded from environment")
        return True
    
    # Check if config file already exists
    if os.path.exists(config_file):
        print("✅ Rclone config file found")
        return True
    
    print("❌ Rclone not configured. Please set RCLONE_CONFIG environment variable.")
    print("📝 Run 'rclone config' locally and copy the contents to RCLONE_CONFIG")
    return False

def get_cancel_keyboard(task_id):
    keyboard = [[InlineKeyboardButton("❌ Cancel Upload", callback_data=f"cancel_{task_id}")]]
    return InlineKeyboardMarkup(keyboard)

def get_file_actions_keyboard(file_id, filename):
    keyboard = [
        [
            InlineKeyboardButton("✏️ Rename", callback_data=f"rename_{file_id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{file_id}")
        ],
        [
            InlineKeyboardButton("🔗 Get Public Link", callback_data=f"public_{file_id}"),
            InlineKeyboardButton("🔒 Get Private Link", callback_data=f"private_{file_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = f"""🎉 **Welcome to Google Drive Upload Bot!**

🚀 **Bot Status:** Online & Ready (Replit Hosted)
📤 **Upload Destination:** {RCLONE_REMOTE}

✅ **Available Features:**
• Upload files & links to Google Drive
• Preserve original filenames  
• Real-time progress with speed & ETA
• Cancel uploads anytime
• Rename files after upload
• Delete files from Drive
• Public/Private link sharing toggle
• Support for forwarded files

📋 **Commands:**
/start - Show this message
/help - Get detailed help
/status - Check bot status
/config - Configure rclone (if needed)

🚀 **Just send me a file or link to get started!**

Made with ❤️ for seamless Drive uploads on Replit"""
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config_text = """🔧 **Rclone Configuration Help**

To configure Google Drive access:

1. **Set Environment Variable:**
   - Go to Replit's "Secrets" tab (🔒 icon)
   - Add key: `RCLONE_CONFIG`
   - Add value: Your rclone.conf content

2. **Get rclone.conf content:**
   - Run `rclone config` locally
   - Choose Google Drive
   - Name it "TelegramUploads"
   - Complete authentication
   - Copy ~/.config/rclone/rclone.conf content

3. **Alternative - Direct setup:**
   - Open Replit Shell
   - Run: `rclone config`
   - Follow Google Drive setup
   - Restart the bot

**Current Status:**"""
    
    # Check rclone status
    config_exists = setup_rclone()
    if config_exists:
        config_text += "\n✅ Rclone configured and ready!"
    else:
        config_text += "\n❌ Rclone not configured yet."
    
    await update.message.reply_text(config_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"""📖 **Detailed Usage Guide (Replit Edition):**

🔰 **Getting Started:**
1. Configure rclone using /config command
2. Send any file or link - no additional setup required!

📁 **Supported Content:**
• Documents, images, videos, audio
• Direct download links
• Forwarded files from any chat
• Files up to 2GB (Telegram limit)

⚡ **During Upload:**
• Real-time progress tracking
• Speed and ETA calculation
• Cancel button to stop anytime

🛠️ **After Upload:**
• Rename files easily
• Delete unwanted files
• Get shareable public links
• Generate private access links

🔧 **Replit Specific:**
• Files uploaded to: {RCLONE_REMOTE}
• Bot runs 24/7 on Replit
• Automatic dependency management
• Environment variables in Secrets

❓ **Support:** Use /config for setup help"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_uploads = len(upload_tasks)
    
    # Check rclone status
    try:
        result = subprocess.run(['rclone', 'version'], capture_output=True, text=True, timeout=5)
        rclone_status = "✅ Working" if result.returncode == 0 else "❌ Error"
        rclone_version = result.stdout.split('\n')[0] if result.returncode == 0 else "Unknown"
    except:
        rclone_status = "❌ Not found"
        rclone_version = "Not installed"
    
    config_status = "✅ Configured" if setup_rclone() else "❌ Not configured"
    
    status_text = f"""📊 **Bot Status (Replit):**

🟢 **Status:** Online & Ready
📤 **Active Uploads:** {active_uploads}
🔧 **Rclone Remote:** {RCLONE_REMOTE}
⚙️ **Rclone Status:** {rclone_status}
📝 **Config Status:** {config_status}
🐍 **Python:** Available
🕐 **Last updated:** {time.strftime('%Y-%m-%d %H:%M:%S')}

💾 **Storage:** Google Drive
🌐 **Platform:** Replit Cloud
🔒 **Environment:** Variables loaded from Secrets

Use /config if you need setup help!"""
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

def extract_filename_from_url(url):
    """Extract filename from URL"""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    if not filename or filename == '/':
        filename = f"downloaded_file_{int(time.time())}"
    return filename

def is_valid_url(url):
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

async def download_file_from_url(url, filename, progress_callback=None):
    """Download file from URL with progress tracking"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=3600)) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                    
                total_size = int(response.headers.get('content-length', 0))
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}")
                downloaded = 0
                
                async for chunk in response.content.iter_chunked(8192):
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        progress_callback(downloaded, total_size)
                
                temp_file.close()
                return temp_file.name, total_size
    except Exception as e:
        print(f"Download error: {e}")
        return None

def rclone_upload(local_path, remote_path, progress_callback=None):
    """Upload file using rclone with progress"""
    try:
        remote_file = f"{RCLONE_REMOTE}{remote_path}{os.path.basename(local_path)}"
        
        cmd = [
            'rclone', 'copy', local_path, f"{RCLONE_REMOTE}{remote_path}",
            '--progress', '--stats', '1s', '--transfers', '1'
        ]
        
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            text=True, universal_newlines=True
        )
        
        file_size = os.path.getsize(local_path)
        
        while True:
            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            if output and progress_callback:
                # Simple progress estimation
                try:
                    if "%" in output:
                        percent_match = re.search(r'(\d+)%', output)
                        if percent_match:
                            percent = int(percent_match.group(1))
                            uploaded = (percent / 100) * file_size
                            progress_callback(int(uploaded))
                except:
                    pass
        
        return_code = process.poll()
        return return_code == 0
        
    except Exception as e:
        print(f"Rclone upload error: {e}")
        return False

def rclone_delete(filename):
    """Delete file from rclone remote"""
    try:
        cmd = ['rclone', 'delete', f"{RCLONE_REMOTE}{filename}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except:
        return False

def rclone_get_link(filename, public=True):
    """Get shareable link from rclone"""
    try:
        cmd = ['rclone', 'link', f"{RCLONE_REMOTE}{filename}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads from Telegram"""
    # Check if rclone is configured
    if not setup_rclone():
        await update.message.reply_text("❌ **Rclone not configured!**\n\nPlease use /config command to set up Google Drive access first.", parse_mode='Markdown')
        return
    
    message = update.message
    
    if message.document:
        file_obj = message.document
        filename = file_obj.file_name or f"document_{int(time.time())}"
        file_size = file_obj.file_size
    elif message.photo:
        file_obj = message.photo[-1]  # Get highest resolution
        filename = f"photo_{int(time.time())}.jpg"
        file_size = file_obj.file_size
    elif message.video:
        file_obj = message.video
        filename = file_obj.file_name or f"video_{int(time.time())}.mp4"
        file_size = file_obj.file_size
    elif message.audio:
        file_obj = message.audio
        filename = file_obj.file_name or f"audio_{int(time.time())}.mp3"
        file_size = file_obj.file_size
    else:
        await message.reply_text("❌ Unsupported file type!")
        return
    
    # Create progress tracker
    progress_msg = await message.reply_text("📤 Starting upload...", parse_mode='Markdown')
    task_id = f"{message.chat.id}_{progress_msg.message_id}"
    
    progress = UploadProgress(message.chat.id, progress_msg.message_id, filename, file_size)
    upload_tasks[task_id] = progress
    
    try:
        # Download file from Telegram
        file = await context.bot.get_file(file_obj.file_id)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}")
        await file.download_to_drive(temp_file.name)
        temp_file.close()
        
        # Start upload in background
        upload_thread = Thread(
            target=background_upload,
            args=(temp_file.name, filename, task_id, context, progress_msg)
        )
        upload_thread.start()
        
        # Update progress display
        await update_progress_display(task_id, context)
        
    except Exception as e:
        await progress_msg.edit_text(f"❌ Upload failed: {str(e)}")
        if task_id in upload_tasks:
            del upload_tasks[task_id]

async def handle_link_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle URL/link uploads"""
    # Check if rclone is configured
    if not setup_rclone():
        await update.message.reply_text("❌ **Rclone not configured!**\n\nPlease use /config command to set up Google Drive access first.", parse_mode='Markdown')
        return
    
    url = update.message.text.strip()
    
    if not is_valid_url(url):
        await update.message.reply_text("❌ Invalid URL provided!")
        return
    
    filename = extract_filename_from_url(url)
    
    progress_msg = await update.message.reply_text("📥 Downloading from link...", parse_mode='Markdown')
    task_id = f"{update.message.chat.id}_{progress_msg.message_id}"
    
    progress = UploadProgress(update.message.chat.id, progress_msg.message_id, filename)
    upload_tasks[task_id] = progress
    
    try:
        # Download from URL
        def download_progress(downloaded, total):
            if task_id in upload_tasks and not upload_tasks[task_id].cancelled:
                upload_tasks[task_id].total_size = total
                upload_tasks[task_id].update_progress(downloaded)
        
        result = await download_file_from_url(url, filename, download_progress)
        if not result:
            await progress_msg.edit_text("❌ Failed to download from URL!")
            del upload_tasks[task_id]
            return
        
        temp_file_path, file_size = result
        upload_tasks[task_id].total_size = file_size
        
        # Start upload
        upload_thread = Thread(
            target=background_upload,
            args=(temp_file_path, filename, task_id, context, progress_msg)
        )
        upload_thread.start()
        
        await update_progress_display(task_id, context)
        
    except Exception as e:
        await progress_msg.edit_text(f"❌ Download failed: {str(e)}")
        if task_id in upload_tasks:
            del upload_tasks[task_id]

def background_upload(temp_file_path, filename, task_id, context, progress_msg):
    """Background upload function"""
    try:
        if task_id not in upload_tasks or upload_tasks[task_id].cancelled:
            return
        
        def upload_progress(uploaded):
            if task_id in upload_tasks:
                upload_tasks[task_id].update_progress(uploaded)
        
        # Upload to Drive
        success = rclone_upload(temp_file_path, "", upload_progress)
        
        if success and task_id in upload_tasks and not upload_tasks[task_id].cancelled:
            upload_tasks[task_id].file_id = filename
            asyncio.run_coroutine_threadsafe(
                upload_complete(filename, task_id, context, progress_msg),
                context.application.loop
            )
        else:
            asyncio.run_coroutine_threadsafe(
                progress_msg.edit_text("❌ Upload failed! Check rclone configuration."),
                context.application.loop
            )
        
        # Cleanup
        try:
            os.unlink(temp_file_path)
        except:
            pass
            
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            progress_msg.edit_text(f"❌ Upload error: {str(e)}"),
            context.application.loop
        )
    finally:
        if task_id in upload_tasks:
            del upload_tasks[task_id]

async def upload_complete(filename, task_id, context, progress_msg):
    """Handle upload completion"""
    success_text = f"""✅ **Upload Successful!**

📁 **File:** {filename}
📤 **Uploaded to:** {RCLONE_REMOTE}
⏰ **Completed:** {time.strftime('%H:%M:%S')}
🌐 **Platform:** Replit

What would you like to do next?"""
    
    keyboard = get_file_actions_keyboard(filename, filename)
    await progress_msg.edit_text(success_text, reply_markup=keyboard, parse_mode='Markdown')

async def update_progress_display(task_id, context):
    """Update progress display periodically"""
    while task_id in upload_tasks:
        progress = upload_tasks[task_id]
        if progress.cancelled:
            break
            
        try:
            keyboard = get_cancel_keyboard(task_id)
            await context.bot.edit_message_text(
                chat_id=progress.chat_id,
                message_id=progress.message_id,
                text=progress.get_progress_text(),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except:
            pass
        
        await asyncio.sleep(2)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("cancel_"):
        task_id = data.replace("cancel_", "")
        if task_id in upload_tasks:
            upload_tasks[task_id].cancelled = True
            await query.edit_message_text("❌ Upload cancelled by user!")
            del upload_tasks[task_id]
    
    elif data.startswith("rename_"):
        filename = data.replace("rename_", "")
        context.user_data['rename_file'] = filename
        await query.edit_message_text("✏️ **Rename File**\n\nSend me the new filename:", parse_mode='Markdown')
    
    elif data.startswith("delete_"):
        filename = data.replace("delete_", "")
        success = rclone_delete(filename)
        if success:
            await query.edit_message_text(f"🗑️ **File Deleted**\n\n{filename} has been removed from Drive.")
        else:
            await query.edit_message_text("❌ Failed to delete file!")
    
    elif data.startswith("public_"):
        filename = data.replace("public_",
