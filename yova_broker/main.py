"""
Main entry point for YOVA Broker service
"""

import asyncio
import logging
import sys
import platform
from .broker import YovaBroker


def get_port_check_instructions(port: int) -> str:
    """Get instructions for checking which process is using a port based on OS"""
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        return f"""Port {port} is busy. To check which process is using it on macOS:
  lsof -i :{port}
  netstat -an | grep :{port}
  sudo lsof -i :{port}  # for more detailed info"""
    
    elif system == "windows":
        return f"""Port {port} is busy. To check which process is using it on Windows:
  netstat -ano | findstr :{port}
  Get-NetTCPConnection -LocalPort {port}  # PowerShell
  netstat -anob | findstr :{port}  # Shows process name (requires admin)"""
    
    else:  # Linux (including Raspberry Pi)
        return f"""Port {port} is busy. To check which process is using it on Linux/Raspberry Pi:
  lsof -i :{port}
  netstat -tulpn | grep :{port}
  ss -tulpn | grep :{port}
  sudo lsof -i :{port}  # for more detailed info"""


def run():
    """Run the YOVA Broker service"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    broker = YovaBroker()
    
    try:
        asyncio.run(broker.start())
    except KeyboardInterrupt:
        logging.info("Received interrupt signal")
    except Exception as e:
        logging.error(f"Broker error: {e}")
        
        # Check if it's a port binding error
        if "Address already in use" in str(e):
            logging.error("\n" + "="*60)
            logging.error("PORT BINDING ERROR DETECTED")
            logging.error("="*60)
            
            # Check both ports
            for port in [broker.frontend_port, broker.backend_port]:
                logging.error(f"\nInstructions for port {port}:")
                logging.error(get_port_check_instructions(port))
            
            logging.error("\n" + "="*60)
            logging.error("SOLUTIONS:")
            logging.error("1. Stop the process using the busy port(s)")
            logging.error("2. Use different ports by modifying the YovaBroker constructor")
            logging.error("3. Wait for the port to become available")
            logging.error("="*60)
        
        sys.exit(1)
    finally:
        asyncio.run(broker.stop())


if __name__ == "__main__":
    run()
