import sys
import unittest
from unittest.mock import patch
from app import app, db
from models import Subject, Submission, AuditLog, Mark, Teacher, Student, Result, ResultRelease, NotificationLog, Admin

class TestResultReleasePhase6(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Ensure we have test data seeded
        db.create_all()
        
        # Setup test teacher
        self.teacher = Teacher.query.filter_by(email="faculty_p6@aits.edu").first()
        if not self.teacher:
            self.teacher = Teacher(name="Test Faculty P6", email="faculty_p6@aits.edu", password_hash="dummy")
            db.session.add(self.teacher)
            db.session.commit()
            
        # Setup unique test student for Phase 6
        self.student = Student.query.filter_by(roll_no="24AK1A0699").first()
        if not self.student:
            self.student = Student(roll_no="24AK1A0699", name="Phase6 Student", email="phase6_stud@gmail.com", aadhar_last4="9999", semester=2)
            db.session.add(self.student)
            db.session.commit()
            
        # Setup unique test subject for Phase 6
        self.subject = Subject.query.filter_by(code="PHASE6_SUB").first()
        if not self.subject:
            self.subject = Subject(code="PHASE6_SUB", name="Phase6 Testing Subject", credits=4, teacher_id=self.teacher.id)
            db.session.add(self.subject)
            db.session.commit()
            
        # Ensure we have a default admin user
        self.admin = Admin.query.filter_by(username='admin').first()
        if not self.admin:
            from werkzeug.security import generate_password_hash
            self.admin = Admin(username='admin', password_hash=generate_password_hash('admin'))
            db.session.add(self.admin)
            db.session.commit()

    def tearDown(self):
        # Reset state for clean exit
        if self.subject:
            self.subject.processing_status = "DRAFT"
            db.session.query(Submission).filter_by(subject_id=self.subject.id).delete()
            db.session.query(AuditLog).filter_by(subject_id=self.subject.id).delete()
            db.session.query(ResultRelease).filter_by(subject_id=self.subject.id).delete()
            
        if self.student:
            db.session.query(NotificationLog).filter_by(student_id=self.student.id).delete()
            db.session.query(Result).filter_by(student_id=self.student.id).delete()
            db.session.query(Mark).filter_by(student_id=self.student.id).delete()
            from models import StudentMapping
            db.session.query(StudentMapping).filter_by(roll_number=self.student.roll_no).delete()
            
        db.session.commit()
        self.app_context.pop()

    def test_01_teacher_cannot_release_results(self):
        """Verify that teacher or unauthenticated user cannot release results (Security)"""
        with self.client.session_transaction() as sess:
            sess['teacher_id'] = self.teacher.id
            
        response = self.client.post('/admin/release_results', data={'subject_id': self.subject.id})
        self.assertEqual(response.status_code, 401)
        
    def test_02_release_eligibility_validation(self):
        """Verify release fails for subjects in DRAFT status"""
        self.subject.processing_status = "DRAFT"
        db.session.commit()
        
        with self.client.session_transaction() as sess:
            sess['admin_id'] = self.admin.id
            
        response = self.client.post('/admin/release_results', data={'subject_id': self.subject.id})
        self.assertEqual(response.status_code, 400)
        
        # Verify status is still DRAFT
        db.session.refresh(self.subject)
        self.assertEqual(self.subject.processing_status, "DRAFT")

    def test_03_release_success_and_auditing(self):
        """Verify successful single subject release, auditing, and result state transitions"""
        # Seed student mapping and marks for calculation & release
        from models import StudentMapping
        mapping = StudentMapping.query.filter_by(subject_id=self.subject.id, roll_number=self.student.roll_no).first()
        if not mapping:
            mapping = StudentMapping(subject_id=self.subject.id, unique_id="U699", roll_number=self.student.roll_no)
            db.session.add(mapping)
        
        mark = Mark.query.filter_by(student_id=self.student.id, subject_id=self.subject.id).first()
        if not mark:
            mark = Mark(student_id=self.student.id, subject_id=self.subject.id, internal=25.0, external=45.0, total=70.0, grade="B", grade_point=8, status="APPROVED")
            db.session.add(mark)
        else:
            mark.status = "APPROVED"
            
        result = Result.query.filter_by(student_id=self.student.id, semester=self.student.semester).first()
        if not result:
            result = Result(student_id=self.student.id, sgpa=8.0, cgpa=8.0, semester=self.student.semester, is_released=False)
            db.session.add(result)
        else:
            result.is_released = False
            
        # Simulate teacher submission
        sub_record = Submission(
            submitted_by=self.teacher.name,
            semester=self.student.semester,
            subject_id=self.subject.id,
            department="CS",
            academic_year="2026-2027",
            batch=self.student.batch,
            workflow_status="APPROVED",
            approved_by=self.admin.username
        )
        db.session.add(sub_record)
        
        self.subject.processing_status = "APPROVED"
        db.session.commit()
        
        with self.client.session_transaction() as sess:
            sess['admin_id'] = self.admin.id
            
        # Patch the background thread email dispatcher to avoid active network calls
        with patch('mail_sender.send_all_results_email') as mock_email:
            mock_email.return_value = (None, 1, 0)
            
            response = self.client.post('/admin/release_results', data={'subject_id': self.subject.id})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            
        db.session.refresh(self.subject)
        db.session.refresh(sub_record)
        db.session.refresh(mark)
        db.session.refresh(result)
        
        # Verify status transitions
        self.assertEqual(self.subject.processing_status, "RELEASED")
        self.assertEqual(sub_record.workflow_status, "RELEASED")
        self.assertEqual(mark.status, "RELEASED")
        self.assertTrue(result.is_released)
        
        # Check ResultRelease history
        release_history = ResultRelease.query.filter_by(subject_id=self.subject.id).first()
        self.assertIsNotNone(release_history)
        self.assertEqual(release_history.released_by, self.admin.username)
        self.assertEqual(release_history.semester, self.student.semester)
        self.assertEqual(release_history.batch, self.student.batch)
        self.assertEqual(release_history.release_version, 1)
        
        # Check AuditLog
        audit = AuditLog.query.filter_by(subject_id=self.subject.id, new_status="RELEASED").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.submitted_by, self.admin.username)

    def test_04_results_locking_after_release(self):
        """Verify editing/uploading/processing APIs are locked for subjects in RELEASED status"""
        self.subject.processing_status = "RELEASED"
        db.session.commit()
        
        with self.client.session_transaction() as sess:
            sess['teacher_id'] = self.teacher.id
            
        # Try editing marks
        response = self.client.post(f'/teacher/edit_student_marks/{self.subject.id}/{self.student.id}', data={'internal': 20.0})
        self.assertEqual(response.status_code, 302) # redirects to marks_preview since it's locked
        
        # Try processing
        response = self.client.post(f'/teacher/process_results/{self.subject.id}')
        self.assertEqual(response.status_code, 400)
        
        # Try submitting
        response = self.client.post(f'/teacher/submit_results/{self.subject.id}')
        self.assertEqual(response.status_code, 400)

    def test_05_student_dashboard_control(self):
        """Verify student dashboard hides unreleased marks/SGPAs vs showing released ones"""
        # Create unreleased marks/result
        result = Result.query.filter_by(student_id=self.student.id, semester=self.student.semester).first()
        if not result:
            result = Result(student_id=self.student.id, sgpa=8.5, cgpa=8.5, semester=self.student.semester, is_released=False)
            db.session.add(result)
        else:
            result.is_released = False
            
        mark = Mark.query.filter_by(student_id=self.student.id, subject_id=self.subject.id).first()
        if not mark:
            mark = Mark(student_id=self.student.id, subject_id=self.subject.id, internal=20.0, external=50.0, total=70.0, grade="B", grade_point=8, status="APPROVED")
            db.session.add(mark)
        else:
            mark.status = "APPROVED"
            
        db.session.commit()
        
        # Access student dashboard before release
        with self.client.session_transaction() as sess:
            sess['student_id'] = self.student.id
            
        response = self.client.get('/student/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your examination results have not yet been released", response.data)
        self.assertNotIn(b"8.5", response.data) # SGPA must not be exposed
        self.assertNotIn(b"Phase6 Testing Subject", response.data) # subject name/marks must not be exposed
        
        # Release the results
        result.is_released = True
        mark.status = "RELEASED"
        db.session.commit()
        
        # Access student dashboard after release
        response = self.client.get('/student/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Result Available", response.data)
        self.assertIn(b"8.5", response.data) # SGPA is exposed
        self.assertIn(b"Phase6 Testing Subject", response.data) # marks details are exposed

if __name__ == '__main__':
    unittest.main()
