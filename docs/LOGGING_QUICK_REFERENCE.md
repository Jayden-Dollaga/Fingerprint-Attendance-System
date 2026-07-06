# Logging System — Quick Reference

## What Was Implemented

A centralized logging system that replaces scattered `print()` statements throughout the codebase.

---

## Features

✅ **Colored Console Output**
- Info (white), Success (green), Warning (yellow), Error (red), Debug (cyan)

✅ **File Logging** (optional)
- Automatically saves to `data/logs/YYYY-MM-DD.log`
- Enable with one config change (no code modification needed)

✅ **Debug Mode** (optional)
- Shows detailed diagnostic messages
- Enable with one config change

✅ **Consistent Timestamps**
- Console: `[HH:MM:SS]`
- File: `YYYY-MM-DD HH:MM:SS`

---

## Setup (Already Done ✅)

1. Created `python/core/logger.py` — centralized logger module
2. Updated `python/config.py` — added logging configuration
3. All modules remain fully compatible

---

## Usage

### Import

```python
from core.logger import log
```

### Log Messages

```python
log.info("Basic information")
log.success("Operation succeeded")
log.warning("Something unexpected")
log.error("Operation failed")
log.debug("Detailed diagnostic info")
```

### Configuration

In `python/config.py`:

```python
# Enable file logging (saves to data/logs/YYYY-MM-DD.log)
LOG_TO_FILE = False  # Change to True to enable

# Enable debug output
ENABLE_DEBUG_LOGGING = False  # Change to True to enable

# Where logs are saved
LOG_FOLDER = str(DATA_DIR / "logs")
```

---

## Example Output

### Console (colored)

```
[22:45:17] [INFO    ] Application started
[22:45:18] [SUCCESS ] Connected to COM5
[22:45:20] [INFO    ] Starting scan mode
[22:45:25] [SUCCESS ] Fingerprint matched: ID 5
[22:45:26] [WARNING ] Low confidence detected
[22:45:27] [ERROR   ] Invalid student number
```

### File (`data/logs/2026-07-04.log`)

```
2026-07-04 22:45:17 [INFO    ] Application started
2026-07-04 22:45:18 [SUCCESS ] Connected to COM5
2026-07-04 22:45:20 [INFO    ] Starting scan mode
2026-07-04 22:45:25 [SUCCESS ] Fingerprint matched: ID 5
2026-07-04 22:45:26 [WARNING ] Low confidence detected
2026-07-04 22:45:27 [ERROR   ] Invalid student number
```

---

## Migration Path

**No immediate action required!** The system works with existing `print()` statements.

When you're ready, migrate core files:

1. **Core (High Priority)**
   - `python/core/serial_handler.py`
   - `python/core/database.py`
   - `python/core/commands.py`
   - `python/core/attendance.py`

2. **Services (Medium Priority)**
   - `python/services/excel_export.py`
   - `python/services/backup.py`

3. **Console (Optional)**
   - `python/main.py`

**GUI Note:** `python/gui/app.py` already uses a log widget, no changes needed.

---

## Before & After Example

### Before (scattered prints)

```python
# serial_handler.py
print(f"[SERIAL]  : Connecting to {port}...")
print("[SERIAL]  : Connected!")

# database.py
print(f"[DB]      : Ready — {path}")
```

### After (centralized logger)

```python
# serial_handler.py
from core.logger import log

log.info(f"Connecting to {port}...")
log.success("Connected!")

# database.py
from core.logger import log

log.success(f"Database ready at {path}")
```

**Benefits:**
- Consistent formatting
- Single import (`from core.logger import log`)
- Can redirect to file without code changes
- Easy to enable/disable debug mode

---

## Verification

The logger has been tested and verified:

✅ Module imports successfully  
✅ All log levels work (info, success, warning, error, debug)  
✅ Colored output displays correctly  
✅ File logging works (creates `data/logs/2026-07-04.log`)  
✅ Configuration options work  
✅ All core modules still import and function  

---

## Files

| File | Purpose |
|------|---------|
| `python/core/logger.py` | Logger implementation |
| `python/config.py` | Logging configuration |
| `docs/LOGGER_USAGE.md` | Detailed usage guide |
| `docs/LOGGING_QUICK_REFERENCE.md` | This file |

---

## Next Steps (Optional)

When ready to use the logger throughout the system:

1. Pick one module (e.g., `serial_handler.py`)
2. Replace `print()` calls with `log.info()`, `log.success()`, etc.
3. Test that module works
4. Move to next module
5. Enable `LOG_TO_FILE = True` when ready for production

No rush — the system works perfectly with or without it.

---

## Questions?

See `docs/LOGGER_USAGE.md` for comprehensive guide with examples.
