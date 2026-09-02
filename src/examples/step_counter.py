import asyncio
import argparse
import logging
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gshock_api.connection import Connection
from gshock_api.exceptions import GShockConnectionError
from gshock_api.gshock_api import GshockAPI
from gshock_api.iolib.step_counter_io import StepCounterIOFunctional
from gshock_api.logger import logger
from gshock_api.model.step_counter_data import StepCounterData


def _extract_step_payload_from_hci(hci_path: str | Path) -> bytes | None:
    """Return the parsed step-record payload from a BTSnoop HCI log.

    The watch usually emits one or more notifications on handle 0x0014. We look for the
    actual step payload, skip leading status bytes, and keep the raw bytes beginning at the
    0x26 life-log marker so the normal parser can decode them.
    """
    path = Path(hci_path)
    candidates = [path]
    if not path.is_absolute():
        candidates.append(Path(__file__).resolve().parents[2] / path)
        candidates.append(Path.cwd() / path)

    for candidate in candidates:
        if candidate.exists():
            path = candidate
            break
    else:
        raise FileNotFoundError(f"HCI log not found: {path}")

    pattern = re.compile(r"Notify Handle: 0x0014 Value:\s*([0-9A-Fa-f]+)")
    # Collect all parseable payload candidates and return the longest one.
    # Rationale: BTSnoop logs and pasted HCI text can contain many fragments
    # (short partial notifications, retransmits, or unrelated handles). Picking
    # the first parseable candidate risks choosing a truncated fragment. The
    # longest successfully-parsed payload is most likely the complete record
    # with full history and a valid timestamp.
    candidates_found: list[bytes] = []
    for line in path.read_text(errors="replace").splitlines():
        match = pattern.search(line)
        if not match:
            continue

        raw = bytes.fromhex(match.group(1))
        if not raw:
            continue

        start = raw.find(b"\x26")
        if start == -1:
            continue

        payload = raw[start:]
        if StepCounterIOFunctional.parse(payload) is not None:
            candidates_found.append(payload)

    if not candidates_found:
        return None

    # Prefer the longest parsed payload
    candidates_found.sort(key=len, reverse=True)
    logger.info(f"Selected HCI payload from file: {len(candidates_found[0])}B")
    return candidates_found[0]

    return None


async def _fetch_steps(
    api: GshockAPI | None,
    *,
    use_summary: bool = False,
    peek: bool = False,
    print_log: bool,
    permissive: bool = False,
    show_raw: bool = False,
    step_data: StepCounterData | None = None,
    strict: bool = False,
) -> None:
    """Fetch the current step-counter payload and optionally print a summary."""
    if step_data is None:
        assert api is not None
        if use_summary:
            total_steps = await api.get_step_summary()
            # Build a minimal StepCounterData instance that works whether the
            # model exposes `timestamp` or separate `month/day_of_month` fields.
            step_data = StepCounterData()
            # populate current_day_steps safely
            try:
                step_data.current_day_steps = total_steps
            except Exception:
                setattr(step_data, "current_day_steps", total_steps)
        else:
            # Prefer explicit history API when requested; otherwise honor peek
            if not peek:
                step_data = await api.get_step_history()
            else:
                step_data = await api.get_step_count(peek=peek)

    total_steps = step_data.current_day_steps if step_data.current_day_steps is not None else 0

    # Strict mode: if timestamp decoding failed or timestamp-related warnings
    # are present, fail loudly and dump the raw payload to a .hex file for
    # postmortem analysis. This makes the behavior deterministic for tests
    # and debugging workflows.
    if strict:
        bad_ts = False
        if not hasattr(step_data, "timestamp") or getattr(step_data, "timestamp") is None:
            bad_ts = True
        if any("timestamp" in (w or "") or "too short" in (w or "") for w in (step_data.warnings or [])):
            bad_ts = True
        if bad_ts:
            # Dump raw payload for inspection
            try:
                from datetime import datetime as _dt

                fn = f"failed_step_payload_{_dt.now():%Y%m%d_%H%M%S}.hex"
                with open(fn, "w") as f:
                    f.write(step_data.raw.hex() if step_data.raw else "")
                logger.error(f"Strict mode: timestamp invalid — dumped payload to {fn}")
            except Exception as e:
                logger.error(f"Strict mode: failed to dump payload: {e}")
            raise ValueError("Strict mode: invalid or missing timestamp in parsed step data")
    logger.info(f"Total steps: {total_steps}")
    # Use friendly pre-computed representations when available
    logger.info(
        f"Hourly samples: {len(step_data.hourly_intervals) or len(step_data.hourly_steps)} | "
        f"Daily history samples: {len(step_data.daily_history_list) or len(step_data.daily_history)}"
    )

    if step_data.warnings:
        logger.warning(f"Step parser warnings: {step_data.warnings}")

    if not print_log:
        return

    print(f"current_day_steps={total_steps}")
    # Print timestamp if the model provides it, else fall back to legacy fields
    if hasattr(step_data, "timestamp") and getattr(step_data, "timestamp"):
        ts = getattr(step_data, "timestamp")
        try:
            print(f"timestamp={ts.isoformat()}")
        except Exception:
            print(f"timestamp={ts}")
    else:
        print("timestamp=None")
    print(f"distance_meters={step_data.distance_meters}")
    print(f"pending_distance_meters={step_data.pending_distance_meters}")
    print(f"total_distance_meters={step_data.total_distance_meters}")
    print(f"bcd_total_steps={step_data.bcd_total_steps}")
    # Print hourly aggregates (24 values) when available
    print("hourly_by_hour=")
    if permissive:
        # Compute permissive aggregation (treat None as 0)
        permissive_hours: list[int] = []
        for h in range(24):
            slots = step_data.hourly_steps[h * 6 : h * 6 + 6]
            permissive_hours.append(sum((s or 0) for s in slots))
        hours_to_print = permissive_hours
    else:
        hours_to_print = step_data.hourly_by_hour

    if hours_to_print:
        for idx in range(0, len(hours_to_print), 6):
            chunk = hours_to_print[idx:idx + 6]
            print(f"  [{idx:02d}-{min(idx + 5, 23):02d}] {chunk}")
    else:
        # Fallback to raw 10-minute slots grouped for readability
        for idx in range(0, len(step_data.hourly_steps), 12):
            print(f"  [{idx:03d}-{min(idx + 11, 143):03d}] {step_data.hourly_steps[idx:idx + 12]}")

    # Optional: show first 24 10-minute intervals
    if step_data.hourly_intervals:
        print("hourly_intervals (first 24):")
        for interval in step_data.hourly_intervals[:24]:
            print(f"  idx={interval['index']:03d} {interval['start_minute']:03d}-{interval['end_minute']:03d} steps={interval['steps']}")
    if show_raw and step_data.raw:
        print("raw_payload=", step_data.raw.hex())
    print("daily_history=")
    if step_data.daily_history_list:
        # Print as days_ago -> steps
        for chunk_start in range(0, len(step_data.daily_history_list), 7):
            chunk = step_data.daily_history_list[chunk_start:chunk_start + 7]
            print("  " + ", ".join(f"-{d['days_ago']}:{d['steps']}" for d in chunk))
    else:
        for idx, value in enumerate(step_data.daily_history):
            if idx % 7 == 0:
                print(f"  [{idx:02d}-{min(idx + 6, 13):02d}] {step_data.daily_history[idx:idx + 7]}")
    if step_data.warnings:
        print(f"warnings={step_data.warnings}")
    else:
        print("warnings=[]")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Sync G-Shock lifelog data.")
    parser.add_argument("--addr", type=str, help="MAC address of the watch to connect to directly")
    parser.add_argument("--timeout", type=float, default=-1.0, help="Connection timeout in seconds (-1 for infinite)")
    parser.add_argument("--peek", action="store_true", help="Read step data without closing the watch transaction")
    parser.add_argument(
        "--permissive",
        action="store_true",
        help="When set, aggregate hours permissively (treat missing 10-min slots as 0).",
    )
    parser.add_argument("--raw", action="store_true", help="Print raw payload hex for debugging")
    parser.add_argument("--log", action="store_true", help="Print the step summary to stdout")
    parser.add_argument("--quiet", action="store_true", help="Reduce log output on stderr (only print errors)")
    parser.add_argument("--hci", type=str, help="Read steps from a BTSnoop HCI log file instead of a live watch")
    parser.add_argument("--stdin", action="store_true", help="Read step payload (raw bytes or hex) from stdin")
    parser.add_argument("--summary", action="store_true", help="Fetch only today's total (fast)")
    parser.add_argument("--history", action="store_true", help="Fetch full step history (forces complete transfer)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail loudly when timestamp decoding is invalid; dump raw payload to a .hex file for postmortem",
    )
    args = parser.parse_args()

    if args.quiet:
        logging.getLogger('gshock_api').setLevel(logging.ERROR)
        logging.getLogger('bleak').setLevel(logging.ERROR)

    logger.info("=======================================================================")
    logger.info("Press and hold lower-left button on your watch for 3 seconds to pair...")
    logger.info("            Press lower-right button once if already paired.           ")
    logger.info("    At 00:30, 06:30, 12:30, or 18:30, a paired watch may auto sync.    ")
    logger.info("=======================================================================")
    logger.info("")

    if args.hci or args.stdin:
        logger.info(f"Reading step-counter data from HCI log: {args.hci}")
        # Support three modes:
        #  - --hci <path>: extract payload from BTSnoop text file
        #  - --hci - : read payload bytes or hex from stdin
        #  - --stdin : read payload bytes or hex from stdin
        if args.hci and args.hci != "-":
            payload = _extract_step_payload_from_hci(args.hci)
            if payload is None:
                raise ValueError(f"No readable step payload found in HCI log: {args.hci}")
        else:
            # read from stdin.buffer; accept raw bytes starting with 0x26 or hex text
            data = sys.stdin.buffer.read()
            if not data:
                raise ValueError("No data provided on stdin")
            # If the first byte looks like the life-log marker, treat as raw
            if data and data[0] == 0x26:
                payload = data
            else:
                # decode as text and try to extract ATT 'Value:' hex fields
                text = data.decode(errors="ignore")
                # Find hex groups following 'Value:' or plain hex groups per line
                candidates = []
                for m in re.finditer(r"Value:\s*([0-9A-Fa-f]+)", text):
                    candidates.append(m.group(1))
                if not candidates:
                    # fallback: any long hex group on its own line
                    for m in re.finditer(r"\b([0-9A-Fa-f]{6,})\b", text):
                        candidates.append(m.group(1))

                payload = None
                matched_hex = None
                parsed_candidates: list[tuple[str, bytes]] = []
                # Build all candidates first (do not stop at first match).
                for hexstr in candidates:
                    try:
                        raw = bytes.fromhex(hexstr)
                    except Exception:
                        continue
                    start = raw.find(b"\x26")
                    if start == -1:
                        continue
                    candidate = raw[start:]
                    # Try to parse candidate payload; ignore parse-time errors
                    try:
                        parsed = StepCounterIOFunctional.parse(candidate)
                    except Exception:
                        parsed = None
                    if parsed is not None:
                        parsed_candidates.append((hexstr, candidate))

                if not parsed_candidates:
                    raise ValueError("Stdin did not contain a parsable step payload")

                # Prefer the longest parsed candidate to avoid selecting short/truncated fragments.
                parsed_candidates.sort(key=lambda t: len(t[1]), reverse=True)
                matched_hex, payload = parsed_candidates[0]

                if payload is None:
                    raise ValueError("Stdin did not contain a parsable step payload")

                # Log which candidate matched for debugging truncated payload issues
                if matched_hex:
                    try:
                        preview = matched_hex[:128]
                        logger.info(f"Matched HCI candidate: len={len(matched_hex)//2}B preview={preview}...")
                    except Exception:
                        logger.info("Matched HCI candidate (preview unavailable)")

        step_data = StepCounterIOFunctional.parse(payload)
        if step_data is None:
            raise ValueError(f"Failed to parse step payload from HCI log: {args.hci}")

        # If user asked for summary/history explicitly, prefer that (stdin/hci payload still overrides)
        use_summary = args.summary
        if args.history:
            use_summary = False
            args.peek = False

        await _fetch_steps(
            None,
            use_summary=use_summary,
            peek=args.peek,
            print_log=args.log,
            permissive=args.permissive,
            show_raw=args.raw,
            step_data=step_data,
            strict=args.strict,
        )
        return

    try:
        logger.info("Waiting for connection...")

        if args.addr:
            logger.info(f"Using specific MAC address: {args.addr}")

        connection = Connection(address=args.addr)

        # Convert -1.0 to sys.float_info.max for infinite timeout
        timeout = sys.float_info.max if args.timeout == -1.0 else args.timeout
        connected = await connection.connect(watch_filter=None, timeout=timeout)
        if not connected:
            raise GShockConnectionError("Failed to find or connect to the watch before timeout.")

        logger.info("Connected...")

        api = GshockAPI(connection)

        watch_name = await api.get_watch_name()
        logger.info(f"got watch name: {watch_name}")

        # Step counter data should be fetched before time-sync on supported watches.
        try:
            if args.summary and args.history:
                raise ValueError("--summary and --history are mutually exclusive")
            use_summary = args.summary
            if args.history:
                use_summary = False
                args.peek = False
            await _fetch_steps(
                api,
                use_summary=use_summary,
                peek=args.peek,
                print_log=args.log,
                permissive=args.permissive,
                show_raw=args.raw,
                strict=args.strict,
            )
        except Exception as e:
            logger.warning(f"Step counter fetch failed: {e}")

        logger.info("Syncing time...")
        await api.set_time(time.time())

    except GShockConnectionError as e:
        logger.error(f"Connection problem: {e}")
        sys.exit(1)

    await connection.disconnect()
    logger.info("disconnected")


if __name__ == "__main__":
    asyncio.run(main())