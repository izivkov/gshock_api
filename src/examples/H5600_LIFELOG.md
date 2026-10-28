# h5600_health.py: notes

`h5600_health.py` is the only script these notes cover. It lives in
`src/examples/` on the `h5600_health` branch of `izivkov/gshock_api`. It uses
the `gshock_api` library for the Bluetooth link and has no other local imports.

---

## 1. What it does

The script gets LifeLog data from a DW-H5600 in one of two ways:

- **Live:** it connects to the watch, runs the sync protocol, and saves every
  message it sent and received.
- **Replay:** it reads a btsnoop capture from a previous sync and rebuilds the
  same session from it.

In both cases it then decodes what it can (the header, steps, and raw energy),
prints the results, and writes one JSON file.

---

## 2. Setup

1. Check out the `h5600_health` branch of `gshock_api` and install its
   environment:

       cd ~/projects/gshock_api
       git checkout h5600_health
       uv sync

2. Pair the watch with the computer once. Without a bond the watch never
   reaches the transfer state. Check with:

       bluetoothctl info <watch address>

   Expect `Paired: yes`, `Bonded: yes`, and `Trusted: yes`. If not:

       bluetoothctl
       power on
       agent on
       default-agent
       scan on            # wait for the DW-H5600 to appear
       pair <address>
       trust <address>
       quit

3. Close the official Casio app on the phone, or turn off its Bluetooth, so
   two clients are not connected to the watch at once.

The watch needs no button press or menu step. The official app starts a sync
as soon as it connects.

---

## 3. Running it

Run from the `gshock_api` checkout root with `uv run`.

Live watch:

    uv run src/examples/h5600_health.py --setup

Live watch at a known address:

    uv run src/examples/h5600_health.py --setup --address <address>

Replay a capture (no watch needed):

    uv run src/examples/h5600_health.py --hci btsnoop_hci_DW-H5600-4.log

Options:

| Option | Default | What it does |
|---|---|---|
| `--address ADDR` | library scan | connect to this address; without it, the library scans for the watch |
| `--setup` | off | send the setup requests before the poll. **Needed for a live sync.** |
| `--set-time` | off | write this computer's time to the watch before the poll (needs `--setup`) |
| `--hci FILE` | none | replay a btsnoop capture instead of connecting |
| `--json PATH` | `h5600_lifelog.json` | output file. Overwritten on every run |
| `--tz N` | -4 | local time offset in hours, used for the local times on screen and in the JSON |
| `--quiet` | off | no screen output; only the JSON file is written |

---

## 4. Live sync: what the script sends and expects

With `--setup`, the script runs this sequence. Each step waits for the reply
before the next.

1. **Setup requests.** One-byte requests, in order: `23 10 11 3b 3a 26 28 20 2f 43 13 45`.
   Each goes to the SETUP characteristic (found on the watch by handle and
   properties), and the script waits up to 5 s for a STATUS reply that starts
   with the same byte. Replies to `11 3b 3a 2f 13 45` are written back to STATUS
   unchanged, as the official app does.
2. **Early START.** `00 2e ff ff ff ff ff` on DRSP. The watch acknowledges it
   later, after it is ready.
3. **Poll.** `00 00 00` on CONVOY.
   - `00 01 xx` means busy. The script waits 3.5 s and polls again.
   - `00 00 00` means ready.
4. **Setup exchange.** `04 00 00 … 00` (10 bytes) on CONVOY, then
   `04 01 18 00 18 00 00 00 dc 05` after the first `04 00 28` reply, then
   `06 00 … 00` (14 bytes) after the second.
5. **Echo of the `06` reply.** The watch replies with a 9-byte `06 xx …`. The
   script echoes it on CONVOY. The second byte varies between sessions (`fa` and
   `17` have both been seen), so any 9-byte `06` reply is accepted.
6. **Transfer starts.** The next `06` reply triggers the real START on DRSP.
   The watch then announces index `00` with `00 2e 00 14 00 00 00`.
7. **Bulk transfer.** For each index announcement `00 2e <idx> <len>` on DRSP,
   the script echoes it. Bulk data arrives on CONVOY as `05 …` notifications;
   each one is acknowledged with `07 00 … 00` (15 bytes). When an index is
   complete, the watch sends `07 2e <idx> <len>` on DRSP, and the script echoes
   that too.
8. **End.** The watch sends `04 2e ff …` on DRSP. The script echoes it and stops.

If the watch stays busy, the script keeps polling until the 180 s overall
timeout. If the link drops, the script stops and records the error.

---

## 5. Replay: what `--hci` does

A btsnoop capture can hold several sync attempts. The script:

1. Reads every ATT message on the four handles it uses (0x10 DRSP, 0x13 CONVOY,
   0x18 STATUS, 0x16 SETUP) in order.
2. Splits the messages at each START write (`00 2e ff …`).
3. Keeps the attempt that ends in END and has the most bulk data.
4. Keeps the poll and setup messages from just before that START, plus everything
   up to and including END.

The result has the same structure as a live session.

---

## 6. Decoding

The script builds the LifeLog byte stream from the CONVOY bulk notifications:

1. Strip the `05` prefix and the 2-byte checksum from each notification.
2. Concatenate the payloads.
3. XOR every byte with `0xFF`.

The stream starts with a 20-byte header (`00 0f 00 00 00 …`), followed by frames.
Each frame begins with a type byte and a 4-byte length. The length is the
buffer size the watch announced, and the frame can be shorter. The script finds
each frame by searching for its exact header (type plus announced length), not by
counting from the length.

What is decoded:

- **Header.** Time (stored in UTC; the local time uses `--tz`), steps for the
  day, and energy (raw).
- **Steps (frame `50`).** 4-byte records: a uint16 step count and a uint16 flag.
  Records are newest first: record *i* is 5×*i* minutes before the header time.
  Values above 1000 are treated as no data.
- **Energy (frame `51`).** Same layout and timing as steps. Values above 5000 are
  treated as no data. The raw values are shown; the kcal conversion is not
  confirmed.

What is located but not decoded: `52` (heart rate), `53` (sleep), `56`
(activity), `58`, `59`, `5a`, `5b`, `63` (daily summary), `65` (current stats),
and `72` (5-minute samples). The script reports each frame's position and the
number of bytes it received.

---

## 7. Output

### JSON file

Written to `--json` (default `h5600_lifelog.json`), overwritten on every run. The
file is saved during the transfer as well, so a partial session survives a failure.

Top-level fields:

- `format`: `"h5600_lifelog_session"`, `version`: 2
- `source`: `"ble:<address>"` or `"hci:<file name>"`
- `started`, `ended`, `finished`, `error`
- `events`: every message, each with `dir` (`TX` or `RX`), `uuid` (short name:
  `DRSP`, `CONVOY`, `STATUS`, or `SETUP`), `handle` (replay only), `hex`, and
  `t` (live only: Unix time)
- `announcements`: the index and 3-byte value the watch announced for each frame

### Screen

Unless `--quiet` is set, the script prints:

- **Session:** source, start and end times, finished flag, error if any
- **Messages:** count of each direction and characteristic
- **Announced frames:** each index with its announced length
- **Status 0x28 (last 3):** the last status messages, with bytes 8 and 9
- **Decoded (partial):** header time (UTC and local), header steps, header energy,
  step slots with their sum, and steps by local hour
- **Frames located:** each frame's start offset and bytes received

During a live run, every message is also printed as it happens, as `TX` or `RX`,
the short name, and the first bytes of the hex.

---

## 8. Status

| Item | Status |
|---|---|
| Live sync completes | yes. One run received all 11 frame types, and the watch accepted END |
| Replay of `-4` capture | steps sum 624, matching the app; hourly split matches the app chart |
| Latest live run, steps | **does not match:** header 4,733, slot sum 120, all in the 19:00 hour. Not resolved |
| Header time | stored in UTC; matches the local clock with `--tz -4` |
| Energy | raw values; kcal scale not confirmed |
| Other frames | located, not decoded |

---

## 9. Known issues

1. **Step total mismatch** on the latest live run (see §8). The decoder may be
   dropping valid values, or mapping them to the wrong times. It needs the JSON
   from that run and the app's totals for the same day to check.
2. **The live sync needs a bond.** Without a bond, the watch never leaves busy.
3. **The `06` reply's second byte varies.** The script accepts any 9-byte `06`
   reply. Its meaning is not known.
4. **The time write** (`--set-time`) sends the first nine bytes as the official
   app does, followed by `00 00`. The last two bytes in the app's write vary
   between captures and are not understood. The script does not need this write
   for the live sync to complete, so it is off by default.
5. **The LifeLog flag does not clear.** The status message's byte 9 stayed `1`
   after a completed sync, so the flag cannot be used to decide when to sync.
6. **The MTU is not set.** The official app negotiated a larger MTU. The script
   does not, and the sync completed anyway.

---

## 10. Dependencies

- Python 3.10 or later, run with `uv`.
- `gshock_api` from the `h5600_health` branch, which brings in `bleak`.
- The standard library for everything else (`asyncio`, `struct`, `json`, `dataclasses`).