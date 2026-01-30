FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install dependencies one by one to avoid build issues
COPY requirements.txt .
RUN pip install --no-cache-dir streamlit==1.39.0 && \
    pip install --no-cache-dir pandas==2.2.3 && \
    pip install --no-cache-dir plotly==5.24.1 && \
    pip install --no-cache-dir pydeck==0.9.1 && \
    pip install --no-cache-dir requests==2.32.3

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 8080

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Run the application
ENTRYPOINT ["streamlit", "run", "datacenter_app.py", "--server.port=8080", "--server.address=0.0.0.0"]
