import subprocess
import time
import os
import psutil
import logging
from typing import Optional

# Configure logging with UTF-8 encoding
import sys

# Configure file handler with UTF-8 encoding
file_handler = logging.FileHandler('evertale_launcher.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Configure console handler with UTF-8 encoding
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

class EvertaleLauncher:
    def __init__(self):
        # Configuration
        self.memu_path = r"A:\all folders\MEmu\Microvirt\MEmu\MEmu.exe"
        self.memu_console_path = r"A:\all folders\MEmu\Microvirt\MEmu\memuc.exe"
        self.memu_instance = "MEmu"
        self.memu_index = "0"
        self.evertale_package = "com.zigzagame.evertale"
        self.adb_path = r"A:\all folders\MEmu\Microvirt\MEmu\adb.exe"
        self.boot_timeout = 120
        self.check_interval = 5
        self.launch_timeout = 45  # Time to wait for app to actually start
    
    def kill_existing_memu_processes(self) -> bool:
        """Kill any existing MEmu processes"""
        try:
            killed_any = False
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name'].lower()
                    if proc_name in ['memu.exe', 'memuheadless.exe', 'memuhyperv.exe']:
                        logger.info(f"Killing existing MEmu process: {proc.info['name']} (PID: {proc.info['pid']})")
                        proc.kill()
                        killed_any = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed_any:
                logger.info("Waiting for processes to terminate...")
                time.sleep(3)
            
            return True
        except Exception as e:
            logger.error(f"Error killing MEmu processes: {e}")
            return False
    
    def is_memu_instance_running(self) -> bool:
        """Check if the specific MEmu instance is running and responsive"""
        try:
            result = subprocess.run([self.adb_path, "devices"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:
                    if line.strip() and 'device' in line:
                        logger.info("Found active MEmu instance via ADB")
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"ADB check failed: {e}")
            return False
    
    def list_memu_instances(self) -> list:
        """List available MEmu instances"""
        try:
            if os.path.exists(self.memu_console_path):
                result = subprocess.run([self.memu_console_path, "listvms"], 
                                      capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    logger.info(f"Available MEmu instances:\n{result.stdout}")
                    return result.stdout.strip().split('\n')
                else:
                    logger.warning(f"Failed to list instances: {result.stderr}")
            return []
        except Exception as e:
            logger.error(f"Error listing MEmu instances: {e}")
            return []
    
    def close_ads_and_dialogs(self) -> bool:
        """Close MEmu ads and any popup dialogs"""
        try:
            logger.info("Attempting to close ads and popup dialogs...")
            
            # Wait a moment for UI to stabilize
            time.sleep(3)
            
            # Try multiple methods to close potential ads/popups
            close_commands = [
                # Press back button multiple times to close ads
                [self.adb_path, "shell", "input", "keyevent", "4"],  # BACK
                [self.adb_path, "shell", "input", "keyevent", "4"],  # BACK again
                # Try to tap common "close" or "X" button locations (top-right corner)
                [self.adb_path, "shell", "input", "tap", "950", "100"],  # Top right
                [self.adb_path, "shell", "input", "tap", "900", "150"],  # Alt position
                # Press home to get to home screen
                [self.adb_path, "shell", "input", "keyevent", "3"],   # HOME
            ]
            
            for cmd in close_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    time.sleep(1)  # Small delay between commands
                    logger.debug(f"Executed: {' '.join(cmd[2:])}")
                except Exception as e:
                    logger.debug(f"Command failed: {e}")
                    continue
            
            logger.info("Ad closing sequence completed")
            return True
            
        except Exception as e:
            logger.warning(f"Error closing ads: {e}")
            return False
    
    def start_memu(self) -> bool:
        """Start MEmu emulator"""
        try:
            if self.is_memu_instance_running():
                logger.info("MEmu instance is already running and responsive")
                return True
            
            logger.info("Cleaning up any existing MEmu processes...")
            self.kill_existing_memu_processes()
            
            if not os.path.exists(self.memu_path):
                logger.error(f"MEmu executable not found at: {self.memu_path}")
                return False
            
            logger.info("Checking available MEmu instances...")
            instances = self.list_memu_instances()
            
            if os.path.exists(self.memu_console_path):
                logger.info(f"Starting MEmu instance '{self.memu_instance}' (index {self.memu_index}) using memuc...")
                cmd = [self.memu_console_path, "start", "-i", self.memu_index]
                logger.info(f"Executing command: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    logger.info("MEmu instance started successfully via memuc")
                    time.sleep(5)
                    return True
                else:
                    logger.warning(f"memuc start failed: {result.stderr}")
                    logger.info("Falling back to direct MEmu.exe launch...")
            
            logger.info("Starting MEmu using direct executable...")
            cmd = [self.memu_path]
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            process = subprocess.Popen(cmd, 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            
            logger.info(f"MEmu startup command sent (PID: {process.pid})")
            time.sleep(5)
            
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"MEmu process exited immediately with code {process.returncode}")
                if stdout:
                    logger.error(f"STDOUT: {stdout.decode()}")
                if stderr:
                    logger.error(f"STDERR: {stderr.decode()}")
                return False
            
            logger.info("MEmu process started successfully, waiting for boot...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MEmu: {e}")
            return False
    
    def check_adb_connection(self) -> bool:
        """Check if ADB can connect to any device"""
        try:
            result = subprocess.run([self.adb_path, "devices"], 
                                  capture_output=True, text=True, timeout=15)
            
            logger.info(f"ADB devices output: {result.stdout.strip()}")
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:
                    if line.strip() and ('device' in line or 'emulator' in line):
                        logger.info(f"Found device: {line.strip()}")
                        return True
            
            logger.warning("No devices found via ADB")
            return False
            
        except Exception as e:
            logger.error(f"ADB connection check failed: {e}")
            return False
    
    def wait_for_boot(self) -> bool:
        """Wait for MEmu to fully boot"""
        logger.info("Waiting for MEmu to boot completely...")
        start_time = time.time()
        adb_connected = False
        
        while time.time() - start_time < self.boot_timeout:
            elapsed = int(time.time() - start_time)
            
            try:
                if not adb_connected:
                    if self.check_adb_connection():
                        adb_connected = True
                        logger.info("ADB connection established!")
                    else:
                        logger.info(f"Waiting for ADB connection... ({elapsed}s/{self.boot_timeout}s)")
                        time.sleep(self.check_interval)
                        continue
                
                boot_result = subprocess.run([self.adb_path, "shell", "getprop", "sys.boot_completed"], 
                                           capture_output=True, text=True, timeout=10)
                
                if boot_result.returncode == 0 and "1" in boot_result.stdout.strip():
                    logger.info("MEmu has booted successfully!")
                    # Wait a bit more for UI to be ready
                    time.sleep(5)
                    
                    # Close any ads that might have appeared
                    self.close_ads_and_dialogs()
                    
                    return True
                else:
                    logger.info(f"Boot in progress... ({elapsed}s/{self.boot_timeout}s)")
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"ADB command timed out at {elapsed}s, MEmu might still be booting...")
            except Exception as e:
                logger.debug(f"Boot check failed (normal during boot): {e}")
            
            time.sleep(self.check_interval)
        
        logger.error(f"MEmu failed to boot within {self.boot_timeout} seconds")
        self.diagnose_boot_failure()
        return False
    
    def diagnose_boot_failure(self):
        """Provide diagnostic information when boot fails"""
        logger.info("Running boot failure diagnostics...")
        
        memu_running = False
        for proc in psutil.process_iter(['pid', 'name']):
            if 'memu' in proc.info['name'].lower():
                memu_running = True
                logger.info(f"MEmu process found: {proc.info['name']} (PID: {proc.info['pid']})")
        
        if not memu_running:
            logger.error("MEmu process is not running - it may have crashed during startup")
        
        try:
            result = subprocess.run([self.adb_path, "devices"], 
                                  capture_output=True, text=True, timeout=10)
            logger.info(f"Final ADB check: {result.stdout.strip()}")
        except Exception as e:
            logger.error(f"Final ADB check failed: {e}")
        
        logger.info("Possible solutions:")
        logger.info("1. Try increasing boot_timeout in the script")
        logger.info(f"2. Check if MEmu instance '{self.memu_instance}' (index {self.memu_index}) exists in MEmu Multi-MEmu")
        logger.info("3. Try starting MEmu manually first to check for issues")
        logger.info("4. Check if virtualization is enabled in BIOS")
    
    def is_evertale_installed(self) -> bool:
        """Check if Evertale is installed"""
        try:
            result = subprocess.run([self.adb_path, "shell", "pm", "list", "packages", self.evertale_package], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and self.evertale_package in result.stdout:
                logger.info("Evertale is installed")
                return True
            else:
                logger.error("Evertale is not installed on this MEmu instance")
                return False
                
        except Exception as e:
            logger.error(f"Error checking if Evertale is installed: {e}")
            return False
    
    def get_evertale_main_activity(self) -> Optional[list[str]]:
        """Get the main activity name for Evertale"""
        try:
            # Try to get the main activity from package info
            cmd = [self.adb_path, "shell", "dumpsys", "package", self.evertale_package]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'android.intent.action.MAIN' in line:
                        # Look for activity name in the line or nearby lines
                        activity_line = line.strip()
                        logger.debug(f"Found MAIN intent line: {activity_line}")
                        
                # Common Unity activity names to try
                common_activities = [
                    "com.unity3d.player.UnityPlayerActivity",
                    "com.unity3d.player.UnityPlayerNativeActivity", 
                    f"{self.evertale_package}.UnityPlayerActivity",
                    f"{self.evertale_package}.MainActivity",
                    f"{self.evertale_package}.SplashActivity"
                ]
                
                return common_activities
                
        except Exception as e:
            logger.debug(f"Error getting main activity: {e}")
            
        return None
    
    def is_evertale_running(self) -> bool:
        """Check if Evertale is currently running"""
        try:
            # Check running processes
            result = subprocess.run([self.adb_path, "shell", "ps", "|", "grep", self.evertale_package], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and self.evertale_package in result.stdout:
                logger.info("Evertale process is running")
                return True
                
            # Alternative method: check current activity
            activity_result = subprocess.run([self.adb_path, "shell", "dumpsys", "activity", "activities", "|", "grep", "mFocusedApp"], 
                                           capture_output=True, text=True, timeout=10)
            
            if activity_result.returncode == 0 and self.evertale_package in activity_result.stdout:
                logger.info("Evertale is the focused app")
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"Error checking if Evertale is running: {e}")
            return False
    
    def launch_evertale(self) -> bool:
        """Launch Evertale game with enhanced verification"""
        try:
            if not self.is_evertale_installed():
                return False
            
            logger.info("Launching Evertale...")
            
            # First, ensure we're on the home screen
            subprocess.run([self.adb_path, "shell", "input", "keyevent", "3"], 
                         capture_output=True, text=True, timeout=10)
            time.sleep(2)
            
            # Method 1: Try launching with monkey (most reliable for games)
            logger.info("Attempting launch with monkey command...")
            monkey_cmd = [self.adb_path, "shell", "monkey", "-p", self.evertale_package, "-c", 
                         "android.intent.category.LAUNCHER", "1"]
            
            result = subprocess.run(monkey_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("Monkey launch command executed successfully")
                
                # Wait and verify the app actually started
                logger.info("Waiting for Evertale to start...")
                for i in range(self.launch_timeout):
                    if self.is_evertale_running():
                        logger.info(f"SUCCESS: Evertale confirmed running after {i+1} seconds!")
                        return True
                    time.sleep(1)
                    
                logger.warning("Monkey launch succeeded but app doesn't appear to be running")
            
            # Method 2: Try with am start and specific activities
            logger.info("Trying alternative launch methods...")
            activities = self.get_evertale_main_activity()
            
            if activities:
                for activity in activities:
                    logger.info(f"Trying activity: {activity}")
                    
                    am_cmd = [self.adb_path, "shell", "am", "start", "-n", 
                             f"{self.evertale_package}/{activity}"]
                    
                    result = subprocess.run(am_cmd, capture_output=True, text=True, timeout=20)
                    
                    if result.returncode == 0:
                        logger.info(f"Launch command succeeded for {activity}")
                        
                        # Verify it actually started
                        for i in range(15):  # Wait up to 15 seconds
                            if self.is_evertale_running():
                                logger.info(f"SUCCESS: Evertale confirmed running with {activity}!")
                                return True
                            time.sleep(1)
                    else:
                        logger.debug(f"Activity {activity} failed: {result.stderr}")
            
            # Method 3: Launch via intent
            logger.info("Trying intent-based launch...")
            intent_cmd = [self.adb_path, "shell", "am", "start", 
                         "-a", "android.intent.action.MAIN",
                         "-c", "android.intent.category.LAUNCHER",
                         self.evertale_package]
            
            result = subprocess.run(intent_cmd, capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0:
                logger.info("Intent launch command executed")
                
                for i in range(15):
                    if self.is_evertale_running():
                        logger.info(f"SUCCESS: Evertale confirmed running via intent after {i+1} seconds!")
                        return True
                    time.sleep(1)
            
            # If all methods failed, provide diagnostics
            logger.error("All launch methods failed. Running diagnostics...")
            self.diagnose_launch_failure()
            return False
                        
        except subprocess.TimeoutExpired:
            logger.error("Evertale launch command timed out")
            return False
        except Exception as e:
            logger.error(f"Error launching Evertale: {e}")
            return False
    
    def diagnose_launch_failure(self):
        """Diagnose why Evertale failed to launch"""
        logger.info("Running launch failure diagnostics...")
        
        try:
            # Check if package exists and is enabled
            pkg_info = subprocess.run([self.adb_path, "shell", "pm", "dump", self.evertale_package], 
                                    capture_output=True, text=True, timeout=15)
            
            if pkg_info.returncode != 0:
                logger.error("Package dump failed - app might not be properly installed")
            else:
                # Look for enabled state
                if "enabled=true" in pkg_info.stdout.lower():
                    logger.info("App is enabled")
                else:
                    logger.warning("App might be disabled")
            
            # Check recent logs for errors
            logger.info("Checking recent system logs for errors...")
            logcat_cmd = [self.adb_path, "shell", "logcat", "-d", "-s", "ActivityManager", "|", "tail", "-20"]
            log_result = subprocess.run(logcat_cmd, capture_output=True, text=True, timeout=10)
            
            if log_result.returncode == 0 and log_result.stdout.strip():
                logger.info(f"Recent ActivityManager logs:\n{log_result.stdout}")
            
        except Exception as e:
            logger.error(f"Diagnostic failed: {e}")
        
        logger.info("Possible solutions:")
        logger.info("1. Try launching Evertale manually to check if it works")
        logger.info("2. Check if Evertale needs to be updated")
        logger.info("3. Clear Evertale's cache/data and try again")
        logger.info("4. Reinstall Evertale if the issue persists")
    
    def run(self) -> bool:
        """Main execution flow"""
        logger.info("=" * 50)
        logger.info("Starting Enhanced Evertale Launcher")
        logger.info("=" * 50)
        
        # Step 1: Start MEmu
        if not self.start_memu():
            logger.error("Failed to start MEmu")
            return False
        
        # Step 2: Wait for boot
        if not self.wait_for_boot():
            logger.error("MEmu failed to boot properly")
            return False
        
        # Step 3: Launch Evertale with verification
        if not self.launch_evertale():
            logger.error("Failed to launch Evertale")
            return False
        
        logger.info("=" * 50)
        logger.info("SUCCESS: Evertale is now running on MEmu!")
        logger.info("=" * 50)
        return True

def main():
    launcher = EvertaleLauncher()
    success = launcher.run()
    
    if success:
        print("\n[SUCCESS] Evertale is now running on MEmu!")
        print("Check your MEmu window to see the game.")
    else:
        print("\n[FAILED] Could not launch Evertale. Check the logs above for details.")
        print("Try running MEmu manually first to see if there are any issues.")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
