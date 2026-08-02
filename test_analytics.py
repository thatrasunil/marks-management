import unittest
import json
import io
import openpyxl
from app import app, db
from models import Admin, Teacher, Student, Subject, Mark, Result, ResultRelease
from services import AnalyticsService

class TestAnalyticsDashboard(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

        # Seed data
        self.admin = Admin.query.filter_by(username='admin').first()
        if not self.admin:
            from werkzeug.security import generate_password_hash
            self.admin = Admin(username='admin', password_hash=generate_password_hash('admin'))
            db.session.add(self.admin)
            db.session.commit()

        self.teacher = Teacher.query.filter_by(email="analytics_teacher@aits.edu").first()
        if not self.teacher:
            self.teacher = Teacher(name="Analytics Teacher", email="analytics_teacher@aits.edu", password_hash="dummy")
            db.session.add(self.teacher)
            db.session.commit()

        self.student = Student.query.filter_by(roll_no="24AK1A0599").first()
        if not self.student:
            self.student = Student(roll_no="24AK1A0599", name="Charlie Brown", email="charlie@aits.edu", aadhar_last4="9999", batch="2024 Intake", semester=1)
            db.session.add(self.student)
            db.session.commit()

        self.sub = Subject.query.filter_by(code="CS101_AN").first()
        if not self.sub:
            self.sub = Subject(code="CS101_AN", name="Computer Science Intro", credits=4, teacher_id=self.teacher.id, processing_status='RELEASED')
            db.session.add(self.sub)
            db.session.commit()

        # Marks
        mark = Mark.query.filter_by(student_id=self.student.id, subject_id=self.sub.id).first()
        if not mark:
            mark = Mark(student_id=self.student.id, subject_id=self.sub.id, internal=25, external=55, total=80, grade='A', grade_point=9, status='RELEASED')
            db.session.add(mark)
            db.session.commit()

        # Result
        res = Result.query.filter_by(student_id=self.student.id, semester=1).first()
        if not res:
            res = Result(student_id=self.student.id, sgpa=9.0, cgpa=9.0, semester=1, is_released=True, credits_registered=4, credits_earned=4)
            db.session.add(res)
            db.session.commit()

    def tearDown(self):
        # Cleanup
        db.session.remove()
        self.app_context.pop()

    def test_analytics_service_methods(self):
        """Test calculation of summary stats and charts via AnalyticsService."""
        filters = {
            'semester': '1',
            'academic_year': 'ALL',
            'department': 'ALL',
            'branch': 'ALL',
            'batch': 'ALL',
            'subject_id': 'ALL',
            'result_status': 'ALL'
        }
        
        # Admin stats
        admin_stats = AnalyticsService.get_admin_dashboard_stats(filters)
        self.assertGreaterEqual(admin_stats['total_students'], 1)
        self.assertGreaterEqual(admin_stats['total_teachers'], 1)
        self.assertGreaterEqual(admin_stats['total_subjects'], 1)

        # Examination stats
        exam_stats = AnalyticsService.get_examination_stats(filters)
        self.assertEqual(exam_stats['appeared'], 1)
        self.assertEqual(exam_stats['passed'], 1)
        self.assertEqual(exam_stats['failed'], 0)
        self.assertEqual(exam_stats['average_sgpa'], 9.0)

        # Chart data
        chart_data = AnalyticsService.get_chart_data(filters)
        self.assertIn("pass_vs_fail", chart_data)
        self.assertIn("grade_distribution", chart_data)
        self.assertEqual(chart_data['pass_vs_fail']['data'], [1, 0])

        # Merit List
        merit_list = AnalyticsService.get_merit_list(filters)
        self.assertEqual(len(merit_list), 1)
        self.assertEqual(merit_list[0]['roll_no'], "24AK1A0599")

        # Subject Analytics
        sub_analytics = AnalyticsService.get_subject_analytics(filters)
        self.assertGreaterEqual(len(sub_analytics), 1)
        self.assertEqual(sub_analytics[0]['code'], "CS101_AN")

        # Teacher stats
        teacher_stats = AnalyticsService.get_teacher_dashboard_stats(self.teacher.id)
        self.assertEqual(teacher_stats['assigned_subjects'], 1)
        self.assertEqual(teacher_stats['average_marks'], 80.0)

    def test_analytics_endpoints_security(self):
        """Test security permissions for analytics routes."""
        # Unauthenticated Admin
        resp = self.client.get('/admin/analytics')
        self.assertEqual(resp.status_code, 302) # Redirect to login

        resp = self.client.get('/admin/analytics/data')
        self.assertEqual(resp.status_code, 401)

        # Unauthenticated Teacher
        resp = self.client.get('/teacher/analytics')
        self.assertEqual(resp.status_code, 302)

        # Authenticated Admin session
        with self.client.session_transaction() as sess:
            sess['admin_id'] = self.admin.id

        resp = self.client.get('/admin/analytics')
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get('/admin/analytics/data?semester=1')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])

        # Excel Export
        resp = self.client.get('/admin/analytics/export?semester=1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # Clean session
        with self.client.session_transaction() as sess:
            sess.clear()

        # Authenticated Teacher session
        with self.client.session_transaction() as sess:
            sess['teacher_id'] = self.teacher.id

        resp = self.client.get('/teacher/analytics')
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get('/teacher/analytics/data')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])

if __name__ == '__main__':
    unittest.main()
