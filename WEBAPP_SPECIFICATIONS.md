# GPX Scaler Web Application - Technical Specifications

## Project Overview
Create a cross-platform web application that provides a graphical user interface for the existing GPX Scaler functionality, while maintaining the original `gpxscaler.py` as a standalone console application.

## Core Requirements

### 1. Architecture
- **Backend**: Python-based web framework
- **Frontend**: Modern web interface (HTML/CSS/JavaScript)
- **File Structure**: Separate web app folder(s) alongside existing `gpxscaler.py`
- **Integration**: Import and utilize existing GPXScaler class functionality
- **Cross-platform**: Runs in any modern web browser

### 2. Recommended Technology Stack
**Primary Option: Flask**
- Lightweight Python web framework
- Easy integration with existing Python code
- Good for file uploads and processing
- Simple deployment options

**Alternative Option: FastAPI**
- Modern Python framework with automatic API documentation
- Built-in support for file uploads
- Async capabilities for better performance

**Frontend Technologies:**
- HTML5/CSS3 for layout and styling
- JavaScript for interactive controls (sliders, file handling)
- Optional: lightweight framework like Alpine.js or vanilla JS
- Chart.js or similar for route visualization

### 3. Core Functionality

#### File Management
- **File Upload**: Drag-and-drop or click-to-browse GPX file upload
- **Multiple Files**: Support uploading multiple GPX files at once
- **File Validation**: Ensure uploaded files are valid GPX format
- **File Preview**: Show list of uploaded files with basic stats (distance, ascent)

#### Interactive Controls
- **Distance Scale Slider**: Visual slider for scaling route distances (0.1x to 2.0x)
- **Ascent Scale Slider**: Visual slider for scaling elevation gains (0.1x to 2.0x)
- **Starting Location**: Interactive map or coordinate input
- **Power/Weight Settings**: Input fields for timing calculations
- **Output Format**: Dropdown selection (GPX, TCX, FIT)

#### Visualization
- **Route Preview**: 2D visualization showing route shape
  - North pointing up (standardized orientation)
  - Elevation profile display
  - Distance markers
  - Before/after comparison when scaling
- **Statistics Display**:
  - Original vs scaled distance
  - Original vs scaled ascent
  - Estimated ride time with power/weight settings

#### Processing & Download
- **Real-time Preview**: Update visualization as sliders change
- **Batch Processing**: Scale all uploaded files with current settings
- **Download Options**:
  - Individual file downloads
  - Zip archive of all processed files
- **Progress Indication**: Show processing status for multiple files

### 4. User Interface Design

#### Main Layout
```
Header: GPX Scaler Web App
├── Upload Section
│   ├── File upload area (drag/drop)
│   └── Uploaded files list with stats
├── Controls Section
│   ├── Distance Scale Slider (with live value display)
│   ├── Ascent Scale Slider (with live value display)
│   ├── Starting Location (map widget or lat/lon inputs)
│   ├── Power/Weight inputs
│   └── Output format selection
├── Preview Section
│   ├── Route visualization (2D map view)
│   ├── Elevation profile chart
│   └── Statistics comparison table
└── Processing Section
    ├── Process All Files button
    ├── Progress indicators
    └── Download links/buttons
```

#### Responsive Design
- Desktop-first design with mobile compatibility
- Collapsible sections for smaller screens
- Touch-friendly controls for tablets/phones

### 5. Technical Implementation

#### Backend Structure
```
webapp/
├── app.py                 # Main Flask/FastAPI application
├── routes/
│   ├── __init__.py
│   ├── upload.py         # File upload handling
│   ├── process.py        # GPX processing endpoints
│   └── download.py       # File download endpoints
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   ├── base.html
│   ├── index.html
│   └── components/
├── utils/
│   ├── __init__.py
│   ├── gpx_integration.py # Bridge to existing GPXScaler
│   └── visualization.py  # Route visualization helpers
└── requirements.txt
```

#### Key Endpoints
- `POST /upload` - Handle GPX file uploads
- `POST /process` - Process files with scaling parameters
- `GET /preview/<file_id>` - Generate route preview data
- `GET /download/<file_id>` - Download processed file
- `GET /download/batch` - Download all processed files as zip

#### Data Flow
1. User uploads GPX files → stored temporarily with unique IDs
2. User adjusts sliders → real-time preview updates via AJAX
3. User clicks "Process" → backend scales files using existing GPXScaler
4. Processed files available for download → automatic cleanup after timeout

### 6. Integration with Existing Code

#### GPXScaler Integration
```python
# utils/gpx_integration.py
from ..gpxscaler import GPXScaler

class WebGPXScaler:
    def __init__(self):
        self.scaler = GPXScaler()

    def process_uploaded_file(self, file_data, scale_params):
        # Bridge between web uploads and existing GPXScaler methods
        pass

    def generate_preview_data(self, gpx_file):
        # Extract visualization data for frontend
        pass
```

#### File Handling
- Temporary file storage during processing
- Secure file validation and sanitization
- Automatic cleanup of processed files after download

### 7. Visualization Requirements

#### Route Display
- **2D Route Path**: Show scaled route overlaid on original
- **North Orientation**: Always display with north pointing up
- **Scale Indicators**: Visual scale bar and distance markers
- **Elevation Profile**: Side-by-side comparison of original vs scaled

#### Interactive Elements
- **Zoom/Pan**: Allow users to explore route details
- **Hover Information**: Show elevation/distance data on hover
- **Layer Toggle**: Switch between original and scaled views

### 8. Deployment Options

#### Development
- Local development server (Flask dev server or Uvicorn for FastAPI)
- Hot reloading for development efficiency

#### Production Options
- **Docker Container**: Containerized deployment for any platform
- **Cloud Platforms**: Heroku, Railway, DigitalOcean App Platform
- **Self-hosted**: Gunicorn/uWSGI with Nginx reverse proxy
- **Desktop App**: Electron wrapper for desktop application feel

### 9. Security Considerations

#### File Upload Security
- File type validation (GPX only)
- File size limits (reasonable for GPX files)
- Temporary file cleanup
- Input sanitization for all parameters

#### General Security
- CSRF protection for forms
- Rate limiting for API endpoints
- Secure headers and HTTPS in production

### 10. Future Enhancement Ideas

#### Advanced Features
- **Route Comparison**: Side-by-side analysis of multiple routes
- **Batch Templates**: Save and reuse scaling configurations
- **Export Presets**: Quick export for different devices/platforms
- **User Accounts**: Save preferences and processing history

#### Visualization Enhancements
- **3D Elevation View**: Three-dimensional route visualization
- **Real Map Integration**: Overlay routes on actual map tiles
- **Animation**: Animated preview of scaling effects

## Questions for Clarification

1. **File Storage**: How long should processed files be available for download?
2. **Concurrent Users**: Expected number of simultaneous users?
3. **File Size Limits**: Maximum GPX file size to support?
4. **Visualization Detail**: How detailed should the route preview be (number of points to display)?
5. **Mobile Priority**: Should mobile experience be fully featured or simplified?

## Development Approach

### Phase 1: Core Functionality
- Basic file upload and processing
- Simple sliders for distance/ascent scaling
- Basic route visualization
- Download processed files

### Phase 2: Enhanced UI
- Interactive route preview
- Real-time scaling updates
- Improved visualization with elevation profiles
- Responsive design

### Phase 3: Advanced Features
- Batch processing optimization
- Enhanced visualizations
- Export presets and templates
- Performance optimizations

---

**Does this specification accurately capture your vision for the web application? Are there any aspects you'd like me to modify or expand upon before we begin implementation?**
