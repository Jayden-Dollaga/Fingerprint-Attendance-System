# Migration Example: serial_handler.py

## Goal

Show how to migrate from `print()` statements to the centralized logger.

---

## Current State (with print)

```python
# python/core/serial_handler.py

import serial
import threading
from config import COM_PORT, BAUD_RATE

class SerialHandler:
    def __init__(self):
        self.serial = None
        self.connected = False
        self.data_thread = None
    
    def connect(self, port=COM_PORT, timeout=1):
        try:
            self.serial = serial.Serial(port, BAUD_RATE, timeout=timeout)
            print(f"[SERIAL]  : {port} @ {BAUD_RATE} baud")  # ← print statement
            self.connected = True
        except Exception as e:
            print(f"[SERIAL]  : ERROR — {e}")  # ← print statement
            self.connected = False
    
    def disconnect(self):
        if self.serial:
            self.serial.close()
            print("[SERIAL]  : Disconnected")  # ← print statement
            self.connected = False
    
    def send_command(self, command):
        if not self.connected:
            print("[SERIAL]  : Not connected!")  # ← print statement
            return
        self.serial.write(f"{command}\n".encode())
        print(f"[SERIAL]  : Sent → {command}")  # ← print statement
```

**Issues:**
- Scattered `print()` calls
- Hard to control verbosity
- Can't redirect to file
- Inconsistent timestamp format

---

## Migrated State (with logger)

```python
# python/core/serial_handler.py

import serial
import threading
from config import COM_PORT, BAUD_RATE
from core.logger import log  # ← Add this import

class SerialHandler:
    def __init__(self):
        self.serial = None
        self.connected = False
        self.data_thread = None
    
    def connect(self, port=COM_PORT, timeout=1):
        try:
            self.serial = serial.Serial(port, BAUD_RATE, timeout=timeout)
            log.success(f"{port} @ {BAUD_RATE} baud")  # ← log.success()
            self.connected = True
        except Exception as e:
            log.error(f"Connection failed — {e}")  # ← log.error()
            self.connected = False
    
    def disconnect(self):
        if self.serial:
            self.serial.close()
            log.info("Disconnected")  # ← log.info()
            self.connected = False
    
    def send_command(self, command):
        if not self.connected:
            log.warning("Not connected!")  # ← log.warning()
            return
        self.serial.write(f"{command}\n".encode())
        log.info(f"Sent → {command}")  # ← log.info()
```

**Benefits:**
- ✅ One import line
- ✅ Consistent method names (`log.success()`, `log.error()`, etc.)
- ✅ Automatic timestamps
- ✅ Can redirect to file with config change
- ✅ Debug mode can be enabled globally
- ✅ Colored output automatically

---

## Output Comparison

### Before (with print)

```
[SERIAL]  : COM5 @ 115200 baud
[SERIAL]  : Sent → SCAN
[SERIAL]  : Not connected!
[SERIAL]  : Disconnected
```

**Problems:**
- No timestamps
- Manual formatting
- Can't filter by log level
- Can't save to file

### After (with logger)

```
[22:45:17] [SUCCESS ] COM5 @ 115200 baud
[22:45:18] [INFO    ] Sent → SCAN
[22:45:20] [WARNING ] Not connected!
[22:45:22] [INFO    ] Disconnected
```

**Advantages:**
- ✅ Automatic timestamps
- ✅ Color-coded by level
- ✅ Consistent formatting
- ✅ Can save to file without code changes
- ✅ Can filter by level (disable warnings, show only errors, etc.)

---

## File Output (Optional)

Enable in `python/config.py`:

```python
LOG_TO_FILE = True
```

Then `data/logs/2026-07-04.log` automatically contains:

```
2026-07-04 22:45:17 [SUCCESS ] COM5 @ 115200 baud
2026-07-04 22:45:18 [INFO    ] Sent → SCAN
2026-07-04 22:45:20 [WARNING ] Not connected!
2026-07-04 22:45:22 [INFO    ] Disconnected
```

**No code changes needed!**

---

## Migration Checklist

To migrate `serial_handler.py` (or any module):

- [ ] Add import: `from core.logger import log`
- [ ] Replace `print(f"[SERIAL]  : ...")` with `log.info(...)`
- [ ] Replace `print(f"[SERIAL]  : ERROR — ...")` with `log.error(...)`
- [ ] Replace `print("[SERIAL]  : ...")` with `log.success()` (for positive messages)
- [ ] Test that module works
- [ ] Commit changes

---

## Summary of Changes

| Old Code | New Code | Benefit |
|----------|----------|---------|
| `print(f"[SERIAL]  : {msg}")` | `log.info(f"{msg}")` | Consistent format, auto-timestamp |
| `print(f"[SERIAL]  : ERROR — {e}")` | `log.error(f"{e}")` | Color-coded, can filter/archive |
| `print("[SERIAL]  : Message")` | `log.success("Message")` | Color-coded success (green) |
| None | `log.warning("Text")` | Warning level (yellow) |
| None | `log.debug("Details")` | Debug mode (cyan, optional) |

---

## Pro Tips

1. **Info** — Use for general messages (connection, mode changes)
   ```python
   log.info("Starting scan mode")
   ```

2. **Success** — Use for operations that succeeded
   ```python
   log.success("Fingerprint enrolled successfully")
   ```

3. **Warning** — Use for unexpected but handled situations
   ```python
   log.warning("Low confidence score detected")
   ```

4. **Error** — Use for failures
   ```python
   log.error(f"Failed to connect: {e}")
   ```

5. **Debug** — Use for detailed diagnostic info (only shows if `ENABLE_DEBUG_LOGGING=True`)
   ```python
   log.debug(f"Confidence value: {conf}")
   ```

---

## Real-World Example

Before:
```python
def handle_fingerprint_match(fingerprint_id, confidence):
    if confidence < MIN_CONFIDENCE:
        print(f"[ATTENDANCE] : Low confidence {confidence}")
        return
    
    student = get_student(fingerprint_id)
    if not student:
        print(f"[ATTENDANCE] : Unknown ID {fingerprint_id}")
        return
    
    log_attendance(fingerprint_id, confidence, "GOOD MATCH")
    print(f"[ATTENDANCE] : {student['name']} checked in")
```

After:
```python
from core.logger import log

def handle_fingerprint_match(fingerprint_id, confidence):
    if confidence < MIN_CONFIDENCE:
        log.warning(f"Low confidence: {confidence} < {MIN_CONFIDENCE}")
        return
    
    student = get_student(fingerprint_id)
    if not student:
        log.error(f"Unknown fingerprint ID: {fingerprint_id}")
        return
    
    log_attendance(fingerprint_id, confidence, "GOOD MATCH")
    log.success(f"{student['name']} checked in")
```

**Output:**
```
[22:45:20] [WARNING ] Low confidence: 85 < 100
[22:45:22] [ERROR   ] Unknown fingerprint ID: 99
[22:45:24] [SUCCESS ] Jayden Reyes checked in
```

---

## Next Module to Migrate

Once you're comfortable with the pattern, migrate:

1. ✅ `serial_handler.py` (example above)
2. 📝 `database.py` — Replace `print()` startup messages
3. 📝 `commands.py` — Add logging for each command
4. 📝 `attendance.py` — Log scan processing
5. 📝 `excel_export.py` — Log export progress

Each follows the same pattern:
- Add `from core.logger import log`
- Replace `print()` with `log.*()` calls
- Test
- Done!

---

## Questions?

Refer to:
- `docs/LOGGER_USAGE.md` — Comprehensive usage guide
- `docs/LOGGING_QUICK_REFERENCE.md` — Quick reference
- `python/core/logger.py` — Implementation details
