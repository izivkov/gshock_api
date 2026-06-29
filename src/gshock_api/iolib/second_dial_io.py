"""
second_dial_io.py — Secondary dial time sync for watches with dual time zones.

Handles the second pass required by watches like MTG-B1000 that have a
secondary dial showing a different city's time.

Protocol (from btsnoop_hci_mgt_b1000.log analysis):

Pass 1 (main time — done by existing initialize_for_setting_time):
  read/write 0x1d (DstWatchState)
  read/write 0x1e slots (DstSetting)
  write 0x24 slot 0 (HomeTime main city — handled by existing code)
  write 0x24 slot 1 (HomeTime second city — pass 1 placeholder)
  write 0x09 (SetTime)
  write 0x21 00 01 (ResetSequence slot 0)

Pass 2 (secondary dial — this class):
  read 0x1d  → echo back unchanged (preserves secondary city assignment)
  read 0x1e slot 0 → echo back unchanged
  read 0x1e slot 1 → echo back unchanged (secondary city DST rule)
  read 0x24 slot 0 → echo back unchanged (main city coords)
  read 0x24 slot 1 → echo back unchanged (secondary city coords)
  write 0x21 01 01 (ResetSequence slot 1 — applies secondary dial)

This preserves whatever secondary city the user configured via the Casio app.
"""

from gshock_api.cancelable_result import CancelableResult
from gshock_api.casio_constants import CasioConstants
from gshock_api.iolib.actions import BLEAction, Write
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.iolib.dst_for_world_cities_io import DstForWorldCitiesIO
from gshock_api.iolib.dst_watch_state_io import DstWatchStateIO, DtsState
from gshock_api.iolib.home_time_io import HomeTimeIO
from gshock_api.logger import logger
from gshock_api.pending_requests_registry import PendingRequestsRegistry


_ALL_FEATURES = 0x000E


class SecondDialIOFunctional:
    """
    Pure functional second-dial modules implementing Monoids.

    Encodes the BLE write commands needed for each step of the second-dial
    sync sequence without performing any I/O itself.
    """

    @staticmethod
    def encode_reset_sequence(slot: int) -> bytes:
        """Return the ResetSequence (0x21) command bytes for the given slot.

        slot=0 → 21 00 01 (apply main time)
        slot=1 → 21 01 01 (apply secondary dial)
        """
        return bytes([0x21, slot, 0x01])

    @staticmethod
    def prepare_watch_commands(slot: int) -> list[BLEAction]:
        """Return the BLE write action needed to commit a ResetSequence for a slot."""
        return [
            Write(
                handle=_ALL_FEATURES,
                data=SecondDialIOFunctional.encode_reset_sequence(slot)
            )
        ]


class SecondDialIO:
    """
    Stateful interpreter for the secondary dial sync sequence.
    Acts as the interpreter for SecondDialIOFunctional commands.

    Unlike single-characteristic IOs, this class orchestrates multiple
    sub-IOs (DstWatchStateIO, DstForWorldCitiesIO, HomeTimeIO) in sequence.
    The CancelableResult is self-resolved after the full sequence completes,
    rather than being resolved by a single BLE on_received callback.
    """

    result: CancelableResult[None] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> None:
        """Execute the full second-dial sync sequence with cancellation support.

        Reads DST/HomeTime data from the watch and echoes it back unchanged,
        then sends ResetSequence for slot 1 to apply the secondary dial.
        Registers with PendingRequestsRegistry so the operation can be
        cancelled if the connection drops.
        """
        SecondDialIO.connection = connection
        SecondDialIO.result = CancelableResult[None]()
        PendingRequestsRegistry.register("SecondDialIO", SecondDialIO.result)
        try:
            await SecondDialIO._run_sync(connection)
            SecondDialIO.result.set_result(None)
            return await SecondDialIO.result.get_result()
        finally:
            PendingRequestsRegistry.unregister("SecondDialIO")
            SecondDialIO.result = None

    @staticmethod
    def on_received(data: bytes) -> None:
        # SecondDialIO orchestrates sub-IOs directly; it has no single
        # BLE notification to wait for — the result is self-resolved in request().
        pass

    @staticmethod
    async def send_to_watch() -> None:
        pass

    @staticmethod
    async def write_reset_sequence(connection: ConnectionProtocol, slot: int) -> None:
        """
        Sends ResetSequence (0x21) to apply DST/HomeTime changes for a slot.
        slot=0 → 21 00 01 (apply main time)
        slot=1 → 21 01 01 (apply secondary dial)
        """
        cmd = SecondDialIOFunctional.encode_reset_sequence(slot)
        logger.info(f"SecondDialIO: ResetSequence slot {slot}: {cmd.hex()}")
        await connection.write(_ALL_FEATURES, cmd.hex())

    # ── Internal implementation ───────────────────────────────────────────────

    @staticmethod
    async def _run_sync(connection: ConnectionProtocol) -> None:
        """
        Execute the second pass for secondary dial watches.
        Reads watch data and echoes back unchanged — preserving whatever
        secondary city the user configured via the Casio app.
        """
        logger.info("SecondDialIO: syncing secondary dial...")

        # ── Read and echo DstWatchState ───────────────────────────────────────
        # Contains both home and secondary city slot assignments.
        # We echo it back unchanged to preserve the secondary city.
        logger.info("SecondDialIO: read/write DstWatchState...")
        dst_state = await DstWatchStateIO.request(connection, DtsState.ZERO)
        await connection.write(_ALL_FEATURES, dst_state.hex())

        # ── Read and echo DstSetting for both slots ───────────────────────────
        logger.info("SecondDialIO: read/write DstSetting slot 0...")
        dst0 = await DstForWorldCitiesIO.request(connection, 0)
        await connection.write(_ALL_FEATURES, dst0.hex())

        logger.info("SecondDialIO: read/write DstSetting slot 1...")
        dst1 = await DstForWorldCitiesIO.request(connection, 1)
        await connection.write(_ALL_FEATURES, dst1.hex())

        # ── Read and echo HomeTime for both slots ─────────────────────────────
        logger.info("SecondDialIO: read/write HomeTime slot 0...")
        ht0 = await HomeTimeIO.request(connection, 0)
        await connection.write(_ALL_FEATURES, ht0.hex())

        logger.info("SecondDialIO: read/write HomeTime slot 1...")
        ht1 = await HomeTimeIO.request(connection, 1)
        await connection.write(_ALL_FEATURES, ht1.hex())

        # ── ResetSequence slot 1 — applies secondary dial changes ─────────────
        # From HCI log: 21 01 01
        logger.info("SecondDialIO: sending ResetSequence for slot 1...")
        reset_cmd = SecondDialIOFunctional.encode_reset_sequence(1)
        await connection.write(_ALL_FEATURES, reset_cmd.hex())

        logger.info("SecondDialIO: secondary dial sync complete.")