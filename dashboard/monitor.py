#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path
from threading import Thread
from flask import Flask, render_template, jsonify, send_from_directory

# Root klasör ekle
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Test ortamını yükle
from test.test_environment import TestEnvironment

# Klasör yolları
frontend_dir = Path("/home/ahmetbekir/sdn-video-streaming/se3506")

template_dir = frontend_dir
static_dir = frontend_dir / "static"

# Flask app oluştur
app = Flask(
    __name__,
    template_folder=str(template_dir),
    static_folder=str(static_dir)
)

test_env = TestEnvironment()
stats_history = []

# Arka planda stats toplayıcı
def collect_stats():
    while True:
        stats = test_env.get_stats()
        stats["timestamp"] = time.time()
        stats_history.append(stats)
        if len(stats_history) > 100:
            stats_history.pop(0)
        time.sleep(1)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/api/stats')
def get_stats():
    return jsonify(test_env.get_stats())

@app.route('/api/history')
def get_history():
    return jsonify(stats_history)

@app.route('/api/simulate/<video_name>')
def simulate_request(video_name):
    client_ip = "10.0.0.1"
    success = test_env.simulate_request(client_ip, f"bbb_{video_name}.mp4")
    return jsonify({'success': success})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(static_dir, filename)

def main():
    print(f"[INFO] Template directory: {template_dir}")
    print(f"[INFO] index.html exists: {(template_dir / 'index.html').exists()}")
    print(f"[INFO] Static directory exists: {static_dir.exists()}")
    
    Thread(target=collect_stats, daemon=True).start()
    app.run(host="0.0.0.0", port=5001, debug=True)

if __name__ == "__main__":
    main()
