#!/usr/bin/env python3
"""
DNS Defense Proxy - Consensus-based DNS Resolution
Runs on dedicated IP (10.0.0.70) port 53
Queries multiple servers and returns majority result to prevent cache poisoning
"""

import socket
import struct
import threading
import time
from collections import defaultdict

class DNSDefenseProxy:
    def __init__(self):
        """Initialize DNS Defense Proxy"""
        # Servers to query for consensus
        self.dns_servers = [
            '10.0.0.40',  # Proxy with delay (legitimate)
            '10.0.0.60',  # Auth DNS 2 (legitimate)  
            '10.0.0.50',  # Attacker (malicious)
        ]
        self.consensus_threshold = 2  # Need 2+ servers to agree
        self.response_cache = {}
        
    def create_dns_query(self, domain, query_type=1, query_id=0x1234):
        """Create a DNS query packet"""
        flags = 0x0100  # Standard query
        qdcount = 1
        ancount = 0
        nscount = 0
        arcount = 0
        
        header = struct.pack('!HHHHHH', query_id, flags, qdcount, ancount, nscount, arcount)
        
        # Question section
        question = b''
        for part in domain.split('.'):
            question += struct.pack('!B', len(part)) + part.encode()
        question += b'\x00'  # Null terminator
        question += struct.pack('!HH', query_type, 1)  # Type A, Class IN
        
        return header + question
    
    def parse_dns_response(self, response_data):
        """Parse DNS response and extract IP address"""
        if len(response_data) < 12:
            return None
            
        # Parse header
        header = struct.unpack('!HHHHHH', response_data[:12])
        ancount = header[3]
        
        if ancount == 0:
            return None
            
        # Skip question section
        offset = 12
        while offset < len(response_data) and response_data[offset] != 0:
            length = response_data[offset]
            offset += length + 1
        offset += 5  # Skip null terminator and type/class
        
        # Parse answer section
        for i in range(ancount):
            if offset + 10 > len(response_data):
                break
                
            # Skip name (compressed format)
            if response_data[offset] >= 0xC0:
                offset += 2
            else:
                while offset < len(response_data) and response_data[offset] != 0:
                    offset += response_data[offset] + 1
                offset += 1
                
            if offset + 10 > len(response_data):
                break
                
            # Parse record type, class, TTL, and data length
            rtype, rclass, ttl, rdlength = struct.unpack('!HHIH', response_data[offset:offset+10])
            offset += 10
            
            if rtype == 1 and rdlength == 4:  # A record (IPv4)
                ip = socket.inet_ntoa(response_data[offset:offset+4])
                return ip
            elif rtype == 28 and rdlength == 16:  # AAAA record (IPv6)
                # For now, we don't handle IPv6 consensus, return None
                # This allows the function to continue looking for A records
                pass
                
            offset += rdlength
            
        return None
    
    def query_dns_server(self, server_ip, domain, results, server_index):
        """Query a single DNS server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.5)  # 1.5 second timeout
            
            query = self.create_dns_query(domain)
            sock.sendto(query, (server_ip, 53))
            
            response, addr = sock.recvfrom(512)
            answer = self.parse_dns_response(response)
            
            if answer:
                results[server_index] = {
                    'server': server_ip,
                    'answer': answer,
                    'timestamp': time.time()
                }
                print(f"[DEFENSE] Server {server_ip} returned: {answer}")
            else:
                print(f"[DEFENSE] Server {server_ip} returned no answer")
                
        except Exception as e:
            print(f"[DEFENSE] Error querying {server_ip}: {e}")
        finally:
            sock.close()
    
    def resolve_with_consensus(self, domain):
        """
        Query multiple servers and return consensus result
        Only return result if consensus_threshold servers agree
        """
        print(f"[DEFENSE] Resolving {domain} with consensus validation...")
        
        # Check cache first
        if domain in self.response_cache:
            cached_result = self.response_cache[domain]
            if time.time() - cached_result['timestamp'] < 10:  # 10 second cache
                print(f"[DEFENSE] Returning cached result: {cached_result['answer']}")
                return cached_result['answer']
        
        # Query all DNS servers in parallel
        results = {}
        threads = []
        
        for i, server in enumerate(self.dns_servers):
            thread = threading.Thread(
                target=self.query_dns_server,
                args=(server, domain, results, i)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=2.0)
        
        # Analyze results for consensus
        answer_counts = defaultdict(list)
        for result in results.values():
            answer = result['answer']
            answer_counts[answer].append(result)
        
        print(f"[DEFENSE] Consensus analysis:")
        for answer, sources in answer_counts.items():
            server_list = [r['server'] for r in sources]
            print(f"  {answer}: {len(sources)} vote(s) from {server_list}")
        
        # Find consensus winner
        for answer, sources in answer_counts.items():
            if len(sources) >= self.consensus_threshold:
                print(f"[DEFENSE] ✅ CONSENSUS REACHED: {answer} ({len(sources)} votes >= {self.consensus_threshold} threshold)")
                # Cache the consensus result
                self.response_cache[domain] = {
                    'answer': answer,
                    'timestamp': time.time(),
                    'votes': len(sources)
                }
                return answer
        
        print(f"[DEFENSE] ❌ NO CONSENSUS: Attack detected! No answer met {self.consensus_threshold} vote threshold")
        return None

    def create_dns_response(self, query_data, ip_address, query_type=1):
        """Create DNS response packet"""
        # Copy query ID from original query
        query_id = struct.unpack('!H', query_data[:2])[0]
        
        # Parse the query type from the original query
        # Extract query type from question section
        offset = 12
        while offset < len(query_data) and query_data[offset] != 0:
            length = query_data[offset]
            offset += length + 1
        offset += 1  # Skip null terminator
        
        if offset + 4 <= len(query_data):
            qtype, qclass = struct.unpack('!HH', query_data[offset:offset+4])
        else:
            qtype = 1  # Default to A record
        
        # DNS header with response flag
        if qtype == 28:  # AAAA query but we don't have IPv6 answer
            # Return NXDOMAIN or no answer
            flags = 0x8183  # Response with NXDOMAIN
            ancount = 0
        else:
            flags = 0x8180  # Standard response, no error
            ancount = 1
            
        qdcount = 1
        nscount = 0
        arcount = 0
        
        header = struct.pack('!HHHHHH', query_id, flags, qdcount, ancount, nscount, arcount)
        
        # Copy question section from original query
        offset = 12
        question_end = offset
        while question_end < len(query_data) and query_data[question_end] != 0:
            length = query_data[question_end]
            question_end += length + 1
        question_end += 5  # Include null terminator and type/class
        
        question = query_data[12:question_end]
        
        # Answer section (only for A records)
        if qtype == 1 and ip_address:  # A record
            name_pointer = 0xC00C  # Pointer to name in question section
            answer = struct.pack('!H', name_pointer)  # Name pointer
            answer += struct.pack('!HH', 1, 1)       # Type A, Class IN
            answer += struct.pack('!I', 10)          # TTL (60 seconds - longer for BIND cache)
            answer += struct.pack('!H', 4)           # Data length
            answer += socket.inet_aton(ip_address)   # IP address
            return header + question + answer
        else:
            # AAAA query or no answer - return question only
            return header + question

    def start_defense_proxy(self):
        """Start the DNS defense proxy server on port 53"""
        print("[DEFENSE] Starting DNS Defense Proxy on 10.0.0.70:53...")
        print(f"[DEFENSE] Monitoring servers: {self.dns_servers}")
        print(f"[DEFENSE] Consensus threshold: {self.consensus_threshold} votes required")
        
        # Create UDP socket and bind to port 53
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(('0.0.0.0', 53))
        except OSError as e:
            print(f"[DEFENSE] Error: Port 53 already in use. {e}")
            return
        
        print("[DEFENSE] ✅ Defense proxy active - Ready to block attacks!")
        
        while True:
            try:
                data, addr = sock.recvfrom(512)
                print(f"[DEFENSE] DNS query received from {addr}")
                
                # Parse domain from query
                if len(data) > 12:
                    # Extract domain name and query type from DNS query
                    offset = 12
                    domain_parts = []
                    while offset < len(data) and data[offset] != 0:
                        length = data[offset]
                        if offset + length + 1 > len(data):
                            break
                        domain_parts.append(data[offset+1:offset+length+1].decode())
                        offset += length + 1
                    
                    # Get query type
                    query_type = 1  # Default A record
                    if offset + 4 <= len(data):
                        query_type = struct.unpack('!H', data[offset+1:offset+3])[0]
                    
                    if domain_parts:
                        domain = '.'.join(domain_parts)
                        print(f"[DEFENSE] Query for domain: {domain} (Type: {'A' if query_type == 1 else 'AAAA' if query_type == 28 else query_type})")
                        
                        if query_type == 1:  # A record - do consensus
                            # Get consensus result
                            consensus_ip = self.resolve_with_consensus(domain)
                            
                            if consensus_ip:
                                # Create and send response
                                response = self.create_dns_response(data, consensus_ip, query_type)
                                sock.sendto(response, addr)
                                print(f"[DEFENSE] ✅ Sent consensus response: {domain} -> {consensus_ip}")
                            else:
                                print(f"[DEFENSE] ❌ Blocked query for {domain} - no consensus reached")
                                # Don't send response to force fallback
                                
                        elif query_type == 28:  # AAAA record - return no answer
                            print(f"[DEFENSE] 📋 AAAA query for {domain} - returning no IPv6 answer")
                            response = self.create_dns_response(data, None, query_type)
                            sock.sendto(response, addr)
                            
                        else:  # Other query types - don't handle
                            print(f"[DEFENSE] ❓ Unsupported query type {query_type} for {domain}")
                            # Don't send response to force fallback
                            
            except KeyboardInterrupt:
                print(f"\n[DEFENSE] Defense proxy stopped by user")
                break
            except Exception as e:
                print(f"[DEFENSE] Error: {e}")
        
        sock.close()
        print("[DEFENSE] Defense proxy shutdown complete")

def main():
    """Main function to start DNS defense proxy"""
    proxy = DNSDefenseProxy()
    proxy.start_defense_proxy()

if __name__ == "__main__":
    main()
