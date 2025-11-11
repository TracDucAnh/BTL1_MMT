import json
import argparse
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from daemon.weaprous import WeApRous
app = WeApRous()

PEERS = {}


# ----------------------------------------------------------
# 1. /submit-info → Peer registration
# ----------------------------------------------------------
@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    """
    body: {"ip": "...", "port": 8001}
    """
    print("DEBUG submit-info headers=", headers)
    print("DEBUG submit-info body=", body)
    data = json.loads(body)
    ip = data["ip"]
    port = data["port"]

    key = f"{ip}:{port}"
    PEERS[key] = {"ip": ip, "port": port}

    return json.dumps({"status": "ok"}), "application/json"


# ----------------------------------------------------------
# 2. /get-list → Peer discovery
# ----------------------------------------------------------
@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    lst = list(PEERS.values())
    return json.dumps({"status": "ok", "peers": lst}), "application/json"


# ----------------------------------------------------------
# 3. /connect-peer → Setup direct P2P connections
# ----------------------------------------------------------
@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers, body):
    """
    body: {"from": {"ip":..., "port":...}, "to": {"ip":..., "port":...}}
    """
    data = json.loads(body)
    print("[Tracker] Peer requesting connection:", data)
    return json.dumps({"status": "ok"}), "application/json"


# ----------------------------------------------------------
# 4. /broadcast-peer
# ----------------------------------------------------------
@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers, body):
    data = json.loads(body)
    print("[Tracker] Broadcast request:", data)
    return json.dumps({"status": "ok"}), "application/json"


# ----------------------------------------------------------
# 5. /send-peer → Optional direct messaging request
# ----------------------------------------------------------
@app.route('/send-peer', methods=['POST'])
def send_peer(headers, body):
    data = json.loads(body)
    print("[Tracker] Peer-to-peer send:", data)
    return json.dumps({"status": "ok"}), "application/json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Tracker', description='', epilog='Tracker daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=7000)
    args = parser.parse_args()

    app.prepare_address(args.server_ip, args.server_port)
    app.run()
