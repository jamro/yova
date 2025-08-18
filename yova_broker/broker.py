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
    
    def get_port_check_instructions(self, port: int) -> str:
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
                logger.error(self.get_port_check_instructions(self.frontend_port))
                logger.error("Please either:")
                logger.error(f"  1. Stop the process using port {self.frontend_port}")
                logger.error(f"  2. Use a different port by modifying the YovaBroker constructor")
                raise
            else:
                logger.error(f"Frontend socket error: {e}")
                raise
        
        try:
            # Backend socket for subscribers
            self.backend = self.context.socket(zmq.XPUB)
            self.backend.bind(f"tcp://*:{self.backend_port}")
            logger.info(f"Backend bound to port {self.backend_port}")
        except zmq.error.ZMQError as e:
            # Clean up frontend if backend fails
            if self.frontend:
                self.frontend.close()
                self.frontend = None
            
            if "Address already in use" in str(e):
                logger.error(f"Backend port {self.backend_port} is already in use!")
                logger.error(self.get_port_check_instructions(self.backend_port))
                logger.error("Please either:")
                logger.error(f"  1. Stop the process using port {self.backend_port}")
                logger.error(f"  2. Use a different port by modifying the YovaBroker constructor")
                raise
            else:
                logger.error(f"Backend socket error: {e}")
                raise
        
        self.running = True
        logger.info("YOVA Broker started successfully")
        
        # Start the proxy in a separate task to avoid blocking
        self._proxy_task = asyncio.create_task(self._run_proxy())
        
        # Wait for proxy to be fully ready
        await asyncio.sleep(0.5)
        logger.info("Broker proxy is ready and accepting connections")
    
    async def wait_for_proxy(self):
        """Wait for the proxy to complete (useful for keeping the broker running)"""
        if hasattr(self, '_proxy_task') and self._proxy_task:
            await self._proxy_task
    
    async def _run_proxy(self):
        """Run the ZeroMQ proxy to forward messages between frontend and backend"""
        try:
            # Run zmq.proxy in a separate thread since it's blocking
            await asyncio.to_thread(zmq.proxy, self.frontend, self.backend)
        except Exception as e:
            if self.running:
                logger.error(f"Proxy error: {e}")
                # Don't re-raise here, let the calling method handle it
            else:
                logger.info("Proxy stopped due to shutdown request")
    
    def is_healthy(self) -> bool:
        """Check if the broker is in a healthy state"""
        return (
            self.running and 
            self.frontend is not None and 
            self.backend is not None and 
            self.context is not None
        )
    
    def is_ready_for_connections(self) -> bool:
        """Check if the broker is ready to accept connections"""
        if not self.is_healthy():
            return False
        
        # Check if proxy task is running
        if not hasattr(self, '_proxy_task') or not self._proxy_task:
            return False
            
        # Check if proxy task is not done
        if self._proxy_task.done():
            return False
            
        return True
    
    async def graceful_shutdown(self):
        """Gracefully shutdown the broker"""
        logger.info("Initiating graceful shutdown...")
        self.running = False
        
        # Give some time for the proxy to stop naturally
        await asyncio.sleep(0.1)
        
        await self.stop()
    
    async def stop(self):
        """Stop the broker service"""
        logger.info("Stopping YOVA Broker...")
        self.running = False
        
        # Cancel the proxy task if it exists
        if hasattr(self, '_proxy_task') and self._proxy_task:
            self._proxy_task.cancel()
            try:
                await self._proxy_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling
            except Exception as e:
                logger.warning(f"Error cancelling proxy task: {e}")
        
        try:
            if self.frontend:
                self.frontend.close()
                self.frontend = None
                logger.debug("Frontend socket closed")
        except Exception as e:
            logger.warning(f"Error closing frontend socket: {e}")
        
        try:
            if self.backend:
                self.backend.close()
                self.backend = None
                logger.debug("Backend socket closed")
        except Exception as e:
            logger.warning(f"Error closing backend socket: {e}")
        
        try:
            if self.context:
                self.context.term()
                self.context = None
                logger.debug("ZMQ context terminated")
        except Exception as e:
            logger.warning(f"Error terminating ZMQ context: {e}")
        
        logger.info("YOVA Broker stopped")
