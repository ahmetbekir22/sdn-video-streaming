#!/usr/bin/env python3

import http.server
import socketserver
import os
import json
from datetime import datetime
from typing import Dict, List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)

class VideoStreamingHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for video streaming."""
    
    def __init__(self, *args, **kwargs):
        self.video_files = self._get_video_files()
        super().__init__(*args, **kwargs)

    def _get_video_files(self) -> Dict[str, str]:
        """Get list of available video files in the current directory."""
        video_files = {}
        for file in os.listdir('.'):
            if file.endswith(('.mp4', '.avi', '.mkv')):
                video_files[file] = os.path.getsize(file)
        return video_files

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self._send_video_list()
        elif self.path.startswith('/video/'):
            self._stream_video(self.path[7:])  # Remove '/video/' prefix
        else:
            self.send_error(404, "File not found")

    def _send_video_list(self):
        """Send list of available videos as JSON."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        video_list = [
            {
                'name': name,
                'size': size,
                'url': f'/video/{name}'
            }
            for name, size in self.video_files.items()
        ]
        
        self.wfile.write(json.dumps(video_list).encode())

    def _stream_video(self, filename: str):
        """Stream video file to client."""
        if filename not in self.video_files:
            self.send_error(404, "Video not found")
            return

        try:
            file_size = self.video_files[filename]
            self.send_response(200)
            self.send_header('Content-type', 'video/mp4')
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()

            with open(filename, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # Read in 8KB chunks
                    if not chunk:
                        break
                    self.wfile.write(chunk)

            logging.info(f"Successfully streamed {filename}")
        except Exception as e:
            logging.error(f"Error streaming {filename}: {str(e)}")
            self.send_error(500, "Internal server error")

def run_server(port: int = 8000):
    """Run the video streaming server."""
    handler = VideoStreamingHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"Serving at port {port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logging.info("Server stopped by user")
            httpd.server_close()

if __name__ == '__main__':
    run_server() 