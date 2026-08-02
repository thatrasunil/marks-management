import unittest
from app import app, db
from models import SystemSetting, SystemActivityLog, Student, Teacher, Subject, Admin

class TestProductionPolish(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed basic admin if not already present
        if not Admin.query.filter_by(username='admin').first():
            self.admin = Admin(username='admin', password_hash='hash')
            db.session.add(self.admin)
        
        # Ensure setting exists
        setting = SystemSetting.query.filter_by(key='institution_name').first()
        if not setting:
            self.setting = SystemSetting(key='institution_name', value='Test University')
            db.session.add(self.setting)
        else:
            setting.value = 'Test University'
            
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_settings_retrieval(self):
        setting = SystemSetting.query.filter_by(key='institution_name').first()
        self.assertIsNotNone(setting)
        self.assertEqual(setting.value, 'Test University')

    def test_activity_logging(self):
        from app import log_activity
        log_activity('admin', 'Tested settings log')
        log = SystemActivityLog.query.filter_by(username='admin').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'Tested settings log')

    def test_search_api_empty(self):
        response = self.client.get('/api/search?q=')
        data = response.get_json()
        self.assertEqual(len(data['students']), 0)

    def test_search_api_partial_match(self):
        student = Student(roll_no='AITS001', name='John Doe', email='john@example.com', aadhar_last4='1234')
        db.session.add(student)
        db.session.commit()

        response = self.client.get('/api/search?q=John')
        data = response.get_json()
        self.assertEqual(len(data['students']), 1)
        self.assertEqual(data['students'][0]['name'], 'John Doe')

if __name__ == '__main__':
    unittest.main()
