#!/usr/bin/env python3
"""
DW-H5600 LifeLog: download from the watch with the gshock_api library, or replay an HCI (btsnoop) capture.

Everything is in this one file. It uses gshock_api.connection.Connection for the BLE link;
the notification handler is replaced so DRSP/CONVOY/STATUS traffic goes to this file's sync code.

Usage:
    uv run src/examples/h5600_health.py --setup                          # live watch (library scan)
    uv run src/examples/h5600_health.py --setup --address AA:BB:CC:DD:EE:FF
    uv run src/examples/h5600_health.py --hci btsnoop_hci_DW-H5600-4.log  # replay a capture
    options: --quiet, --detailed, --json PATH, --tz N, --set-time

Output: h5600_lifelog.json (or --json PATH), overwritten on every run. It holds all input
(each message as raw hex) and the announcements.

What is decoded, and how far each value can be trusted:
  steps, 5-minute slots (frame 0x50)   confirmed on one full day (sum matched the app)
  header time                          confirmed (stored in UTC; --tz gives local time)
  header steps                         shown only if plausible; check against the app
  energy, 5-minute slots (frame 0x51)  raw values only; kcal scale NOT confirmed
  everything else                      located and sized, NOT decoded
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
from datetime import timezone
from zoneinfo import ZoneInfo
from dataclasses import dataclass, field
import json
from pathlib import Path
import struct
import sys
import time
import traceback

from bleak import BleakClient
from gshock_api.connection import Connection
from gshock_api.scanner import scanner

# ----------------------------------------------------------------------------
# GATT characteristics (UUIDs from gshock_api casio_constants.py)
# ----------------------------------------------------------------------------
UUID_DRSP = "26eb0023-b012-49a8-b1f8-394fb2032b0f"     # index announce / finish / START / END
UUID_CONVOY = "26eb0024-b012-49a8-b1f8-394fb2032b0f"   # poll, setup replies, bulk fragments, acks
UUID_STATUS = "26eb002d-b012-49a8-b1f8-394fb2032b0f"   # status 0x28, and replies to setup requests
SHORT_NAME = {UUID_DRSP: "DRSP", UUID_CONVOY: "CONVOY", UUID_STATUS: "STATUS"}
HANDLE_TO_UUID = {0x0010: UUID_DRSP, 0x0013: UUID_CONVOY, 0x0018: UUID_STATUS}
SETUP_CHAR_UUID = "26eb002c-b012-49a8-b1f8-394fb2032b0f"   # one-byte setup requests (found on DW-H5600)

# One-byte setup requests the official app sends before its first poll (capture -2_1, rows 233-316)
# "working": the sequence that completed the live sync on 2026-11-16 (default).
SETUP_WORKING = [0x23, 0x10, 0x11, 0x3B, 0x3A, 0x26, 0x28, 0x20, 0x2F, 0x43, 0x13, 0x45]
# "documented": the initialisation order from the 3516 handshake documents. Not yet tested on a watch.
SETUP_DOCUMENTED = [0x23, 0x22, 0x10, 0x11, 0x3B, 0x3A, 0x26, 0x28, 0x20, 0x1D, 0x1E, 0x3D]
# Replies the official app writes back unchanged to the status characteristic
ECHO_REPLY_COMMANDS = {0x11, 0x3B, 0x3A, 0x2F, 0x13, 0x45}
SETUP_REPLY_TIMEOUT_S = 1.2

# Sync protocol messages
POLL = bytes.fromhex("000000")
SETUP_1 = bytes.fromhex("04" + "00" * 9)
SETUP_2 = bytes.fromhex("0401180018000000dc05")
SETUP_3 = bytes.fromhex("06" + "00" * 13)
ACK_FRAGMENT = bytes.fromhex("07" + "00" * 14)
START = bytes.fromhex("002effffffffff")
POLL_RETRY_S = 3.5
OVERALL_TIMEOUT_S = 180
FLUSH_EVERY = 20

# Frames
FRAME_ORDER = [0x65, 0x50, 0x51, 0x52, 0x53, 0x56, 0x58, 0x59, 0x5A, 0x5B, 0x63, 0x72]
FRAME_NAME = {0x00: "header", 0x50: "steps", 0x51: "energy", 0x52: "heart rate", 0x53: "sleep",
              0x56: "activity", 0x58: "breath", 0x59: "SpO2", 0x5A: "sleep data",
              0x5B: "cardio load", 0x63: "daily summary", 0x65: "current stats", 0x72: "5-min samples"}
HEADER_MAGIC = b"\x00\x0f\x00\x00\x00"
MAX_STEPS_PER_SLOT = 1000          # a 5-minute slot above this is treated as no data
MAX_ENERGY_RAW_PER_SLOT = 5000     # same for raw energy
MAX_PLAUSIBLE_DAY_STEPS = 100000   # header steps above this are rejected as misread


def resolve_tz(arg: str):
    """Accept an IANA zone name (default America/Toronto, which follows daylight saving) or a fixed
    offset in hours such as -4."""
    if arg.lstrip("+-").isdigit():
        return timezone(dt.timedelta(hours=int(arg)))
    return ZoneInfo(arg)


# ----------------------------------------------------------------------------
# Session document: written to JSON on every run (overwritten, never appended)
# ----------------------------------------------------------------------------
@dataclass
class Session:
    source: str
    path: Path
    started: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    ended: str | None = None
    finished: bool = False
    error: str | None = None
    events: list = field(default_factory=list)
    announcements: list = field(default_factory=list)
    _since_flush: int = 0

    def log(self, direction: str, name: str, data: bytes, handle: int | None = None) -> None:
        self.events.append({"t": round(time.time(), 3), "dir": direction, "uuid": name,
                            "handle": handle, "hex": data.hex()})
        self._since_flush += 1
        if self._since_flush >= FLUSH_EVERY:
            self.save()

    def announce(self, index: int, value: bytes) -> None:
        self.announcements.append({"index": index, "value": value.hex()})

    def to_doc(self) -> dict:
        return {"format": "h5600_lifelog_session", "version": 2, "source": self.source,
                "started": self.started, "ended": self.ended, "finished": self.finished,
                "error": self.error, "events": self.events, "announcements": self.announcements}

    def save(self) -> None:
        self._since_flush = 0
        self.path.write_text(json.dumps(self.to_doc(), indent=2))

    def close(self, finished: bool, error: str | None = None) -> None:
        self.finished = finished
        self.error = error
        self.ended = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self.save()


# ----------------------------------------------------------------------------
# Sync protocol: a state machine with no BLE code
# ----------------------------------------------------------------------------
class LifeLogSync:
    """Feed each notification to on_notify(); it returns the writes to perform as (which, bytes)."""

    def __init__(self) -> None:
        self.phase = "idle"
        self.echo_06 = 0
        self.sent_setup_2 = False
        self.done = False

    def start(self) -> list:
        self.phase = "polling"
        return [("convoy", POLL)]

    def on_notify(self, uuid: str, data: bytes) -> list:
        out: list = []
        if uuid == UUID_CONVOY:
            if self.phase == "polling":
                if data == b"\x00\x00\x00":
                    self.phase = "setup"
                    out.append(("convoy", SETUP_1))
                else:
                    out.append(("convoy", POLL))             # busy: poll again
            elif self.phase == "setup" and data[:1] == b"\x04" and data[1:2] == b"\x00":
                if not self.sent_setup_2:
                    self.sent_setup_2 = True
                    out.append(("convoy", SETUP_2))
                else:
                    out.append(("convoy", SETUP_3))
                    self.phase = "setup_wait"
            elif self.phase == "setup_wait" and data[:1] == b"\x06" and len(data) == 9:
                # the second byte varies between sessions (seen 0xfa and 0x17)
                self.echo_06 += 1
                if self.echo_06 == 1:
                    out.append(("convoy", data))             # echo the watch's 9-byte value
                else:
                    out.append(("drsp", START))
                    self.phase = "transfer"
            elif self.phase == "transfer":
                if data[:1] == b"\x05":
                    out.append(("convoy", ACK_FRAGMENT))
                elif data[:2] == b"\x03\x01":
                    self.phase = "post_end"
                    out.append(("convoy", POLL))
            return out
        if uuid == UUID_DRSP and self.phase == "transfer":
            if len(data) >= 3 and data[:2] in (b"\x00\x2e", b"\x07\x2e"):
                out.append(("drsp", bytes(data)))           # echo index announce / finish verbatim
            elif len(data) >= 2 and data[:2] == b"\x04\x2e":
                self.done = True
                self.phase = "done"
                out.append(("drsp", bytes(data)))           # echo END
        return out


# ----------------------------------------------------------------------------
# Live watch: gshock_api Connection with our own notification routing
# ----------------------------------------------------------------------------
class LifeLogConnection(Connection):
    """gshock_api Connection that sends notifications for DRSP, CONVOY, STATUS to on_message."""

    def __init__(self, address: str | None, on_message) -> None:
        super().__init__(address)
        self._on_message = on_message

    def notification_handler(self, characteristic, data) -> None:   # overrides the library handler
        self._on_message(characteristic.uuid, bytes(data))

    async def connect(self, watch_filter=None, timeout: float | None = None) -> bool:
        if self.address is None:
            device = await scanner.scan(device_address=self.address, watch_filter=watch_filter, timeout=timeout)
            if device is None:
                return False
            self.address = device.address
            await asyncio.sleep(1.0)
        if self.address is None:
            return False

        self.client = BleakClient(self.address)
        await self.client.connect()
        if not self.client.is_connected:
            return False

        await self.init_characteristics_map()
        # Subscribe ONLY to the three characteristics the sync uses. Subscribing to all of them
        # (such as 26EB0030) makes the watch disconnect.
        for uuid in (UUID_DRSP, UUID_CONVOY, UUID_STATUS):
            if uuid in self.characteristics_map:
                try:
                    await self.client.start_notify(uuid, self.notification_handler)
                except Exception:
                    pass
        return True


async def download_live(address: str | None, session: Session, setup: bool, sequence: list) -> None:
    inbox: asyncio.Queue = asyncio.Queue()
    conn = LifeLogConnection(address, lambda uuid, data: inbox.put_nowait((uuid, data)))

    ok = False
    for attempt in range(1, 4):
        ok = await conn.connect(timeout=20.0)
        if ok and conn.client and conn.client.is_connected:
            break
        print(f"Connection attempt {attempt} failed, retrying in 2 seconds...")
        await asyncio.sleep(2.0)
    if not ok or conn.client is None or not conn.client.is_connected:
        raise ConnectionError("could not connect to the watch (awake? bonded? not connected to a phone?)")
    session.source = f"ble:{conn.address}"

    try:
        async def write(which: str, data: bytes) -> None:
            if not conn.client.is_connected:
                raise ConnectionError("the watch disconnected before this write")
            uuid, response = (UUID_DRSP, True) if which == "drsp" else (UUID_CONVOY, False)
            session.log("TX", SHORT_NAME[uuid], data)
            await conn.client.write_gatt_char(uuid, data, response=response)

        print(f"Connected to {conn.address}. Initializing transfer...")
        if setup:
            setup_char = find_setup_characteristic(conn.client.services)
            if setup_char is None:
                print("No setup characteristic found; continuing without setup requests.")
            else:
                print("Executing setup handshake sequence...")
                for cmd in sequence:
                    session.log("TX", "SETUP", bytes([cmd]))
                    try:
                        await conn.client.write_gatt_char(setup_char.uuid, bytes([cmd]), response=False)
                    except Exception as e:
                        print(f"  Setup 0x{cmd:02x} error: {e}")
                        continue
                    reply = await _wait_reply(inbox, cmd, SETUP_REPLY_TIMEOUT_S)
                    if reply is None:
                        print(f"  Setup 0x{cmd:02x} -> no reply")
                        continue
                    session.log("RX", "STATUS", reply)
                    print(f"  Setup 0x{cmd:02x} -> OK")
                    if cmd in ECHO_REPLY_COMMANDS:
                        session.log("TX", "STATUS", reply)
                        try:
                            await conn.client.write_gatt_char(UUID_STATUS, reply, response=True)
                        except Exception:
                            pass

        if setup:
            # The official app writes START before its first poll; the watch acknowledges it on DRSP
            # only after it becomes ready.
            session.log("TX", "DRSP", START)
            await conn.client.write_gatt_char(UUID_DRSP, START, response=True)

        print("Polling watch for LifeLog transfer readiness...")
        sync = LifeLogSync()
        for which, data in sync.start():
            await write(which, data)
        deadline = time.monotonic() + OVERALL_TIMEOUT_S
        while not sync.done:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print("Timed out waiting for the transfer to finish.")
                break
            try:
                uuid, data = await asyncio.wait_for(inbox.get(), timeout=min(remaining, POLL_RETRY_S + 5))
            except TimeoutError:
                if sync.phase == "polling":
                    for which, d in sync.on_notify(UUID_CONVOY, b"\x00\x01\x04"):
                        await write(which, d)
                continue
            session.log("RX", SHORT_NAME.get(uuid, uuid), data)
            if uuid == UUID_DRSP and data[:2] == b"\x00\x2e" and data[2:3] != b"\xff":
                session.announce(data[2], data[3:6])
                size = int.from_bytes(data[3:6], "little")
                print(f"  Receiving {FRAME_NAME.get(data[2], f'tag 0x{data[2]:02x}')} (announced {size} B)...")
            if uuid == UUID_CONVOY and data[:2] == b"\x00\x01":
                print("  Watch busy preparing LifeLog memory; retrying poll in 3.5 s")
                await asyncio.sleep(POLL_RETRY_S)
            for which, d in sync.on_notify(uuid, data):
                await write(which, d)
        session.finished = sync.done
    finally:
        await conn.disconnect()


def find_setup_characteristic(services):
    """The setup requests go to characteristic 26eb002c on the DW-H5600."""
    chars = [c for s in services for c in s.characteristics]
    for c in chars:
        if c.uuid.lower() == SETUP_CHAR_UUID:
            return c
    candidates = [c for c in chars if "write-without-response" in c.properties and c.handle in (0x15, 0x16, 0x17)]
    return candidates[0] if candidates else None


async def _wait_reply(inbox: asyncio.Queue, cmd: int, timeout: float):
    """Wait for a STATUS notification starting with the request byte. Other messages are put back."""
    deadline = time.monotonic() + timeout
    held, found = [], None
    while time.monotonic() < deadline and found is None:
        try:
            uuid, data = await asyncio.wait_for(inbox.get(), timeout=deadline - time.monotonic())
        except TimeoutError:
            break
        if uuid == UUID_STATUS and data[:1] == bytes([cmd]):
            found = data
        else:
            held.append((uuid, data))
    for item in held:
        inbox.put_nowait(item)
    return found


# ----------------------------------------------------------------------------
# HCI (btsnoop) replay: builds the same session from a capture
# ----------------------------------------------------------------------------
def load_hci(path: Path, session: Session) -> None:
    """Keep the one complete LifeLog transfer in a btsnoop capture: the attempt that ends with END
    and carries the most bulk data, plus the setup and poll messages sent just before it."""
    raw = path.read_bytes()
    if raw[:8] != b"btsnoop\x00":
        raise SystemExit(f"{path} is not a btsnoop file")
    session.source = f"hci:{path.name}"
    msgs = []   # (direction, short name, handle, value)
    off = 16
    while off + 24 <= len(raw):
        _olen, ilen, flags, _drops, _ts = struct.unpack(">IIIIq", raw[off:off + 24])
        off += 24
        pkt = raw[off:off + ilen]
        off += ilen
        if not pkt or pkt[0] != 0x02 or len(pkt) < 5:
            continue
        l2len = struct.unpack("<H", pkt[3:5])[0]
        pl = pkt[5:5 + l2len]
        if len(pl) < 5 or struct.unpack("<H", pl[2:4])[0] != 4:
            continue                                     # not ATT
        att = pl[4:]
        if att[0] not in (0x12, 0x52, 0x1B, 0x1D):
            continue
        handle = struct.unpack("<H", att[1:3])[0]
        if handle not in HANDLE_TO_UUID:
            continue
        msgs.append(("TX" if (flags & 1) == 0 else "RX", SHORT_NAME[HANDLE_TO_UUID[handle]], handle, att[3:]))

    starts = [i for i, m in enumerate(msgs) if m[0] == "TX" and m[1] == "DRSP" and m[3][:3] == START[:3]]
    best = None
    for k, st in enumerate(starts):
        stop = starts[k + 1] if k + 1 < len(starts) else len(msgs)
        seg = msgs[st:stop]
        complete = any(m[0] == "RX" and m[1] == "DRSP" and m[3][:2] == b"\x04\x2e" for m in seg)
        bulk = sum(len(m[3]) for m in seg if m[0] == "RX" and m[1] == "CONVOY")
        if complete and (best is None or bulk > best[1]):
            best = (st, bulk, stop)
    if best is None:
        session.error = "no complete LifeLog transfer found in this capture"
        return
    st, _, stop = best
    lo = st
    while lo > 0 and not (msgs[lo - 1][0] == "TX" and msgs[lo - 1][1] == "CONVOY" and msgs[lo - 1][3] == POLL):
        lo -= 1
    for direction, name, handle, value in msgs[lo:stop]:
        session.events.append({"t": None, "dir": direction, "uuid": name, "handle": handle, "hex": value.hex()})
        if direction == "RX" and name == "DRSP" and value[:2] == b"\x00\x2e" and value[2:3] != b"\xff":
            session.announce(value[2], value[3:6])
    session.finished = any(m[0] == "RX" and m[1] == "DRSP" and m[3][:2] == b"\x04\x2e" for m in msgs[st:stop])


# ----------------------------------------------------------------------------
# Decoding
# ----------------------------------------------------------------------------
def stream_from_notifications(notifs: list[bytes]) -> bytes:
    out = bytearray()
    for n in notifs:
        if n[:1] == b"\x05":
            out += n[1:-2]          # drop the 0x05 prefix and the 2-byte checksum
    return bytes(b ^ 0xFF for b in out)


def records4(s: bytes, start: int, end: int):
    body = s[start + 5:end]
    return [struct.unpack_from("<HH", body, i) for i in range(0, len(body) - 3, 4)]


def decode(doc: dict, tz) -> dict:
    notifs = [bytes.fromhex(e["hex"]) for e in doc["events"] if e["dir"] == "RX" and e["uuid"] == "CONVOY"]
    announced: dict[int, int] = {}
    for a in doc["announcements"]:
        announced.setdefault(a["index"], int.from_bytes(bytes.fromhex(a["value"]), "little"))
    s = stream_from_notifications(notifs)
    result: dict = {"header": None, "slots": [], "frames": {}, "steps_by_hour": {}}
    if s[:5] != HEADER_MAGIC:
        result["error"] = "LifeLog header not found in the data"
        return result

    t_utc = dt.datetime(2000 + s[5], s[6], s[7], s[8], s[9], tzinfo=timezone.utc)
    # Steps: u16 at offset 14, valid only when bytes 16-17 are zero (see spec section 5).
    # A non-zero pair there means the header layout differs; the value is then not reported.
    steps_raw = struct.unpack_from("<H", s, 14)[0] if s[16:18] == b"\x00\x00" else None
    result["header"] = {
        "time_utc": t_utc.replace(tzinfo=None).isoformat(timespec="minutes"),
        "time_local": t_utc.astimezone(tz).replace(tzinfo=None).isoformat(timespec="minutes"),
        "steps": steps_raw if steps_raw is not None and steps_raw <= MAX_PLAUSIBLE_DAY_STEPS else None,
        "energy_raw": struct.unpack_from("<H", s, 18)[0],
    }

    spans, pos = {}, 20
    for t in FRAME_ORDER:
        if t not in announced:
            continue
        p = s.find(bytes([t]) + struct.pack("<i", announced[t]), pos)
        if p >= 0:
            spans[t] = p
            pos = p + 5
    order = sorted(spans.items(), key=lambda kv: kv[1])
    ends = {t: (order[i + 1][1] if i + 1 < len(order) else len(s)) for i, (t, _) in enumerate(order)}
    for t, p in spans.items():
        size = ends[t] - p
        result["frames"][t] = {"name": FRAME_NAME.get(t, "?"), "start": p,
                               "bytes_received": size, "preview_hex": s[p:p + min(size, 16)].hex(" ")}

    if 0x50 in spans and 0x51 in spans:
        steps = records4(s, spans[0x50], ends[0x50])
        energy = records4(s, spans[0x51], ends[0x51])
        for i in range(min(len(steps), len(energy))):
            st, sf = steps[i]
            en, _ = energy[i]
            if st > MAX_STEPS_PER_SLOT:
                continue
            slot_t = (t_utc - dt.timedelta(minutes=5 * i)).astimezone(tz).replace(tzinfo=None)
            result["slots"].append({
                "slot": i, "time_local": slot_t.isoformat(timespec="minutes"),
                "steps": st, "steps_flag": f"0x{sf:04x}",
                "energy_raw": en if en <= MAX_ENERGY_RAW_PER_SLOT else None,
            })
    for r in result["slots"]:
        hour = r["time_local"][11:13]
        result["steps_by_hour"][hour] = result["steps_by_hour"].get(hour, 0) + r["steps"]

    # Heart rate. Daily max/min/resting: 16-bit little-endian at bytes 88, 90, 92 of the current-stats
    # frame (layout from parse_lifelog.py; 0xFEFF = not available). Matched the watch on 2026-11-16.
    if 0x65 in spans:
        body65 = s[spans[0x65] + 5:ends[0x65]]

        def hr_at(off: int):
            if len(body65) < off + 2:
                return None
            v = struct.unpack_from("<H", body65, off)[0]
            return v if 30 <= v <= 220 else None

        result["hr_day"] = {"max": hr_at(88), "min": hr_at(90), "resting": hr_at(92)}

    # Recent heart-rate samples: frame 0x52, 4-byte records, first byte = bpm (0xFE = none).
    if 0x52 in spans:
        body52 = s[spans[0x52] + 5:ends[0x52]]
        vals = [body52[i] for i in range(0, len(body52) - 3, 4) if 30 <= body52[i] <= 220]
        if vals:
            result["hr_recent"] = {"count": len(vals), "min": min(vals), "max": max(vals),
                                   "avg": round(sum(vals) / len(vals))}
    return result


# ----------------------------------------------------------------------------
# Screen output
# ----------------------------------------------------------------------------
def rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def _row(label: str, value: str) -> None:
    print(f"  {label:<18}{value}")


def _is_recent_only(dec: dict, doc: dict) -> bool:
    """True when the step frame holds only a few slots, i.e. this sync brought only new data."""
    return len(dec.get("slots", [])) < 24


def show(doc: dict, dec: dict, detailed: bool = False) -> None:
    hdr = dec.get("header")
    if not hdr:
        print(f"\nNo LifeLog data: {dec.get('error', 'LifeLog header not found')}")
        return

    date_str = hdr["time_local"][:10]
    recent = _is_recent_only(dec, doc)
    slots = dec.get("slots", [])
    slot_sum = sum(s["steps"] for s in slots)

    print()
    print(f"LifeLog sync  ·  CASIO DW-H5600  ·  {date_str}")
    print("=" * 60)
    _row("Synced at", f"{hdr['time_local'][11:16]} local")
    _row("Transfer", "completed" if doc.get("finished") else "incomplete")
    status = [e["hex"] for e in doc.get("events", []) if e.get("dir") == "RX" and e.get("uuid") == "STATUS"
              and e.get("hex", "").startswith("28")]
    if status:
        b = bytes.fromhex(status[-1])
        if len(b) >= 10:
            _row("Watch status", "LifeLog up to date" if b[9] == 0 else "new LifeLog waiting")

    rule("Steps")
    if hdr["steps"] is not None:
        _row("Today (watch)", f"{hdr['steps']:,} steps")
    else:
        _row("Today (watch)", "not available")
    if recent:
        _row("Recent intervals", f"{len(slots)} five-minute slots, {slot_sum:,} steps")
        print("  This sync brought only recent data, so the slots don't cover the whole day.")
    elif slots:
        _row("Five-minute slots", f"{len(slots)} with data, {slot_sum:,} steps")
        if hdr["steps"] is not None and hdr["steps"] != slot_sum:
            print("  The slots and the watch total differ; the slots may not cover the full day.")
    if slots and slot_sum > 0:
        print()
        print("  By hour")
        top = max(dec["steps_by_hour"].values()) or 1
        for hour in sorted(dec["steps_by_hour"]):
            n = dec["steps_by_hour"][hour]
            if n == 0:
                continue
            bar = "█" * max(1, round(20 * n / top))
            print(f"    {hour}:00  {bar:<20} {n:>6,}")

    rule("Energy")
    raw_hdr = hdr["energy_raw"]
    _row("Today (watch)", f"{raw_hdr:,} raw units")
    print("  The conversion to kcal is not confirmed yet, so no kcal figure is shown.")

    rule("Heart rate")
    hd = dec.get("hr_day") or {}
    hr_recent = dec.get("hr_recent")
    if hd.get("max") is not None and hd.get("min") is not None:
        _row("Max / min", f"{hd['max']} / {hd['min']} bpm  (watch daily values; checked on one day)")
    elif hd:
        _row("Max / min", "not available in this sync")
    if hd.get("resting") is not None:
        _row("Resting", f"{hd['resting']} bpm  (watch daily value; not yet checked)")
    if hr_recent:
        _row("Recent samples", f"{hr_recent['count']} readings, {hr_recent['min']}-{hr_recent['max']} bpm, "
                               f"average {hr_recent['avg']} (last few minutes only)")
    if not hd and not hr_recent:
        _row("Heart rate", "no data in this sync")
    print("  No day average is shown: its field has not been located yet.")

    rule("On the watch, not decoded yet")
    names = [(0x53, "Sleep stages"), (0x56, "Activity"), (0x58, "Breathing"),
             (0x59, "SpO2"), (0x5A, "Sleep data"), (0x5B, "Cardio load"), (0x63, "Daily summary"),
             (0x72, "5-minute samples")]
    for tag, label in names:
        f = dec["frames"].get(tag)
        if f:
            _row(label, f"{f['bytes_received']:,} bytes")
        else:
            _row(label, "none in this sync")

    if detailed:
        rule("Five-minute slots")
        print(f"  {'time':<8}{'steps':>7}{'energy raw':>13}")
        for s in slots:
            en = "-" if s["energy_raw"] is None else f"{s['energy_raw']:,}"
            print(f"  {s['time_local'][11:16]:<8}{s['steps']:>7}{en:>13}")
        rule("Frames")
        for tag, f in sorted(dec["frames"].items()):
            print(f"  0x{tag:02x}  {f['name']:<16} {f['bytes_received']:>7,} bytes   {f['preview_hex']}")
    else:
        print("\n  Run with --detailed for the slot table and frame details.")


def export_health(doc: dict, dec: dict, path: Path) -> None:
    """Write the data that is reliable enough to import, plus a list of what is not available.

    Health Connect needs a time interval and a unit for each record. Steps can be written once the
    day total is confirmed. Energy, heart rate, and sleep cannot be written yet, so they are listed
    under not_available rather than exported with a guessed unit.
    """
    hdr = dec.get("header")
    if not hdr:
        return
    date_str = hdr["time_local"][:10]
    local_midnight = f"{date_str}T00:00:00"
    recent = _is_recent_only(dec, doc)
    slots = dec.get("slots", [])
    out = {
        "schema": "dw_h5600_export/1",
        "device": {"model": "CASIO DW-H5600", "address": doc.get("source", "").replace("ble:", "")},
        "synced_at_local": hdr["time_local"],
        "synced_at_utc": hdr["time_utc"],
        "day": date_str,
        "steps": None,
        "steps_recent_slots": [],
        "energy": {"status": "raw_only", "raw_units": hdr["energy_raw"], "kcal": None},
        "not_available": ["sleep", "spo2", "active_calories", "breathing", "cardio_load"],
        "heart_rate": None,
    }
    hd = dec.get("hr_day") or {}
    if hd.get("max") is not None and hd.get("min") is not None:
        out["heart_rate"] = {
            "max_bpm": hd["max"], "min_bpm": hd["min"], "resting_bpm": hd.get("resting"),
            "status": "watch_reported; max and min checked against the watch on 2026-11-16 (one day)",
            "scope": "current-stats frame of this sync",
        }
    else:
        out["not_available"].insert(0, "heart_rate")
    if hdr["steps"] is not None and not recent:
        out["steps"] = {
            "count": hdr["steps"],
            "start": local_midnight,
            "end": hdr["time_local"],
            "status": "unverified",
            "replace_on_sync": True,
            "confidence": "watch header; matched the app on 2026-10-26 and the watch on 2026-11-16; "
                          "check against the app on each new day before importing",
        }
    for s in slots:
        out["steps_recent_slots"].append({
            "start": s["time_local"],
            "count": s["steps"],
            "minutes": 5,
        })
    path.write_text(json.dumps(out, indent=2))


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DW-H5600 LifeLog download and decode (gshock_api)")
    p.add_argument("--address", help="BLE address of the watch (omit to let gshock_api scan)")
    p.add_argument("--hci", type=Path, help="btsnoop HCI log to replay instead of a live watch")
    p.add_argument("--json", type=Path, default=Path("h5600_lifelog.json"), help="output JSON (overwritten)")
    p.add_argument("--tz", type=str, default="America/Toronto",
                   help="time zone: an IANA name (default America/Toronto, follows daylight saving) or an offset in hours")
    p.add_argument("--quiet", action="store_true", help="no screen output")
    p.add_argument("--detailed", action="store_true", help="print the slot table and frame previews")
    p.add_argument("--export", type=Path, help="also write a JSON file for the Android health app")
    p.add_argument("--setup", action="store_true", help="send the setup requests before polling (needed for a live sync)")
    p.add_argument("--setup-sequence", choices=["working", "documented"], default="working",
                   help="setup commands: 'working' (default, completed a sync) or 'documented' (untested)")
    return p.parse_args(argv)


async def main_async(args: argparse.Namespace) -> int:
    if args.hci:
        if not args.hci.exists():
            print(f"Error: capture file not found: {args.hci}", file=sys.stderr)
            return 1
        session = Session(source=f"hci:{args.hci.name}", path=args.json)
        load_hci(args.hci, session)
        session.close(finished=session.finished, error=session.error)
    else:
        session = Session(source="ble", path=args.json)
        session.save()
        try:
            seq = SETUP_WORKING if args.setup_sequence == "working" else SETUP_DOCUMENTED
            await download_live(args.address, session, setup=args.setup, sequence=seq)
            session.close(finished=session.finished)
        except (KeyboardInterrupt, asyncio.CancelledError):
            session.close(finished=False, error="interrupted")
            raise
        except BaseException as exc:
            traceback.print_exc()
            session.close(finished=False, error=f"{type(exc).__name__}: {exc}")
            return 1

    doc = session.to_doc()
    dec = decode(doc, resolve_tz(args.tz))
    if not args.quiet:
        show(doc, dec, detailed=args.detailed)
    if args.export:
        export_health(doc, dec, args.export)
        print(f"Health export written to {args.export}")
    print(f"Session JSON written to {args.json}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(main_async(parse_args(sys.argv[1:] if argv is None else argv)))


if __name__ == "__main__":
    raise SystemExit(main())
