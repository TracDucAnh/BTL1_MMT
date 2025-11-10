import datetime
import os
import mimetypes
from .dictionary import CaseInsensitiveDict
import uuid   # === ADDED FOR COOKIE MANAGEMENT ===

BASE_DIR = ""
SESSION_STORE = {}
# === ADDED FOR COOKIE MANAGEMENT ===
SESSION_STORE = {}  # simple in-memory session store


class Response():
    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]

    def __init__(self, request=None):
        self._content = False
        self._content_consumed = False
        self._next = None
        self.status_code = None
        self.headers = {}
        self.url = None
        self.encoding = None
        self.history = []
        self.reason = None
        self.cookies = CaseInsensitiveDict()
        self.elapsed = datetime.timedelta(0)
        self.request = None

    # === ADDED FOR COOKIE MANAGEMENT ===
    def create_session(self, user="guest"):
        """Create a new session ID and store it in SESSION_STORE."""
        session_id = str(uuid.uuid4())
        SESSION_STORE[session_id] = {
            "user": user,
            "created_at": datetime.datetime.now(),
        }
        return session_id

    def validate_session(self, cookie_header):
        """Validate cookie from request header."""
        if not cookie_header:
            return False
        parts = cookie_header.split(";")
        for p in parts:
            if "sessionid=" in p:
                sid = p.strip().split("sessionid=")[1]
                if sid in SESSION_STORE:
                    return sid
        return False

    def get_mime_type(self, path):
        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'

    def prepare_content_type(self, mime_type='text/html'):
        base_dir = ""
        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] processing MIME main_type={} sub_type={}".format(main_type, sub_type))
        if main_type == 'text':
            self.headers['Content-Type'] = 'text/{}'.format(sub_type)
            if sub_type == 'plain' or sub_type == 'css':
                base_dir = BASE_DIR + "static/"
            elif sub_type == 'html':
                base_dir = BASE_DIR + "www/"
            else:
                #handle_text_other(sub_type)
                base_dir = BASE_DIR+"www/"
        elif main_type == 'image':
            base_dir = os.path.join(BASE_DIR, "static/")
            self.headers['Content-Type'] = f"image/{sub_type}"
        elif main_type == 'application':
            base_dir = BASE_DIR + "apps/"
            self.headers['Content-Type'] = 'application/{}'.format(sub_type)
        elif main_type == "video":
            base_dir = BASE_DIR + "videos/"
            self.headers["Content-Type"] = "videos/{}".format(sub_type)
        elif main_type == "audio":
            base_dir = BASE_DIR + "audios/"
            self.headers["Content-Type"] = "audio/{}".format(sub_type)
        elif main_type == "application" and sub_type in ["xml", "zip", "json"]:
            base_dir = BASE_DIR + "apps/"
            self.headers["Content-Type"] = "application/{}".format(sub_type)
        elif main_type == "text" and sub_type in ["csv", "xml"]:
            base_dir = BASE_DIR + "static/"
            self.headers["Content-Type"] = "text/{}".format(sub_type)
        else:
            raise ValueError("Invalid MEME type: main_type={} sub_type={}".format(main_type, sub_type))
        
        return base_dir

    def build_content(self, path, base_dir):
        filepath = os.path.join(base_dir, path.lstrip('/'))
        print("[Response] serving the object at location {}".format(filepath))
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            return len(content), content
        except FileNotFoundError:
            print("[Response] File not found: {}".format(filepath))
            content = b"404 Not Found"
            return len(content), content
        except Exception as e:
            print("[Response] Error reading file: {}".format(e))
            content = b"500 Internal Server Error"
            return len(content), content

    def build_response_header(self, request):
        reqhdr = request.headers
        rsphdr = self.headers

        if not self.status_code:
            self.status_code = 200
            self.reason = "OK"

        headers = {
            "Date": datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Server": "WeApRous/1.0",
            "Content-Type": rsphdr.get("Content-Type", "text/html"),
            "Content-Length": str(len(self._content) if self._content else 0),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "close",
            "User-Agent": reqhdr.get("User-Agent", "WeApRousClient/1.0"),
        }

        # === ADDED FOR COOKIE MANAGEMENT ===
        if "Set-Cookie" in rsphdr:
            headers["Set-Cookie"] = rsphdr["Set-Cookie"]

        if self.status_code == 302 and hasattr(self, "redirect_location"):
            headers["Location"] = self.redirect_location

        status_line = f"HTTP/1.1 {self.status_code} {self.reason}\r\n"
        for k, v in headers.items():
            status_line += f"{k}: {v}\r\n"
        status_line += "\r\n"

        return status_line.encode("utf-8")

    def build_notfound(self):
        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Accept-Ranges: bytes\r\n"
            "Content-Type: text/html\r\n"
            "Content-Length: 13\r\n"
            "Cache-Control: max-age=86000\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode('utf-8')

    def build_response(self, request):
        """
        Builds a full HTTP response including headers and content based on the request.

        :params request (class:`Request <Request>`): incoming request object.

        :rtype bytes: complete HTTP response using prepared headers and content.
        """

        path = request.path
    
        mime_type = self.get_mime_type(path)
        print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

        base_dir = ""

        # If HTML, parse and serve embedded objects
        if path.endswith('.html') or mime_type == 'text/html':
            base_dir = self.prepare_content_type(mime_type = 'text/html')
        elif path.endswith('.js') or mime_type == 'application/javascript':
            # serve JS from static/
            self.headers['Content-Type'] = 'application/javascript'
            base_dir = BASE_DIR + 'static/'
        elif mime_type == 'text/css':
            base_dir = self.prepare_content_type(mime_type = 'text/css')
        #
        # TODO: add support objects
        #
        else:
            return self.build_notfound()

        c_len, self._content = self.build_content(path, base_dir)
        self._header = self.build_response_header(request)

        return self._header + self._content