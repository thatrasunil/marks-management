import os
import random
from app import app, db, calculate_grade
from models import Student, Subject, Mark, Result

def import_students():
    input_file = r"d:\My_Projects\Marks Management System\data.txt"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with app.app_context():
        # Get existing subjects
        subjects = Subject.query.all()
        if not subjects:
            print("No subjects found. Please run seed.py first.")
            return

        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[1:]  # skip header
            count = 0
            for line in lines:
                line = line.strip()
                if not line or line == ".": continue
                
                parts = line.split('\t')
                if len(parts) < 6: continue
                
                name = parts[0].strip()
                # Handle Aadhar parsing
                aadhar_raw = parts[3].strip()
                if '.00' in aadhar_raw:
                    aadhar_full = aadhar_raw.split('.')[0]
                else:
                    aadhar_full = aadhar_raw
                
                aadhar_last4 = aadhar_full[-4:] if len(aadhar_full) >= 4 else "0000"
                roll_no = parts[5].strip()
                email = f"{roll_no.lower()}@college.edu"

                if not roll_no: continue

                # Check if student already exists
                student = Student.query.filter_by(roll_no=roll_no).first()
                if not student:
                    student = Student(
                        roll_no=roll_no,
                        name=name,
                        email=email,
                        aadhar_last4=aadhar_last4,
                        batch="2024-2028", 
                        semester=4        
                    )
                    db.session.add(student)
                    db.session.flush() # Get student.id
                    count += 1
                
                # Simulate marks for all subjects
                for sub in subjects:
                    mark = Mark.query.filter_by(student_id=student.id, subject_id=sub.id).first()
                    if not mark:
                        internal = round(random.uniform(18, 28), 1)
                        external = round(random.uniform(35, 65), 1)
                        total = internal + external
                        grade, gp = calculate_grade(total)
                        
                        mark = Mark(
                            student_id=student.id,
                            subject_id=sub.id,
                            internal=internal,
                            external=external,
                            total=total,
                            grade=grade,
                            grade_point=gp
                        )
                        db.session.add(mark)

                # Simulate Result
                result = Result.query.filter_by(student_id=student.id).first()
                if not result:
                    sgpa = round(random.uniform(7.5, 9.8), 2)
                    result = Result(
                        student_id=student.id,
                        sgpa=sgpa,
                        cgpa=sgpa,
                        semester=student.semester,
                        is_released=True
                    )
                    db.session.add(result)

            db.session.commit()
            print(f"Successfully imported {count} new students and simulated marks for all.")

if __name__ == "__main__":
    import_students()
