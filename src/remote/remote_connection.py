import json
import asyncio
import websockets
from typing import TypeVar, Any

from gshock_api import message_dispatcher
from gshock_api.casio_constants import CasioConstants
from gshock_api.exceptions import GShockConnectionError
from gshock_api.logger import logger
from gshock_api.utils import to_casio_cmd
from gshock_api.watch_info import watch_info
import contextlib

T = TypeVar("T")

DEFAULT_HOST       = "0.0.0.0"
DEFAULT_PORT       = 9999
DUPLICATE_THRESHOLD = 0.5   # seconds
READ_HANDLE        = 0x0C
BLE_CONNECT_TIMEOUT = 60.0  # seconds to wait for Android BLE handshake


class RemoteConnection:
    """
    Server-side WebSocket connection — drop-in replacement for Connection.

    Implements the same interface as Connection (write, request, send_message,
    disconnect, is_service_supported) so GshockAPI works identically whether
    BLE is local or proxied through an Android device.

    Flow:
      1. Python starts WebSocket server and waits for Android to connect.
      2. Android establishes BLE link to the watch, sends {"type":"connected"}.
      3. Python gates all writes behind that signal — no commands sent early.
      4. Watch notifications arrive as {"type":"notification","payload":"hex"}
         and are routed to MessageDispatcher exactly as in local Connection.

    Protocol (WebSocket JSON):
      Python → Android:  {"type": "write", "handle": "0x0e", "payload": "hex"}
      Android → Python:  {"type": "notification", "payload": "hex"}
      Android → Python:  {"type": "connected", "address": '{"name":"...","address":"..."}'}
      Android → Python:  {"type": "log", "level": "info", "msg": "..."}
    """

    HandleMap = dict[int, str]

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self.websocket = None
        self.server = None
        self.handles_map: RemoteConnection.HandleMap = self.init_handles_map()
        self.characteristics_map: dict[str, str] = {
            uuid: uuid for uuid in self.handles_map.values()
        }
        self._client_ip: str = ""
        self._handler_task: asyncio.Task | None = None
        self._ble_connected_future: asyncio.Future | None = None
        self._last_payload: str = ""
        self._last_payload_time: float = 0.0

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(self, watch_filter=None) -> str:
        """Wait for Android WebSocket + BLE-ready signal, then return client IP.

        No writes should be attempted before this coroutine returns — the
        BLE-connected future acts as the gate that ensures the watch is ready.
        """
        logger.info(f"Waiting for Android on {self.host}:{self.port}…")

        await self._cancel_stale_handler()

        self._client_ip = ""
        self.websocket = None

        loop = asyncio.get_running_loop()
        ws_connected_future      = loop.create_future()
        self._ble_connected_future = loop.create_future()

        async def handler(websocket, path=""):
            self._client_ip = websocket.remote_address[0]
            self.websocket  = websocket
            logger.info(f"Android connected from {self._client_ip}")

            if not ws_connected_future.done():
                ws_connected_future.set_result(True)

            self._handler_task = asyncio.current_task()
            try:
                await self._listen(websocket)
            except asyncio.CancelledError:
                logger.info("Handler cancelled — new session starting.")
                raise
            except Exception as e:
                logger.error(f"WebSocket handler error: {e}")
            finally:
                self.websocket     = None
                self._handler_task = None
                logger.info("Android client disconnected.")

        # Start the server once; reuse across reconnections
        if self.server is None:
            self.server = await websockets.serve(
                handler,
                self.host,
                self.port,
                reuse_address=True,
                reuse_port=True,
                ping_interval=None,
            )
            logger.info(f"WebSocket server listening on {self.host}:{self.port}")

        # Gate 1: WebSocket handshake
        await ws_connected_future
        logger.info("WebSocket handshake complete.")

        # Gate 2: BLE-ready signal from Android
        logger.info("Waiting for BLE connection signal from Android…")
        try:
            await asyncio.wait_for(
                asyncio.shield(self._ble_connected_future),
                timeout=BLE_CONNECT_TIMEOUT,
            )
            logger.info("BLE ready — proceeding with commands.")
        except TimeoutError:
            logger.warning(
                f"BLE connection signal not received within {BLE_CONNECT_TIMEOUT}s — "
                "proceeding anyway."
            )

        return self._client_ip

    async def disconnect(self) -> None:
        """Shut down the WebSocket server."""
        await self._cancel_stale_handler()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            logger.info("WebSocket server stopped.")

    async def _cancel_stale_handler(self) -> None:
        """Cancel any running handler from a previous session."""
        if self._handler_task and not self._handler_task.done():
            logger.info("Cancelling stale handler from previous session.")
            self._handler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._handler_task
        self._handler_task = None

    # ── Notification listener ─────────────────────────────────────────────────

    async def _listen(self, websocket) -> None:
        """Receive and dispatch all inbound WebSocket messages."""
        try:
            async for raw_message in websocket:
                await self._handle_message(raw_message)
        except (
            websockets.exceptions.ConnectionClosedOK,
            websockets.exceptions.ConnectionClosedError,
        ):
            pass

    async def _handle_message(self, raw: str) -> None:
        """Route a single inbound JSON message."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Malformed JSON from Android: {raw!r}")
            return

        msg_type = data.get("type")

        if msg_type == "connected":
            await self._on_ble_connected(data)

        elif msg_type == "notification":
            self._on_notification(data)

        elif msg_type == "log":
            level = data.get("level", "info").lower()
            msg   = data.get("message", data.get("msg", ""))
            getattr(logger, level, logger.info)(f"[Android] {msg}")

        elif msg_type == "event":
            if (self._ble_connected_future
                    and not self._ble_connected_future.done()):
                self._ble_connected_future.set_result("event")

        else:
            logger.debug(f"Unhandled message type: {msg_type!r}")

    async def _on_ble_connected(self, data: dict) -> None:
        """Handle the BLE-ready signal from Android."""
        try:
            # Android sends address as a JSON-encoded string
            device = json.loads(data["address"])
            name   = device["name"]
            addr   = device["address"]
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            logger.error(f"Malformed 'connected' message: {data} — {e}")
            return

        logger.info(f"BLE connected: {name} ({addr})")
        watch_info.set_name_and_model(name)

        if (self._ble_connected_future
                and not self._ble_connected_future.done()):
            self._ble_connected_future.set_result(addr)

    def _on_notification(self, data: dict) -> None:
        """Deduplicate and dispatch a watch notification to MessageDispatcher."""
        payload = data.get("payload", "")
        if not payload:
            return

        now = asyncio.get_event_loop().time()
        if (payload == self._last_payload
                and (now - self._last_payload_time) < DUPLICATE_THRESHOLD):
            logger.debug(f"Dropping duplicate notification: 0x{payload[:2]}")
            self._last_payload_time = now
            return

        self._last_payload      = payload
        self._last_payload_time = now

        raw = bytes.fromhex(payload)
        logger.debug(f"Notification: {raw.hex()}")
        message_dispatcher.MessageDispatcher.on_received(raw)

    # ── Write interface (matches Connection) ──────────────────────────────────

    async def write(self, handle: int, data: Any) -> None:
        """Send a write command to the Android BLE proxy."""
        if not self.websocket:
            raise GShockConnectionError("No Android client connected")

        if isinstance(data, (bytes, bytearray)):
            payload_hex = data.hex()
        else:
            payload_hex = to_casio_cmd(data).hex()

        message = {
            "type":    "write",
            "handle":  hex(handle),
            "payload": payload_hex,
        }
        logger.debug(f"write → Android: handle={hex(handle)} payload={payload_hex}")
        try:
            await self.websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosedError as e:
            raise GShockConnectionError(f"WebSocket send failed: {e}") from e

    async def request(self, request: T) -> None:
        """Send a read request via the standard read handle (0x0C)."""
        await self.write(READ_HANDLE, request)

    async def send_message(self, message: T) -> None:
        """Dispatch a high-level action message through MessageDispatcher."""
        await message_dispatcher.MessageDispatcher.send_to_watch(message)

    # ── Service support (matches Connection) ──────────────────────────────────

    def is_service_supported(self, handle: int) -> bool:
        """Return True if the handle maps to a known characteristic."""
        uuid = self.handles_map.get(handle)
        return uuid is not None and uuid in self.characteristics_map

    # ── Handles map ───────────────────────────────────────────────────────────

    def init_handles_map(self) -> HandleMap:
        return {
            0x04: CasioConstants.CASIO_GET_DEVICE_NAME,
            0x06: CasioConstants.CASIO_APPEARANCE,
            0x09: CasioConstants.TX_POWER_LEVEL_CHARACTERISTIC_UUID,
            0x0C: CasioConstants.CASIO_READ_REQUEST_FOR_ALL_FEATURES_CHARACTERISTIC_UUID,
            0x0D: CasioConstants.CASIO_NOTIFICATION_CHARACTERISTIC_UUID,
            0x0E: CasioConstants.CASIO_ALL_FEATURES_CHARACTERISTIC_UUID,
            0x11: CasioConstants.CASIO_DATA_REQUEST_SP_CHARACTERISTIC_UUID,
            0x14: CasioConstants.CASIO_CONVOY_CHARACTERISTIC_UUID,
            0x17: CasioConstants.CASIO_SET_CONFIGURATION_CHARACTERISTIC_UUID,
            0x19: CasioConstants.CASIO_GET_CONFIGURATION_CHARACTERISTIC_UUID,
            0xFF: CasioConstants.SERIAL_NUMBER_STRING,
        }