import os
import datetime
import logging
import subprocess
import cv2
import numpy as np

# Configure logging for better visibility into the screen capture process
logger = logging.getLogger(__name__)

# Define the path to the ADB (Android Debug Bridge) executable.
# This path is crucial for interacting with Android devices.
# It should be configured correctly for your environment.
ADB_PATH = r"A:\all folders\MEmu\Microvirt\MEmu\adb.exe"

class ScreenCapture:
    """
    A class responsible for capturing screenshots from an Android device
    using ADB (Android Debug Bridge) commands.
    """
    def __init__(self):
        """
        Initializes the ScreenCapture class.
        No special setup is needed here as ADB commands are executed directly.
        """
        pass

    def take_screenshot(self, filename=None, save_dir="assets/screenshots", save_to_disk=True):
        """
        Captures a screenshot from the connected Android device.
        Optionally saves it locally and returns the image data as a NumPy array.

        Args:
            filename (str, optional): The desired name for the screenshot file.
                                      If None, a timestamped filename will be used.
            save_dir (str): The local directory where the screenshot will be saved (if save_to_disk is True).
            save_to_disk (bool): If True, the screenshot will be saved to a local file.
                                 If False, it will only be processed in memory and the local file will be deleted.

        Returns:
            tuple[str | None, np.ndarray | None]: A tuple containing:
                                                 - The absolute path to the saved screenshot (str) if save_to_disk is True,
                                                   otherwise None.
                                                 - The screenshot image data as a NumPy array (np.ndarray),
                                                   or None if capture/decoding failed.
        """
        local_temp_path = os.path.join(save_dir, "temp_screenshot.png") # Temporary local path
        remote_temp_path = "/sdcard/screen.png" # Temporary path on device
        final_save_path = None
        screenshot_np = None

        try:
            # Step 1: Take screenshot on device and save to a temporary file on the device
            screencap_cmd = [ADB_PATH, "shell", "screencap", "-p", remote_temp_path]
            logger.debug(f"Executing: {' '.join(screencap_cmd)}")
            result = subprocess.run(screencap_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"Failed to take screenshot on device: {result.stderr}")
                return None, None

            # Step 2: Pull the temporary screenshot from device to local machine
            pull_cmd = [ADB_PATH, "pull", remote_temp_path, local_temp_path]
            logger.debug(f"Executing: {' '.join(pull_cmd)}")
            result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"Failed to pull screenshot to local: {result.stderr}")
                return None, None

            # Step 3: Read the image into a NumPy array from the local temporary file
            screenshot_np = cv2.imread(local_temp_path, cv2.IMREAD_UNCHANGED)
            if screenshot_np is None:
                logger.error(f"Could not read screenshot image from {local_temp_path} into NumPy array.")
                return None, None

            # Step 4: Handle saving to disk and cleanup
            if save_to_disk:
                # Ensure save directory exists
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                    logger.info(f"Created directory: {save_dir}")

                # Generate filename if not provided
                if filename is None:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"screenshot_{timestamp}.png"
                if not filename.lower().endswith(".png"):
                    filename += ".png"
                final_save_path = os.path.join(save_dir, filename)

                # Move/rename the temporary file to its final destination
                os.replace(local_temp_path, final_save_path)
                logger.info(f"Screenshot saved to: {os.path.abspath(final_save_path)}")
            else:
                # If not saving to disk, delete the local temporary file immediately
                if os.path.exists(local_temp_path):
                    os.remove(local_temp_path)
                    logger.debug(f"Deleted temporary local screenshot: {local_temp_path}")

            # Step 5: Remove temporary screenshot from device
            rm_cmd = [ADB_PATH, "shell", "rm", remote_temp_path]
            subprocess.run(rm_cmd, capture_output=True, text=True, timeout=10) # No need to check return code for rm

            return os.path.abspath(final_save_path) if final_save_path else None, screenshot_np

        except FileNotFoundError:
            logger.error(f"ADB executable not found at {ADB_PATH}. Please ensure the path is correct and ADB is installed.")
            return None, None
        except subprocess.TimeoutExpired as e:
            logger.error(f"ADB command timed out: {e}. Consider increasing timeout if device is slow.")
            return None, None
        except Exception as e:
            logger.error(f"An unexpected error occurred during screenshot capture: {e}")
            return None, None

# This block runs only when the script is executed directly (not imported as a module)
if __name__ == "__main__":
    # Configure basic logging for console output
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("Attempting to take a screenshot for testing purposes...")
    sc = ScreenCapture()
    # Test with saving to disk
    path_saved, np_saved = sc.take_screenshot(filename="test_saved_screenshot.png", save_to_disk=True)
    if path_saved:
        print(f"Test screenshot saved to: {path_saved}")
    else:
        print("Failed to save test screenshot.")

    # Test without saving to disk
    path_temp, np_temp = sc.take_screenshot(save_to_disk=False)
    if np_temp is not None:
        print("Test screenshot captured in memory (not saved to disk).")
    else:
        print("Failed to capture test screenshot in memory.")