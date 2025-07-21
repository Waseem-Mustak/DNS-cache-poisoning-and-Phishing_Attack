#!/usr/bin/env python3
import socket
import time
import threading
import sys

# Force unbuffered output
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

def forward_dns_query(data, client_addr, server_socket):
    """Forward DNS query to auth server with delay"""
    try:
        # Add 500ms delay before forwarding
        print(f"[DELAY] Adding 500ms delay for query from {client_addr[0]}:{client_addr[1]}", flush=True)
        time.sleep(0.5)  # 500ms delay
        
        # Forward to auth server (10.0.0.30:53)
        auth_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        auth_socket.settimeout(5.0)
        
        print(f"[FORWARD] Forwarding query to auth server 10.0.0.30:53", flush=True)
        auth_socket.sendto(data, ('10.0.0.30', 53))
        
        # Get response from auth server
        response, _ = auth_socket.recvfrom(512)
        auth_socket.close()
        
        print(f"[RESPONSE] Sending response back to {client_addr[0]}:{client_addr[1]}", flush=True)
        # Send response back to client
        server_socket.sendto(response, client_addr)
        
    except Exception as e:
        print(f"[ERROR] Failed to forward query: {e}", flush=True)

def dns_proxy_server():
    """Main DNS proxy server with delay"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('0.0.0.0', 53))
    
    print("[PROXY] DNS Proxy with 500ms delay started on port 53", flush=True)
    print("[PROXY] Forwarding queries to auth server 10.0.0.30:53", flush=True)
    
    while True:
        try:
            # Receive DNS query
            data, client_addr = server_socket.recvfrom(512)
            print(f"[QUERY] Received DNS query from {client_addr[0]}:{client_addr[1]}", flush=True)
            
            # Handle each query in a separate thread
            thread = threading.Thread(
                target=forward_dns_query, 
                args=(data, client_addr, server_socket)
            )
            thread.daemon = True
            thread.start()
            
        except KeyboardInterrupt:
            print("[PROXY] Shutting down DNS proxy", flush=True)
            break
        except Exception as e:
            print(f"[ERROR] Server error: {e}", flush=True)
    
    server_socket.close()

if __name__ == "__main__":
    dns_proxy_server()
