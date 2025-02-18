import os
import requests
import time
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import Message

# Fetch environment variables
API_ID = int(os.getenv("API_ID"))  # API_ID is an integer
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Create Pyrogram Client
bot = Client("video_converter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store user session data (to track video URL)
user_data = {}

async def download_file(url, filename, message):
    """Download file with progress updates"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0
    start_time = time.time()

    with open(filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)

                elapsed_time = time.time() - start_time
                speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                eta = (total_size - downloaded) / speed if speed > 0 else 0

                progress_msg = (
                    f"📥 **Downloading video:** `{filename}`\n"
                    f"📦 **Size:** `{downloaded / 1024 / 1024:.2f} MB / {total_size / 1024 / 1024:.2f} MB`\n"
                    f"⚡ **Speed:** `{speed / 1024 / 1024:.2f} MB/s`\n"
                    f"⏳ **ETA:** `{eta:.2f} sec`"
                )
                await message.edit_text(progress_msg)

    return filename

@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply("👋 Send me a **video link** and I'll download and convert it to MP4!")

@bot.on_message(filters.text)
async def handle_video(_, message):
    user_id = message.from_user.id
    video_url = message.text.strip()

    if video_url.startswith("http"):
        user_data[user_id] = {"video_url": video_url}

        await message.reply("✅ **Video URL saved!** Downloading and converting now...")
        await convert_video(message)
    else:
        await message.reply("❌ Invalid URL. Please send a valid **video URL**.")

async def convert_video(message):
    """Download and convert video to MP4"""
    user_id = message.from_user.id
    video_url = user_data[user_id]["video_url"]

    video_file = f"video_{user_id}.ts"
    output_file = f"video_{user_id}.mp4"

    status_msg = await message.reply("⏳ **Downloading video...**")
    await download_file(video_url, video_file, status_msg)

    await message.reply("🎥 **Converting to MP4...**")
    
    # Convert the downloaded video to MP4 using ffmpeg
    ffmpeg.input(video_file).output(output_file, vcodec="copy", acodec="aac").run(overwrite_output=True)

    # Send back the converted MP4 video
    await message.reply_document(output_file, caption="✅ **Here is your converted MP4 video!**")

    # Clean up
    os.remove(video_file)
    os.remove(output_file)

    # Reset user session
    del user_data[user_id]

# Start bot
bot.run()
