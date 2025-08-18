#!/usr/bin/env python3
"""
YOVA Development Supervisor
Monitors file changes and automatically restarts supervisor processes
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from typing import Set, List, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SupervisorDev:
    def __init__(self, config_file: str = "configs/supervisord.conf"):
        self.config_file = config_file
        self.project_root = Path(__file__).parent.parent
        self.config_path = self.project_root / config_file
        self.supervisor_pid_file = "/tmp/supervisord.pid"
        self.running = False
        self.watched_paths = self._get_watched_paths()
        self.last_restart = 0
        self.restart_cooldown = 2  # seconds
        self.log_streaming_active = False
        self.log_streaming_thread = None
        
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _get_watched_paths(self) -> Set[Path]:
        """Get paths to monitor for changes"""
        paths = set()
        
        # Core source directories
        core_dirs = ['yova_core', 'tests']
        for dir_name in core_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                paths.add(dir_path)
        
        # Configuration files
        config_dir = self.project_root / 'configs'
        if config_dir.exists():
            paths.add(config_dir)
        
        # Python files in root
        for py_file in self.project_root.glob('*.py'):
            paths.add(py_file)
        
        # pyproject.toml
        pyproject = self.project_root / 'pyproject.toml'
        if pyproject.exists():
            paths.add(pyproject)
        
        return paths
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.stop_supervisor()
        sys.exit(0)
    
    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run a command and return the result"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, -1, "", "Command timed out")
        except Exception as e:
            logger.error(f"Error running command {' '.join(cmd)}: {e}")
            return subprocess.CompletedProcess(cmd, -1, "", str(e))
    
    def is_supervisor_running(self) -> bool:
        """Check if supervisor is running"""
        if not os.path.exists(self.supervisor_pid_file):
            return False
        
        try:
            with open(self.supervisor_pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ValueError, OSError, FileNotFoundError):
            return False
    
    def start_supervisor(self) -> bool:
        """Start supervisor"""
        if self.is_supervisor_running():
            logger.info("Supervisor is already running")
            return True
        
        logger.info("Starting supervisor...")
        cmd = ["poetry", "run", "supervisord", "-c", self.config_file]
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            # Wait a bit for supervisor to start
            time.sleep(3)
            if self.is_supervisor_running():
                logger.info("Supervisor started successfully")
                return True
            else:
                logger.error("Supervisor failed to start")
                return False
        else:
            logger.error(f"Failed to start supervisor: {result.stderr}")
            return False
    
    def stop_supervisor(self) -> bool:
        """Stop supervisor"""
        if not self.is_supervisor_running():
            logger.info("Supervisor is not running")
            return True
        
        logger.info("Stopping supervisor...")
        cmd = ["poetry", "run", "supervisorctl", "-c", self.config_file, "shutdown"]
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            # Wait for supervisor to stop
            time.sleep(3)
            if not self.is_supervisor_running():
                logger.info("Supervisor stopped successfully")
                return True
            else:
                logger.warning("Supervisor may still be running")
                return False
        else:
            logger.error(f"Failed to stop supervisor: {result.stderr}")
            return False
    
    def restart_supervisor(self) -> bool:
        """Restart supervisor"""
        current_time = time.time()
        if current_time - self.last_restart < self.restart_cooldown:
            logger.info("Skipping restart due to cooldown")
            return False
        
        logger.info("Restarting supervisor...")
        self.stop_supervisor()
        time.sleep(1)
        success = self.start_supervisor()
        if success:
            self.last_restart = current_time
            # Wait for processes to start after restart
            time.sleep(3)
            # Signal that log streaming should be restarted
            self.log_streaming_active = False
        return success
    
    def get_supervisor_status(self) -> str:
        """Get status of all supervisor processes"""
        if not self.is_supervisor_running():
            return "Supervisor is not running"
        
        cmd = ["poetry", "run", "supervisorctl", "-c", self.config_file, "status"]
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error getting status: {result.stderr}"
    
    def restart_log_streaming(self):
        """Restart log streaming after supervisor restart"""
        if self.log_streaming_thread and self.log_streaming_thread.is_alive():
            logger.info("Stopping existing log streaming...")
            self.log_streaming_active = False
            self.log_streaming_thread.join(timeout=5)
        
        logger.info("Restarting log streaming...")
        self.log_streaming_active = True
        self.log_streaming_thread = threading.Thread(target=self.stream_logs, daemon=True)
        self.log_streaming_thread.start()
    
    def stream_logs(self):
        """Stream logs from all supervisor processes"""
        if not self.is_supervisor_running():
            logger.error("Supervisor is not running")
            return
        
        logger.info("Starting log stream from all processes...")
        
        # Check if we should continue streaming
        if not self.log_streaming_active:
            logger.info("Log streaming stopped")
            return
        
        # Get list of all programs
        cmd = ["poetry", "run", "supervisorctl", "-c", self.config_file, "status"]
        result = self._run_command(cmd)
        
        if result.returncode != 0:
            logger.error(f"Failed to get program status: {result.stderr}")
            return
        
        # Parse program names from status output
        programs = []
        for line in result.stdout.split('\n'):
            if line.strip():
                # Split by whitespace and take the first part as program name
                parts = line.split()
                if parts and parts[0] and parts[0] != 'supervisor':
                    programs.append(parts[0])
        
        if not programs:
            logger.warning("No programs found to monitor")
            return
        
        logger.info(f"Monitoring logs for programs: {', '.join(programs)}")
        
        # Start log streaming for each program
        threads = []
        for program in programs:
            thread = threading.Thread(
                target=self._stream_program_logs,
                args=(program,),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        # Keep main thread alive
        try:
            while self.running and self.log_streaming_active:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Log streaming interrupted")
    
    def _stream_program_logs(self, program_name: str):
        """Stream logs for a specific program"""
        cmd = ["poetry", "run", "supervisorctl", "-c", self.config_file, "tail", "-f", program_name]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            logger.info(f"Started log stream for {program_name}")
            
            # Stream stdout
            for line in iter(process.stdout.readline, ''):
                if not self.running:
                    break
                if line.strip():
                    print(f"[{program_name}] {line.rstrip()}")
            
            process.terminate()
            process.wait()
            
        except Exception as e:
            logger.error(f"Error streaming logs for {program_name}: {e}")
    
    def monitor_files(self):
        """Monitor files for changes and restart supervisor when needed"""
        logger.info("Starting file monitoring...")
        logger.info(f"Watching paths: {[str(p) for p in self.watched_paths]}")
        
        # Get initial file states
        file_states = {}
        for path in self.watched_paths:
            if path.is_file():
                file_states[path] = path.stat().st_mtime
            elif path.is_dir():
                for py_file in path.rglob('*.py'):
                    file_states[py_file] = py_file.stat().st_mtime
                for config_file in path.rglob('*.conf'):
                    file_states[config_file] = config_file.stat().st_mtime
                for toml_file in path.rglob('*.toml'):
                    file_states[toml_file] = toml_file.stat().st_mtime
        
        while self.running:
            time.sleep(1)
            
            # Check for changes
            for path in list(file_states.keys()):
                if not path.exists():
                    continue
                
                try:
                    current_mtime = path.stat().st_mtime
                    if current_mtime > file_states[path]:
                        logger.info(f"File changed: {path}")
                        file_states[path] = current_mtime
                        
                        # Restart supervisor
                        if self.restart_supervisor():
                            logger.info("Supervisor restarted due to file changes")
                        else:
                            logger.warning("Failed to restart supervisor")
                        
                        # Update file states for new files
                        for new_path in self.watched_paths:
                            if new_path.is_file() and new_path not in file_states:
                                file_states[new_path] = new_path.stat().st_mtime
                            elif new_path.is_dir():
                                for py_file in new_path.rglob('*.py'):
                                    if py_file not in file_states:
                                        file_states[py_file] = py_file.stat().st_mtime
                        
                        break
                        
                except OSError:
                    continue
    
    def run(self):
        """Main run method"""
        logger.info("Starting YOVA Development Supervisor")
        
        # Start supervisor
        if not self.start_supervisor():
            logger.error("Failed to start supervisor, exiting")
            return
        
        # Wait a bit more for processes to fully start
        logger.info("Waiting for processes to start...")
        time.sleep(5)
        
        # Show initial status
        print("\n" + "="*50)
        print("SUPERVISOR STATUS")
        print("="*50)
        print(self.get_supervisor_status())
        print("="*50 + "\n")
        
        self.running = True
        self.log_streaming_active = True
        
        # Start file monitoring in background thread
        monitor_thread = threading.Thread(target=self.monitor_files, daemon=True)
        monitor_thread.start()
        
        # Start log streaming in background thread
        self.log_streaming_thread = threading.Thread(target=self.stream_logs, daemon=True)
        self.log_streaming_thread.start()
        
        # Main loop to monitor and restart log streaming when needed
        try:
            while self.running:
                time.sleep(1)
                
                # Check if log streaming needs to be restarted
                if not self.log_streaming_active and self.is_supervisor_running():
                    logger.info("Detected supervisor restart, restarting log streaming...")
                    self.restart_log_streaming()
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.running = False
            self.log_streaming_active = False
            logger.info("Shutting down development supervisor")


def main():
    """Main entry point"""
    config_file = "configs/supervisord.conf"
    
    # Check if config file exists
    if not os.path.exists(config_file):
        print(f"Error: Config file {config_file} not found")
        print("Make sure you're running this from the project root directory")
        sys.exit(1)
    
    # Check if poetry is available
    try:
        subprocess.run(["poetry", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Poetry is not available")
        print("Please install Poetry or activate the virtual environment")
        sys.exit(1)
    
    # Create and run supervisor dev
    supervisor_dev = SupervisorDev(config_file)
    supervisor_dev.run()


if __name__ == "__main__":
    main()
