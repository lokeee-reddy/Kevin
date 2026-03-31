import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from nav_msgs.msg import OccupancyGrid
import numpy as np
import cv2  # OpenCV is great for saving images (pip install opencv-python)
import sys
import select
import tty
import termios
import os

class ManualMapSaver(Node):
    def __init__(self):
        super().__init__('manual_map_saver')
        
        # 1. Setup Quality of Service (Must match the Mapper)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        
        self.subscription = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.map_callback,
            qos)
            
        self.latest_map = None
        self.get_logger().info('Ready! Move your Lidar to update the map.')
        self.get_logger().info('PRESS [ENTER] TO SAVE THE MAP AS AN IMAGE.')

    def map_callback(self, msg):
        # Always keep the latest map in memory
        self.latest_map = msg

    def save_map(self):
        if self.latest_map is None:
            print("No map received yet! Move the Lidar slightly...")
            return

        msg = self.latest_map
        width = msg.info.width
        height = msg.info.height
        data = msg.data
        resolution = msg.info.resolution

        print(f"Saving map... Size: {width}x{height}, Resolution: {resolution}m/px")

        # Convert to Image (0-255)
        # 0 (Black) = Wall (100)
        # 255 (White) = Free (0)
        # 127 (Grey) = Unknown (-1)
        
        img_data = np.array(data, dtype=np.int8).reshape((height, width))
        
        # Create image array initialized to Grey
        image = np.full((height, width), 127, dtype=np.uint8)
        
        # Apply colors
        image[img_data == 0] = 255      # Free space -> White
        image[img_data == 100] = 0      # Walls -> Black
        
        # Flip to match image coordinates (Top-Left origin)
        image = np.flipud(image)

        # Generate filename with timestamp
        import time
        filename = f"map_capture_{int(time.time())}.pgm"
        
        # Save simple PGM (Portable Gray Map)
        with open(filename, 'wb') as f:
            header = f"P5\n{width} {height}\n255\n"
            f.write(header.encode('ascii'))
            f.write(image.tobytes())

        print(f"✅ SUCCESS! Map saved to: {os.getcwd()}/{filename}")

# Helper to read keyboard without pressing enter (Non-blocking)
def isData():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

def main():
    rclpy.init()
    saver = ManualMapSaver()

    # Interactive Loop
    try:
        while rclpy.ok():
            rclpy.spin_once(saver, timeout_sec=0.1)
            
            # Check for keyboard input
            if isData():
                c = sys.stdin.read(1)
                if c == '\n':  # If ENTER is pressed
                    saver.save_map()
                    
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    # Settings to capture keyboard input raw
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        main()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
