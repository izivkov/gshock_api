"""Backward-compatible import for StepCounterData.

This module preserves the older import path used by existing scripts and tests:
    from gshock_api.step_counter_data import StepCounterData
"""

from gshock_api.model.step_counter_data import StepCounterData

__all__ = ["StepCounterData"]
