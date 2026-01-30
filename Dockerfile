FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including build tools for compilation
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 8080

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Run the application
ENTRYPOINT ["streamlit", "run", "datacenter_app.py", "--server.port=8080", "--server.address=0.0.0.0"]

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 8080

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Run the application
ENTRYPOINT ["streamlit", "run", "datacenter_app.py", "--server.port=8080", "--server.address=0.0.0.0"]
