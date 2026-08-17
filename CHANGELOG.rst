=========
Changelog
=========

Version 2.0.39 (2026-08-17)
============================

- FEATURE: Introduced ``WatchProtocol`` design pattern (``StandardProtocol``, ``MipProtocol``, ``AnalogueProtocol``) decoupling model-specific execution from core API.
- FEATURE: Aligned ``WatchInfo`` with Kotlin ``GShockAPI`` reference including full ``WatchModel`` enum, per-model capability attributes (``ModelInfo``), and official Casio model lookup table (``EXACT_MODEL_MAP``).
- FEATURE: Added full support for GW-BX5600 series watches, including ``CasioTimeZoneHelper`` for world city coordinate lookups and 94-byte Step 2 location record payload construction.
- FEATURE: Added complete step counter support for ABL-100 series watches, including ``StepCounterData`` model, multi-packet fragment accumulation, DRSP length announcement processing, and end-transaction signaling.
- REFACTOR: Updated ``MessageDispatcher.on_received`` and ``GshockAPI`` operations to delegate via ``WatchProtocol``.
- FIX: Resolved infinite recursion loop in ``StandardProtocol.get_time_adjustment()``.
- FIX: Added ``lookup_watch_info()`` on ``WatchInfo`` preventing BLE scanner attribute errors during device filtering.


Version 2.0.38 (2026-05-31)
============================

- FEATURE: Converted the entire library to a pure functional programming model
  using monoids for data transformation. This architectural change improves code
  composability, predictability, and testability.
- FEATURE: Implemented functional model with monoids for TimeIO module as the
  primary data transformation handler for time synchronisation operations.
- REFACTOR: All iolib modules (TimeIO, SettingsIO, TimerIO, AlarmsIO, EventsIO,
  and others) now use a functional composition approach with immutable data
  structures and monoid operations for buffer handling and packet encoding/decoding.
- IMPROVEMENT: Enhanced test coverage for functional model implementations
  in test_code.py
- IMPROVEMENT: Added new actions module to support functional data transformations


Version 2.0.37 (2026-05-29)
============================

- FIX: ``TimeEncoder.prepare_current_time`` now correctly computes ``arr[8]``
  (the sub-second fraction byte) using the formula
  ``(microseconds * 1_000 * 256) // 1_000_000_000`` instead of hardcoding 0.
  This matches the reference Kotlin implementation and ensures accurate
  sub-second time synchronisation with the watch.

Version 2.0.36
==============

- Added data structures to BLE packet buffers (``Header``, ``Payload``, ``Protocol``).

Version 2.0.35 and earlier
===========================

- Initial public release and iterative improvements.
