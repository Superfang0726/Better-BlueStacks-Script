import os
import time
from ppadb.client import Client as AdbClient
import cv2
import numpy as np


# BlueStacks Bot Class to handle ADB interactions
# BlueStacks 機器人類別，用於處理 ADB 互動
class BlueStacksBot:
    def __init__(self, device_host="127.0.0.1", device_port=5555, logger=None):
        """
        Initialize the bot and connect to the ADB server and device.
        初始化機器人並連接到 ADB 伺服器與設備。
        """
        self.logger = logger if logger else print
        
        # ADB Server is always local to the script (inside container or local machine)
        # ADB 伺服器永遠在本地 (容器內或本機)
        adb_server_host = "127.0.0.1"
        adb_server_port = 5037
        
        self.logger(f"Connecting to ADB Server at {adb_server_host}:{adb_server_port}...")
        self.client = AdbClient(host=adb_server_host, port=adb_server_port)
        self.device = None
        
        # Connect to the target device
        # 連接到目標設備
        target_device = f"{device_host}:{device_port}"
        self.logger(f"Connecting to device at {target_device}...")
        
        try:
            self.client.remote_connect(device_host, device_port)
        except Exception as e:
            self.logger(f"Remote connect failed: {e}")

        try:
            devices = self.client.devices()
            if not devices:
                self.logger("No devices found after connect.")
                self.device = None
            else:
                # Find the specific device if possible
                try:
                    self.device = self.client.device(target_device)
                except:
                    self.device = devices[0]
                    
                if self.device:
                    self.logger(f"Connected to device: {self.device.serial}")
                else:
                    self.logger("Detailed device connect failed.")
                
        except Exception as e:
            self.logger(f"Failed to get devices: {e}")
            self.device = None

    def click(self, x, y):
        """
        Simulate a tap at the given coordinates.
        模擬在給定座標點擊。
        
        Args:
            x (int): X coordinate.
            y (int): Y coordinate.
        """
        if self.device:
            # Send the shell command to tap
            # 發送 shell 指令進行點擊
            self.device.shell(f"input tap {x} {y}")
            self.logger(f"Clicked at ({x}, {y})")
            # 已點擊於 ({x}, {y})
        else:
            self.logger("Device not connected.")
            # 設備未連接。


    def swipe(self, x1, y1, x2, y2, duration=500):
        """
        Simulate a swipe from (x1, y1) to (x2, y2).
        模擬從 (x1, y1) 滑動到 (x2, y2)。
        
        Args:
            x1, y1: Start coordinates / 起始座標
            x2, y2: End coordinates / 結束座標
            duration: Duration in milliseconds / 持續時間 (毫秒)
        """
        if self.device:
            self.device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
            self.logger(f"Swiped from ({x1}, {y1}) to ({x2}, {y2})")
            # 已從 ({x1}, {y1}) 滑動到 ({x2}, {y2})
        else:
            self.logger("Device not connected.")

    def home(self):
        """
        Press the Home button.
        按下 Home 鍵。
        """
        if self.device:
            self.device.shell("input keyevent 3")
            self.logger("Pressed HOME button")
        else:
            self.logger("Device not connected.")

    def clear_recent_apps(self):
        """
        Open the recent apps / app switcher screen.
        打開「最近使用的應用程式」(多工畫面)。
        """
        if self.device:
            # Open recent apps screen (App Switcher / Overview)
            self.device.shell("input keyevent 187")  # KEYCODE_APP_SWITCH
            self.logger("Opened Recent Apps screen")
        else:
            self.logger("Device not connected.")

    def screencap(self, filename="screenshot.png"):
        """
        Capture the screen and save to a file.
        擷取螢幕並存檔。
        """
        if self.device:
            try:
                # Get the screenshot binary data
                # 獲取截圖的二進制數據
                result = self.device.screencap()
                with open(filename, "wb") as f:
                    f.write(result)
                self.logger(f"Screenshot saved to {filename}")
                # 截圖已保存至 {filename}
            except Exception as e:
                self.logger(f"Failed to take screenshot: {e}")
        else:
            self.logger("Device not connected.")

    def get_pixel_color(self, x, y):
        """
        Get the color of a specific pixel at (x, y).
        獲取特定座標 (x, y) 的像素顏色。
        Returns: (B, G, R) tuple or None
        """
        if not self.device:
            return None
            
        try:
            result = self.device.screencap()
            img_array = np.frombuffer(result, np.uint8)
            img_color = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img_color is not None:
                # height, width, channels
                h, w, _ = img_color.shape
                if 0 <= x < w and 0 <= y < h:
                    bgr = img_color[y, x]
                    return tuple(map(int, bgr))
                else:
                    self.logger(f"Coordinates ({x}, {y}) out of bounds ({w}x{h})")
        except Exception as e:
            self.logger(f"Failed to get pixel color: {e}")
            
        return None

    def find_with_sift(self, template_path, timeout=3, min_match_count=10):
        """
        Find image using SIFT feature matching. Robust to scale and rotation.
        使用 SIFT 特徵比對尋找圖片。對縮放和旋轉有較強的魯棒性。
        """
        if not self.device: return None
        
        # Load template
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            self.logger(f"Could not load template: {template_path}")
            return None
            
        # Initialize SIFT
        try:
            sift = cv2.SIFT_create()
        except:
            self.logger("SIFT not available.")
            return None

        kp1, des1 = sift.detectAndCompute(template, None)
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Capture screen
            result = self.device.screencap()
            img_array = np.frombuffer(result, np.uint8)
            img_color = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            target = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
            
            # Compute SIFT on target
            kp2, des2 = sift.detectAndCompute(target, None)
            
            if des2 is None: 
                time.sleep(0.5)
                continue
            
            # Match
            flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
            matches = flann.knnMatch(des1, des2, k=2)
            
            # Lowe's ratio test
            good = []
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    good.append(m)
            
            # self.logger(f"SIFT Good Matches: {len(good)}/{min_match_count}")

            if len(good) > min_match_count:
                # Homography to find location
                src_pts = np.float32([ kp1[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
                dst_pts = np.float32([ kp2[m.trainIdx].pt for m in good ]).reshape(-1,1,2)
                
                M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if M is not None:
                    h, w = template.shape
                    pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)
                    dst = cv2.perspectiveTransform(pts, M)
                    
                    # --- State Verification (Pixel Check) ---
                    # Use Homography to unwarp the detected region from the screenshot back to template size
                    # This lets us verify if the pixel content (e.g. text/state) actually matches
                    try:
                        M_inv = np.linalg.inv(M)
                        # Warp the target image (screenshot) back to the template's perspective
                        warped_patch = cv2.warpPerspective(target, M_inv, (w, h))
                        
                        # Compare the unwrapped patch with the original template
                        # Using Correlation Coefficient (1.0 = perfect match)
                        res = cv2.matchTemplate(template, warped_patch, cv2.TM_CCOEFF_NORMED)
                        score = res[0][0] # Result is 1x1 array
                        
                        # self.logger(f"SIFT Candidate Score: {score}")
                        
                        # If pixel correlation is too low, it means we found the shape/text 
                        # but the internal details (like ON/OFF state) don't match.
                        if score < 0.7: # Raised to 0.7 to prevent false positives (was 0.55)
                            self.logger(f"Rejected SIFT match due to low pixel correlation: {score:.2f}")
                            continue
                            
                    except Exception as e:
                        # If warping fails, fallback to trusting SIFT (or log warning)
                        self.logger(f"Verification warning: {e}")
                        pass
                    # ----------------------------------------
                    
                    # Calculate center
                    center_x = int(np.mean(dst[:, 0, 0]))
                    center_y = int(np.mean(dst[:, 0, 1]))
                    
                    return (center_x, center_y)
            
            time.sleep(0.5)
                    
        return None

    def find_with_template_matching(self, template_path, timeout=3, threshold=0.7):
        """
        Fallback method using Multi-Scale Template Matching.
        Best for low-feature images (buttons, flat icons) where SIFT fails.
        """
        if not self.device: return None

        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            return None
        t_h, t_w = template.shape[:2]

        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.device.screencap()
            img_array = np.frombuffer(result, np.uint8)
            img_color = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)

            # Multi-scale loop - Expanded range and steps
            found = None
            for scale in np.linspace(0.5, 1.5, 20): 
                resized = cv2.resize(gray, None, fx=scale, fy=scale)
                if resized.shape[0] < t_h or resized.shape[1] < t_w:
                    continue

                res = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)

                if found is None or max_val > found[0]:
                    found = (max_val, max_loc, scale)

            if found and found[0] >= threshold:
                max_val, max_loc, scale = found
                # self.logger(f"Template Found! Score: {max_val:.2f} Scale: {scale:.2f}")
                
                # Map back to original coordinate
                center_x = int((max_loc[0] + t_w/2) / scale)
                center_y = int((max_loc[1] + t_h/2) / scale)
                return (center_x, center_y)
            
            time.sleep(0.5)
        return None

    def find_and_click(self, template_path, timeout=3, click_target=True, method='auto'):
        """
        Find an image template on the screen and optionally click it.
        在螢幕上尋找圖片並可選點擊。
        
        Args:
            template_path (str): Path to image template.
            timeout (int): Search timeout in seconds.
            click_target (bool): Whether to click if found.
            method (str): 'auto', 'sift', or 'template'.
        """
        if not self.device:
            self.logger("Device not connected.")
            return False

        center = None
        method = method.lower()
        
        if method == 'sift':
            # Force SIFT
            center = self.find_with_sift(template_path, timeout=timeout)
            
        elif method == 'template':
            # Force Template Matching
            center = self.find_with_template_matching(template_path, timeout=timeout, threshold=0.8)
            
        else: # auto
            # 1. Try SIFT (Robust)
            center = self.find_with_sift(template_path, timeout=min(timeout, 2))
            
            if not center:
                # 2. Fallback to Template Matching
                center = self.find_with_template_matching(template_path, timeout=min(timeout, 2), threshold=0.8)
                if center:
                     self.logger(f"Template Matching Found {template_path} at ({center[0]}, {center[1]})")

        if center:
            self.logger(f"Found at ({center[0]}, {center[1]})")
            if click_target:
                self.click(center[0], center[1])
            return center
        else:
            self.logger(f"Failed to find {template_path}")
            return None

def main():
    """
    Main execution entry point for standalone testing.
    獨立測試的主要入口點。
    
    This function allows testing the bot connection and basic actions 
    without running the Flask server.
    此功能允許在不運行 Flask 伺服器的情況下測試機器人連接和基本動作。
    """
    
    # Get host and port from environment variables or use defaults
    # 從環境變數獲取主機和連接埠，或使用預設值
    host = os.environ.get("ADB_HOST", "127.0.0.1")
    port = int(os.environ.get("ADB_PORT", 5555))
    
    print(f"Initializing bot connecting to {host}:{port}...")
    
    bot = BlueStacksBot(host, port)
    
    if bot.device:
        # Example interaction loop
        # 範例互動迴圈
        
        # Take an initial screenshot
        # 拍一張初始截圖
        bot.screencap("before_action.png")
        
        # Wait a bit
        time.sleep(1)
        
        # Example click (adjust coordinates for your specific app)
        # 範例點擊 (請針對您的應用程式調整座標)
        # bot.click(500, 500)
        
        print("Test sequence completed.")
    else:
        print("Bot failed to initialize device connection.")

if __name__ == "__main__":
    main()
