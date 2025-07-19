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
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta

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
        self.config_file = Path("gpx_scaler_config.json")

    def load_config(self):
        """Load configuration from JSON file."""
        default_config = {
            "scale": 0.5,
            "start_lat": 52.5,
            "start_lon": 4.0,
            "output_format": "tcx",
            "base_name": "",
            "add_timing": False,
            "power": 250,
            "weight": 75,
            "min_distance": None,
            "max_ascent": None
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to handle missing keys
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                return default_config
        else:
            return default_config

    def save_config(self, scale=None, start_lat=None, start_lon=None,
                   output_format=None, base_name=None, add_timing=None,
                   power=None, weight=None, min_distance=None, max_ascent=None):
        """Save configuration to JSON file."""
        config = self.load_config()

        # Update only provided parameters
        if scale is not None:
            config["scale"] = scale
        if start_lat is not None:
            config["start_lat"] = start_lat
        if start_lon is not None:
            config["start_lon"] = start_lon
        if output_format is not None:
            config["output_format"] = output_format
        if base_name is not None:
            config["base_name"] = base_name
        if add_timing is not None:
            config["add_timing"] = add_timing
        if power is not None:
            config["power"] = power
        if weight is not None:
            config["weight"] = weight
        if min_distance is not None:
            config["min_distance"] = min_distance
        if max_ascent is not None:
            config["max_ascent"] = max_ascent

        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")

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

    def calculate_cycling_speed(self, power_watts, weight_kg, elevation_change_m, distance_m, grade_factor=0.05):
        """
        Calculate cycling speed based on power, weight, and terrain.

        Args:
            power_watts: Cyclist's average power output in watts
            weight_kg: Total weight (rider + bike) in kg
            elevation_change_m: Elevation change over the segment in meters
            distance_m: Distance of the segment in meters
            grade_factor: Factor for how much grade affects speed (0.05 = 5% speed reduction per 1% grade)

        Returns:
            Speed in m/s
        """
        # Basic power-to-speed calculation (simplified physics model)
        # Base speed from power (assumes flat terrain, no wind resistance)
        # This is a simplified model - real cycling physics are much more complex

        # Base speed calculation: P = F * v, where F is roughly proportional to weight and v^2
        # Simplified: v = (P / (weight_factor * weight))^(1/3)
        weight_factor = 0.1  # Adjust this factor based on typical cycling conditions
        base_speed_ms = (power_watts / (weight_factor * weight_kg)) ** (1/3)

        # Adjust for gradient
        if distance_m > 0:
            gradient_percent = (elevation_change_m / distance_m) * 100
            # Reduce speed on uphills, increase on downhills
            speed_adjustment = 1 - (gradient_percent * grade_factor)
            # Limit speed adjustment to reasonable bounds
            speed_adjustment = max(0.2, min(2.0, speed_adjustment))
            adjusted_speed = base_speed_ms * speed_adjustment
        else:
            adjusted_speed = base_speed_ms

        # Ensure minimum realistic cycling speed (1 m/s = 3.6 km/h)
        return max(1.0, adjusted_speed)

    def calculate_total_ride_duration(self, gpx, power_watts, weight_kg):
        """
        Calculate the total duration of a ride in seconds based on power/weight.

        Args:
            gpx: GPXpy object
            power_watts: Average power output in watts
            weight_kg: Total weight (rider + bike) in kg

        Returns:
            Total duration in seconds
        """
        total_seconds = 0

        # Process tracks
        for track in gpx.tracks:
            for segment in track.segments:
                if len(segment.points) < 2:
                    continue

                for i in range(1, len(segment.points)):
                    prev_point = segment.points[i-1]
                    curr_point = segment.points[i]

                    # Calculate distance and elevation change
                    distance_m = self.calculate_distance(prev_point, curr_point)

                    elevation_change = 0
                    if (prev_point.elevation is not None and
                        curr_point.elevation is not None):
                        elevation_change = curr_point.elevation - prev_point.elevation

                    # Calculate speed and time for this segment
                    speed_ms = self.calculate_cycling_speed(
                        power_watts, weight_kg, elevation_change, distance_m
                    )

                    # Calculate time for this segment
                    time_seconds = distance_m / speed_ms
                    total_seconds += time_seconds

        # Process routes (similar logic)
        for route in gpx.routes:
            if len(route.points) < 2:
                continue

            for i in range(1, len(route.points)):
                prev_point = route.points[i-1]
                curr_point = route.points[i]

                # Calculate distance and elevation change
                distance_m = self.calculate_distance(prev_point, curr_point)

                elevation_change = 0
                if (prev_point.elevation is not None and
                    curr_point.elevation is not None):
                    elevation_change = curr_point.elevation - prev_point.elevation

                # Calculate speed and time for this segment
                speed_ms = self.calculate_cycling_speed(
                    power_watts, weight_kg, elevation_change, distance_m
                )

                # Calculate time for this segment
                time_seconds = distance_m / speed_ms
                total_seconds += time_seconds

        return total_seconds

    def add_timing_data_to_gpx(self, gpx, power_watts, weight_kg, start_time=None):
        """
        Add timing data to GPX based on power and weight calculations.
        Also converts routes to tracks when timing data is added.

        Args:
            gpx: GPXpy object
            power_watts: Average power output in watts
            weight_kg: Total weight (rider + bike) in kg
            start_time: Starting datetime (default: calculated from current time)
        """
        if start_time is None:
            # Calculate total ride duration first to set appropriate start time
            total_duration_seconds = self.calculate_total_ride_duration(gpx, power_watts, weight_kg)

            # Use current date and time, then subtract ride duration to get start time
            now = datetime.now()
            # Add 10 minutes buffer to ensure we finish before current time
            start_time = now - timedelta(seconds=total_duration_seconds + 600)

            print(f"Calculated ride duration: {total_duration_seconds/3600:.1f} hours")
            print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"End time: {(start_time + timedelta(seconds=total_duration_seconds)).strftime('%Y-%m-%d %H:%M:%S')}")

        current_time = start_time

        # Convert routes to tracks when adding timing data
        if gpx.routes:
            for route in gpx.routes:
                if route.points:
                    # Create a new track from the route
                    track = gpxpy.gpx.GPXTrack()
                    track.name = route.name or "Converted Route"
                    segment = gpxpy.gpx.GPXTrackSegment()

                    # Copy route points to track points
                    for route_point in route.points:
                        track_point = gpxpy.gpx.GPXTrackPoint(
                            latitude=route_point.latitude,
                            longitude=route_point.longitude,
                            elevation=route_point.elevation
                        )
                        segment.points.append(track_point)

                    track.segments.append(segment)
                    gpx.tracks.append(track)

            # Clear routes since we've converted them to tracks
            gpx.routes = []

        # Process tracks
        for track in gpx.tracks:
            for segment in track.segments:
                if len(segment.points) < 2:
                    continue

                # Set time for first point
                segment.points[0].time = current_time

                # Calculate times for subsequent points
                for i in range(1, len(segment.points)):
                    prev_point = segment.points[i-1]
                    curr_point = segment.points[i]

                    # Calculate distance and elevation change
                    distance_m = self.calculate_distance(prev_point, curr_point)

                    elevation_change = 0
                    if (prev_point.elevation is not None and
                        curr_point.elevation is not None):
                        elevation_change = curr_point.elevation - prev_point.elevation

                    # Calculate speed and time for this segment
                    speed_ms = self.calculate_cycling_speed(
                        power_watts, weight_kg, elevation_change, distance_m
                    )

                    # Calculate time for this segment
                    time_seconds = distance_m / speed_ms
                    current_time += timedelta(seconds=time_seconds)

                    # Set time for current point
                    curr_point.time = current_time

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

            # Process tracks using gpxpy's built-in methods (much faster)
            for track in gpx.tracks:
                for segment in track.segments:
                    if len(segment.points) < 2:
                        continue

                    # Use gpxpy's built-in length calculation (optimized)
                    segment_distance = segment.length_2d()
                    if segment_distance:
                        total_distance += segment_distance

                    # Calculate elevation gains/losses
                    uphill, downhill = segment.get_uphill_downhill()
                    if uphill:
                        total_ascent += uphill
                    if downhill:
                        total_descent += downhill

            # Process routes using manual calculation (no built-in methods)
            for route in gpx.routes:
                if len(route.points) < 2:
                    continue

                # Calculate distance manually for routes
                points = route.points
                for i in range(1, len(points)):
                    distance = self.calculate_distance(points[i-1], points[i])
                    total_distance += distance

                    if (points[i-1].elevation is not None and
                            points[i].elevation is not None):
                        elevation_change = (points[i].elevation -
                                            points[i-1].elevation)
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
            response = requests.get('http://ipapi.co/json/', timeout=3)  # Reduced timeout
            if response.status_code == 200:
                data = response.json()
                return data.get('latitude'), data.get('longitude')
        except:
            pass

        try:
            # Alternative: ip-api.com
            response = requests.get('http://ip-api.com/json/', timeout=3)  # Reduced timeout
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
            response = requests.get(url, timeout=5)  # Reduced timeout
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
            response = requests.get(url, timeout=5)  # Reduced timeout
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

    def calculate_elevation_scale(self, original_ascent_m, distance_scale, max_ascent_m):
        """Calculate elevation scale factor to meet maximum ascent requirement."""
        if max_ascent_m is None:
            return distance_scale

        scaled_ascent = original_ascent_m * distance_scale

        if scaled_ascent > max_ascent_m:
            # Adjust elevation scale to meet maximum ascent
            elevation_scale = max_ascent_m / original_ascent_m
            return elevation_scale
        else:
            # Use distance scale as it already meets maximum
            return distance_scale

    def preview_scaling_results(self, scale_factor, min_distance_km=None, max_ascent_m=None):
        """Preview what the scaling results would be and allow adjustments."""
        print("\n" + "="*80)
        print("SCALING PREVIEW")
        print("="*80)
        print(f"Distance scale factor: {scale_factor}")
        if min_distance_km:
            print(f"Minimum distance: {min_distance_km} km")
        if max_ascent_m:
            print(f"Maximum ascent: {max_ascent_m} m")

        print(f"\n{'Route Name':<35} {'Orig Dist':<10} {'Scaled Dist':<12} {'Dist Scale':<10} {'Elev Scale':<10} {'Orig Ascent':<11} {'Ascent (m)':<10}")
        print("-" * 110)

        # Sort routes by stage number (numerical order)
        sorted_routes = sorted(self.route_stats.items(),
                               key=lambda x: self.extract_stage_number(x[0].name))

        total_original_distance = 0
        total_scaled_distance = 0
        total_scaled_ascent = 0
        total_scaled_descent = 0

        for gpx_file, stats in sorted_routes:
            original_distance = stats['distance_km']
            actual_distance_scale = self.calculate_adjusted_scale(original_distance, scale_factor, min_distance_km)
            actual_elevation_scale = self.calculate_elevation_scale(stats['ascent_m'], actual_distance_scale, max_ascent_m)

            scaled_distance = original_distance * actual_distance_scale
            scaled_ascent = stats['ascent_m'] * actual_elevation_scale
            scaled_descent = stats['descent_m'] * actual_elevation_scale

            filename = gpx_file.name
            if len(filename) > 34:
                filename = filename[:31] + "..."

            print(f"{filename:<35} {original_distance:<10.1f} {scaled_distance:<12.1f} {actual_distance_scale:<10.3f} {actual_elevation_scale:<10.3f} {stats['ascent_m']:<11.0f} {scaled_ascent:<10.0f}")

            total_original_distance += original_distance
            total_scaled_distance += scaled_distance
            total_scaled_ascent += scaled_ascent
            total_scaled_descent += scaled_descent

        print("-" * 110)
        print(f"{'TOTAL:':<35} {total_original_distance:<10.1f} {total_scaled_distance:<12.1f} {'':>32} {total_scaled_ascent:<10.0f}")
        print("="*110)

        return total_scaled_distance, total_scaled_ascent, total_scaled_descent

    def scale_gpx_file(self, gpx_file, scale_factor, start_lat, start_lon,
                       min_distance_km=None, max_ascent_m=None,
                       starting_elevation=None, output_folder=None,
                       output_format='gpx', base_name=None,
                       add_timing=False, power_watts=None, weight_kg=None):
        """Scale a GPX file and save the result."""
        try:
            with open(gpx_file, 'r') as f:
                gpx = gpxpy.parse(f)

            # Get original stats to calculate adjusted scales if needed
            actual_distance_scale = scale_factor
            actual_elevation_scale = scale_factor

            if min_distance_km is not None or max_ascent_m is not None:
                if gpx_file in self.route_stats:
                    original_distance = self.route_stats[gpx_file]['distance_km']
                    original_ascent = self.route_stats[gpx_file]['ascent_m']

                    # Calculate distance scale (may be adjusted for minimum distance)
                    actual_distance_scale = self.calculate_adjusted_scale(original_distance, scale_factor, min_distance_km)

                    # Calculate elevation scale (may be different from distance scale)
                    actual_elevation_scale = self.calculate_elevation_scale(original_ascent, actual_distance_scale, max_ascent_m)

                    if actual_distance_scale != scale_factor:
                        print(f"Adjusting distance scale for {gpx_file.name}: {scale_factor:.3f} → {actual_distance_scale:.3f}")

                    if actual_elevation_scale != actual_distance_scale:
                        print(f"Adjusting elevation scale for {gpx_file.name}: {actual_distance_scale:.3f} → {actual_elevation_scale:.3f}")

            # Find the first point to use as reference for original base elevation
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

            # Get the original base elevation for scaling calculations
            original_base_elevation = first_point.elevation if first_point.elevation is not None else 0

            # Use provided starting elevation or fallback to original
            if starting_elevation is not None:
                new_base_elevation = starting_elevation
            else:
                new_base_elevation = original_base_elevation

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
                        scaled_distance = original_distance * actual_distance_scale

                        # Calculate new position using scaled vector from previous scaled point
                        new_lat, new_lon = self.calculate_destination_point(
                            prev_point.latitude, prev_point.longitude,
                            original_bearing, scaled_distance
                        )

                        # Update point position
                        segment.points[i].latitude = new_lat
                        segment.points[i].longitude = new_lon

                        # Scale elevation change from previous point using elevation scale
                        if (original_points[i-1].elevation is not None and
                            original_points[i].elevation is not None):
                            original_elevation_change = original_points[i].elevation - original_points[i-1].elevation
                            scaled_elevation_change = original_elevation_change * actual_elevation_scale
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
                    scaled_distance = original_distance * actual_distance_scale

                    # Calculate new position using scaled vector from previous
                    new_lat, new_lon = self.calculate_destination_point(
                        prev_point.latitude, prev_point.longitude,
                        original_bearing, scaled_distance
                    )

                    # Update point position
                    route.points[i].latitude = new_lat
                    route.points[i].longitude = new_lon

                    # Scale elevation change from previous point using elevation scale
                    if (original_points[i-1].elevation is not None and
                            original_points[i].elevation is not None):
                        original_elevation_change = (
                            original_points[i].elevation -
                            original_points[i-1].elevation)
                        scaled_elevation_change = (
                            original_elevation_change * actual_elevation_scale)
                        route.points[i].elevation = (
                            prev_point.elevation + scaled_elevation_change)
                    else:
                        # If no elevation data, keep same as previous
                        route.points[i].elevation = prev_point.elevation

            # Add timing data if requested
            if add_timing and power_watts is not None and weight_kg is not None:
                print(f"Adding timing data based on {power_watts}W power and {weight_kg}kg weight...")
                self.add_timing_data_to_gpx(gpx, power_watts, weight_kg)

            # Create output subfolder if it doesn't exist
            if output_folder is not None:
                scaled_folder = output_folder
            else:
                scaled_folder = gpx_file.parent / "scaled"
            scaled_folder.mkdir(exist_ok=True)

            # Generate output filename in the scaled subfolder
            # Scale factor is now in folder name, so filenames are cleaner

            # Determine base filename using base_name if provided
            if base_name:
                # Extract stage number from filename
                stage_number = self.extract_stage_number(gpx_file.name)
                if isinstance(stage_number, int):
                    base_filename = (f"{base_name.replace(' ', '_')}_"
                                     f"{stage_number}")
                    display_name = f"{base_name} {stage_number}"
                else:
                    base_filename = base_name.replace(' ', '_')
                    display_name = base_name
            else:
                base_filename = gpx_file.stem
                display_name = None

            # Set track name in GPX data if base_name is provided
            if display_name and gpx.tracks:
                for track in gpx.tracks:
                    track.name = display_name

            if actual_distance_scale == actual_elevation_scale:
                # Same scale - no scale in filename since it's in folder name
                if output_format == 'fit':
                    output_file = scaled_folder / f"{base_filename}.fit"
                elif output_format == 'tcx':
                    output_file = scaled_folder / f"{base_filename}.tcx"
                else:
                    output_file = scaled_folder / f"{base_filename}.gpx"
            else:
                # Different scales - include elevation scale difference
                # Format elevation scale to 3 decimal places to avoid extremely long filenames
                elev_str = f"{actual_elevation_scale:.3f}".replace('.', '')
                if output_format == 'fit':
                    output_file = (scaled_folder /
                                   f"{base_filename}_elev_{elev_str}.fit")
                elif output_format == 'tcx':
                    output_file = (scaled_folder /
                                   f"{base_filename}_elev_{elev_str}.tcx")
                else:
                    output_file = (scaled_folder /
                                   f"{base_filename}_elev_{elev_str}.gpx")

            # Save file in appropriate format
            if output_format in ['fit', 'tcx']:
                # Create temporary GPX file first, then convert
                temp_gpx = scaled_folder / f"temp_{gpx_file.stem}.gpx"
                with open(temp_gpx, 'w') as f:
                    f.write(gpx.to_xml())

                # Convert to requested format with timing information
                if output_format == 'fit':
                    success = self.convert_gpx_to_fit_format(temp_gpx, output_file, add_timing)
                else:  # tcx
                    success = self.convert_gpx_to_tcx_format(temp_gpx, output_file, add_timing)

                # Note: temp file cleanup is handled by conversion functions

                if not success:
                    return False
            else:
                # Save as GPX
                with open(output_file, 'w') as f:
                    f.write(gpx.to_xml())

            print(f"Scaled {gpx_file.name} → {output_file.name}")
            return True

        except Exception as e:
            print(f"Error scaling {gpx_file.name}: {e}")
            return False

    def scale_all_files(self, scale_factor, start_lat, start_lon,
                        min_distance_km=None, max_ascent_m=None,
                        output_folder=None, output_format='gpx',
                        base_name=None, add_timing=False,
                        power_watts=None, weight_kg=None):
        """Scale all GPX files."""
        print(f"\nScaling all files by factor {scale_factor}")
        if min_distance_km:
            print(f"Minimum distance requirement: {min_distance_km} km")
        if max_ascent_m:
            print(f"Maximum ascent requirement: {max_ascent_m} m")
        print(f"New starting coordinates: {start_lat:.6f}, {start_lon:.6f}")
        print(f"Output format: {output_format.upper()}")

        if add_timing:
            print(f"Adding timing data: {power_watts}W power, {weight_kg}kg weight")

        # Determine output folder and always include scale factor
        if output_folder is None:
            # Generate default folder name with timestamp and scale
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scale_str = f"{scale_factor:.2f}".replace('.', '')
            output_folder = f"{timestamp}_scale_{scale_str}"
        else:
            # User-provided folder name - append scale factor
            scale_str = f"{scale_factor:.2f}".replace('.', '')
            output_folder = f"{output_folder}_scale_{scale_str}"

        if self.gpx_files:
            base_folder = Path(self.gpx_files[0].parent)
        else:
            base_folder = Path(".")

        scaled_folder = base_folder / output_folder
        print(f"Output folder: {scaled_folder}")

        # Check if output folder exists and has files
        if scaled_folder.exists() and any(scaled_folder.glob("*.gpx")):
            existing_files = list(scaled_folder.glob("*.gpx"))
            print(f"\nFound {len(existing_files)} existing scaled files")

            choice = input("Clean up old files? (y/n/s for selective): ").strip().lower()
            if choice in ['y', 'yes']:
                for old_file in existing_files:
                    old_file.unlink()
                print(f"Removed {len(existing_files)} old scaled files")
            elif choice in ['s', 'selective']:
                print("Existing files:")
                for i, old_file in enumerate(existing_files, 1):
                    print(f"  {i}. {old_file.name}")

                to_remove = input("Enter file numbers to remove (e.g., 1,3,5-7) or 'all': ").strip()
                if to_remove.lower() == 'all':
                    for old_file in existing_files:
                        old_file.unlink()
                    print(f"Removed all {len(existing_files)} files")
                elif to_remove:
                    # Parse ranges and individual numbers
                    indices_to_remove = set()
                    for part in to_remove.split(','):
                        part = part.strip()
                        if '-' in part:
                            start, end = map(int, part.split('-'))
                            indices_to_remove.update(range(start-1, end))
                        else:
                            indices_to_remove.add(int(part) - 1)

                    removed_count = 0
                    for i in sorted(indices_to_remove, reverse=True):
                        if 0 <= i < len(existing_files):
                            existing_files[i].unlink()
                            removed_count += 1
                    print(f"Removed {removed_count} files")

        # Get elevation once for the new starting coordinates
        print("Getting elevation data for starting coordinates...")
        starting_elevation = self.get_elevation(start_lat, start_lon)
        if starting_elevation is not None:
            print(f"Will use {starting_elevation}m as the new base elevation for all routes")
        else:
            print("Will preserve original base elevation for each route")

        print("\nProcessing files...")

        success_count = 0
        for gpx_file in self.gpx_files:
            if self.scale_gpx_file(gpx_file, scale_factor, start_lat, start_lon,
                                   min_distance_km, max_ascent_m, starting_elevation,
                                   scaled_folder, output_format, base_name,
                                   add_timing, power_watts, weight_kg):
                success_count += 1

        print(f"\nCompleted: {success_count}/{len(self.gpx_files)} files processed successfully.")

        # Save configuration for next time
        self.save_config(
            scale=scale_factor,
            start_lat=start_lat,
            start_lon=start_lon,
            output_format=output_format,
            base_name=base_name,
            add_timing=add_timing,
            power=power_watts,
            weight=weight_kg,
            min_distance=min_distance_km,
            max_ascent=max_ascent_m
        )


    def get_flat_terrain_coordinates(self):
        """Get predefined coordinates that are Garmin-compatible."""
        flat_locations = [
            {
                'name': 'North Sea (Garmin-compatible offshore)',
                'lat': 54.0,
                'lon': 3.0,
                'description': 'Offshore North Sea - flat water, Garmin-compatible coordinates'
            },
            {
                'name': 'English Channel (moderate offshore)',
                'lat': 50.5,
                'lon': 0.0,
                'description': 'English Channel - flat water, commonly used coordinates'
            },
            {
                'name': 'Mediterranean Sea (stable coordinates)',
                'lat': 40.0,
                'lon': 15.0,
                'description': 'Mediterranean Sea - flat, stable coordinates for Garmin'
            },
            {
                'name': 'Baltic Sea (conservative offshore)',
                'lat': 58.0,
                'lon': 18.0,
                'description': 'Baltic Sea - flat water, conservative European coordinates'
            },
            {
                'name': 'Bay of Biscay (Atlantic offshore)',
                'lat': 45.0,
                'lon': -5.0,
                'description': 'Bay of Biscay - flat Atlantic area, moderate coordinates'
            },
            {
                'name': 'Netherlands Coast (minimal elevation)',
                'lat': 52.5,
                'lon': 4.0,
                'description': 'Just off Netherlands coast - very flat, Garmin-friendly'
            },
            {
                'name': 'Remote Pacific Ocean (anti-Garmin elevation)',
                'lat': 0.0,
                'lon': 180.0,
                'description': 'International Date Line - for testing only, may cause import issues'
            }
        ]
        return flat_locations

    def suggest_flat_terrain_location(self):
        """Suggest flat terrain coordinates to minimize Garmin elevation conflicts."""
        print("\n" + "="*80)
        print("FLAT TERRAIN COORDINATE SUGGESTIONS")
        print("="*80)
        print("Using flat terrain coordinates minimizes Garmin Connect's")
        print("elevation interference while preserving your scaled elevation profile.")
        print("="*80)

        flat_locations = self.get_flat_terrain_coordinates()

        for i, location in enumerate(flat_locations, 1):
            print(f"{i}. {location['name']}")
            print(f"   Coordinates: {location['lat']:.1f}, {location['lon']:.1f}")
            print(f"   {location['description']}")
            print()

        print("7. Enter custom coordinates")
        print("8. Use current location (may cause elevation conflicts)")

        while True:
            try:
                choice = input("Choose an option (1-8): ").strip()
                choice_num = int(choice)

                if 1 <= choice_num <= 6:
                    selected = flat_locations[choice_num - 1]
                    print(f"\nSelected: {selected['name']}")
                    print(f"Coordinates: {selected['lat']:.6f}, {selected['lon']:.6f}")
                    confirm = input("Use these coordinates? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes', '']:
                        return selected['lat'], selected['lon']
                elif choice_num == 7:
                    return None, None  # Custom coordinates
                elif choice_num == 8:
                    # Try to get current location
                    current_lat, current_lon = self.get_current_location()
                    if current_lat and current_lon:
                        print(f"Current location: {current_lat:.6f}, {current_lon:.6f}")
                        print("WARNING: Using your current location may cause Garmin to override")
                        print("your scaled elevation data with real terrain elevation.")
                        confirm = input("Continue anyway? (y/n): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            return current_lat, current_lon
                    else:
                        print("Could not detect current location.")
                        continue
                else:
                    print("Please enter a number between 1 and 8.")
                    continue

            except ValueError:
                print("Please enter a valid number.")
                continue

    def create_garmin_activity_tcx(self, gpx_file_path, output_path):
        """Create a Garmin Connect compatible TCX file with Activity format."""
        try:
            # Read the GPX file
            with open(gpx_file_path, 'r') as f:
                gpx = gpxpy.parse(f)

            # Start building TCX content
            tcx_lines = []
            tcx_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
            tcx_lines.append('<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">')
            tcx_lines.append('  <Activities>')

            # Create Activity ID (past date for compatibility)
            activity_time = datetime(2024, 6, 1, 9, 0, 0)
            activity_id = activity_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

            tcx_lines.append('    <Activity Sport="Biking">')
            tcx_lines.append(f'      <Id>{activity_id}</Id>')

            # Process tracks as laps
            for track in gpx.tracks:
                for segment in track.segments:
                    if not segment.points:
                        continue

                    first_point = segment.points[0]
                    last_point = segment.points[-1]

                    # Calculate lap stats
                    lap_start = first_point.time or activity_time
                    lap_end = last_point.time or activity_time
                    total_time = (lap_end - lap_start).total_seconds()

                    # Calculate distance
                    total_distance = 0
                    for i in range(1, len(segment.points)):
                        total_distance += self.calculate_distance(segment.points[i-1], segment.points[i])

                    tcx_lines.append(f'      <Lap StartTime="{lap_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")}">')
                    tcx_lines.append(f'        <TotalTimeSeconds>{total_time:.1f}</TotalTimeSeconds>')
                    tcx_lines.append(f'        <DistanceMeters>{total_distance:.2f}</DistanceMeters>')
                    tcx_lines.append('        <Calories>300</Calories>')
                    tcx_lines.append('        <Intensity>Active</Intensity>')
                    tcx_lines.append('        <TriggerMethod>Manual</TriggerMethod>')
                    tcx_lines.append('        <Track>')

                    # Add trackpoints
                    for point in segment.points:
                        tcx_lines.append('          <Trackpoint>')

                        if point.time:
                            time_str = point.time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                        else:
                            time_str = activity_id
                        tcx_lines.append(f'            <Time>{time_str}</Time>')

                        tcx_lines.append('            <Position>')
                        tcx_lines.append(f'              <LatitudeDegrees>{point.latitude:.7f}</LatitudeDegrees>')
                        tcx_lines.append(f'              <LongitudeDegrees>{point.longitude:.7f}</LongitudeDegrees>')
                        tcx_lines.append('            </Position>')

                        if point.elevation is not None:
                            tcx_lines.append(f'            <AltitudeMeters>{point.elevation:.1f}</AltitudeMeters>')

                        tcx_lines.append('          </Trackpoint>')

                    tcx_lines.append('        </Track>')
                    tcx_lines.append('      </Lap>')

            tcx_lines.append('    </Activity>')
            tcx_lines.append('  </Activities>')
            tcx_lines.append('</TrainingCenterDatabase>')

            # Write TCX file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(tcx_lines))

            print(f"✅ Activity-based TCX file created: {output_path}")

            # Clean up temp file
            try:
                if os.path.exists(gpx_file_path):
                    os.remove(gpx_file_path)
            except Exception:
                pass  # Silently ignore cleanup errors

            return True

        except Exception as e:
            print(f"❌ Error creating Activity TCX: {e}")
            return False

    def convert_gpx_to_fit_format(self, gpx_file_path, output_path, has_timing=False):
        """Convert GPX to FIT format using GPSBabel."""
        try:
            import subprocess

            # Check if GPSBabel is available
            try:
                subprocess.run(['gpsbabel', '-V'], capture_output=True,
                               check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("GPSBabel not found. Please install it with: "
                      "brew install gpsbabel")
                return False

            if has_timing:
                print(f"Converting to FIT activity format (with timing): {gpx_file_path.name}")
            else:
                print(f"Converting to FIT course format (route): {gpx_file_path.name}")

            # Convert to FIT format
            cmd = [
                'gpsbabel',
                '-i', 'gpx',
                '-f', str(gpx_file_path),
                '-o', 'garmin_fit',
                '-F', str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                if (os.path.exists(output_path) and
                    os.path.getsize(output_path) > 0):
                    print(f"✅ FIT file created: {output_path}")

                    # Clean up temp file
                    try:
                        if os.path.exists(gpx_file_path):
                            os.remove(gpx_file_path)
                    except Exception:
                        pass  # Silently ignore cleanup errors

                    return True
                else:
                    print("❌ GPSBabel completed but no FIT file was created")
                    return False
            else:
                print(f"❌ FIT conversion failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Error during FIT conversion: {e}")
            return False

    def convert_gpx_to_tcx_format(self, gpx_file_path, output_path, has_timing=False):
        """Convert GPX to TCX format using GPSBabel."""
        try:
            import subprocess

            # Check if GPSBabel is available
            try:
                subprocess.run(['gpsbabel', '-V'], capture_output=True,
                               check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("GPSBabel not found. Please install it with: "
                      "brew install gpsbabel")
                return False

            if has_timing:
                print(f"Converting to TCX activity format (with timing): {gpx_file_path.name}")
                # For activities with timing, we should create a custom TCX
                return self.create_garmin_activity_tcx(gpx_file_path, output_path)
            else:
                print(f"Converting to TCX course format (route): {gpx_file_path.name}")

            # Convert to TCX format (course format for routes without timing)
            cmd = [
                'gpsbabel',
                '-i', 'gpx',
                '-f', str(gpx_file_path),
                '-o', 'gtrnctr',  # Garmin Training Center TCX format
                '-F', str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                if (os.path.exists(output_path) and
                    os.path.getsize(output_path) > 0):
                    print(f"✅ TCX file created: {output_path}")

                    # Clean up temp file
                    try:
                        if os.path.exists(gpx_file_path):
                            os.remove(gpx_file_path)
                    except Exception:
                        pass  # Silently ignore cleanup errors

                    return True
                else:
                    print("❌ GPSBabel completed but no TCX file was created")
                    return False
            else:
                print(f"❌ TCX conversion failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Error during TCX conversion: {e}")
            return False

    def convert_original_gpx_to_tcx(self, gpx_file_path, output_path):
        """Convert original GPX to TCX format without modifications."""
        try:
            import subprocess

            # Check if GPSBabel is available
            try:
                subprocess.run(['gpsbabel', '-V'], capture_output=True,
                               check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("GPSBabel not found. Please install it with: "
                      "brew install gpsbabel")
                return False

            print(f"Converting original GPX to clean TCX: {gpx_file_path.name}")

            # Convert directly to TCX without any modifications
            cmd = [
                'gpsbabel',
                '-i', 'gpx',
                '-f', str(gpx_file_path),
                '-o', 'gtrnctr',  # Garmin Training Center TCX format
                '-F', str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                if (os.path.exists(output_path) and
                    os.path.getsize(output_path) > 0):
                    print(f"✅ Clean TCX file created: {output_path}")

                    # Verify content
                    try:
                        with open(gpx_file_path, 'r', encoding='utf-8') as f:
                            gpx = gpxpy.parse(f)

                        point_count = 0
                        for track in gpx.tracks:
                            for segment in track.segments:
                                point_count += len(segment.points)
                        for route in gpx.routes:
                            point_count += len(route.points)

                        if point_count > 0:
                            print(f"   📊 Contains {point_count} points with "
                                  "original coordinates and elevation")
                            print("   🎯 No coordinate relocation - "
                                  "maintains original geography")
                            print("   📈 No elevation offset - "
                                  "preserves original elevation profile")
                    except Exception:
                        print("   ✅ TCX file created successfully")

                    return True
                else:
                    print("❌ GPSBabel completed but no TCX file was created")
                    return False
            else:
                print(f"❌ TCX conversion failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Error during clean TCX conversion: {e}")
            return False

    def convert_all_to_clean_tcx(self):
        """Convert all original GPX files to clean TCX format."""
        print("\n" + "="*80)
        print("CLEAN TCX CONVERSION FOR GARMIN CONNECT")
        print("="*80)
        print("Converting original GPX files to TCX format without "
              "any modifications.")
        print("This maximizes compatibility with Garmin Connect's "
              "elevation handling.")
        print("="*80)

        if not self.gpx_files:
            print("No GPX files found.")
            return False

        # Create clean_tcx folder
        if self.gpx_files:
            folder_path = self.gpx_files[0].parent
        else:
            folder_path = Path(".")

        clean_tcx_folder = folder_path / "clean_tcx"
        clean_tcx_folder.mkdir(exist_ok=True)

        success_count = 0
        total_files = len(self.gpx_files)

        print(f"\nProcessing {total_files} GPX files...")

        for i, gpx_file in enumerate(self.gpx_files, 1):
            print(f"\n[{i}/{total_files}] Processing {gpx_file.name}...")

            # Create output filename
            tcx_output = clean_tcx_folder / f"{gpx_file.stem}_clean.tcx"

            if self.convert_original_gpx_to_tcx(gpx_file, tcx_output):
                success_count += 1
            else:
                print(f"❌ Failed to convert {gpx_file.name}")

        print("\n" + "="*80)
        print("CLEAN TCX CONVERSION COMPLETE")
        print("="*80)
        print(f"✅ Successfully converted: {success_count}/{total_files} files")
        print(f"📁 Output folder: {clean_tcx_folder}")
        print("\n🔍 NEXT STEPS:")
        print(f"1. Import the TCX files from {clean_tcx_folder} "
              "into Garmin Connect")
        print("2. Check if elevations are preserved (no auto-correction)")
        print("3. If elevations are still zeroed, Garmin Connect may be "
              "force-correcting all imported routes")
        print("="*80)

        return success_count > 0


def get_user_input():
    """Get user input for interactive mode."""
    # Get folder
    folder = input("\nEnter folder path (or press Enter for current "
                   "directory): ").strip()
    if not folder:
        folder = "."

    scaler = GPXScaler()
    config = scaler.load_config()

    if not scaler.find_gpx_files(folder):
        return None

    # Analyze files to show distances/ascents before parameter input
    scaler.analyze_all_files()

    # Get scale factor and minimum distance with preview
    while True:
        # Get scale factor
        while True:
            try:
                scale_input = input(
                    f"\nEnter scale factor (default: {config['scale']}) "
                    "(e.g., 0.5 for half size, 2.0 for double): "
                ).strip()
                if not scale_input:
                    scale_factor = config['scale']
                else:
                    scale_factor = float(scale_input)
                if scale_factor <= 0:
                    print("Scale factor must be positive.")
                    continue
                break
            except ValueError:
                print("Please enter a valid number.")

        # Get minimum distance (optional)
        min_distance_km = None
        min_dist_default = f" (default: {config['min_distance']}km)" if config['min_distance'] else ""
        min_dist_input = input(f"\nEnter minimum distance in km{min_dist_default} "
                              f"(or press Enter to skip): ").strip()
        if min_dist_input:
            try:
                min_distance_km = float(min_dist_input)
                if min_distance_km <= 0:
                    print("Warning: Minimum distance should be positive.")
                    min_distance_km = None
            except ValueError:
                print("Invalid minimum distance, skipping minimum distance requirement.")
                min_distance_km = None
        elif config['min_distance']:
            min_distance_km = config['min_distance']

        # Get maximum ascent (optional)
        max_ascent_m = None
        max_ascent_default = f" (default: {config['max_ascent']}m)" if config['max_ascent'] else ""
        max_ascent_input = input(f"\nEnter maximum ascent in meters{max_ascent_default} "
                                f"(or press Enter to skip): ").strip()
        if max_ascent_input:
            try:
                max_ascent_m = float(max_ascent_input)
                if max_ascent_m <= 0:
                    print("Warning: Maximum ascent should be positive.")
                    max_ascent_m = None
            except ValueError:
                print("Invalid maximum ascent, skipping maximum ascent requirement.")
                max_ascent_m = None
        elif config['max_ascent']:
            max_ascent_m = config['max_ascent']

        # Show preview
        scaler.preview_scaling_results(scale_factor, min_distance_km, max_ascent_m)

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

    # Get output folder
    default_folder = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_input = input(f"\nEnter output folder name (default: {default_folder}): ").strip()
    output_folder = output_input if output_input else default_folder

    # Ask about TCX/FIT file output
    print("\n" + "="*80)
    print("OUTPUT FORMAT SELECTION")
    print("="*80)
    print("TCX files often preserve elevation data better than FIT in Garmin Connect.")
    print("Since Garmin zeroed your FIT elevation, we'll try TCX format instead.")
    print("TCX is Garmin's Training Center format and typically respects elevation.")
    print("="*80)

    print("Choose output format:")
    format_map = {'gpx': '1', 'tcx': '2', 'fit': '3'}
    default_format_num = format_map.get(config['output_format'], '2')
    format_default_text = {
        '1': 'GPX', '2': 'TCX (better for Garmin Connect)', '3': 'FIT'
    }[default_format_num]

    print(f"1. GPX")
    print(f"2. TCX (better for Garmin Connect)")
    print(f"3. FIT (for Garmin devices)")

    format_choice = input(f"Choose format (1/2/3, default: {default_format_num} - "
                         f"{format_default_text}): ").strip()
    if not format_choice:
        format_choice = default_format_num

    if format_choice == '1':
        output_format = 'gpx'
    elif format_choice == '3':
        output_format = 'fit'
    else:  # Default to TCX (option 2 or empty)
        output_format = 'tcx'

    # Get starting coordinates with ocean suggestions
    print("\nChoosing starting coordinates...")

    # First, suggest flat terrain locations to minimize elevation conflicts
    start_lat, start_lon = scaler.suggest_flat_terrain_location()

    # If user chose custom coordinates
    if start_lat is None:
        print("\nEntering custom coordinates...")
        while True:
            try:
                lat_input = input(f"Enter starting latitude (default: {config['start_lat']}): ").strip()
                if not lat_input:
                    start_lat = config['start_lat']
                else:
                    start_lat = float(lat_input)
                if not (-90 <= start_lat <= 90):
                    print("Latitude must be between -90 and 90.")
                    continue
                break
            except ValueError:
                print("Please enter a valid latitude.")

        while True:
            try:
                lon_input = input(f"Enter starting longitude (default: {config['start_lon']}): ").strip()
                if not lon_input:
                    start_lon = config['start_lon']
                else:
                    start_lon = float(lon_input)
                if not (-180 <= start_lon <= 180):
                    print("Longitude must be between -180 and 180.")
                    continue
                break
            except ValueError:
                print("Please enter a valid longitude.")

    # Get base name for output files (optional)
    base_name = None
    default_base = config['base_name'] if config['base_name'] else "original filenames"
    base_name_input = input(f"\nEnter base name for output files "
                           f"(e.g., 'Stage' for Stage 1, Stage 2, etc., "
                           f"or press Enter for {default_base}): ").strip()
    if base_name_input:
        base_name = base_name_input
    elif config['base_name']:
        base_name = config['base_name']

    # Ask about timing data
    add_timing = False
    power_watts = None
    weight_kg = None

    print("\n" + "="*80)
    print("TIMING DATA GENERATION")
    print("="*80)
    print("Generate estimated timing data based on power and weight?")
    print("This will add timestamps to each GPS point based on calculated "
          "cycling speeds.")
    print("="*80)

    default_timing = "y" if config['add_timing'] else "n"
    timing_choice = input(f"Add timing data? (y/n, default: {default_timing}): "
                         ).strip().lower()

    if not timing_choice:
        timing_choice = default_timing

    if timing_choice in ['y', 'yes']:
        add_timing = True

        # Get power input
        while True:
            try:
                power_input = input(f"Enter average power output in watts "
                                   f"(default: {config['power']}): ").strip()
                if not power_input:
                    power_watts = config['power']
                else:
                    power_watts = float(power_input)
                if power_watts <= 0:
                    print("Power must be positive.")
                    continue
                break
            except ValueError:
                print("Please enter a valid power value in watts.")

        # Get weight input
        while True:
            try:
                weight_input = input(f"Enter total weight (rider + bike) in kg "
                                    f"(default: {config['weight']}): ").strip()
                if not weight_input:
                    weight_kg = config['weight']
                else:
                    weight_kg = float(weight_input)
                if weight_kg <= 0:
                    print("Weight must be positive.")
                    continue
                break
            except ValueError:
                print("Please enter a valid weight in kg.")

        print("\nTiming data will be generated based on:")
        print(f"  - Average power: {power_watts}W")
        print(f"  - Total weight: {weight_kg}kg")
        print("  - Terrain-adjusted speeds calculated per segment")

    # Save the updated configuration
    updated_config = {
        "scale": scale_factor,
        "start_lat": start_lat,
        "start_lon": start_lon,
        "output_format": output_format,
        "base_name": base_name or "",
        "add_timing": add_timing,
        "power": power_watts or config['power'],
        "weight": weight_kg or config['weight'],
        "min_distance": min_distance_km,
        "max_ascent": max_ascent_m
    }
    scaler.save_config(updated_config)

    return (scaler, scale_factor, start_lat, start_lon, min_distance_km,
            max_ascent_m, output_folder, output_format, base_name,
            add_timing, power_watts, weight_kg)


def main():
    # Create scaler instance to load config defaults
    scaler = GPXScaler()
    config = scaler.load_config()

    parser = argparse.ArgumentParser(
        description="Scale GPX routes in distance and elevation with coordinate relocation"
    )
    parser.add_argument('--folder', default='.', help='Folder containing GPX files (default: current directory)')
    parser.add_argument('--scale', type=float, default=config["scale"],
                       help=f'Scaling factor for distance and elevation (default: {config["scale"]})')
    parser.add_argument('--min-distance', type=float, default=config["min_distance"],
                       help='Minimum distance in km (scale will be adjusted if needed)')
    parser.add_argument('--max-ascent', type=float, default=config["max_ascent"],
                       help='Maximum ascent in meters')
    parser.add_argument('--start-lat', type=float, default=config["start_lat"],
                       help=f'New starting latitude (default: {config["start_lat"]})')
    parser.add_argument('--start-lon', type=float, default=config["start_lon"],
                       help=f'New starting longitude (default: {config["start_lon"]})')
    parser.add_argument('--terrain', type=int, choices=[1, 2, 3, 4, 5, 6],
                       help='Use predefined flat terrain coordinates (1-6, see --list-terrain)')
    parser.add_argument('--list-terrain', action='store_true',
                       help='List available flat terrain coordinate options')
    parser.add_argument('--fit', action='store_true',
                       help='Output FIT files instead of GPX')
    parser.add_argument('--tcx', action='store_true',
                       help='Output TCX files instead of GPX')
    parser.add_argument('--clean-tcx', action='store_true',
                       help='Convert original GPX files to clean TCX '
                            'format without modifications')
    parser.add_argument('--base-name', type=str, default=config["base_name"],
                       help='Base name for output files and track names '
                            '(e.g., "Stage" for Stage 1, Stage 2, etc.)')

    # Add timing-related arguments
    timing_default = 'yes' if config["add_timing"] else 'no'
    parser.add_argument('--add-timing', action='store_true',
                       default=config["add_timing"],
                       help=f'Add timing data based on power and weight calculations (default: {timing_default})')
    parser.add_argument('--power', type=float, default=config["power"],
                       help=f'Average power output in watts (default: {config["power"]}W)')
    parser.add_argument('--weight', type=float, default=config["weight"],
                       help=f'Total weight (rider + bike) in kg (default: {config["weight"]}kg)')

    # Keep --ocean and --list-oceans for backwards compatibility
    parser.add_argument('--ocean', type=int, choices=[1, 2, 3, 4, 5, 6],
                       help='Alias for --terrain (backwards compatibility)')
    parser.add_argument('--list-oceans', action='store_true',
                       help='Alias for --list-terrain (backwards compatibility)')

    args = parser.parse_args()

    # Check if any arguments were explicitly provided (not just defaults)
    provided_args = sys.argv[1:]  # All command line arguments except script name
    has_explicit_args = len(provided_args) > 0

    # Check if timing arguments are provided correctly
    if args.add_timing and (args.power is None or args.weight is None):
        print("Error: --add-timing requires both --power and --weight arguments")
        sys.exit(1)

    # Handle --list-terrain and --list-oceans flags (backwards compatibility)
    if args.list_terrain or args.list_oceans:
        flat_locations = scaler.get_flat_terrain_coordinates()
        print("Available Flat Terrain Coordinates:")
        print("=" * 50)
        for i, location in enumerate(flat_locations, 1):
            print(f"{i}. {location['name']}")
            print(f"   Coordinates: {location['lat']:.1f}, {location['lon']:.1f}")
            print(f"   {location['description']}")
            print()
        print("Use with: --terrain <number> (e.g., --terrain 1)")
        sys.exit(0)

    print("="*60)
    print("             GPX SCALER")
    print("="*60)
    print("Scale GPX routes in distance and elevation")
    print("with coordinate relocation capability")
    print("="*60)

    # Handle terrain/ocean coordinate selection (ocean is alias for terrain)
    start_lat_arg, start_lon_arg = args.start_lat, args.start_lon
    terrain_choice = args.terrain or args.ocean
    if terrain_choice:
        flat_locations = scaler.get_flat_terrain_coordinates()
        if 1 <= terrain_choice <= len(flat_locations):
            selected = flat_locations[terrain_choice - 1]
            start_lat_arg = selected['lat']
            start_lon_arg = selected['lon']
            print(f"Using flat terrain coordinates: {selected['name']}")
            print(f"Coordinates: {start_lat_arg:.6f}, {start_lon_arg:.6f}")
        else:
            print(f"Error: Invalid terrain option {terrain_choice}. Use --list-terrain to see options.")
            sys.exit(1)

    # Check if all required arguments are explicitly provided via command line
    # (not just config defaults) - only go to command line mode if user provided args
    if has_explicit_args and args.scale and (start_lat_arg is not None and start_lon_arg is not None):
        # Command line mode
        if not scaler.find_gpx_files(args.folder):
            sys.exit(1)

        scaler.analyze_all_files()

        # Show preview even in command line mode
        scaler.preview_scaling_results(args.scale, args.min_distance, args.max_ascent)
        proceed = input("\nProceed with scaling? (y/n): ").strip().lower()
        if proceed not in ['y', 'yes', '']:
            print("Operation cancelled.")
            sys.exit(0)

        # Determine output format
        output_format = 'gpx'  # default
        if args.fit:
            output_format = 'fit'
        elif args.tcx:
            output_format = 'tcx'

        scaler.scale_all_files(args.scale, start_lat_arg, start_lon_arg,
                              args.min_distance, args.max_ascent, None,
                              output_format, args.base_name,
                              args.add_timing, args.power, args.weight)
        print("\nGPX scaling completed!")
        sys.exit(0)

    # Handle clean TCX conversion mode
    elif args.clean_tcx:
        if not scaler.find_gpx_files(args.folder):
            sys.exit(1)

        scaler.analyze_all_files()
        if scaler.convert_all_to_clean_tcx():
            sys.exit(0)
        else:
            sys.exit(1)

    else:
        # Interactive mode
        result = get_user_input()
        if result is None:
            sys.exit(1)

        (scaler, scale_factor, start_lat, start_lon, min_distance_km,
         max_ascent_m, output_folder, output_format, base_name,
         add_timing, power_watts, weight_kg) = result

        scaler.scale_all_files(scale_factor, start_lat, start_lon,
                               min_distance_km, max_ascent_m,
                               output_folder, output_format, base_name,
                               add_timing, power_watts, weight_kg)

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
        if max_ascent_m is not None:
            cmd += f" --max-ascent {max_ascent_m}"
        if base_name is not None:
            cmd += f" --base-name \"{base_name}\""
        if output_format == 'fit':
            cmd += " --fit"
        elif output_format == 'tcx':
            cmd += " --tcx"
        if add_timing:
            cmd += f" --add-timing --power {power_watts} --weight {weight_kg}"

        print(f"  {cmd}")
        print("="*80)

    print("\nGPX scaling completed!")


if __name__ == "__main__":
    main()
