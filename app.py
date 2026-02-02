"""
US Data Centers and Water Scarcity Visualization
Maps data center locations against state water availability
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go
import requests

# Page configuration with dark theme
st.set_page_config(
    page_title="US Data Centers and Water Scarcity",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dark mode styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .metric-value {
        color: #ffffff !important;
        font-weight: bold;
    }
    /* Brighter text for all elements */
    .stMarkdown, p, span, div {
        color: #ffffff !important;
    }
    /* Reduce chart margins */
    .js-plotly-plot {
        margin-top: 0 !important;
        margin-bottom: 10px !important;
    }
    /* Reduce map container margins */
    [data-testid="stDeckGlJsonChart"] {
        margin-top: 0 !important;
        margin-bottom: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Main title
st.markdown('<h1 style="color: #ffffff; font-weight: bold; font-size: 48px;">US Data Centers & Water Scarcity</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #ffffff; font-size: 16px;">Mapping data center infrastructure against state water availability</p>', unsafe_allow_html=True)

def calculate_energy(facility_sqft, power_density_w_sqft, pue=1.2):
    """
    Calculate energy consumption for a data center
    Formula: (Facility Size in sq ft × Power Density in W/sq ft × PUE) ÷ 1,000,000 = MW
    
    Args:
        facility_sqft: Facility size in square feet
        power_density_w_sqft: Power density in watts per square foot
        pue: Power Usage Effectiveness (default 1.2 for modern facilities)
    
    Returns:
        Energy consumption in megawatts (MW)
    """
    return round((facility_sqft * power_density_w_sqft * pue) / 1_000_000)

def classify_facility_type(provider_name):
    """
    Classify data center facility type based on provider name
    
    Categories:
    - Hyperscale: Large cloud providers (AWS, Google, Microsoft, Meta, Apple, Oracle, etc.)
    - Colocation: Multi-tenant data center operators (Equinix, Digital Realty, etc.)
    - Telecom: Telecommunications companies (Verizon, AT&T, Lumen, etc.)
    - Enterprise: Companies running their own data centers
    - Unknown: Cannot determine from name alone
    
    Args:
        provider_name: Company/brand name
    
    Returns:
        Facility type category string
    """
    if not provider_name or pd.isna(provider_name):
        return 'Unknown'
    
    provider_lower = str(provider_name).lower()
    
    # Hyperscale cloud providers
    hyperscale_keywords = [
        'amazon', 'aws', 'google', 'microsoft', 'azure', 'meta', 'facebook',
        'apple', 'oracle', 'alibaba', 'tencent', 'ibm cloud'
    ]
    
    # Colocation providers
    colocation_keywords = [
        'equinix', 'digital realty', 'cyrusone', 'coresite', 'qts', 'switch',
        'databank', 'flexential', 'tierpoint', 'vantage', 'stack infrastructure',
        'centersquare', 'iron mountain', 'serverfarm', 'data center', 'datacenter',
        'colocation', 'colo', 'aligned data centers', 'h5 data centers'
    ]
    
    # Telecommunications companies
    telecom_keywords = [
        'verizon', 'at&t', 'lumen', 'centurylink', 'comcast', 'charter',
        'cox', 'spectrum', 'frontier', 'windstream', 't-mobile', 'sprint',
        'ntt', 'cogent', 'zayo', 'level 3', 'tw telecom'
    ]
    
    # Check hyperscale first (most specific)
    for keyword in hyperscale_keywords:
        if keyword in provider_lower:
            return 'Hyperscale'
    
    # Check colocation
    for keyword in colocation_keywords:
        if keyword in provider_lower:
            return 'Colocation'
    
    # Check telecom
    for keyword in telecom_keywords:
        if keyword in provider_lower:
            return 'Telecom'
    
    # If provider name ends with common business suffixes, likely enterprise
    enterprise_patterns = ['llc', 'inc', 'corp', 'ltd', 'properties', 'holdings', 'investors']
    for pattern in enterprise_patterns:
        if provider_lower.endswith(pattern) or f' {pattern}' in provider_lower:
            return 'Enterprise'
    
    # Default to unknown
    return 'Unknown'

def estimate_water_consumption(energy_mw, facility_type, state):
    """
    Estimate daily water consumption for a data center based on power usage
    
    Water consumption varies by:
    - Cooling method (water-cooled vs air-cooled)
    - Climate/geography (hot vs cool regions)
    - Efficiency/age of facility
    
    Based on research:
    - Li et al. (2025): Data center water consumption global perspective
    - Mytton et al. (2021): Nature - Data centre water consumption
    - Typical range: 0.1-5 liters per kWh
    
    Args:
        energy_mw: Energy consumption in megawatts
        facility_type: Type of facility (Hyperscale, Colocation, etc.)
        state: US state (affects climate assumptions)
    
    Returns:
        Dictionary with water usage estimates (gallons/day and liters/day)
    """
    if pd.isna(energy_mw) or energy_mw <= 0:
        return {'gallons_per_day_low': 0, 'gallons_per_day_high': 0, 
                'liters_per_day_low': 0, 'liters_per_day_high': 0}
    
    # Convert MW to kWh per day: MW * 1000 kW/MW * 24 hours = kWh/day
    kwh_per_day = energy_mw * 1000 * 24
    
    # Hot climate states (higher water usage due to cooling needs)
    hot_states = ['AZ', 'NV', 'TX', 'NM', 'CA', 'FL', 'GA', 'LA', 'MS', 'AL', 'SC']
    # Cool climate states (lower water usage)
    cool_states = ['OR', 'WA', 'ID', 'MT', 'WY', 'ND', 'SD', 'MN', 'WI', 'MI', 'ME', 'VT', 'NH']
    
    # Determine cooling assumption based on facility type and location
    # Hyperscale facilities often use water cooling for efficiency
    # Colocation varies, Telecom/Enterprise often air-cooled
    
    if facility_type == 'Hyperscale':
        # Hyperscale typically uses water cooling (1-4 L/kWh)
        if state in hot_states:
            liters_per_kwh_low = 2.0
            liters_per_kwh_high = 4.5
        elif state in cool_states:
            liters_per_kwh_low = 1.0
            liters_per_kwh_high = 2.5
        else:
            liters_per_kwh_low = 1.5
            liters_per_kwh_high = 3.5
    
    elif facility_type == 'Colocation':
        # Mixed cooling methods (0.5-3 L/kWh)
        if state in hot_states:
            liters_per_kwh_low = 1.0
            liters_per_kwh_high = 3.0
        elif state in cool_states:
            liters_per_kwh_low = 0.3
            liters_per_kwh_high = 1.5
        else:
            liters_per_kwh_low = 0.5
            liters_per_kwh_high = 2.0
    
    else:
        # Telecom/Enterprise/Unknown - assume more air cooling (0.1-2 L/kWh)
        if state in hot_states:
            liters_per_kwh_low = 0.5
            liters_per_kwh_high = 2.0
        elif state in cool_states:
            liters_per_kwh_low = 0.1
            liters_per_kwh_high = 0.8
        else:
            liters_per_kwh_low = 0.2
            liters_per_kwh_high = 1.2
    
    # Calculate daily water consumption in liters
    liters_per_day_low = kwh_per_day * liters_per_kwh_low
    liters_per_day_high = kwh_per_day * liters_per_kwh_high
    
    # Convert to gallons (1 liter = 0.264172 gallons)
    gallons_per_day_low = liters_per_day_low * 0.264172
    gallons_per_day_high = liters_per_day_high * 0.264172
    
    return {
        'gallons_per_day_low': gallons_per_day_low,
        'gallons_per_day_high': gallons_per_day_high,
        'liters_per_day_low': liters_per_day_low,
        'liters_per_day_high': liters_per_day_high
    }

# Load data center locations (we'll create this)
@st.cache_data
def load_datacenter_data():
    """
    Load US data center locations from Business Insider investigation
    Source: Business Insider's analysis of state air permit applications
    Data includes ~1,240 data center facilities across 46 US states
    Power consumption calculated from backup generator capacity (MWh/year)
    """
    import os
    
    # Load geocoded Business Insider data
    csv_path = os.path.join(os.path.dirname(__file__), 'datacenters.csv')
    
    if not os.path.exists(csv_path):
        st.error(f"Data file not found: {csv_path}")
        return pd.DataFrame()
    
    df = pd.read_csv(csv_path)
    
    # Rename columns to match existing structure
    df = df.rename(columns={
        'Brand': 'provider',
        'State': 'state',
        'County': 'county',
        'Low_MWh_year': 'low_mwh_year',
        'High_MWh_year': 'high_mwh_year'
    })
    
    # Create facility name from provider and county
    df['name'] = df.apply(lambda row: f"{row['provider']} ({row['county']}, {row['state']})", axis=1)
    
    # Classify facility type based on provider name
    df['facility_type'] = df['provider'].apply(classify_facility_type)
    
    # Convert annual MWh to average MW (MWh/year ÷ 8760 hours/year = MW)
    # Use midpoint of low and high estimates for visualization
    df['energy_mw'] = ((df['low_mwh_year'] + df['high_mwh_year']) / 2) / 8760
    
    # Also keep low and high MW values for range display
    df['energy_mw_low'] = df['low_mwh_year'] / 8760
    df['energy_mw_high'] = df['high_mwh_year'] / 8760
    
    # Calculate estimated water consumption for each facility
    water_estimates = df.apply(
        lambda row: estimate_water_consumption(row['energy_mw'], row['facility_type'], row['state']),
        axis=1
    )
    
    # Add water consumption columns to dataframe
    df['water_gallons_day_low'] = water_estimates.apply(lambda x: x['gallons_per_day_low'])
    df['water_gallons_day_high'] = water_estimates.apply(lambda x: x['gallons_per_day_high'])
    df['water_liters_day_low'] = water_estimates.apply(lambda x: x['liters_per_day_low'])
    df['water_liters_day_high'] = water_estimates.apply(lambda x: x['liters_per_day_high'])
    
    # Calculate midpoint for visualization
    df['water_gallons_day'] = (df['water_gallons_day_low'] + df['water_gallons_day_high']) / 2
    df['water_liters_day'] = (df['water_liters_day_low'] + df['water_liters_day_high']) / 2
    
    return df

@st.cache_data
def load_water_scarcity_data():
    """
    Load state-level water source data
    Primary water sources for each state
    """
    water_data = {
        "state": ["California", "Arizona", "Nevada", "Texas", "New Mexico", "Utah", 
                 "Colorado", "Oregon", "Washington", "Idaho", "Montana", "Wyoming",
                 "North Dakota", "South Dakota", "Nebraska", "Kansas", "Oklahoma",
                 "Iowa", "Missouri", "Arkansas", "Louisiana", "Mississippi", "Alabama",
                 "Georgia", "Florida", "South Carolina", "North Carolina", "Virginia",
                 "West Virginia", "Kentucky", "Tennessee", "Illinois", "Indiana", "Ohio",
                 "Michigan", "Wisconsin", "Minnesota", "New York", "Pennsylvania",
                 "New Jersey", "Delaware", "Maryland", "Maine", "Vermont", "New Hampshire",
                 "Massachusetts", "Rhode Island", "Connecticut"],
        
        "water_source": ["River/Snowmelt", "River/Groundwater", "River/Groundwater", "River/Groundwater", "River/Groundwater", "River/Snowmelt",
                        "River/Snowmelt", "River/Rain", "River/Rain", "River/Snowmelt", "River/Snowmelt", "River/Snowmelt",
                        "River/Groundwater", "River/Groundwater", "River/Groundwater", "River/Groundwater", "River/Groundwater",
                        "River/Groundwater", "River", "River", "River", "River/Groundwater", "River/Groundwater",
                        "River/Groundwater", "River/Groundwater", "River", "River", "River/Groundwater",
                        "River", "River", "River", "River/Lake", "River/Groundwater", "River/Lake",
                        "Lake", "Lake", "Lake", "Lake/River", "River/Groundwater",
                        "River/Groundwater", "River/Groundwater", "River/Groundwater", "River/Lake", "River/Lake", "River/Lake",
                        "River/Reservoir", "River/Reservoir", "River/Reservoir"],
        
        "water_scarcity": [8.5, 9.0, 9.5, 7.5, 8.0, 7.0,
                          6.5, 4.0, 3.5, 5.0, 4.5, 6.0,
                          4.0, 5.5, 6.0, 6.5, 6.0,
                          3.5, 5.0, 4.5, 4.0, 4.5, 4.0,
                          5.5, 5.0, 4.5, 4.0, 5.0,
                          3.0, 4.0, 5.0, 4.5, 4.0, 3.5,
                          3.0, 3.5, 3.5, 3.0, 3.5,
                          4.0, 4.5, 4.5, 2.5, 2.5, 2.5,
                          3.0, 3.0, 3.5]
    }
    
    return pd.DataFrame(water_data)

# Load data
datacenter_df = load_datacenter_data()
water_df = load_water_scarcity_data()

# State abbreviation to full name mapping
state_abbrev_to_name = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
}

# Convert state abbreviations to full names for merge
datacenter_df['state_full'] = datacenter_df['state'].map(state_abbrev_to_name)

# Merge water source info with datacenters using full state names
datacenter_df = datacenter_df.merge(water_df, left_on='state_full', right_on='state', how='left', suffixes=('', '_water'))

# Keep the abbreviation as 'state' and remove duplicate
if 'state_water' in datacenter_df.columns:
    datacenter_df = datacenter_df.drop(columns=['state_water'])
datacenter_df = datacenter_df.rename(columns={'state': 'state_abbrev', 'state_full': 'state_name'})
datacenter_df['state'] = datacenter_df['state_abbrev']

# Water consumption colors - using Plotly's Turbo colorscale for smooth gradients
import plotly.express as px

def get_water_consumption_color(water_gallons_day, min_water, max_water):
    """
    Create a smooth color gradient based on water consumption using Plotly's Turbo colorscale
    Low water use = Blue/Cyan, High water use = Red
    """
    # Handle NaN values - use gray for unknown
    if pd.isna(water_gallons_day):
        return [128, 128, 128]  # Gray for unknown
    
    # Normalize to 0-1 range using linear scale
    normalized = (water_gallons_day - min_water) / (max_water - min_water) if max_water > min_water else 0
    
    # Use Plotly's Turbo colorscale (smooth blue -> cyan -> green -> yellow -> orange -> red)
    # Sample the colorscale at the normalized position
    import plotly.colors as pcolors
    color_string = pcolors.sample_colorscale('Turbo', [normalized])[0]
    
    # Convert RGB string or hex to RGB tuple
    if color_string.startswith('rgb'):
        # Parse rgb(r, g, b) format
        import re
        rgb_values = re.findall(r'\d+', color_string)
        r, g, b = int(rgb_values[0]), int(rgb_values[1]), int(rgb_values[2])
    else:
        # Parse hex format
        color_string = color_string.lstrip('#')
        r, g, b = tuple(int(color_string[i:i+2], 16) for i in (0, 2, 4))
    
    return [r, g, b]

# Add color based on water consumption (gradient from blue to red)
min_water = datacenter_df['water_gallons_day'].min()
max_water = datacenter_df['water_gallons_day'].max()
datacenter_df['color'] = datacenter_df['water_gallons_day'].apply(lambda x: get_water_consumption_color(x, min_water, max_water))

# Format numbers for tooltip display (PyDeck doesn't support format strings in tooltips)
datacenter_df['energy_mw_display'] = datacenter_df['energy_mw'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
datacenter_df['water_gallons_display'] = datacenter_df['water_gallons_day'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
datacenter_df['water_scarcity_display'] = datacenter_df['water_scarcity'].apply(lambda x: f"{x:.1f}/10" if pd.notna(x) else "N/A")

# Add jitter to longitude and latitude for overlapping facilities
# This creates small random offsets so facilities in the same location don't perfectly overlap
import numpy as np
np.random.seed(67)  # For reproducible jitter
jitter_amount = 0.15  # Increased jitter (roughly 10-15 miles)
datacenter_df['longitude_jittered'] = datacenter_df['longitude'] + np.random.uniform(-jitter_amount, jitter_amount, len(datacenter_df))
datacenter_df['latitude_jittered'] = datacenter_df['latitude'] + np.random.uniform(-jitter_amount, jitter_amount, len(datacenter_df))

# Create 3D visualization

# Legend in a styled box
st.markdown("""
    <div style="background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 2px solid #333333; margin-bottom: 20px;">
        <h4 style="color: #ffffff; margin-top: 0;">Map Legend</h4>
        <table style="width: 59%; color: #ffffff;">
            <tr>
                <td style="padding: 5px;"><strong>Bar Colors:</strong></td>
                <td style="padding: 5px;">Water consumption (Blue/Cyan = low use, Yellow/Orange = medium, Red = high use)</td>
            </tr>
            <tr>
                <td style="padding: 5px;"><strong>Bar Heights:</strong></td>
                <td style="padding: 5px;">Energy consumption in megawatts (MW)</td>
            </tr>
            <tr>
                <td style="padding: 5px;"><strong>State Fill:</strong></td>
                <td style="padding: 5px;">Water scarcity intensity (Darker red = higher scarcity)</td>
            </tr>
        </table>
    </div>
""", unsafe_allow_html=True)
@st.cache_data
def load_state_boundaries():
    url = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
    response = requests.get(url)
    return response.json()

states_geojson = load_state_boundaries()

# Create state-water scarcity lookup
state_water_lookup = dict(zip(water_df['state'], water_df['water_scarcity']))

# Add water scarcity to GeoJSON properties
for feature in states_geojson['features']:
    state_name = feature['properties']['name']
    feature['properties']['water_scarcity'] = state_water_lookup.get(state_name, 5.0)

# Map: States colored by water scarcity + 3D bars for data centers
st.markdown("**Red states = high water scarcity, Blue states = abundant water**")

# Create layers
state_layer = pdk.Layer(
    "GeoJsonLayer",
    states_geojson,
    pickable=False,  # Disable tooltips for states
    stroked=True,
    filled=True,
    extruded=False,
    get_fill_color="[255 * properties.water_scarcity / 10, 100, 255 - (255 * properties.water_scarcity / 10), 100]",
    get_line_color=[255, 255, 255, 80],
    line_width_min_pixels=2,
)

datacenter_layer = pdk.Layer(
    "ColumnLayer",
    data=datacenter_df,
    get_position=["longitude_jittered", "latitude_jittered"],  # Use jittered positions
    get_elevation="energy_mw * 2000",  # Reduced height for better visibility
    elevation_scale=8,  # Moderate scale for good height differences
    radius=15000,  # Thinner columns for cleaner look
    get_fill_color="color",
    pickable=True,
    auto_highlight=True,
    opacity=0.5,
)

# View state
view_state = pdk.ViewState(
    latitude=39.8283,
    longitude=-98.5795,
    zoom=3.5,
    pitch=60,
    bearing=0
)

# Tooltip - using plain field names (PyDeck doesn't support format strings)
tooltip = {
    "html": "<b>{name}</b><br/>Provider: {provider}<br/>Type: {facility_type}<br/>State: {state}<br/>Energy: {energy_mw_display} MW<br/>Est. Water Use: {water_gallons_display} gal/day<br/>Water Source: {water_source}<br/>Water Scarcity: {water_scarcity_display}",
    "style": {"backgroundColor": "black", "color": "white"}
}

# Render map
deck = pdk.Deck(
    layers=[state_layer, datacenter_layer],
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="mapbox://styles/mapbox/dark-v10",
)

st.pydeck_chart(deck)

# Statistics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<p class="metric-value" style="color: #ffffff; font-size: 24px;">{}</p>'.format(len(datacenter_df)), unsafe_allow_html=True)
    st.markdown('<p style="color: #ffffff; font-weight: bold;">Total Data Centers</p>', unsafe_allow_html=True)

with col2:
    total_energy = datacenter_df['energy_mw'].sum()
    st.markdown('<p class="metric-value" style="color: #ffffff; font-size: 24px;">{:,} MW</p>'.format(int(total_energy)), unsafe_allow_html=True)
    st.markdown('<p style="color: #ffffff; font-weight: bold;">Total Energy Output</p>', unsafe_allow_html=True)

with col3:
    high_risk = len(datacenter_df[datacenter_df['water_scarcity'] >= 7])
    st.markdown('<p class="metric-value" style="color: #ffffff; font-size: 24px;">{}</p>'.format(high_risk), unsafe_allow_html=True)
    st.markdown('<p style="color: #ffffff; font-weight: bold;">High Risk Locations</p>', unsafe_allow_html=True)

with col4:
    water_sources = datacenter_df['water_source'].nunique()
    st.markdown('<p class="metric-value" style="color: #ffffff; font-size: 24px;">{}</p>'.format(water_sources), unsafe_allow_html=True)
    st.markdown('<p style="color: #ffffff; font-weight: bold;">Water Source Types</p>', unsafe_allow_html=True)

# Bottom chart: Energy Output by Water Scarcity Level
st.markdown('<h3 style="color: #ffffff;">Total Energy Output vs Water Scarcity</h3>', unsafe_allow_html=True)

# Aggregate by actual scarcity values for continuous x-axis
scarcity_energy = datacenter_df.groupby('water_scarcity', observed=True)['energy_mw'].sum().reset_index()
scarcity_energy = scarcity_energy.sort_values('water_scarcity')

# Create bar chart with numerical x-axis
fig = go.Figure()

# Color bars based on scarcity level
def get_color(scarcity):
    if scarcity < 3:
        return '#00BFFF'  # Blue
    elif scarcity < 5:
        return '#FFD700'  # Yellow
    elif scarcity < 7:
        return '#FF8C00'  # Orange
    else:
        return '#FF0000'  # Red

fig.add_trace(go.Bar(
    x=scarcity_energy['water_scarcity'],
    y=scarcity_energy['energy_mw'],
    marker_color=[get_color(s) for s in scarcity_energy['water_scarcity']],
    text=[f"{int(e)} MW" for e in scarcity_energy['energy_mw']],
    textposition='outside',
    textfont=dict(color='#ffffff', size=12),
    showlegend=False
))

fig.update_layout(
    title=dict(
        text="Total Energy Output (MW) by Water Scarcity Level",
        font=dict(color='#ffffff', size=18)
    ),
    xaxis_title=dict(
        text="Water Scarcity Level (0 = Abundant, 10 = Severe)",
        font=dict(color='#ffffff', size=14)
    ),
    yaxis_title=dict(
        text="Total Energy Output (Megawatts)",
        font=dict(color='#ffffff', size=14)
    ),
    plot_bgcolor='#0e1117',
    paper_bgcolor='#0e1117',
    font=dict(color='#ffffff'),
    height=450,
    margin=dict(t=60, b=40, l=60, r=20),  # Increased top margin from 40 to 60
    xaxis=dict(
        gridcolor='#333333',
        tickfont=dict(color='#ffffff'),
        range=[0, 10],
        dtick=1
    ),
    yaxis=dict(
        gridcolor='#333333',
        tickfont=dict(color='#ffffff')
    ),
)

st.plotly_chart(fig, use_container_width=True)

# Facility Type Breakdown
st.markdown('<h3 style="color: #ffffff;">Data Center Facilities by Type</h3>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    # Pie chart for facility count by type
    facility_counts = datacenter_df['facility_type'].value_counts().reset_index()
    facility_counts.columns = ['Facility Type', 'Count']
    
    fig_types = go.Figure(data=[go.Pie(
        labels=facility_counts['Facility Type'],
        values=facility_counts['Count'],
        hole=0.4,
        marker=dict(
            colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        ),
        textfont=dict(color='#ffffff', size=14)
    )])
    
    fig_types.update_layout(
        title=dict(
            text="Facility Count by Type",
            font=dict(color='#ffffff', size=16)
        ),
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='#ffffff'),
        height=450,
        showlegend=True,
        legend=dict(
            font=dict(color='#ffffff')
        )
    )
    
    st.plotly_chart(fig_types, use_container_width=True)

with col2:
    # Bar chart for energy consumption by type
    facility_energy = datacenter_df.groupby('facility_type', observed=True)['energy_mw'].sum().reset_index()
    facility_energy = facility_energy.sort_values('energy_mw', ascending=False)
    
    fig_energy = go.Figure(data=[go.Bar(
        x=facility_energy['facility_type'],
        y=facility_energy['energy_mw'],
        marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'][:len(facility_energy)],
        text=[f"{int(e):,} MW" for e in facility_energy['energy_mw']],
        textposition='outside',
        textfont=dict(color='#ffffff', size=12)
    )])
    
    fig_energy.update_layout(
        title=dict(
            text="Total Energy Consumption by Type",
            font=dict(color='#ffffff', size=16)
        ),
        xaxis_title=dict(
            text="Facility Type",
            font=dict(color='#ffffff', size=12)
        ),
        yaxis_title=dict(
            text="Energy Output (MW)",
            font=dict(color='#ffffff', size=12)
        ),
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='#ffffff'),
        height=450,
        margin=dict(t=60, b=40, l=60, r=20),  # Increased top margin from default to 60
        xaxis=dict(
            gridcolor='#333333',
            tickfont=dict(color='#ffffff')
        ),
        yaxis=dict(
            gridcolor='#333333',
            tickfont=dict(color='#ffffff')
        ),
        showlegend=False
    )
    
    st.plotly_chart(fig_energy, use_container_width=True)

# Summary statistics by facility type
st.markdown('<h4 style="color: #ffffff;">Facility Type Statistics</h4>', unsafe_allow_html=True)

# Add explanatory text with tooltips
st.markdown("""
    <p style="color: #cccccc; font-size: 13px; margin-bottom: 10px;">
        <strong>Total Energy:</strong> Sum of all facilities of this type &nbsp;|&nbsp; 
        <strong>Avg Energy:</strong> Average per facility &nbsp;|&nbsp; 
        <strong>Max Energy:</strong> Largest single facility of this type
    </p>
""", unsafe_allow_html=True)

type_stats = datacenter_df.groupby('facility_type', observed=True).agg({
    'provider': 'count',
    'energy_mw': ['sum', 'mean', 'max']
}).round(2)

type_stats.columns = ['Count', 'Total Energy (MW)', 'Avg Energy (MW)', 'Max Energy (MW)']
type_stats = type_stats.sort_values('Total Energy (MW)', ascending=False)

# Style the dataframe
st.dataframe(
    type_stats.style.format({
        'Total Energy (MW)': '{:,.0f}',
        'Avg Energy (MW)': '{:,.2f}',
        'Max Energy (MW)': '{:,.2f}'
    }),
    use_container_width=True
)

# Water Consumption Analysis
st.markdown("---")
st.markdown('<h3 style="color: #ffffff;">Estimated Water Consumption</h3>', unsafe_allow_html=True)
st.markdown('<p style="color: #ffffff; font-size: 14px;">Based on research by Li et al. (2025) and Mytton et al. (2021), water consumption varies by cooling method, climate, and facility type. These are conservative estimates.</p>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    # Water consumption by state (top 10)
    state_water = datacenter_df.groupby('state', observed=True).agg({
        'water_gallons_day': 'sum',
        'water_scarcity': 'first'
    }).reset_index()
    state_water = state_water.sort_values('water_gallons_day', ascending=False).head(10)
    
    # Convert to millions of gallons
    state_water['water_million_gal_day'] = state_water['water_gallons_day'] / 1_000_000
    
    fig_water_state = go.Figure(data=[go.Bar(
        x=state_water['state'],
        y=state_water['water_million_gal_day'],
        marker_color=['#FF0000' if ws >= 7 else '#FFA500' if ws >= 5 else '#00BFFF' 
                      for ws in state_water['water_scarcity']],
        text=[f"{v:.1f}M" for v in state_water['water_million_gal_day']],
        textposition='outside',
        textfont=dict(color='#ffffff', size=11),
        hovertemplate='<b>%{x}</b><br>%{y:.2f} million gallons/day<extra></extra>'
    )])
    
    fig_water_state.update_layout(
        title=dict(
            text="Top 10 States by Est. Water Consumption",
            font=dict(color='#ffffff', size=16)
        ),
        xaxis_title=dict(
            text="State",
            font=dict(color='#ffffff', size=12)
        ),
        yaxis_title=dict(
            text="Million Gallons per Day",
            font=dict(color='#ffffff', size=12)
        ),
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='#ffffff'),
        height=450,  # Increased from 400
        margin=dict(t=60, b=40, l=60, r=20),  # Added margin for top spacing
        xaxis=dict(
            gridcolor='#333333',
            tickfont=dict(color='#ffffff')
        ),
        yaxis=dict(
            gridcolor='#333333',
            tickfont=dict(color='#ffffff')
        ),
        showlegend=False
    )
    
    st.plotly_chart(fig_water_state, use_container_width=True)

with col2:
    # Water consumption by facility type
    type_water = datacenter_df.groupby('facility_type', observed=True)['water_gallons_day'].sum().reset_index()
    type_water = type_water.sort_values('water_gallons_day', ascending=False)
    type_water['water_million_gal_day'] = type_water['water_gallons_day'] / 1_000_000
    
    fig_water_type = go.Figure(data=[go.Bar(
        x=type_water['facility_type'],
        y=type_water['water_million_gal_day'],
        marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'][:len(type_water)],
        text=[f"{v:.1f}M" for v in type_water['water_million_gal_day']],
        textposition='outside',
        textfont=dict(color='#ffffff', size=11),
        hovertemplate='<b>%{x}</b><br>%{y:.2f} million gallons/day<extra></extra>'
    )])
    
    fig_water_type.update_layout(
        title=dict(
            text="Est. Water Consumption by Facility Type",
            font=dict(color='#ffffff', size=16)
        ),
        xaxis_title=dict(
            text="Facility Type",
            font=dict(color='#ffffff', size=12)
        ),
        yaxis_title=dict(
            text="Million Gallons per Day",
            font=dict(color='#ffffff', size=12)
        ),
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='#ffffff'),
        height=450,
        xaxis=dict(
            gridcolor='#333333',
            tickfont=dict(color='#ffffff')
        ),
        yaxis=dict(
            gridcolor='#333333',
            tickfont=dict(color='#ffffff')
        ),
        showlegend=False
    )
    
    st.plotly_chart(fig_water_type, use_container_width=True)

# Water consumption summary metrics
col1, col2, col3, col4 = st.columns(4)

total_water_gallons = datacenter_df['water_gallons_day'].sum()
total_water_million_gal = total_water_gallons / 1_000_000
total_water_billion_gal_year = (total_water_gallons * 365) / 1_000_000_000

with col1:
    st.markdown(f'<p class="metric-value" style="color: #ffffff; font-size: 20px;">{total_water_million_gal:,.0f}M gal/day</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #ffffff; font-weight: bold; font-size: 12px;">Total Est. Water Use</p>', unsafe_allow_html=True)

with col2:
    st.markdown(f'<p class="metric-value" style="color: #ffffff; font-size: 20px;">{total_water_billion_gal_year:.1f}B gal/year</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #ffffff; font-weight: bold; font-size: 12px;">Annual Consumption</p>', unsafe_allow_html=True)

with col3:
    high_scarcity_water = datacenter_df[datacenter_df['water_scarcity'] >= 7]['water_gallons_day'].sum() / 1_000_000
    st.markdown(f'<p class="metric-value" style="color: #FF6B6B; font-size: 20px;">{high_scarcity_water:,.0f}M gal/day</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #ffffff; font-weight: bold; font-size: 12px;">In High-Scarcity States</p>', unsafe_allow_html=True)

with col4:
    avg_per_facility = total_water_gallons / len(datacenter_df)
    st.markdown(f'<p class="metric-value" style="color: #ffffff; font-size: 20px;">{avg_per_facility:,.0f} gal/day</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #ffffff; font-weight: bold; font-size: 12px;">Avg per Facility</p>', unsafe_allow_html=True)

st.markdown('<p style="color: #aaaaaa; font-size: 13px; margin-top: 15px;"><em>Note: Water consumption estimates based on facility type, power usage, and regional climate. Actual usage varies by cooling technology (water vs. air cooling) and operational efficiency. Hyperscale facilities in hot climates may use 2-5 liters per kWh, while air-cooled facilities in cool climates may use &lt;1 liter per kWh.</em></p>', unsafe_allow_html=True)

# Analysis text
st.markdown("---")
st.markdown('<h3 style="color: #ffffff;">Summary</h3>', unsafe_allow_html=True)
st.markdown('<ul style="color: #ffffff;"><li><strong>{:.0f}%</strong> of US data centers are located in states with moderate to severe water scarcity</li></ul>'.format(100 * len(datacenter_df[datacenter_df['water_scarcity'] >= 5]) / len(datacenter_df)), unsafe_allow_html=True)
st.markdown('<ul style="color: #ffffff;"><li>Major cloud providers have significant infrastructure in California, Arizona, and Nevada - among the most water-stressed states</li></ul>', unsafe_allow_html=True)
st.markdown('<ul style="color: #ffffff;"><li>Data centers consume substantial water for cooling systems, with large facilities using <strong>millions of gallons per day</strong></li></ul>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<h3 style="color: #ffffff;">Data Sources & Citations</h3>', unsafe_allow_html=True)

st.markdown('<p style="color: #ffffff;"><strong>Data Sources - Data Center Locations</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><strong>Business Insider Investigation (2024-2025):</strong>
            <ul style="margin-top: 10px;">
                <li><a href="https://www.businessinsider.com/how-calculate-data-center-cost-environmental-impact-methodology-2025-6/" target="_blank" style="color: #00BFFF;">Investigation Methodology</a></li>
                <li><a href="https://www.businessinsider.com/data-center-water-use-crisis-drought-scarce-google-amazon-microsoft-2025-6/" target="_blank" style="color: #00BFFF;">Water Crisis Investigation</a></li>
            </ul>
        </li>
    </ul>
""", unsafe_allow_html=True)

st.markdown('<p style="color: #ffffff;"><strong>Water Consumption Research:</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><a href="https://www.sciencedirect.com/science/article/pii/S0921344925001892" target="_blank" style="color: #00BFFF;">Li et al. (2025)</a> - "Data center water consumption: A global perspective" - Resources, Conservation and Recycling</li>
        <li><a href="https://www.nature.com/articles/s41545-021-00101-w" target="_blank" style="color: #00BFFF;">Mytton et al. (2021)</a> - "Data centre water consumption" - Nature npj Clean Water</li>
        <li><strong>Typical Water Usage Rates:</strong>
            <ul style="margin-top: 10px;">
                <li><strong>Water-cooled facilities:</strong> 1-5 liters per kWh (0.26-1.3 gallons/kWh)</li>
                <li><strong>Air-cooled facilities:</strong> 0.1-1 liter per kWh (0.03-0.26 gallons/kWh)</li>
                <li><strong>Example:</strong> A 100 MW facility using water cooling consumes ~9-45 million liters/day (2.4-12 million gallons/day)</li>
                <li><strong>Regional Variation:</strong> Higher in hot climates (Arizona, Texas) vs. cooler regions (Oregon, Washington)</li>
            </ul>
        </li>
    </ul>
""", unsafe_allow_html=True)

st.markdown('<p style="color: #ffffff;"><strong>Water Scarcity & Environmental Data:</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><a href="https://www.usgs.gov/mission-areas/water-resources" target="_blank" style="color: #00BFFF;">USGS Water Resources</a> - United States Geological Survey water availability data</li>
        <li><a href="https://droughtmonitor.unl.edu/" target="_blank" style="color: #00BFFF;">U.S. Drought Monitor</a> - Current drought conditions and historical trends</li>
        <li><a href="https://www.wri.org/aqueduct" target="_blank" style="color: #00BFFF;">World Resources Institute Aqueduct</a> - Global water risk mapping and indicators</li>
        <li>State water source classifications based on primary surface water and groundwater dependencies</li>
    </ul>
""", unsafe_allow_html=True)


st.markdown('<p style="margin-top: 20px; font-size: 14px; color: #aaaaaa;"><em>This visualization incorporates data from Business Insider\'s investigation alongside public cloud provider information to provide a comprehensive view of US data center infrastructure and environmental impacts.</em></p>', unsafe_allow_html=True)
