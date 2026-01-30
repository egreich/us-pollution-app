# US Data Center App

An interactive Streamlit application that visualizes data centers across the United States.

Launch the app here: https://us-datacenter-app.fly.dev

## Project Structure

```
app/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration for deployment
├── fly.toml              # Fly.io deployment configuration
├── setup.sh              # Automated setup script
├── .streamlit/
│   └── config.toml       # Streamlit configuration
├── .gitignore
└── README.md
```

## Data Source

Data Centers:

Official cloud provider websites (AWS, Google, Microsoft, Meta, Oracle)
Colocation provider sites (Equinix, Digital Realty)
Industry publications (Data Center Dynamics)
Energy estimates based on industry standards for hyperscale facilities

Water Data:

USGS (United States Geological Survey)
U.S. Drought Monitor
World Resources Institute Aqueduct water risk tool