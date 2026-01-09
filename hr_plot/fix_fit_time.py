# python3 fix_fit_time.py bad.fit fixed.fit \
#   --new-start "2025-03-09 05:30:00"

# python3 fix_fit_time.py bad.fit fixed.fit \
#   --offset 3600
import argparse
from datetime import timedelta
from fitdecode import FitReader, FitWriter
from fitdecode.records import FitDataMessage


def parse_time(t):
    from pandas import to_datetime
    return to_datetime(t).to_pydatetime()


def fix_fit_time(
    input_fit,
    output_fit,
    new_start_time=None,
    offset_seconds=None
):
    with FitReader(input_fit) as reader, FitWriter(output_fit) as writer:

        first_timestamp = None

        for frame in reader:
            if isinstance(frame, FitDataMessage):
                ts = frame.get_value("timestamp")

                if ts and first_timestamp is None:
                    first_timestamp = parse_time(ts)

                if ts:
                    ts = parse_time(ts)

                    if new_start_time:
                        delta = new_start_time - first_timestamp
                        ts = ts + delta
                    elif offset_seconds:
                        ts = ts + timedelta(seconds=offset_seconds)

                    frame.set_value("timestamp", ts)

            writer.write(frame)

    print(f"✅ Fixed FIT saved to: {output_fit}")
