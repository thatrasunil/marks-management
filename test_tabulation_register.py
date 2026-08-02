import unittest
import io
import openpyxl
from app import app, db
from models import Admin, Teacher, Student, Subject, Mark, Result, ResultRelease
from services import TabulationRegisterService

class TestTabulationRegisterPhase8(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

        # Seed Admin
        self.admin = Admin.query.filter_by(username='admin').first()
        if not self.admin:
            from werkzeug.security import generate_password_hash
            self.admin = Admin(username='admin', password_hash=generate_password_hash('admin'))
            db.session.add(self.admin)
            db.session.commit()

        # Seed Teacher
        self.teacher = Teacher.query.filter_by(email="tr_teacher@aits.edu").first()
        if not self.teacher:
            self.teacher = Teacher(name="TR Teacher", email="tr_teacher@aits.edu", password_hash="dummy")
            db.session.add(self.teacher)
            db.session.commit()

        # Seed Students for TR testing
        self.student1 = Student.query.filter_by(roll_no="24AK1A0501").first()
        if not self.student1:
            self.student1 = Student(roll_no="24AK1A0501", name="Alice Smith", email="alice@aits.edu", aadhar_last4="1111", batch="2024 Intake", semester=1)
            db.session.add(self.student1)
            
        self.student2 = Student.query.filter_by(roll_no="24AK1A0502").first()
        if not self.student2:
            self.student2 = Student(roll_no="24AK1A0502", name="Bob Jones", email="bob@aits.edu", aadhar_last4="2222", batch="2024 Intake", semester=1)
            db.session.add(self.student2)
        db.session.commit()

        # Seed Subjects
        self.sub1 = Subject.query.filter_by(code="CS101_TR").first()
        if not self.sub1:
            self.sub1 = Subject(code="CS101_TR", name="C Programming", credits=4, teacher_id=self.teacher.id, processing_status='RELEASED')
            db.session.add(self.sub1)

        self.sub2 = Subject.query.filter_by(code="MA101_TR").first()
        if not self.sub2:
            self.sub2 = Subject(code="MA101_TR", name="Mathematics I", credits=3, teacher_id=self.teacher.id, processing_status='RELEASED')
            db.session.add(self.sub2)

        # Unreleased Subject (Draft)
        self.sub_unreleased = Subject.query.filter_by(code="DRAFT101").first()
        if not self.sub_unreleased:
            self.sub_unreleased = Subject(code="DRAFT101", name="Draft Subject", credits=3, teacher_id=self.teacher.id, processing_status='DRAFT')
            db.session.add(self.sub_unreleased)

        db.session.commit()

        # Seed Marks (RELEASED)
        # Student 1 Marks
        m11 = Mark.query.filter_by(student_id=self.student1.id, subject_id=self.sub1.id).first()
        if not m11:
            m11 = Mark(student_id=self.student1.id, subject_id=self.sub1.id, internal=25, external=65, total=90, grade='A+', grade_point=10, status='RELEASED')
            db.session.add(m11)

        m12 = Mark.query.filter_by(student_id=self.student1.id, subject_id=self.sub2.id).first()
        if not m12:
            m12 = Mark(student_id=self.student1.id, subject_id=self.sub2.id, internal=22, external=58, total=80, grade='A', grade_point=9, status='RELEASED')
            db.session.add(m12)

        # Student 2 Marks (One Fail)
        m21 = Mark.query.filter_by(student_id=self.student2.id, subject_id=self.sub1.id).first()
        if not m21:
            m21 = Mark(student_id=self.student2.id, subject_id=self.sub1.id, internal=15, external=20, total=35, grade='F', grade_point=0, status='RELEASED')
            db.session.add(m21)

        m22 = Mark.query.filter_by(student_id=self.student2.id, subject_id=self.sub2.id).first()
        if not m22:
            m22 = Mark(student_id=self.student2.id, subject_id=self.sub2.id, internal=20, external=45, total=65, grade='C', grade_point=7, status='RELEASED')
            db.session.add(m22)

        # Student 1 Result
        res1 = Result.query.filter_by(student_id=self.student1.id, semester=1).first()
        if not res1:
            res1 = Result(student_id=self.student1.id, sgpa=9.57, cgpa=9.57, semester=1, is_released=True, credits_registered=7, credits_earned=7)
            db.session.add(res1)
        else:
            res1.is_released = True
            res1.sgpa = 9.57

        # Student 2 Result
        res2 = Result.query.filter_by(student_id=self.student2.id, semester=1).first()
        if not res2:
            res2 = Result(student_id=self.student2.id, sgpa=3.0, cgpa=3.0, semester=1, is_released=True, credits_registered=7, credits_earned=3)
            db.session.add(res2)
        else:
            res2.is_released = True
            res2.sgpa = 3.0

        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        self.app_context.pop()

    def test_security_rbac(self):
        """Test RBAC security: Unauthenticated users are rejected."""
        response = self.client.get('/admin/tabulation_register')
        self.assertEqual(response.status_code, 302) # Redirect to login

        response_api = self.client.get('/admin/tabulation_register/data')
        self.assertEqual(response_api.status_code, 401)

    def test_tr_filter_options(self):
        """Test retrieving filter options."""
        filters = TabulationRegisterService.get_tr_filter_options()
        self.assertIn("semesters", filters)
        self.assertIn("departments", filters)
        self.assertIn("batches", filters)

    def test_generate_tr_matrix_and_summary(self):
        """Test dynamic TR matrix generation and summary stats."""
        tr_data = TabulationRegisterService.generate_tabulation_register(semester=1)
        
        self.assertEqual(tr_data['metadata']['semester'], 1)
        self.assertTrue(len(tr_data['subjects']) >= 2)
        self.assertTrue(len(tr_data['students']) >= 2)

        # Verify summary
        summary = tr_data['summary']
        self.assertEqual(summary['total_students'], 2)
        self.assertEqual(summary['passed'], 1)
        self.assertEqual(summary['failed'], 1)
        self.assertEqual(summary['pass_percentage'], 50.0)

    def test_search_and_filter(self):
        """Test searching student by name/roll and filtering by PASS/FAIL."""
        # Search by name "Alice"
        tr_alice = TabulationRegisterService.generate_tabulation_register(semester=1, search="Alice")
        self.assertEqual(len(tr_alice['students']), 1)
        self.assertEqual(tr_alice['students'][0]['roll_no'], "24AK1A0501")

        # Filter by PASS
        tr_pass = TabulationRegisterService.generate_tabulation_register(semester=1, pass_fail="PASS")
        self.assertEqual(len(tr_pass['students']), 1)
        self.assertEqual(tr_pass['students'][0]['overall_result'], "PASS")

        # Filter by FAIL
        tr_fail = TabulationRegisterService.generate_tabulation_register(semester=1, pass_fail="FAIL")
        self.assertEqual(len(tr_fail['students']), 1)
        self.assertEqual(tr_fail['students'][0]['overall_result'], "FAIL")

    def test_excel_export(self):
        """Test openpyxl Excel export generation."""
        tr_data = TabulationRegisterService.generate_tabulation_register(semester=1)
        excel_io = TabulationRegisterService.export_tabulation_register_excel(tr_data)
        
        self.assertIsNotNone(excel_io)
        wb = openpyxl.load_workbook(excel_io)
        ws = wb.active
        self.assertEqual(ws.title, "Tabulation Register")
        self.assertEqual(ws.cell(row=1, column=1).value, "Annamacharya Institute of Technology and Sciences, Tirupati")

    def test_authenticated_routes(self):
        """Test authenticated admin routes for TR view, data, export, and print."""
        with self.client.session_transaction() as sess:
            sess['admin_id'] = self.admin.id

        # HTML TR page
        res = self.client.get('/admin/tabulation_register?semester=1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Tabulation Register", res.data)

        # JSON Data API
        res_data = self.client.get('/admin/tabulation_register/data?semester=1')
        self.assertEqual(res_data.status_code, 200)
        json_resp = res_data.get_json()
        self.assertTrue(json_resp['success'])

        # Excel Export
        res_exp = self.client.get('/admin/tabulation_register/export?semester=1')
        self.assertEqual(res_exp.status_code, 200)
        self.assertEqual(res_exp.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # Print View
        res_print = self.client.get('/admin/tabulation_register/print?semester=1')
        self.assertEqual(res_print.status_code, 200)
        self.assertIn(b"Official Tabulation Register - Print Layout", res_print.data)

if __name__ == '__main__':
    unittest.main()
