
import logging
import time
import os
import sys

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.game_actions import GameActions
from config.settings import POPUP_DISMISS_COORDS

logger = logging.getLogger(__name__)

# --- Optimized Checkpoint and ROI Definitions ---
# Define paths to checkpoint images
base_path = os.path.abspath(os.path.join("assets", "checkpoints"))
start_game_checkpoint = os.path.join(base_path, "checkpoint_001_start_game_boot_page.PNG")
sliding_page_checkpoint = os.path.join(base_path, "checkpoint_002_sliding_page.PNG")
home_page_checkpoint = os.path.join(base_path, "checkpoint_003_home_page.PNG")

# Define Regions of Interest (ROI) for each checkpoint to speed up searches
# Format: (x, y, width, height)
# These values should be tuned for your specific screen resolution (e.g., 1920x1080)
ROI_BOOT_PAGE = None      # Search full screen
ROI_SLIDING_PAGE = None     # Search full screen
ROI_HOME_PAGE = None         # Search full screen

# --- State Handler Functions ---
def _handle_home_page(ga):
    logger.info("Successfully reached the home page (main menu). Automation complete.")
    return True  # Indicate completion

def _handle_sliding_page(ga):
    logger.info("Game is at the sliding page. Performing swipe and tap to proceed.")
    ga.drag_and_drop(523, 500, 950, 500)
    time.sleep(2)

    tap_coords = (1833, 143)
    tap_interval = 0.3
    tap_timeout = 30
    start_tap_time = time.time()

    while time.time() - start_tap_time < tap_timeout:
        ga.tap(tap_coords[0], tap_coords[1], delay_after_tap=0)
        time.sleep(tap_interval)

        _, screenshot_np = ga.screen_capture.take_screenshot(save_to_disk=False)
        if screenshot_np is None:
            logger.warning("Failed to take screenshot during rapid tap, continuing...")
            continue

        # Check if the home page is reached, searching only in the defined ROI
        if ga.image_recognition.find_template(screenshot_np, home_page_checkpoint, threshold=0.7, roi=ROI_HOME_PAGE):
            logger.info("Successfully reached the home page from sliding page.")
            return True

    logger.error(f"Failed to reach home page within {tap_timeout}s from sliding page.")
    return False

def _handle_boot_page(ga):
    logger.info("Game is at the start game boot page. Proceeding with rapid tap.")
    tap_coords = (190, 930)
    tap_interval = 0.3
    tap_timeout = 10
    start_tap_time = time.time()
    

    while time.time() - start_tap_time < tap_timeout:
        ga.tap(tap_coords[0], tap_coords[1], delay_after_tap=0)
        time.sleep(tap_interval)

    # After 10 seconds of tapping, take a screenshot and check for the next state
    _, screenshot_np = ga.screen_capture.take_screenshot(save_to_disk=False)
    if screenshot_np is None:
        logger.warning("Failed to take screenshot after rapid tap, cannot determine next state.")
        return False 

    if ga.image_recognition.find_template(screenshot_np, sliding_page_checkpoint, threshold=0.7, roi=ROI_SLIDING_PAGE):
        logger.info("Successfully reached the sliding page.")
        return False  # Not complete, re-evaluate state in the main loop
    elif ga.image_recognition.find_template(screenshot_np, home_page_checkpoint, threshold=0.7, roi=ROI_HOME_PAGE):
        logger.info("Successfully reached the home page directly from boot page.")
        return True  # Automation complete
    else:
        logger.error(f"After {tap_timeout}s of tapping, game state not recognized from boot page.")
        return False
        #Automation 
        

# --- Main Execution Logic ---
def run():
    logger.info("Starting 'getting_main_menue' automation with optimizations...")
    ga = GameActions()

    # Checkpoints now include their specific ROI for targeted searching 
    checkpoints = [
        (start_game_checkpoint, 0.7, _handle_boot_page, ROI_BOOT_PAGE),
        (sliding_page_checkpoint, 0.7, _handle_sliding_page, ROI_SLIDING_PAGE),
        (home_page_checkpoint, 0.7, _handle_home_page, ROI_HOME_PAGE)
    ]
    overall_timeout = 120
    start_overall_time = time.time()

    while time.time() - start_overall_time < overall_timeout:
        # Take a single screenshot, ensuring it's kept in memory
        _, screenshot_np = ga.screen_capture.take_screenshot(save_to_disk=False)
        if screenshot_np is None:
            logger.warning("Failed to capture screenshot, retrying...")
            time.sleep(2)
            continue
        

        state_handled = False
        for cp_path, threshold, handler_func, roi in checkpoints:
            # Pass the screenshot, template, threshold, and ROI to the optimized find_template function
            if ga.image_recognition.find_template(screenshot_np, cp_path, threshold=threshold, roi=roi):
                logger.info(f"Checkpoint '{os.path.basename(cp_path)}' found in its ROI.")
                if handler_func(ga):  # Execute handler
                    return  # Exit if handler signals completion
                state_handled = True
                break  # Re-evaluate state from the top

        if not state_handled:
            logger.info(f"Game state not recognized. Retrying... ({time.time() - start_overall_time:.0f}s elapsed)")
            time.sleep(5)

    logger.error(f"Overall timeout of {overall_timeout}s reached. Failed to get to the main menu.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    run()
    
