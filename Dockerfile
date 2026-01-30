FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for Python packages
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies with prebuilt wheels only (no source builds)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 8080

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Run the application
ENTRYPOINT ["streamlit", "run", "datacenter_app.py", "--server.port=8080", "--server.address=0.0.0.0"]
