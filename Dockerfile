FROM python:3.11

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .

# Install pyarrow separately first to ensure we get prebuilt wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir pyarrow==14.0.1 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 8080

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health || exit 1

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
