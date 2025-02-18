FROM python:3.9-slim

# Install OS dependencies (FFmpeg is not used here, but you could add others if needed)
RUN apt-get update && apt-get install -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose port 8000 for the health check
EXPOSE 8000

CMD ["python", "bot.py"]
