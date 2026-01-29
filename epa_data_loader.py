import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import json
from pathlib import Path

# EPA AQS API Configuration
EPA_API_BASE = "https://aqs.epa.gov/data/api"
EPA_EMAIL = os.getenv("EPA_EMAIL")
EPA_API_KEY = os.getenv("EPA_API_KEY")

# Major US cities with their county and state FIPS codes for EPA API
CITIES_CONFIG = [
    # Top 10 by population
    {"city": "Los Angeles", "state": "06", "county": "037", "latitude": 34.0522, "longitude": -118.2437},
    {"city": "New York", "state": "36", "county": "061", "latitude": 40.7128, "longitude": -74.0060},
    {"city": "Chicago", "state": "17", "county": "031", "latitude": 41.8781, "longitude": -87.6298},
    {"city": "Houston", "state": "48", "county": "201", "latitude": 29.7604, "longitude": -95.3698},
    {"city": "Phoenix", "state": "04", "county": "013", "latitude": 33.4484, "longitude": -112.0740},
    {"city": "Philadelphia", "state": "42", "county": "101", "latitude": 39.9526, "longitude": -75.1652},
    {"city": "San Antonio", "state": "48", "county": "029", "latitude": 29.4241, "longitude": -98.4936},
    {"city": "San Diego", "state": "06", "county": "073", "latitude": 32.7157, "longitude": -117.1611},
    {"city": "Dallas", "state": "48", "county": "113", "latitude": 32.7767, "longitude": -96.7970},
    {"city": "San Jose", "state": "06", "county": "085", "latitude": 37.3382, "longitude": -121.8863},
    
    # Additional major cities for better geographic coverage
    {"city": "Austin", "state": "48", "county": "453", "latitude": 30.2672, "longitude": -97.7431},
    {"city": "Jacksonville", "state": "12", "county": "031", "latitude": 30.3322, "longitude": -81.6557},
    {"city": "Fort Worth", "state": "48", "county": "439", "latitude": 32.7555, "longitude": -97.3308},
    {"city": "Columbus", "state": "39", "county": "049", "latitude": 39.9612, "longitude": -82.9988},
    {"city": "Charlotte", "state": "37", "county": "119", "latitude": 35.2271, "longitude": -80.8431},
    {"city": "San Francisco", "state": "06", "county": "075", "latitude": 37.7749, "longitude": -122.4194},
    {"city": "Indianapolis", "state": "18", "county": "097", "latitude": 39.7684, "longitude": -86.1581},
    {"city": "Seattle", "state": "53", "county": "033", "latitude": 47.6062, "longitude": -122.3321},
    {"city": "Denver", "state": "08", "county": "031", "latitude": 39.7392, "longitude": -104.9903},
    {"city": "Boston", "state": "25", "county": "025", "latitude": 42.3601, "longitude": -71.0589},
    {"city": "El Paso", "state": "48", "county": "141", "latitude": 31.7619, "longitude": -106.4850},
    {"city": "Detroit", "state": "26", "county": "163", "latitude": 42.3314, "longitude": -83.0458},
    {"city": "Nashville", "state": "47", "county": "037", "latitude": 36.1627, "longitude": -86.7816},
    {"city": "Portland", "state": "41", "county": "051", "latitude": 45.5152, "longitude": -122.6784},
    {"city": "Las Vegas", "state": "32", "county": "003", "latitude": 36.1699, "longitude": -115.1398},
    {"city": "Memphis", "state": "47", "county": "157", "latitude": 35.1495, "longitude": -90.0490},
    {"city": "Louisville", "state": "21", "county": "111", "latitude": 38.2527, "longitude": -85.7585},
    {"city": "Baltimore", "state": "24", "county": "510", "latitude": 39.2904, "longitude": -76.6122},
    {"city": "Milwaukee", "state": "55", "county": "079", "latitude": 43.0389, "longitude": -87.9065},
    {"city": "Albuquerque", "state": "35", "county": "001", "latitude": 35.0844, "longitude": -106.6504},
    {"city": "Tucson", "state": "04", "county": "019", "latitude": 32.2226, "longitude": -110.9747},
    {"city": "Fresno", "state": "06", "county": "019", "latitude": 36.7378, "longitude": -119.7871},
    {"city": "Sacramento", "state": "06", "county": "067", "latitude": 38.5816, "longitude": -121.4944},
    {"city": "Kansas City", "state": "29", "county": "095", "latitude": 39.0997, "longitude": -94.5786},
    {"city": "Atlanta", "state": "13", "county": "121", "latitude": 33.7490, "longitude": -84.3880},
    {"city": "Miami", "state": "12", "county": "086", "latitude": 25.7617, "longitude": -80.1918},
    {"city": "Cleveland", "state": "39", "county": "035", "latitude": 41.4993, "longitude": -81.6944},
    {"city": "New Orleans", "state": "22", "county": "071", "latitude": 29.9511, "longitude": -90.0715},
    {"city": "Minneapolis", "state": "27", "county": "053", "latitude": 44.9778, "longitude": -93.2650},
    {"city": "Tampa", "state": "12", "county": "057", "latitude": 27.9506, "longitude": -82.4572},
]

# EPA Parameter codes for pollutants
POLLUTANT_CODES = {
    "PM2.5": "88101",  # PM2.5 Local Conditions
    "Ozone": "44201",  # Ozone
    "SO2": "42401",    # Sulfur dioxide
    "NO2": "42602",    # Nitrogen dioxide
    "CO": "42101",     # Carbon monoxide
}

POLLUTANT_UNITS = {
    "PM2.5": "μg/m³",
    "Ozone": "ppm",
    "SO2": "ppb",
    "NO2": "ppb",
    "CO": "ppm",
}


def fetch_epa_data(state_code, county_code, parameter_code, begin_date, end_date, max_retries=3):
    """
    Fetch data from EPA AQS API for a specific location and pollutant.
    
    Args:
        state_code: Two-digit state FIPS code
        county_code: Three-digit county FIPS code
        parameter_code: EPA parameter code for pollutant
        begin_date: Start date (YYYYMMDD format)
        end_date: End date (YYYYMMDD format)
        max_retries: Maximum number of retry attempts
    
    Returns:
        DataFrame with pollution data or None if request fails
    
    Raises:
        ValueError: If EPA credentials are not configured
        requests.exceptions.RequestException: If API request fails after retries
    """
    if not EPA_EMAIL or not EPA_API_KEY:
        raise ValueError(
            "EPA API credentials not configured!\n"
            "Please set EPA_EMAIL and EPA_API_KEY environment variables.\n"
            "Sign up at: https://aqs.epa.gov/aqsweb/documents/data_api.html#signup"
        )
    
    url = f"{EPA_API_BASE}/annualData/byCounty"
    
    params = {
        "email": EPA_EMAIL,
        "key": EPA_API_KEY,
        "param": parameter_code,
        "bdate": begin_date,
        "edate": end_date,
        "state": state_code,
        "county": county_code,
    }
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("Data"):
                    return pd.DataFrame(data["Data"])
                else:
                    # No data available for this query
                    return None
            elif response.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt
                print(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                print(error_msg)
                raise requests.exceptions.RequestException(error_msg)
                
        except requests.exceptions.RequestException as e:
            last_exception = e
            print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    
    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    
    return None


def load_pollution_data_with_cache():
    """
    Load pollution data with file-based caching for persistence across app restarts.
    Cache expires after 365 days (1 year).
    """
    cache_dir = Path("data_cache")
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / "epa_pollution_data.csv"
    cache_meta_file = cache_dir / "cache_metadata.json"
    
    # Check if cache exists and is recent
    if cache_file.exists() and cache_meta_file.exists():
        try:
            with open(cache_meta_file, 'r') as f:
                metadata = json.load(f)
            
            cache_date = datetime.fromisoformat(metadata['timestamp'])
            cache_age_days = (datetime.now() - cache_date).days
            
            if cache_age_days < 365:
                print(f"Loading cached data from {cache_date.strftime('%Y-%m-%d')} ({cache_age_days} days old)")
                df = pd.read_csv(cache_file)
                print(f"✓ Loaded {len(df)} records from cache")
                return df
            else:
                print(f"Cache expired ({cache_age_days} days old), fetching fresh data...")
        except Exception as e:
            print(f"Error reading cache: {e}, fetching fresh data...")
    
    # Fetch fresh data
    df = load_pollution_data()
    
    # Save to cache
    try:
        df.to_csv(cache_file, index=False)
        with open(cache_meta_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'record_count': len(df),
                'years': f"{df['year'].min()}-{df['year'].max()}"
            }, f)
        print(f"✓ Cached data saved to {cache_file}")
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")
    
    return df


def load_pollution_data():
    """
    Load pollution data from EPA AQS API.
    
    Returns:
        DataFrame with pollution data from EPA API
    
    Raises:
        ValueError: If EPA credentials are not configured
        RuntimeError: If no data could be fetched from EPA API
    """
    
    # Verify credentials are set
    if not EPA_EMAIL or not EPA_API_KEY:
        raise ValueError(
            "EPA API credentials not configured!\n\n"
            "To use this app, you need to:\n"
            "1. Sign up for EPA API at: https://aqs.epa.gov/aqsweb/documents/data_api.html#signup\n"
            "2. Set environment variables:\n"
            "   export EPA_EMAIL='your.email@example.com'\n"
            "   export EPA_API_KEY='your_api_key'\n"
            "3. Run the app with: source .env && streamlit run app.py"
        )
    
    all_data = []
    
    # Fetch historical data starting from 1980 (EPA data availability)
    # Fetch every 2 years to balance data coverage and API request count
    current_year = datetime.now().year
    start_year = 1980
    
    # Fetch every 2 years from 1980-2000, then annually from 2000-present for better recent resolution
    years_to_fetch = list(range(start_year, 2000, 2)) + list(range(2000, current_year + 1))
    
    print(f"Fetching EPA data for {len(years_to_fetch)} years from {start_year} to {current_year}")
    print(f"Using email: {EPA_EMAIL}")
    print(f"This will take several minutes...")
    
    errors = []
    total_requests = len(CITIES_CONFIG) * len(POLLUTANT_CODES) * len(years_to_fetch)
    completed_requests = 0
    
    for city in CITIES_CONFIG:
        for pollutant_name, param_code in POLLUTANT_CODES.items():
            print(f"\nFetching {pollutant_name} data for {city['city']}...")
            
            # Fetch one year at a time (EPA API requirement)
            for year in years_to_fetch:
                begin_date = f"{year}0101"
                end_date = f"{year}1231"
                
                try:
                    df = fetch_epa_data(
                        city["state"],
                        city["county"],
                        param_code,
                        begin_date,
                        end_date
                    )
                    
                    completed_requests += 1
                    progress = (completed_requests / total_requests) * 100
                    print(f"  {year}: {'✓' if df is not None and not df.empty else '✗'} ({progress:.1f}% complete)")
                    
                    if df is not None and not df.empty:
                        # Process the data
                        df['city'] = city['city']
                        df['latitude'] = city['latitude']
                        df['longitude'] = city['longitude']
                        df['pollutant'] = pollutant_name
                        df['unit'] = POLLUTANT_UNITS[pollutant_name]
                        df['year'] = df['year'].astype(int)
                        
                        # Use arithmetic mean as the value
                        df['value'] = df['arithmetic_mean'].astype(float)
                        
                        # Select relevant columns
                        df = df[['year', 'city', 'state_code', 'latitude', 'longitude', 
                                'pollutant', 'value', 'unit']]
                        df = df.rename(columns={'state_code': 'state'})
                        
                        all_data.append(df)
                    
                except Exception as e:
                    error_msg = f"Error fetching {pollutant_name} for {city['city']} ({year}): {str(e)}"
                    print(f"  ✗ {year}: {str(e)[:80]}...")
                    errors.append(error_msg)
                    completed_requests += 1
                
                # Rate limiting: wait between requests
                time.sleep(0.3)
    
    if not all_data:
        error_summary = "\n".join(errors[:10]) if errors else "Unknown error"  # Show first 10 errors
        raise RuntimeError(
            f"Failed to fetch any data from EPA API!\n\n"
            f"Errors encountered (first 10):\n{error_summary}\n\n"
            f"Please check:\n"
            f"1. Your EPA_EMAIL and EPA_API_KEY are correct\n"
            f"2. You have internet connectivity\n"
            f"3. The EPA API service is online: {EPA_API_BASE}"
        )
    
    combined_data = pd.concat(all_data, ignore_index=True)
    print(f"\n✓ Successfully loaded {len(combined_data)} records from EPA API")
    print(f"  Years: {combined_data['year'].min()} - {combined_data['year'].max()}")
    print(f"  Cities: {combined_data['city'].nunique()}")
    print(f"  Pollutants: {', '.join(combined_data['pollutant'].unique())}")
    
    if errors:
        print(f"\n⚠ Warning: {len(errors)} requests failed (see above)")
    
    return combined_data


def get_legislation_timeline():
    """
    Return a DataFrame of major US environmental legislation.
    """
    legislation = [
        {
            'year': 1970,
            'title': 'Clean Air Act',
            'abbrev': 'CAA',
            'description': 'Established national air quality standards and required states to develop implementation plans.'
        },
        {
            'year': 1977,
            'title': 'Clean Air Act Amendments',
            'abbrev': 'CAAA 77',
            'description': 'Set stricter standards for industrial pollutants and vehicle emissions.'
        },
        {
            'year': 1990,
            'title': 'Clean Air Act Amendments',
            'abbrev': 'CAAA 90',
            'description': 'Addressed acid rain, ozone depletion, and toxic air pollution with market-based approaches.'
        },
        {
            'year': 2011,
            'title': 'Cross-State Air Pollution Rule',
            'abbrev': 'CSAPR',
            'description': 'Required states to reduce power plant emissions that cross state lines.'
        },
        {
            'year': 2012,
            'title': 'Mercury and Air Toxics Standards',
            'abbrev': 'MATS',
            'description': 'First national standards to reduce mercury and toxic air pollution from power plants.'
        },
        {
            'year': 2015,
            'title': 'Clean Power Plan',
            'abbrev': 'CPP',
            'description': 'Set carbon pollution standards for existing power plants (implementation varied by administration).'
        },
    ]
    
    return pd.DataFrame(legislation)

