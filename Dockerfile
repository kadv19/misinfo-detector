FROM python:3.12-slim

WORKDIR /app

# Install system deps (for NLTK/TextBlob)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose dynamic port
EXPOSE $PORT

# Health check (optional, for Cloud Run)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Start command (binds to $PORT and 0.0.0.0)
CMD ["sh", "-c", "streamlit run app.py --server.port=$$PORT --server.address=0.0.0.0 --server.enableCORS=false --server.headless=true"]
