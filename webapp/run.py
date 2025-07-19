#!/usr/bin/env python3
"""
Quick start script for GPX Scaler Web Application
"""

import subprocess
import sys
import os
from pathlib import Path

def check_requirements():
    """Check if required packages are installed."""
    try:
        import flask
        import gpxpy
        print("✓ Required packages are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing required package: {e}")
        print("Installing requirements...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        return True

def main():
    """Main function to start the web application."""
    print("GPX Scaler Web Application")
    print("=" * 40)

    # Change to webapp directory
    webapp_dir = Path(__file__).parent
    os.chdir(webapp_dir)

    # Check requirements
    if not check_requirements():
        print("Failed to install requirements")
        return 1

    # Get port from environment variable or default to 5001
    # (5000 conflicts with AirPlay on macOS)
    port = int(os.environ.get('PORT', 5001))

    print("\nStarting web application...")
    print(f"Open your browser and go to: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    print("-" * 40)

    try:
        # Import and run the Flask app
        from app import app
        app.run(host='0.0.0.0', port=port, debug=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
