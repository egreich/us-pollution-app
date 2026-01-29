# Quick Start Guide

## First Time Setup

### 1. Get EPA API Credentials (Required)

Visit: https://aqs.epa.gov/aqsweb/documents/data_api.html#signup

Fill out the form with your email address and you'll receive an API key.

### 2. Setup the Project

Run the automated setup:
```bash
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Create a .env file template

### 3. Configure Your Credentials

Edit the `.env` file and add your EPA credentials:
```bash
nano .env
```

Replace the placeholder values:
```
export EPA_EMAIL="your.email@example.com"
export EPA_API_KEY="your_actual_api_key"
```

### 4. Run the App

```bash
./run.sh
```

The app will:
- Load your environment variables from `.env`
- Activate the virtual environment
- Start Streamlit on http://localhost:8501

## Alternative: Manual Run

If you prefer to run manually:

```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
source .env

# Run the app
streamlit run app.py
```

## What to Expect

On first run:
- The app will fetch data from EPA API (takes 1-2 minutes)
- You'll see progress messages in the console
- Subsequent runs will be instant due to caching

## Common Issues

**"Command not found: streamlit"**
- Make sure virtual environment is activated: `source venv/bin/activate`

**"EPA API credentials not configured"**
- Check that .env file exists and has correct values
- Make sure you ran `source .env` or used `./run.sh`

**"Permission denied" when running setup.sh or run.sh**
- Make scripts executable: `chmod +x setup.sh run.sh`

## Next Steps

Once the app is running:
1. Use the year slider to explore different time periods
2. Switch between pollutants using the dropdown
3. Click on cities on the map for detailed information
4. Scroll down to see the timeline chart with legislation markers
5. Expand the "View Legislation Details" section to learn about environmental laws

Enjoy exploring US pollution data! 🌍
