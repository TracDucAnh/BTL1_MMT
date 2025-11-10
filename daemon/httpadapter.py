#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3O93/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from urllib import request
from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict
import json
from .response import SESSION_STORE
import uuid

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.
    ... (Phần Docstring và __attrs__ giữ nguyên) ...
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.
        ... (Phần khởi tạo __init__ giữ nguyên) ...
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.
        ... (Phần Docstring của handle_client giữ nguyên) ...
        """

        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        # Handle the request
        msg = conn.recv(1024).decode()
        
        # Đọc full body nếu có Content-Length
        content_length = 0
        if 'Content-Length:' in msg:
            for line in msg.split('\n'):
                if line.startswith('Content-Length:'):
                    content_length = int(line.split(':')[1].strip())
                    break
        
        if content_length > 0:
            while len(msg.split('\r\n\r\n', 1)[1] if '\r\n\r\n' in msg else '') < content_length:
                chunk = conn.recv(1024).decode()
                if not chunk:
                    break
                msg += chunk

        print("[HttpAdapter Debug] Raw request:", msg.replace('\n', '\\n'))
        req.prepare(msg, routes)

        # === BẮT ĐẦU KHỐI SỬA LỖI ===
        #
        # Logic điều phối API (Xử lý API hook)
        #
        if req.method == 'OPTIONS':
            print("[HttpAdapter] Handling OPTIONS preflight request for CORS")
            resp.status_code = 200
            resp.reason = 'OK'
            
            # Phản hồi các header cho phép
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            resp.headers['Content-Length'] = '0' # OPTIONS không có nội dung
            
            conn.sendall(resp.build_response_header(req)) # Chỉ gửi header
            conn.close()
            return
        
        if req.hook:
            try:
                # 1. Gọi hàm API của bạn (ví dụ: submit_info)
                #    Nó trả về một DICTIONARY (ví dụ: {'status': 'ok'})
                result_dict = req.hook(headers=req.headers, body=getattr(req, 'body', None))

                if isinstance(result_dict, dict):
                    # 2. Chuyển dictionary thành chuỗi JSON, sau đó thành bytes
                    result_bytes = json.dumps(result_dict).encode('utf-8')
                    
                    # 3. Xây dựng phản hồi (resp)
                    resp.status_code = 200
                    resp.reason = 'OK'
                    resp.headers['Content-Type'] = 'application/json'
                    # Cho phép CORS (quan trọng cho fetch từ domain/port khác)
                    resp.headers['Access-Control-Allow-Origin'] = '*' 
                    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                    
                    # 4. GÁN NỘI DUNG. Bước này RẤT QUAN TRỌNG
                    #    để build_response_header tính Content-Length đúng
                    resp._content = result_bytes 
                    
                    # 5. Gửi header (đã có Content-Length đúng) + nội dung
                    conn.sendall(resp.build_response_header(req) + resp._content)
                    conn.close()
                    return # QUAN TRỌNG: Dừng lại ở đây

                else:
                    # (Xử lý nếu API của bạn trả về str hoặc thứ gì khác)
                    print(f"[HttpAdapter] hook returned non-dict: {type(result_dict)}")
                    return

            except Exception as e:
                print(f'[HttpAdapter] hook error: {e}')
                return
        
        # === KẾT THÚC KHỐI SỬA LỖI ===

        if req.method == 'POST' and req.path == '/login':
            body_params = {}
            if req.body:
                pairs = req.body.split('&')
                for pair in pairs:
                    if '=' in pair: # Đảm bảo pair hợp lệ
                        key, val = pair.split('=', 1)
                        body_params[key.strip()] = val.strip()

            username = body_params.get('username')
            password = body_params.get('password')
            is_authenticated = False
            try:
                with open("db/account.json", "r", encoding="utf-8") as f:
                    accounts = json.load(f)
                    for acc in accounts:
                        if acc.get("username") == username and acc.get("password") == password:
                            is_authenticated = True
                            break
            except FileNotFoundError:
                print("[HttpAdapter] account.json not found.")
            except json.JSONDecodeError:
                print("[HttpAdapter] account.json invalid format!")

            if is_authenticated:
                sid = str(uuid.uuid4())
                SESSION_STORE[sid] = username
                resp.status_code = 200
                resp.reason = "OK"
                resp.headers["Set-Cookie"] = f"sessionid={sid}; Path=/; HttpOnly"
                resp.headers["Location"] = "/index.html"
                req.path = "/index.html"
            else:
                resp.status_code = 401
                resp.reason = 'Unauthorized'
                resp._content = (
                    b"<html><head><title>401 Unauthorized</title></head><body>401 Unauthorized</body></html>"
                )
                header = (
                    f"HTTP/1.1 401 Unauthorized\r\n"
                    f"Content-Type: text/html\r\n"
                    f"Content-Length: {len(resp._content)}\r\n"
                    f"Connection: close\r\n\r\n"
                ).encode("utf-8")
                conn.sendall(header + resp._content)
                conn.close()
                return

        elif req.method == 'GET':
            # Sửa lỗi: Lấy cookie từ req.headers (do request.py chuẩn bị)
            cookies_string = req.headers.get('cookie', '')

            # Cho phép truy cập trực tiếp static files mà không cần auth
            public_paths = ("/login.html", "/css/", "/js/", "/images/", "/static/")
            if req.path.startswith(public_paths):
                resp.status_code = 200
                resp.reason = "OK"

            # Sửa lỗi: Dùng hàm validate_session từ response.py
            elif resp.validate_session(cookies_string):
                if req.path == '/':
                    req.path = '/index.html'
                resp.status_code = 200
                resp.reason = "OK"

            # Còn lại thì bắt redirect về login
            else:
                req.path = "/login.html"
                resp.status_code = 302 # Mã 302 là Redirect
                resp.reason = "Redirect to login"
                resp.headers["Location"] = "/login.html"


        # Build response (Xử lý file tĩnh - CHỈ CHẠY NẾU req.hook là None)
        response = resp.build_response(req)

        #print(response)
        conn.sendall(response)
        conn.close()

    @property
    def extract_cookies(self, req, resp):
        # ... (Phần còn lại của file giữ nguyên) ...
        """
        Build cookies from the :class:`Request <Request>` headers.
        ...
        """
        cookies = {}
        for header in req.headers:
            if header.startswith("Cookie:"):
                cookie_str = header.split(":", 1)[1].strip()
                for pair in cookie_str.split(";"):
                    if "=" in pair:
                        key, value = pair.strip().split("=")
                        cookies[key] = value
        return cookies

    def build_response(self, req, resp):
        # ... (Phần còn lại của file giữ nguyên) ...
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set default encoding for response
        response.encoding = 'utf-8' 
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        # Sửa lỗi: extract_cookies cần 2 tham số
        response.cookies = self.extract_cookies(req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    # def get_connection(self, url, proxies=None):
    # ... (Phần còn lại của file giữ nguyên) ...

    def add_headers(self, request):
        # ... (Phần còn lại của file giữ nguyên) ...
        pass

    def build_proxy_headers(self, proxy):
        # ... (Phần còn lại của file giữ nguyên) ...
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("user1", "password")
    
        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers