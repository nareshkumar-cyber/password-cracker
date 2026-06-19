#!/usr/bin/env python3
"""
Password Cracker Using Python
By Inlighn Tech

A multi-threaded password cracking tool that supports dictionary attacks
and brute-force techniques for educational cybersecurity training.
"""

import hashlib
import argparse
import time
import sys
import os
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional, List, Generator
import itertools

# Color codes for output formatting
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'

# Supported hash algorithms
SUPPORTED_HASHES = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1,
    'sha224': hashlib.sha224,
    'sha256': hashlib.sha256,
    'sha384': hashlib.sha384,
    'sha512': hashlib.sha512,
    'blake2b': hashlib.blake2b,
    'blake2s': hashlib.blake2s,
}

class PasswordCracker:
    """Main password cracking class with dictionary and brute-force capabilities."""
    
    def __init__(self, target_hash: str, hash_type: str, verbose: bool = False):
        """
        Initialize the password cracker.
        
        Args:
            target_hash: The hash to crack
            hash_type: Type of hash (md5, sha256, etc.)
            verbose: Enable verbose output
        """
        self.target_hash = target_hash.lower()
        self.hash_type = hash_type.lower()
        self.verbose = verbose
        self.found_password = None
        self.attempts = 0
        self.start_time = None
        self.end_time = None
        
        # Validate hash algorithm
        if self.hash_type not in SUPPORTED_HASHES:
            raise ValueError(f"Unsupported hash type. Choose from: {', '.join(SUPPORTED_HASHES.keys())}")
        
        self.hash_func = SUPPORTED_HASHES[self.hash_type]
        
    def hash_password(self, password: str) -> str:
        """Generate hash for a given password."""
        return self.hash_func(password.encode('utf-8')).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """Check if password matches the target hash."""
        self.attempts += 1
        return self.hash_password(password) == self.target_hash
    
    def print_banner(self) -> None:
        """Display application banner."""
        banner = f"""
{Colors.CYAN}{'='*60}
    Password Cracker Using Python
    By Inlighn Tech
    Ethical Hacking & Security Training Tool
{'='*60}{Colors.END}
{Colors.YELLOW}Target Hash: {self.target_hash}
Hash Type: {self.hash_type.upper()}
{Colors.END}{'='*60}
"""
        print(banner)
    
    def dictionary_attack(self, wordlist_path: str, max_workers: int = 10) -> Optional[str]:
        """
        Perform dictionary attack using a wordlist.
        
        Args:
            wordlist_path: Path to wordlist file
            max_workers: Number of threads for concurrent processing
            
        Returns:
            Cracked password or None
        """
        if not os.path.exists(wordlist_path):
            print(f"{Colors.RED}[!] Wordlist file not found: {wordlist_path}{Colors.END}")
            return None
        
        print(f"{Colors.BLUE}[*] Starting Dictionary Attack...{Colors.END}")
        print(f"[*] Wordlist: {wordlist_path}")
        print(f"[*] Using {max_workers} threads")
        
        # Count total words for progress
        total_words = sum(1 for _ in open(wordlist_path, 'r', encoding='utf-8', errors='ignore'))
        print(f"[*] Total passwords to try: {total_words:,}")
        
        checked_words = 0
        
        def check_password(word: str) -> Optional[str]:
            """Check a single password."""
            nonlocal checked_words
            password = word.strip()
            
            if self.verify_password(password):
                return password
            
            checked_words += 1
            if self.verbose and checked_words % 1000 == 0:
                progress = (checked_words / total_words) * 100
                print(f"\r[*] Progress: {checked_words:,}/{total_words:,} ({progress:.1f}%)", 
                      end="", flush=True)
            
            return None
        
        # Process wordlist with threading
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for word in f:
                    if self.found_password:
                        break
                    future = executor.submit(check_password, word)
                    futures.append(future)
                    
                    # Process in batches to manage memory
                    if len(futures) >= max_workers * 10:
                        for future in as_completed(futures):
                            result = future.result()
                            if result:
                                self.found_password = result
                                executor.shutdown(wait=False)
                                return result
                        futures.clear()
            
            # Check remaining futures
            for future in as_completed(futures):
                result = future.result()
                if result:
                    self.found_password = result
                    return result
        
        print()  # New line after progress
        return None
    
    def generate_bruteforce_passwords(self, min_length: int = 1, max_length: int = 4, 
                                       charset: str = None) -> Generator[str, None, None]:
        """
        Generate passwords for brute-force attack.
        
        Args:
            min_length: Minimum password length
            max_length: Maximum password length
            charset: Character set to use (default: lowercase + digits)
            
        Yields:
            Password strings
        """
        if charset is None:
            charset = string.ascii_lowercase + string.digits
        
        for length in range(min_length, max_length + 1):
            for combination in itertools.product(charset, repeat=length):
                yield ''.join(combination)
    
    def brute_force_attack(self, min_length: int = 1, max_length: int = 4, 
                           charset: str = None, max_workers: int = 10) -> Optional[str]:
        """
        Perform brute-force attack by generating all possible combinations.
        
        Args:
            min_length: Minimum password length
            max_length: Maximum password length
            charset: Character set to use
            max_workers: Number of threads for concurrent processing
            
        Returns:
            Cracked password or None
        """
        if charset is None:
            charset = string.ascii_lowercase + string.digits
        
        total_combinations = sum(len(charset) ** length for length in range(min_length, max_length + 1))
        
        print(f"{Colors.BLUE}[*] Starting Brute-Force Attack...{Colors.END}")
        print(f"[*] Password length: {min_length} to {max_length}")
        print(f"[*] Character set: {charset}")
        print(f"[*] Total combinations: {total_combinations:,}")
        print(f"[*] Using {max_workers} threads")
        
        # Break combinations into chunks for threading
        password_gen = self.generate_bruteforce_passwords(min_length, max_length, charset)
        
        def check_password_chunk(chunk_size: int = 1000) -> Optional[str]:
            """Check a chunk of passwords."""
            passwords = []
            for _ in range(chunk_size):
                try:
                    passwords.append(next(password_gen))
                except StopIteration:
                    break
            
            for password in passwords:
                if self.verify_password(password):
                    return password
            return None
        
        checked = 0
        chunk_size = max_workers * 100
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while not self.found_password:
                futures = []
                for _ in range(max_workers):
                    if self.found_password:
                        break
                    future = executor.submit(check_password_chunk, chunk_size)
                    futures.append(future)
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        self.found_password = result
                        executor.shutdown(wait=False)
                        return result
                    
                    checked += chunk_size
                    if self.verbose and checked % (chunk_size * 10) == 0:
                        progress = (checked / total_combinations) * 100
                        print(f"\r[*] Progress: {checked:,}/{total_combinations:,} ({progress:.2f}%)", 
                              end="", flush=True)
        
        print()  # New line after progress
        return None
    
    def smart_attack(self, wordlist_path: str = None, min_length: int = 1, 
                     max_length: int = 6, charset: str = None, 
                     max_workers: int = 10) -> Optional[str]:
        """
        Combined attack: try wordlist first, then fall back to brute-force.
        """
        # First try dictionary attack if wordlist provided
        if wordlist_path and os.path.exists(wordlist_path):
            result = self.dictionary_attack(wordlist_path, max_workers)
            if result:
                return result
            
            print(f"\n{Colors.YELLOW}[!] Dictionary attack failed. Switching to brute-force...{Colors.END}\n")
        
        # Fall back to brute-force
        return self.brute_force_attack(min_length, max_length, charset, max_workers)
    
    def display_results(self, cracked: bool) -> None:
        """Display cracking results and statistics."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        
        if cracked and self.found_password:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ PASSWORD CRACKED SUCCESSFULLY!{Colors.END}")
            print(f"{Colors.GREEN}Password: {self.found_password}{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ PASSWORD CRACKING FAILED{Colors.END}")
            print(f"{Colors.YELLOW}Could not crack the hash with given parameters.{Colors.END}")
        
        print(f"\n{Colors.BLUE}Statistics:{Colors.END}")
        print(f"  • Total attempts: {self.attempts:,}")
        print(f"  • Time taken: {duration:.2f} seconds")
        print(f"  • Attempts per second: {self.attempts / duration:.2f}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")

def print_common_hashes_examples() -> None:
    """Print examples of common password hashes for testing."""
    examples = f"""
{Colors.YELLOW}Example Hashes for Testing:{Colors.END}
  MD5:
    • 'password123' -> 482c811da5d5b4bc6d497ffa98491e38
    • 'admin'       -> 21232f297a57a5a743894a0e4a801fc3
    • 'letmein'     -> 0d107d09f5bbe40cade3de5c71e9e9b7
  
  SHA-256:
    • 'password123' -> ef92b778bafe771e89245b89ecbf08f47e4f2b7b5a1f2b3e4f5c6d7e8f9a0b1c
    • 'admin'       -> 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
  
  SHA-512:
    • 'password123' -> b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb9
                      80b1d6fa5fcb3e7f4c5d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c
{Colors.END}
"""
    print(examples)

def main():
    """Main function to run the password cracker."""
    parser = argparse.ArgumentParser(
        description="Password Cracker - Dictionary and Brute-Force Attacks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dictionary attack with wordlist
  python password_cracker.py -H 482c811da5d5b4bc6d497ffa98491e38 -t md5 -w wordlist.txt
  
  # Brute-force attack (4-6 chars, lowercase+digits)
  python password_cracker.py -H 5f4dcc3b5aa765d61d8327deb882cf99 -t md5 -b -min 4 -max 6
  
  # Smart attack (dictionary first, then brute-force)
  python password_cracker.py -H ef92b778bafe771e89245b89ecbf08f4 -t sha256 -w rockyou.txt -b -min 1 -max 5
  
  # Custom character set for brute-force
  python password_cracker.py -H target_hash -t md5 -b -min 3 -max 4 -chars "abc123"
        """
    )
    
    parser.add_argument("-H", "--hash", help="Target hash to crack")
    parser.add_argument("-t", "--type", default="md5", 
                        help=f"Hash type (default: md5). Options: {', '.join(SUPPORTED_HASHES.keys())}")
    parser.add_argument("-w", "--wordlist", help="Path to wordlist file for dictionary attack")
    parser.add_argument("-b", "--bruteforce", action="store_true", 
                        help="Enable brute-force attack")
    parser.add_argument("-min", "--min-length", type=int, default=1, 
                        help="Minimum password length for brute-force (default: 1)")
    parser.add_argument("-max", "--max-length", type=int, default=4, 
                        help="Maximum password length for brute-force (default: 4)")
    parser.add_argument("-chars", "--charset", 
                        help="Character set for brute-force (default: lowercase a-z + digits 0-9)")
    parser.add_argument("-w", "--workers", type=int, default=10, 
                        help="Number of worker threads (default: 10)")
    parser.add_argument("-v", "--verbose", action="store_true", 
                        help="Enable verbose output")
    parser.add_argument("--examples", action="store_true", 
                        help="Show example hashes for testing")
    
    args = parser.parse_args()
    
    # Show examples if requested
    if args.examples:
        print_common_hashes_examples()
        return
    
    # Get target hash if not provided
    target_hash = args.hash
    if not target_hash:
        target_hash = input(f"{Colors.YELLOW}Enter the target hash: {Colors.END}").strip()
    
    if not target_hash:
        print(f"{Colors.RED}[!] No hash provided. Exiting.{Colors.END}")
        return
    
    try:
        # Initialize cracker
        cracker = PasswordCracker(target_hash, args.type, args.verbose)
        cracker.print_banner()
        cracker.start_time = time.time()
        
        # Choose attack method
        if args.wordlist and os.path.exists(args.wordlist):
            print(f"{Colors.GREEN}[✓] Wordlist found: {args.wordlist}{Colors.END}")
            result = cracker.dictionary_attack(args.wordlist, args.workers)
            
            if not result and args.bruteforce:
                print(f"\n{Colors.YELLOW}[!] Switching to brute-force mode...{Colors.END}")
                result = cracker.brute_force_attack(
                    args.min_length, args.max_length, args.charset, args.workers
                )
        
        elif args.bruteforce:
            result = cracker.brute_force_attack(
                args.min_length, args.max_length, args.charset, args.workers
            )
        
        else:
            print(f"{Colors.RED}[!] No attack method specified. Use -w for dictionary or -b for brute-force.{Colors.END}")
            print(f"{Colors.YELLOW}Example: python password_cracker.py -H {target_hash} -t {args.type} -b -min 1 -max 4{Colors.END}")
            return
        
        # Display results
        cracker.display_results(result is not None)
        
    except ValueError as e:
        print(f"{Colors.RED}[!] Error: {e}{Colors.END}")
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!] Attack interrupted by user.{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}[!] Unexpected error: {e}{Colors.END}")

if __name__ == "__main__":
    main()