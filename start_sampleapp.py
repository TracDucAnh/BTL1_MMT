#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

import json
import socket
import argparse
import time
from urllib.parse import parse_qs
import urllib.request

from daemon.weaprous import WeApRous

PORT = 8000  # Default port

app = WeApRous()

app.peers = {}
app.messages = []
role = None

# ================================================
# CORS HELPER
# ================================================
def add_cors_headers(response):
    """
    Thêm CORS headers vào response để cho phép cross-origin requests.
    """
    if isinstance(response, dict):
        # Nếu response là dict, thêm headers vào metadata
        if '_cors_headers' not in response:
            response['_cors_headers'] = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
    return response

# ================================================
# HELPERS
# ================================================
def parse_body(headers, body):
    """Parse body from request (supports form & JSON)."""
    data = {}
    if not body or body.strip() == "":
        return data

    content_type = (headers.get('content-type') or '').lower()

    try:
        if 'application/json' in content_type:
            data = json.loads(body)
        else:
            parsed = parse_qs(body)
            data = {k: v[0] for k, v in parsed.items() if v}
    except Exception as e:
        print("[Parser] Failed to parse body:", e)

    return data

def register_routes(app, role):
    # ================================================
    # CORS PREFLIGHT HANDLER
    # ================================================
    @app.route('/submit-info', methods=['OPTIONS'])
    @app.route('/get-list', methods=['OPTIONS'])
    @app.route('/connect-peer', methods=['OPTIONS'])
    @app.route('/get-connected-peers', methods=['OPTIONS'])
    @app.route('/send-peer', methods=['OPTIONS'])
    @app.route('/get-messages', methods=['OPTIONS'])
    @app.route('/hello', methods=['OPTIONS'])
    def handle_options(headers=None, body=None):
        """Xử lý CORS preflight requests"""
        return add_cors_headers({'status': 'ok'})

    @app.route('/hello', methods=['PUT'])
    def hello(headers=None, body=None):
        """
        Handle greeting via PUT request.

        This route prints a greeting message to the console using the provided headers
        and body.

        :param headers (str): The request headers or user identifier.
        :param body (str): The request body or message payload.
        """
        print ("[SampleApp] ['PUT'] Hello in {} to {}".format(headers, body))
        return add_cors_headers({'status': 'ok'})

    @app.route('/submit-info', methods=['POST'])
    def submit_info(headers=None, body=None):
        """
        (TRACKER) Endpoint để một PEER đăng ký thông tin (IP, Port) với Tracker này.
        """
        global role
        if role != 'tracker':
            return add_cors_headers({'status': 'error', 'reason': 'This is for tracker'})
        
        try:        
            data = parse_body(headers, body)
            ip = data.get('ip')
            port = data.get('port')
            username = data.get('username')
            if not ip or not port or not username:
                return add_cors_headers({'status': 'error', 'reason': 'Missing ip or port'})
            
            key = (ip, port)
            peer_data = {
                'ip': ip, 
                'port': port, 
                'username': username,
                'last_seen': time.time()
            }
            if key in app.peers:
                app.peers[key].update(peer_data)
                print(f"[Tracker] Refreshed (keep-alive) peer {key}")
            else:
                app.peers[key] = peer_data
                print(f"[Tracker] Registered peer {key}")

            return add_cors_headers({'status': 'ok'})
        except Exception as e:
            print('[Tracker] Register error:', e)
            return add_cors_headers({'status': 'error', 'reason': str(e)})

    @app.route('/get-list', methods=['GET'])
    def get_list(headers=None, body=None):
        """
        (TRACKER) Endpoint để một PEER lấy danh sách 
        TẤT CẢ các peer khác đã đăng ký (online).
        """
        if role != 'tracker':
            return add_cors_headers({'status': 'error', 'reason': 'This is for tracker'})

        try:
            alive = []
            remove = []
            for k, v in app.peers.items():
                if time.time() - v['last_seen'] <= 180:
                    alive.append({
                        'username': v['username'], 
                        'ip': v['ip'], 
                        'port': v['port']
                        })
                    print(f"Peer address: {v['ip']}, port: {v['port']}")
                else:
                    remove.append(k)
            for k in remove:
                del app.peers[k]
            if not alive:
                return add_cors_headers({'status': 'ok', 'peers': [], 'message': 'No peers online'})
            return add_cors_headers({'status': 'ok', 'peers': alive})
        except Exception as e:
            print('[Tracker] get-list error:', e)
            return add_cors_headers({'status': 'error', 'reason': str(e)})

    @app.route('/connect-peer', methods=['POST'])
    def connect_peer(headers, body):
        """
        (PEER) Đây là một hành động của PEER.
        Một client sẽ gọi route này trên server A,
        yêu cầu server A kết nối với server B (Tracker).
        """
        if role != 'peer':
            return add_cors_headers({'status': 'error', 'reason': 'This is for peer'})

        try:
            data = parse_body(headers, body)
            
            ip = data.get('ip')
            port_str = data.get('port')
            if not ip or not port_str:
                return add_cors_headers({'status': 'error', 'reason': 'Missing ip or port'})
            
            try:
                port = int(port_str)
            except ValueError:
                return add_cors_headers({'status': 'error', 'reason': f'Invalid port number: {port_str}'})
            
            if ip == app.ip and port == app.port:
                print(f"[Peer] Blocked attempt to connect to self: {(ip, port)}")
                return add_cors_headers({'status': 'error', 'reason': 'Cannot connect to self'})
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            try:
                s.connect((ip, port))
                print(f"[Peer] Successfully connected to peer {(ip, port)}")
                return add_cors_headers({'status': 'ok'})
            except socket.timeout:
                print(f"[Peer] Connection timeout to {(ip, port)}")
                return add_cors_headers({'status': 'error', 'reason': 'Connection timeout'})
            except Exception as e:
                print(f"[Peer] Failed to connect to peer {(ip, port)}: {e}")
                return add_cors_headers({'status': 'error', 'reason': str(e)})
            finally:
                s.close()
        except Exception as e:
            print('[Peer] connect-peer error:', e)
            return add_cors_headers({'status': 'error', 'reason': str(e)})

    @app.route('/get-connected-peers', methods=['GET'])
    def get_connected_peers(headers=None, body=None):
        """
        (PEER) Endpoint để một PEER lấy danh sách 
        TẤT CẢ các peer khác đã kết nối với mình.
        """
        try:
            connected = []
            for k, v in app.peers.items():
                connected.append({'ip': v['ip'], 'port': v['port']})
            if not connected:
                return add_cors_headers({'status': 'ok', 'peers': [], 'message': 'No peers online'})
            return add_cors_headers({'status': 'ok', 'peers': connected})
        except Exception as e:
            print('[PEER] get-connected-peers error:', e)
            return add_cors_headers({'status': 'error', 'reason': str(e)})

    @app.route('/send-peer', methods=['POST'])
    def send_peer(headers=None, body=None):
        """
        (PEER) Đây là một hành động của PEER.
        Yêu cầu server này gửi một tin nhắn TRỰC TIẾP đến một peer khác.
        """
        if role != 'peer':
            return add_cors_headers({'status': 'error', 'reason': 'This is for peer'})

        try:
            data = parse_body(headers, body)

            sender_ip = data.get('sender_ip')
            sender_port = data.get('sender_port')
            
            if sender_ip and sender_port:
                sender_message = data.get('message') or data.get('msg') or data.get('text')
                if not sender_message:
                    return add_cors_headers({'status': 'error', 'reason': 'Missing message content'})
            else:
                return add_cors_headers({'status': 'error', 'reason': 'Missing sender_ip or sender_port'})

            mess = {
                'username': data.get('username'),
                'sender_ip': sender_ip,
                'sender_port': sender_port,
                'message': sender_message
            }

            app.messages.append(mess)
            print(f"[Peer] Received message from {(sender_ip, sender_port)}: {sender_message}")
            return add_cors_headers({'status': 'ok'})
        except Exception as e:
            print('[Peer] send-peer error:', e)
            return add_cors_headers({'status': 'error', 'reason': str(e)})

    @app.route('/get-messages', methods=['GET'])
    def get_messages(headers=None, body=None):
        """
        (PEER) Đây là một hành động của PEER.
        Trả về tin nhắn cho PEER.

        """
        try:
            return add_cors_headers({'status': 'ok', 'messages': app.messages})
        except Exception as e:
            print('[Peer/Tracker] broadcast-peer error:', e)
            return add_cors_headers({'status': 'error', 'reason': str(e)})

    @app.route('/broadcast', methods=['POST'])
    def broadcast(headers=None, body=None):
        """
        (PEER) Đây là một hành động của PEER.
        Yêu cầu server này gửi một tin nhắn TRỰC TIẾP đến kênh chung cho các PEER đang HOẠT ĐỘNG.
        """
        if role != 'peer':
            return add_cors_headers({'status': 'error', 'reason': 'This is for peer'})

        try:
            data = parse_body(headers, body)

            message_content = data.get('message') or data.get('msg') or data.get('text')
            if not message_content:
                return add_cors_headers({'status': 'error', 'reason': 'Missing message content'})
            
            sender_ip = data.get('sender_ip')
            sender_port = data.get('sender_port')
            
            tracker_url = 'http://127.0.0.1:9000/get-list'
            active_peers = []
            try:
                # Dùng urllib để server gọi đến một server khác
                with urllib.request.urlopen(tracker_url, timeout=5) as response:
                    if response.status == 200:
                        tracker_data = json.loads(response.read().decode('utf-8'))
                        if tracker_data.get('status') == 'ok':
                            active_peers = tracker_data.get('peers', [])
                    else:
                        raise Exception(f"Tracker returned status {response.status}")
            except Exception as e:
                print(f"[Broadcast] Failed to get peer list from tracker: {e}")
                return add_cors_headers({'status': 'error', 'reason': f'Failed to contact tracker: {e}'})

            if not active_peers:
                return add_cors_headers({'status': 'ok', 'message': 'No other peers online to broadcast to.'})

            sent_count = 0
            failed_count = 0

            mess = {
                'username': body.get('username'),
                'sender_ip': sender_ip,
                'sender_port': sender_port,
                'message': f"[Broadcast] {message_content}"
            }
            form_data = urllib.parse.urlencode(mess).encode('utf-8')

            for peer in active_peers:
                try:
                    peer_ip = peer.get('ip')
                    peer_port = int(peer.get('port')) # Port từ JSON có thể là string

                    # 5. Bỏ qua, không gửi cho chính mình
                    if peer_ip == sender_ip and peer_port == sender_port:
                        continue

                    # 6. Gửi POST /send-peer đến peer đích
                    target_url = f"http://{peer_ip}:{peer_port}/send-peer"
                    
                    # Tạo một request POST mới
                    req = urllib.request.Request(target_url, data=form_data, method='POST')
                    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
                    
                    with urllib.request.urlopen(req, timeout=3) as peer_response:
                        if peer_response.status == 200:
                            print(f"[Broadcast] Sent message to {peer_ip}:{peer_port}")
                            sent_count += 1
                        else:
                            print(f"[Broadcast] Failed to send to {peer_ip}:{peer_port}, status: {peer_response.status}")
                            failed_count += 1
                except Exception as e:
                    # Bắt lỗi nếu 1 peer bị timeout hoặc offline
                    print(f"[Broadcast] Error sending to {peer.get('ip')}:{peer.get('port')}: {e}")
                    failed_count += 1
            return add_cors_headers({'status': 'ok', 'message': f'Broadcast complete. Sent to {sent_count} peers. Failed {failed_count} peers.'})
        except Exception as e:
            print('[Broadcast] General error: {e}')
            return add_cors_headers({'status': 'error', 'reason': str(e)})

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--role', type=str, default='peer', choices=['tracker', 'peer'])
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
 
    args = parser.parse_args()
    role = args.role
    ip = args.server_ip
    port = args.server_port

    register_routes(app, role)
    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()