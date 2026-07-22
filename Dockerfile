FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    pipx \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Ensure pipx path is accessible
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the local project files to the container
COPY . /app

# Install agent-reach from the source
RUN pip install --no-cache-dir -e .

# Pre-install twitter-cli using pipx (used by fetch_tweets.py)
RUN pipx install twitter-cli

# Expose the default port (Render will override with $PORT)
EXPOSE 10000

# Start the FastAPI web server using Render's dynamic PORT
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000}"]
