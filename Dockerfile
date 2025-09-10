FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY veripay_bot.py .
COPY core/ ./core/
COPY database/ ./database/
COPY utils/ ./utils/

# Create necessary directories
RUN mkdir -p logs uploads reports

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV BOT_TOKEN=8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc
ENV GOOGLE_VISION_API_KEY=AIzaSyC4ESpSW_c1ijlLGwTUQ5wdBhflQOPps6M

# Expose port (if needed for health checks)
EXPOSE 8000

# Run the bot
CMD ["python", "veripay_bot.py"]
