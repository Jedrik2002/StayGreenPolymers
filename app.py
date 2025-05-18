import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
import pydeck as pdk
import time
import datetime

# Load the CSV file
df = pd.read_csv("sdata.csv")

# Geocoder setup
geolocator = Nominatim(user_agent="streamlit_map_app")

@st.cache_data
def geocode_location(location):
    try:
        time.sleep(1)  # Avoid hitting API limits
        loc = geolocator.geocode(location)
        if loc:
            return loc.latitude, loc.longitude
    except:
        pass
    return None, None

# Show progress
st.text("Geocoding locations...")

# Add Latitude & Longitude columns
df[['Latitude', 'Longitude']] = df['Location'].apply(lambda loc: pd.Series(geocode_location(loc)))
df = df.dropna(subset=['Latitude', 'Longitude'])

# Assign color based on quantity
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
        return [128, 128, 128]  # Gray for unexpected values

df['color'] = df['Quantity (Tons)'].apply(get_color)

# Streamlit UI
st.title("Business Dealers Map")

# Pydeck layer
layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position='[Longitude, Latitude]',
    get_fill_color='color',
    get_radius=200,
    pickable=True,
    auto_highlight=True,
)

# Map view setup
view_state = pdk.ViewState(
    latitude=df['Latitude'].mean(),
    longitude=df['Longitude'].mean(),
    zoom=10,
    pitch=0,
)

# Tooltip config
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

# Render map
deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip
)

st.pydeck_chart(deck)

# ------------------------------
# Monthly Target Progress Tracker
# ------------------------------
st.markdown("### ♻️ Monthly PET Plastic Collection Progress")

# Convert 'Date' column to datetime
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

# Filter current month data
today = datetime.datetime.now()
monthly_target = 30  # tons
this_month = df[(df['Date'].dt.month == today.month) & (df['Date'].dt.year == today.year)]

# Calculate progress
collected = this_month['Quantity (Tons)'].sum()
progress = min(collected / monthly_target, 1.0)

# Display
st.metric(label="Progress This Month", value=f"{collected:.2f} / {monthly_target} Tons")
st.progress(progress)

# Optional message
if progress >= 1.0:
    st.success("🎉 Target achieved this month!")
elif progress >= 0.5:
    st.info("🚀 Over halfway there, keep going!")
else:
    st.warning("⏳ Off to a slow start. Let's collect more!")
