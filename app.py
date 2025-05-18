import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import pydeck as pdk
import time
from datetime import datetime
import json
import geopandas as gpd

# ---------------------------
# PAGE HEADER
# ---------------------------
st.markdown("<h1 style='text-align: center; color: green;'>StayGreenPolymers</h1>", unsafe_allow_html=True)
st.markdown("## ♻️ Monthly PET Plastic Collection Progress")

# ---------------------------
# LOAD AND PROCESS DATA
# ---------------------------
df = pd.read_csv("sdata.csv")

# Geocoder setup
geolocator = Nominatim(user_agent="streamlit_map_app")

@st.cache_data
def geocode_location(location):
    try:
        time.sleep(1)  # avoid hitting API limits
        loc = geolocator.geocode(location)
        if loc:
            return loc.latitude, loc.longitude
    except:
        pass
    return None, None

# Geocode if missing
if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
    st.text("Geocoding locations...")
    df[['Latitude', 'Longitude']] = df['Location'].apply(lambda loc: pd.Series(geocode_location(loc)))
    df = df.dropna(subset=['Latitude', 'Longitude'])

# ---------------------------
# MONTHLY PROGRESS BAR
# ---------------------------
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df = df.dropna(subset=['Date'])

current_month = datetime.now().month
current_year = datetime.now().year

monthly_df = df[(df['Date'].dt.month == current_month) & (df['Date'].dt.year == current_year)]
total_quantity = monthly_df['Quantity (Tons)'].sum()
target = 30.0

st.markdown("### 🗓️ Current Month Collection Progress")
progress_pct = min(total_quantity / target, 1.0)
st.progress(progress_pct)
st.markdown(f"**{total_quantity:.2f} / {target} Tons collected in {datetime.now().strftime('%B %Y')}**")

# ---------------------------
# COLOR BY QUANTITY
# ---------------------------
def get_color(qty):
    if 1 <= qty <= 2:
        return [255, 0, 0]      # Red
    elif 3 <= qty <= 4:
        return [0, 0, 255]      # Blue
    elif 5 <= qty <= 8:
        return [0, 255, 0]      # Green
    elif 9 <= qty <= 10:
        return [255, 255, 255]  # White
    else:
        return [128, 128, 128]  # Gray

df['color'] = df['Quantity (Tons)'].apply(get_color)

# ---------------------------
# LOAD SALEM DISTRICT GEOJSON AND FILTER
# ---------------------------
@st.cache_data
def load_salem_boundary_and_filter_dealers():
    # Load GeoJSON file
    gdf = gpd.read_file("salem_district.geojson")

    st.write("Columns in Salem GeoJSON:", list(gdf.columns))
    # Check district column name, assume 'DISTRICT' or inspect columns

    district_col = None
    for col in gdf.columns:
        if gdf[col].dtype == 'object':
            unique_vals = gdf[col].str.lower().unique()
            if 'salem' in unique_vals:
                district_col = col
                break
    if district_col is None:
        st.error("District column with 'Salem' not found in GeoJSON.")
        return None, None

    # Filter Salem district polygon
    salem_gdf = gdf[gdf[district_col].str.lower() == 'salem']

    # Create unified polygon for containment check
    salem_polygon = salem_gdf.unary_union

    # Convert dealer df to GeoDataFrame for spatial filter
    dealers_gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
        crs=gdf.crs
    )

    # Filter dealers inside Salem polygon
    in_salem_mask = dealers_gdf.geometry.within(salem_polygon)
    salem_dealers = dealers_gdf[in_salem_mask].copy()

    return salem_gdf, salem_dealers

salem_gdf, salem_df = load_salem_boundary_and_filter_dealers()

# ---------------------------
# TOGGLE SWITCH FOR MAP VIEW
# ---------------------------
view_option = st.radio("Select Map View:", ("All Dealers Map", "Salem District Focus Map"))

# ---------------------------
# MAP CONFIGURATION
# ---------------------------
if view_option == "All Dealers Map":
    st.markdown("## 🗺️ All Dealers Map")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[Longitude, Latitude]',
        get_fill_color='color',
        get_radius=200,
        pickable=True,
        auto_highlight=True,
    )

    view_state = pdk.ViewState(
        latitude=df['Latitude'].mean(),
        longitude=df['Longitude'].mean(),
        zoom=10,
        pitch=0,
    )

    tooltip = {
        "html": """
        <b>Dealer:</b> {Dealer Name}<br/>
        <b>Phone:</b> {Phone Number}<br/>
        <b>Quantity:</b> {Quantity (Tons)} tons<br/>
        <b>Date:</b> {Date}<br/>
        <b>Location:</b> {Location}
        """,
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip
    )

    st.pydeck_chart(deck)

else:
    st.markdown("## 🟩 Salem District Focus Map")

    if salem_gdf is None or salem_df is None or salem_df.empty:
        st.warning("No dealers found within Salem district or Salem GeoJSON not loaded.")
    else:
        # Convert Salem GeoDataFrame to GeoJSON format
        salem_geojson = json.loads(salem_gdf.to_json())

        salem_layer = pdk.Layer(
            "ScatterplotLayer",
            data=salem_df,
            get_position='[Longitude, Latitude]',
            get_fill_color='color',
            get_radius=300,
            pickable=True,
            auto_highlight=True,
        )

        boundary_layer = pdk.Layer(
            "GeoJsonLayer",
            data=salem_geojson,
            get_fill_color='[0, 255, 0, 40]',  # Transparent green
            get_line_color='[0, 255, 0]',
            line_width_min_pixels=2
        )

        salem_view = pdk.ViewState(
            latitude=salem_df['Latitude'].mean(),
            longitude=salem_df['Longitude'].mean(),
            zoom=11.5,
            pitch=0,
        )

        tooltip = {
            "html": """
            <b>Dealer:</b> {Dealer Name}<br/>
            <b>Phone:</b> {Phone Number}<br/>
            <b>Quantity:</b> {Quantity (Tons)} tons<br/>
            <b>Date:</b> {Date}<br/>
            <b>Location:</b> {Location}
            """,
            "style": {
                "backgroundColor": "steelblue",
                "color": "white"
            }
        }

        deck_salem = pdk.Deck(
            layers=[boundary_layer, salem_layer],
            initial_view_state=salem_view,
            tooltip=tooltip,
            map_style="mapbox://styles/mapbox/light-v9",
        )

        st.pydeck_chart(deck_salem)
