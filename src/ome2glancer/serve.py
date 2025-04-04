import html
import http.server
import io
import os
import socket
import sys
import urllib
import webbrowser

import typer
from typing_extensions import Annotated

import ome2glancer


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


class CORSRequestHandlerWithNeuroglancerLinks(CORSRequestHandler):
    def list_directory(self, path):
        """
        Copied from cpython/Lib/http/server.py

        Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list_of_dir = os.listdir(path)
        except OSError:
            self.send_error(http.HTTPStatus.NOT_FOUND, "No permission to list directory")
            return None
        list_of_dir.sort(key=lambda a: a.lower())
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path, errors="surrogatepass")
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(self.path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = f"Directory listing for {displaypath}"
        r.append("<!DOCTYPE HTML>")
        r.append('<html lang="en">')
        r.append("<head>")
        r.append(f'<meta charset="{enc}">')
        r.append(f"<title>{title}</title>\n</head>")
        r.append(f"<body>\n<h1>{title}</h1>")
        r.append("<hr>\n<ul>")
        for name in list_of_dir:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /

            r.append(
                '<li><a href="{}">{}</a></li>'.format(
                    urllib.parse.quote(linkname, errors="surrogatepass"), html.escape(displayname, quote=False)
                )
            )
            if name.endswith(".ome.zarr"):
                neuroglancer_linkname = ome2glancer.link_gen.link_gen(
                    f"http://{self.server.server_name}:{self.server.server_port}{self.path}{name}",
                    open_in_browser=False,
                )
                r[-1] = r[-1].split("</li>")[0] + f"<br><a href={neuroglancer_linkname}>Open in Neuroglancer</a></li>"
        r.append("</ul>\n<hr>\n</body>\n</html>\n")
        encoded = "\n".join(r).encode(enc, "surrogateescape")
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(http.HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f


def serve(
    path: Annotated[
        str,
        typer.Argument(help="Path to the folder that should be server. Can be a .ome.zarr file"),
    ],
    ip: Annotated[str, typer.Option(help="Address of the server.")] = get_local_ip(),
    port: Annotated[int, typer.Option(help="Port on which to serve the folder.")] = 8000,
    open_in_browser: Annotated[bool, typer.Option(help="Open the link in the default webbrowser.")] = True,
    silent: Annotated[bool, typer.Option(help="Stope the server from printing to the console.")] = True,
    create_links: Annotated[
        bool,
        typer.Option(help="Link to neuroglancer for folder ending in .ome.zarr instead of resursing into the folder."),
    ] = True,
):
    os.chdir(path)
    with open(os.devnull, "w") as f:
        if silent:
            sys.stdout = f
            sys.stderr = f
        if create_links:
            server = http.server.ThreadingHTTPServer((ip, port), CORSRequestHandlerWithNeuroglancerLinks)
        else:
            server = http.server.ThreadingHTTPServer((ip, port), CORSRequestHandler)

        if open_in_browser:
            webbrowser.open_new(f"{ip}:{port}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
