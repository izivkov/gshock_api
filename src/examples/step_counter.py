"""
Step counter example CLI

This script connects to a paired G-Shock watch over BLE using `Connection` +
`GshockAPI` and prints human-friendly step-counter (lifelog) output for
debugging and demonstration purposes.

Fetch modes:
- `--summary`: quick total for today via `get_step_summary()`.
- `--history` (default when neither `--summary` nor `--peek` is given):
    full history via `get_step_history()`.
- `--peek`: low-level diagnostic mode via `get_step_count(peek=True)` that
    leaves the watch transaction open.

Key behaviors:
- Outputs a two-column Summary table, an hourly table, and detailed activity
    records for today.
"""

import asyncio
import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gshock_api.connection import Connection
from gshock_api.exceptions import GShockConnectionError
from gshock_api.gshock_api import GshockAPI
from gshock_api.logger import logger
from gshock_api.model.step_counter_data import StepCounterData


async def _fetch_steps(
    api: GshockAPI,
    *,
    use_summary: bool = False,
    peek: bool = False,
    print_log: bool,
    show_raw: bool = False,
) -> None:
    """Fetch the current step-counter payload from a connected watch and optionally print a summary."""
    if use_summary:
        total_steps = await api.get_step_summary()
        # Build a minimal StepCounterData instance that works whether the
        # model exposes `timestamp` or separate `month/day_of_month` fields.
        step_data = StepCounterData()
        try:
            step_data.current_day_steps = total_steps
        except Exception:
            setattr(step_data, "current_day_steps", total_steps)
    elif not peek:
        step_data = await api.get_step_history()
    else:
        step_data = await api.get_step_count(peek=peek)

    total_steps = step_data.current_day_steps if step_data.current_day_steps is not None else 0

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

    # Build and print a neat two-column summary table
    if hasattr(step_data, "timestamp") and getattr(step_data, "timestamp"):
        ts = getattr(step_data, "timestamp")
        try:
            ts_str = ts.isoformat()
        except Exception:
            ts_str = str(ts)
    else:
        ts_str = "None"

    summary = [
        ("Current day steps", str(total_steps)),
        ("Timestamp", ts_str),
        ("Distance (m)", str(step_data.distance_meters)),
        ("Pending distance (m)", str(step_data.pending_distance_meters)),
        ("Total distance (m)", str(step_data.total_distance_meters)),
        ("BCD total steps", str(step_data.bcd_total_steps)),
    ]

    # column widths
    key_w = max(len(k) for k, _ in summary)
    val_w = max(len(v) for _, v in summary)
    print('\nSummary:')
    print('Field'.ljust(key_w) + ' | ' + 'Value'.ljust(val_w))
    print(('-' * key_w) + '-+-' + ('-' * val_w))
    for k, v in summary:
        print(k.ljust(key_w) + ' | ' + v.ljust(val_w))

    # Print hourly aggregates neatly as a table
    hours_to_print = step_data.hourly_by_hour

    print('\nHourly by hour:')
    print(f"{'Hour':>4} | {'Steps':>6} | {'Dist m':>6}")
    print('------+--------+----------')
    if hours_to_print:
        for h in range(24):
            val = hours_to_print[h] if h < len(hours_to_print) else None
            distance = None
            if step_data.timestamp:
                distance_index = (step_data.timestamp.hour - h - 1) % 24
                if distance_index < len(step_data.committed_distances):
                    distance = step_data.committed_distances[distance_index]
                if h == step_data.timestamp.hour:
                    distance = step_data.pending_distance_meters
            distance_str = str(distance) if distance is not None else "-"
            print(
                f" {h:02d}   | {(val if val is not None else '-'):>6}"
                f" | {distance_str:>8}"
            )
    else:
        print('Hourly breakdown unavailable')

    print('\nActivity records:')
    if step_data.hourly_intervals:
        for interval in step_data.hourly_intervals:
            index = interval['index']
            distance = (
                step_data.committed_distances[index]
                if index < len(step_data.committed_distances)
                else None
            )
            intensity = interval.get('intensity', ())
            print(
                f"  idx={index:02d} steps={interval['steps']}"
                f" distance_m={distance if distance is not None else '-'}"
                f" intensity={intensity}"
            )
    else:
        print('No activity records available')

    if step_data.pending_intensity or step_data.pending_distance_meters is not None:
        print(
            f"  current hour pending_distance_m={step_data.pending_distance_meters}"
            f" intensity={step_data.pending_intensity}"
        )

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
    parser.add_argument("--timeout", type=float, default=-1.0, help="Connection timeout in seconds (-1 for infinite)")
    parser.add_argument(
        "--peek",
        action="store_true",
        help="Diagnostic mode: leave the watch transaction open (may omit history)",
    )
    parser.add_argument("--raw", action="store_true", help="Print raw payload hex for debugging")
    parser.add_argument("--log", action="store_true", help="Print the step summary to stdout")
    parser.add_argument("--quiet", action="store_true", help="Reduce log output on stderr (only print errors)")
    parser.add_argument("--summary", action="store_true", help="Fetch only today's total (fast)")
    parser.add_argument("--history", action="store_true", help="Fetch full step history (forces complete transfer)")
    args = parser.parse_args()

    if args.summary and args.history:
        parser.error("--summary and --history are mutually exclusive")

    if args.quiet:
        logging.getLogger('gshock_api').setLevel(logging.ERROR)
        logging.getLogger('bleak').setLevel(logging.ERROR)

    logger.info("=======================================================================")
    logger.info("Press and hold lower-left button on your watch for 3 seconds to pair...")
    logger.info("            Press lower-right button once if already paired.           ")
    logger.info("    At 00:30, 06:30, 12:30, or 18:30, a paired watch may auto sync.    ")
    logger.info("=======================================================================")
    logger.info("")

    try:
        logger.info("Waiting for connection...")

        connection = Connection()

        scan_timeout = None if args.timeout == -1.0 else args.timeout
        connected = await asyncio.wait_for(
            connection.connect(watch_filter=None, timeout=scan_timeout),
            timeout=scan_timeout,
        )
        if not connected:
            raise GShockConnectionError("Failed to find or connect to the watch before timeout.")

        logger.info("Connected...")

        api = GshockAPI(connection)

        watch_name = await asyncio.wait_for(api.get_watch_name(), timeout=scan_timeout)
        logger.info(f"got watch name: {watch_name}")

        # Step counter data should be fetched before time-sync on supported watches.
        try:
            use_summary = args.summary
            peek = args.peek
            if args.history:
                use_summary = False
                peek = True
            fetch_steps = _fetch_steps(
                api,
                use_summary=use_summary,
                peek=peek,
                print_log=args.log,
                show_raw=args.raw,
            )
            await asyncio.wait_for(fetch_steps, timeout=scan_timeout)
        except Exception as e:
            logger.warning(f"Step counter fetch failed: {e}")

        logger.info("Syncing time...")
        await asyncio.wait_for(api.set_time(time.time()), timeout=scan_timeout)

    except (GShockConnectionError, TimeoutError) as e:
        message = str(e) or "operation timed out"
        logger.error(f"Connection problem: {message}")
        sys.exit(1)

    await connection.disconnect()
    logger.info("disconnected")


if __name__ == "__main__":
    asyncio.run(main())