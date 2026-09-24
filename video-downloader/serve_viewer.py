#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import http.server
import os
import socket
import socketserver
import threading
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"


class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return int(s.getsockname()[1])


def main() -> int:
    os.chdir(ROOT)
    port = pick_port()
    url = f"http://{HOST}:{port}/index.html"

    handler = http.server.SimpleHTTPRequestHandler
    with ReuseTCPServer((HOST, port), handler) as httpd:
        print(f"Realtime Video Viewer: {url}")
        print("이 창을 닫으면 뷰어 서버도 종료됩니다.")

        def open_browser() -> None:
            time.sleep(0.4)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
