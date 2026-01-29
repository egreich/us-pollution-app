import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import os
import json
from epa_data_loader import load_pollution_data_with_cache, get_legislation_timeline

# Page configuration
st.set_page_config(
    page_title="US Pollution Timeline",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Force dark theme
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("How does legislation impact pollution over time?")

st.markdown("""
Explore how air quality and pollution levels have changed across the United States over time, 
with key environmental legislation marked on the timeline.
""")

# Load data
@st.cache_data
def load_data():
    return load_pollution_data_with_cache()

@st.cache_data
def get_legislation():
    return get_legislation_timeline()

@st.cache_data
def load_state_boundaries():
    """Load US state boundaries GeoJSON"""
    # Using a simple US states GeoJSON URL
    url = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
    try:
        import requests
        response = requests.get(url, timeout=10)
        return response.json()
    except:
        return None

# Load data with error handling
try:
    pollution_data = load_data()
    legislation = get_legislation()
    st.success(f"Loaded {len(pollution_data)} records from EPA API")
except ValueError as e:
    st.error(f"Configuration Error\n\n{str(e)}")
    st.stop()
except RuntimeError as e:
    st.error(f"Data Loading Error\n\n{str(e)}")
    st.stop()
except Exception as e:
    st.error(f"Unexpected Error\n\n{str(e)}")
    st.exception(e)
    st.stop()

# Define base color scheme for different pollutants (neon palette)
pollutant_base_colors = {
    "PM2.5": [255, 20, 147],     # Neon Pink
    "Ozone": [0, 255, 255],      # Cyan
    "SO2": [255, 255, 0],        # Bright Yellow
    "NO2": [186, 85, 211],       # Neon Purple
    "CO": [57, 255, 20],         # Neon Green
}

# Get available years
available_years = sorted(pollution_data['year'].unique())

# Main title
st.title("US Air Pollution Visualization")
st.caption("Data from 40 major US cities")

# Year selection
selected_year = st.select_slider(
    "Select Year",
    options=available_years,
    value=available_years[-1]
)

# Filter data by year only (show all pollutants)
filtered_data = pollution_data[
    pollution_data['year'] == selected_year
].copy()

# Create two columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    # Add border styling around map
    st.markdown("""
    <style>
    [data-testid="stPyDeckChart"] {
        border: 2px solid #4a4a4a;
        border-radius: 8px;
        padding: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader(f"Pollutants in {selected_year}")
    # Create map visualization
    if not filtered_data.empty:
        # Normalize pollution values for visualization
        max_pollution = filtered_data['value'].max()
        min_pollution = filtered_data['value'].min()
        
        # Add jitter offset for each pollutant (increased for better separation)
        import numpy as np
        pollutant_offset = {
            "PM2.5": -0.25,
            "Ozone": -0.125,
            "SO2": 0.0,
            "NO2": 0.125,
            "CO": 0.25,
        }
        filtered_data['jitter_lat'] = filtered_data.apply(
            lambda row: row['latitude'] + pollutant_offset.get(row['pollutant'], 0), axis=1
        )
        filtered_data['jitter_lon'] = filtered_data.apply(
            lambda row: row['longitude'] + pollutant_offset.get(row['pollutant'], 0), axis=1
        )
        
        # Normalize heights per pollutant (since units differ)
        filtered_data['height'] = 0
        for pollutant in filtered_data['pollutant'].unique():
            mask = filtered_data['pollutant'] == pollutant
            pollutant_data = filtered_data[mask]
            max_val = pollutant_data['value'].max()
            if max_val > 0:
                normalized = pollutant_data['value'] / max_val
                filtered_data.loc[mask, 'height'] = normalized * 200000
        
        # Use solid colors per pollutant (no gradient)
        def get_solid_color(row):
            base_color = pollutant_base_colors.get(row['pollutant'], [255, 140, 0])
            return base_color + [230]  # Full opacity
        
        filtered_data['color'] = filtered_data.apply(get_solid_color, axis=1)
        
        # Create layers list
        layers = []
        
        # Add state boundaries layer
        state_geojson = load_state_boundaries()
        if state_geojson:
            layers.append(
                pdk.Layer(
                    "GeoJsonLayer",
                    data=state_geojson,
                    stroked=True,
                    filled=False,
                    line_width_min_pixels=2,
                    get_line_color=[200, 200, 200, 255],
                    get_line_width=3,
                    pickable=False,
                )
            )
        
        # Add 3D column/bar layer for pollution data
        layers.append(
            pdk.Layer(
                "ColumnLayer",
                data=filtered_data,
                get_position=["jitter_lon", "jitter_lat"],
                get_elevation="height",
                elevation_scale=2.5,
                radius=25000,
                get_fill_color="color",
                pickable=True,
                auto_highlight=True,
                extruded=True,
            )
        )
        
        # Set the initial view state with pitch for 3D view
        view_state = pdk.ViewState(
            latitude=37.0902,
            longitude=-95.7129,
            zoom=3.5,
            pitch=60,  # Increased tilt for more dramatic 3D effect
            bearing=0,
        )
        
        # Create the deck
        deck = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip={
                "html": "<b>Location:</b> {city}, {state}<br/>"
                        "<b>{pollutant}:</b> {value} {unit}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            },
            map_style="mapbox://styles/mapbox/dark-v9"
        )
        
        st.pydeck_chart(deck)
    else:
        available_years = sorted(pollution_data['year'].unique())
        st.warning(f"No data available for {selected_year}. Available years: {min(available_years)}-{max(available_years)}")

with col2:
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 600;
    }
    [data-testid="stMetricLabel"] {
        color: #e0e0e0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader("Pollution Statistics")
    
    if not filtered_data.empty:
        # Show statistics for each pollutant
        for pollutant in sorted(filtered_data['pollutant'].unique()):
            pollutant_data = filtered_data[filtered_data['pollutant'] == pollutant]
            avg_value = pollutant_data['value'].mean()
            unit = pollutant_data['unit'].iloc[0]
            color = pollutant_base_colors.get(pollutant, [255, 140, 0])
            color_hex = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            
            st.markdown(f"**<span style='color:{color_hex}; font-size: 18px;'>{pollutant}</span>**", unsafe_allow_html=True)
            st.metric("Average", f"{avg_value:.2f} {unit}")
    else:
        st.info("Select data to view statistics")

# Timeline section
st.markdown("---")
st.subheader("Pollution Trends & Legislative Timeline")

# Create plotly figure
fig = go.Figure()

# Add trend line for each pollutant
for pollutant in sorted(pollution_data['pollutant'].unique()):
    timeline_data = pollution_data[
        pollution_data['pollutant'] == pollutant
    ].groupby('year')['value'].mean().reset_index()
    
    pollutant_unit = pollution_data[pollution_data['pollutant'] == pollutant]['unit'].iloc[0]
    color = pollutant_base_colors.get(pollutant, [255, 140, 0])
    color_str = f'rgb({color[0]}, {color[1]}, {color[2]})'
    
    fig.add_trace(go.Scatter(
        x=timeline_data['year'],
        y=timeline_data['value'],
        mode='lines+markers',
        name=pollutant,
        line=dict(color=color_str, width=2),
        marker=dict(size=4),
        hovertemplate=f'<b>Year:</b> %{{x}}<br><b>{pollutant}:</b> %{{y:.2f}} {pollutant_unit}<extra></extra>'
    ))

# Add legislation markers
for _, law in legislation.iterrows():
    fig.add_vline(
        x=law['year'],
        line_dash="dash",
        line_color="red",
        annotation_text=law['abbrev'],
        annotation_position="top",
        annotation=dict(textangle=-90)
    )

# Update layout
fig.update_layout(
    xaxis_title="Year",
    yaxis_title="Pollution Level (varies by pollutant)",
    hovermode='x unified',
    height=400,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

st.plotly_chart(fig, use_container_width=True)

# Legislation details
with st.expander("View Legislation Details"):
    for _, law in legislation.iterrows():
        st.markdown(f"""
        **{law['year']} - {law['title']}**  
        {law['description']}
        """)
        st.markdown("---")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Data visualization showing the relationship between environmental policy and pollution levels</p>
</div>
""", unsafe_allow_html=True)
