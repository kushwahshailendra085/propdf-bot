# Base Image with Python
FROM python:3.11-slim

# Install system dependencies for Playwright and PyMuPDF
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers AND their dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy project files
COPY . .

# Create downloads directory
RUN mkdir -p downloads

# Set Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port for health checks
EXPOSE 8080

# Command to run the bot
CMD ["python", "bot.py"]
