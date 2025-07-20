import cv2
import numpy as np
import os
import logging
import sys

# Configure logging for better visibility into the image recognition process
logger = logging.getLogger(__name__)

class ImageRecognition:
    """
    A class for performing basic image recognition tasks, primarily template matching,
    to find occurrences of smaller images (templates) within larger images (screenshots).
    This version is optimized with automatic masking for templates with solid backgrounds.
    """
    def __init__(self):
        """
        Initializes the ImageRecognition class.
        """
        pass

    def find_template(self, screenshot_source, template_path, threshold=0.8, roi=None):
        """
        Finds a template image within a given screenshot using OpenCV's template matching.
        It automatically creates a mask to ignore a solid white background in the template.

        Args:
            screenshot_source (str or np.ndarray): The source of the screenshot (path or NumPy array).
            template_path (str): The absolute path to the template image.
            threshold (float): The confidence threshold (0.0 to 1.0) for a match.
            roi (tuple, optional): A tuple (x, y, w, h) defining the Region of Interest.

        Returns:
            tuple: A tuple (x, y, width, height) of the matched region, or None if not found.
        """
        # --- 1. Load Template and Screenshot ---
        if not os.path.exists(template_path):
            logger.error(f"Template not found: {template_path}")
            return None
        template_color = cv2.imread(template_path)
        if template_color is None:
            logger.error(f"Could not read template image: {template_path}")
            return None
        template_height, template_width = template_color.shape[:2]

        if isinstance(screenshot_source, str):
            if not os.path.exists(screenshot_source):
                logger.error(f"Screenshot not found: {screenshot_source}")
                return None
            screenshot_color = cv2.imread(screenshot_source)
            if screenshot_color is None:
                logger.error(f"Could not read screenshot image: {screenshot_source}")
                return None
        elif isinstance(screenshot_source, np.ndarray):
            screenshot_color = screenshot_source
        else:
            logger.error("Invalid screenshot_source type. Must be str (path) or np.ndarray.")
            return None

        # --- 2. Handle ROI --- 
        if roi:
            x, y, w, h = roi
            if x < 0 or y < 0 or x + w > screenshot_color.shape[1] or y + h > screenshot_color.shape[0]:
                logger.error(f"ROI {roi} is out of bounds for screenshot shape {screenshot_color.shape}")
                return None
            search_region_color = screenshot_color[y:y+h, x:x+w]
        else:
            search_region_color = screenshot_color

        # --- 3. Create Mask and Convert to Grayscale ---
        background_color = np.array([255, 255, 255])
        mask = cv2.inRange(template_color, background_color, background_color)
        mask = cv2.bitwise_not(mask)

        # Convert images to grayscale for matching
        template_gray = cv2.cvtColor(template_color, cv2.COLOR_BGR2GRAY)
        search_region_gray = cv2.cvtColor(search_region_color, cv2.COLOR_BGR2GRAY)

        if template_height > search_region_gray.shape[0] or template_width > search_region_gray.shape[1]:
            logger.warning(f"Template '{os.path.basename(template_path)}' ({template_width}x{template_height}) is larger than the search region ({search_region_gray.shape[1]}x{search_region_gray.shape[0]}).")
            return None

        # --- 4. Perform Masked Template Matching ---
        try:
            result = cv2.matchTemplate(search_region_gray, template_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                match_loc = max_loc
                if roi:
                    final_x = roi[0] + match_loc[0]
                    final_y = roi[1] + match_loc[1]
                else:
                    final_x = match_loc[0]
                    final_y = match_loc[1]

                logger.info(f"Found template '{os.path.basename(template_path)}' at ({final_x}, {final_y}) with confidence {max_val:.2f}")
                return (final_x, final_y, template_width, template_height)
            else:
                logger.info(f"Template '{os.path.basename(template_path)}' not found with confidence above {threshold:.2f} (max confidence: {max_val:.2f})")
                return None

        except Exception as e:
            logger.error(f"Error during template matching: {e}", exc_info=True)
            return None

# This block executes only when the script is run directly (not imported as a module)
if __name__ == "__main__":
    # Configure basic logging to display information and errors to the console
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Add the project root directory to the system path.
    # This ensures that modules like 'core.screen_capture' can be imported correctly
    # when this script is run standalone.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    sys.path.insert(0, project_root)

    # --- Example Usage of ImageRecognition ---
    # To run this example, ensure you have:
    # 1. An Android emulator/device connected via ADB.
    # 2. A screenshot can be taken successfully by screen_capture.py.
    # 3. A template image (e.g., a button from your game) exists at the specified path.
    
    print("Starting Image Recognition example...")
    
    # Step 1: Take a fresh screenshot from the device
    from core.screen_capture import ScreenCapture
    sc = ScreenCapture()
    test_screenshot_path = sc.take_screenshot(filename="test_screenshot.png")

    if test_screenshot_path:
        # Step 2: Define the path to the template image you want to find.
        # Replace "START_GAME.PNG" with the actual name of your template image.
        # Ensure the path is correct relative to your project structure.
        test_template_path = os.path.abspath(os.path.join("assets", "buttons", "START_GAME.PNG"))
        
        # Create an instance of ImageRecognition
        ir = ImageRecognition()
        
        # Attempt to find the template in the screenshot
        found_location = ir.find_template(test_screenshot_path, test_template_path)

        if found_location:
            # If the template is found, unpack its coordinates and dimensions
            x, y, w, h = found_location
            print(f"Template found at: x={x}, y={y}, width={w}, height={h}")
            
            # Optional: Draw a green rectangle around the found region on the screenshot
            # and save it as a new image to visually verify the match.
            try:
                img = cv2.imread(test_screenshot_path) # Reload the screenshot to draw on it
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2) # Draw rectangle (BGR color: Green)
                output_path = os.path.join(os.path.dirname(test_screenshot_path), "matched_screenshot.png")
                cv2.imwrite(output_path, img) # Save the image with the drawn rectangle
                print(f"Matched region highlighted in: {output_path}")
            except Exception as e:
                logger.warning(f"Could not draw rectangle on screenshot: {e}")
        else:
            print("Template not found in the screenshot.")
    else:
        print("Could not take a screenshot to perform image recognition. Please check ADB connection and path.")