
import socket
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# Color codes for formatted output (optional, for better visualization)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

# Common port-service mapping
COMMON_SERVICES = {
    20: "FTP-data", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 111: "RPC", 135: "RPC",
    139: "NetBIOS", 143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS",
    995: "POP3S", 1723: "PPTP", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB"
}

def get_service_name(port: int) -> str:
    return COMMON_SERVICES.get(port, "Unknown")

def get_banner(sock: socket.socket, port: int, timeout: float = 2) -> str:
    try:
        sock.settimeout(timeout)
        
        probes = {
            80: b"HEAD / HTTP/1.1\r\nHost: localhost\r\n\r\n",
            443: b"HEAD / HTTP/1.1\r\nHost: localhost\r\n\r\n",
            21: b"HELP\r\n",
            22: b"SSH-2.0-ClientTest\r\n",
            25: b"EHLO test\r\n",
            110: b"CAPA\r\n",
            143: b"A001 CAPABILITY\r\n",
        }
        
        if port in probes:
            sock.send(probes[port])
        
        banner = sock.recv(256).decode('utf-8', errors='ignore').strip()
        return banner[:100] + "..." if len(banner) > 100 else banner
        
    except (socket.timeout, socket.error, UnicodeDecodeError):
        return "No banner captured"
    except Exception:
        return "Banner retrieval failed"

def scan_port(target_ip: str, port: int, timeout: float = 1.0, 
              grab_banner: bool = True) -> Dict:
    result = {
        'port': port,
        'open': False,
        'service': None,
        'banner': None,
        'error': None
    }
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        connection_result = sock.connect_ex((target_ip, port))
        
        if connection_result == 0:
            result['open'] = True
            result['service'] = get_service_name(port)
            
            if grab_banner:
                result['banner'] = get_banner(sock, port)
        
        sock.close()
        
    except socket.gaierror:
        result['error'] = "Hostname resolution error"
    except socket.error as e:
        result['error'] = str(e)
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
    
    return result

def validate_ip(ip: str) -> bool:
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False

def parse_port_range(port_range: str) -> Tuple[int, int]:
    try:
        if '-' in port_range:
            start, end = map(int, port_range.split('-'))
            if start < 1 or end > 65535 or start > end:
                raise ValueError
            return start, end
        elif ',' in port_range:
            return -1, -1
        else:
            port = int(port_range)
            if 1 <= port <= 65535:
                return port, port
            raise ValueError
    except ValueError:
        print(f"{Colors.RED}Invalid port range format. Using default (1-1024){Colors.END}")
        return 1, 1024

def scan_ports_multithreaded(target_ip: str, start_port: int, end_port: int,
                              max_workers: int = 100, grab_banner: bool = True) -> List[Dict]:

    results = []
    ports_to_scan = range(start_port, end_port + 1)
    total_ports = end_port - start_port + 1
    
    print(f"{Colors.BLUE}[*] Scanning {target_ip} for ports {start_port}-{end_port}{Colors.END}")
    print(f"[*] Total ports to scan: {total_ports}")
    print(f"[*] Using {max_workers} concurrent threads")
    print(f"[*] Banner grabbing: {'Enabled' if grab_banner else 'Disabled'}")
    print("-" * 60)
    
    scanned = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_port = {
            executor.submit(scan_port, target_ip, port, 1.0, grab_banner): port 
            for port in ports_to_scan
        }
        
        for future in as_completed(future_to_port):
            port = future_to_port[future]
            scanned += 1
            
            if scanned % 100 == 0 or scanned == total_ports:
                progress = (scanned / total_ports) * 100
                print(f"\r[*] Progress: {scanned}/{total_ports} ({progress:.1f}%)", 
                      end="", flush=True)
            
            try:
                result = future.result()
                if result['open']:
                    results.append(result)
            except Exception as e:
                print(f"\n{Colors.RED}Error scanning port {port}: {e}{Colors.END}")
    
    print()
    return results

def display_results(results: List[Dict]) -> None:
    if not results:
        print(f"\n{Colors.YELLOW}No open ports found.{Colors.END}")
        return
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}=== SCAN RESULTS ==={Colors.END}")
    print(f"{Colors.BOLD}{'Port':<8} {'Service':<20} {'Banner':<40}{Colors.END}")
    print("-" * 70)
    
    for result in sorted(results, key=lambda x: x['port']):
        port_str = f"{Colors.GREEN}{result['port']}{Colors.END}"
        service = result['service'] or "Unknown"
        banner = result['banner'] or "No banner"
        
        if len(banner) > 40:
            banner = banner[:37] + "..."
        
        print(f"{port_str:<8} {service:<20} {banner:<40}")
    
    print("-" * 70)
    print(f"{Colors.BOLD}Total open ports: {len(results)}{Colors.END}")

def save_results(results: List[Dict], target_ip: str, filename: str = None) -> None:
    if not filename:
        filename = f"scan_{target_ip.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        with open(filename, 'w') as f:
            f.write(f"Port Scan Results for {target_ip}\n")
            f.write(f"Scan completed at: {datetime.now()}\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'Port':<8} {'Service':<20} {'Banner':<40}\n")
            f.write("-" * 60 + "\n")
            
            for result in sorted(results, key=lambda x: x['port']):
                f.write(f"{result['port']:<8} {result['service']:<20} {result['banner']:<40}\n")
            
            f.write("-" * 60 + "\n")
            f.write(f"Total open ports: {len(results)}\n")
        
        print(f"\n{Colors.GREEN}[✓] Results saved to: {filename}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}[✗] Failed to save results: {e}{Colors.END}")

def print_banner() -> None:
    banner = f"""
{Colors.BLUE}{'='*50}
    Port Scanner Using Python
    By Inlighn Tech
    Ethical Hacking & Network Security Tool
{'='*50}{Colors.END}
"""
    print(banner)

def main() -> None:
    print_banner()
    
    parser = argparse.ArgumentParser(description="Multi-threaded Port Scanner")
    parser.add_argument("-t", "--target", help="Target IP address or hostname")
    parser.add_argument("-p", "--ports", default="1-1024", 
                        help="Port range (e.g., 80, 1-100, 20,25,80)")
    parser.add_argument("-w", "--workers", type=int, default=100, 
                        help="Number of worker threads (default: 100)")
    parser.add_argument("--no-banner", action="store_true", 
                        help="Disable banner grabbing")
    parser.add_argument("-o", "--output", help="Output file for results")
    parser.add_argument("--quick", action="store_true", 
                        help="Quick scan (common ports only)")
    
    args = parser.parse_args()
    
    target_ip = args.target
    if not target_ip:
        target_ip = input(f"{Colors.YELLOW}Enter target IP address or hostname: {Colors.END}").strip()
    
    try:
        target_ip = socket.gethostbyname(target_ip)
        print(f"{Colors.GREEN}[✓] Resolved target to: {target_ip}{Colors.END}")
    except socket.gaierror:
        print(f"{Colors.RED}[✗] Invalid hostname or IP address: {target_ip}{Colors.END}")
        sys.exit(1)
    
    if args.quick:
        ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 
                 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 6379, 8080, 8443]
        start_port = min(ports)
        end_port = max(ports)
        print(f"{Colors.BLUE}[*] Quick scan mode: Scanning {len(ports)} common ports{Colors.END}")
    else:
        start_port, end_port = parse_port_range(args.ports)
        if start_port == -1:
            ports_list = [int(p.strip()) for p in args.ports.split(',')]
            start_port = min(ports_list)
            end_port = max(ports_list)

    print(f"\n{Colors.YELLOW}Target: {target_ip}")
    print(f"Port Range: {start_port}-{end_port}")
    print(f"Concurrent Threads: {args.workers}")
    confirm = input(f"Start scan? (y/n): {Colors.END}").lower()
    
    if confirm != 'y':
        print("Scan cancelled.")
        sys.exit(0)
    
    start_time = datetime.now()
    
    results = scan_ports_multithreaded(
        target_ip, 
        start_port, 
        end_port, 
        max_workers=args.workers,
        grab_banner=not args.no_banner
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    display_results(results)
    
    print(f"\n{Colors.BLUE}[*] Scan completed in {duration:.2f} seconds{Colors.END}")
    if args.output or results:
        save_results(results, target_ip, args.output)
    
    # Security warning
    print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  LEGAL DISCLAIMER ⚠️{Colors.END}")
    print(f"{Colors.YELLOW}This tool is for educational and authorized testing purposes only.")
    print("Only scan systems you own or have explicit permission to test.{Colors.END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}\n[!] Scan interrupted by user.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}\n[!] Unexpected error: {e}{Colors.END}")
        sys.exit(1)