
from garmin_fit_sdk import Decoder, Stream
from pyproj import Transformer
import pandas as pd
import numpy as np
import plotly.graph_objects as go

FIT_FILE = "graysTorreysPeak.fit"

# Decode FIT file
stream = Stream.from_file(FIT_FILE)
decoder = Decoder(stream)
messages, errors = decoder.read()

if errors:
    print("FIT warnings:", errors)

df = pd.DataFrame(messages.get("record_mesgs", []))

# Check required data
required = ["position_lat", "position_long", "timestamp"]
if not all(col in df.columns for col in required):
    raise ValueError("GPS coordinates or timestamps are missing.")

alt_col = (
    "enhanced_altitude"
    if "enhanced_altitude" in df.columns
    else "altitude"
)

if alt_col not in df.columns:
    raise ValueError("Elevation data is missing.")

df = df.dropna(
    subset=required + [alt_col]
).copy()

df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df = df.sort_values("timestamp").reset_index(drop=True)

# Convert FIT semicircles to degrees when necessary
def to_degrees(value):
    value = float(value)
    if abs(value) > 180:
        return value * 180 / (2 ** 31)
    return value

df["lat"] = df["position_lat"].apply(to_degrees)
df["lon"] = df["position_long"].apply(to_degrees)
df["elevation"] = pd.to_numeric(df[alt_col])

df = df[
    df["lat"].between(-90, 90)
    & df["lon"].between(-180, 180)
].copy()

if len(df) < 2:
    raise ValueError("Not enough valid GPS points.")

# Convert geographic coordinates to local meter coordinates
lat0 = df["lat"].iloc[0]
lon0 = df["lon"].iloc[0]
elev0 = df["elevation"].min()

transformer = Transformer.from_crs(
    "EPSG:4326",
    f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} "
    "+datum=WGS84 +units=m +type=crs",
    always_xy=True
)

x, y = transformer.transform(
    df["lon"].to_numpy(),
    df["lat"].to_numpy()
)

df["x"] = x
df["y"] = y
df["z"] = df["elevation"] - elev0

# Reduce number of animation frames
step = max(1, len(df) // 250)
indices = list(range(0, len(df), step))

if indices[-1] != len(df) - 1:
    indices.append(len(df) - 1)

# Full 3D route
route = go.Scatter3d(
    x=df["x"],
    y=df["y"],
    z=df["z"],
    mode="lines",
    line=dict(color="royalblue", width=6),
    name="Hiking route"
)

# Animated hiker marker
marker = go.Scatter3d(
    x=[df["x"].iloc[0]],
    y=[df["y"].iloc[0]],
    z=[df["z"].iloc[0]],
    mode="markers",
    marker=dict(size=7, color="red"),
    name="Hiker"
)

frames = []

for i in indices:
    frames.append(
        go.Frame(
            data=[
                go.Scatter3d(
                    x=[df["x"].iloc[i]],
                    y=[df["y"].iloc[i]],
                    z=[df["z"].iloc[i]],
                    mode="markers",
                    marker=dict(size=7, color="red")
                )
            ],
            traces=[1],
            name=str(i)
        )
    )

fig = go.Figure(
    data=[route, marker],
    frames=frames
)

fig.update_layout(
    title="Garmin 3D Hiking Animation",
    scene=dict(
        xaxis_title="East-West (m)",
        yaxis_title="North-South (m)",
        zaxis_title="Elevation above minimum (m)",
        aspectmode="data"
    ),
    updatemenus=[
        dict(
            type="buttons",
            buttons=[
                dict(
                    label="Play",
                    method="animate",
                    args=[
                        None,
                        {
                            "frame": {
                                "duration": 40,
                                "redraw": True
                            },
                            "transition": {"duration": 0},
                            "fromcurrent": True
                        }
                    ]
                ),
                dict(
                    label="Pause",
                    method="animate",
                    args=[
                        [None],
                        {
                            "mode": "immediate",
                            "frame": {"duration": 0},
                            "transition": {"duration": 0}
                        }
                    ]
                )
            ]
        )
    ]
)

fig.write_html("garmin_3d_hike.html", auto_open=True)

print("Created garmin_3d_hike.html")
