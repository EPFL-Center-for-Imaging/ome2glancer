import http.server
import os
import sys


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super().end_headers()


def serve(path, port=8000, silent=True):
    os.chdir(path)
    with open(os.devnull, "w") as f:
        if silent:
            sys.stdout = f
            sys.stderr = f
        server = http.server.HTTPServer(("localhost", 8000), CORSRequestHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
