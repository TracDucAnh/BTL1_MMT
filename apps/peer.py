import json
import socket
import threading
import time
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import argparse
# REMOVE THIS LINE: from daemon.request import Request

# Global State
CONNECTED_PEER = {}
MY_IP = None
MY_PORT = None
TRACKER_IP = None
TRACKER_PORT = None

# 1. Register to tracker
def register_to_tracker(my_ip, my_port, tracker_ip, tracker_port):
    body = json.dumps({"ip": my_ip, "port": my_port})
    request = (
        "POST /submit-info HTTP/1.1\r\n"
        f"Host: {tracker_ip}:{tracker_port}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "\r\n"
        f"{body}"
    )

    s = socket.socket()
    try:
        s.connect((tracker_ip, tracker_port))
        s.send(request.encode())
        resp = s.recv(4096).decode()
        print(f"[Peer] Registered to tracker: {resp[:100]}")
        s.close()
        return resp
    except Exception as e:
        print(f"[Peer] Failed to register: {e}")
        s.close()
        return None

# 2. Get peer list
def get_peer_list(tracker_ip, tracker_port):
    req_text = (
        "GET /get-list HTTP/1.1\r\n"
        f"Host: {tracker_ip}:{tracker_port}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )

    s = socket.socket()
    try:
        s.connect((tracker_ip, tracker_port))
        s.send(req_text.encode())

        resp = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
        s.close()

        resp = resp.decode()

        # Split header và body
        parts = resp.split("\r\n\r\n", 1)
        if len(parts) < 2:
            print("[Peer] Empty response from tracker")
            return []

        body = parts[1].strip()
        if not body:
            print("[Peer] Empty body from tracker")
            return []

        try:
            data = json.loads(body)
            peers = data.get("peers", [])
            print(f"[Peer] Got {len(peers)} peer(s) from tracker")
            return peers
        except json.JSONDecodeError as e:
            print(f"[Peer] Response is not valid JSON: {body[:100]}")
            return []
    except Exception as e:
        print(f"[Peer] Error getting peer list: {e}")
        return []


# 3. Connect to peer
def connect_to_peer(ip, port):
    # Don't connect to yourself
    if ip == MY_IP and port == MY_PORT:
        return
    
    key = f"{ip}:{port}"
    if key in CONNECTED_PEER:
        return 
    
    s = socket.socket()
    try:
        s.connect((ip, port))
        CONNECTED_PEER[key] = s
        print(f"[Peer] Connected to {key}")
    except Exception as e:
        print(f"[Peer] Failed to connect to {key}: {e}")

# 4. Broadcast
def broadcast(message):
    if not CONNECTED_PEER:
        print("[Peer] No peers connected to broadcast")
        return
    
    dead = []
    sent_count = 0

    for key, s in CONNECTED_PEER.items():
        try:
            s.send(message.encode())
            sent_count += 1
        except Exception as e:
            print(f"[Peer] Failed to send to {key}: {e}")
            dead.append(key)

    for k in dead:
        del CONNECTED_PEER[k]
    
    print(f"[Peer] Broadcasted to {sent_count} peer(s)")

# 5. TCP Server: receive messages
def server_loop():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((MY_IP, MY_PORT))
        srv.listen(5)
        print(f"[Peer] Listening on {MY_IP}:{MY_PORT}")
    except Exception as e:
        print(f"[Peer] Failed to bind server: {e}")
        return

    while True:
        try:
            conn, addr = srv.accept()
            threading.Thread(target=client_handler, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print(f"[Peer] Server error: {e}")
            break

def client_handler(conn, addr):
    print(f"[Peer] Incoming connection from {addr}")
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break
            print(f"[Recv from {addr}] {data.decode()}")
        except Exception as e:
            print(f"[Peer] Error handling client {addr}: {e}")
            break
    conn.close()

# 6. Periodically sync with tracker
def tracker_sync_loop():
    print("[Peer] Starting tracker sync loop...")
    while True:
        try:
            peers = get_peer_list(TRACKER_IP, TRACKER_PORT)

            for p in peers:
                ip = p["ip"]
                port = p["port"]
                connect_to_peer(ip, port)

        except Exception as e:
            print(f"[Peer] Tracker sync error: {e}")
        
        time.sleep(5)

# 7. UI Loop (console)
def input_loop():
    print("\n[Peer] Ready! Type messages to broadcast (Ctrl+C to exit)")
    while True:
        try:
            msg = input("> ")
            if msg.strip():
                broadcast(msg)
        except KeyboardInterrupt:
            print("\n[Peer] Shutting down...")
            break
        except Exception as e:
            print(f"[Peer] Input error: {e}")


# MAIN
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--tracker-ip", required=True)
    parser.add_argument("--tracker-port", type=int, required=True)
    args = parser.parse_args()

    MY_IP = args.ip
    MY_PORT = args.port
    TRACKER_IP = args.tracker_ip
    TRACKER_PORT = args.tracker_port

    print(f"[Peer] Starting peer at {MY_IP}:{MY_PORT}")
    print(f"[Peer] Tracker at {TRACKER_IP}:{TRACKER_PORT}")

    register_to_tracker(MY_IP, MY_PORT, TRACKER_IP, TRACKER_PORT)

    threading.Thread(target=server_loop, daemon=True).start()
    threading.Thread(target=tracker_sync_loop, daemon=True).start()
    time.sleep(1)
    input_loop()