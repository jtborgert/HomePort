"""Socket.IO / WebSocket client for Homey Pro real-time event updates."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import select
import socket
import ssl
import struct
import threading
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, str, Any], None]  # (uri, event_type, data)


class HomeyRealtimeClient:
    """
    Lightweight, dependency-free WebSocket & Socket.IO client for Homey Pro.
    Handles Engine.io / Socket.io protocol framing, authentication handshake,
    subscriptions, and real-time capability / flow events.
    """

    def __init__(
        self,
        base_url: str,
        session_token: str,
        homey_id: Optional[str] = None,
        on_event: Optional[EventCallback] = None,
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.session_token = session_token
        self.homey_id = homey_id or ""
        self.on_event = on_event
        self.verify_ssl = verify_ssl

        self.subscribed_uris: Set[str] = set()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._authenticated = False
        self._ack_callbacks: Dict[int, Callable[[Any, Any], None]] = {}
        self._ack_counter = 1
        self._lock = threading.Lock()
        self._namespace = ""

    @property
    def is_connected(self) -> bool:
        return self._connected and self._running

    def start(self) -> None:
        """Starts the real-time client in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, name="HomeySocketIO", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops the real-time client and closes connection."""
        self._running = False
        self._close_socket()
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._connected = False
        self._authenticated = False

    def subscribe(self, uri: str) -> None:
        """Subscribes to an event URI (e.g. 'homey:manager:flow', 'homey:device:<id>')."""
        self.subscribed_uris.add(uri)
        if self._connected and self._authenticated:
            self._send_subscribe(uri)

    def unsubscribe(self, uri: str) -> None:
        """Unsubscribes from an event URI."""
        self.subscribed_uris.discard(uri)
        if self._connected and self._authenticated:
            self._send_unsubscribe(uri)

    # --------------------------------------------------------------------------
    # Main Connection and Processing Loop
    # --------------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Background connection and reconnection loop."""
        reconnect_delay = 2.0
        max_reconnect_delay = 30.0

        while self._running:
            try:
                self._connect_and_listen()
                reconnect_delay = 2.0
            except Exception as e:
                if self._running:
                    logger.warning("Homey Socket.io connection lost: %s. Reconnecting in %.1fs...", e, reconnect_delay)
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)

    def _connect_and_listen(self) -> None:
        """Connects via WebSocket and processes incoming Socket.io frames."""
        parsed = urllib.parse.urlparse(self.base_url)
        is_ssl = parsed.scheme in ("https", "wss")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if is_ssl else 80)

        # 1. Establish TCP socket
        raw_sock = socket.create_connection((host, port), timeout=10.0)
        if is_ssl:
            ssl_ctx = ssl.create_default_context()
            if not self.verify_ssl:
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            self._sock = ssl_ctx.wrap_socket(raw_sock, server_hostname=host)
        else:
            self._sock = raw_sock

        # 2. Perform WebSocket Upgrade Handshake
        ws_key = base64.b64encode(os.urandom(16)).decode("utf-8")
        ws_path = f"{parsed.path or ''}/socket.io/?EIO=4&transport=websocket"
        if not ws_path.startswith("/"):
            ws_path = "/" + ws_path

        req = (
            f"GET {ws_path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"Origin: {self.base_url}\r\n"
            f"\r\n"
        )
        self._sock.sendall(req.encode("utf-8"))

        # Read HTTP upgrade response
        res = b""
        while b"\r\n\r\n" not in res:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionResetError("Connection closed during WebSocket handshake")
            res += chunk

        status_line = res.split(b"\r\n")[0].decode("utf-8", errors="ignore")
        if "101" not in status_line:
            raise ConnectionError(f"WebSocket upgrade failed: {status_line}")

        self._connected = True
        logger.info("Connected to Homey WebSocket: %s", self.base_url)

        # 3. Main frame read loop
        buffer = bytearray()
        last_ping = time.time()

        while self._running:
            # Check if socket is readable
            r, _, _ = select.select([self._sock], [], [], 1.0)
            if r:
                opcode, payload = self._read_ws_frame()
                if opcode == 0x8:  # Close frame
                    break
                elif opcode == 0x9:  # Ping frame
                    self._send_ws_frame(0xA, payload)  # Pong
                elif opcode in (0x1, 0x2):  # Text or binary
                    text_msg = payload.decode("utf-8", errors="ignore")
                    self._handle_socketio_packet(text_msg)

            # Send Engine.io ping if needed
            if time.time() - last_ping > 20.0:
                self._send_raw_socketio("2")  # Engine.io ping
                last_ping = time.time()

        self._close_socket()

    # --------------------------------------------------------------------------
    # Socket.IO / Engine.IO Protocol Handlers
    # --------------------------------------------------------------------------

    def _handle_socketio_packet(self, packet: str) -> None:
        """Parses Engine.io / Socket.io packet text."""
        if not packet:
            return

        pkt_type = packet[0]
        payload = packet[1:]

        if pkt_type == "0":  # Engine.io OPEN
            # Send Socket.io CONNECT
            self._send_raw_socketio("40")
        elif pkt_type == "2":  # Engine.io PING
            self._send_raw_socketio("3")  # Engine.io PONG
        elif pkt_type == "3":  # Engine.io PONG
            pass
        elif pkt_type == "4":  # Socket.io message packet
            self._handle_socketio_message(payload)

    def _handle_socketio_message(self, msg: str) -> None:
        """Handles Socket.io message packet (starts with sio type)."""
        if not msg:
            return

        sio_type = msg[0]
        rest = msg[1:]

        # Handle namespace if present (e.g. "/api,")
        ns = ""
        if rest.startswith("/"):
            comma_idx = rest.find(",")
            if comma_idx != -1:
                ns = rest[:comma_idx]
                rest = rest[comma_idx + 1:]

        if sio_type == "0":  # SIO CONNECTED
            logger.info("Socket.io connected (ns=%s). Starting handshakeClient...", ns)
            self._send_handshake_client()

        elif sio_type == "2":  # SIO EVENT
            try:
                data = json.loads(rest)
                if isinstance(data, list) and len(data) >= 1:
                    event_name = data[0]
                    event_type = data[1] if len(data) > 1 and isinstance(data[1], str) else "update"
                    event_payload = data[2] if len(data) > 2 else (data[1] if len(data) > 1 else None)

                    if self.on_event:
                        self.on_event(event_name, event_type, event_payload)
            except Exception as e:
                logger.debug("Failed to parse SIO event: %s (%s)", rest, e)

        elif sio_type == "3":  # SIO ACK
            # Parse ack id and result
            try:
                # Find start of JSON array
                json_start = rest.find("[")
                if json_start != -1:
                    ack_id_str = rest[:json_start]
                    ack_data = json.loads(rest[json_start:])
                    ack_id = int(ack_id_str) if ack_id_str.isdigit() else None
                    if ack_id and ack_id in self._ack_callbacks:
                        cb = self._ack_callbacks.pop(ack_id)
                        err = ack_data[0] if len(ack_data) > 0 else None
                        res = ack_data[1] if len(ack_data) > 1 else None
                        cb(err, res)
            except Exception as e:
                logger.debug("Failed to parse SIO ACK: %s (%s)", rest, e)

    def _send_handshake_client(self) -> None:
        """Emits `handshakeClient` event to authenticate with Homey."""
        ack_id = self._next_ack_id()

        def on_handshake_ack(err: Any, res: Any) -> None:
            if err:
                logger.error("Homey handshakeClient failed: %s", err)
                self._authenticated = False
                return
            logger.info("Homey handshakeClient successful: %s", res)
            self._authenticated = True
            if isinstance(res, dict) and "namespace" in res:
                self._namespace = res["namespace"]

            # Resubscribe to all existing subscriptions
            for uri in list(self.subscribed_uris):
                self._send_subscribe(uri)

        self._ack_callbacks[ack_id] = on_handshake_ack

        handshake_payload = {
            "token": self.session_token,
            "homeyId": self.homey_id,
        }
        # SIO Event with Ack ID: 42<ackId>["handshakeClient", {...}]
        msg = f"42{ack_id}[\"handshakeClient\",{json.dumps(handshake_payload)}]"
        self._send_raw_socketio(msg)

    def _send_subscribe(self, uri: str) -> None:
        """Sends `subscribe` event for a URI."""
        ack_id = self._next_ack_id()
        prefix = f"42{self._namespace}," if self._namespace else "42"
        msg = f"{prefix}{ack_id}[\"subscribe\",{json.dumps(uri)}]"
        self._send_raw_socketio(msg)

    def _send_unsubscribe(self, uri: str) -> None:
        """Sends `unsubscribe` event for a URI."""
        prefix = f"42{self._namespace}," if self._namespace else "42"
        msg = f"{prefix}[\"unsubscribe\",{json.dumps(uri)}]"
        self._send_raw_socketio(msg)

    def _next_ack_id(self) -> int:
        with self._lock:
            self._ack_counter += 1
            return self._ack_counter

    def _send_raw_socketio(self, text: str) -> None:
        """Encapsulates text in a WebSocket text frame and sends it."""
        try:
            self._send_ws_frame(0x1, text.encode("utf-8"))
        except Exception as e:
            logger.debug("Failed to send WebSocket frame: %s", e)

    # --------------------------------------------------------------------------
    # Low-level RFC 6455 WebSocket Framing
    # --------------------------------------------------------------------------

    def _send_ws_frame(self, opcode: int, data: bytes) -> None:
        """Constructs and sends a masked client WebSocket frame."""
        if not self._sock:
            return

        header = bytearray()
        # FIN bit + Opcode
        header.append(0x80 | (opcode & 0x0F))

        # Client-to-server frames MUST be masked
        mask_bit = 0x80
        length = len(data)

        if length < 126:
            header.append(mask_bit | length)
        elif length < 65536:
            header.append(mask_bit | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(mask_bit | 127)
            header.extend(struct.pack("!Q", length))

        # Generate 4-byte masking key
        mask = os.urandom(4)
        header.extend(mask)

        # Apply masking to payload
        masked_payload = bytearray(length)
        for i in range(length):
            masked_payload[i] = data[i] ^ mask[i % 4]

        with self._lock:
            if self._sock:
                self._sock.sendall(header + masked_payload)

    def _read_ws_frame(self) -> Tuple[int, bytes]:
        """Reads a single WebSocket frame from the socket."""
        if not self._sock:
            raise ConnectionResetError("Socket is closed")

        # Read first 2 bytes
        head = self._recv_exact(2)
        b1, b2 = head[0], head[1]
        opcode = b1 & 0x0F
        has_mask = (b2 & 0x80) != 0
        length = b2 & 0x7F

        if length == 126:
            ext_len = self._recv_exact(2)
            length = struct.unpack("!H", ext_len)[0]
        elif length == 127:
            ext_len = self._recv_exact(8)
            length = struct.unpack("!Q", ext_len)[0]

        mask = self._recv_exact(4) if has_mask else None
        payload = bytearray(self._recv_exact(length))

        if has_mask and mask:
            for i in range(length):
                payload[i] ^= mask[i % 4]

        return opcode, bytes(payload)

    def _recv_exact(self, num_bytes: int) -> bytes:
        """Reads exactly num_bytes from the socket."""
        data = bytearray()
        while len(data) < num_bytes:
            if not self._sock:
                raise ConnectionResetError("Socket closed")
            chunk = self._sock.recv(num_bytes - len(data))
            if not chunk:
                raise ConnectionResetError("Socket connection closed by peer")
            data.extend(chunk)
        return bytes(data)

    def _close_socket(self) -> None:
        """Safely closes the underlying socket."""
        with self._lock:
            if self._sock:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
