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

app = Flask(__name__, template_folder=str(project_root / 'se3506'), static_folder=str(project_root / 'se3506'), static_url_path='/')
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

def main():
    # Start stats collection in background
    collector = Thread(target=collect_stats, daemon=True)
    collector.start()
    
    # Start Flask app on port 5001 instead of 5000
    app.run(host='0.0.0.0', port=5001, debug=True)

if __name__ == '__main__':
    main() 