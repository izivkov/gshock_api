"""Transport for the exercise/profile opcode (0x2D).

ExerciseIO owns only in-flight request state. Profile data belongs to the app
and is passed through the Exercise model; nothing is cached or persisted here.
"""
from gshock_api.cancelable_result import CancelableResult
from gshock_api.iolib.connection_protocol import ConnectionProtocol
from gshock_api.model.exercise import Exercise

OPCODE = 0x2D
ALL_FEATURES_WRITE_HANDLE = 0x000E


class ExerciseIO:
    result: CancelableResult[Exercise] | None = None
    connection: ConnectionProtocol | None = None

    @staticmethod
    async def request(connection: ConnectionProtocol) -> Exercise:
        ExerciseIO.connection = connection
        ExerciseIO.result = CancelableResult[Exercise]()
        await connection.request(f"{OPCODE:02X}")
        return await ExerciseIO.result.get_result()

    @staticmethod
    async def send_to_watch(_message: str) -> None:
        if ExerciseIO.connection is None:
            raise RuntimeError("ExerciseIO.connection is not set")
        ExerciseIO.result = CancelableResult[Exercise]()
        await ExerciseIO.connection.request(f"{OPCODE:02X}")

    @staticmethod
    async def set_exercise(connection: ConnectionProtocol, exercise: Exercise) -> None:
        """Write an app-supplied profile without retaining a copy in the library."""
        await connection.write(ALL_FEATURES_WRITE_HANDLE, exercise.encode())

    @staticmethod
    async def send_to_watch_set(message: str) -> None:
        if ExerciseIO.connection is None:
            raise RuntimeError("ExerciseIO.connection is not set")
        await ExerciseIO.set_exercise(ExerciseIO.connection, Exercise.from_json(message))

    @staticmethod
    def on_received(message: bytes) -> None:
        if ExerciseIO.result is None:
            raise RuntimeError("ExerciseIO.result is not set")
        ExerciseIO.result.set_result(Exercise.decode(message))
