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
    initial_sidebar_state="expanded"
)

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

# Sidebar controls
st.sidebar.header("Controls")

# Year selection
min_year = int(pollution_data['year'].min())
max_year = int(pollution_data['year'].max())
selected_year = st.sidebar.slider(
    "Select Year",
    min_value=min_year,
    max_value=max_year,
    value=max_year,
    step=1
)

# Pollutant selection
pollutants = pollution_data['pollutant'].unique()
selected_pollutant = st.sidebar.selectbox(
    "Select Pollutant",
    options=pollutants,
    index=0
)

# Filter data
filtered_data = pollution_data[
    (pollution_data['year'] == selected_year) & 
    (pollution_data['pollutant'] == selected_pollutant)
]

# Create two columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"{selected_pollutant} Levels in {selected_year}")
    st.caption("Data from 10 largest US cities by population")
    
    # Create map visualization
    if not filtered_data.empty:
        # Normalize pollution values for visualization
        max_pollution = filtered_data['value'].max()
        min_pollution = filtered_data['value'].min()
        
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
                    line_width_min_pixels=1,
                    get_line_color=[100, 100, 100, 200],
                    get_line_width=2,
                    pickable=False,
                )
            )
        
        # Add heatmap layer for pollution data
        layers.append(
            pdk.Layer(
                "HeatmapLayer",
                data=filtered_data,
                get_position=["longitude", "latitude"],
                get_weight="value",
                radiusPixels=60,
                intensity=1,
                threshold=0.05,
                opacity=0.8,
            )
        )
        
        # Add scatter plot layer for city markers
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=filtered_data,
                get_position=["longitude", "latitude"],
                get_radius=15000,
                get_fill_color=[255, 140, 0, 180],
                pickable=True,
                auto_highlight=True,
            )
        )
        
        # Set the initial view state
        view_state = pdk.ViewState(
            latitude=37.0902,
            longitude=-95.7129,
            zoom=3.5,
            pitch=0,
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
            map_style="mapbox://styles/mapbox/light-v9"
        )
        
        st.pydeck_chart(deck)
    else:
        st.warning("No data available for the selected filters.")

with col2:
    st.subheader("Pollution Statistics")
    
    if not filtered_data.empty:
        avg_value = filtered_data['value'].mean()
        max_value = filtered_data['value'].max()
        min_value = filtered_data['value'].min()
        unit = filtered_data['unit'].iloc[0]
        
        st.metric("Average Level", f"{avg_value:.2f} {unit}")
        st.metric("Maximum", f"{max_value:.2f} {unit}")
        st.metric("Minimum", f"{min_value:.2f} {unit}")
    else:
        st.info("Select data to view statistics")

# Timeline section
st.markdown("---")
st.subheader("Pollution Trends & Legislative Timeline")

# Create timeline data for the selected pollutant
timeline_data = pollution_data[
    pollution_data['pollutant'] == selected_pollutant
].groupby('year')['value'].mean().reset_index()

# Get unit for the selected pollutant
pollutant_unit = pollution_data[pollution_data['pollutant'] == selected_pollutant]['unit'].iloc[0]

# Create plotly figure
fig = go.Figure()

# Add pollution trend line
fig.add_trace(go.Scatter(
    x=timeline_data['year'],
    y=timeline_data['value'],
    mode='lines+markers',
    name=f'{selected_pollutant} Average',
    line=dict(color='#1f77b4', width=3),
    marker=dict(size=6),
    hovertemplate=f'<b>Year:</b> %{{x}}<br><b>Average:</b> %{{y:.2f}} {pollutant_unit}<extra></extra>'
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
    yaxis_title=f"{selected_pollutant} Level ({pollutant_unit})",
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
