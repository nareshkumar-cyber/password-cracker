
import argparse
import sys
import os
import io
import itertools
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import PyPDF2

class PDFPasswordCracker:
    
    def __init__(self, pdf_path):
        
        self.pdf_path = pdf_path
        self.pdf_data = None
        self.found_password = None
        self.stop_flag = False
        self.attempts = 0
        self.start_time = None
        
    def test_password(self, password):
        
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(self.pdf_data))
            # Try to decrypt with the password
            if pdf_reader.decrypt(password):
                return True
        except Exception:
            # Silently handle errors (wrong password, corrupted file, etc.)
            pass
        
        self.attempts += 1
        return False
    
    def dictionary_attack(self, wordlist_path, max_workers=8):
       
        if not os.path.exists(wordlist_path):
            raise FileNotFoundError(f"Wordlist file not found: {wordlist_path}")
        
        # Read all passwords from wordlist
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                passwords = [line.strip() for line in f if line.strip()]
        except Exception as e:
            raise Exception(f"Error reading wordlist: {e}")
        
        print(f"\n[*] Dictionary Attack Started")
        print(f"[*] Wordlist: {wordlist_path}")
        print(f"[*] Total passwords to try: {len(passwords):,}")
        print(f"[*] Threads: {max_workers}")
        print("-" * 50)
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all password tests
            future_to_password = {
                executor.submit(self.test_password, pwd): pwd 
                for pwd in passwords
            }
            
            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_password), 1):
                if self.stop_flag:
                    break
                    
                password = future_to_password[future]
                
                if future.result():
                    self.found_password = password
                    self.stop_flag = True
                    return password
                
                # Progress indicator (every 1000 attempts)
                if i % 1000 == 0:
                    elapsed = time.time() - self.start_time if self.start_time else 0
                    rate = self.attempts / elapsed if elapsed > 0 else 0
                    print(f"[*] Progress: {i}/{len(passwords)} ({i/len(passwords)*100:.1f}%) | "
                          f"Attempts: {self.attempts:,} | Rate: {rate:.1f} pwd/s", end='\r')
        
        return None
    
    def brute_force_attack(self, charset, min_length, max_length, max_workers=8):
        """
        Brute-force attack: Generate and try all possible password combinations
        
        Args:
            charset (str): Characters to use in password generation
            min_length (int): Minimum password length
            max_length (int): Maximum password length
            max_workers (int): Number of threads for parallel execution
            
        Returns:
            str: Found password or None
        """
        # Calculate total combinations
        total_combinations = sum(len(charset) ** length 
                                for length in range(min_length, max_length + 1))
        
        print(f"\n[*] Brute-Force Attack Started")
        print(f"[*] Character set: {charset}")
        print(f"[*] Character set size: {len(charset)}")
        print(f"[*] Length range: {min_length} to {max_length}")
        print(f"[*] Total combinations: {total_combinations:,}")
        print(f"[*] Threads: {max_workers}")
        print("-" * 50)
        
        # Use a single ThreadPoolExecutor for the entire brute-force process
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Try each length
            for length in range(min_length, max_length + 1):
                if self.stop_flag:
                    break
                    
                print(f"\n[*] Trying passwords of length {length}...")
                combinations_count = len(charset) ** length
                
                # Generate all combinations of current length
                password_generator = itertools.product(charset, repeat=length)
                
                # Process in batches for better performance
                batch_size = 1000
                batch = []
                
                for i, combo in enumerate(password_generator, 1):
                    if self.stop_flag:
                        break
                        
                    password = ''.join(combo)
                    batch.append(password)
                    
                    # Test batch when it reaches batch_size
                    if len(batch) >= batch_size:
                        # Test batch in parallel using the shared executor
                        futures = {executor.submit(self.test_password, pwd): pwd 
                                  for pwd in batch}
                        
                        for future in as_completed(futures):
                            if future.result():
                                self.found_password = futures[future]
                                self.stop_flag = True
                                return self.found_password
                        
                        batch = []
                        
                        # Progress update
                        if i % 10000 == 0:
                            elapsed = time.time() - self.start_time if self.start_time else 0
                            rate = self.attempts / elapsed if elapsed > 0 else 0
                            progress = (i / combinations_count) * 100
                            print(f"    Length {length}: {i:,}/{combinations_count:,} ({progress:.1f}%) | "
                                  f"Attempts: {self.attempts:,} | Rate: {rate:.1f} pwd/s", end='\r')
                
                # Test remaining passwords in the last batch
                if batch and not self.stop_flag:
                    futures = {executor.submit(self.test_password, pwd): pwd 
                              for pwd in batch}
                    
                    for future in as_completed(futures):
                        if future.result():
                            self.found_password = futures[future]
                            self.stop_flag = True
                            return self.found_password
        
        return None
    
    def crack(self, wordlist=None, charset=None, min_length=1, max_length=4, max_workers=8):
        """
        Main cracking method - chooses appropriate attack based on parameters
        
        Args:
            wordlist (str): Path to wordlist file for dictionary attack
            charset (str): Character set for brute-force attack
            min_length (int): Minimum password length (brute-force only)
            max_length (int): Maximum password length (brute-force only)
            max_workers (int): Number of threads
            
        Returns:
            tuple: (password, attempts, time_taken)
        """
        self.start_time = time.time()
        self.found_password = None
        self.stop_flag = False
        self.attempts = 0
        
        try:
            # Validate PDF file
            if not os.path.exists(self.pdf_path):
                raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
            
            # Read file data once into memory to prevent heavy I/O overhead in threads
            with open(self.pdf_path, 'rb') as f:
                self.pdf_data = f.read()
            
            # Test if PDF is actually encrypted
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(self.pdf_data))
            if not pdf_reader.is_encrypted:
                raise Exception("PDF file is not password protected!")
            
            # Choose attack method
            if wordlist:
                # Dictionary attack
                password = self.dictionary_attack(wordlist, max_workers)
            elif charset:
                # Brute-force attack
                password = self.brute_force_attack(charset, min_length, max_length, max_workers)
            else:
                raise ValueError("Either wordlist or charset must be provided")
            
            elapsed_time = time.time() - self.start_time
            return password, self.attempts, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - self.start_time
            raise Exception(f"Cracking failed: {e}")
    
    @staticmethod
    def validate_pdf(pdf_path):
        """
        Validate that the PDF file exists and is encrypted
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not os.path.exists(pdf_path):
            print(f"[!] Error: PDF file not found: {pdf_path}")
            return False
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                if not pdf_reader.is_encrypted:
                    print(f"[!] Error: PDF file is not password protected: {pdf_path}")
                    return False
            return True
        except Exception as e:
            print(f"[!] Error: Invalid or corrupted PDF file: {e}")
            return False


def main():
    """Main function with argument parsing and error handling"""
    
    parser = argparse.ArgumentParser(
        description='PDF Password Cracker - Educational Tool for Password Security',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dictionary attack with wordlist
  python pdf_cracker.py document.pdf -w wordlist.txt
  
  # Brute-force attack with custom settings
  python pdf_cracker.py document.pdf -b -c abc123 -l 3 -m 5
  
  # Dictionary attack with 4 threads
  python pdf_cracker.py document.pdf -w wordlist.txt -t 4
        """
    )
    
    # Required argument
    parser.add_argument('pdf_file', help='Path to password-protected PDF file')
    
    # Attack method arguments (mutually exclusive but not enforced here for flexibility)
    parser.add_argument('-w', '--wordlist', help='Path to wordlist file for dictionary attack')
    parser.add_argument('-b', '--bruteforce', action='store_true', 
                       help='Use brute-force attack (use with -c, -l, -m)')
    
    # Brute-force specific arguments
    parser.add_argument('-c', '--charset', default='abcdefghijklmnopqrstuvwxyz',
                       help='Character set for brute-force (default: lowercase letters)')
    parser.add_argument('-l', '--min-length', type=int, default=1,
                       help='Minimum password length for brute-force (default: 1)')
    parser.add_argument('-m', '--max-length', type=int, default=4,
                       help='Maximum password length for brute-force (default: 4)')
    
    # Performance arguments
    parser.add_argument('-t', '--threads', type=int, default=8,
                       help='Number of threads for parallel processing (default: 8)')
    
    # Output arguments
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Suppress progress output')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Error Handling: Check if required arguments are missing
    if not args.wordlist and not args.bruteforce:
        parser.error("Either --wordlist or --bruteforce must be specified")
    
    # Error Handling: Validate brute-force parameters
    if args.bruteforce:
        if args.min_length < 1:
            parser.error("Minimum length must be at least 1")
        if args.max_length < args.min_length:
            parser.error("Maximum length must be greater than or equal to minimum length")
        if args.max_length > 8:
            print("[!] Warning: Password length > 8 may take very long time")
    
    # Error Handling: Validate thread count
    if args.threads < 1 or args.threads > 32:
        parser.error("Thread count must be between 1 and 32")
    
    # Error Handling: Validate PDF file
    if not PDFPasswordCracker.validate_pdf(args.pdf_file):
        sys.exit(1)
    
    # Print banner
    print("=" * 60)
    print("PDF PASSWORD CRACKER - Educational Tool")
    print("=" * 60)
    print(f"Target PDF: {args.pdf_file}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create cracker instance
    cracker = PDFPasswordCracker(args.pdf_file)
    
    try:
        # Perform cracking based on arguments
        if args.wordlist:
            # Dictionary attack
            print(f"Attack type: Dictionary Attack")
            print(f"Wordlist: {args.wordlist}")
            password, attempts, elapsed = cracker.crack(
                wordlist=args.wordlist,
                max_workers=args.threads
            )
        else:
            # Brute-force attack
            print(f"Attack type: Brute-Force Attack")
            print(f"Character set: {args.charset}")
            print(f"Length range: {args.min_length}-{args.max_length}")
            password, attempts, elapsed = cracker.crack(
                charset=args.charset,
                min_length=args.min_length,
                max_length=args.max_length,
                max_workers=args.threads
            )
        
        # Display results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        if password:
            print(f"[+] SUCCESS! Password found: {password}")
            print(f"[+] Total attempts: {attempts:,}")
            print(f"[+] Time taken: {elapsed:.2f} seconds")
            print(f"[+] Average speed: {attempts/elapsed:.1f} passwords/second")
        else:
            print(f"[-] FAILED! Password not found")
            print(f"[-] Total attempts: {attempts:,}")
            print(f"[-] Time taken: {elapsed:.2f} seconds")
        
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n[!] Cracking interrupted by user")
        print(f"[!] Attempts made: {cracker.attempts:,}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()