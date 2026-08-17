"""UDP and TCP listeners. Both speak the same one-JSON-object-per-message
protocol and drop everything into a single queue the render loop drains."""

from __future__ import annotations

import json
import queue
import socket
import threading


class Listener:
    def __init__(self, cfg):
        self.q: "queue.Queue[dict]" = queue.Queue()
        self.cfg = cfg
        self._stop = threading.Event()
        self.threads: list[threading.Thread] = []

    def start(self):
        if not self.cfg.get("net.enabled", True):
            return
        host = self.cfg.get("net.host", "127.0.0.1")
        udp = int(self.cfg.get("net.udp_port", 9955))
        tcp = int(self.cfg.get("net.tcp_port", 9956))
        for target, args in ((self._udp, (host, udp)), (self._tcp, (host, tcp))):
            th = threading.Thread(target=target, args=args, daemon=True)
            th.start()
            self.threads.append(th)
        return host, udp, tcp

    def stop(self):
        self._stop.set()

    def drain(self):
        out = []
        while True:
            try:
                out.append(self.q.get_nowait())
            except queue.Empty:
                return out

    # -- workers -----------------------------------------------------------

    def _push(self, raw: bytes):
        try:
            msg = json.loads(raw.decode("utf-8"))
        except Exception:
            return
        if isinstance(msg, dict):
            self.q.put(msg)
        elif isinstance(msg, list):
            for m in msg:
                if isinstance(m, dict):
                    self.q.put(m)

    def _udp(self, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.settimeout(0.4)
        while not self._stop.is_set():
            try:
                data, _ = s.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            self._push(data)
        s.close()

    def _tcp(self, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(4)
        s.settimeout(0.4)
        while not self._stop.is_set():
            try:
                conn, _ = s.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()
        s.close()

    def _serve(self, conn: socket.socket):
        conn.settimeout(0.5)
        buf = b""
        while not self._stop.is_set():
            try:
                chunk = conn.recv(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if line.strip():
                    self._push(line)
        conn.close()
