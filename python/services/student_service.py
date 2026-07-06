from core.database import delete_student, get_all_students, get_student, register_student


class StudentService:
    """Thin service layer for student data operations."""

    def get_all_students(self):
        return get_all_students()

    def get_student(self, fingerprint_id):
        return get_student(fingerprint_id)

    def save_student(self, fingerprint_id, student_no, student_name, grade, section):
        return register_student(fingerprint_id, student_no, student_name, grade, section)

    def delete_student(self, fingerprint_id):
        return delete_student(fingerprint_id)
