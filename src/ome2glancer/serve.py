import http.server
import os
import socket
import sys
import webbrowser

import typer
from typing_extensions import Annotated


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


def serve(
    path: Annotated[
        str,
        typer.Argument(help="Path to the folder that should be server. Can be a .ome.zarr file"),
    ],
    ip: Annotated[str, typer.Option(help="Address of the server.")] = "localhost",
    port: Annotated[int, typer.Option(help="Port on which to serve the folder.")] = 8000,
    open_in_browser: Annotated[bool, typer.Option(help="Open the link in the default webbrowser.")] = True,
    silent: Annotated[bool, typer.Option(help="Stope the server from printing to the console.")] = True,
):
    os.chdir(path)
    with open(os.devnull, "w") as f:
        if silent:
            sys.stdout = f
            sys.stderr = f
        server = http.server.HTTPServer((ip, port), CORSRequestHandler)

        if open_in_browser:
            webbrowser.open_new(f"{ip}:{port}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
