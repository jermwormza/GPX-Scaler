#!/usr/bin/env python3
"""
GPXScaler - A tool to scale GPX routes in distance and elevation with coordinate relocation.
"""

import os
import sys
import argparse
import glob
import math
import re
import requests
from pathlib import Path

try:
    import gpxpy
    import gpxpy.gpx
except ImportError:
    print("Error: gpxpy library not found. Please install it with: pip install gpxpy")
    sys.exit(1)


class GPXScaler:
    def __init__(self):
        self.gpx_files = []
        self.route_stats = {}

    def extract_stage_number(self, filename):
        """Extract stage number from filename for proper numerical sorting."""
        # Look for patterns like "stage-1-", "stage-10-", etc.
        match = re.search(r'stage-(\d+)', filename.lower())
        if match:
            return int(match.group(1))
        # If no stage number found, return filename for alphabetical sort
        return float('inf'), filename

    def find_gpx_files(self, folder_path):
        """Find all GPX files in the specified folder."""
        folder = Path(folder_path)
        if not folder.exists():
            print(f"Error: Folder '{folder_path}' does not exist.")
            return False

        self.gpx_files = list(folder.glob("*.gpx"))
        if not self.gpx_files:
            print(f"No GPX files found in '{folder_path}'")
            return False

        print(f"Found {len(self.gpx_files)} GPX files:")
        for gpx_file in self.gpx_files:
            print(f"  - {gpx_file.name}")
        return True

    def calculate_distance(self, point1, point2):
        """Calculate distance between two GPS points using Haversine formula."""
        R = 6371000  # Earth radius in meters

        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def calculate_bearing(self, point1, point2):
        """Calculate bearing (direction) from point1 to point2 in radians."""
        lat1 = math.radians(point1.latitude)
        lat2 = math.radians(point2.latitude)
        dlon = math.radians(point2.longitude - point1.longitude)

        x = math.sin(dlon) * math.cos(lat2)
        y = (math.cos(lat1) * math.sin(lat2) -
             math.sin(lat1) * math.cos(lat2) * math.cos(dlon))

        bearing = math.atan2(x, y)
        return bearing

    def calculate_destination_point(self, lat, lon, bearing, distance):
        """Calculate destination point given start point, bearing and distance."""
        R = 6371000  # Earth radius in meters

        lat1 = math.radians(lat)
        lon1 = math.radians(lon)

        lat2 = math.asin(math.sin(lat1) * math.cos(distance/R) +
                         math.cos(lat1) * math.sin(distance/R) * math.cos(bearing))

        lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(distance/R) * math.cos(lat1),
                                 math.cos(distance/R) - math.sin(lat1) * math.sin(lat2))

        return math.degrees(lat2), math.degrees(lon2)

    def analyze_gpx_file(self, gpx_file):
        """Analyze a GPX file to extract distance and elevation statistics."""
        try:
            with open(gpx_file, 'r') as f:
                gpx = gpxpy.parse(f)

            total_distance = 0
            total_ascent = 0
            total_descent = 0

            # Process tracks
            for track in gpx.tracks:
                for segment in track.segments:
                    points = segment.points
                    if len(points) < 2:
                        continue

                    for i in range(1, len(points)):
                        # Calculate distance
                        distance = self.calculate_distance(points[i-1], points[i])
                        total_distance += distance

                        # Calculate elevation change
                        if points[i-1].elevation is not None and points[i].elevation is not None:
                            elevation_change = points[i].elevation - points[i-1].elevation
                            if elevation_change > 0:
                                total_ascent += elevation_change
                            else:
                                total_descent += abs(elevation_change)

            # Process routes (if any)
            for route in gpx.routes:
                points = route.points
                if len(points) < 2:
                    continue

                for i in range(1, len(points)):
                    distance = self.calculate_distance(points[i-1], points[i])
                    total_distance += distance

                    if points[i-1].elevation is not None and points[i].elevation is not None:
                        elevation_change = points[i].elevation - points[i-1].elevation
                        if elevation_change > 0:
                            total_ascent += elevation_change
                        else:
                            total_descent += abs(elevation_change)

            return {
                'distance_km': total_distance / 1000,
                'ascent_m': total_ascent,
                'descent_m': total_descent
            }

        except Exception as e:
            print(f"Error analyzing {gpx_file}: {e}")
            return None

    def analyze_all_files(self):
        """Analyze all found GPX files and display statistics."""
        print("\n" + "="*80)
        print("GPX ROUTE ANALYSIS")
        print("="*80)

        # Analyze all files first
        for gpx_file in self.gpx_files:
            stats = self.analyze_gpx_file(gpx_file)
            if stats:
                self.route_stats[gpx_file] = stats

        # Display results in table format
        if self.route_stats:
            print(f"\n{'Route Name':<35} {'Distance (km)':<15} {'Ascent (m)':<12} {'Descent (m)':<12}")
            print("-" * 80)

            # Sort routes by stage number (numerical order)
            sorted_routes = sorted(self.route_stats.items(),
                                   key=lambda x: self.extract_stage_number(x[0].name))

            for gpx_file, stats in sorted_routes:
                filename = gpx_file.name
                if len(filename) > 34:
                    filename = filename[:31] + "..."
                print(f"{filename:<35} {stats['distance_km']:<15.2f} {stats['ascent_m']:<12.0f} {stats['descent_m']:<12.0f}")

            # Summary
            total_distance = sum(stats['distance_km'] for stats in self.route_stats.values())
            total_ascent = sum(stats['ascent_m'] for stats in self.route_stats.values())
            total_descent = sum(stats['descent_m'] for stats in self.route_stats.values())

            print("-" * 80)
            print(f"{'TOTAL:':<35} {total_distance:<15.2f} {total_ascent:<12.0f} {total_descent:<12.0f}")
            print("="*80)

    def get_current_location(self):
        """Attempt to get current device location."""
        try:
            # Try ipapi.co for location based on IP
            response = requests.get('http://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('latitude'), data.get('longitude')
        except:
            pass

        try:
            # Alternative: ip-api.com
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return data.get('lat'), data.get('lon')
        except:
            pass

        return None, None

    def get_elevation(self, lat, lon):
        """Get elevation at given coordinates using online elevation API."""
        try:
            # Try Open-Elevation API (free, no API key required)
            url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    elevation = data['results'][0].get('elevation')
                    if elevation is not None:
                        print(f"Found real elevation at starting coordinates: {elevation}m")
                        return elevation
        except Exception as e:
            print(f"Warning: Could not get elevation from Open-Elevation API: {e}")

        try:
            # Fallback: Try elevation-api.io (also free)
            url = f"https://elevation-api.io/api/elevation?points=({lat},{lon})"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('elevations') and len(data['elevations']) > 0:
                    elevation = data['elevations'][0].get('elevation')
                    if elevation is not None:
                        print(f"Found real elevation at starting coordinates: {elevation}m")
                        return elevation
        except Exception as e:
            print(f"Warning: Could not get elevation from elevation-api.io: {e}")

        print("Warning: Could not retrieve elevation data. Using original base elevation.")
        return None

    def calculate_adjusted_scale(self, original_distance_km, desired_scale, min_distance_km):
        """Calculate adjusted scale factor to meet minimum distance requirement."""
        if min_distance_km is None:
            return desired_scale

        scaled_distance = original_distance_km * desired_scale

        if scaled_distance < min_distance_km:
            # Adjust scale to meet minimum distance
            adjusted_scale = min_distance_km / original_distance_km
            return adjusted_scale
        else:
            # Use desired scale as it already meets minimum
            return desired_scale

    def preview_scaling_results(self, scale_factor, min_distance_km=None):
        """Preview what the scaling results would be and allow adjustments."""
        print("\n" + "="*80)
        print("SCALING PREVIEW")
        print("="*80)
        print(f"Scale factor: {scale_factor}")
        if min_distance_km:
            print(f"Minimum distance: {min_distance_km} km")

        print(f"\n{'Route Name':<35} {'Original (km)':<13} {'Scaled (km)':<12} {'Ascent (m)':<12} {'Descent (m)':<12}")
        print("-" * 80)

        # Sort routes by stage number (numerical order)
        sorted_routes = sorted(self.route_stats.items(),
                               key=lambda x: self.extract_stage_number(x[0].name))

        total_original_distance = 0
        total_scaled_distance = 0
        total_scaled_ascent = 0
        total_scaled_descent = 0

        for gpx_file, stats in sorted_routes:
            original_distance = stats['distance_km']
            actual_scale = self.calculate_adjusted_scale(original_distance, scale_factor, min_distance_km)
            scaled_distance = original_distance * actual_scale
            scaled_ascent = stats['ascent_m'] * actual_scale
            scaled_descent = stats['descent_m'] * actual_scale

            filename = gpx_file.name
            if len(filename) > 34:
                filename = filename[:31] + "..."

            print(f"{filename:<35} {original_distance:<13.2f} {scaled_distance:<12.2f} {scaled_ascent:<12.0f} {scaled_descent:<12.0f}")

            total_original_distance += original_distance
            total_scaled_distance += scaled_distance
            total_scaled_ascent += scaled_ascent
            total_scaled_descent += scaled_descent

        print("-" * 80)
        print(f"{'TOTAL:':<35} {total_original_distance:<13.2f} {total_scaled_distance:<12.2f} {total_scaled_ascent:<12.0f} {total_scaled_descent:<12.0f}")
        print("="*80)

        return total_scaled_distance, total_scaled_ascent, total_scaled_descent

    def scale_gpx_file(self, gpx_file, scale_factor, start_lat, start_lon, min_distance_km=None):
        """Scale a GPX file and save the result."""
        try:
            with open(gpx_file, 'r') as f:
                gpx = gpxpy.parse(f)

            # Get original stats to calculate adjusted scale if needed
            if min_distance_km is not None:
                if gpx_file in self.route_stats:
                    original_distance = self.route_stats[gpx_file]['distance_km']
                    actual_scale = self.calculate_adjusted_scale(original_distance, scale_factor, min_distance_km)
                    if actual_scale != scale_factor:
                        print(f"Adjusting scale for {gpx_file.name}: {scale_factor:.3f} → {actual_scale:.3f} (to meet {min_distance_km}km minimum)")
                        scale_factor = actual_scale

            # Find the first point to use as reference
            first_point = None
            for track in gpx.tracks:
                for segment in track.segments:
                    if segment.points:
                        first_point = segment.points[0]
                        break
                if first_point:
                    break

            if not first_point:
                for route in gpx.routes:
                    if route.points:
                        first_point = route.points[0]
                        break

            if not first_point:
                print(f"Warning: No points found in {gpx_file.name}")
                return False

            # Get the starting elevation for scaling reference
            base_elevation = first_point.elevation if first_point.elevation is not None else 0

            # Get real elevation at starting coordinates
            real_elevation = self.get_elevation(start_lat, start_lon)
            if real_elevation is not None:
                # Use real elevation as the new base
                new_base_elevation = real_elevation
                print(f"Using real elevation {real_elevation}m as base for {gpx_file.name}")
            else:
                # Fallback to original elevation
                new_base_elevation = base_elevation

            # Scale tracks - properly scale the route path using vector-based scaling
            for track in gpx.tracks:
                for segment in track.segments:
                    if len(segment.points) < 2:
                        continue

                    # Store original points for reference
                    original_points = [gpxpy.gpx.GPXTrackPoint(p.latitude, p.longitude, p.elevation)
                                     for p in segment.points]

                    # Set first point to new starting location
                    segment.points[0].latitude = start_lat
                    segment.points[0].longitude = start_lon
                    segment.points[0].elevation = new_base_elevation

                    # Scale each subsequent point based on the vector from the previous point
                    for i in range(1, len(segment.points)):
                        # Get the previous point (already scaled)
                        prev_point = segment.points[i-1]

                        # Calculate the original vector from previous to current point
                        original_distance = self.calculate_distance(original_points[i-1], original_points[i])
                        original_bearing = self.calculate_bearing(original_points[i-1], original_points[i])

                        # Scale the distance vector
                        scaled_distance = original_distance * scale_factor

                        # Calculate new position using scaled vector from previous scaled point
                        new_lat, new_lon = self.calculate_destination_point(
                            prev_point.latitude, prev_point.longitude,
                            original_bearing, scaled_distance
                        )

                        # Update point position
                        segment.points[i].latitude = new_lat
                        segment.points[i].longitude = new_lon

                        # Scale elevation change from previous point
                        if (original_points[i-1].elevation is not None and
                            original_points[i].elevation is not None):
                            original_elevation_change = original_points[i].elevation - original_points[i-1].elevation
                            scaled_elevation_change = original_elevation_change * scale_factor
                            segment.points[i].elevation = prev_point.elevation + scaled_elevation_change
                        else:
                            # If no elevation data, keep same as previous
                            segment.points[i].elevation = prev_point.elevation

            # Scale routes using the same vector-based logic as tracks
            for route in gpx.routes:
                if len(route.points) < 2:
                    continue

                # Store original points for reference
                original_points = [gpxpy.gpx.GPXRoutePoint(p.latitude, p.longitude, p.elevation)
                                 for p in route.points]

                # Set first point to new starting location
                route.points[0].latitude = start_lat
                route.points[0].longitude = start_lon
                route.points[0].elevation = new_base_elevation

                # Scale each subsequent point based on vector from previous point
                for i in range(1, len(route.points)):
                    # Get the previous point (already scaled)
                    prev_point = route.points[i-1]

                    # Calculate original vector from previous to current point
                    original_distance = self.calculate_distance(
                        original_points[i-1], original_points[i])
                    original_bearing = self.calculate_bearing(
                        original_points[i-1], original_points[i])

                    # Scale the distance vector
                    scaled_distance = original_distance * scale_factor

                    # Calculate new position using scaled vector from previous
                    new_lat, new_lon = self.calculate_destination_point(
                        prev_point.latitude, prev_point.longitude,
                        original_bearing, scaled_distance
                    )

                    # Update point position
                    route.points[i].latitude = new_lat
                    route.points[i].longitude = new_lon

                    # Scale elevation change from previous point
                    if (original_points[i-1].elevation is not None and
                            original_points[i].elevation is not None):
                        original_elevation_change = (
                            original_points[i].elevation -
                            original_points[i-1].elevation)
                        scaled_elevation_change = (
                            original_elevation_change * scale_factor)
                        route.points[i].elevation = (
                            prev_point.elevation + scaled_elevation_change)
                    else:
                        # If no elevation data, keep same as previous
                        route.points[i].elevation = prev_point.elevation

            # Generate output filename
            scale_str = str(scale_factor).replace('.', '')
            output_file = gpx_file.parent / (
                f"{gpx_file.stem}_scaled_{scale_str}.gpx")

            # Save scaled GPX
            with open(output_file, 'w') as f:
                f.write(gpx.to_xml())

            print(f"Scaled {gpx_file.name} → {output_file.name}")
            return True

        except Exception as e:
            print(f"Error scaling {gpx_file.name}: {e}")
            return False

    def scale_all_files(self, scale_factor, start_lat, start_lon, min_distance_km=None):
        """Scale all GPX files."""
        print(f"\nScaling all files by factor {scale_factor}")
        if min_distance_km:
            print(f"Minimum distance requirement: {min_distance_km} km")
        print(f"New starting coordinates: {start_lat:.6f}, {start_lon:.6f}")
        print("\nProcessing files...")

        success_count = 0
        for gpx_file in self.gpx_files:
            if self.scale_gpx_file(gpx_file, scale_factor, start_lat, start_lon, min_distance_km):
                success_count += 1

        print(f"\nCompleted: {success_count}/{len(self.gpx_files)} files processed successfully.")


def get_user_input():
    """Get user input for interactive mode."""
    # Get folder
    folder = input(f"\nEnter folder path (or press Enter for current directory): ").strip()
    if not folder:
        folder = "."

    scaler = GPXScaler()
    if not scaler.find_gpx_files(folder):
        return None

    # Analyze files
    scaler.analyze_all_files()

    # Get scale factor and minimum distance with preview
    while True:
        # Get scale factor
        while True:
            try:
                scale_input = input(f"\nEnter scale factor (e.g., 0.5 for half size, 2.0 for double): ").strip()
                scale_factor = float(scale_input)
                if scale_factor <= 0:
                    print("Scale factor must be positive.")
                    continue
                break
            except ValueError:
                print("Please enter a valid number.")

        # Get minimum distance (optional)
        min_distance_km = None
        min_dist_input = input("\nEnter minimum distance in km (or press Enter to skip): ").strip()
        if min_dist_input:
            try:
                min_distance_km = float(min_dist_input)
                if min_distance_km <= 0:
                    print("Warning: Minimum distance should be positive.")
                    min_distance_km = None
            except ValueError:
                print("Invalid minimum distance, skipping minimum distance requirement.")
                min_distance_km = None

        # Show preview
        scaler.preview_scaling_results(scale_factor, min_distance_km)

        # Ask if user wants to proceed or adjust
        choice = input("\nProceed with these settings? (y/n) or 'a' to adjust: ").strip().lower()
        if choice in ['y', 'yes', '']:
            break
        elif choice in ['a', 'adjust']:
            continue
        elif choice in ['n', 'no']:
            print("Operation cancelled.")
            return None
        else:
            print("Please enter 'y' to proceed, 'n' to cancel, or 'a' to adjust.")
            continue

    # Get starting coordinates
    print(f"\nAttempting to detect current location...")
    current_lat, current_lon = scaler.get_current_location()

    if current_lat and current_lon:
        print(f"Detected location: {current_lat:.6f}, {current_lon:.6f}")
        use_current = input("Use this as starting coordinates? (y/n): ").strip().lower()
        if use_current in ['y', 'yes', '']:
            return scaler, scale_factor, current_lat, current_lon, min_distance_km

    # Manual coordinate input
    while True:
        try:
            lat_input = input("Enter starting latitude: ").strip()
            start_lat = float(lat_input)
            if not (-90 <= start_lat <= 90):
                print("Latitude must be between -90 and 90.")
                continue
            break
        except ValueError:
            print("Please enter a valid latitude.")

    while True:
        try:
            lon_input = input("Enter starting longitude: ").strip()
            start_lon = float(lon_input)
            if not (-180 <= start_lon <= 180):
                print("Longitude must be between -180 and 180.")
                continue
            break
        except ValueError:
            print("Please enter a valid longitude.")

    return scaler, scale_factor, start_lat, start_lon, min_distance_km


def main():
    parser = argparse.ArgumentParser(
        description="Scale GPX routes in distance and elevation with coordinate relocation"
    )
    parser.add_argument('--folder', default='.', help='Folder containing GPX files (default: current directory)')
    parser.add_argument('--scale', type=float, help='Scaling factor for distance and elevation')
    parser.add_argument('--min-distance', type=float, help='Minimum distance in km (scale will be adjusted if needed)')
    parser.add_argument('--start-lat', type=float, help='New starting latitude')
    parser.add_argument('--start-lon', type=float, help='New starting longitude')

    args = parser.parse_args()

    print("="*60)
    print("             GPX SCALER")
    print("="*60)
    print("Scale GPX routes in distance and elevation")
    print("with coordinate relocation capability")
    print("="*60)

    # Check if all required arguments are provided
    if args.scale and args.start_lat is not None and args.start_lon is not None:
        # Command line mode
        scaler = GPXScaler()
        if not scaler.find_gpx_files(args.folder):
            sys.exit(1)

        scaler.analyze_all_files()

        # Show preview even in command line mode
        scaler.preview_scaling_results(args.scale, args.min_distance)
        proceed = input("\nProceed with scaling? (y/n): ").strip().lower()
        if proceed not in ['y', 'yes', '']:
            print("Operation cancelled.")
            sys.exit(0)

        scaler.scale_all_files(args.scale, args.start_lat, args.start_lon, args.min_distance)

    else:
        # Interactive mode
        result = get_user_input()
        if result is None:
            sys.exit(1)

        scaler, scale_factor, start_lat, start_lon, min_distance_km = result
        scaler.scale_all_files(scale_factor, start_lat, start_lon, min_distance_km)

        # Output equivalent command-line invocation
        print("\n" + "="*80)
        print("COMMAND-LINE EQUIVALENT")
        print("="*80)
        print("To repeat this operation without interactive prompts, use:")
        print()

        # Get the folder path (handle current directory case)
        if scaler.gpx_files:
            folder_path = scaler.gpx_files[0].parent
        else:
            folder_path = Path(".")
        folder_display = "." if folder_path == Path(".") else str(folder_path)

        cmd = (f"python3 gpxscaler.py --folder \"{folder_display}\" "
               f"--scale {scale_factor} --start-lat {start_lat} "
               f"--start-lon {start_lon}")
        if min_distance_km is not None:
            cmd += f" --min-distance {min_distance_km}"

        print(f"  {cmd}")
        print("="*80)

    print("\nGPX scaling completed!")


if __name__ == "__main__":
    main()