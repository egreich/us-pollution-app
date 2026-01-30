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
    page_title="US Data Centers & Water Scarcity",
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
st.title("US Data Centers & Water Scarcity")
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

# Load data center locations (we'll create this)
@st.cache_data
def load_datacenter_data():
    """
    Load major US data center locations with calculated energy consumption
    Sources: Public information from major cloud providers, colocation facilities
    Energy calculated using: (Facility Size × Power Density × PUE) ÷ 1,000,000 = MW
    """
    datacenters = [
        # AWS Regions - Hyperscale facilities with older infrastructure
        {"name": "AWS US-East-1 (Virginia)", "provider": "AWS", "latitude": 38.9072, "longitude": -77.0369, "state": "Virginia", 
         "facility_sqft": 1_000_000, "power_density": 200, "pue": 1.5},  # Older region, higher PUE
        
        {"name": "AWS US-East-2 (Ohio)", "provider": "AWS", "latitude": 40.4173, "longitude": -82.9071, "state": "Ohio",
         "facility_sqft": 750_000, "power_density": 180, "pue": 1.3},
        
        {"name": "AWS US-West-1 (N. California)", "provider": "AWS", "latitude": 37.3541, "longitude": -121.9552, "state": "California",
         "facility_sqft": 850_000, "power_density": 190, "pue": 1.3},
        
        {"name": "AWS US-West-2 (Oregon)", "provider": "AWS", "latitude": 45.5152, "longitude": -122.6784, "state": "Oregon",
         "facility_sqft": 900_000, "power_density": 200, "pue": 1.2},  # Newer, more efficient
        
        # Google Cloud - Industry-leading efficiency
        {"name": "Google Iowa", "provider": "Google", "latitude": 41.2619, "longitude": -95.8608, "state": "Iowa",
         "facility_sqft": 600_000, "power_density": 180, "pue": 1.1},  # Google's efficient design
        
        {"name": "Google Oregon", "provider": "Google", "latitude": 45.5897, "longitude": -121.1789, "state": "Oregon",
         "facility_sqft": 750_000, "power_density": 180, "pue": 1.1},
        
        {"name": "Google South Carolina", "provider": "Google", "latitude": 33.3683, "longitude": -79.8056, "state": "South Carolina",
         "facility_sqft": 500_000, "power_density": 180, "pue": 1.1},
        
        {"name": "Google Virginia", "provider": "Google", "latitude": 36.8946, "longitude": -76.2595, "state": "Virginia",
         "facility_sqft": 650_000, "power_density": 180, "pue": 1.1},
        
        # Microsoft Azure - Modern efficient facilities
        {"name": "Azure East US (Virginia)", "provider": "Microsoft", "latitude": 37.3719, "longitude": -79.8164, "state": "Virginia",
         "facility_sqft": 800_000, "power_density": 190, "pue": 1.25},
        
        {"name": "Azure West US (California)", "provider": "Microsoft", "latitude": 37.7749, "longitude": -122.4194, "state": "California",
         "facility_sqft": 750_000, "power_density": 180, "pue": 1.25},
        
        {"name": "Azure Central US (Iowa)", "provider": "Microsoft", "latitude": 41.5868, "longitude": -93.6250, "state": "Iowa",
         "facility_sqft": 700_000, "power_density": 170, "pue": 1.2},
        
        {"name": "Azure South Central US (Texas)", "provider": "Microsoft", "latitude": 29.4241, "longitude": -98.4936, "state": "Texas",
         "facility_sqft": 750_000, "power_density": 170, "pue": 1.25},
        
        # Meta - Hyperscale optimized facilities
        {"name": "Meta Prineville (Oregon)", "provider": "Meta", "latitude": 44.2999, "longitude": -120.8342, "state": "Oregon",
         "facility_sqft": 900_000, "power_density": 180, "pue": 1.2},
        
        {"name": "Meta Forest City (N. Carolina)", "provider": "Meta", "latitude": 35.3387, "longitude": -81.8643, "state": "North Carolina",
         "facility_sqft": 800_000, "power_density": 180, "pue": 1.25},
        
        {"name": "Meta Altoona (Iowa)", "provider": "Meta", "latitude": 41.6545, "longitude": -93.4650, "state": "Iowa",
         "facility_sqft": 950_000, "power_density": 180, "pue": 1.2},
        
        # Oracle - Mid-tier cloud
        {"name": "Oracle Phoenix", "provider": "Oracle", "latitude": 33.4484, "longitude": -112.0740, "state": "Arizona",
         "facility_sqft": 350_000, "power_density": 150, "pue": 1.5},
        
        {"name": "Oracle Ashburn", "provider": "Oracle", "latitude": 39.0438, "longitude": -77.4874, "state": "Virginia",
         "facility_sqft": 400_000, "power_density": 150, "pue": 1.5},
        
        # Equinix - Major colocation facilities
        {"name": "Equinix Chicago", "provider": "Equinix", "latitude": 41.8781, "longitude": -87.6298, "state": "Illinois",
         "facility_sqft": 250_000, "power_density": 150, "pue": 1.6},  # Multi-tenant, less efficient
        
        {"name": "Equinix Dallas", "provider": "Equinix", "latitude": 32.7767, "longitude": -96.7970, "state": "Texas",
         "facility_sqft": 270_000, "power_density": 150, "pue": 1.6},
        
        {"name": "Equinix New York", "provider": "Equinix", "latitude": 40.7128, "longitude": -74.0060, "state": "New York",
         "facility_sqft": 300_000, "power_density": 150, "pue": 1.55},
        
        {"name": "Equinix Silicon Valley", "provider": "Equinix", "latitude": 37.3688, "longitude": -121.9851, "state": "California",
         "facility_sqft": 320_000, "power_density": 150, "pue": 1.55},
        
        {"name": "Equinix Los Angeles", "provider": "Equinix", "latitude": 34.0522, "longitude": -118.2437, "state": "California",
         "facility_sqft": 280_000, "power_density": 150, "pue": 1.55},
        
        # Digital Realty - Colocation
        {"name": "Digital Realty Atlanta", "provider": "Digital Realty", "latitude": 33.7490, "longitude": -84.3880, "state": "Georgia",
         "facility_sqft": 230_000, "power_density": 150, "pue": 1.6},
        
        {"name": "Digital Realty Phoenix", "provider": "Digital Realty", "latitude": 33.4484, "longitude": -112.0740, "state": "Arizona",
         "facility_sqft": 250_000, "power_density": 150, "pue": 1.6},
        
        {"name": "Digital Realty Portland", "provider": "Digital Realty", "latitude": 45.5152, "longitude": -122.6784, "state": "Oregon",
         "facility_sqft": 220_000, "power_density": 140, "pue": 1.6},
        
        # Switch - Exceptionally large campus
        {"name": "Switch Las Vegas", "provider": "Switch", "latitude": 36.1699, "longitude": -115.1398, "state": "Nevada",
         "facility_sqft": 2_000_000, "power_density": 140, "pue": 1.0},  # Claims PUE of 1.0
        
        # Apple - Renewable-focused
        {"name": "Apple Mesa (Arizona)", "provider": "Apple", "latitude": 33.4152, "longitude": -111.8315, "state": "Arizona",
         "facility_sqft": 650_000, "power_density": 170, "pue": 1.15},  # Efficient with renewables
        
        {"name": "Apple Reno (Nevada)", "provider": "Apple", "latitude": 39.5296, "longitude": -119.8138, "state": "Nevada",
         "facility_sqft": 700_000, "power_density": 170, "pue": 1.15},
        
        # Regional colocation hubs
        {"name": "Denver Colocation Hub", "provider": "Various", "latitude": 39.7392, "longitude": -104.9903, "state": "Colorado",
         "facility_sqft": 180_000, "power_density": 140, "pue": 1.6},
        
        {"name": "Seattle Colocation Hub", "provider": "Various", "latitude": 47.6062, "longitude": -122.3321, "state": "Washington",
         "facility_sqft": 200_000, "power_density": 140, "pue": 1.6},
        
        {"name": "Miami Colocation Hub", "provider": "Various", "latitude": 25.7617, "longitude": -80.1918, "state": "Florida",
         "facility_sqft": 170_000, "power_density": 140, "pue": 1.65},
    ]
    
    # Calculate energy_mw for each facility
    df = pd.DataFrame(datacenters)
    df['energy_mw'] = df.apply(lambda row: calculate_energy(row['facility_sqft'], row['power_density'], row['pue']), axis=1)
    
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

# Merge water source info with datacenters
datacenter_df = datacenter_df.merge(water_df, on='state', how='left')

# Water source colors - blue to red gradient based on scarcity
def get_water_source_color(scarcity):
    """
    Create a blue-to-red gradient based on water scarcity
    0 (abundant) = Deep Blue, 10 (severe) = Bright Red
    """
    # Normalize scarcity to 0-1 range
    normalized = scarcity / 10.0
    
    # Blue to red gradient
    red = int(255 * normalized)
    green = int(100 * (1 - normalized))
    blue = int(255 * (1 - normalized))
    
    return [red, green, blue]

# Add color based on water scarcity (gradient from blue to red)
datacenter_df['color'] = datacenter_df['water_scarcity'].apply(get_water_source_color)

# Create 3D visualization
st.subheader("Data Center Energy Consumption & Water Scarcity Map")

# Legend in a styled box
st.markdown("""
    <div style="background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 2px solid #333333; margin-bottom: 20px;">
        <h4 style="color: #ffffff; margin-top: 0;">Map Legend</h4>
        <table style="width: 59%; color: #ffffff;">
            <tr>
                <td style="padding: 5px;"><strong>Bar Colors:</strong></td>
                <td style="padding: 5px;">Blue-to-red gradient by water scarcity (Blue = abundant, Red = severe)</td>
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
    get_position=["longitude", "latitude"],
    get_elevation="energy_mw * 500",  # Height based on energy consumption
    elevation_scale=2,
    radius=25000,
    get_fill_color="color",
    pickable=True,
    auto_highlight=True,
    opacity=0.8,
)

# View state
view_state = pdk.ViewState(
    latitude=39.8283,
    longitude=-98.5795,
    zoom=3.5,
    pitch=60,
    bearing=0
)

# Tooltip
tooltip = {
    "html": "<b>{name}</b><br/>Provider: {provider}<br/>State: {state}<br/>Energy: {energy_mw} MW<br/>Water Source: {water_source}<br/>Water Scarcity: {water_scarcity}/10",
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
    height=350,
    margin=dict(t=40, b=40, l=60, r=20),
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

# Analysis text
st.markdown("---")
st.markdown('<h3 style="color: #ffffff;">Summary</h3>', unsafe_allow_html=True)
st.markdown('<ul style="color: #ffffff;"><li><strong>{:.0f}%</strong> of US data centers are located in states with moderate to severe water scarcity</li></ul>'.format(100 * len(datacenter_df[datacenter_df['water_scarcity'] >= 5]) / len(datacenter_df)), unsafe_allow_html=True)
st.markdown('<ul style="color: #ffffff;"><li>Major cloud providers have significant infrastructure in California, Arizona, and Nevada - among the most water-stressed states</li></ul>', unsafe_allow_html=True)
st.markdown('<ul style="color: #ffffff;"><li>Data centers consume substantial water for cooling systems, with large facilities using <strong>millions of gallons per day</strong> (<a href="https://www.nature.com/articles/s41545-021-00101-w" target="_blank" style="color: #00BFFF;">Nature study, 2021</a>)</li></ul>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<h3 style="color: #ffffff;">Data Sources</h3>', unsafe_allow_html=True)
st.markdown('<p style="color: #ffffff;"><strong>Data Center Locations & Energy Consumption:</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><a href="https://aws.amazon.com/about-aws/global-infrastructure/regions_az/" target="_blank" style="color: #00BFFF;">AWS Global Infrastructure</a> - Official AWS region locations</li>
        <li><a href="https://cloud.google.com/about/locations" target="_blank" style="color: #00BFFF;">Google Cloud Locations</a> - Google Cloud Platform data center regions</li>
        <li><a href="https://azure.microsoft.com/en-us/explore/global-infrastructure/geographies/" target="_blank" style="color: #00BFFF;">Microsoft Azure Geographies</a> - Azure data center locations</li>
        <li><a href="https://sustainability.fb.com/data-centers/" target="_blank" style="color: #00BFFF;">Meta Data Centers</a> - Meta/Facebook data center information</li>
        <li><a href="https://www.equinix.com/data-centers" target="_blank" style="color: #00BFFF;">Equinix Data Centers</a> - Global colocation facility locations</li>
        <li><a href="https://www.digitalrealty.com/data-centers" target="_blank" style="color: #00BFFF;">Digital Realty Data Centers</a> - Colocation and data center locations</li>
        <li><a href="https://www.datacenterdynamics.com/" target="_blank" style="color: #00BFFF;">Data Center Dynamics</a> - Industry news and facility information</li>
        <li>Energy estimates based on typical data center power consumption (30-300 MW range for hyperscale facilities)</li>
    </ul>
""", unsafe_allow_html=True)
st.markdown('<p style="color: #ffffff;"><strong>Water Scarcity Data:</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><a href="https://www.usgs.gov/mission-areas/water-resources" target="_blank" style="color: #00BFFF;">USGS Water Resources</a> - United States Geological Survey water data</li>
        <li><a href="https://droughtmonitor.unl.edu/" target="_blank" style="color: #00BFFF;">U.S. Drought Monitor</a> - Current drought conditions and historical data</li>
        <li><a href="https://www.wri.org/aqueduct" target="_blank" style="color: #00BFFF;">World Resources Institute Aqueduct</a> - Water risk mapping and indicators</li>
        <li>State water source classifications based on primary surface water and groundwater dependencies</li>
    </ul>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown('<h3 style="color: #ffffff;">Methodology: Energy Consumption Estimates</h3>', unsafe_allow_html=True)
st.markdown('<p style="color: #ffffff;">Energy consumption estimates are based on industry-standard power density calculations and facility size classifications:</p>', unsafe_allow_html=True)

st.markdown('<p style="color: #ffffff;"><strong>Hyperscale Data Centers (AWS, Google, Microsoft, Meta, Apple):</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><strong>Power Range:</strong> 100-280 MW per facility</li>
        <li><strong>Calculation Basis:</strong> Hyperscale facilities typically occupy 500,000-1,000,000+ sq ft with power density of 150-300 watts/sq ft</li>
        <li><strong>Example Math:</strong> 750,000 sq ft × 200 W/sq ft = 150,000,000 W = 150 MW</li>
        <li><strong>Adjustments:</strong> 
            <ul>
                <li>+20-30% for older regions with less efficient infrastructure (Virginia, California)</li>
                <li>-10-20% for newer facilities with advanced cooling and renewable energy (Oregon, Iowa)</li>
                <li>+50-80% for exceptionally large campuses (Switch Las Vegas = 280 MW for 2M+ sq ft facility)</li>
            </ul>
        </li>
        <li><strong>Sources:</strong> Industry reports indicate AWS us-east-1 (Virginia) uses 200-300 MW across multiple facilities; Google's Iowa facility reported ~120-150 MW; Meta's Prineville campus estimated 200+ MW</li>
    </ul>
""", unsafe_allow_html=True)

st.markdown('<p style="color: #ffffff;"><strong>Enterprise Colocation Facilities (Equinix, Digital Realty):</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><strong>Power Range:</strong> 30-75 MW per facility</li>
        <li><strong>Calculation Basis:</strong> Multi-tenant facilities typically 100,000-300,000 sq ft with 100-200 watts/sq ft power density</li>
        <li><strong>Example Math:</strong> 200,000 sq ft × 150 W/sq ft = 30,000,000 W = 30 MW</li>
        <li><strong>Adjustments:</strong>
            <ul>
                <li>Major metro hubs (NYC, Silicon Valley, LA): 65-75 MW (high-density multi-building campuses)</li>
                <li>Secondary markets (Chicago, Dallas, Atlanta): 50-65 MW (single large buildings)</li>
                <li>Regional facilities: 40-50 MW (smaller footprint, mixed use)</li>
            </ul>
        </li>
        <li><strong>Sources:</strong> Equinix publicly reports their largest facilities range 30-90 MW; Digital Realty's IBX facilities average 40-60 MW</li>
    </ul>
""", unsafe_allow_html=True)

st.markdown('<p style="color: #ffffff;"><strong>Mid-Tier Cloud Providers (Oracle):</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><strong>Power Range:</strong> 50-100 MW per facility</li>
        <li><strong>Calculation Basis:</strong> Regional cloud facilities typically 250,000-400,000 sq ft with 120-180 watts/sq ft</li>
        <li><strong>Example Math:</strong> 300,000 sq ft × 150 W/sq ft = 45,000,000 W = 45 MW, scaled to 80-90 MW for multi-building campuses</li>
    </ul>
""", unsafe_allow_html=True)

st.markdown('<p style="color: #ffffff;"><strong>General Formula Used:</strong></p>', unsafe_allow_html=True)
st.markdown("""
    <ul style="color: #ffffff; line-height: 1.8;">
        <li><strong>Base Calculation:</strong> Power (MW) = (Facility Size in sq ft × Power Density in W/sq ft) ÷ 1,000,000</li>
        <li><strong>Efficiency Factor:</strong> Multiply by PUE (Power Usage Effectiveness)
            <ul>
                <li>Modern facilities (2015+): PUE ≈ 1.2-1.3</li>
                <li>Older facilities (pre-2015): PUE ≈ 1.5-2.0</li>
                <li>Google, Apple: PUE ≈ 1.1-1.15</li>
            </ul>
        </li>
    </ul>
""", unsafe_allow_html=True)

st.markdown('<p style="margin-top: 20px; font-size: 14px; color: #aaaaaa;"><em>Note: This visualization is for educational and illustrative purposes. Data center energy consumption estimates are approximations based on facility size and publicly available information.</em></p>', unsafe_allow_html=True)
st.markdown('<p style="margin-top: 15px; font-size: 14px; color: #aaaaaa;"><em>Actual consumption varies significantly based on workload utilization (typically 40-80% of capacity), time of day, season, and specific tenant requirements. These estimates represent design capacity or typical peak load, not real-time consumption. Some facilities may have significantly different actual usage.</em></p>', unsafe_allow_html=True)
