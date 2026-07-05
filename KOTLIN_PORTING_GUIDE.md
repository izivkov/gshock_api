# Kotlin Porting Guide

This document captures the exact changes introduced on the current branch compared with main, with a focus on what needs to be mirrored in a Kotlin version of the library.

## Goal of this branch

The branch adds initial support for reading daily step counts from compatible Casio watches and improves the BLE handling flow so the library can react to activity-record notifications.

## High-level change summary

| Area | Files | What changed | Why it matters for Kotlin |
| --- | --- | --- | --- |
| Step counter feature | src/gshock_api/iolib/step_counter_io.py, src/gshock_api/gshock_api.py, src/gshock_api/message_dispatcher.py, src/gshock_api/casio_constants.py, src/gshock_api/watch_info.py | Added a new step-counter request/response flow, a parser for activity-record payloads, a public API entry point, and a new capability flag for supported watches. | Kotlin needs an equivalent request class, dispatcher registration, and public API method for step-count retrieval. |
| BLE connection robustness | src/gshock_api/connection.py | The connection layer now discovers characteristics dynamically and subscribes to all notify/indicate characteristics instead of relying on a narrow, hardcoded flow. | Kotlin should implement the same adaptive subscription pattern so new notifications are handled automatically. |
| Example/test flow | src/examples/api_tests.py | The example script now reads step count first and gates the destructive actions behind a flag. | Kotlin examples should avoid destructive behavior by default and show the new capability in a safe way. |

## File-by-file breakdown

### 1) src/gshock_api/iolib/step_counter_io.py

What changed:
- Added a new class, StepCounterIO, to request step count data from the watch.
- The request sends a specific payload to handle 0x0011 (CASIO data request SP).
- The class listens for activity-record notifications arriving on handle 0x0014.
- It parses the payload and extracts the daily step total from the activity-record bytes.

Why this was added:
- The branch targets watches that expose daily step data through a life-log/activity-record notification format.
- The parser is needed because the raw payload is not a simple numeric field; it is a structured notification with multiple record sections.

What Kotlin should implement:
- Create a StepCounterIO or equivalent class with:
  - a request method that writes the request bytes to the correct characteristic,
  - an onReceived callback that receives the notification payload,
  - parsing logic that extracts the daily step total from the activity-record bytes.
- Preserve the same request/response pattern used by the other I/O handlers.

### 2) src/gshock_api/gshock_api.py

What changed:
- Added a public method, get_step_count(), to the main API facade.
- The method checks whether the current watch model advertises step-counter support before attempting the request.
- If the watch does not support the feature, it returns 0 and logs the condition.

Why this was added:
- This makes step-count reading available through the same high-level API used for alarms, settings, reminders, and watch condition.
- It also prevents unsupported models from failing when the feature is not available.

What Kotlin should implement:
- Expose a matching high-level method such as getStepCount().
- Keep the capability guard in the API layer so unsupported watches return a safe default value instead of crashing.

### 3) src/gshock_api/message_dispatcher.py

What changed:
- Registered StepCounterIO as the handler for the activity-record characteristic key.
- This ensures incoming notification bytes are routed to the new parser rather than ignored.

Why this was added:
- Without dispatcher registration, the library would receive the data but never process it.
- The change is essential for making the feature work end to end.

What Kotlin should implement:
- Add a dispatcher entry that maps the activity-record characteristic ID to the step-counter handler.
- Mirror the existing event-routing design so incoming data is delegated to the correct handler class.

### 4) src/gshock_api/casio_constants.py

What changed:
- Added a characteristic mapping entry for CASIO_ACTIVITY_RECORD with the value 0x26.

Why this was added:
- The dispatcher needs a stable identifier for the activity-record feature.
- This makes the raw characteristic code explicit and reusable across the library.

What Kotlin should implement:
- Add the same constant or enum entry in the Kotlin constants layer so the feature key is not hardcoded in multiple places.

### 5) src/gshock_api/watch_info.py

What changed:
- Added a new capability flag, hasStepCounter, with a default value of false.
- Enabled that flag for the ABL model.

Why this was added:
- The library now needs a model-level capability model so the API can decide whether step counting is supported before issuing a request.
- This makes the feature model-aware rather than assuming every watch can support it.

What Kotlin should implement:
- Add an equivalent capability flag to the watch metadata model.
- Populate it for the relevant watch model(s) and keep the default as false.

### 6) src/gshock_api/connection.py

What changed:
- The connection logic now builds a characteristics map from the discovered BLE services.
- It subscribes to all characteristics that support notifications or indications.
- The write logic uses the discovered characteristic map and the handle mapping more dynamically.

Why this was added:
- The previous flow was more rigid and could miss characteristics depending on the watch model.
- This makes the connection layer more adaptable and better suited for supporting additional watch features in the future.

What Kotlin should implement:
- Create a similar characteristic discovery step.
- Subscribe to all notify/indicate characteristics in a generic way instead of hardcoding a small list.
- Keep the write path tolerant of watches that do not expose every characteristic.

### 7) src/examples/api_tests.py

What changed:
- Added a new destructive flag set to false by default.
- The script now requests the step count before the other operations.
- The destructive actions (time changes, alarms, reminders, settings changes) are wrapped behind the flag so they are no longer executed by default.

Why this was added:
- The example script should be safe to run without altering a watch unexpectedly.
- It also demonstrates the new step-count capability without requiring the user to perform destructive actions.

What Kotlin should implement:
- Keep a “safe by default” demo flow.
- Show the new step-count call early in the sample, but keep write-based operations opt-in.

## Porting checklist for Kotlin

1. Add a step-counter I/O class.
2. Register the activity-record characteristic in the dispatcher.
3. Add a public API method for reading step count.
4. Add a capability flag to the watch-info model.
5. Add the characteristic constant mapping.
6. Make BLE connection subscription generic and adaptive.
7. Keep example/demo code safe by default.

## Suggested Kotlin class mapping

| Python | Kotlin equivalent |
| --- | --- |
| GshockAPI | GshockApi |
| StepCounterIO | StepCounterIo |
| MessageDispatcher | MessageDispatcher |
| WatchInfo / model capabilities | WatchInfo / capability model |
| Connection | Connection |

## Important implementation note

The most important behavioral change is not just the new parser; it is the fact that the library now expects activity-record notifications to arrive and be routed through the dispatcher. A Kotlin port should preserve that flow rather than treating step-count support as a one-off API method without the message-routing infrastructure.
