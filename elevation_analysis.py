#!/usr/bin/env python3

import gpxpy
import sys
from pathlib import Path

def analyze_elevation_detailed(filename):
    """Analyze elevation with different methods to match fitness platforms."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)

        print(f"\nDetailed elevation analysis for: {Path(filename).name}")
        print("=" * 60)

        # Method 1: Raw point-to-point (what my test script does)
        raw_ascent = 0
        raw_descent = 0

        # Method 2: With minimum threshold (like Garmin)
        threshold_ascent = 0
        threshold_descent = 0
        min_elevation_change = 3.0  # meters (common threshold)

        # Method 3: Using gpxpy built-in (what gpxscaler uses for analysis)
        gpxpy_ascent = 0
        gpxpy_descent = 0

        all_elevations = []

        for track in gpx.tracks:
            for segment in track.segments:
                if len(segment.points) < 2:
                    continue

                # Get gpxpy's calculation
                uphill, downhill = segment.get_uphill_downhill()
                if uphill:
                    gpxpy_ascent += uphill
                if downhill:
                    gpxpy_descent += downhill

                # Manual calculations
                points = segment.points
                for i in range(len(points)):
                    if points[i].elevation is not None:
                        all_elevations.append(points[i].elevation)

                # Raw calculation
                for i in range(1, len(points)):
                    if (points[i-1].elevation is not None and
                            points[i].elevation is not None):
                        elevation_change = points[i].elevation - points[i-1].elevation
                        if elevation_change > 0:
                            raw_ascent += elevation_change
                        else:
                            raw_descent += abs(elevation_change)

                # Threshold-based calculation (accumulate small changes)
                accumulated_gain = 0
                accumulated_loss = 0
                for i in range(1, len(points)):
                    if (points[i-1].elevation is not None and
                            points[i].elevation is not None):
                        elevation_change = points[i].elevation - points[i-1].elevation
                        if elevation_change > 0:
                            accumulated_gain += elevation_change
                            if accumulated_gain >= min_elevation_change:
                                threshold_ascent += accumulated_gain
                                accumulated_gain = 0
                        else:
                            accumulated_loss += abs(elevation_change)
                            if accumulated_loss >= min_elevation_change:
                                threshold_descent += accumulated_loss
                                accumulated_loss = 0

        # Statistics
        if all_elevations:
            min_elev = min(all_elevations)
            max_elev = max(all_elevations)
            elevation_range = max_elev - min_elev
        else:
            min_elev = max_elev = elevation_range = 0

        print(f"Elevation range: {min_elev:.1f}m to {max_elev:.1f}m (range: {elevation_range:.1f}m)")
        print(f"Total data points: {len(all_elevations)}")
        print()
        print("ASCENT CALCULATIONS:")
        print(f"  Raw point-to-point:     {raw_ascent:.1f}m")
        print(f"  With {min_elevation_change}m threshold:     {threshold_ascent:.1f}m")
        print(f"  GPXpy built-in:         {gpxpy_ascent:.1f}m")
        print()
        print("DESCENT CALCULATIONS:")
        print(f"  Raw point-to-point:     {raw_descent:.1f}m")
        print(f"  With {min_elevation_change}m threshold:     {threshold_descent:.1f}m")
        print(f"  GPXpy built-in:         {gpxpy_descent:.1f}m")

        return {
            'raw_ascent': raw_ascent,
            'threshold_ascent': threshold_ascent,
            'gpxpy_ascent': gpxpy_ascent,
            'elevation_range': elevation_range
        }

    except Exception as e:
        print(f"Error analyzing {filename}: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "stage-1-route.gpx"

    analyze_elevation_detailed(filename)
