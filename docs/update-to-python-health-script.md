# DW-H5600 LifeLog: implementation summary

Status: working notes for implementers. Evidence levels:
**C** = confirmed by captures or by a complete live sync, **S** = strongly supported by
documents, **H** = hypothesis, **U** = unknown.

Scope: model 3516 (DW-H5600). Where a fact comes from the 3461 (GW-B5600) or 3506 (GBD-200)
family, it is marked and must not be treated as proof for 3516.

---

## 1. BLE link

| Role | UUID | Handle seen in captures | Evidence |
|---|---|---|---|
| DRSP: index announce, START, finish, END | `26eb0023-b012-49a8-b1f8-394fb2032b0f` | value 0x0010 | C (live sync) |
| CONVOY: poll, setup replies, bulk data, acks | `26eb0024-b012-49a8-b1f8-394fb2032b0f` | value 0x0013 | C (live sync) |
| STATUS: watch condition `0x28`, setup replies | `26eb002d-b012-49a8-b1f8-394fb2032b0f` | value 0x0018 | C; handle confirmed by an external issue |
| SETUP: one-byte requests (write without response) | `26eb002c-b012-49a8-b1f8-394fb2032b0f` | declaration 0x0015 | C (live sync wrote here successfully) |

- Subscribe to DRSP, CONVOY, STATUS only. Subscribing to other characteristics (such as
  `26eb0030`) made the watch disconnect during tests.
- The GW-BX5600 setup UUID `26eb002e` is not present on the DW-H5600. Do not use it.
- Pairing: the watch must be paired and bonded. Without a bond it never reaches the transfer
  state. Removing stale entries is needed when the watch's address changes.
- Watch addresses change between sessions. Look devices up by name or by a fresh scan.

## 2. Setup exchange (before polling)

Write each command to SETUP (write without response), wait up to ~1.2–5 s for a STATUS
notification that starts with the same byte, then continue.

Commands that worked in the 16 Nov live sync:
`23 10 11 3b 3a 26 28 20 2f 43 13 45`

Replies to these are echoed unchanged to STATUS (write with response) for:
`11 3b 3a 2f 13 45`

Observed reply examples (16 Nov):
- `23` → ASCII device name `CASIO DW-H5600`
- `28` → `28 06 16 00 00 fa 00 00 01 01` form (see §6)

S: the fuller sequence from the 3516 handshake document is
`23 22 10 11 3b 3a 26 28 20 1d 1e 3d`. The working sync did not send `22`, `1d`, `1e`, or
`3d`. Their role is H.

## 3. Sync protocol (C, live and replay)

1. Poll: write `00 00 00` to CONVOY. Reply `00 00 00` = ready. Reply `00 01 xx` = busy: wait
   about 3.5 s and poll again. A busy state that never clears means the setup or bond is wrong.
2. Write `04 00 00 00 00 00 00 00 00 00` (10 bytes) to CONVOY. Expect `04 00 28 00 28 …`.
3. Write `04 01 18 00 18 00 00 00 dc 05` to CONVOY. Expect another `04 00 28 …`.
4. Write `06 00 … 00` (14 bytes) to CONVOY. Expect a 9-byte reply `06 xx …`. Echo it
   verbatim to CONVOY. The second byte varies between sessions (`fa`, `17` seen).
5. The next 9-byte `06` reply triggers the transfer. Write START `00 2e ff ff ff ff ff` to
   DRSP. The watch acknowledges it on DRSP as `00 2e ff ff ff ff ff`.
6. Index announcements arrive on DRSP as `00 2e <idx> <len:3 LE>`. Echo each one verbatim
   to DRSP.
7. Bulk data arrives on CONVOY as notifications starting with `05`. Write
   `07 00 … 00` (15 bytes) to CONVOY as an ack for each one.
8. When an index is complete the watch sends `07 2e <idx> <len>` on DRSP. Echo it verbatim.
9. END: the watch sends `04 2e ff ff ff ff ff` on DRSP. Echo it. The capture then shows
   `03 01` on CONVOY, followed by a poll.

Timing: the whole 16 Nov sync took about 35 s; the 26 Oct sync about 48 s.

## 4. Watch condition, status `0x28` (STATUS notifications)

Layout observed: `28 06 <b2> 00 00 <b5> 00 00 <b8> <b9>`.

| Byte | Meaning | Evidence |
|---|---|---|
| 9 | LifeLog: 1 = new data waiting, 0 = up to date | C (1 before a sync, 0 after; 0 on 16 Nov, "up to date") |
| 8 | ActivityLog: nonzero = workouts pending | S (external notes; value 5 seen on 16 Nov) |
| 2 | date-like value (0x1a/0x1b seen) | H |

The `0x28` message is labelled WATCH_CONDITION in two documents.

## 5. Frame format of the bulk stream (C)

Build the stream:
1. Strip the leading `05` and the trailing 2 bytes from every CONVOY notification.
2. Concatenate the rest.
3. XOR every byte with `0xFF`.

The result is the LifeLog stream: a 20-byte file header, then frames.

**File header (20 bytes)** — C for the fields listed:

| Offset | Size | Field |
|---|---|---|
| 0 | 5 | magic `00 0f 00 00 00` |
| 5 | 5 | time: year−2000, month, day, hour, minute (decimal, UTC) |
| 10 | 4 | payload length, u32 LE |
| 14 | 4 | steps today, i32 LE (u16 sufficed when bytes 16–17 are zero) |
| 18 | 2 | energy, u16 LE, raw units |

Caution: on 16 Nov the 4-byte steps read gave 75,764,969. The u16 read at offset 14 gave
4,925. Use u16, and reject values outside 0–100,000.

**Frames**: each frame is `type (1) | length (4, u32 LE) | body`. The length is the announced
size; the body on the wire can be shorter. Locate each frame by searching for its exact header
(`type + announced length`) in order, and take each frame's end as the start of the next one.

| Type | Announced size (example) | Content | Status |
|---|---|---|---|
| 0x65 | 99 | current stats: heart rate max/min/resting at body offsets 88/90/92, u16 LE, 0xFEFF = not available | C for max/min (matched the watch on 16 Nov, one day); resting H |
| 0x50 | 17 to 1185 | 5-minute steps: 4-byte records, u16 steps + u16 flag; newest first | C (sum matched app on 26 Oct) |
| 0x51 | same as 0x50 | 5-minute energy, same record layout, raw units | raw C; kcal scale U |
| 0x52 | 37 to 8645 | heart-rate samples, 4-byte records; first byte = bpm, 0xFE = none; roughly 2-minute spacing | C for values (plausible range); timestamps H |
| 0x53 | ~2021 | sleep stages | U |
| 0x56 | 53 to 12965 | activity records | U |
| 0x58 | 20 | breathing | U |
| 0x59 | 15 | SpO2 | U |
| 0x5A | 60 to 170 | sleep data | U |
| 0x5B | 19 to 47 | cardio load | U |
| 0x63 | 114 to 332 | daily summary, 109-byte records; BCD date at offset 0, BCD date-time at offset 102 | partly: layout U beyond these |
| 0x72 | 101 to 27653 | 5-minute samples, 32-byte records (marker `d9 f7`, one varying byte) | U |

Newest-first timing: slot i is `header_time − 5·i` minutes. The header time is stored in UTC.
Convert with `America/Toronto` (daylight saving applies).

## 6. Heart rate (C for max/min, plausible for recent samples)

- Daily max/min/resting: current-stats frame (0x65), bytes 88, 90, 92, u16 LE.
  Verified on 16 Nov (156 / 47 bpm, matching the watch display). Resting 55–62 bpm on the
  days read so far; not yet checked against the watch.
- Recent samples: frame 0x52, first byte of each 4-byte record. Values 30–220 plausible.
  These cover only a few minutes to a few hours, not a whole day.
- The watch's day average (95 on 16 Nov) has not been located in any frame.

## 7. Time setting (U, conflicting evidence)

- Older captures: a message `09 <year u16 LE> <month> <day> <hour> <minute> <second> <weekday>
  <2 unknown bytes>`, sent to STATUS. Weekday: Sunday = 0. The first nine bytes match the
  official app's write; the last two (`7a 01`, `8e 01`, `4d 01`) vary and are not understood.
- 3516 capture: `39 04` on the setup channel, labelled `CURRENT_TIME_MANAGER` by one document.
  Its payload is not known.

Do not write the clock until the `0x39` payload is captured from an official-app time sync.

## 8. Data model in the official app (S)

From the app's compiled strings (not the watch protocol):

- Daily log: `step`, `exercise`.
- Half-hour log: `step1`–`step4`, `exercise`, `option`. The meaning of the four step
  fields is unknown.
- Hour log: `step`, `exercise`.
- Activity (workout) log: average heart rate, average resting heart rate, heart-rate
  zones, calories, distance.
- Health Connect: the app requests Android health permissions and has conversion functions
  for steps and heart rate on other families (3515, 3552, 5554, 5594). No DW-H5600 mapping is
  visible.

## 9. Health Connect export (what is safe to write)

| Data | Ready? | Notes |
|---|---|---|
| Steps, day total | Yes, with care | Header steps; record start = local midnight, end = sync time. Replace the day's record on each sync rather than adding another. |
| Steps, 5-minute slots | Partly | Use only for display. Slots are incomplete on partial syncs. |
| Heart rate, max/min | Possible | Report as a watch daily value, one day checked. |
| Active calories | No | Needs the kcal conversion (raw units only). |
| Sleep, SpO2, breathing, cardio load | No | Layouts not decoded. |

## 10. Open items

1. Time-set command and payload (`0x39` vs `0x09`).
2. kcal conversion for energy (raw units): needs paired readings, watch or app, at several times.
3. Meaning of the four half-hour step fields and the 0x72 samples.
4. Resting heart-rate check and the day average field.
5. Sleep and SpO2 layouts: needs a sync after a night's sleep and a manual SpO2 reading.
6. The role of setup commands `22`, `1d`, `1e`, `3d`.
7. Timestamps of individual heart-rate samples in 0x52.

## 11. Sources

- Live syncs of 26 Oct 2026 (HCI capture `-4`) and 16 Nov 2026 (own script output).
- Repository `test_data/parse_lifelog.py` (field offsets for 0x63, 0x65, 0x52).
- Document set: 3516 handshake report (R5), command report (R9, R10), app-side strings
  (`dart_strings.txt`), firmware transport report (convoy_3516.md), and external issue #19
  for the status-byte role and handle.