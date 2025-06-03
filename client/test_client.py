#!/usr/bin/env python3

import requests
import json
import time
import argparse
import logging
from typing import Dict, List
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('client.log'),
        logging.StreamHandler()
    ]
)

class VideoStreamingClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()

    def get_video_list(self) -> List[Dict]:
        """Get list of available videos from server."""
        try:
            response = self.session.get(f"{self.server_url}/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting video list: {str(e)}")
            return []

    def download_video(self, video_url: str, output_dir: str = '.') -> bool:
        """Download a video file from the server."""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.server_url}{video_url}", stream=True)
            response.raise_for_status()

            # Get filename from URL
            filename = os.path.join(output_dir, video_url.split('/')[-1])
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192  # 8KB chunks
            downloaded = 0

            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Calculate progress
                        progress = (downloaded / total_size) * 100
                        logging.info(f"Download progress: {progress:.1f}%")

            end_time = time.time()
            duration = end_time - start_time
            speed = total_size / (1024 * 1024 * duration)  # MB/s
            
            logging.info(f"Download completed: {filename}")
            logging.info(f"Download speed: {speed:.2f} MB/s")
            return True

        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading video: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Video Streaming Client')
    parser.add_argument('--server', required=True, help='Server URL (e.g., http://localhost:8000)')
    parser.add_argument('--output', default='.', help='Output directory for downloaded videos')
    args = parser.parse_args()

    client = VideoStreamingClient(args.server)
    
    # Get list of available videos
    videos = client.get_video_list()
    if not videos:
        logging.error("No videos available or server not responding")
        return

    # Display available videos
    print("\nAvailable videos:")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video['name']} ({video['size'] / (1024*1024):.1f} MB)")

    # Let user choose a video to download
    while True:
        try:
            choice = int(input("\nEnter video number to download (0 to exit): "))
            if choice == 0:
                break
            if 1 <= choice <= len(videos):
                video = videos[choice - 1]
                print(f"\nDownloading {video['name']}...")
                client.download_video(video['url'], args.output)
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nDownload cancelled by user.")
            break

if __name__ == '__main__':
    main() 