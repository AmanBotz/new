FROM python:3.9-slim

# Install FFmpeg and required OS packages
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose port 8000 for health checks (Koyeb)
EXPOSE 8000

# Command to run the bot (which starts both the Telegram bot and the health check server)
CMD ["python", "bot.py"]
