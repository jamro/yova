"""
ZeroMQ-based event broker for YOVA system
"""

import asyncio
import json
import logging
import platform
from typing import Dict, Set, Any
import zmq
import zmq.asyncio

logger = logging.getLogger(__name__)


class YovaBroker:
    """ZeroMQ-based event broker that routes messages between publishers and subscribers"""
    
    def __init__(self, frontend_port: int = 5555, backend_port: int = 5556):
        self.frontend_port = frontend_port
        self.backend_port = backend_port
        self.context = zmq.asyncio.Context()
        self.frontend = None
        self.backend = None
        self.subscribers: Dict[str, Set[str]] = {}  # topic -> set of subscriber addresses
        self.running = False
    
    def _get_port_check_instructions(self, port: int) -> str:
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
    
    async def start(self):
        """Start the broker service"""
        logger.info("Starting YOVA Broker...")
        
        try:
            # Frontend socket for publishers
            self.frontend = self.context.socket(zmq.XSUB)
            self.frontend.bind(f"tcp://*:{self.frontend_port}")
            logger.info(f"Frontend bound to port {self.frontend_port}")
        except zmq.error.ZMQError as e:
            if "Address already in use" in str(e):
                logger.error(f"Frontend port {self.frontend_port} is already in use!")
                logger.error(self._get_port_check_instructions(self.frontend_port))
                logger.error("Please either:")
                logger.error(f"  1. Stop the process using port {self.frontend_port}")
                logger.error(f"  2. Use a different port by modifying the YovaBroker constructor")
                raise
            else:
                raise
        
        try:
            # Backend socket for subscribers
            self.backend = self.context.socket(zmq.XPUB)
            self.backend.bind(f"tcp://*:{self.backend_port}")
            logger.info(f"Backend bound to port {self.backend_port}")
        except zmq.error.ZMQError as e:
            if "Address already in use" in str(e):
                logger.error(f"Backend port {self.backend_port} is already in use!")
                logger.error(self._get_port_check_instructions(self.backend_port))
                logger.error("Please either:")
                logger.error(f"  1. Stop the process using port {self.backend_port}")
                logger.error(f"  2. Use a different port by modifying the YovaBroker constructor")
                raise
            else:
                raise
        
        self.running = True
        logger.info("YOVA Broker started successfully")
        
        # Start the proxy
        await self._run_proxy()
    
    async def _run_proxy(self):
        """Run the ZeroMQ proxy to forward messages between frontend and backend"""
        try:
            await zmq.proxy(self.frontend, self.backend)
        except Exception as e:
            if self.running:
                logger.error(f"Proxy error: {e}")
                raise
    
    async def stop(self):
        """Stop the broker service"""
        logger.info("Stopping YOVA Broker...")
        self.running = False
        
        if self.frontend:
            self.frontend.close()
        if self.backend:
            self.backend.close()
        if self.context:
            self.context.term()
        
        logger.info("YOVA Broker stopped")


async def main():
    """Main entry point for the broker"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    broker = YovaBroker()
    
    try:
        await broker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Broker error: {e}")
    finally:
        await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
