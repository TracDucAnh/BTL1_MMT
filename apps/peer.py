import json
import socket
import threading
import time
import argparse

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
        f"Host: tracker\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
        f"{body}"
    )

    s = socket.socket()
    s.connect((tracker_ip, tracker_port))
    s.send(request.encode())
    resp = s.recv(4096).decode()
    s.close()
    return resp

# 2. Get peer list
def get_peer_list(tracker_ip, tracker_port):
    req = (
        "GET /get-list HTTP/1.1\r\n"
        "Host: tracker\r\n"
        "\r\n"
    )

    s = socket.socket()
    s.connect((tracker_ip, tracker_port))
    s.send(req.encode())
    resp = s.recv(4096).decode()
    s.close()

    header, body = resp.split("\r\n\r\n")
    data = json.loads(body)
    return data["peers"]


# 3. Connect to peer
def connect_to_peer(ip, port):
    key = f"{ip}:{port}"
    if key in CONNECTED_PEER:
        return 
    
    s = socket.socket()
    try:
        s.connect((ip, port))
        CONNECTED_PEER[key] = s
        print(f"[Peer] Connected to {key}")
    except:
        print(f"[Peer] Failed connect to {key}")

# 4. Broadcast
def broadcast(message):
    dead = []

    for key, s in CONNECTED_PEER.items():
        try:
            s.send(message.encode())
        except:
            dead.append(key)

    for k in dead:
        del CONNECTED_PEER[k]

# 5. TCP Server: receive messages
def server_loop():
    srv = socket.socket()
    srv.bind((MY_IP, MY_PORT))
    srv.listen(5)
    print(f"[Peer] Listening on {MY_IP}:{MY_PORT}")

    while True:
        conn, addr = srv.accept()
        threading.Thread(target=client_handler, args=(conn,), daemon=True).start()

def client_handler(conn):
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                return 
            print("[Recv]", data.decode())
        except:
            return

# 6. Periodically sync with tracker
def tracker_sync_loop():
    while True:
        peers = get_peer_list(TRACKER_IP, TRACKER_PORT)

        for p in peers:
            ip = p["ip"]
            port = p["port"]
            if ip == MY_IP and port == MY_PORT:
                continue
            connect_to_peer(ip, port)

        time.sleep(5)

# 7. UI Loop (console)
def input_loop():
    while True:
        msg = input("")
        broadcast(msg)


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

    register_to_tracker(MY_IP, MY_PORT, TRACKER_IP, TRACKER_PORT)

    threading.Thread(target=server_loop, daemon=True).start()
    threading.Thread(target=tracker_sync_loop, daemon=True).start()

    input_loop()