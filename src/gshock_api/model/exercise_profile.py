from dataclasses import dataclass


@dataclass
class ExerciseProfile:
    step_goal: int = 10000
    height: int = 0
    weight: int = 0
    