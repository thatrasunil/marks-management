import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import app, db
from models import Teacher, Subject, Mark, AnonymousMarkData, StudentMapping

def test_process():
    with app.test_client() as client:
        # Simulate teacher login
        with client.session_transaction() as sess:
            sess['teacher_id'] = 1  # Ravi's ID is 1
            
        print("Logged in as Ravi.")
        
        # Check database before process
        subject = Subject.query.get(1)
        print(f"Subject CS101 status before processing: {subject.processing_status}")
        
        # Perform results processing
        res = client.post('/teacher/process_results/1')
        print(f"Status code: {res.status_code}")
        print(f"Response: {res.get_json()}")
        
        # Check database after process
        db.session.refresh(subject)
        print(f"Subject CS101 status after processing: {subject.processing_status}")

if __name__ == '__main__':
    with app.app_context():
        test_process()
