# Logger Usage Guide

## Overview

The project now has a centralized logging system that replaces scattered `print()` statements throughout the codebase.

**Benefits:**
- ✅ Colored console output (info, success, warning, error)
- ✅ Can redirect to files later without changing any code
- ✅ Consistent timestamp format
- ✅ Single configuration point for debug logging
- ✅ Easy to enable/disable file logging

---

## Quick Start

### Basic Usage

```python
from core.logger import log

# Different log levels
log.info("Application started")
log.success("Enrollment completed successfully")
log.warning("Low sensor confidence detected")
log.error("Failed to connect to COM port")
log.debug("Variable x = 5")  # Only shows if ENABLE_DEBUG_LOGGING = True
```

### Console Output

```
[22:45:17] [INFO    ] System initialized
[22:45:17] [SUCCESS ] All systems operational
[22:45:17] [WARNING ] Low confidence detected
[22:45:17] [ERROR   ] Connection failed
```

---

## Configuration

Edit `python/config.py` to control logging:

```python
# ── Logging ───────────────────────────────────────────────────────────────────
LOG_TO_FILE           = False               # Enable file logging
LOG_FOLDER            = str(DATA_DIR / "logs")  # Where to save logs
ENABLE_DEBUG_LOGGING  = False               # Show debug messages
```

### Enable File Logging

```python
LOG_TO_FILE = True
```

Then logs automatically save to `data/logs/YYYY-MM-DD.log` without any code changes.

### Enable Debug Logging

```python
ENABLE_DEBUG_LOGGING = True
```

Then all `log.debug()` calls will appear in output.

---

## Usage Examples

### Before (scattered print statements)

```python
# serial_handler.py
print(f"[SERIAL]  : Connecting to {port}...")
print("[SERIAL]  : Connected!")

# database.py
print(f"[DB]      : Ready — {os.path.abspath(DB_PATH)}")
```

### After (centralized logger)

```python
# serial_handler.py
from core.logger import log

log.info(f"Connecting to {port}...")
log.success("Connected!")

# database.py
from core.logger import log

log.success(f"Database ready at {os.path.abspath(DB_PATH)}")
```

---

## Log Levels

| Level | Color | Use Case | Example |
|-------|-------|----------|---------|
| `info()` | White | General information | "Scan mode started" |
| `success()` | Green | Operation succeeded | "Fingerprint enrolled" |
| `warning()` | Yellow | Something unexpected | "Low confidence match" |
| `error()` | Red | Operation failed | "COM port not found" |
| `debug()` | Cyan | Detailed diagnostic info | "Variable x = 100" |

---

## Files That Should Use Logger

### High Priority (Core)
- `python/core/serial_handler.py` — Replace print statements
- `python/core/database.py` — Replace print statements
- `python/core/commands.py` — Add logging for commands
- `python/core/attendance.py` — Add logging for scans

### Medium Priority (Services)
- `python/services/excel_export.py` — Add logging for exports
- `python/services/backup.py` — Add logging for backups

### GUI (Already Uses Log Display)
- `python/gui/app.py` — No changes needed, uses existing log widget

### Console
- `python/main.py` — Update startup messages

---

## Example: Updating serial_handler.py

**Before:**
```python
def connect(self, port=COM_PORT, timeout=1):
    try:
        self.serial = serial.Serial(port, BAUD_RATE, timeout=timeout)
        print(f"[SERIAL]  : {port} @ {BAUD_RATE} baud")
    except Exception as e:
        print(f"[SERIAL]  : ERROR — {e}")
```

**After:**
```python
from core.logger import log

def connect(self, port=COM_PORT, timeout=1):
    try:
        self.serial = serial.Serial(port, BAUD_RATE, timeout=timeout)
        log.success(f"{port} @ {BAUD_RATE} baud")
    except Exception as e:
        log.error(f"Failed to connect — {e}")
```

---

## Example: Updating database.py

**Before:**
```python
def init_database():
    # ... create tables ...
    print(f"[DB]      : Ready — {os.path.abspath(DB_PATH)}")
```

**After:**
```python
from core.logger import log

def init_database():
    # ... create tables ...
    log.success(f"Database ready at {os.path.abspath(DB_PATH)}")
```

---

## File Logging Example

Once you enable file logging:

```python
# config.py
LOG_TO_FILE = True
```

Every log message is automatically saved to `data/logs/2026-07-04.log`:

```
2026-07-04 22:45:17 [INFO    ] System initialized
2026-07-04 22:45:17 [SUCCESS ] Connected to COM5
2026-07-04 22:45:18 [INFO    ] Starting scan mode
2026-07-04 22:45:20 [SUCCESS ] Fingerprint matched: ID 5
2026-07-04 22:45:22 [WARNING ] Low confidence: 85 < 100
```

**No code changes needed** — this works automatically!

---

## Advanced: Debug Logging

For troubleshooting, enable debug output:

```python
# config.py
ENABLE_DEBUG_LOGGING = True
```

Then use `log.debug()` for detailed information:

```python
log.debug(f"Fingerprint ID: {fp_id}")
log.debug(f"Confidence value: {confidence}")
log.debug(f"Database query result: {rows}")
```

Debug messages only appear when enabled, so you can leave them in production code.

---

## Why This Matters

### Before (Scattered Prints)
```
[SERIAL]  : Connected!
[DB]      : Ready
Enrollment starting...
Place finger...
ID FOUND: 5
Enrolling as ID #7
SUCCESS! Finger saved as ID #7
```

⚠️ Hard to distinguish log sources  
⚠️ No timestamps  
⚠️ No file logging option  
⚠️ Print statements scattered everywhere

### After (Centralized Logger)
```
[22:45:17] [SUCCESS ] Connected to COM5
[22:45:18] [SUCCESS ] Database ready
[22:45:20] [INFO    ] Enrollment started
[22:45:25] [INFO    ] Fingerprint detected
[22:45:30] [SUCCESS ] Enrolled as ID #7
```

✅ Consistent format  
✅ Automatic timestamps  
✅ Color-coded by level  
✅ Can save to file automatically  
✅ Single configuration point  

---

## Next Steps

1. ✅ Logger module created (`python/core/logger.py`)
2. ✅ Configuration added (`python/config.py`)
3. ⏳ Update core files to use logger (when ready)
4. ⏳ Enable file logging in production (when ready)

The logger is **ready to use immediately**. You can start using it in new code, and gradually migrate old `print()` statements when convenient.

---

## Testing the Logger

```bash
cd python
python -c "
import sys
sys.path.insert(0, '.')
from core.logger import log

log.info('Test info')
log.success('Test success')
log.warning('Test warning')
log.error('Test error')
log.debug('Test debug')
"
```

---

## Questions?

Refer to `python/core/logger.py` for complete implementation details and docstrings.
