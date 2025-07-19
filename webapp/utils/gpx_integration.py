"""
GPX Integration utilities for the web application.
This module provides a bridge between the web interface and the existing GPXScaler class.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add parent directory to path to import gpxscaler
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from gpxscaler import GPXScaler
import gpxpy


class WebGPXIntegration:
    """Bridge class between web uploads and existing GPXScaler functionality."""

    def __init__(self):
        self.scaler = GPXScaler()

    def process_uploaded_file(self, file_content, scale_params):
        """
        Process an uploaded GPX file with the given scaling parameters.

        Args:
            file_content (str): Content of the uploaded GPX file
            scale_params (dict): Dictionary containing scaling parameters
                - distance_scale: Distance scaling factor
                - ascent_scale: Elevation scaling factor (if different from distance)
                - start_lat: Starting latitude
                - start_lon: Starting longitude
                - output_format: Output file format ('gpx', 'tcx', 'fit')
                - add_timing: Whether to add timing data
                - power_watts: Power in watts (if timing enabled)
                - weight_kg: Weight in kg (if timing enabled)

        Returns:
            tuple: (success: bool, output_file_path: str or None, error: str or None)
        """
        try:
            # Create temporary input file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as temp_input:
                temp_input.write(file_content)
                temp_input_path = temp_input.name

            # Create temporary output directory
            output_dir = tempfile.mkdtemp()

            # Extract parameters
            distance_scale = scale_params.get('distance_scale', 1.0)
            start_lat = scale_params.get('start_lat', 0.0)
            start_lon = scale_params.get('start_lon', 0.0)
            output_format = scale_params.get('output_format', 'gpx')
            add_timing = scale_params.get('add_timing', False)
            power_watts = scale_params.get('power_watts', 200) if add_timing else None
            weight_kg = scale_params.get('weight_kg', 75) if add_timing else None

            # Process the file using GPXScaler
            success = self.scaler.scale_gpx_file(
                Path(temp_input_path),
                distance_scale,
                start_lat,
                start_lon,
                output_folder=Path(output_dir),
                output_format=output_format,
                add_timing=add_timing,
                power_watts=power_watts,
                weight_kg=weight_kg
            )

            if success:
                # Find the output file
                output_files = list(Path(output_dir).glob(f'*.{output_format}'))
                if output_files:
                    output_file_path = str(output_files[0])

                    # Clean up input file
                    os.unlink(temp_input_path)

                    return True, output_file_path, None
                else:
                    return False, None, "No output file generated"
            else:
                return False, None, "GPXScaler processing failed"

        except Exception as e:
            return False, None, str(e)
        finally:
            # Clean up temp input file if it still exists
            try:
                if 'temp_input_path' in locals():
                    os.unlink(temp_input_path)
            except:
                pass

    def extract_route_preview_data(self, gpx_content):
        """
        Extract route data for preview visualization.

        Args:
            gpx_content (str): GPX file content

        Returns:
            dict: Route data including points, elevations, distances, stats
        """
        try:
            gpx = gpxpy.parse(gpx_content)

            points = []
            elevations = []
            distances = []
            cumulative_distance = 0

            # Process tracks first
            for track in gpx.tracks:
                for segment in track.segments:
                    prev_point = None
                    for point in segment.points:
                        if prev_point:
                            distance = self.scaler.calculate_distance(prev_point, point)
                            cumulative_distance += distance

                        points.append({
                            'lat': point.latitude,
                            'lon': point.longitude,
                            'ele': point.elevation if point.elevation else 0
                        })
                        elevations.append(point.elevation if point.elevation else 0)
                        distances.append(cumulative_distance / 1000)  # Convert to km
                        prev_point = point

            # Process routes if no tracks found
            if not points:
                for route in gpx.routes:
                    prev_point = None
                    for point in route.points:
                        if prev_point:
                            distance = self.scaler.calculate_distance(prev_point, point)
                            cumulative_distance += distance

                        points.append({
                            'lat': point.latitude,
                            'lon': point.longitude,
                            'ele': point.elevation if point.elevation else 0
                        })
                        elevations.append(point.elevation if point.elevation else 0)
                        distances.append(cumulative_distance / 1000)  # Convert to km
                        prev_point = point

            # Calculate statistics
            total_ascent = self._calculate_total_ascent(elevations)
            bounds = self._calculate_bounds(points)

            return {
                'points': points,
                'elevations': elevations,
                'distances': distances,
                'total_distance': cumulative_distance / 1000,
                'total_ascent': total_ascent,
                'bounds': bounds,
                'point_count': len(points)
            }

        except Exception as e:
            raise ValueError(f"Failed to parse GPX data: {str(e)}")

    def generate_scaled_preview(self, original_data, distance_scale, ascent_scale, start_lat, start_lon):
        """
        Generate scaled preview data without actually processing the file.

        Args:
            original_data (dict): Original route data
            distance_scale (float): Distance scaling factor
            ascent_scale (float): Elevation scaling factor
            start_lat (float): New starting latitude
            start_lon (float): New starting longitude

        Returns:
            dict: Scaled route data
        """
        if not original_data or not original_data.get('points'):
            return original_data

        # Scale coordinates (simplified version for preview)
        scaled_points = self._scale_coordinates_simple(
            original_data['points'],
            distance_scale,
            start_lat,
            start_lon
        )

        # Scale elevations
        scaled_elevations = [e * ascent_scale for e in original_data['elevations']]

        # Scale distances
        scaled_distances = [d * distance_scale for d in original_data['distances']]

        return {
            'points': scaled_points,
            'elevations': scaled_elevations,
            'distances': scaled_distances,
            'total_distance': original_data['total_distance'] * distance_scale,
            'total_ascent': original_data['total_ascent'] * ascent_scale,
            'bounds': self._calculate_bounds(scaled_points),
            'point_count': len(scaled_points)
        }

    def _calculate_total_ascent(self, elevations):
        """Calculate total ascent from elevation profile."""
        total_ascent = 0
        for i in range(1, len(elevations)):
            if elevations[i] > elevations[i-1]:
                total_ascent += elevations[i] - elevations[i-1]
        return total_ascent

    def _calculate_bounds(self, points):
        """Calculate bounding box for route."""
        if not points:
            return None

        lats = [p['lat'] for p in points]
        lons = [p['lon'] for p in points]

        return {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons)
        }

    def _scale_coordinates_simple(self, points, distance_scale, start_lat, start_lon):
        """
        Simple coordinate scaling for preview (not as accurate as full GPXScaler).
        """
        if not points:
            return []

        scaled_points = []

        # Set first point to new starting location
        scaled_points.append({
            'lat': start_lat,
            'lon': start_lon,
            'ele': points[0]['ele']
        })

        # Scale subsequent points
        for i in range(1, len(points)):
            prev_orig = points[i-1]
            curr_orig = points[i]
            prev_scaled = scaled_points[i-1]

            # Simple scaling (more sophisticated scaling would use the GPXScaler methods)
            lat_diff = (curr_orig['lat'] - prev_orig['lat']) * distance_scale
            lon_diff = (curr_orig['lon'] - prev_orig['lon']) * distance_scale

            scaled_points.append({
                'lat': prev_scaled['lat'] + lat_diff,
                'lon': prev_scaled['lon'] + lon_diff,
                'ele': curr_orig['ele']
            })

        return scaled_points
