###############################################################################
#  database.py
#  AS608 Fingerprint Attendance System
#
#  All database operations live here.
#  Tables:
#    students   - maps fingerprint ID to student info
#    attendance - normalized scan logs (fingerprint_id + scan data only)
###############################################################################

import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import DB_PATH
from core.logger import log

# Chart generation
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-GUI backend
    import matplotlib.pyplot as plt
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False


def get_connection() -> sqlite3.Connection:
    """Open and return a database connection. Creates DB file if not exists."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Rows accessible by column name
    return conn


def init_database() -> None:
    """Create tables if they don't exist. Safe to call every startup."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── Students table ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            fingerprint_id  INTEGER PRIMARY KEY,
            student_no      TEXT    NOT NULL UNIQUE,
            student_name    TEXT    NOT NULL,
            grade           TEXT    NOT NULL,
            section         TEXT    NOT NULL,
            enrollment_date TEXT    NOT NULL,
            updated_date    TEXT    NOT NULL
        )
    """)

    # ── Indexes on students table for faster lookups ───────────────────────────
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_student_no
        ON students(student_no)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_grade_section
        ON students(grade, section)
    """)

    # ── Attendance table ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint_id  INTEGER NOT NULL,
            date            TEXT    NOT NULL,
            time            TEXT    NOT NULL,
            confidence      INTEGER NOT NULL,
            status          TEXT    NOT NULL,
            timestamp       TEXT    NOT NULL,
            FOREIGN KEY (fingerprint_id) REFERENCES students(fingerprint_id)
        )
    """)

    # ── Indexes on attendance table for faster queries ──────────────────────────
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_attendance_fingerprint_id
        ON attendance(fingerprint_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_attendance_date
        ON attendance(date)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_attendance_timestamp
        ON attendance(timestamp)
    """)

    # Protect the sentinel fingerprint ID from being treated as a real student profile.
    conn.execute("DELETE FROM students WHERE fingerprint_id <= 0")

    conn.commit()
    conn.close()
    log.success(f"Database ready at {os.path.abspath(DB_PATH)}")


# ==============================================================================
#  STUDENT OPERATIONS
# ==============================================================================

def add_student(fingerprint_id: int, student_no: str, student_name: str, grade: str, section: str) -> Tuple[bool, str]:
    """
    Add a new student to the database.
    Automatically sets enrollment_date and updated_date to current time.
    Returns (True, "OK") on success or (False, error message) on failure.
    """
    if fingerprint_id is None or int(fingerprint_id) <= 0:
        return False, "Fingerprint ID must be a positive integer."

    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO students 
            (fingerprint_id, student_no, student_name, grade, section, enrollment_date, updated_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (fingerprint_id, student_no, student_name, grade, section, now, now))
        conn.commit()
        return True, "OK"
    except sqlite3.IntegrityError as e:
        if "fingerprint_id" in str(e):
            return False, f"Fingerprint ID {fingerprint_id} already assigned to a student."
        if "student_no" in str(e):
            return False, f"Student number {student_no} already exists."
        return False, str(e)
    finally:
        conn.close()


def update_student(fingerprint_id: int, student_no: str, student_name: str, grade: str, section: str) -> Tuple[bool, str]:
    """
    Update an existing student's info by fingerprint ID.
    Automatically updates the updated_date to current time.
    """
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE students
            SET student_no=?, student_name=?, grade=?, section=?, updated_date=?
            WHERE fingerprint_id=?
        """, (student_no, student_name, grade, section, now, fingerprint_id))
        conn.commit()
        return True, "OK"
    except sqlite3.IntegrityError as e:
        return False, str(e)
    finally:
        conn.close()


def delete_student(fingerprint_id: int) -> None:
    """Delete a student by fingerprint ID."""
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE fingerprint_id = ?", (fingerprint_id,))
    conn.commit()
    conn.close()


def clear_all_students() -> int:
    """Delete every student profile and return the number removed."""
    conn = get_connection()
    try:
        students = get_all_students()
        conn.execute("DELETE FROM students")
        conn.commit()
        return len(students)
    finally:
        conn.close()


def get_student(fingerprint_id: int) -> Optional[Dict[str, Any]]:
    """Get one student by fingerprint ID. Returns dict or None."""
    if fingerprint_id is None or int(fingerprint_id) <= 0:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE fingerprint_id = ?", (fingerprint_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_students() -> List[Dict[str, Any]]:
    """Get all students ordered by fingerprint ID. Returns list of dicts."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM students ORDER BY fingerprint_id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_count() -> int:
    """Return total number of students in database."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    conn.close()
    return count


def register_student(fingerprint_id: int, student_no: str, student_name: str, grade: str, section: str) -> Tuple[bool, str]:
    """
    Register a student — adds if new, updates if fingerprint_id already exists.
    Use this instead of add_student() when you want upsert behavior.
    """
    existing = get_student(fingerprint_id)
    if existing:
        return update_student(fingerprint_id, student_no, student_name, grade, section)
    return add_student(fingerprint_id, student_no, student_name, grade, section)


def import_students_from_list(students: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk import students from a list of dicts.
    Each dict must have: fingerprint_id, student_no, student_name, grade, section

    Example:
        import_students_from_list([
            {"fingerprint_id": 1, "student_no": "2026001",
             "student_name": "Jayden", "grade": "12", "section": "STEM-A"},
        ])
    """
    results = {"success": 0, "failed": 0, "errors": []}
    for s in students:
        ok, msg = register_student(
            s["fingerprint_id"], s["student_no"],
            s["student_name"], s["grade"], s["section"]
        )
        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(f"ID {s['fingerprint_id']}: {msg}")
    return results


# ==============================================================================
#  ATTENDANCE OPERATIONS
# ==============================================================================

def log_attendance(fingerprint_id: int, confidence: int, status: str, now: Optional[datetime] = None) -> None:
    """
    Save one attendance scan to database.
    now: datetime object (defaults to current time if not provided)
    """
    if now is None:
        now = datetime.now()
    
    timestamp = now.isoformat()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    conn = get_connection()
    conn.execute("""
        INSERT INTO attendance (fingerprint_id, date, time, confidence, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fingerprint_id, date_str, time_str, confidence, status, timestamp))
    conn.commit()
    conn.close()


def get_attendance_today() -> List[Dict[str, Any]]:
    """
    Get today's attendance records with student info via JOIN.
    Returns list of dicts.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    conn  = get_connection()
    rows  = conn.execute("""
        SELECT
            a.id,
            a.fingerprint_id,
            COALESCE(s.student_no,   'N/A')             AS student_no,
            CASE WHEN a.fingerprint_id = 0 THEN 'Unregistered' ELSE COALESCE(s.student_name, 'Unknown ID:' || a.fingerprint_id) END AS student_name,
            COALESCE(s.grade,        'N/A')             AS grade,
            COALESCE(s.section,      'N/A')             AS section,
            a.date,
            a.time,
            a.confidence,
            a.status
        FROM attendance a
        LEFT JOIN students s ON a.fingerprint_id = s.fingerprint_id
        WHERE a.date = ?
        ORDER BY a.timestamp DESC
    """, (today,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_all() -> List[Dict[str, Any]]:
    """
    Get ALL attendance records with student info via JOIN.
    Returns list of dicts.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            a.id,
            a.fingerprint_id,
            COALESCE(s.student_no,   'N/A')             AS student_no,
            CASE WHEN a.fingerprint_id = 0 THEN 'Unregistered' ELSE COALESCE(s.student_name, 'Unknown ID:' || a.fingerprint_id) END AS student_name,
            COALESCE(s.grade,        'N/A')             AS grade,
            COALESCE(s.section,      'N/A')             AS section,
            a.date,
            a.time,
            a.confidence,
            a.status
        FROM attendance a
        LEFT JOIN students s ON a.fingerprint_id = s.fingerprint_id
        ORDER BY a.timestamp DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_paginated(limit=100, offset=0):
    """Return attendance rows ordered by timestamp desc with LIMIT/OFFSET."""
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT
            a.id,
            a.fingerprint_id,
            CASE WHEN a.fingerprint_id = 0 THEN 'Unregistered' ELSE COALESCE(s.student_no, 'N/A') END AS student_no,
            CASE WHEN a.fingerprint_id = 0 THEN 'Unregistered' ELSE COALESCE(s.student_name, 'Unknown ID:' || a.fingerprint_id) END AS student_name,
            CASE WHEN a.fingerprint_id = 0 THEN 'N/A' ELSE COALESCE(s.grade, 'N/A') END AS grade,
            CASE WHEN a.fingerprint_id = 0 THEN 'N/A' ELSE COALESCE(s.section, 'N/A') END AS section,
            a.date,
            a.time,
            a.confidence,
            a.status
        FROM attendance a
        LEFT JOIN students s ON a.fingerprint_id = s.fingerprint_id
        ORDER BY a.timestamp DESC
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_count_today():
    """Return number of scans logged today."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn  = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE date = ?", (today,)
    ).fetchone()[0]
    conn.close()
    return count


def get_attendance_by_date(date_str):
    """
    Get attendance for a specific date (format: YYYY-MM-DD).
    Returns list of dicts with student info joined.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            a.id,
            a.fingerprint_id,
            COALESCE(s.student_no,   'N/A')             AS student_no,
            CASE WHEN a.fingerprint_id = 0 THEN 'Unregistered' ELSE COALESCE(s.student_name, 'Unknown ID:' || a.fingerprint_id) END AS student_name,
            COALESCE(s.grade,        'N/A')             AS grade,
            COALESCE(s.section,      'N/A')             AS section,
            a.date,
            a.time,
            a.confidence,
            a.status
        FROM attendance a
        LEFT JOIN students s ON a.fingerprint_id = s.fingerprint_id
        WHERE a.date = ?
        ORDER BY a.time
    """, (date_str,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==============================================================================
#  ADDITIONAL ATTENDANCE & REPORTING OPERATIONS
# ==============================================================================

def clear_all_attendance():
    """
    Delete ALL attendance records from database.
    Useful for archiving or resetting. Returns count of records deleted.
    WARNING: This is permanent!
    """
    conn = get_connection()
    try:
        records = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
        conn.execute("DELETE FROM attendance")
        conn.commit()
        return records
    finally:
        conn.close()


def clear_all_data():
    """
    Delete all student profiles and all attendance records.
    Returns a tuple of (student_count, attendance_count).
    """
    conn = get_connection()
    try:
        student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        attendance_count = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
        conn.execute("DELETE FROM students")
        conn.execute("DELETE FROM attendance")
        conn.commit()
        return student_count, attendance_count
    finally:
        conn.close()


def get_attendance_by_student(fingerprint_id):
    """
    Get all attendance records for a specific student (by fingerprint ID).
    Returns list of dicts with metadata.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            a.id,
            a.fingerprint_id,
            COALESCE(s.student_no,   'N/A')             AS student_no,
            CASE WHEN a.fingerprint_id = 0 THEN 'Unregistered' ELSE COALESCE(s.student_name, 'Unknown ID:' || a.fingerprint_id) END AS student_name,
            COALESCE(s.grade,        'N/A')             AS grade,
            COALESCE(s.section,      'N/A')             AS section,
            a.date,
            a.time,
            a.confidence,
            a.status
        FROM attendance a
        LEFT JOIN students s ON a.fingerprint_id = s.fingerprint_id
        WHERE a.fingerprint_id = ?
        ORDER BY a.date DESC, a.time DESC
    """, (fingerprint_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_students_by_grade_section(grade, section):
    """
    Get all students in a specific grade and section.
    Returns list of dicts.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM students
        WHERE grade = ? AND section = ?
        ORDER BY student_name
    """, (grade, section)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_attendance_by_date(date_str):
    """
    Count number of attendance records for a given date.
    date_str format: YYYY-MM-DD
    """
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE date = ?", (date_str,)
    ).fetchone()[0]
    conn.close()
    return count


def get_attendance_statistics():
    """
    Get summary statistics about attendance data.
    Returns dict with counts and breakdown by status.
    """
    conn = get_connection()
    
    total = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    unique_students = conn.execute(
        "SELECT COUNT(DISTINCT fingerprint_id) FROM attendance"
    ).fetchone()[0]
    
    # Count by status
    status_counts = {}
    rows = conn.execute("""
        SELECT status, COUNT(*) as count
        FROM attendance
        GROUP BY status
    """).fetchall()
    for row in rows:
        status_counts[row["status"]] = row["count"]
    
    # Average confidence
    avg_confidence = conn.execute(
        "SELECT AVG(confidence) FROM attendance"
    ).fetchone()[0]
    avg_confidence = round(avg_confidence, 2) if avg_confidence else 0
    
    # Date range
    date_info = conn.execute("""
        SELECT MIN(date) as earliest, MAX(date) as latest
        FROM attendance
    """).fetchone()
    
    conn.close()
    
    return {
        "total_scans": total,
        "unique_students": unique_students,
        "status_breakdown": status_counts,
        "average_confidence": avg_confidence,
        "earliest_date": date_info["earliest"],
        "latest_date": date_info["latest"],
    }


def get_students_statistics():
    """
    Get summary statistics about enrolled students.
    Returns dict with counts by grade and section.
    """
    conn = get_connection()
    
    total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    
    # Count by grade
    grade_counts = {}
    rows = conn.execute("""
        SELECT grade, COUNT(*) as count
        FROM students
        GROUP BY grade
        ORDER BY grade
    """).fetchall()
    for row in rows:
        grade_counts[row["grade"]] = row["count"]
    
    # Count by section
    section_counts = {}
    rows = conn.execute("""
        SELECT section, COUNT(*) as count
        FROM students
        GROUP BY section
        ORDER BY section
    """).fetchall()
    for row in rows:
        section_counts[row["section"]] = row["count"]
    
    conn.close()
    
    return {
        "total_students": total,
        "by_grade": grade_counts,
        "by_section": section_counts,
    }


def export_attendance_range(start_date, end_date):
    """
    Export attendance records for a date range.
    Dates format: YYYY-MM-DD
    Returns list of dicts suitable for Excel export.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            a.id,
            a.fingerprint_id,
            COALESCE(s.student_no,   'N/A')             AS student_no,
            CASE WHEN a.fingerprint_id = 0 THEN 'Unregistered' ELSE COALESCE(s.student_name, 'Unknown ID:' || a.fingerprint_id) END AS student_name,
            COALESCE(s.grade,        'N/A')             AS grade,
            COALESCE(s.section,      'N/A')             AS section,
            a.date,
            a.time,
            a.confidence,
            a.status
        FROM attendance a
        LEFT JOIN students s ON a.fingerprint_id = s.fingerprint_id
        WHERE a.date >= ? AND a.date <= ?
        ORDER BY a.date ASC, a.time ASC
    """, (start_date, end_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def generate_statistics_report():
    """
    Generate a comprehensive statistics report as formatted text.
    Returns a multi-line string suitable for display or export.
    """
    try:
        conn = get_connection()
        
        # Total counts
        total_students = conn.execute("SELECT COUNT(*) as count FROM students").fetchone()['count']
        total_attendance = conn.execute("SELECT COUNT(*) as count FROM attendance").fetchone()['count']
        
        # Attendance by date
        attendance_by_date = conn.execute("""
            SELECT date, COUNT(*) as count FROM attendance GROUP BY date ORDER BY date DESC LIMIT 30
        """).fetchall()
        
        # Top students by attendance
        top_students = conn.execute("""
            SELECT 
                COALESCE(s.student_name, 'Unknown') as name,
                COUNT(a.id) as count
            FROM attendance a
            LEFT JOIN students s ON a.fingerprint_id = s.fingerprint_id
            GROUP BY a.fingerprint_id
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
        # Grade statistics
        grade_stats = conn.execute("""
            SELECT grade, COUNT(*) as count FROM students GROUP BY grade
        """).fetchall()
        
        # Build report
        report_lines = [
            "=" * 70,
            "ATTENDANCE STATISTICS REPORT",
            "=" * 70,
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "─" * 70,
            "KEY METRICS",
            "─" * 70,
            f"Total Students Enrolled: {total_students}",
            f"Total Attendance Records: {total_attendance}",
            f"Average per Student: {total_attendance / max(total_students, 1):.1f} records",
            "",
            "─" * 70,
            "TOP 10 STUDENTS (By Attendance Count)",
            "─" * 70,
        ]
        
        if top_students:
            for i, (name, count) in enumerate(top_students, 1):
                report_lines.append(f"{i:2d}. {name:<30s} {count:4d} scans")
        else:
            report_lines.append("No attendance records yet.")
        
        report_lines.extend([
            "",
            "─" * 70,
            "STUDENTS BY GRADE",
            "─" * 70,
        ])
        
        if grade_stats:
            for grade, count in grade_stats:
                grade_label = grade if grade else "Unspecified"
                report_lines.append(f"{grade_label:<20s} {count:4d} students")
        else:
            report_lines.append("No students registered.")
        
        report_lines.extend([
            "",
            "─" * 70,
            "RECENT ATTENDANCE (Last 30 Days)",
            "─" * 70,
        ])
        
        if attendance_by_date:
            for date, count in attendance_by_date:
                report_lines.append(f"{date}  {count:4d} scans")
        else:
            report_lines.append("No attendance records yet.")
        
        report_lines.extend([
            "",
            "=" * 70,
        ])
        
        conn.close()
        return "\n".join(report_lines)
    except Exception as e:
        log.error(f"Report generation failed: {e}")
        return f"Error generating report: {e}"


def generate_attendance_chart():
    """Generate attendance timeline chart (last 30 days). Returns image path or None."""
    if not CHARTS_AVAILABLE:
        return None
    
    try:
        import io
        from pathlib import Path
        
        conn = get_connection()
        rows = conn.execute("""
            SELECT date, COUNT(*) as count FROM attendance 
            GROUP BY date ORDER BY date DESC LIMIT 30
        """).fetchall()
        conn.close()
        
        if not rows:
            return None
        
        # Reverse to show chronological order
        rows = list(reversed(rows))
        dates = [r['date'] for r in rows]
        counts = [r['count'] for r in rows]
        
        # Create chart
        fig, ax = plt.subplots(figsize=(10, 4), dpi=80)
        ax.plot(range(len(dates)), counts, marker='o', linewidth=2, markersize=6, color='#3b82f6')
        ax.fill_between(range(len(dates)), counts, alpha=0.3, color='#3b82f6')
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Attendance Count', fontsize=10)
        ax.set_title('Attendance Timeline (Last 30 Days)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Limit x-axis labels to avoid crowding
        step = max(1, len(dates) // 10)
        ax.set_xticks(range(0, len(dates), step))
        ax.set_xticklabels(dates[::step], rotation=45, ha='right', fontsize=8)
        
        plt.tight_layout()
        
        # Save to temporary file
        chart_dir = Path(DB_PATH).parent / "charts"
        chart_dir.mkdir(exist_ok=True)
        chart_path = chart_dir / "attendance_timeline.png"
        plt.savefig(str(chart_path), dpi=80, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    except Exception as e:
        log.error(f"Attendance chart generation failed: {e}")
        return None


def generate_section_chart():
    """Generate students per section chart. Returns image path or None."""
    if not CHARTS_AVAILABLE:
        return None
    
    try:
        conn = get_connection()
        rows = conn.execute("""
            SELECT section, COUNT(*) as count FROM students 
            WHERE section IS NOT NULL AND section != ''
            GROUP BY section ORDER BY count DESC
        """).fetchall()
        conn.close()
        
        if not rows:
            return None
        
        sections = [r['section'] for r in rows]
        counts = [r['count'] for r in rows]
        
        # Create chart
        fig, ax = plt.subplots(figsize=(10, 4), dpi=80)
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        ax.bar(sections, counts, color=colors[:len(sections)], edgecolor='black', linewidth=1.2)
        ax.set_xlabel('Section', fontsize=10)
        ax.set_ylabel('Number of Students', fontsize=10)
        ax.set_title('Students by Section', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for i, (sec, cnt) in enumerate(zip(sections, counts)):
            ax.text(i, cnt + 0.1, str(cnt), ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        
        # Save to temporary file
        chart_dir = Path(DB_PATH).parent / "charts"
        chart_dir.mkdir(exist_ok=True)
        chart_path = chart_dir / "section_chart.png"
        plt.savefig(str(chart_path), dpi=80, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    except Exception as e:
        log.error(f"Section chart generation failed: {e}")
        return None


def generate_grade_chart():
    """Generate attendance by grade pie chart. Returns image path or None."""
    if not CHARTS_AVAILABLE:
        return None
    
    try:
        conn = get_connection()
        rows = conn.execute("""
            SELECT COALESCE(s.grade, 'Unspecified') as grade, COUNT(a.id) as count
            FROM attendance a
            LEFT JOIN students s ON a.fingerprint_id = s.fingerprint_id
            GROUP BY s.grade
            ORDER BY count DESC
        """).fetchall()
        conn.close()
        
        if not rows:
            return None
        
        grades = [r['grade'] for r in rows]
        counts = [r['count'] for r in rows]
        
        # Create chart
        fig, ax = plt.subplots(figsize=(8, 6), dpi=80)
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        wedges, texts, autotexts = ax.pie(
            counts, labels=grades, autopct='%1.1f%%',
            colors=colors[:len(grades)], startangle=90
        )
        
        # Style text
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        ax.set_title('Attendance by Grade', fontsize=12, fontweight='bold')
        plt.tight_layout()
        
        # Save to temporary file
        chart_dir = Path(DB_PATH).parent / "charts"
        chart_dir.mkdir(exist_ok=True)
        chart_path = chart_dir / "grade_chart.png"
        plt.savefig(str(chart_path), dpi=80, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    except Exception as e:
        log.error(f"Grade chart generation failed: {e}")
        return None


def backup_database():
    """
    Backup the database file to a backups directory.
    Returns (success, message, backup_path).
    """
    try:
        backup_dir = Path(DB_PATH).parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"attendance_{timestamp}.db"
        
        # Copy database file
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, backup_path)
            log.success(f"Database backed up to {backup_path}")
            return True, f"Backup created: {backup_path.name}", str(backup_path)
        else:
            return False, "Database file not found", None
    except Exception as e:
        log.error(f"Database backup failed: {e}")
        return False, f"Backup failed: {e}", None


def restore_database(backup_path):
    """
    Restore database from a backup file.
    Returns (success, message).
    """
    try:
        if not os.path.exists(backup_path):
            return False, "Backup file not found"
        
        # Close any existing connection
        # Restore from backup
        shutil.copy2(backup_path, DB_PATH)
        log.success(f"Database restored from {backup_path}")
        return True, f"Database restored successfully"
    except Exception as e:
        log.error(f"Database restore failed: {e}")
        return False, f"Restore failed: {e}"


def list_backups():
    """
    List all available database backups.
    Returns list of (backup_name, backup_path, backup_size, backup_date).
    """
    try:
        backup_dir = Path(DB_PATH).parent / "backups"
        if not backup_dir.exists():
            return []
        
        backups = []
        for backup_file in sorted(backup_dir.glob("attendance_*.db"), reverse=True):
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size_mb': f"{size_mb:.2f} MB",
                'date': mtime.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return backups
    except Exception as e:
        log.error(f"Failed to list backups: {e}")
        return []
