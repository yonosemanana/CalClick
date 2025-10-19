FROM python:3.12-slim

# Add build arg for Chrome version
ARG CHROME_VERSION=""

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y wget gnupg2 xvfb \
    && wget -q -O /usr/share/keyrings/google-linux-signing-key.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) \
    && echo "CHROME_VERSION=${CHROME_VERSION}" >> /etc/environment \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Start Xvfb and run the application
CMD Xvfb :99 -screen 0 1024x768x16 & python main.py
