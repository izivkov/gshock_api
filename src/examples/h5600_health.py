#!/usr/bin/env python3
"""
DW-H5600 LifeLog: download from the watch with the gshock_api library, or replay an HCI (btsnoop) capture.

Everything is in this one file. It uses gshock_api.connection.Connection for the BLE link;
the notification handler is replaced so DRSP/CONVOY traffic goes to this file's sync code,
not to the ABL-100 step counter code.

Usage:
    uv run src/examples/h5600_health.py --address AA:BB:CC:DD:EE:FF      # live watch
    uv run src/examples/h5600_health.py                                  # live watch, library scan
    uv run src/examples/h5600_health.py --hci btsnoop_hci_DW-H5600-4.log # replay a capture
    add --quiet to suppress screen output

Output: h5600_lifelog.json (or --json PATH), overwritten on every run. It holds all input
(each message as raw hex) and the announcements. Decoded values are printed on screen.

Decoding status (also printed on screen):
  header time, steps, energy (raw)   confirmed on one day against the app
  step slots (0x50)                  confirmed: the valid slots sum to the app total
  energy slots (0x51)                raw values only; kcal scale NOT confirmed
  other frames                       located, not decoded
Time zone is an assumption (--tz, default -4 = Toronto, late October).
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import struct
import sys
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from gshock_api.connection import Connection

# ----------------------------------------------------------------------------
# GATT characteristics (UUIDs from gshock_api casio_constants.py)
# ----------------------------------------------------------------------------
UUID_DRSP = "26eb0023-b012-49a8-b1f8-394fb2032b0f"     # index announce / finish / START / END
UUID_CONVOY = "26eb0024-b012-49a8-b1f8-394fb2032b0f"   # poll, setup, bulk fragments, acks
UUID_STATUS = "26eb002d-b012-49a8-b1f8-394fb2032b0f"   # status 0x28, and replies to setup requests
UUID_SETUP = "26eb002e-b012-49a8-b1f8-394fb2032b0f"    # GW-BX5600 setup request; not present on the DW-H5600

SHORT_NAME = {UUID_DRSP: "DRSP", UUID_CONVOY: "CONVOY", UUID_STATUS: "STATUS"}
HANDLE_TO_UUID = {0x0010: UUID_DRSP, 0x0013: UUID_CONVOY, 0x0018: UUID_STATUS}

# One-byte setup requests the official app sends before its first poll (capture -2, rows 233-259).
# The write target is found on the watch by find_setup_characteristic(); UUID_SETUP is not used.
# Capture -2_1 rows 233-316: the app also sends 2f, 43, 13, 45 before the poll becomes ready.
SETUP_COMMANDS = [0x23, 0x10, 0x11, 0x3B, 0x3A, 0x26, 0x28, 0x20, 0x2F, 0x43, 0x13, 0x45]
SETUP_REPLY_TIMEOUT_S = 5.0
def time_message(now: dt.datetime) -> bytes:
    """Date-and-time write (command 0x09), from capture -2 rows 231/284.

    Layout inferred from the capture: 09, year (u16 LE), month, day, hour, minute, second, weekday
    (Sunday = 0; 2026-08-29 is a Saturday and the capture shows 06). The last two bytes vary in the
    capture and are not understood; they are sent as 00 00 here.
    """
    weekday = (now.weekday() + 1) % 7
    return (b"\x09" + struct.pack("<H", now.year)
            + bytes([now.month, now.day, now.hour, now.minute, now.second, weekday]) + b"\x00\x00")


# Replies the official app writes back unchanged to the status characteristic (capture -2, rows 240-259)
ECHO_REPLY_COMMANDS = {0x11, 0x3B, 0x3A, 0x2F, 0x13, 0x45}

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
MAX_STEPS_PER_SLOT = 1000
MAX_ENERGY_RAW_PER_SLOT = 5000


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

    def log(self, direction: str, name: str, data: bytes, handle: int | None = None, echo: bool = True) -> None:
        self.events.append({"t": round(time.time(), 3), "dir": direction, "uuid": name,
                            "handle": handle, "hex": data.hex()})
        if echo:
            print(f"  {direction:2} {name:7} {data.hex(' ')[:60]}", flush=True)
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
                # the second byte varies between sessions (seen 0xfa and 0x17); echo the first reply
                # verbatim, then start the transfer on the second
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
    """gshock_api Connection that sends every notification to on_message instead of the ABL-100 handlers."""

    def __init__(self, address: str | None, on_message) -> None:
        super().__init__(address)
        self._on_message = on_message

    def notification_handler(self, characteristic, data) -> None:   # overrides the library handler
        self._on_message(characteristic.uuid, bytes(data))


async def download_live(address: str | None, session: Session, setup: bool, set_time: bool) -> None:
    inbox: asyncio.Queue = asyncio.Queue()
    conn = LifeLogConnection(address, lambda uuid, data: inbox.put_nowait((uuid, data)))

    print("connecting ...", flush=True)
    ok = await conn.connect(timeout=20.0)
    if not ok or conn.client is None or not conn.client.is_connected:
        raise ConnectionError("could not connect to the watch (is it awake and not connected to a phone?)")
    address = conn.address
    session.source = f"ble:{address}"
    print(f"connected to {address}", flush=True)

    try:
        # gshock_api.connect() has already subscribed to every notifiable characteristic,
        # and our notification_handler receives all of them. Nothing else is done here.

        async def write(which: str, data: bytes) -> None:
            if not conn.client.is_connected:
                raise ConnectionError("the watch disconnected before this write")
            uuid, response = (UUID_DRSP, True) if which == "drsp" else (UUID_CONVOY, False)
            session.log("TX", SHORT_NAME[uuid], data)
            await conn.client.write_gatt_char(uuid, data, response=response)

        if setup:
            setup_char = find_setup_characteristic(conn.client.services)
            if setup_char is None:
                print("no setup characteristic found; skipping setup requests", flush=True)
            else:
                print(f"setup requests -> {setup_char.uuid} (handle {setup_char.handle:#06x})", flush=True)
                for cmd in SETUP_COMMANDS:
                    session.log("TX", "SETUP", bytes([cmd]))
                    await conn.client.write_gatt_char(setup_char.uuid, bytes([cmd]), response=False)
                    reply = await _wait_reply(inbox, cmd, SETUP_REPLY_TIMEOUT_S)
                    if reply is None:
                        print(f"   no reply to setup request 0x{cmd:02x} (continuing)", flush=True)
                    else:
                        session.log("RX", "STATUS", reply)
                        if cmd in ECHO_REPLY_COMMANDS:
                            # the official app writes these replies back to the status characteristic
                            session.log("TX", "STATUS", reply)
                            await conn.client.write_gatt_char(UUID_STATUS, reply, response=True)

        if set_time:
            msg = time_message(dt.datetime.now())
            print(f"setting the watch clock: {msg.hex(' ')}  ({dt.datetime.now().isoformat(timespec='seconds')})", flush=True)
            session.log("TX", "STATUS", msg)
            await conn.client.write_gatt_char(UUID_STATUS, msg, response=True)
            reply = await _wait_reply(inbox, 0x09, SETUP_REPLY_TIMEOUT_S)
            print("   no reply to the time write" if reply is None else f"   time reply: {reply.hex(' ')}", flush=True)
            if reply is not None:
                session.log("RX", "STATUS", reply)

        if setup:
            # The official app writes START before its first poll (capture -2_1 row 300). The watch
            # acknowledges it on DRSP only after it becomes ready, so this write is sent first.
            session.log("TX", "DRSP", START)
            await conn.client.write_gatt_char(UUID_DRSP, START, response=True)

        sync = LifeLogSync()
        for which, data in sync.start():
            await write(which, data)
        deadline = time.monotonic() + OVERALL_TIMEOUT_S
        while not sync.done:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print("timeout: the transfer did not finish; partial data is saved", flush=True)
                break
            try:
                uuid, data = await asyncio.wait_for(inbox.get(), timeout=min(remaining, POLL_RETRY_S + 5))
            except asyncio.TimeoutError:
                if sync.phase == "polling":
                    for which, d in sync.on_notify(UUID_CONVOY, b"\x00\x01\x04"):
                        await write(which, d)
                continue
            name = SHORT_NAME.get(uuid, uuid)
            session.log("RX", name, data)
            if uuid == UUID_DRSP and data[:2] == b"\x00\x2e" and data[2:3] != b"\xff":
                session.announce(data[2], data[3:6])
            if uuid == UUID_CONVOY and data[:2] == b"\x00\x01":
                # busy: the official app waits about 3.5 s before polling again
                await asyncio.sleep(POLL_RETRY_S)
            for which, d in sync.on_notify(uuid, data):
                await write(which, d)
        session.finished = sync.done
    finally:
        await conn.disconnect()


def find_setup_characteristic(services):
    """The setup requests use a write-without-response characteristic near handle 0x16 (capture -2).

    The UUID differs between models, so the handle and property decide the choice.
    """
    chars = [c for s in services for c in s.characteristics]
    candidates = [c for c in chars if "write-without-response" in c.properties and c.handle in (0x15, 0x16, 0x17)]
    if not candidates:
        candidates = [c for c in chars if "write-without-response" in c.properties and c.uuid != UUID_CONVOY]
    return candidates[0] if candidates else None


async def _wait_reply(inbox: asyncio.Queue, cmd: int, timeout: float):
    """Wait for a STATUS notification starting with the request byte. Other messages are put back."""
    deadline = time.monotonic() + timeout
    held, found = [], None
    while time.monotonic() < deadline and found is None:
        try:
            uuid, data = await asyncio.wait_for(inbox.get(), timeout=deadline - time.monotonic())
        except asyncio.TimeoutError:
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
    """Read a btsnoop capture and keep the one complete LifeLog transfer in it.

    A capture can hold several sync attempts. Each starts with a START write (00 2e ff..).
    A complete attempt ends with the watch's END (04 2e ff..). The attempt with the most bulk
    data is kept, together with the setup and poll messages sent just before it.
    """
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
        uuid = HANDLE_TO_UUID[handle]
        msgs.append(("TX" if (flags & 1) == 0 else "RX", SHORT_NAME[uuid], handle, att[3:]))

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
# Decoding (partial)
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


def decode(doc: dict, tz_offset_h: int) -> dict:
    notifs = [bytes.fromhex(e["hex"]) for e in doc["events"] if e["dir"] == "RX" and e["uuid"] == "CONVOY"]
    announced: dict[int, int] = {}
    for a in doc["announcements"]:
        announced.setdefault(a["index"], int.from_bytes(bytes.fromhex(a["value"]), "little"))
    s = stream_from_notifications(notifs)
    result: dict = {"header": None, "slots": [], "frames": {}, "steps_by_hour": {}}
    if s[:5] != HEADER_MAGIC:
        result["error"] = "LifeLog header not found in the data"
        return result
    y, mo, d, h, mi = s[5], s[6], s[7], s[8], s[9]
    t_utc = dt.datetime(2000 + y, mo, d, h, mi)
    result["header"] = {
        "time_utc": t_utc.isoformat(timespec="minutes"),
        "time_local": (t_utc + dt.timedelta(hours=tz_offset_h)).isoformat(timespec="minutes"),
        "steps": struct.unpack_from("<i", s, 14)[0],
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
        result["frames"][t] = {"name": FRAME_NAME.get(t, "?"), "start": p, "bytes_received": ends[t] - p}

    if 0x50 in spans and 0x51 in spans:
        steps = records4(s, spans[0x50], ends[0x50])
        energy = records4(s, spans[0x51], ends[0x51])
        for i in range(min(len(steps), len(energy))):
            st, sf = steps[i]
            en, _ = energy[i]
            if st > MAX_STEPS_PER_SLOT:
                continue
            slot_t = t_utc + dt.timedelta(hours=tz_offset_h) - dt.timedelta(minutes=5 * i)
            result["slots"].append({
                "slot": i, "time_local": slot_t.isoformat(timespec="minutes"),
                "steps": st, "steps_flag": f"0x{sf:04x}",
                "energy_raw": en if en <= MAX_ENERGY_RAW_PER_SLOT else None,
            })
    for r in result["slots"]:
        hour = r["time_local"][11:13]
        result["steps_by_hour"][hour] = result["steps_by_hour"].get(hour, 0) + r["steps"]
    return result


# ----------------------------------------------------------------------------
# Screen output
# ----------------------------------------------------------------------------
def show(doc: dict, dec: dict) -> None:
    def rule(title: str) -> None:
        print(f"\n== {title} " + "=" * max(0, 60 - len(title)))

    rule("Session")
    print(f"  source    {doc['source']}")
    print(f"  started   {doc['started']}")
    print(f"  ended     {doc['ended']}")
    print(f"  finished  {doc['finished']}")
    if doc.get("error"):
        print(f"  error     {doc['error']}")

    rule(f"Messages ({len(doc['events'])})")
    for (direction, name), n in sorted(Counter((e["dir"], e["uuid"]) for e in doc["events"]).items()):
        print(f"  {direction:3} {name:8} {n}")

    rule("Announced frames")
    for a in doc["announcements"]:
        val = int.from_bytes(bytes.fromhex(a["value"]), "little")
        print(f"  0x{a['index']:02x}  {FRAME_NAME.get(a['index'], '?'):16} announced {val:>6} bytes")

    rule("Status 0x28 (last 3)")
    status = [e["hex"] for e in doc["events"] if e["dir"] == "RX" and e["uuid"] == "STATUS" and e["hex"][:2] == "28"]
    if not status:
        print("  none in this session")
    for hx in status[-3:]:
        b = bytes.fromhex(hx)
        if len(b) >= 10:
            print(f"  {' '.join(f'{x:02x}' for x in b)}   byte8={b[8]} byte9={b[9]}")

    rule("Decoded (partial)")
    hdr = dec.get("header")
    if hdr is None:
        print(f"  {dec.get('error', 'no data')}")
        return
    print(f"  header time (stored, UTC)  {hdr['time_utc']}")
    print(f"  header time (local)        {hdr['time_local']}")
    print(f"  header steps               {hdr['steps']}")
    print(f"  header energy (raw)        {hdr['energy_raw']}")
    total = sum(s["steps"] for s in dec["slots"])
    print(f"  step slots                 {len(dec['slots'])}   sum {total}")
    if dec["steps_by_hour"]:
        print("  steps by local hour        " + ", ".join(f"{h}:00={v}" for h, v in sorted(dec["steps_by_hour"].items())))

    rule("Frames located")
    for t, f in sorted(dec["frames"].items()):
        print(f"  0x{t:02x}  {f['name']:16} at byte {f['start']:6}  bytes received {f['bytes_received']}")
    print("\n  energy: raw values only (kcal scale not confirmed). Other frames: not decoded.")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DW-H5600 LifeLog download and decode (gshock_api)")
    p.add_argument("--address", help="BLE address of the watch (omit to let gshock_api scan)")
    p.add_argument("--hci", type=Path, help="btsnoop HCI log to replay instead of a live watch")
    p.add_argument("--json", type=Path, default=Path("h5600_lifelog.json"), help="output JSON (overwritten)")
    p.add_argument("--tz", type=int, default=-4, help="local time offset in hours (default -4)")
    p.add_argument("--quiet", action="store_true", help="no screen output")
    p.add_argument("--set-time", action="store_true",
                   help="set the watch clock to this computer's time before polling (needs --setup)")
    p.add_argument("--setup", action="store_true",
                   help="send the one-byte setup requests before polling (off by default; the setup UUID is unverified)")
    return p.parse_args(argv)


async def main_async(args: argparse.Namespace) -> int:
    if args.hci:
        session = Session(source=f"hci:{args.hci.name}", path=args.json)
        load_hci(args.hci, session)
        session.close(finished=session.finished, error=session.error)
    else:
        session = Session(source="ble", path=args.json)
        session.save()
        try:
            await download_live(args.address, session, setup=args.setup, set_time=args.set_time)
            session.close(finished=session.finished)
        except (KeyboardInterrupt, asyncio.CancelledError):
            session.close(finished=False, error="interrupted")
            raise
        except BaseException as exc:
            traceback.print_exc()
            session.close(finished=False, error=f"{type(exc).__name__}: {exc}")
            return 1
    doc = session.to_doc()
    dec = decode(doc, args.tz)
    if not args.quiet:
        show(doc, dec)
    print(f"\nJSON written to {args.json} (overwritten on each run)")
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(main_async(parse_args(sys.argv[1:] if argv is None else argv)))


if __name__ == "__main__":
    raise SystemExit(main())