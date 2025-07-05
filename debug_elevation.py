#!/usr/bin/env python3

import gpxpy
import sys
from pathlib import Path

def debug_elevation_scaling(original_file, scaled_file):
    """Debug elevation scaling by comparing original and scaled files."""

    def analyze_file(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)

        elevations = []
        ascent = 0
        descent = 0

        for track in gpx.tracks:
            for segment in track.segments:
                points = segment.points
                for i, point in enumerate(points):
                    if point.elevation is not None:
                        elevations.append(point.elevation)

                        if i > 0 and points[i-1].elevation is not None:
                            elev_change = point.elevation - points[i-1].elevation
                            if elev_change > 0:
                                ascent += elev_change
                            else:
                                descent += abs(elev_change)

        return {
            'elevations': elevations,
            'ascent': ascent,
            'descent': descent,
            'min_elev': min(elevations) if elevations else 0,
            'max_elev': max(elevations) if elevations else 0,
            'first_elev': elevations[0] if elevations else None,
            'last_elev': elevations[-1] if elevations else None
        }

    print("ELEVATION SCALING DEBUG")
    print("=" * 50)

    try:
        orig_data = analyze_file(original_file)
        print(f"ORIGINAL FILE: {Path(original_file).name}")
        print(f"  First elevation: {orig_data['first_elev']:.1f}m")
        print(f"  Last elevation:  {orig_data['last_elev']:.1f}m")
        print(f"  Min elevation:   {orig_data['min_elev']:.1f}m")
        print(f"  Max elevation:   {orig_data['max_elev']:.1f}m")
        print(f"  Elevation range: {orig_data['max_elev'] - orig_data['min_elev']:.1f}m")
        print(f"  Total ascent:    {orig_data['ascent']:.1f}m")
        print(f"  Total descent:   {orig_data['descent']:.1f}m")
        print(f"  Data points:     {len(orig_data['elevations'])}")

    except Exception as e:
        print(f"Error analyzing original file: {e}")
        return

    try:
        scaled_data = analyze_file(scaled_file)
        print(f"\nSCALED FILE: {Path(scaled_file).name}")
        print(f"  First elevation: {scaled_data['first_elev']:.1f}m")
        print(f"  Last elevation:  {scaled_data['last_elev']:.1f}m")
        print(f"  Min elevation:   {scaled_data['min_elev']:.1f}m")
        print(f"  Max elevation:   {scaled_data['max_elev']:.1f}m")
        print(f"  Elevation range: {scaled_data['max_elev'] - scaled_data['min_elev']:.1f}m")
        print(f"  Total ascent:    {scaled_data['ascent']:.1f}m")
        print(f"  Total descent:   {scaled_data['descent']:.1f}m")
        print(f"  Data points:     {len(scaled_data['elevations'])}")

        print(f"\nSCALING RATIOS:")
        if orig_data['ascent'] > 0:
            ascent_ratio = scaled_data['ascent'] / orig_data['ascent']
            print(f"  Ascent ratio:    {ascent_ratio:.3f} (scaled/original)")

        orig_range = orig_data['max_elev'] - orig_data['min_elev']
        scaled_range = scaled_data['max_elev'] - scaled_data['min_elev']
        if orig_range > 0:
            range_ratio = scaled_range / orig_range
            print(f"  Range ratio:     {range_ratio:.3f} (scaled/original)")

        # Check for suspicious elevation jumps
        print(f"\nELEVATION ANALYSIS:")
        print(f"  Original range:  {orig_range:.1f}m")
        print(f"  Scaled range:    {scaled_range:.1f}m")

        # Sample first 10 and last 10 elevations for comparison
        print(f"\nFIRST 10 ELEVATIONS:")
        print(f"  Original: {[f'{e:.1f}' for e in orig_data['elevations'][:10]]}")
        print(f"  Scaled:   {[f'{e:.1f}' for e in scaled_data['elevations'][:10]]}")

        if len(orig_data['elevations']) > 10:
            print(f"\nLAST 10 ELEVATIONS:")
            print(f"  Original: {[f'{e:.1f}' for e in orig_data['elevations'][-10:]]}")
            print(f"  Scaled:   {[f'{e:.1f}' for e in scaled_data['elevations'][-10:]]}")

    except Exception as e:
        print(f"Error analyzing scaled file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_elevation.py <original_file> <scaled_file>")
        sys.exit(1)

    debug_elevation_scaling(sys.argv[1], sys.argv[2])
