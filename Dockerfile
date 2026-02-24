# Use official Playwright image which includes all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create downloads directory
RUN mkdir -p downloads

# Set Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose port for health checks
EXPOSE 7860

# Command to run the bot
CMD ["python", "bot.py"]
