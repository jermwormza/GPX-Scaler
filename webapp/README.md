# GPX Scaler Web Application

A web-based interface for the GPX Scaler tool that allows you to scale GPX routes interactively through your browser.

## Features

- **Drag & Drop File Upload**: Upload multiple GPX files easily
- **Interactive Scaling**: Real-time sliders for distance and elevation scaling
- **Route Visualization**: 2D route preview with north-up orientation
- **Elevation Profiles**: Interactive elevation charts comparing original vs scaled routes
- **Multiple Output Formats**: Export as GPX, TCX, or FIT files
- **Timing Data**: Optional power/weight-based timing calculations
- **Batch Processing**: Process and download multiple files at once
- **Cross-Platform**: Runs in any modern web browser

## Quick Start

1. **Install Dependencies**:
   ```bash
   cd webapp
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Open in Browser**:
   Open your web browser and go to `http://localhost:5000`

## How to Use

### 1. Upload GPX Files
- Drag and drop GPX files onto the upload area, or click to browse
- Multiple files can be uploaded at once
- Files are validated to ensure they're valid GPX format

### 2. Adjust Scaling Parameters
- **Distance Scale**: Use the slider to scale route distances (0.1x to 2.0x)
- **Ascent Scale**: Independently scale elevation gains/losses
- **Starting Location**: Set new coordinates for the scaled route
- **Output Format**: Choose between GPX, TCX, or FIT formats

### 3. Preview Routes
- View original and scaled routes in the preview area
- Toggle between Original, Scaled, and Comparison views
- Interactive elevation profile shows changes in real-time
- Statistics panel displays distance and ascent changes

### 4. Add Timing (Optional)
- Enable timing data generation
- Set your power output (watts) and weight (kg)
- Timing calculations use realistic cycling physics

### 5. Process and Download
- Click "Process All Files" to scale all uploaded routes
- Download individual files or all files as a ZIP archive
- Files are automatically cleaned up after 1 hour

## Default Settings

- **Starting Location**: 52.5°N, 4.0°E (Netherlands Coast - flat terrain)
- **Power**: 200W
- **Weight**: 75kg
- **Output Format**: GPX

The default starting location is chosen to minimize elevation conflicts with Garmin Connect's terrain data.

## Browser Compatibility

- Chrome 70+
- Firefox 65+
- Safari 12+
- Edge 79+

## File Limits

- Maximum file size: 50MB
- No limit on number of files
- Files are temporarily stored and auto-deleted after 1 hour

## Deployment Options

### Local Development
```bash
python app.py
```
Application runs on `http://localhost:5000`

### Production Deployment

#### Option 1: Railway (Recommended for free hosting)
1. Create account at [Railway.app](https://railway.app)
2. Connect your GitHub repository
3. Railway will auto-detect the Flask app and deploy

#### Option 2: Render
1. Create account at [Render.com](https://render.com)
2. Connect repository and select "Web Service"
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python app.py`

#### Option 3: Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

## Security Features

- File type validation (GPX only)
- Secure filename handling
- Automatic file cleanup
- CSRF protection
- Input sanitization

## Technical Details

### Architecture
- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Chart.js
- **Styling**: Bootstrap 5

### File Structure
```
webapp/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/style.css     # Custom styles
│   └── js/app.js         # Frontend JavaScript
├── templates/
│   ├── base.html         # Base template
│   └── index.html        # Main page
└── utils/
    └── gpx_integration.py # GPXScaler bridge
```

### API Endpoints
- `POST /upload` - Upload GPX files
- `GET /preview/<file_id>` - Get route preview data
- `GET /preview_scaled/<file_id>` - Get scaled preview data
- `POST /process` - Process files with scaling
- `GET /download/<file_id>` - Download processed file
- `POST /download_batch` - Download multiple files as ZIP

## Performance Notes

- Route previews use simplified coordinate scaling for speed
- Full GPXScaler processing is used for final file generation
- Large files (>1000 points) may take longer to process
- Elevation charts are optimized for up to 10,000 data points

## Troubleshooting

### Common Issues

1. **Upload fails**: Ensure files are valid GPX format
2. **Preview not showing**: Check browser console for JavaScript errors
3. **Processing takes long**: Large files with many points take more time
4. **Download fails**: Files are auto-deleted after 1 hour

### Browser Console
Open developer tools (F12) and check the Console tab for error messages.

### Log Files
Check the terminal where you ran `python app.py` for server-side errors.

## Integration with GPXScaler

The web app uses the existing `gpxscaler.py` module without modification:
- Files are temporarily written to disk for processing
- All GPXScaler functionality is available through the web interface
- Timing calculations use the same physics model as the console app

## Contributing

The web application is designed to be easily extensible:
- Add new visualization features in `static/js/app.js`
- Extend styling in `static/css/style.css`
- Add new endpoints in `app.py`
- Enhance GPX processing in `utils/gpx_integration.py`

## License

Same license as the main GPX Scaler project.
