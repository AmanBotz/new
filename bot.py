import os
import tempfile
import threading
import logging

import m3u8
import requests
from Crypto.Cipher import AES
from urllib.parse import urljoin

from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

# Set up logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve Telegram credentials from environment variables.
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

if not all([TG_API_ID, TG_API_HASH, TG_BOT_TOKEN]):
    logger.error("TG_API_ID, TG_API_HASH, and TG_BOT_TOKEN must be set!")
    exit(1)

#####################################
# Health Check Web Server (Flask)
#####################################

app = Flask(__name__)

@app.route("/")
def health():
    return "OK", 200

def run_health_server():
    app.run(host="0.0.0.0", port=8000)

#####################################
# Download & Decrypt Function using m3u8, requests, and AES
#####################################

def download_and_decrypt_m3u8(m3u8_url: str, output_path: str) -> bool:
    """
    Loads the m3u8 manifest, downloads each TS segment,
    decrypts it if a key is specified, and writes the data to output_path.
    Returns True on success, False on failure.
    """
    try:
        playlist = m3u8.load(m3u8_url)
    except Exception as e:
        logger.error("Error loading m3u8: %s", str(e))
        return False

    key = None
    iv = None
    if playlist.keys and playlist.keys[0] and playlist.keys[0].uri:
        key_url = urljoin(m3u8_url, playlist.keys[0].uri)
        key_response = requests.get(key_url)
        if key_response.status_code != 200:
            logger.error("Failed to retrieve key from %s", key_url)
            return False
        key = key_response.content
        if playlist.keys[0].iv:
            iv = bytes.fromhex(playlist.keys[0].iv.replace("0x", ""))
        else:
            iv = b'\x00' * 16  # Default IV if not specified

    with open(output_path, "wb") as out_file:
        for segment in playlist.segments:
            seg_url = urljoin(m3u8_url, segment.uri)
            seg_response = requests.get(seg_url)
            if seg_response.status_code != 200:
                logger.error("Failed to download segment: %s", seg_url)
                return False
            seg_data = seg_response.content
            if key:
                try:
                    cipher = AES.new(key, AES.MODE_CBC, iv)
                    seg_data = cipher.decrypt(seg_data)
                except Exception as e:
                    logger.error("Decryption error for segment %s: %s", seg_url, str(e))
                    return False
            out_file.write(seg_data)
    return True

#####################################
# Telegram Bot Setup (Pyrogram)
#####################################

bot = Client(
    "m3u8_bot",
    api_id=int(TG_API_ID),
    api_hash=TG_API_HASH,
    bot_token=TG_BOT_TOKEN
)

@bot.on_message(filters.command("start"))
def start_handler(client: Client, message: Message):
    message.reply_text(
        "Hello! I can download HLS streams (m3u8 URLs) for you.\n"
        "Usage: /download <m3u8 URL>\n"
        "Example:\n/download https://your-stream.example.com/your.m3u8"
    )

@bot.on_message(filters.command("download"))
def download_handler(client: Client, message: Message):
    if len(message.command) < 2:
        message.reply_text("Usage: /download <m3u8 URL>")
        return

    m3u8_url = message.command[1].strip()
    message.reply_text("Downloading your video. This may take a few minutes...")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ts") as temp_out:
        output_file = temp_out.name

    logger.info("Temporary output file created: %s", output_file)

    if download_and_decrypt_m3u8(m3u8_url, output_file):
        try:
            message.reply_document(document=output_file, caption="Here is your video!")
            logger.info("Video sent successfully.")
        except Exception as e:
            logger.error("Error sending video: %s", str(e))
            message.reply_text("Error sending the video file.")
    else:
        message.reply_text("Failed to download the video. It may be DRM-protected or require extra authentication.")

    try:
        os.remove(output_file)
        logger.info("Temporary file removed.")
    except Exception as e:
        logger.warning("Error removing temporary file: %s", str(e))

#####################################
# Main Entrypoint
#####################################

def main():
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health server started on port 8000.")
    logger.info("Starting Telegram bot...")
    bot.run()

if __name__ == "__main__":
    main()
