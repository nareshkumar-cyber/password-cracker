import ipaddress
import socket
import threading
from queue import Queue

# Try to import scapy with error handling
try:
    from scapy.all import ARP, Ether, srp
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("[-] Scapy not installed. Install it using: pip install scapy")
    exit(1)

results = []
print_lock = threading.Lock()

def get_hostname(ip):
    """Resolve hostname from IP address"""
    try:
        hostname = socket.gethostbyaddr(str(ip))[0]
        return hostname
    except:
        return "Unknown"

def scan_ip(ip):
    """Scan a single IP address using ARP request"""
    try:
        # Create ARP request packet
        arp_request = ARP(pdst=str(ip))
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp_request
        
        # Send packet and receive response (timeout=1 second)
        result = srp(packet, timeout=1, verbose=False)[0]
        
        if result:
            for sent, received in result:
                hostname = get_hostname(received.psrc)
                with print_lock:
                    results.append({
                        'ip': received.psrc,
                        'mac': received.hwsrc,
                        'hostname': hostname
                    })
                    print(f"{received.psrc:<18} {received.hwsrc:<18} {hostname:<18}")
    except Exception as e:
        pass  # Silently ignore errors for individual IPs

def worker(queue):
    """Worker thread function"""
    while not queue.empty():
        try:
            ip = queue.get()
            scan_ip(ip)
            queue.task_done()
        except:
            queue.task_done()

def network_scanner(network_cidr):
    """Main scanner function"""
    try:
        # Generate all IPs in the network
        network = ipaddress.ip_network(network_cidr, strict=False)
        ip_list = list(network.hosts())
        
        print(f"\n[*] Scanning {network_cidr} ({len(ip_list)} hosts)...")
        print("[*] This may take a moment...\n")
        print("{:<18} {:<18} {:<18}".format("IP Address", "MAC Address", "Hostname"))
        print("-" * 56)
        
        # Create queue and add all IPs
        q = Queue()
        for ip in ip_list:
            q.put(ip)
        
        # Create and start threads
        threads = []
        num_threads = min(30, len(ip_list))  # Max 30 threads to avoid errors
        
        for _ in range(num_threads):
            t = threading.Thread(target=worker, args=(q,))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Wait for all threads to complete
        q.join()
        
        # Summary
        print("-" * 56)
        print(f"\n[+] Scan complete! Found {len(results)} active device(s).")
        
    except ValueError as e:
        print(f"[-] Invalid network format: {e}")
    except Exception as e:
        print(f"[-] Error: {e}")

# Main execution
if __name__ == "__main__":
    print("\n" + "="*50)
    print("    NETWORK SCANNER TOOL")
    print("="*50)
    
    # Get user input
    network = input("\nEnter network (CIDR format like 192.168.1.0/24): ")
    
    if network.strip():
        network_scanner(network)
    else:
        print("[-] Please enter a valid network address")