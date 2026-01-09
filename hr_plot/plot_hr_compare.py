import os
import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
from fitdecode import FitReader, FitDataMessage

DEBUG = True

# =========================
# Utils
# =========================
def normalize_time(t):
    return pd.to_datetime(t).tz_localize(None)


def mps_to_pace(mps):
    if mps is None or mps <= 0:
        return None
    return 1000.0 / (mps * 60.0)  # min/km

# =========================
# FIT loader (SAFE)
# =========================
def load_fit_for_plot(filepath):
    rows = []
    fname = os.path.basename(filepath)

    if DEBUG:
        print(f"🔍 FIT parse: {fname}")

    with FitReader(filepath) as fr:
        for frame in fr:
            if not isinstance(frame, FitDataMessage):
                continue
            if frame.name != "record":
                continue

            try:
                ts = frame.get_value("timestamp")
            except Exception:
                continue

            if ts is None:
                continue

            try:
                time = normalize_time(ts)
            except Exception:
                continue

            try:
                hr = frame.get_value("heart_rate")
            except Exception:
                hr = None

            try:
                speed = frame.get_value("speed")
            except Exception:
                speed = None

            rows.append({
                "time": time,
                "hr": hr,
                "pace": mps_to_pace(speed),
            })

    if DEBUG:
        print(f"✅ FIT rows: {len(rows)}")

    return pd.DataFrame(rows)



# =========================
# Garmin GPX loader
# =========================
def load_garmin_gpx_for_plot(filepath):
    rows = []
    fname = os.path.basename(filepath)

    if DEBUG:
        print(f"🔍 GPX parse: {fname}")

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ GPX XML error: {e}")
        return pd.DataFrame()

    ns = {
        "gpx": "http://www.topografix.com/GPX/1/1",
        "gpxtpx": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
    }

    trkpts = root.findall(".//gpx:trkpt", ns)

    if DEBUG:
        print(f"📍 trkpt count: {len(trkpts)}")

    for trkpt in trkpts:
        time_el = trkpt.find("gpx:time", ns)
        if time_el is None:
            continue

        hr = None
        speed = None

        ext = trkpt.find("gpx:extensions", ns)
        if ext is not None:
            hr_el = ext.find(".//gpxtpx:hr", ns)
            if hr_el is not None:
                hr = int(hr_el.text)

            speed_el = ext.find(".//gpxtpx:speed", ns)
            if speed_el is not None:
                speed = float(speed_el.text)

        rows.append({
            "time": normalize_time(time_el.text),
            "hr": hr,
            "pace": mps_to_pace(speed)
        })

    if DEBUG:
        print(f"✅ GPX rows: {len(rows)}")

    return pd.DataFrame(rows)


# =========================
# Load all FIT + GPX
# =========================
def load_all_for_plot(folder):
    data = {}

    print(f"📂 Scan folder: {folder}")

    for fname in sorted(os.listdir(folder)):
        path = os.path.join(folder, fname)

        if fname.lower().endswith(".fit"):
            df = load_fit_for_plot(path)

        elif fname.lower().endswith(".gpx"):
            df = load_garmin_gpx_for_plot(path)

        else:
            continue

        if df is None or df.empty:
            print(f"⚠️ EMPTY: {fname}")
            continue

        df = df.sort_values("time")
        data[fname] = df

        if DEBUG:
            print(df.head(3))

    return data


# =========================
# Plot
# =========================
def plot(data, metric, combined):
    if combined:
        fig, ax = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

        for name, df in data.items():
            ax[0].plot(df["time"], df["hr"], label=name)
            ax[1].plot(df["time"], df["pace"], label=name)

        ax[0].set_ylabel("Heart Rate (bpm)")
        ax[1].set_ylabel("Pace (min/km)")
        ax[1].invert_yaxis()
        ax[1].set_xlabel("Time")

        ax[0].legend()
        ax[1].legend()

        for a in ax:
            a.grid(True)

        plt.show()
        return

    metrics = [metric] if metric != "both" else ["hr", "pace"]

    for m in metrics:
        plt.figure(figsize=(14, 6))
        for name, df in data.items():
            plt.plot(df["time"], df[m], label=name)

        plt.ylabel("Heart Rate (bpm)" if m == "hr" else "Pace (min/km)")
        if m == "pace":
            plt.gca().invert_yaxis()

        plt.xlabel("Time")
        plt.title(m.upper())
        plt.legend()
        plt.grid(True)
        plt.show()


# =========================
# Main
# =========================
def main():
    parser = argparse.ArgumentParser(
        description="Compare HR / Pace from FIT & Garmin GPX files"
    )
    parser.add_argument("folder", nargs="?", default="data",
                        help="Folder containing .fit / .gpx files")
    parser.add_argument("--metric", choices=["hr", "pace", "both"],
                        default="both", help="Metric to plot")
    parser.add_argument("--combined", action="store_true",
                        help="HR + Pace on same figure")

    args = parser.parse_args()

    plot_data = load_all_for_plot(args.folder)
    if not plot_data:
        print("❌ No data to plot")
        sys.exit(1)

    plot(plot_data, args.metric, args.combined)


if __name__ == "__main__":
    main()
