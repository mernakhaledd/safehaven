#!/usr/bin/env python3
"""
Raspberry Pi Video Streamer
Turns the Pi into a raw TCP video server.
The laptop connects to this to fetch frames for heavy AI processing.
"""

import subprocess
import sys
import time
import socket

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def start_stream():
    port = 8554
    ip = get_ip_address()
    
    print("="*50)
    print(f"Starting Video Stream on tcp://{ip}:{port}")
    print("="*50)
    print(f"ON LAPTOP: Update 'inference.py' source to: tcp://{ip}:{port}")
    print("OR run: python 9_laptop_inference.py")
    print("="*50)

    # Command to stream H264 via TCP
    # GStreamer is reliable for networking
    # But let's use the simplest rpicam-vid raw TCP listen mode
    cmd = [
        'rpicam-vid',
        '-t', '0',           # No timeout
        '--inline',          # Insert PPS/SPS headers (crucial for streaming)
        '--width', '640',
        '--height', '480',
        '--framerate', '30', # Real-time speed
        '--codec', 'h264',   # Compressed video saves wifi bandwidth
        '--listen',          # Wait for connection
        '-o', f'tcp://0.0.0.0:{port}'
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nStopping Stream...")

if __name__ == "__main__":
    start_stream()
