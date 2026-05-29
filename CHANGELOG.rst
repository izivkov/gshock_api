=========
Changelog
=========

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

