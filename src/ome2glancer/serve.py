import http.server
import os
import socket
import sys


def get_local_ip():
    """
    From https://stackoverflow.com/a/166589
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super().end_headers()


def serve(path, ip="localhost", port=8000, silent=True):
    os.chdir(path)
    with open(os.devnull, "w") as f:
        if silent:
            sys.stdout = f
            sys.stderr = f
        server = http.server.HTTPServer((ip, port), CORSRequestHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
