FROM python:3.12-slim

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y \
    xvfb google-chrome-stable \

# Install Poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Start Xvfb and run the application
CMD Xvfb :99 -screen 0 1024x768x16 & poetry run python main.py
