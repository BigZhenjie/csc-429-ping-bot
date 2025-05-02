import socket
import asyncio
import hikari
import time
import aiohttp
import json

class ServerMonitor:
    def __init__(self, ip_address, ports_to_monitor=None, check_interval=60, port_services=None, 
                api_endpoint=None):
        """
        Initialize the ServerMonitor class.
        
        Args:
            ip_address (str): IP address to monitor
            ports_to_monitor (list): List of ports to monitor
            check_interval (int): How often to check ports in seconds
            port_services (dict): Dictionary mapping ports to service names
            api_endpoint (str): API endpoint to check
        """
        self.ip_address = ip_address
        self.ports_to_monitor = ports_to_monitor or [22, 80, 443]
        self.check_interval = check_interval
        self.port_services = port_services or {
            22: "SSH",
            80: "HTTP Website",
            443: "HTTPS Website",
        }
        self.port_states = {port: None for port in self.ports_to_monitor}
        self.api_endpoint = api_endpoint
        self.api_state = None
    
    async def check_port(self, port, timeout=2):
        """Check if a specific port is open"""
        try:
            return await asyncio.to_thread(self._check_socket, port, timeout)
        except Exception as e:
            print(f"Error checking port {port}: {e}")
            return False
    
    def _check_socket(self, port, timeout):
        """Helper function to perform socket connection"""
        try:
            # Use context manager to ensure socket is always closed properly
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_obj:
                socket_obj.settimeout(timeout)
                result = socket_obj.connect_ex((self.ip_address, port))
                return result == 0  # Return True if connection succeeded
        except socket.error as e:
            print(f"Socket error on {self.ip_address}:{port} - {e}")
            return False
        except Exception as e:
            print(f"Unexpected error checking {self.ip_address}:{port} - {e}")
            return False
    
    async def check_api_endpoint(self, timeout=5):
        """
        Check if the API endpoint is responding properly
        
        Args:
            timeout (int): Request timeout in seconds
            
        Returns:
            bool: True if API responds correctly, False otherwise
        """
        if not self.api_endpoint:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_endpoint, 
                    json={"name": "test"},
                    timeout=timeout
                ) as response:
                    # Check for successful status code (2xx)
                    if 200 <= response.status < 300:
                        try:
                            # Try to parse response as JSON
                            json_response = await response.json()
                            
                            # Verify the response contains the 'hash' field
                            if 'hash' in json_response:
                                return True
                            else:
                                print(f"API endpoint {self.api_endpoint} responded without required 'hash' field")
                                return False
                        except:
                            # Response wasn't valid JSON
                            print(f"API endpoint {self.api_endpoint} responded with non-JSON content")
                            return False
                    else:
                        print(f"API endpoint {self.api_endpoint} responded with status code {response.status}")
                        return False
        except asyncio.TimeoutError:
            print(f"API endpoint {self.api_endpoint} timed out after {timeout} seconds")
            return False
        except Exception as e:
            print(f"Error checking API endpoint {self.api_endpoint}: {e}")
            return False
    
    async def monitor_ports(self, bot, channel_id):
        """
        Continuously monitor ports and send alerts to the specified channel
        
        Args:
            bot: Hikari bot instance
            channel_id (int): Channel ID to send alerts to
        """
        print(f"Starting monitoring for {self.ip_address} on ports: {', '.join(map(str, self.ports_to_monitor))}")
        if self.api_endpoint:
            print(f"Also monitoring API endpoint: {self.api_endpoint}")
        
        while True:
            # Check all ports in parallel
            tasks = {port: self.check_port(port) for port in self.ports_to_monitor}
            
            # Add API endpoint check if configured
            api_task = None
            if self.api_endpoint:
                api_task = self.check_api_endpoint()
            
            # Wait for all checks to complete
            for port, task in tasks.items():
                service_name = self.port_services.get(port, f"Port {port}")
                try:
                    is_up = await task
                    
                    # First check - initialize state
                    if self.port_states[port] is None:
                        self.port_states[port] = is_up
                        print(f"{service_name} initial state: {'UP' if is_up else 'DOWN'}")
                        continue
                    
                    # Alert on state change from up to down
                    if self.port_states[port] and not is_up:
                        print(f"ALERT: {service_name} went DOWN!")
                        await bot.rest.create_message(
                            channel_id,
                            content=f"@everyone ⚠️ {service_name} on {self.ip_address} is DOWN!"
                        )
                        self.port_states[port] = False
                    
                    # Log recovery
                    elif not self.port_states[port] and is_up:
                        print(f"{service_name} recovered and is now UP")
                        await bot.rest.create_message(
                            channel_id,
                            content=f"{service_name} on {self.ip_address} is back online"
                        )
                        self.port_states[port] = True
                        
                except Exception as e:
                    print(f"Error in monitor task for {service_name}: {e}")
            
            # Check API endpoint if configured
            if api_task:
                try:
                    api_is_up = await api_task
                    
                    # First check - initialize state
                    if self.api_state is None:
                        self.api_state = api_is_up
                        print(f"API endpoint initial state: {'UP' if api_is_up else 'DOWN'}")
                    
                    # Alert on state change from up to down
                    elif self.api_state and not api_is_up:
                        print(f"ALERT: API endpoint went DOWN!")
                        await bot.rest.create_message(
                            channel_id,
                            content=f"@everyone ⚠️ API endpoint {self.api_endpoint} is DOWN!"
                        )
                        self.api_state = False
                    
                    # Log recovery
                    elif not self.api_state and api_is_up:
                        print(f"API endpoint recovered and is now UP")
                        await bot.rest.create_message(
                            channel_id,
                            content=f"API endpoint {self.api_endpoint} is back online"
                        )
                        self.api_state = True
                        
                except Exception as e:
                    print(f"Error in API endpoint monitoring: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def check_all_ports(self, timeout=1):
        """
        Check all monitored ports once and return results
        
        Args:
            timeout (int): Connection timeout in seconds
        
        Returns:
            dict: Dictionary with port status information
        """
        # Check all ports in parallel
        port_tasks = {}
        for port in self.ports_to_monitor:
            port_tasks[port] = asyncio.create_task(self.check_port(port, timeout=timeout))
        
        # Add API endpoint check if configured
        api_task = None
        if self.api_endpoint:
            api_task = asyncio.create_task(self.check_api_endpoint(timeout=timeout*2))
        
        # Wait for all checks to complete (with a reasonable total timeout)
        await asyncio.wait(list(port_tasks.values()), timeout=timeout * 2)
        
        # Wait for API check if applicable
        if api_task:
            try:
                await asyncio.wait([api_task], timeout=timeout * 2)
            except Exception as e:
                print(f"Error waiting for API task: {e}")
        
        # Map results back to their ports
        port_results = {}
        for port, task in port_tasks.items():
            try:
                if task.done():
                    port_results[port] = task.result()
                else:
                    # If task didn't complete in time, mark port as down
                    task.cancel()
                    port_results[port] = False
            except Exception:
                # Handle any exceptions during task execution
                port_results[port] = False
        
        # Get API result if applicable
        api_result = False
        if api_task:
            try:
                if api_task.done():
                    api_result = api_task.result()
                else:
                    api_task.cancel()
            except Exception:
                api_result = False
        
        up_ports = sum(1 for status in port_results.values() if status)
        down_ports = sum(1 for status in port_results.values() if not status)
        
        status_messages = []
        for port in self.ports_to_monitor:
            service_name = self.port_services.get(port, f"Port {port}")
            is_up = port_results.get(port, False)
            
            status = "✅ UP" if is_up else "❌ DOWN"
            status_messages.append(f"{service_name}: {status}")
        
        # Add API status if applicable
        if self.api_endpoint:
            api_status = "✅ UP" if api_result else "❌ DOWN"
            status_messages.append(f"API Endpoint: {api_status}")
            if not api_result:
                down_ports += 1
            else:
                up_ports += 1
        
        # Create a summary header
        total_services = len(self.ports_to_monitor) + (1 if self.api_endpoint else 0)
        if down_ports == 0:
            header = f"🟢 All services on {self.ip_address} are operational"
        elif down_ports == total_services:
            header = f"🔴 All services on {self.ip_address} are down!"
        else:
            header = f"🟡 {down_ports}/{total_services} services on {self.ip_address} are down"
        
        # Return complete result
        return {
            "header": header,
            "status_messages": status_messages,
            "up_ports": up_ports,
            "down_ports": down_ports,
            "port_results": port_results,
            "api_result": api_result if self.api_endpoint else None
        }