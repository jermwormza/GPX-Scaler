from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
import os
import sys
import uuid
import json
import tempfile
import zipfile
from pathlib import Path
import threading
import time

# Add parent directory to path to import gpxscaler
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from gpxscaler import GPXScaler
import gpxpy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create a base temp directory for the app
BASE_TEMP_DIR = Path(tempfile.gettempdir()) / 'gpx_scaler_webapp'
BASE_TEMP_DIR.mkdir(exist_ok=True)

# Global storage for uploaded files and processing results
uploaded_files = {}
processed_files = {}
# Progress tracking for file processing
processing_progress = {}
progress_lock = threading.Lock()


def create_session_directory(session_id):
    """Create a unique directory for each session to avoid file conflicts."""
    session_dir = BASE_TEMP_DIR / f'session_{session_id}'
    session_dir.mkdir(exist_ok=True)
    return session_dir

class WebGPXHandler:
    def __init__(self):
        self.scaler = GPXScaler()

    def validate_gpx_file(self, file_content):
        """Validate that uploaded file is a valid GPX file."""
        try:
            gpx = gpxpy.parse(file_content)
            return True, gpx
        except Exception as e:
            return False, str(e)

    def extract_route_data(self, gpx):
        """Extract route data for visualization."""
        points = []
        elevations = []
        distances = []
        cumulative_distance = 0

        # Process tracks
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

        # Process routes if no tracks
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

        return {
            'points': points,
            'elevations': elevations,
            'distances': distances,
            'total_distance': cumulative_distance / 1000,
            'total_ascent': self.calculate_total_ascent(elevations),
            'bounds': self.calculate_bounds(points)
        }

    def calculate_total_ascent(self, elevations):
        """Calculate total ascent from elevation profile."""
        total_ascent = 0
        for i in range(1, len(elevations)):
            if elevations[i] > elevations[i-1]:
                total_ascent += elevations[i] - elevations[i-1]
        return total_ascent

    def calculate_bounds(self, points):
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

    def scale_route_coordinates(self, points, distance_scale, start_lat, start_lon):
        """Scale route coordinates for preview."""
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
            # Calculate original bearing and distance from previous point
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

gpx_handler = WebGPXHandler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle GPX file uploads."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    uploaded_file_data = []

    for file in files:
        if file.filename == '':
            continue

        if not file.filename.lower().endswith('.gpx'):
            return jsonify({'error': f'File {file.filename} is not a GPX file'}), 400

        # Generate unique ID for this upload
        file_id = str(uuid.uuid4())

        # Read file content
        file_content = file.read().decode('utf-8')

        # Validate GPX
        is_valid, gpx_or_error = gpx_handler.validate_gpx_file(file_content)
        if not is_valid:
            return jsonify({'error': f'Invalid GPX file {file.filename}: {gpx_or_error}'}), 400

        # Extract route data for preview
        route_data = gpx_handler.extract_route_data(gpx_or_error)

        # Store file data
        uploaded_files[file_id] = {
            'filename': secure_filename(file.filename),
            'content': file_content,
            'gpx': gpx_or_error,
            'route_data': route_data,
            'upload_time': time.time()
        }

        uploaded_file_data.append({
            'id': file_id,
            'filename': file.filename,
            'distance': round(route_data['total_distance'], 1),
            'ascent': round(route_data['total_ascent'], 0),
            'points': len(route_data['points'])
        })

    return jsonify({
        'success': True,
        'files': uploaded_file_data
    })

@app.route('/preview/<file_id>')
def get_preview_data(file_id):
    """Get route preview data for visualization."""
    if file_id not in uploaded_files:
        return jsonify({'error': 'File not found'}), 404

    file_data = uploaded_files[file_id]
    return jsonify({
        'success': True,
        'route_data': file_data['route_data']
    })

@app.route('/preview_scaled/<file_id>')
def get_scaled_preview(file_id):
    """Get scaled route preview data."""
    if file_id not in uploaded_files:
        return jsonify({'error': 'File not found'}), 404

    distance_scale = float(request.args.get('distance_scale', 1.0))
    ascent_scale = float(request.args.get('ascent_scale', 1.0))
    start_lat = float(request.args.get('start_lat', 0.0))
    start_lon = float(request.args.get('start_lon', 0.0))
    power_watts = request.args.get('power_watts')
    weight_kg = request.args.get('weight_kg')

    file_data = uploaded_files[file_id]
    original_data = file_data['route_data']

    # Create scaled preview data
    scaled_points = gpx_handler.scale_route_coordinates(
        original_data['points'], distance_scale, start_lat, start_lon
    ) if start_lat != 0 or start_lon != 0 else original_data['points']

    scaled_data = {
        'points': scaled_points,
        'elevations': [e * ascent_scale for e in original_data['elevations']],
        'distances': [d * distance_scale for d in original_data['distances']],
        'total_distance': original_data['total_distance'] * distance_scale,
        'total_ascent': original_data['total_ascent'] * ascent_scale,
        'bounds': gpx_handler.calculate_bounds(scaled_points) if scaled_points else original_data['bounds']
    }

    # Calculate timing if power and weight are provided
    timing_data = {}
    if power_watts and weight_kg:
        try:
            power_watts = int(power_watts)
            weight_kg = int(weight_kg)

            # Use already parsed GPX object for timing calculations
            original_gpx = file_data['gpx']

            # Calculate original route timing
            scaler = gpx_handler.scaler
            original_duration = scaler.calculate_total_ride_duration(
                original_gpx, power_watts, weight_kg
            )

            # For scaled timing, apply simple scaling to the original duration
            # This is a reasonable approximation for preview purposes
            distance_factor = distance_scale
            ascent_factor = ascent_scale

            # Estimate scaled duration based on distance and ascent changes
            # Distance directly affects duration, ascent affects it less directly
            scaled_duration = original_duration * (distance_factor * 0.8 + ascent_factor * 0.2)

            timing_data = {
                'original_duration_seconds': original_duration,
                'scaled_duration_seconds': scaled_duration,
                'original_duration_hours': original_duration / 3600,
                'scaled_duration_hours': scaled_duration / 3600
            }
        except Exception:
            timing_data = {}

    return jsonify({
        'success': True,
        'original': original_data,
        'scaled': scaled_data,
        'timing': timing_data
    })


@app.route('/progress/<session_id>')
def progress_stream(session_id):
    """Server-sent events endpoint for processing progress."""
    def generate():
        while True:
            with progress_lock:
                if session_id in processing_progress:
                    data = processing_progress[session_id]
                    yield f"data: {json.dumps(data)}\n\n"

                    # Clean up completed sessions
                    if data.get('status') == 'completed':
                        del processing_progress[session_id]
                        break
                else:
                    # Session doesn't exist, end stream
                    break
            time.sleep(0.1)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/process', methods=['POST'])
def process_files():
    """Process uploaded files with scaling parameters."""
    data = request.get_json()

    # Generate a unique session ID for this processing job
    session_id = str(uuid.uuid4())

    # Extract parameters
    file_ids = data.get('file_ids', [])
    distance_scale = float(data.get('distance_scale', 1.0))
    ascent_scale = float(data.get('ascent_scale', 1.0))
    start_lat = float(data.get('start_lat', 52.5))
    start_lon = float(data.get('start_lon', 4.0))
    base_name = data.get('base_name', '').strip()
    output_format = data.get('output_format', 'gpx').lower()
    add_timing = data.get('add_timing', False)
    power_watts = int(data.get('power_watts', 200)) if add_timing else None
    weight_kg = int(data.get('weight_kg', 75)) if add_timing else None

    # Initialize progress tracking
    with progress_lock:
        processing_progress[session_id] = {
            'status': 'starting',
            'total_files': len(file_ids),
            'current_file': 0,
            'files': {}
        }

    def process_files_async():
        processed_file_data = []

        try:
            for i, file_id in enumerate(file_ids):
                if file_id not in uploaded_files:
                    continue

                file_data = uploaded_files[file_id]

                # Update progress - starting file
                with progress_lock:
                    processing_progress[session_id].update({
                        'status': 'processing',
                        'current_file': i + 1,
                        'current_filename': file_data['filename'],
                        'files': {
                            **processing_progress[session_id]['files'],
                            file_id: {'status': 'processing', 'filename': file_data['filename']}
                        }
                    })

                try:
                    # Create session-specific directory for file processing
                    session_dir = create_session_directory(session_id)

                    # Create temporary file for processing in session directory
                    temp_file_path = session_dir / f"input_{file_id}_{file_data['filename']}"
                    with open(temp_file_path, 'w') as temp_file:
                        temp_file.write(file_data['content'])

                    # Create output directory in session directory
                    output_dir = session_dir / f"output_{file_id}"
                    output_dir.mkdir(exist_ok=True)

                    # Process the file
                    success = gpx_handler.scaler.scale_gpx_file(
                        Path(temp_file_path),
                        distance_scale,
                        start_lat,
                        start_lon,
                        output_folder=Path(output_dir),
                        output_format=output_format,
                        base_name=base_name if base_name else None,
                        add_timing=add_timing,
                        power_watts=power_watts,
                        weight_kg=weight_kg,
                        original_filename=file_data['filename'],
                        ascent_scale=ascent_scale
                    )

                    if success:
                        # Find the processed file
                        processed_files_list = list(Path(output_dir).glob(f'*.{output_format}'))
                        if processed_files_list:
                            processed_file_path = processed_files_list[0]

                            # Store processed file info
                            processed_id = str(uuid.uuid4())
                            processed_files[processed_id] = {
                                'file_path': str(processed_file_path),
                                'original_filename': file_data['filename'],
                                'output_format': output_format,
                                'process_time': time.time()
                            }

                            processed_file_data.append({
                                'id': processed_id,
                                'filename': processed_file_path.name,
                                'original_filename': file_data['filename'],
                                'format': output_format.upper()
                            })

                            # Update progress - file completed
                            with progress_lock:
                                processing_progress[session_id]['files'][file_id] = {
                                    'status': 'completed',
                                    'filename': file_data['filename']
                                }
                        else:
                            # Update progress - file failed
                            with progress_lock:
                                processing_progress[session_id]['files'][file_id] = {
                                    'status': 'failed',
                                    'filename': file_data['filename'],
                                    'error': 'No output file generated'
                                }
                    else:
                        # Update progress - file failed
                        with progress_lock:
                            processing_progress[session_id]['files'][file_id] = {
                                'status': 'failed',
                                'filename': file_data['filename'],
                                'error': 'Processing failed'
                            }

                    # Clean up temp file
                    try:
                        os.unlink(temp_file_path)
                    except OSError:
                        pass  # File may already be deleted

                except Exception as e:
                    # Update progress - file failed
                    with progress_lock:
                        processing_progress[session_id]['files'][file_id] = {
                            'status': 'failed',
                            'filename': file_data.get('filename', 'Unknown'),
                            'error': str(e)
                        }

            # Mark processing as completed
            with progress_lock:
                processing_progress[session_id]['status'] = 'completed'
                processing_progress[session_id]['processed_files'] = processed_file_data

        except Exception as e:
            # Mark processing as failed
            with progress_lock:
                processing_progress[session_id]['status'] = 'failed'
                processing_progress[session_id]['error'] = str(e)

    # Start processing in background thread
    thread = threading.Thread(target=process_files_async)
    thread.daemon = True
    thread.start()

    # Return session ID for progress tracking
    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Processing started'
    })

@app.route('/download/<processed_id>')
def download_file(processed_id):
    """Download a processed file."""
    if processed_id not in processed_files:
        return jsonify({'error': 'File not found'}), 404

    file_info = processed_files[processed_id]
    return send_file(
        file_info['file_path'],
        as_attachment=True,
        download_name=Path(file_info['file_path']).name
    )

@app.route('/download_batch', methods=['POST'])
def download_batch():
    """Download all processed files as a ZIP."""
    data = request.get_json()
    processed_ids = data.get('processed_ids', [])

    if not processed_ids:
        return jsonify({'error': 'No files to download'}), 400

    # Create temporary ZIP file
    zip_path = tempfile.mktemp(suffix='.zip')

    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for processed_id in processed_ids:
            if processed_id in processed_files:
                file_info = processed_files[processed_id]
                zip_file.write(
                    file_info['file_path'],
                    Path(file_info['file_path']).name
                )

    return send_file(
        zip_path,
        as_attachment=True,
        download_name='scaled_gpx_files.zip'
    )

# Cleanup old files periodically
def cleanup_old_files():
    """Remove old uploaded and processed files and session directories."""
    while True:
        current_time = time.time()

        # Clean uploaded files older than 1 hour
        for file_id in list(uploaded_files.keys()):
            if current_time - uploaded_files[file_id]['upload_time'] > 3600:
                del uploaded_files[file_id]

        # Clean processed files older than 1 hour
        for processed_id in list(processed_files.keys()):
            file_info = processed_files[processed_id]
            if current_time - file_info['process_time'] > 3600:
                try:
                    os.unlink(file_info['file_path'])
                except OSError:
                    pass
                del processed_files[processed_id]

        # Clean old session directories (older than 2 hours)
        try:
            for session_dir in BASE_TEMP_DIR.iterdir():
                if session_dir.is_dir() and session_dir.name.startswith('session_'):
                    try:
                        # Check if directory is older than 2 hours
                        dir_age = current_time - session_dir.stat().st_mtime
                        if dir_age > 7200:  # 2 hours
                            import shutil
                            shutil.rmtree(session_dir, ignore_errors=True)
                    except OSError:
                        pass
        except OSError:
            pass

        time.sleep(300)  # Check every 5 minutes

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
