# Logging Guide

The project uses a centralized Python logger so events from the GUI, serial handler, and database layer are captured in one place.

## Where logs go

- Console output: shown in the terminal or app console
- File output: written to the data logs folder when enabled in the configuration

Default log location:
- data/logs/YYYY-MM-DD.log

## Configuration

The logger behavior is controlled in [python/config.py](../python/config.py).

Key settings:
- LOG_TO_FILE: enable or disable file logging
- LOG_FOLDER: directory for log files
- ENABLE_DEBUG_LOGGING: include extra debug messages

## How to use it

Import the shared logger:

```python
from core.logger import log
```

Common usage:

```python
log.info("System started")
log.success("Fingerprint saved")
log.warning("Low confidence score")
log.error("Connection failed")
```

## What gets logged

Typical entries include:
- ESP32 connection events
- Scan results and attendance saves
- Enrollment progress and cancellations
- Database resets and backup actions
- Errors from serial communication or GUI actions

### Reconnect / Connection status

The serial layer logs reconnect attempts and outcomes. Typical messages you will see:

- `log.warning("Attempting reconnect ({n}/{max}) in {delay}s...")` — scheduled retry with backoff
- `log.warning("Auto-reconnect attempt {n} failed: {msg}")` — a retry failed
- `log.success("Auto-reconnect successful")` — reconnect succeeded
- `log.error("Auto-reconnect failed after {max} attempts")` — max retries reached

The GUI also reflects reconnect progress by observing `serial_handler.reconnect_count` and writing user-oriented messages via `log_message()` (which delegates to the shared logger).

When troubleshooting intermittent disconnects, enable `ENABLE_DEBUG_LOGGING` and review the sequence of reconnect warnings and any underlying serial exceptions. These entries usually reveal whether the device is unreachable, the port closed unexpectedly, or the firmware is spamming unexpected output.

### Backup & Restore

Backup and restore operations are logged at the time they run. Example messages:

- `log.success(f"Database backed up to {path}")` — successful backup (includes full path)
- `log.error(f"Database backup failed: {e}")` — failure during backup
- `log.success(f"Database restored from {backup_path}")` — successful restore
- `log.error(f"Database restore failed: {e}")` — restore failure

The GUI surfaces these outcomes in dialogs but you should always check the log file for the full exception text on failures. Restores replace the active DB file; therefore successful restore entries are critical to confirm data state changes.

### Recommended log levels

- `DEBUG`: Low-level serial I/O, detailed reconnect backoff timing (enable only when troubleshooting)
- `INFO` / `SUCCESS`: Normal lifecycle events (connect, disconnect, backup created, restore completed)
- `WARNING`: Reconnect attempts, recoverable sensor warnings
- `ERROR` / `CRITICAL`: Failed commands, unrecoverable IO errors, failed backups/restores

## Useful tips

## Useful tips

- Keep log files for troubleshooting and audits
- Review the daily log if a scan or enrollment fails
- Enable debug logging when investigating serial or firmware issues
 - When investigating reconnects, search for `Attempting reconnect` and follow the subsequent `failed`/`successful` messages in the same log file
 - For backup/restore issues, copy the timestamped log lines around the operation and include the backup filename when requesting support
