import argparse
import numpy as np
import pandas as pd
from fitparse import FitFile
from scipy.signal import correlate
import gpxpy
import gpxpy.gpx
from datetime import timedelta


# =========================
# Load FIT → DataFrame
# =========================
def load_fit_df(filepath):
    fitfile = FitFile(filepath)
    rows = []

    for rec in fitfile.get_messages("record"):
        v = rec.get_values()
        if "timestamp" not in v:
            continue

        rows.append({
            "time": pd.to_datetime(v["timestamp"]),
            "lat": v.get("position_lat"),
            "lon": v.get("position_long"),
            "ele": v.get("altitude"),
            "hr": v.get("heart_rate"),
            "cad": v.get("cadence"),
            "speed": v.get("speed"),
        })

    return pd.DataFrame(rows).sort_values("time")


# =========================
# HR preprocessing
# =========================
def prep_hr(df):
    d = df[["time", "hr"]].dropna().set_index("time")
    d = d.resample("1s").mean()
    d["hr"] = d["hr"].interpolate()
    d["hr"] = d["hr"].rolling(5, center=True).mean()
    return d.dropna()


# =========================
# Find offset by HR
# =========================
def find_offset(ref, bad, max_shift):
    a = bad["hr"].values
    b = ref["hr"].values

    corr = correlate(a - a.mean(), b - b.mean(), mode="full")
    lags = np.arange(-len(a) + 1, len(b))
    lag = lags[np.argmax(corr)]

    return int(np.clip(lag, -max_shift, max_shift))


# =========================
# Export Garmin GPX
# =========================
def export_garmin_gpx(df, output):
    gpx = gpxpy.gpx.GPX()
    trk = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(trk)
    seg = gpxpy.gpx.GPXTrackSegment()
    trk.segments.append(seg)

    for _, r in df.iterrows():
        if pd.isna(r["lat"]) or pd.isna(r["lon"]):
            continue

        p = gpxpy.gpx.GPXTrackPoint(
            latitude=r["lat"],
            longitude=r["lon"],
            elevation=r["ele"],
            time=r["time"].to_pydatetime()
        )

        ext = gpxpy.gpx.GPXExtensions()
        tpx = gpxpy.gpx.GPXExtension()
        tpx.tag = "gpxtpx:TrackPointExtension"

        if not pd.isna(r["hr"]):
            e = gpxpy.gpx.GPXExtension()
            e.tag = "gpxtpx:hr"
            e.text = str(int(r["hr"]))
            tpx.children.append(e)

        if not pd.isna(r["cad"]):
            e = gpxpy.gpx.GPXExtension()
            e.tag = "gpxtpx:cad"
            e.text = str(int(r["cad"]))
            tpx.children.append(e)

        ext.children.append(tpx)
        p.extensions.append(ext)
        seg.points.append(p)

    with open(output, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())

    print(f"✅ Garmin GPX saved: {output}")


# =========================
# Main
# =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fix FIT timestamp and export Garmin-style GPX",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--ref", help="FIT đúng time (dùng cho auto HR sync)")
    parser.add_argument("--bad", required=True, help="FIT sai time")
    parser.add_argument("--out", default="fixed.gpx")
    parser.add_argument("--max-shift", type=int, default=3600)

    parser.add_argument("--new-start",
                        help="Ép start time (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--offset",
                        type=int,
                        help="Shift time theo giây (+/-)")

    args = parser.parse_args()

    print("📥 Loading FIT...")
    bad_df = load_fit_df(args.bad)

    # =========================
    # Determine offset
    # =========================
    if args.new_start:
        new_start = pd.to_datetime(args.new_start)
        old_start = bad_df["time"].iloc[0]
        offset = int((new_start - old_start).total_seconds())
        print(f"⏱ Using new-start offset = {offset}s")

    elif args.offset is not None:
        offset = args.offset
        print(f"⏱ Using manual offset = {offset}s")

    else:
        if not args.ref:
            raise SystemExit("❌ Auto HR sync cần --ref")

        print("🧠 Auto syncing by HR overlap...")
        ref_df = load_fit_df(args.ref)
        ref_hr = prep_hr(ref_df)
        bad_hr = prep_hr(bad_df)
        offset = find_offset(ref_hr, bad_hr, args.max_shift)
        print(f"⏱ HR-detected offset = {offset}s")

    # =========================
    # Apply offset & export
    # =========================
    bad_df["time"] = bad_df["time"] + timedelta(seconds=offset)
    export_garmin_gpx(bad_df, args.out)
