 Evertale Bot

  An automation bot for the mobile game Evertale, designed to handle daily tasks and events. This bot   
  uses Python, image recognition, and ADB (Android Debug Bridge) to interact with the game running in   
  the MEmu Android emulator.

  Key Features

   * Automated Game Launch: The bot can automatically launch the MEmu emulator and the Evertale game.    
   * Image Recognition: It uses image recognition to identify game states, buttons, and other elements on
     the screen.
   * Task Automation: The bot can perform a sequence of actions to complete daily quests, events, and    
     other tasks.
   * State Management: It uses a state-machine-like approach to navigate through the game's menus and    
     handle different game states.

  Getting Started

  Prerequisites

   * Python 3.x (https://www.python.org/downloads/)
   * MEmu Android Emulator (https://www.memuplay.com/)
   * The Evertale game installed in MEmu.

  Installation

   1. Clone the repository:
   1     git clone https://github.com/Parth-Manav/Evertale-Bot-Public.git
   2     cd Evertale-Bot-Public

   2. Install the required Python packages:
   1     pip install -r requirements.txt

  Configuration

  Before running the bot, you need to configure the path to your ADB executable.

   1. Open the core/game_actions.py file.
   2. Find the line ADB_PATH = r"A:\all folders\MEmu\Microvirt\MEmu\adb.exe"
   3. Change the path to match the location of the adb.exe file in your MEmu installation directory.    

  Usage

  To run the bot, simply execute the main.py script:

   1 python main.py

  The bot will then launch MEmu, start the Evertale game, and begin the automation tasks.

  Disclaimer

  This bot is for educational purposes only. The use of bots or other automation tools may be against
  the terms of service of the game. Use this bot at your own risk. The developers of this project are
  not responsible for any consequences that may arise from the use of this bot.



by hte way, this program is still under development
