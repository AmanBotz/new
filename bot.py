import os
import subprocess
import tempfile
import threading
import logging

from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

# Configure logging
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
    # Run Flask on 0.0.0.0:8000 for health checks.
    app.run(host="0.0.0.0", port=8000)

#####################################
# FFmpeg Download Function
#####################################

def download_m3u8_stream(m3u8_url: str, output_path: str) -> bool:
    """
    Download an HLS stream using FFmpeg.
    Adds a User-Agent header to mimic a browser.
    Returns True if successful, else False.
    """
    # Use a common browser User-Agent.
    headers = "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36\r\n"

    # Build the FFmpeg command:
    cmd = [
        "ffmpeg",
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
        "-headers", headers,
        "-i", m3u8_url,
        "-c", "copy",
        "-y",  # overwrite existing file if any
        output_path
    ]
    logger.info("Executing FFmpeg command: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("FFmpeg finished successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg error: %s", e.stderr.decode())
        return False

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
        "Example:\n/download https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
    )

@bot.on_message(filters.command("download"))
def download_handler(client: Client, message: Message):
    if len(message.command) < 2:
        message.reply_text("Please provide a valid m3u8 URL.\nUsage: /download <m3u8 URL>")
        return

    m3u8_url = message.command[1].strip()
    message.reply_text("Downloading your video. This may take a few minutes...")

    # Create a temporary file to store the downloaded video.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_out:
        output_file = temp_out.name

    logger.info("Temporary output file: %s", output_file)

    # Download the stream.
    if download_m3u8_stream(m3u8_url, output_file):
        try:
            message.reply_document(document=output_file, caption="Here is your video!")
            logger.info("Video sent successfully.")
        except Exception as e:
            logger.error("Error sending video: %s", str(e))
            message.reply_text("Error sending the video file.")
    else:
        message.reply_text("Failed to download the video. Please check the URL and try again.")

    # Clean up the temporary file.
    try:
        os.remove(output_file)
        logger.info("Temporary file removed.")
    except Exception as e:
        logger.warning("Error removing temporary file: %s", str(e))

#####################################
# Main Entrypoint
#####################################

def main():
    # Start the health-check Flask server in a daemon thread.
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health server started on port 8000.")

    # Start the Telegram bot.
    logger.info("Starting Telegram bot...")
    bot.run()

if __name__ == "__main__":
    main()
