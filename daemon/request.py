# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict


class Request:
    """The fully mutable `Request` object containing
    the exact bytes that will be sent to the server.

    Instances are generated from an incoming HTTP message
    and should not be instantiated manually.
    """

    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL or path.
        self.url = None
        self.path = None
        #: Dictionary of HTTP headers.
        self.headers = CaseInsensitiveDict()
        #: Cookies associated with the request.
        self.cookies = CaseInsensitiveDict()
        #: Request body (bytes or string).
        self.body = None
        #: Routes mapping (method, path) → handler.
        self.routes = {}
        #: Hook point for a routed mapped path.
        self.hook = None
        #: HTTP version.
        self.version = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if path == "/":
                path = "/index.html"
        except Exception as e:
            print(request)
            print(f"[Request] Error parsing request line: {e}")
            return None, None, None

        return method, path, version

    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split("\r\n")
        headers = {}
        for line in lines[1:]:
            if ": " in line:
                key, val = line.split(": ", 1)
                headers[key.lower()] = val
        return CaseInsensitiveDict(headers)

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        # Extract request line
        self.method, self.path, self.version = self.extract_request_line(request)
        print(f"[Request] {self.method} path {self.path} version {self.version}")

        # Routing hook
        if routes:
            self.routes = routes
            route_key = (self.method, self.path)
            self.hook = routes.get(route_key)

        # Parse headers
        self.headers = self.prepare_headers(request)

        # Parse body (safe split)
        body_pattern = "\r\n\r\n"
        body = request.split(body_pattern, 1)[1] if body_pattern in request else ""
        self.prepare_body(body)

        # Parse cookies
        cookies = self.headers.get("cookie", "")
        if cookies:
            self.cookies = self.prepare_cookies(cookies)
        else:
            self.cookies = CaseInsensitiveDict()

        return self

    def prepare_body(self, data, files=None, json=None):
        """Prepare and set the body content."""
        self.body = data
        self.prepare_content_length(data)
        return

    def prepare_content_length(self, body):
        """Ensure Content-Length is present and accurate."""
        if self.headers is None:
            self.headers = CaseInsensitiveDict()

        if body is None:
            self.headers["Content-Length"] = "0"
            return

        if isinstance(body, (bytes, bytearray)):
            self.headers["Content-Length"] = str(len(body))
            return

        try:
            encoded = str(body).encode()
            self.headers["Content-Length"] = str(len(encoded))
        except Exception:
            self.headers["Content-Length"] = "0"
        return

    def prepare_auth(self, auth, url=""):
        """TODO: Prepare request authentication."""
        # self.auth = ...
        return

    def prepare_cookies(self, cookies):
        """Parse and store the cookies header."""
        cookie_dict = CaseInsensitiveDict()
        for kv in cookies.split(";"):
            if "=" in kv:
                k, v = kv.strip().split("=", 1)
                cookie_dict[k] = v
        self.headers["Cookie"] = cookies
        return cookie_dict
