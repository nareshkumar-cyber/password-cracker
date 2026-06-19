import os
import queue
import threading
import urllib.request
import urllib.error

# A robust list of common subdomains for web/API infrastructure scanning
DEFAULT_SUBDOMAINS = [
    "www", "mail", "ftp", "localhost", "webmail", "smtp", "admin", "portal",
    "db", "mariadb", "mysql", "postgresql", "cpanel", "whm", "autodiscover",
    "api", "dev", "staging", "test", "demo", "secure", "shop", "wiki",
    "blog", "forum", "vpn", "dns", "ns1", "ns2", "cloud", "status", "files",
    "docs", "support", "help", "billing", "client"
]

def load_subdomains(filepath):
    """
    Loads potential subdomains from subdomains.txt.
    If the file does not exist, it creates it using DEFAULT_SUBDOMAINS.
    """
    if not os.path.exists(filepath):
        print(f"'{filepath}' not found. Generating default list of common subdomains...")
        with open(filepath, 'w') as f:
            for sub in DEFAULT_SUBDOMAINS:
                f.write(f"{sub}\n")
    
    subdomains = []
    with open(filepath, 'r') as f:
        for line in f:
            sub = line.strip().lower()
            # Ignore empty lines or comment lines starting with #
            if sub and not sub.startswith('#'):
                subdomains.append(sub)
    return subdomains

def check_subdomain(subdomain, domain, output_file, lock):
    """
    Attempts to establish an HTTP connection to the subdomain.
    If it succeeds (or receives a standard web server response like 403 or 404),
    it is recorded as active and written to output_file using lock synchronization.
    """
    url = f"http://{subdomain}.{domain}"
    
    # Use urllib.request to avoid external library dependencies (like requests)
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SubdomainScanner/1.0'},
        method='HEAD'  # HEAD request is much faster than GET as it retrieves headers only
    )
    
    try:
        # A timeout prevents threads from hanging indefinitely on inactive subdomains
        with urllib.request.urlopen(req, timeout=3) as response:
            status = response.status
    except urllib.error.HTTPError as e:
        # An HTTPError (e.g. 403, 404, 500) indicates the server is active and responded
        status = e.code
    except urllib.error.URLError:
        # URLError (e.g. Host not found, connection refused) means it is inactive
        return False
    except Exception:
        # Catch other network anomalies, but treat them as inactive for safety
        return False
        
    # If we reached this point, the subdomain is active!
    with lock:
        print(f"[+] Reachable: {url} (HTTP Status: {status})")
        with open(output_file, 'a') as f:
            f.write(f"{subdomain}.{domain}\n")
    return True

def worker(subdomain_queue, domain, output_file, lock):
    """
    Worker thread logic: continuously pulls subdomains from queue and checks them.
    """
    while not subdomain_queue.empty():
        try:
            subdomain = subdomain_queue.get_nowait()
        except queue.Empty:
            break
            
        check_subdomain(subdomain, domain, output_file, lock)
        subdomain_queue.task_done()

def main():
    print("=========================================")
    print("   MULTITHREADED SUBDOMAIN SCANNER       ")
    print("=========================================")
    
    domain = input("Enter the main domain name (e.g., example.com): ").strip()
    if not domain:
        print("Error: Main domain name cannot be empty.")
        return
        
    # Clean the domain input in case the user entered http(s):// prefix or trailing slashes
    if "://" in domain:
        domain = domain.split("://")[-1]
    domain = domain.split("/")[0].split(":")[0]
    
    input_file = "subdomains.txt"
    output_file = "discovered_subdomains.txt"
    
    # 1. Input Handling
    subdomains = load_subdomains(input_file)
    print(f"Loaded {len(subdomains)} potential subdomains from '{input_file}'.")
    
    # Clear previous results to avoid appending to stale data
    if os.path.exists(output_file):
        os.remove(output_file)
        
    # Thread-safe queue
    subdomain_queue = queue.Queue()
    for sub in subdomains:
        subdomain_queue.put(sub)
        
    # 6. Thread Synchronization Lock
    lock = threading.Lock()
    
    # 2. Threading for Efficiency
    # Limit maximum threads to number of subdomains or a reasonable default (e.g., 20)
    num_threads = min(20, len(subdomains))
    threads = []
    
    print(f"Scanning '{domain}' using {num_threads} threads...")
    print("-----------------------------------------")
    
    for _ in range(num_threads):
        t = threading.Thread(target=worker, args=(subdomain_queue, domain, output_file, lock))
        t.start()
        threads.append(t)
        
    # Wait for all threads to complete
    for t in threads:
        t.join()
        
    print("-----------------------------------------")
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            count = len(f.readlines())
        print(f"Scan complete. Discovered {count} active subdomains.")
        print(f"Results saved to '{output_file}'.")
    else:
        print("Scan complete. No active subdomains were found.")

if __name__ == "__main__":
    main()
