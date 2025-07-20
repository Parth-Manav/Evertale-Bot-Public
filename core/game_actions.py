import os
import logging
import subprocess
import time
import sys


# Import necessary modules for screen capture, image recognition, and advanced image analysis
from core.screen_capture import ScreenCapture
from core.image_recognition import ImageRecognition
from core.image_analyzer import check_region_for_color, find_references, get_first_location

# Configure logging for better visibility into the bot's actions
logger = logging.getLogger(__name__)

# Define the path to the ADB (Android Debug Bridge) executable.
# This path should be configured correctly for your environment.
ADB_PATH = r"A:\all folders\MEmu\Microvirt\MEmu\adb.exe"

class GameActions:
    """
    A class to encapsulate various actions performed within the game,
    including screen interaction, image recognition, and game state management.
    """
    def __init__(self):
        """
        Initializes the GameActions class, setting up instances for
        screen capture and basic image recognition.
        """
        self.screen_capture = ScreenCapture()
        self.image_recognition = ImageRecognition()

    def click_image(self, template_path, confidence=0.7, max_attempts=3, delay_after_click=1):
        """
        Attempts to find a specified template image on the screen and clicks its center.
        This method retries multiple times if the image is not found immediately.

        Args:
            template_path (str): Absolute path to the template image (e.g., a button image).
            confidence (float): The minimum confidence level (0.0 to 1.0) required to consider
                                a match successful. Higher values mean stricter matching.
            max_attempts (int): The maximum number of times to try finding and clicking the image.
            delay_after_click (int): The time in seconds to wait after a successful click
                                     before returning. This helps in stabilizing the game state.

        Returns:
            bool: True if the image was found and successfully clicked within the given attempts,
                  False otherwise.
        """
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Attempt {attempt}/{max_attempts}: Looking for {os.path.basename(template_path)}...")
            
            # Take a screenshot of the current game screen
            screenshot_path, screenshot_np = self.screen_capture.take_screenshot(save_to_disk=False)
            if screenshot_np is None:
                logger.warning("Failed to take screenshot or convert to numpy array. Retrying...")
                time.sleep(delay_after_click) # Wait before retrying screenshot
                continue

            # Use the advanced image_analyzer to find references of the template in the screenshot
            # We pass [template_path] as a list because find_references expects a list of paths.
            locations = find_references(screenshot_np, [template_path], tolerance=confidence)
            # Get the first found location, if any
            found_location = get_first_location(locations)

            if found_location:
                # Extract coordinates and dimensions of the found image
                # Note: The image_analyzer's get_first_location returns [x, y] directly,
                # so w and h are not directly available from it.
                # For simplicity, we'll assume the click is at the found (x,y)
                # If precise center calculation based on template size is needed,
                # the template image itself would need to be loaded here to get its dimensions.
                # For now, we'll just use the found_location as the click point.
                center_x, center_y = found_location[0], found_location[1]
                
                logger.info(f"Found {os.path.basename(template_path)} at ({center_x},{center_y}). Clicking center...")
                
                try:
                    # Execute ADB tap command to simulate a click at the calculated center
                    tap_cmd = [ADB_PATH, "shell", "input", "tap", str(center_x), str(center_y)]
                    result = subprocess.run(tap_cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully clicked at ({center_x},{center_y}).")
                        time.sleep(delay_after_click) # Wait for game to react to the click
                        return True
                    else:
                        logger.error(f"ADB tap command failed: {result.stderr}")
                except Exception as e:
                    logger.error(f"Error executing ADB tap: {e}")
            else:
                logger.info(f"{os.path.basename(template_path)} not found in this attempt.")
            
            time.sleep(delay_after_click) # Wait before the next attempt

        logger.warning(f"Failed to find and click {os.path.basename(template_path)} after {max_attempts} attempts.")
        return False

    def wait_for_checkpoint(self, checkpoint_path, confidence=0.7, timeout=30, check_interval=2):
        """
        Waits for a specific checkpoint image to appear on the screen within a given timeout.
        This is useful for pausing execution until a certain game state is reached.

        Args:
            checkpoint_path (str): Absolute path to the checkpoint image to wait for.
            confidence (float): The minimum confidence level (0.0 to 1.0) for image matching.
            timeout (int): The maximum time in seconds to wait for the checkpoint image.
            check_interval (int): The time in seconds to wait between each check (screenshot and analysis).

        Returns:
            bool: True if the checkpoint image is found within the timeout, False otherwise.
        """
        logger.info(f"Waiting for checkpoint: {os.path.basename(checkpoint_path)} (timeout: {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Take a screenshot
            screenshot_path, screenshot_np = self.screen_capture.take_screenshot(save_to_disk=False)
            if screenshot_np is None:
                logger.warning("Failed to take screenshot or convert to numpy array. Retrying...")
                time.sleep(check_interval)
                continue

            # Use image_analyzer to find the checkpoint image
            locations = find_references(screenshot_np, [checkpoint_path], tolerance=confidence)
            
            # Check if the checkpoint was found
            if get_first_location(locations):
                logger.info(f"Checkpoint '{os.path.basename(checkpoint_path)}' found.")
                return True
            
            logger.info(f"Checkpoint not found. Retrying in {check_interval} seconds...")
            time.sleep(check_interval)

        logger.warning(f"Timeout reached. Checkpoint '{os.path.basename(checkpoint_path)}' not found after {timeout} seconds.")
        return False

    def tap(self, x, y, delay_after_tap=1):
        """
        Taps a specific coordinate on the screen using ADB.

        Args:
            x (int): The x-coordinate to tap.
            y (int): The y-coordinate to tap.
            delay_after_tap (int): Delay in seconds after the tap.
        """
        logger.info(f"Tapping at coordinates ({x},{y})...")
        try:
            # ADB tap command
            tap_cmd = [ADB_PATH, "shell", "input", "tap", str(x), str(y)]
            result = subprocess.run(tap_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"Successfully tapped at ({x},{y}).")
                time.sleep(delay_after_tap)
                return True
            else:
                logger.error(f"ADB tap command failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error executing ADB tap: {e}")
            return False

    def find_and_click_any(self, template_paths, folder, confidence=0.88, max_attempts=3, delay_after_click=1):
        """
        Finds any of the provided template images on the screen and clicks the first one found.
        This is useful when multiple visual cues can indicate the same interactive element.

        Args:
            template_paths (list): A list of absolute paths to the template images.
            folder (str): The subfolder within 'reference_images' where templates are located.
                          (Note: This parameter might be redundant if template_paths are already absolute).
            confidence (float): The minimum confidence level for image matching.
            max_attempts (int): Maximum number of attempts to find and click an image.
            delay_after_click (int): Delay in seconds after a successful click.

        Returns:
            bool: True if any image was found and clicked, False otherwise.
        """
        # Extract just the filenames from the full paths for logging purposes
        template_names = [os.path.basename(p) for p in template_paths]

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Attempt {attempt}/{max_attempts}: Looking for any of {template_names}...")
            
            screenshot_path, screenshot_np = self.screen_capture.take_screenshot(save_to_disk=False)
            if screenshot_np is None:
                logger.warning("Failed to take screenshot or convert to numpy array. Retrying...")
                time.sleep(delay_after_click)
                continue

            # Find references for all provided templates
            # Note: The 'folder' parameter here is passed directly to find_references,
            # but find_references in image_analyzer.py now expects absolute paths in template_paths.
            # This 'folder' parameter might need re-evaluation or removal if template_paths are always absolute.
            locations = find_references(screenshot_np, template_paths, tolerance=confidence)
            # Get the first valid location found among all templates
            found_location = get_first_location(locations)

            if found_location:
                # Extract the center coordinates from the found location
                center_x, center_y = found_location[0], found_location[1]
                
                logger.info(f"Found one of {template_names} at ({center_x},{center_y}). Clicking...")
                
                try:
                    # Execute ADB tap command
                    tap_cmd = [ADB_PATH, "shell", "input", "tap", str(center_x), str(center_y)]
                    result = subprocess.run(tap_cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info(f"Successfully clicked at ({center_x},{center_y}).")
                        time.sleep(delay_after_click)
                        return True
                    else:
                        logger.error(f"ADB tap command failed: {result.stderr}")
                except Exception as e:
                    logger.error(f"Error executing ADB tap: {e}")
            else:
                logger.info(f"None of {template_names} found in this attempt.")
            
            time.sleep(delay_after_click)

        logger.warning(f"Failed to find and click any of {template_names} after {max_attempts} attempts.")
        return False

    def wait_for_any_checkpoint(self, checkpoint_paths, folder, confidence=0.88, timeout=30, check_interval=2):
        """
        Waits for any of the specified checkpoint images to appear on the screen.
        This is useful for scenarios where multiple visual cues can indicate a state change.

        Args:
            checkpoint_paths (list): A list of absolute paths to the checkpoint images.
            folder (str): The subfolder within 'reference_images' where templates are located.
                          (Note: This parameter might be redundant if checkpoint_paths are already absolute).
            confidence (float): The minimum confidence level for image matching.
            timeout (int): Maximum time in seconds to wait for any checkpoint.
            check_interval (int): Time in seconds between each check.

        Returns:
            bool: True if any checkpoint is found within the timeout, False otherwise.
        """
        # Extract just the filenames for logging
        checkpoint_names = [os.path.basename(p) for p in checkpoint_paths]
        logger.info(f"Waiting for any of checkpoints: {checkpoint_names} (timeout: {timeout}s)...\n")
        start_time = time.time()

        while time.time() - start_time < timeout:
            screenshot_path, screenshot_np = self.screen_capture.take_screenshot(save_to_disk=False)
            if screenshot_np is None:
                logger.warning("Failed to take screenshot or convert to numpy array. Retrying...")
                time.sleep(check_interval)
                continue

            # Find references for all provided checkpoint images
            # Note: Similar to find_and_click_any, the 'folder' parameter here might be redundant.
            locations = find_references(screenshot_np, checkpoint_paths, tolerance=confidence)
            
            # Check if any of the checkpoints were found
            if any(loc is not None for loc in locations):
                logger.info(f"One of checkpoints {checkpoint_names} found.")
                return True
            
            logger.info(f"None of checkpoints found. Retrying in {check_interval} seconds...")
            time.sleep(check_interval)

        logger.warning(f"Timeout reached. None of checkpoints {checkpoint_names} found after {timeout} seconds.")
        return False

    def check_for_color(self, region, color):
        """
        Checks if a specific color is present within a defined rectangular region of the screen.
        This is useful for detecting subtle visual cues that are not full images, like status indicators.

        Args:
            region (list): A list [left, top, width, height] defining the area to check.
                           'left' and 'top' are the coordinates of the top-left corner,
                           'width' and 'height' define the dimensions of the region.
            color (tuple): An (R, G, B) tuple representing the color to look for.

        Returns:
            bool: True if the color is found within the region, False otherwise.
        """
        logger.info(f"Checking region {region} for color {color}...")
        
        # Take a screenshot
        screenshot_path, screenshot_np = self.screen_capture.take_screenshot(save_to_disk=False)
        if screenshot_np is None:
            logger.warning("Failed to take screenshot or convert to numpy array.")
            return False

        # Delegate the actual color checking to the image_analyzer module, passing the in-memory screenshot
        return check_region_for_color(region, color, screenshot_np)

    def drag_and_drop(self, start_x, start_y, end_x, end_y, duration_ms=1000):
        """
        Performs a drag and drop (swipe) action on the screen using ADB.

        Args:
            start_x (int): The starting x-coordinate of the swipe.
            start_y (int): The starting y-coordinate of the swipe.
            end_x (int): The ending x-coordinate of the swipe.
            end_y (int): The ending y-coordinate of the swipe.
            duration_ms (int): The duration of the swipe in milliseconds. Longer duration means slower swipe.

        Returns:
            bool: True if the drag and drop was successful, False otherwise.
        """
        logger.info(f"Performing drag and drop from ({start_x},{start_y}) to ({end_x},{end_y})...")
        try:
            # ADB swipe command
            swipe_cmd = [ADB_PATH, "shell", "input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)]
            result = subprocess.run(swipe_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("Drag and drop successful.")
                return True
            else:
                logger.error(f"ADB swipe command failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error executing ADB swipe: {e}")
            return False