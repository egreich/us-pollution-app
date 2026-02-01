"""
Geocoding utility to convert county/state locations to lat/lon coordinates
Uses the Census Bureau's geocoding API
"""

import pandas as pd
import requests
import time
from typing import Optional, Tuple


# US County seat coordinates (fallback for major counties)
# This covers the most common counties where data centers are located
COUNTY_COORDINATES = {
    # Virginia (Data Center Alley)
    ("Loudoun", "VA"): (39.0438, -77.4874),  # Ashburn - primary data center hub
    ("Fairfax", "VA"): (38.8462, -77.3064),
    ("Prince William", "VA"): (38.7932, -77.4605),
    ("Henrico", "VA"): (37.5407, -77.4360),
    
    # California
    ("Santa Clara", "CA"): (37.3541, -121.9552),  # Silicon Valley
    ("Alameda", "CA"): (37.7652, -122.2416),
    ("Los Angeles", "CA"): (34.0522, -118.2437),
    ("San Francisco", "CA"): (37.7749, -122.4194),
    ("San Mateo", "CA"): (37.5630, -122.3255),
    ("Orange", "CA"): (33.7175, -117.8311),
    ("Sacramento", "CA"): (38.5816, -121.4944),
    ("San Diego", "CA"): (32.7157, -117.1611),
    
    # Texas
    ("Dallas", "TX"): (32.7767, -96.7970),
    ("Harris", "TX"): (29.7604, -95.3698),  # Houston
    ("Bexar", "TX"): (29.4241, -98.4936),  # San Antonio
    ("Collin", "TX"): (33.1972, -96.6397),
    ("Tarrant", "TX"): (32.7555, -97.3308),
    ("Travis", "TX"): (30.2672, -97.7431),  # Austin
    
    # Arizona
    ("Maricopa", "AZ"): (33.4484, -112.0740),  # Phoenix
    ("Pima", "AZ"): (32.2217, -110.9265),  # Tucson
    
    # Illinois
    ("Cook", "IL"): (41.8781, -87.6298),  # Chicago
    ("DuPage", "IL"): (41.8500, -88.0834),
    
    # Georgia
    ("Fulton", "GA"): (33.7490, -84.3880),  # Atlanta
    ("Douglas", "GA"): (33.7468, -84.7452),
    
    # New Jersey
    ("Hudson", "NJ"): (40.7434, -74.0324),
    ("Middlesex", "NJ"): (40.4862, -74.4518),
    ("Essex", "NJ"): (40.7834, -74.2299),
    ("Passaic", "NJ"): (40.8587, -74.2282),
    
    # Ohio
    ("Franklin", "OH"): (39.9612, -82.9988),  # Columbus
    ("Licking", "OH"): (40.0581, -82.4013),
    
    # Oregon
    ("Washington", "OR"): (45.5272, -122.9360),
    ("Morrow", "OR"): (45.4948, -119.5508),
    ("Umatilla", "OR"): (45.6354, -118.8447),
    
    # Iowa
    ("Pottawattamie", "IA"): (41.2619, -95.8608),  # Council Bluffs
    ("Polk", "IA"): (41.5868, -93.6250),  # Des Moines
    
    # North Carolina
    ("Mecklenberg", "NC"): (35.2271, -80.8431),  # Charlotte
    ("Catawba", "NC"): (35.6918, -81.2151),
    
    # Washington
    ("Grant", "WA"): (47.2087, -119.4094),
    
    # Nebraska
    ("Douglas", "NE"): (41.2565, -95.9345),  # Omaha
    ("Sarpy", "NE"): (41.1175, -96.0422),
    
    # New York
    ("New York", "NY"): (40.7128, -74.0060),  # Manhattan
    ("Westchester", "NY"): (41.1220, -73.7949),
    
    # Massachusetts
    ("Middlesex", "MA"): (42.4868, -71.3824),
    ("Suffolk", "MA"): (42.3601, -71.0589),  # Boston
    
    # Colorado
    ("Arapahoe", "CO"): (39.6433, -104.3005),
    ("Denver", "CO"): (39.7392, -104.9903),
    ("Adams", "CO"): (39.8747, -104.3339),
    
    # Nevada
    ("Clark", "NV"): (36.1699, -115.1398),  # Las Vegas
    
    # Utah
    ("Salt Lake", "UT"): (40.7608, -111.8910),
    
    # Minnesota
    ("Hennepin", "MN"): (44.9778, -93.2650),  # Minneapolis
}


def geocode_county_census(county: str, state: str) -> Optional[Tuple[float, float]]:
    """
    Geocode a county using the Census Bureau's geocoding API
    
    Args:
        county: County name
        state: Two-letter state abbreviation
        
    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    try:
        # Census Bureau geocoding API endpoint
        url = "https://geocoding.geo.census.gov/geocoder/locations/address"
        
        # Try to geocode the county seat (most counties have a city with the same name)
        params = {
            "street": "",
            "city": county,
            "state": state,
            "benchmark": "Public_AR_Current",
            "format": "json"
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("result", {}).get("addressMatches"):
                match = data["result"]["addressMatches"][0]
                coords = match["coordinates"]
                return (coords["y"], coords["x"])  # lat, lon
                
    except Exception as e:
        print(f"Census geocoding failed for {county}, {state}: {e}")
    
    return None


def geocode_county(county: str, state: str, use_fallback: bool = True) -> Tuple[float, float]:
    """
    Geocode a county to lat/lon coordinates
    
    Args:
        county: County name (e.g., "Santa Clara")
        state: Two-letter state abbreviation (e.g., "CA")
        use_fallback: Whether to use fallback coordinates if API fails
        
    Returns:
        Tuple of (latitude, longitude)
    """
    # First, check our hardcoded coordinates (fast, reliable for common counties)
    key = (county, state)
    if key in COUNTY_COORDINATES:
        return COUNTY_COORDINATES[key]
    
    # Try Census API
    coords = geocode_county_census(county, state)
    if coords:
        return coords
    
    # If we have fallback enabled and nothing worked, use approximate state center
    if use_fallback:
        print(f"Warning: Could not geocode {county}, {state}. Using fallback.")
        # Return a default coordinate (continental US center)
        return (39.8283, -98.5795)
    
    raise ValueError(f"Could not geocode {county}, {state}")


def add_coordinates_to_dataframe(df: pd.DataFrame, 
                                 county_col: str = "County", 
                                 state_col: str = "State") -> pd.DataFrame:
    """
    Add latitude and longitude columns to a DataFrame with county/state data
    
    Args:
        df: DataFrame with county and state columns
        county_col: Name of the county column
        state_col: Name of the state column
        
    Returns:
        DataFrame with added 'latitude' and 'longitude' columns
    """
    df = df.copy()
    
    # Initialize coordinate columns
    df['latitude'] = 0.0
    df['longitude'] = 0.0
    
    print(f"Geocoding {len(df)} locations...")
    
    # Track unique county/state combinations to avoid redundant API calls
    unique_locations = df[[county_col, state_col]].drop_duplicates()
    location_coords = {}
    
    for idx, row in unique_locations.iterrows():
        county = row[county_col]
        state = row[state_col]
        
        if pd.isna(county) or pd.isna(state):
            continue
            
        try:
            lat, lon = geocode_county(county, state)
            location_coords[(county, state)] = (lat, lon)
            
            # Rate limiting for API calls (be nice to Census servers)
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error geocoding {county}, {state}: {e}")
            location_coords[(county, state)] = (39.8283, -98.5795)  # US center fallback
    
    # Apply coordinates to all matching rows
    for (county, state), (lat, lon) in location_coords.items():
        mask = (df[county_col] == county) & (df[state_col] == state)
        df.loc[mask, 'latitude'] = lat
        df.loc[mask, 'longitude'] = lon
    
    print(f"Geocoded {len(location_coords)} unique locations")
    
    return df


def main():
    """
    Test the geocoding functionality with Business Insider data
    """
    print("Testing geocoding with Business Insider data...")
    
    # Load the Business Insider CSV
    df = pd.read_csv("business_insider_datacenters.csv")
    
    print(f"\nLoaded {len(df)} data centers")
    print(f"Unique counties: {df['County'].nunique()}")
    print(f"Unique states: {df['State'].nunique()}")
    
    # Add coordinates
    df_with_coords = add_coordinates_to_dataframe(df)
    
    # Show sample results
    print("\nSample geocoded data:")
    print(df_with_coords[['Brand', 'State', 'County', 'latitude', 'longitude']].head(20))
    
    # Save geocoded data
    output_file = "business_insider_datacenters_geocoded.csv"
    df_with_coords.to_csv(output_file, index=False)
    print(f"\nSaved geocoded data to {output_file}")
    
    # Statistics
    print("\nGeocoding statistics:")
    print(f"Successfully geocoded: {(df_with_coords['latitude'] != 39.8283).sum()} / {len(df_with_coords)}")
    print(f"Used fallback: {(df_with_coords['latitude'] == 39.8283).sum()}")


if __name__ == "__main__":
    main()
