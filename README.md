# US Pollution Timeline App

An interactive Streamlit application that visualizes real EPA pollution data across the United States over time, with markers showing major environmental legislation to highlight the impact of policy on air quality.

## Features

- Uses the official EPA Air Quality System (AQS) API
- Visualize pollution levels across major US cities
- Explore data from the last 10+ years
- View PM2.5, Ozone, SO2, NO2, and CO levels
- See how major environmental laws correlate with pollution trends

## Project Structure

```
app/
├── app.py                 # Main Streamlit application
├── epa_data_loader.py     # EPA API data loader
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration for deployment
├── fly.toml              # Fly.io deployment configuration
├── .env.example          # Example environment variables
├── setup.sh              # Automated setup script
├── run.sh                # Run script with environment loading
├── .streamlit/
│   └── config.toml       # Streamlit configuration
├── .gitignore
└── README.md
```

## Data Source

This app uses real data from the EPA Air Quality System API.
**EPA API**: [https://aqs.epa.gov/aqsweb/documents/data_api.html#signup](https://aqs.epa.gov/aqsweb/documents/data_api.html#signup)
- Official EPA air quality measurements
- Annual data from monitoring stations across the US
- Covers PM2.5, Ozone, SO2, NO2, and CO pollutants

### Monitored Cities

The app fetches data for these major US cities:
- Los Angeles, CA
- New York, NY
- Chicago, IL
- Houston, TX
- Phoenix, AZ
- Philadelphia, PA
- San Antonio, TX
- San Diego, CA
- Dallas, TX
- San Jose, CA

## License

This project is open source and available under the MIT License.