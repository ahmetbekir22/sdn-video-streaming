#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Get the absolute path to the project root directory
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, jsonify
import json
import time
from threading import Thread
import logging

# Now import the TestEnvironment
from test.test_environment import TestEnvironment

# Define paths for templates and static files
frontend_dir = Path("/home/ahmetbekir/sdn-video-streaming/se3506")
template_dir = frontend_dir
static_dir = frontend_dir / "static"  # Assuming static files are in a 'static' subdirectory

# Create Flask app with custom template and static directories
app = Flask(__name__, 
           template_folder=str(template_dir),
           static_folder=str(static_dir) if static_dir.exists() else None)

test_env = TestEnvironment()
stats_history = []

def collect_stats():
    """Collect statistics periodically."""
    while True:
        stats = test_env.get_stats()
        stats['timestamp'] = time.time()
        stats_history.append(stats)
        # Keep only last 100 data points
        if len(stats_history) > 100:
            stats_history.pop(0)
        time.sleep(1)

@app.route('/')
def index():
    """Render the dashboard."""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get current statistics."""
    return jsonify(test_env.get_stats())

@app.route('/api/history')
def get_history():
    """Get historical statistics."""
    return jsonify(stats_history)

@app.route('/api/simulate/<video_name>')
def simulate_request(video_name):
    """Simulate a video request."""
    client_ip = f"10.0.0.1"  # Fixed client IP for simulation
    success = test_env.simulate_request(client_ip, f"bbb_{video_name}.mp4")
    return jsonify({'success': success})

# Add route to serve static files if no static folder is configured
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from the frontend directory."""
    return app.send_from_directory(str(frontend_dir), filename)

def main():
    # Verify paths exist
    if not frontend_dir.exists():
        print(f"Warning: Frontend directory does not exist: {frontend_dir}")
    else:
        print(f"Frontend directory found: {frontend_dir}")
        
    if not (frontend_dir / "index.html").exists():
        print(f"Warning: index.html not found in: {frontend_dir}")
    else:
        print(f"index.html found in: {frontend_dir}")
    
    # Start stats collection in background
    collector = Thread(target=collect_stats, daemon=True)
    collector.start()
    
    # Start Flask app on port 5001 instead of 5000
    print(f"Starting Flask app...")
    print(f"Template directory: {template_dir}")
    print(f"Static directory: {static_dir}")
    app.run(host='0.0.0.0', port=5001, debug=True)

if __name__ == '__main__':
    main()
