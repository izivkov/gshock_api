import struct
from typing import Final

from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.logger import logger
from gshock_api.step_counter_data import StepCounterData

FALLBACK_EXPECTED_LENGTH: Final[int] = 400
DRSP_CATEGORY_EXERCISE: Final[int] = 0x11
START_TRANSACTION_CMD: Final[bytes] = bytes([0x00, DRSP_CATEGORY_EXERCISE, 0x00, 0x00, 0x00])
END_TRANSACTION_CMD: Final[bytes] = bytes([0x04, DRSP_CATEGORY_EXERCISE, 0x00, 0x00, 0x00])


class StepCounterIOFunctional:
    """Pure functional core for decoding ABL-100WE step counter (life-log) records."""

    HEADER_SIZE: Final[int] = 6
    HOURLY_SLOT_COUNT: Final[int] = 144
    HOURLY_SLOT_SIZE: Final[int] = 2
    BETWEEN_HISTORY_PADDING_SIZE: Final[int] = 24
    DAILY_SLOT_COUNT: Final[int] = 14
    DAILY_SLOT_SIZE: Final[int] = 4

    @staticmethod
    def parse(payload: bytes) -> StepCounterData | None:
        daily_history_offset = (
            StepCounterIOFunctional.HEADER_SIZE
            + StepCounterIOFunctional.HOURLY_SLOT_COUNT * StepCounterIOFunctional.HOURLY_SLOT_SIZE
            + StepCounterIOFunctional.BETWEEN_HISTORY_PADDING_SIZE
        )
        current_day_offset = (
            daily_history_offset
            + StepCounterIOFunctional.DAILY_SLOT_COUNT * StepCounterIOFunctional.DAILY_SLOT_SIZE
        )

        if len(payload) < current_day_offset + StepCounterIOFunctional.DAILY_SLOT_SIZE or payload[0] != 0x26:
            return None

        hourly_steps: list[int | None] = []
        for i in range(StepCounterIOFunctional.HOURLY_SLOT_COUNT):
            offset = StepCounterIOFunctional.HEADER_SIZE + i * StepCounterIOFunctional.HOURLY_SLOT_SIZE
            val = struct.unpack_from("<H", payload, offset)[0]
            hourly_steps.append(None if val == 0xFFFE else val)

        daily_history: list[int | None] = []
        for i in range(StepCounterIOFunctional.DAILY_SLOT_COUNT):
            offset = daily_history_offset + i * StepCounterIOFunctional.DAILY_SLOT_SIZE
            val = struct.unpack_from("<I", payload, offset)[0]
            daily_history.append(None if val == 0xFFFFFFFE else val)

        cur_val = struct.unpack_from("<I", payload, current_day_offset)[0]
        current_day_steps = None if cur_val == 0xFFFFFFFE else cur_val

        return StepCounterData(
            day_of_week=payload[1],
            month=payload[2],
            day_of_month=payload[3],
            hourly_steps=hourly_steps,
            daily_history=daily_history,
            current_day_steps=current_day_steps,
        )


class StepCounterIO:
    """Manages requesting, fragment accumulation, and decoding of ABL-100 step counter notifications."""

    result: CancelableResult[StepCounterData] | None = None
    connection: ConnectionProtocol | None = None
    accumulator: bytearray = bytearray()
    expected_length: int = FALLBACK_EXPECTED_LENGTH
    reset: bool = True

    @staticmethod
    async def request(connection: ConnectionProtocol, reset: bool = False) -> StepCounterData:
        """Request steps counter data from the watch and optionally reset them"""
        from gshock_api.watch_info import watch_info

        if not watch_info.hasStepCounter:
            logger.info(f"Step counter not supported on watch model: {watch_info.model}")
            return StepCounterData.unavailable()

        StepCounterIO.connection = connection
        StepCounterIO.reset = reset
        StepCounterIO.accumulator = bytearray()
        StepCounterIO.expected_length = FALLBACK_EXPECTED_LENGTH
        StepCounterIO.result = CancelableResult[StepCounterData]()

        # Handle 0x0011 is CASIO_DATA_REQUEST_SP
        await connection.write(0x0011, START_TRANSACTION_CMD)
        try:
            return await StepCounterIO.result.get_result()
        finally:
            StepCounterIO.result = None
            StepCounterIO.accumulator = bytearray()

    @staticmethod
    def on_drsp_received(data: bytes) -> None:
        """Handles length announcement or ACK notifications on the DRSP characteristic (handle 0x0011)."""
        if len(data) < 5:
            return
        command = data[0]
        category = data[1]
        if category != DRSP_CATEGORY_EXERCISE:
            return

        if command == 0x00:
            announced_length = data[2] | (data[3] << 8) | (data[4] << 16)
            if StepCounterIO.result is not None:
                StepCounterIO.expected_length = announced_length
                logger.debug(f"StepCounterIO: expected length announced = {announced_length}B")

    @staticmethod
    def on_received(data: bytes) -> None:
        """Accumulates incoming fragments and parses StepCounterData when full payload is received. Acknowledge the transaction if `reset` was passed earlier so the watch reset the counters."""
        if StepCounterIO.result is None:
            return

        StepCounterIO.accumulator.extend(data)
        logger.debug(
            f"StepCounterIO.on_received: accumulated={len(StepCounterIO.accumulator)}B / "
            f"expected={StepCounterIO.expected_length}B"
        )

        if len(StepCounterIO.accumulator) < StepCounterIO.expected_length:
            return

        # Acknowledge end of transaction if reset was requested
        if StepCounterIO.connection is not None and StepCounterIO.reset:
            try:
                # Fire-and-forget end transaction command
                import asyncio
                asyncio.create_task(
                    StepCounterIO.connection.write(0x0011, END_TRANSACTION_CMD)
                )
            except Exception as e:
                logger.warning(f"Failed to send end transaction command: {e}")

        full_payload = bytes(StepCounterIO.accumulator)
        step_data = StepCounterIOFunctional.parse(full_payload)

        if step_data is not None:
            logger.info(f"Step count parsed: {step_data}")
            StepCounterIO.result.set_result(step_data)
        else:
            logger.warning(f"Failed to parse activity record from {len(full_payload)}B payload")
            StepCounterIO.result.set_result(StepCounterData.unavailable())
