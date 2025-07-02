# GPXScaler

GPXScaler is a Python tool designed to scale GPX route files both in distance and elevation (ascent/descent), while also allowing you to set a new starting coordinate for the routes.

## Features

- **Scale Distance**: Modify the horizontal distance of routes by a specified factor
- **Scale Elevation**: Adjust ascent and descent values by the same scaling factor
- **Relocate Routes**: Set new starting coordinates for your routes
- **Batch Processing**: Process all GPX files in a specified folder
- **Route Analysis**: Display total distance and ascent for each route before scaling
- **Auto-Location**: Attempts to use device's current location as default starting point

## Usage

### Command Line Arguments

```bash
python gpxscaler.py [--folder FOLDER] [--scale FACTOR] [--min-distance DISTANCE] [--start-lat LATITUDE] [--start-lon LONGITUDE]
```

#### Arguments

- `--folder`: Target folder containing GPX files (default: current directory)
- `--scale`: Scaling factor for distance and elevation (e.g., 0.5 for half size, 2.0 for double)
- `--min-distance`: Minimum distance in km - scale will be automatically adjusted if the scaled route would be shorter than this
- `--start-lat`: New starting latitude coordinate
- `--start-lon`: New starting longitude coordinate

### Interactive Mode

If no command line arguments are provided, the script will run in interactive mode:

1. **Folder Selection**: Choose the folder containing GPX files (defaults to current directory)
2. **Route Analysis**: View distance and elevation data for each GPX file
3. **Scale Factor**: Enter the desired scaling factor
4. **Minimum Distance** (optional): Set a minimum distance requirement - routes shorter than this will be automatically scaled up
5. **Starting Coordinates**: Set new starting coordinates (attempts to auto-detect current location)

### Examples

```bash
# Scale all GPX files in current directory by 75% with minimum 50km distance and set new start point
python gpxscaler.py --scale 0.75 --min-distance 50 --start-lat 45.5088 --start-lon -73.5878

# Process GPX files in a specific folder with minimum distance requirement
python gpxscaler.py --folder "./tour-routes" --scale 1.2 --min-distance 40

# Interactive mode (no arguments)
python gpxscaler.py
```

## Requirements

- Python 3.6+
- gpxpy library for GPX file parsing
- requests library for location services (optional)

## Installation

1. Clone or download this repository
2. Install required dependencies:

   ```bash
   pip install gpxpy requests
   ```

## Output

The scaled GPX files will be saved with a suffix indicating the scaling factor, for example:

- `stage-1-route.gpx` → `stage-1-route_scaled_075.gpx` (for 0.75x scaling)

## Notes

- Original GPX files are preserved; scaled versions are created as new files
- Elevation scaling applies proportionally to both ascent and descent
- The tool maintains the relative shape and characteristics of the original routes
- Location auto-detection requires an internet connection and may not work in all environments

## License

This project is open source. Feel free to modify and distribute as needed.
