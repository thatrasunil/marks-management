from app import app, db
from models import Student, Mark, Result

def remove_specific_students():
    roll_numbers = ['24AK1A3008', '24AK1A3009', '24AK1A3020', '24AK1A3041']
    
    with app.app_context():
        for roll_no in roll_numbers:
            student = Student.query.filter_by(roll_no=roll_no).first()
            if student:
                print(f"Removing student: {student.name} ({roll_no})")
                
                # Delete associated marks
                Mark.query.filter_by(student_id=student.id).delete()
                
                # Delete associated result
                Result.query.filter_by(student_id=student.id).delete()
                
                # Delete student
                db.session.delete(student)
                print(f"Successfully removed {roll_no}")
            else:
                print(f"Student with roll number {roll_no} not found.")
        
        db.session.commit()
        print("Done.")

if __name__ == "__main__":
    remove_specific_students()
