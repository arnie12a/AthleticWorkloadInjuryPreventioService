
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.ndimage import median_filter, gaussian_filter1d
from garmin_fit_sdk import Decoder, Stream


# ==========================================
# CONFIGURATION
# ==========================================

FIT_FILE = "graysTorreysPeak.fit"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Distance over which to calculate slope
GRADE_WINDOW_METERS = 100

# Minimum sustained hill length
MIN_HILL_DISTANCE = 150

# Minimum gradient for hill classification
HILL_THRESHOLD = 3.0

# Elevation changes smaller than this are ignored
ELEVATION_THRESHOLD = 3.0


# ==========================================
# 1. READ GARMIN FIT FILE
# ==========================================

stream = Stream.from_file(FIT_FILE)
decoder = Decoder(stream)

messages, errors = decoder.read()

if errors:
    print("FIT decoding warnings:", errors)

records = messages.get("record_mesgs", [])

if not records:
    raise ValueError("No activity records found.")

df = pd.DataFrame(records)

print("Available FIT fields:")
print(df.columns.tolist())


# ==========================================
# 2. EXTRACT ELEVATION AND DISTANCE
# ==========================================

altitude_col = (
    "enhanced_altitude"
    if "enhanced_altitude" in df.columns
    else "altitude"
)

if altitude_col not in df.columns:
    raise ValueError("No elevation data in FIT file.")

if "distance" not in df.columns:
    raise ValueError("No distance data in FIT file.")

columns = ["distance", altitude_col]

if "heart_rate" in df.columns:
    columns.append("heart_rate")

if "timestamp" in df.columns:
    columns.append("timestamp")

df = df[columns].copy()

df = df.rename(columns={
    altitude_col: "elevation"
})

df["distance"] = pd.to_numeric(
    df["distance"], errors="coerce"
)

df["elevation"] = pd.to_numeric(
    df["elevation"], errors="coerce"
)

df = df.dropna(
    subset=["distance", "elevation"]
)

df = df.sort_values("distance")

# Remove duplicate distance measurements
df = df.drop_duplicates(
    subset=["distance"], keep="last"
)

df = df.reset_index(drop=True)

if len(df) < 3:
    raise ValueError("Not enough elevation records.")


# ==========================================
# 3. SMOOTH ELEVATION
# ==========================================

# First remove isolated elevation spikes
elevation = median_filter(
    df["elevation"].to_numpy(),
    size=5
)

# Then apply Gaussian smoothing
elevation = gaussian_filter1d(
    elevation.astype(float),
    sigma=3
)

df["smoothed_elevation"] = elevation

df["distance_km"] = df["distance"] / 1000


# ==========================================
# 4. CALCULATE ELEVATION GAIN / LOSS
# ==========================================

# Threshold small changes to reduce GPS noise
gain = 0.0
loss = 0.0

reference_elevation = elevation[0]

for current in elevation[1:]:
    change = current - reference_elevation

    if change >= ELEVATION_THRESHOLD:
        gain += change
        reference_elevation = current

    elif change <= -ELEVATION_THRESHOLD:
        loss += abs(change)
        reference_elevation = current

max_elevation = df["smoothed_elevation"].max()
min_elevation = df["smoothed_elevation"].min()

total_distance = df["distance_km"].max()


# ==========================================
# 5. CALCULATE HILL GRADIENT
# ==========================================

distances = df["distance"].to_numpy()
elevations = df["smoothed_elevation"].to_numpy()

grades = []

half_window = GRADE_WINDOW_METERS / 2

for distance in distances:

    left = np.searchsorted(
        distances, distance - half_window
    )

    right = np.searchsorted(
        distances, distance + half_window
    )

    right = min(right, len(distances) - 1)

    horizontal_distance = (
        distances[right] - distances[left]
    )

    elevation_change = (
        elevations[right] - elevations[left]
    )

    if horizontal_distance > 0:
        grade = (
            elevation_change / horizontal_distance
        ) * 100
    else:
        grade = 0

    grades.append(grade)

df["gradient_percent"] = grades

steepest_uphill = df["gradient_percent"].max()
steepest_downhill = df["gradient_percent"].min()


# ==========================================
# 6. IDENTIFY HILL SECTIONS
# ==========================================

def classify_gradient(grade):
    if grade >= HILL_THRESHOLD:
        return "Uphill"
    elif grade <= -HILL_THRESHOLD:
        return "Downhill"
    return "Flat"


df["terrain"] = df["gradient_percent"].apply(
    classify_gradient
)

# Find consecutive terrain sections
df["segment_id"] = (
    df["terrain"] != df["terrain"].shift()
).cumsum()

segments = []

for _, group in df.groupby("segment_id"):

    terrain = group["terrain"].iloc[0]

    start_distance = group["distance"].iloc[0]
    end_distance = group["distance"].iloc[-1]

    segment_distance = (
        end_distance - start_distance
    )

    if (
        terrain != "Flat"
        and segment_distance >= MIN_HILL_DISTANCE
    ):

        start_elevation = (
            group["smoothed_elevation"].iloc[0]
        )

        end_elevation = (
            group["smoothed_elevation"].iloc[-1]
        )

        segments.append({
            "terrain": terrain,
            "start_km": start_distance / 1000,
            "end_km": end_distance / 1000,
            "distance_m": segment_distance,
            "elevation_change_m": (
                end_elevation - start_elevation
            ),
            "avg_gradient_percent": (
                (end_elevation - start_elevation)
                / segment_distance * 100
            ),
            "max_gradient_percent": (
                group["gradient_percent"].max()
                if terrain == "Uphill"
                else group["gradient_percent"].min()
            )
        })

segments_df = pd.DataFrame(segments)


# ==========================================
# 7. PRINT SUMMARY
# ==========================================

print("\n========== HIKING ANALYSIS ==========")

print(f"Distance: {total_distance:.2f} km")
print(f"Elevation Gain: {gain:.1f} m")
print(f"Elevation Loss: {loss:.1f} m")
print(f"Highest Elevation: {max_elevation:.1f} m")
print(f"Lowest Elevation: {min_elevation:.1f} m")

print(
    f"Steepest Uphill: {steepest_uphill:.1f}%"
)

print(
    f"Steepest Downhill: {steepest_downhill:.1f}%"
)

print("\n========== HILL SEGMENTS ==========")

if not segments_df.empty:
    print(segments_df.to_string(index=False))
else:
    print("No sustained hills detected.")


# ==========================================
# 8. ELEVATION PROFILE
# ==========================================

plt.figure(figsize=(12, 5))

plt.plot(
    df["distance_km"],
    df["smoothed_elevation"],
    label="Elevation"
)

plt.fill_between(
    df["distance_km"],
    df["smoothed_elevation"].min(),
    df["smoothed_elevation"],
    alpha=0.2
)

plt.title("Garmin Hiking Elevation Profile")
plt.xlabel("Distance (km)")
plt.ylabel("Elevation (m)")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "elevation_profile.png",
    dpi=200
)

plt.show()


# ==========================================
# 9. GRADIENT PROFILE
# ==========================================

plt.figure(figsize=(12, 5))

plt.plot(
    df["distance_km"],
    df["gradient_percent"]
)

plt.axhline(
    HILL_THRESHOLD,
    linestyle="--",
    label="Uphill threshold"
)

plt.axhline(
    -HILL_THRESHOLD,
    linestyle="--",
    label="Downhill threshold"
)

plt.axhline(0, linewidth=0.8)

plt.title("Hill Gradient Along Hike")
plt.xlabel("Distance (km)")
plt.ylabel("Gradient (%)")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "hill_gradient.png",
    dpi=200
)

plt.show()


# ==========================================
# 10. HEART RATE VS ELEVATION
# ==========================================

if "heart_rate" in df.columns:

    df["heart_rate"] = pd.to_numeric(
        df["heart_rate"], errors="coerce"
    )

    if df["heart_rate"].notna().any():

        fig, ax1 = plt.subplots(figsize=(12, 5))

        ax1.plot(
            df["distance_km"],
            df["smoothed_elevation"],
            label="Elevation"
        )

        ax1.set_xlabel("Distance (km)")
        ax1.set_ylabel("Elevation (m)")

        ax2 = ax1.twinx()

        ax2.plot(
            df["distance_km"],
            df["heart_rate"],
            alpha=0.65,
            label="Heart Rate",
            color="red"
        )

        ax2.set_ylabel("Heart Rate (BPM)")

        plt.title("Heart Rate vs Elevation")
        plt.tight_layout()

        plt.savefig(
            OUTPUT_DIR / "heart_rate_elevation.png",
            dpi=200
        )

        plt.show()


# ==========================================
# 11. EXPORT RESULTS
# ==========================================

df.to_csv(
    OUTPUT_DIR / "hiking_data.csv",
    index=False
)

segments_df.to_csv(
    OUTPUT_DIR / "hill_segments.csv",
    index=False
)

print("\nAnalysis complete!")
print(f"Results saved to: {OUTPUT_DIR}")
