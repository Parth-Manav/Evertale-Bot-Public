
import logging
import sys
import os

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.evertale_launcher import EvertaleLauncher
from automation import getting_main_menue, dailies, dailies_rewards, banner, id_changing, events, events_rewards, wars

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main function to launch the game and run automation scripts.
    """
    logger.info("Starting the Evertale Bot...")
    
    launcher = EvertaleLauncher()
    
    # Step 1: Launch the game
    game_launched = launcher.run()
    
    if game_launched:
        import time
        time.sleep(15) # Wait for 15 seconds after game launch
        logger.info("Game launched successfully. Starting automation tasks...")
        
        try:
            # Step 2: Run the automation scripts in sequence
            getting_main_menue.run()
            # dailies.run()
            # dailies_rewards.run()
            # banner.run()
            # id_changing.run()
            # events.run()
            # events_rewards.run()
            # wars.run()
            
            logger.info("All automation tasks completed.")
            
        except Exception as e:
            logger.error(f"An error occurred during automation: {e}", exc_info=True)
            
    else:
        logger.error("Failed to launch the game. Automation scripts will not be run.")
        
    logger.info("Evertale Bot has finished its run.")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
