# Use Python 3.10 as base image
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Expose port 8000 for health check
EXPOSE 8000

# Run the bot and health check server
CMD ["sh", "-c", "python3 bot.py & python3 server.py"]
