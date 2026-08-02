import time
import json
import logging
from models import db, Student, Teacher, Subject, Mark, Result, AnonymousMarkData, StudentMapping, ProcessingLog, ResultRelease

# Configure file logging for processing auditing
logger = logging.getLogger('result_processing')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('processing.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(stage)s] - %(message)s')
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

class ValidationException(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} errors.")

class GradeService:
    @staticmethod
    def calculate_grade(total_marks):
        """
        Calculate Grade and Grade Point based on Total Marks (100)
        Centralized grading policy as per system specifications.
        """
        if total_marks >= 90:
            return 'A+', 10
        elif total_marks >= 80:
            return 'A', 9
        elif total_marks >= 70:
            return 'B', 8
        elif total_marks >= 60:
            return 'C', 7
        elif total_marks >= 50:
            return 'D', 6
        elif total_marks >= 40:
            return 'E', 5
        else:
            return 'F', 0

class SGPAService:
    @staticmethod
    def calculate_semester_stats(student_id, target_semester):
        """
        Compute SGPA, Credits Registered, and Credits Earned for a student in a target semester.
        Formula:
          SGPA = Sum(Subject Credits * Subject Grade Point) / Sum(Subject Credits)
          Credits Registered = Sum of credits of all subjects registered in the semester
          Credits Earned = Sum of credits of passed subjects (Grade Point > 0)
        """
        # Fetch all marks of the student
        all_marks = Mark.query.join(Subject).filter(
            Mark.student_id == student_id
        ).all()
        
        student = Student.query.get(student_id)
        if not student:
            return 0.0, 0, 0
            
        student_marks = []
        for m in all_marks:
            # Check if this student is mapped to the subject
            is_mapped = StudentMapping.query.filter_by(subject_id=m.subject_id, roll_number=student.roll_no).first() is not None
            # If mapped, it is part of this semester's results
            if is_mapped:
                student_marks.append(m)
                
        if not student_marks:
            student_marks = all_marks
            
        total_credits_registered = 0
        total_credits_earned = 0
        total_grade_points = 0
        
        for m in student_marks:
            credits = m.subject.credits if m.subject else 0
            total_credits_registered += credits
            total_grade_points += m.grade_point * credits
            if m.grade_point > 0:  # GP > 0 means passed (A+ to E)
                total_credits_earned += credits
                
        sgpa = total_grade_points / total_credits_registered if total_credits_registered > 0 else 0.0
        return round(sgpa, 2), total_credits_registered, total_credits_earned

class LoggingService:
    @staticmethod
    def log(subject_id, level, stage, message):
        """
        Audits the processing pipeline state in the log file and the database.
        """
        # Log to file
        extra = {'stage': stage}
        log_msg = f"Subject ID {subject_id}: {message}" if subject_id else message
        if level.upper() == 'ERROR':
            logger.error(log_msg, extra=extra)
        elif level.upper() == 'WARNING':
            logger.warning(log_msg, extra=extra)
        else:
            logger.info(log_msg, extra=extra)
            
        # Log to database (creates a log entry in a nested session or standalone insert)
        try:
            db_log = ProcessingLog(subject_id=subject_id, level=level.upper(), stage=stage.upper(), message=message)
            db.session.add(db_log)
        except Exception as e:
            print(f"[LoggingService] Failed to write DB log: {e}")

class ValidationService:
    @staticmethod
    def validate_subject_processing(subject_id):
        """
        Performs 14 validation checks before allowing results processing.
        Raises ValidationException if any validations fail.
        """
        errors = []
        
        # 1. Subject exists
        subject = Subject.query.get(subject_id)
        if not subject:
            errors.append("Subject does not exist in the database.")
            raise ValidationException(errors)
            
        # 2. Subject mapping exists
        mappings = StudentMapping.query.filter_by(subject_id=subject_id).all()
        if not mappings:
            errors.append("Subject mapping does not exist (no students mapped to this subject).")
            
        # 3. Internal marks exist (at least one record)
        internal_count = Mark.query.filter(Mark.subject_id == subject_id, Mark.internal != None).count()
        if internal_count == 0:
            errors.append("Internal marks do not exist (no internal marks have been uploaded).")
            
        # 4. External marks exist (at least one record)
        latest_version = db.session.query(db.func.max(AnonymousMarkData.upload_version)).filter_by(subject_id=subject_id).scalar()
        external_records = []
        if latest_version:
            external_records = AnonymousMarkData.query.filter_by(subject_id=subject_id, upload_version=latest_version).all()
        if not external_records:
            errors.append("External marks do not exist (no external marks have been uploaded).")

        # Exit early if primary data components are completely missing
        if errors:
            raise ValidationException(errors)

        # 5. Duplicate hall tickets / unique IDs check in external sheet
        seen_ext_uids = set()
        dup_ext_uids = set()
        for ext in external_records:
            if ext.unique_id in seen_ext_uids:
                dup_ext_uids.add(ext.unique_id)
            seen_ext_uids.add(ext.unique_id)
        if dup_ext_uids:
            errors.append(f"Duplicate unique IDs found in external marks: {', '.join(dup_ext_uids)}")

        # 6. Duplicate mappings check
        seen_map_uids = set()
        seen_map_rolls = set()
        dup_map_uids = set()
        dup_map_rolls = set()
        for m in mappings:
            if m.unique_id in seen_map_uids:
                dup_map_uids.add(m.unique_id)
            if m.roll_number in seen_map_rolls:
                dup_map_rolls.add(m.roll_number)
            seen_map_uids.add(m.unique_id)
            seen_map_rolls.add(m.roll_number)
            
        if dup_map_uids:
            errors.append(f"Duplicate Unique IDs in student mapping: {', '.join(dup_map_uids)}")
        if dup_map_rolls:
            errors.append(f"Duplicate Roll Numbers in student mapping: {', '.join(dup_map_rolls)}")

        # 7 & 8. Student exists check (every mapping roll_number must exist in the Student database)
        roll_numbers = [m.roll_number for m in mappings]
        students = Student.query.filter(Student.roll_no.in_(roll_numbers)).all()
        student_rolls = {s.roll_no for s in students}
        
        missing_students = [r for r in roll_numbers if r not in student_rolls]
        if missing_students:
            errors.append(f"Missing students: Mapped Roll Numbers {', '.join(missing_students)} do not exist in the Student database.")

        # 9 & 10. Invalid marks / Marks exceeding maximum allowed check
        # Internal marks validation
        subject_marks = Mark.query.filter_by(subject_id=subject_id).all()
        marks_by_student_id = {m.student_id: m for m in subject_marks}
        
        for m in subject_marks:
            if m.internal is not None:
                if not isinstance(m.internal, (int, float)):
                    errors.append(f"Invalid internal marks for student ID {m.student_id}: Value must be numeric.")
                elif m.internal < 0 or m.internal > 30:
                    errors.append(f"Marks exceeding maximum allowed: Internal marks ({m.internal}) for student ID {m.student_id} must be between 0 and 30.")

        # External marks validation
        for ext in external_records:
            if ext.external_total is not None:
                if not isinstance(ext.external_total, (int, float)):
                    errors.append(f"Invalid external marks for Unique ID {ext.unique_id}: Value must be numeric.")
                elif ext.external_total < 0 or ext.external_total > 70:
                    errors.append(f"Marks exceeding maximum allowed: External total ({ext.external_total}) for Unique ID {ext.unique_id} must be between 0 and 70.")
                    
            # Parse question-level marks and validate them if JSON breakup is present
            if ext.marks_data:
                try:
                    q_data = json.loads(ext.marks_data)
                    for q_col, val in q_data.items():
                        try:
                            q_val = float(val)
                            if q_val < 0:
                                errors.append(f"Invalid marks: Question {q_col} marks for Unique ID {ext.unique_id} cannot be negative.")
                        except (ValueError, TypeError):
                            errors.append(f"Invalid marks: Question {q_col} marks for Unique ID {ext.unique_id} must be numeric.")
                except Exception:
                    errors.append(f"Invalid marks: Corrupt external breakup JSON for Unique ID {ext.unique_id}.")

        # 11 & 12. Missing internal / Missing external marks check per mapped student
        student_id_by_roll = {s.roll_no: s.id for s in students}
        external_by_uid = {ext.unique_id: ext for ext in external_records}
        
        for m in mappings:
            s_id = student_id_by_roll.get(m.roll_number)
            if not s_id or s_id not in marks_by_student_id or marks_by_student_id[s_id].internal is None:
                errors.append(f"Missing internal marks: Student {m.roll_number} has no internal marks uploaded.")
                
            if m.unique_id not in external_by_uid:
                errors.append(f"Missing external marks: Student {m.roll_number} (Unique ID {m.unique_id}) has no external marks records.")

        if errors:
            raise ValidationException(errors)

        return True

class ProcessingService:
    @staticmethod
    def get_subject_semester_and_batch(subject_id):
        """
        Deduces the semester and batch associated with a subject by examining mapped students.
        """
        mappings = StudentMapping.query.filter_by(subject_id=subject_id).all()
        if not mappings:
            return 1, "Unknown"
        roll_numbers = [m.roll_number for m in mappings]
        students = Student.query.filter(Student.roll_no.in_(roll_numbers)).all()
        if not students:
            return 1, "Unknown"
            
        # Get most common semester and batch
        semesters = [s.semester for s in students]
        batches = [s.batch for s in students if s.batch]
        
        most_common_sem = max(set(semesters), key=semesters.count) if semesters else 1
        most_common_batch = max(set(batches), key=batches.count) if batches else "Unknown"
        return most_common_sem, most_common_batch

    @staticmethod
    def process_subject_results(subject_id):
        """
        Orchestrates result processing in a single transaction:
        1. Lock subject / semester check.
        2. Validate inputs.
        3. Assign grades & calculate totals.
        4. Compute SGPA for students.
        5. Update statuses and log.
        6. Commit if successful, otherwise roll back.
        """
        start_time = time.time()
        start_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Deduce semester & batch
        semester, batch = ProcessingService.get_subject_semester_and_batch(subject_id)
        
        # 1. Concurrency Check: Verify if any other subject in this semester is processing
        active_processing = db.session.query(Subject).join(StudentMapping).join(Student, Student.roll_no == StudentMapping.roll_number).filter(
            Student.semester == semester,
            Subject.processing_status == 'PROCESSING',
            Subject.id != subject_id
        ).first()
        
        if active_processing:
            error_msg = f"Cannot process: Subject {active_processing.code} in Semester {semester} is currently being processed."
            LoggingService.log(subject_id, 'ERROR', 'PROCESSING_STARTED', error_msg)
            return {'success': False, 'message': error_msg}
            
        subject = Subject.query.get(subject_id)
        if not subject:
            return {'success': False, 'message': "Subject does not exist."}
            
        # Set subject status to PROCESSING to establish the database-level lock, and commit immediately
        subject.processing_status = 'PROCESSING'
        db.session.commit()
        
        # Start log auditing
        LoggingService.log(subject_id, 'INFO', 'VALIDATION_STARTED', "Validation started for results processing.")
        
        try:
            # 2. Validation Engine
            ValidationService.validate_subject_processing(subject_id)
            LoggingService.log(subject_id, 'INFO', 'VALIDATION_COMPLETED', "Validation completed successfully. No errors found.")
            
            # Start calculation engine
            LoggingService.log(subject_id, 'INFO', 'PROCESSING_STARTED', "Calculation engine started.")
            
            # Fetch mappings and external records
            mappings = StudentMapping.query.filter_by(subject_id=subject_id).all()
            mapping_dict = {m.unique_id: m.roll_number for m in mappings}
            
            latest_version = db.session.query(db.func.max(AnonymousMarkData.upload_version)).filter_by(subject_id=subject_id).scalar()
            external_records = AnonymousMarkData.query.filter_by(subject_id=subject_id, upload_version=latest_version).all()
            external_dict = {ext.unique_id: ext for ext in external_records}
            
            processed_students = 0
            processed_subjects = 1
            passed_students = 0
            failed_students = 0
            warnings_count = 0
            skipped_records = 0
            
            students = Student.query.filter(Student.roll_no.in_(list(mapping_dict.values()))).all()
            student_by_roll = {s.roll_no: s for s in students}
            
            # 3. Calculation & Grade Engine loop
            for unique_id, roll_number in mapping_dict.items():
                student = student_by_roll.get(roll_number)
                if not student:
                    skipped_records += 1
                    continue
                    
                ext_record = external_dict.get(unique_id)
                if not ext_record:
                    skipped_records += 1
                    continue
                    
                # Get or create Mark
                mark = Mark.query.filter_by(student_id=student.id, subject_id=subject_id).first()
                if not mark:
                    mark = Mark(student_id=student.id, subject_id=subject_id)
                    db.session.add(mark)
                    
                # Update Mark fields
                mark.external = ext_record.external_total
                mark.external_breakup = ext_record.marks_data
                mark.total = mark.internal + mark.external
                
                # Grading Policy
                grade, gp = GradeService.calculate_grade(mark.total)
                mark.grade = grade
                mark.grade_point = gp
                mark.status = 'DRAFT'
                
                if grade == 'F':
                    failed_students += 1
                else:
                    passed_students += 1
                    
                processed_students += 1
            
            # 4. SGPA Engine Loop
            for unique_id, roll_number in mapping_dict.items():
                student = student_by_roll.get(roll_number)
                if not student:
                    continue
                    
                # Compute SGPA stats
                sgpa, credits_reg, credits_earn = SGPAService.calculate_semester_stats(student.id, semester)
                
                result = Result.query.filter_by(student_id=student.id, semester=semester).first()
                if not result:
                    result = Result(student_id=student.id, semester=semester)
                    db.session.add(result)
                    
                result.sgpa = sgpa
                result.cgpa = sgpa
                result.is_released = False
                result.credits_registered = credits_reg
                result.credits_earned = credits_earn
            
            # Complete Subject Processing status
            subject.processing_status = 'DRAFT'
            
            # Calculate duration
            end_time = time.time()
            duration = round(end_time - start_time, 4)
            end_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Deduce Department
            department_prefix = "".join([c for c in subject.code if c.isalpha()]).upper()
            dept_map = {
                'CS': 'Computer Science',
                'MA': 'Mathematics',
                'EC': 'Electronics & Communication',
                'EE': 'Electrical Engineering',
                'ME': 'Mechanical Engineering',
                'IT': 'Information Technology',
            }
            department = dept_map.get(department_prefix, 'General/Other')
            
            summary = {
                'semester': semester,
                'batch': batch,
                'department': department,
                'processed_students': processed_students,
                'processed_subjects': processed_subjects,
                'passed_students': passed_students,
                'failed_students': failed_students,
                'warnings': warnings_count,
                'skipped_records': skipped_records,
                'duration': f"{duration}s",
                'start_time': start_datetime,
                'end_time': end_datetime,
                'status': 'DRAFT'
            }
            
            LoggingService.log(subject_id, 'INFO', 'PROCESSING_COMPLETED', f"Calculation engine completed. Summary: {summary}")
            
            # Commit the single transaction
            db.session.commit()
            
            return {
                'success': True,
                'message': f"Processed {processed_students} student results successfully.",
                'summary': summary
            }
            
        except ValidationException as val_err:
            db.session.rollback()
            # Restore subject status back to NOT_PROCESSED
            subject = Subject.query.get(subject_id)
            if subject:
                subject.processing_status = 'NOT_PROCESSED'
                db.session.commit()
                
            # Log failure
            for err in val_err.errors:
                LoggingService.log(subject_id, 'ERROR', 'VALIDATION_FAILED', err)
            db.session.commit()
            
            return {
                'success': False,
                'stage': 'validation',
                'message': "Validation failed. Results could not be processed.",
                'errors': val_err.errors
            }
            
        except Exception as e:
            db.session.rollback()
            # Restore subject status back to NOT_PROCESSED
            subject = Subject.query.get(subject_id)
            if subject:
                subject.processing_status = 'NOT_PROCESSED'
                db.session.commit()
                
            # Log critical failure
            err_msg = f"Unexpected processing failure: {str(e)}"
            LoggingService.log(subject_id, 'ERROR', 'PROCESSING_FAILED', err_msg)
            LoggingService.log(subject_id, 'ERROR', 'ROLLBACK', "Transaction rolled back due to error.")
            db.session.commit()
            
            return {
                'success': False,
                'stage': 'processing',
                'message': f"Processing error: {str(e)}",
                'errors': [err_msg]
            }


class TabulationRegisterService:
    """
    University Tabulation Register (TR) Service.
    Handles dynamic matrix generation, performance-optimized querying,
    multi-field filtering, sorting, summary statistics, and openpyxl Excel exports.
    """

    @staticmethod
    def get_tr_filter_options():
        """Retrieve distinct filter options from released results & students."""
        semesters = [1, 2, 3, 4, 5, 6, 7, 8]
        
        batches = [b[0] for b in db.session.query(Student.batch).distinct().all() if b[0]]
        if not batches:
            batches = ["2024 Intake"]
            
        years = [r[0] for r in db.session.query(ResultRelease.academic_year).distinct().all() if r[0]]
        if not years:
            years = ["2024-2025", "2025-2026"]
            
        departments = [
            "Computer Science",
            "Electronics & Communication",
            "Electrical Engineering",
            "Mechanical Engineering",
            "Mathematics",
            "Information Technology",
            "General/Other"
        ]
        
        branches = [
            "Computer Science & Engineering",
            "Electronics & Communication Engineering",
            "Electrical & Electronics Engineering",
            "Mechanical Engineering",
            "Mathematics",
            "Information Technology",
            "General/Other"
        ]
        
        sections = ["ALL", "A", "B", "C"]
        exam_types = ["ALL", "Regular", "Supplementary"]
        
        return {
            "semesters": semesters,
            "batches": sorted(list(set(batches))),
            "academic_years": sorted(list(set(years))),
            "departments": departments,
            "branches": branches,
            "sections": sections,
            "exam_types": exam_types
        }

    @staticmethod
    def get_department_and_branch(subject_code):
        """Map subject code prefix to department and branch name."""
        prefix = "".join([c for c in subject_code if c.isalpha()]).upper() if subject_code else "CS"
        dept_map = {
            'CS': ('Computer Science', 'Computer Science & Engineering'),
            'MA': ('Mathematics', 'Mathematics'),
            'EC': ('Electronics & Communication', 'Electronics & Communication Engineering'),
            'EE': ('Electrical Engineering', 'Electrical & Electronics Engineering'),
            'ME': ('Mechanical Engineering', 'Mechanical Engineering'),
            'IT': ('Information Technology', 'Information Technology'),
        }
        return dept_map.get(prefix, ('General/Other', 'General/Other'))

    @staticmethod
    def generate_tabulation_register(
        semester=1,
        department="ALL",
        branch="ALL",
        batch="ALL",
        academic_year="ALL",
        section="ALL",
        exam_type="ALL",
        search="",
        pass_fail="ALL",
        grade_filter="ALL",
        min_sgpa=None,
        max_sgpa=None,
        min_pct=None,
        max_pct=None,
        sort_by="roll_no",
        sort_dir="asc"
    ):
        """
        Generate dynamic Tabulation Register data matrix and summary statistics.
        Only RELEASED examination results are included.
        """
        from datetime import datetime
        from sqlalchemy.orm import joinedload

        subject_query = Subject.query.filter_by(processing_status='RELEASED')
        all_released_subjects = subject_query.all()
        semester_subjects = []
        for sub in all_released_subjects:
            sem, bat = ProcessingService.get_subject_semester_and_batch(sub.id)
            if sem == semester:
                dept_name, branch_name = TabulationRegisterService.get_department_and_branch(sub.code)
                if department != "ALL" and dept_name != department:
                    continue
                if branch != "ALL" and branch_name != branch:
                    continue
                semester_subjects.append(sub)

        semester_subjects.sort(key=lambda s: s.code)
        subject_ids = [s.id for s in semester_subjects]

        if not subject_ids:
            return {
                "metadata": {
                    "university_name": "Annamacharya Institute of Technology and Sciences, Tirupati",
                    "report_title": "OFFICIAL TABULATION REGISTER",
                    "semester": semester,
                    "department": department if department != "ALL" else "All Departments",
                    "branch": branch if branch != "ALL" else "All Branches",
                    "batch": batch if batch != "ALL" else "All Batches",
                    "academic_year": academic_year if academic_year != "ALL" else "2024-2025",
                    "generated_date": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
                    "total_subjects": 0
                },
                "subjects": [],
                "students": [],
                "summary": {
                    "total_students": 0,
                    "appeared": 0,
                    "passed": 0,
                    "failed": 0,
                    "pass_percentage": 0.0,
                    "highest_sgpa": 0.0,
                    "lowest_sgpa": 0.0,
                    "average_sgpa": 0.0,
                    "highest_percentage": 0.0,
                    "lowest_percentage": 0.0
                }
            }

        released_marks = Mark.query.filter(
            Mark.subject_id.in_(subject_ids),
            Mark.status == 'RELEASED'
        ).options(joinedload(Mark.student), joinedload(Mark.subject)).all()

        student_marks_map = {}
        students_dict = {}

        for m in released_marks:
            if m.student:
                st = m.student
                if batch != "ALL" and st.batch != batch:
                    continue
                
                students_dict[st.id] = st
                if st.id not in student_marks_map:
                    student_marks_map[st.id] = {}
                student_marks_map[st.id][m.subject_id] = m

        student_ids = list(students_dict.keys())
        results_list = Result.query.filter(
            Result.student_id.in_(student_ids),
            Result.semester == semester,
            Result.is_released == True
        ).all() if student_ids else []
        result_map = {r.student_id: r for r in results_list}

        student_rows = []
        for st_id, st in students_dict.items():
            res_obj = result_map.get(st_id)
            marks_dict = student_marks_map.get(st_id, {})

            subject_entries = []
            total_earned_credits = 0
            total_registered_credits = 0
            total_obtained_marks = 0.0
            max_possible_marks = 0.0
            has_failed_subject = False
            grades_list = []

            for sub in semester_subjects:
                m = marks_dict.get(sub.id)
                if m:
                    int_marks = m.internal
                    ext_marks = m.external
                    tot_marks = m.total
                    gr = m.grade
                    gp = m.grade_point
                else:
                    int_marks = 0.0
                    ext_marks = 0.0
                    tot_marks = 0.0
                    gr = 'F'
                    gp = 0

                subject_entries.append({
                    "subject_id": sub.id,
                    "code": sub.code,
                    "internal": round(int_marks, 1),
                    "external": round(ext_marks, 1),
                    "total": round(tot_marks, 1),
                    "grade": gr,
                    "grade_point": gp,
                    "credits": sub.credits
                })

                total_registered_credits += sub.credits
                total_obtained_marks += tot_marks
                max_possible_marks += 100.0
                grades_list.append(gr)

                if gp > 0 and gr != 'F':
                    total_earned_credits += sub.credits
                else:
                    has_failed_subject = True

            if res_obj and res_obj.sgpa > 0:
                calc_sgpa = res_obj.sgpa
                calc_cgpa = res_obj.cgpa
            else:
                total_gp = sum(entry['grade_point'] * entry['credits'] for entry in subject_entries)
                calc_sgpa = round(total_gp / total_registered_credits, 2) if total_registered_credits > 0 else 0.0
                calc_cgpa = calc_sgpa

            percentage = round((total_obtained_marks / max_possible_marks * 100.0), 2) if max_possible_marks > 0 else 0.0
            overall_result = "PASS" if (not has_failed_subject and total_registered_credits > 0) else "FAIL"

            dept_name, branch_name = TabulationRegisterService.get_department_and_branch(semester_subjects[0].code if semester_subjects else "")

            student_rows.append({
                "student_id": st.id,
                "roll_no": st.roll_no,
                "name": st.name,
                "batch": st.batch,
                "semester": semester,
                "department": dept_name,
                "branch": branch_name,
                "subjects": subject_entries,
                "total_credits": total_registered_credits,
                "credits_earned": total_earned_credits,
                "total_marks": round(total_obtained_marks, 1),
                "max_marks": max_possible_marks,
                "sgpa": calc_sgpa,
                "cgpa": calc_cgpa,
                "percentage": percentage,
                "overall_result": overall_result,
                "grades": grades_list
            })

        filtered_rows = []
        search_lower = search.strip().lower() if search else ""

        for row in student_rows:
            if search_lower:
                if search_lower not in row['roll_no'].lower() and search_lower not in row['name'].lower():
                    continue

            if pass_fail != "ALL" and row['overall_result'] != pass_fail:
                continue

            if grade_filter != "ALL" and grade_filter not in row['grades']:
                continue

            if min_sgpa is not None and str(min_sgpa).strip() != "":
                if row['sgpa'] < float(min_sgpa): continue
            if max_sgpa is not None and str(max_sgpa).strip() != "":
                if row['sgpa'] > float(max_sgpa): continue

            if min_pct is not None and str(min_pct).strip() != "":
                if row['percentage'] < float(min_pct): continue
            if max_pct is not None and str(max_pct).strip() != "":
                if row['percentage'] > float(max_pct): continue

            filtered_rows.append(row)

        reverse_sort = (sort_dir.lower() == "desc")
        if sort_by == "name":
            filtered_rows.sort(key=lambda r: r['name'].lower(), reverse=reverse_sort)
        elif sort_by == "sgpa":
            filtered_rows.sort(key=lambda r: (r['sgpa'], r['roll_no']), reverse=reverse_sort)
        elif sort_by == "cgpa":
            filtered_rows.sort(key=lambda r: (r['cgpa'], r['roll_no']), reverse=reverse_sort)
        elif sort_by == "percentage":
            filtered_rows.sort(key=lambda r: (r['percentage'], r['roll_no']), reverse=reverse_sort)
        elif sort_by == "total_marks":
            filtered_rows.sort(key=lambda r: (r['total_marks'], r['roll_no']), reverse=reverse_sort)
        else:
            filtered_rows.sort(key=lambda r: r['roll_no'], reverse=reverse_sort)

        total_students = len(filtered_rows)
        appeared = total_students
        passed = sum(1 for r in filtered_rows if r['overall_result'] == 'PASS')
        failed = sum(1 for r in filtered_rows if r['overall_result'] == 'FAIL')
        pass_percentage = round((passed / appeared * 100.0), 2) if appeared > 0 else 0.0

        sgpa_list = [r['sgpa'] for r in filtered_rows]
        pct_list = [r['percentage'] for r in filtered_rows]

        summary = {
            "total_students": total_students,
            "appeared": appeared,
            "passed": passed,
            "failed": failed,
            "pass_percentage": pass_percentage,
            "highest_sgpa": round(max(sgpa_list), 2) if sgpa_list else 0.0,
            "lowest_sgpa": round(min(sgpa_list), 2) if sgpa_list else 0.0,
            "average_sgpa": round(sum(sgpa_list) / len(sgpa_list), 2) if sgpa_list else 0.0,
            "highest_percentage": round(max(pct_list), 2) if pct_list else 0.0,
            "lowest_percentage": round(min(pct_list), 2) if pct_list else 0.0
        }

        primary_dept = filtered_rows[0]['department'] if filtered_rows else (department if department != "ALL" else "Computer Science")
        primary_branch = filtered_rows[0]['branch'] if filtered_rows else (branch if branch != "ALL" else "Computer Science & Engineering")
        primary_batch = filtered_rows[0]['batch'] if filtered_rows else (batch if batch != "ALL" else "2024 Intake")
        acad_year = academic_year if academic_year != "ALL" else f"{2024 + (semester-1)//2}-{2025 + (semester-1)//2}"

        return {
            "metadata": {
                "university_name": "Annamacharya Institute of Technology and Sciences, Tirupati",
                "report_title": "OFFICIAL TABULATION REGISTER",
                "semester": semester,
                "department": primary_dept,
                "branch": primary_branch,
                "batch": primary_batch,
                "academic_year": acad_year,
                "generated_date": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
                "total_subjects": len(semester_subjects)
            },
            "subjects": [
                {"id": s.id, "code": s.code, "name": s.name, "credits": s.credits} for s in semester_subjects
            ],
            "students": filtered_rows,
            "summary": summary
        }

    @staticmethod
    def export_tabulation_register_excel(tr_data):
        """
        Generate a professionally formatted Excel Tabulation Register (.xlsx) using openpyxl.
        Includes title headers, metadata block, dynamic subject sub-headers, student marks matrix,
        formatted summary statistics, and styled cells with auto-adjusted column widths.
        """
        import io
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "Tabulation Register"
        ws.views.sheetView[0].showGridLines = True

        meta = tr_data['metadata']
        subjects = tr_data['subjects']
        students = tr_data['students']
        summary = tr_data['summary']

        num_subjects = len(subjects)
        total_cols = max(3 + (4 * num_subjects) + 6, 9)

        navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        blue_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        slate_fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid")
        light_gray_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        summary_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
        
        pass_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        fail_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

        white_title_font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
        white_subtitle_font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
        white_header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        bold_font = Font(name="Calibri", size=10, bold=True)
        regular_font = Font(name="Calibri", size=10)
        pass_font = Font(name="Calibri", size=10, bold=True, color="15803D")
        fail_font = Font(name="Calibri", size=10, bold=True, color="B91C1C")

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")

        # Row 1: Title Header
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
        c1 = ws.cell(row=1, column=1, value=meta['university_name'])
        c1.font = white_title_font
        c1.fill = navy_fill
        c1.alignment = align_center

        # Row 2: Subtitle
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
        c2 = ws.cell(row=2, column=1, value=f"{meta['report_title']} - SEMESTER {meta['semester']} EXAMINATION")
        c2.font = white_subtitle_font
        c2.fill = blue_fill
        c2.alignment = align_center

        # Row 3: Metadata Details
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=total_cols)
        details_text = f"Department: {meta['department']} | Branch: {meta['branch']} | Academic Year: {meta['academic_year']} | Batch: {meta['batch']} | Date: {meta['generated_date']}"
        c3 = ws.cell(row=3, column=1, value=details_text)
        c3.font = bold_font
        c3.fill = summary_fill
        c3.alignment = align_center

        ws.row_dimensions[1].height = 30
        ws.row_dimensions[2].height = 24
        ws.row_dimensions[3].height = 20
        ws.row_dimensions[4].height = 10

        # Row 5: Grouped Headers
        row5 = 5
        ws.cell(row=row5, column=1, value="S.No").fill = slate_fill
        ws.cell(row=row5, column=2, value="Hall Ticket No").fill = slate_fill
        ws.cell(row=row5, column=3, value="Student Name").fill = slate_fill

        for r in range(1, 4):
            c = ws.cell(row=row5, column=r)
            c.font = white_header_font
            c.alignment = align_center
            c.border = thin_border

        col_idx = 4
        for sub in subjects:
            ws.merge_cells(start_row=row5, start_column=col_idx, end_row=row5, end_column=col_idx+3)
            cell = ws.cell(row=row5, column=col_idx, value=f"{sub['code']} - {sub['name']} ({sub['credits']} C)")
            cell.font = white_header_font
            cell.fill = navy_fill
            cell.alignment = align_center
            cell.border = thin_border
            for c_i in range(col_idx, col_idx+4):
                ws.cell(row=row5, column=c_i).border = thin_border
                ws.cell(row=row5, column=c_i).fill = navy_fill
            col_idx += 4

        # Aggregates Header Group
        ws.merge_cells(start_row=row5, start_column=col_idx, end_row=row5, end_column=col_idx+5)
        agg_cell = ws.cell(row=row5, column=col_idx, value="SEMESTER PERFORMANCE SUMMARY")
        agg_cell.font = white_header_font
        agg_cell.fill = slate_fill
        agg_cell.alignment = align_center
        for c_i in range(col_idx, col_idx+6):
            ws.cell(row=row5, column=c_i).border = thin_border
            ws.cell(row=row5, column=c_i).fill = slate_fill

        # Row 6: Sub Headers
        row6 = 6
        for c_i in range(1, 4):
            c = ws.cell(row=row6, column=c_i)
            c.border = thin_border
            c.fill = slate_fill

        col_idx = 4
        for _ in subjects:
            headers = ["Internal", "External", "Total", "Grade"]
            for h in headers:
                c = ws.cell(row=row6, column=col_idx, value=h)
                c.font = white_header_font
                c.fill = blue_fill
                c.alignment = align_center
                c.border = thin_border
                col_idx += 1

        agg_headers = ["Total Credits", "Earned Credits", "SGPA", "CGPA", "Percentage", "Result"]
        for h in agg_headers:
            c = ws.cell(row=row6, column=col_idx, value=h)
            c.font = white_header_font
            c.fill = slate_fill
            c.alignment = align_center
            c.border = thin_border
            col_idx += 1

        ws.row_dimensions[row5].height = 24
        ws.row_dimensions[row6].height = 20

        # Row 7+: Student Rows
        curr_row = 7
        for idx, st in enumerate(students, start=1):
            ws.cell(row=curr_row, column=1, value=idx).alignment = align_center
            ws.cell(row=curr_row, column=2, value=st['roll_no']).alignment = align_center
            ws.cell(row=curr_row, column=3, value=st['name']).alignment = align_left

            col_i = 4
            for sub_entry in st['subjects']:
                c_int = ws.cell(row=curr_row, column=col_i, value=sub_entry['internal'])
                c_ext = ws.cell(row=curr_row, column=col_i+1, value=sub_entry['external'])
                c_tot = ws.cell(row=curr_row, column=col_i+2, value=sub_entry['total'])
                c_grd = ws.cell(row=curr_row, column=col_i+3, value=sub_entry['grade'])

                c_int.alignment = align_right
                c_ext.alignment = align_right
                c_tot.alignment = align_right
                c_grd.alignment = align_center

                c_tot.font = bold_font
                c_grd.font = bold_font
                col_i += 4

            ws.cell(row=curr_row, column=col_i, value=st['total_credits']).alignment = align_center
            ws.cell(row=curr_row, column=col_i+1, value=st['credits_earned']).alignment = align_center
            
            c_sgpa = ws.cell(row=curr_row, column=col_i+2, value=st['sgpa'])
            c_sgpa.alignment = align_right
            c_sgpa.font = bold_font
            c_sgpa.number_format = '0.00'

            c_cgpa = ws.cell(row=curr_row, column=col_i+3, value=st['cgpa'])
            c_cgpa.alignment = align_right
            c_cgpa.number_format = '0.00'

            c_pct = ws.cell(row=curr_row, column=col_i+4, value=f"{st['percentage']}%")
            c_pct.alignment = align_right
            c_pct.font = bold_font

            c_res = ws.cell(row=curr_row, column=col_i+5, value=st['overall_result'])
            c_res.alignment = align_center
            if st['overall_result'] == 'PASS':
                c_res.fill = pass_fill
                c_res.font = pass_font
            else:
                c_res.fill = fail_fill
                c_res.font = fail_font

            row_fill = light_gray_fill if idx % 2 == 0 else PatternFill(fill_type=None)
            for c_idx in range(1, total_cols + 1):
                cell = ws.cell(row=curr_row, column=c_idx)
                cell.border = thin_border
                if c_idx <= 3 and row_fill.fill_type:
                    cell.fill = row_fill
                if not cell.font:
                    cell.font = regular_font

            ws.row_dimensions[curr_row].height = 20
            curr_row += 1

        # Summary Section
        curr_row += 1
        ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=min(6, total_cols))
        s_title = ws.cell(row=curr_row, column=1, value="OVERALL COHORT SUMMARY STATISTICS")
        s_title.font = white_subtitle_font
        s_title.fill = navy_fill
        s_title.alignment = align_left

        for c_i in range(1, min(7, total_cols + 1)):
            ws.cell(row=curr_row, column=c_i).border = thin_border
            ws.cell(row=curr_row, column=c_i).fill = navy_fill

        ws.row_dimensions[curr_row].height = 24
        curr_row += 1

        stats_items = [
            ("Total Students Registered", summary['total_students'], "Pass Percentage", f"{summary['pass_percentage']}%"),
            ("Students Appeared", summary['appeared'], "Highest SGPA", summary['highest_sgpa']),
            ("Students Passed", summary['passed'], "Lowest SGPA", summary['lowest_sgpa']),
            ("Students Failed", summary['failed'], "Average SGPA", summary['average_sgpa']),
            ("Highest Percentage", f"{summary['highest_percentage']}%", "Lowest Percentage", f"{summary['lowest_percentage']}%")
        ]

        for label1, val1, label2, val2 in stats_items:
            ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=2)
            c_l1 = ws.cell(row=curr_row, column=1, value=label1)
            c_l1.font = bold_font
            c_l1.alignment = align_left
            c_l1.fill = summary_fill

            c_v1 = ws.cell(row=curr_row, column=3, value=val1)
            c_v1.font = bold_font
            c_v1.alignment = align_right

            ws.merge_cells(start_row=curr_row, start_column=4, end_row=curr_row, end_column=5)
            c_l2 = ws.cell(row=curr_row, column=4, value=label2)
            c_l2.font = bold_font
            c_l2.alignment = align_left
            c_l2.fill = summary_fill

            c_v2 = ws.cell(row=curr_row, column=6, value=val2)
            c_v2.font = bold_font
            c_v2.alignment = align_right

            for col_i in range(1, min(7, total_cols + 1)):
                ws.cell(row=curr_row, column=col_i).border = thin_border

            ws.row_dimensions[curr_row].height = 20
            curr_row += 1

        # Auto adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    val_str = str(cell.value)
                    if len(val_str) > max_len and len(val_str) < 50:
                        max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 11)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output


class AnalyticsService:
    @staticmethod
    def get_analytics_filters():
        """Retrieve distinct filter options for analytics dropdowns."""
        semesters = [1, 2, 3, 4, 5, 6, 7, 8]
        batches = [b[0] for b in db.session.query(Student.batch).distinct().all() if b[0]]
        if not batches:
            batches = ["2024 Intake"]
        
        years = [r[0] for r in db.session.query(ResultRelease.academic_year).distinct().all() if r[0]]
        if not years:
            years = ["2024-2025", "2025-2026"]

        departments = [
            "Computer Science",
            "Electronics & Communication",
            "Electrical Engineering",
            "Mechanical Engineering",
            "Mathematics",
            "Information Technology",
            "General/Other"
        ]

        branches = [
            "Computer Science & Engineering",
            "Electronics & Communication Engineering",
            "Electrical & Electronics Engineering",
            "Mechanical Engineering",
            "Mathematics",
            "Information Technology",
            "General/Other"
        ]

        # All subjects
        subjects = [{"id": s.id, "code": s.code, "name": s.name} for s in Subject.query.order_by(Subject.code).all()]
        teachers = [{"id": t.id, "name": t.name} for t in Teacher.query.order_by(Teacher.name).all()]

        return {
            "semesters": semesters,
            "batches": sorted(list(set(batches))),
            "academic_years": sorted(list(set(years))),
            "departments": departments,
            "branches": branches,
            "subjects": subjects,
            "teachers": teachers,
            "result_statuses": ["DRAFT", "SUBMITTED", "APPROVED", "RELEASED", "NOT_PROCESSED"]
        }

    @staticmethod
    def get_filtered_subjects(filters):
        """Helper to get subjects and their metadata based on filters."""
        query = Subject.query
        if filters.get('teacher_id'):
            query = query.filter(Subject.teacher_id == filters['teacher_id'])
        if filters.get('subject_id') and filters['subject_id'] != 'ALL':
            query = query.filter(Subject.id == filters['subject_id'])
        if filters.get('result_status') and filters['result_status'] != 'ALL':
            query = query.filter(Subject.processing_status == filters['result_status'])
        
        subjects = query.all()
        filtered = []
        for sub in subjects:
            sem, bat = ProcessingService.get_subject_semester_and_batch(sub.id)
            dept, br = TabulationRegisterService.get_department_and_branch(sub.code)
            
            if filters.get('semester') and filters['semester'] != 'ALL':
                if str(sem) != str(filters['semester']):
                    continue
            if filters.get('batch') and filters['batch'] != 'ALL':
                if bat != filters['batch']:
                    continue
            if filters.get('department') and filters['department'] != 'ALL':
                if dept != filters['department']:
                    continue
            if filters.get('branch') and filters['branch'] != 'ALL':
                if br != filters['branch']:
                    continue
            if filters.get('academic_year') and filters['academic_year'] != 'ALL':
                # Deduce academic year
                ay = f"{2024 + (sem-1)//2}-{2025 + (sem-1)//2}"
                if ay != filters['academic_year']:
                    continue
            filtered.append({
                "subject": sub,
                "semester": sem,
                "batch": bat,
                "department": dept,
                "branch": br
            })
        return filtered

    @staticmethod
    def get_admin_dashboard_stats(filters):
        """High-level summary cards."""
        # Total Students: filter by batch/dept if requested
        student_query = Student.query
        if filters.get('batch') and filters['batch'] != 'ALL':
            student_query = student_query.filter(Student.batch == filters['batch'])
        if filters.get('semester') and filters['semester'] != 'ALL':
            student_query = student_query.filter(Student.semester == filters['semester'])
        total_students = student_query.count()

        total_teachers = Teacher.query.count()
        
        # Filtered subjects
        filtered_subs = AnalyticsService.get_filtered_subjects(filters)
        total_subjects = len(filtered_subs)

        # Unique Departments
        depts = set(s['department'] for s in filtered_subs)
        total_departments = len(depts) if depts else 0

        # Semesters count
        sems = set(s['semester'] for s in filtered_subs)
        total_semesters = len(sems) if sems else 0

        # Status counts
        draft_count = sum(1 for s in filtered_subs if s['subject'].processing_status == 'DRAFT')
        submitted_count = sum(1 for s in filtered_subs if s['subject'].processing_status == 'SUBMITTED')
        approved_count = sum(1 for s in filtered_subs if s['subject'].processing_status == 'APPROVED')
        released_count = sum(1 for s in filtered_subs if s['subject'].processing_status == 'RELEASED')

        # Processed Results count (any status other than NOT_PROCESSED)
        processed_count = sum(1 for s in filtered_subs if s['subject'].processing_status != 'NOT_PROCESSED')

        pending_review = submitted_count
        pending_release = approved_count

        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_subjects": total_subjects,
            "departments": total_departments,
            "semesters": total_semesters,
            "processed_results": processed_count,
            "draft_results": draft_count,
            "submitted_results": submitted_count,
            "approved_results": approved_count,
            "released_results": released_count,
            "pending_review": pending_review,
            "pending_release": pending_release
        }

    @staticmethod
    def get_examination_stats(filters):
        """Academic statistics for the selected semester/cohort."""
        filtered_subs = AnalyticsService.get_filtered_subjects(filters)
        subject_ids = [s['subject'].id for s in filtered_subs]
        if not subject_ids:
            return {
                "appeared": 0, "passed": 0, "failed": 0,
                "pass_percentage": 0.0, "fail_percentage": 0.0,
                "average_sgpa": 0.0, "average_percentage": 0.0,
                "highest_sgpa": 0.0, "lowest_sgpa": 0.0,
                "highest_percentage": 0.0, "lowest_percentage": 0.0
            }

        # Query all marks for these subjects
        marks = Mark.query.filter(Mark.subject_id.in_(subject_ids)).all()
        
        # Group by student
        student_marks = {}
        for m in marks:
            if m.student_id not in student_marks:
                student_marks[m.student_id] = []
            student_marks[m.student_id].append(m)

        appeared = len(student_marks)
        passed = 0
        failed = 0
        sgpa_list = []
        pct_list = []

        # Find results for target semesters if we need SGPA, or calculate dynamically
        student_ids = list(student_marks.keys())
        results = Result.query.filter(Result.student_id.in_(student_ids)).all()
        result_map = {r.student_id: r for r in results}

        for st_id, st_marks in student_marks.items():
            # Check if student failed any subject
            has_failed = any(m.grade == 'F' or m.grade_point == 0 for m in st_marks)
            if has_failed:
                failed += 1
            else:
                passed += 1

            # Get SGPA
            res_obj = result_map.get(st_id)
            if res_obj and res_obj.sgpa > 0:
                sgpa_list.append(res_obj.sgpa)
            else:
                total_gp = sum(m.grade_point * m.subject.credits for m in st_marks if m.subject)
                total_credits = sum(m.subject.credits for m in st_marks if m.subject)
                sgpa = total_gp / total_credits if total_credits > 0 else 0.0
                sgpa_list.append(sgpa)

            # Percentage calculation
            total_obtained = sum(m.total for m in st_marks)
            max_possible = len(st_marks) * 100.0
            percentage = (total_obtained / max_possible * 100.0) if max_possible > 0 else 0.0
            pct_list.append(percentage)

        pass_percentage = round((passed / appeared * 100.0), 2) if appeared > 0 else 0.0
        fail_percentage = round((failed / appeared * 100.0), 2) if appeared > 0 else 0.0
        average_sgpa = round(sum(sgpa_list) / len(sgpa_list), 2) if sgpa_list else 0.0
        average_percentage = round(sum(pct_list) / len(pct_list), 2) if pct_list else 0.0

        return {
            "appeared": appeared,
            "passed": passed,
            "failed": failed,
            "pass_percentage": pass_percentage,
            "fail_percentage": fail_percentage,
            "average_sgpa": average_sgpa,
            "average_percentage": average_percentage,
            "highest_sgpa": round(max(sgpa_list), 2) if sgpa_list else 0.0,
            "lowest_sgpa": round(min(sgpa_list), 2) if sgpa_list else 0.0,
            "highest_percentage": round(max(pct_list), 2) if pct_list else 0.0,
            "lowest_percentage": round(min(pct_list), 2) if pct_list else 0.0
        }

    @staticmethod
    def get_chart_data(filters):
        """Retrieve responsive chart datasets."""
        filtered_subs = AnalyticsService.get_filtered_subjects(filters)
        subject_ids = [s['subject'].id for s in filtered_subs]
        if not subject_ids:
            return {}

        marks = Mark.query.filter(Mark.subject_id.in_(subject_ids)).all()
        student_marks = {}
        for m in marks:
            if m.student_id not in student_marks:
                student_marks[m.student_id] = []
            student_marks[m.student_id].append(m)

        # 1. Pass vs Fail
        passed = 0
        failed = 0
        sgpa_list = []
        pct_list = []
        grade_counts = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}

        for st_id, st_marks in student_marks.items():
            has_failed = any(m.grade == 'F' for m in st_marks)
            if has_failed:
                failed += 1
            else:
                passed += 1

            for m in st_marks:
                grade_counts[m.grade] = grade_counts.get(m.grade, 0) + 1

            total_obtained = sum(m.total for m in st_marks)
            max_possible = len(st_marks) * 100.0
            percentage = (total_obtained / max_possible * 100.0) if max_possible > 0 else 0.0
            pct_list.append(percentage)

            total_gp = sum(m.grade_point * m.subject.credits for m in st_marks if m.subject)
            total_credits = sum(m.subject.credits for m in st_marks if m.subject)
            sgpa = total_gp / total_credits if total_credits > 0 else 0.0
            sgpa_list.append(sgpa)

        # 2. Subject-wise Average Marks
        subj_avg = []
        for s in filtered_subs:
            sub_id = s['subject'].id
            sub_marks = [m.total for m in marks if m.subject_id == sub_id]
            avg = round(sum(sub_marks) / len(sub_marks), 2) if sub_marks else 0.0
            subj_avg.append({"code": s['subject'].code, "name": s['subject'].name, "average": avg})

        # Top Performing / Lowest Performing Subjects
        sorted_subjs = sorted(subj_avg, key=lambda x: x['average'], reverse=True)
        top_subjects = sorted_subjs[:5]
        lowest_subjects = sorted_subjs[-5:][::-1]

        # 3. Department-wise Pass Percentage
        dept_marks = {}
        for s in filtered_subs:
            dept = s['department']
            if dept not in dept_marks:
                dept_marks[dept] = []
            dept_marks[dept].extend([m for m in marks if m.subject_id == s['subject'].id])

        dept_pass_rates = []
        for dept, d_marks in dept_marks.items():
            d_st_marks = {}
            for m in d_marks:
                if m.student_id not in d_st_marks:
                    d_st_marks[m.student_id] = []
                d_st_marks[m.student_id].append(m)
            
            d_passed = sum(1 for st_id, st_m in d_st_marks.items() if not any(m.grade == 'F' for m in st_m))
            d_appeared = len(d_st_marks)
            rate = round((d_passed / d_appeared * 100.0), 2) if d_appeared > 0 else 0.0
            dept_pass_rates.append({"department": dept, "pass_percentage": rate})

        # 4. Semester-wise Performance
        sem_marks = {}
        for s in filtered_subs:
            sem = s['semester']
            if sem not in sem_marks:
                sem_marks[sem] = []
            sem_marks[sem].extend([m for m in marks if m.subject_id == s['subject'].id])

        sem_performance = []
        for sem, s_marks in sem_marks.items():
            s_st_marks = {}
            for m in s_marks:
                if m.student_id not in s_st_marks:
                    s_st_marks[m.student_id] = []
                s_st_marks[m.student_id].append(m)

            s_passed = sum(1 for st_id, st_m in s_st_marks.items() if not any(m.grade == 'F' for m in st_m))
            s_appeared = len(s_st_marks)
            rate = round((s_passed / s_appeared * 100.0), 2) if s_appeared > 0 else 0.0
            sem_performance.append({"semester": f"Sem {sem}", "pass_percentage": rate})

        # 5. SGPA Distribution (Histogram)
        sgpa_dist = {"<4.0": 0, "4.0-5.0": 0, "5.0-6.0": 0, "6.0-7.0": 0, "7.0-8.0": 0, "8.0-9.0": 0, "9.0-10.0": 0}
        for val in sgpa_list:
            if val < 4.0: sgpa_dist["<4.0"] += 1
            elif val < 5.0: sgpa_dist["4.0-5.0"] += 1
            elif val < 6.0: sgpa_dist["5.0-6.0"] += 1
            elif val < 7.0: sgpa_dist["6.0-7.0"] += 1
            elif val < 8.0: sgpa_dist["7.0-8.0"] += 1
            elif val < 9.0: sgpa_dist["8.0-9.0"] += 1
            else: sgpa_dist["9.0-10.0"] += 1

        # 6. Percentage Distribution (Histogram)
        pct_dist = {"<40%": 0, "40-50%": 0, "50-60%": 0, "60-70%": 0, "70-80%": 0, "80-90%": 0, "90-100%": 0}
        for val in pct_list:
            if val < 40.0: pct_dist["<40%"] += 1
            elif val < 50.0: pct_dist["40-50%"] += 1
            elif val < 60.0: pct_dist["50-60%"] += 1
            elif val < 70.0: pct_dist["60-70%"] += 1
            elif val < 80.0: pct_dist["70-80%"] += 1
            elif val < 90.0: pct_dist["80-90%"] += 1
            else: pct_dist["90-100%"] += 1

        return {
            "pass_vs_fail": {"labels": ["Pass", "Fail"], "data": [passed, failed]},
            "grade_distribution": {"labels": list(grade_counts.keys()), "data": list(grade_counts.values())},
            "subject_averages": {"labels": [x['code'] for x in subj_avg], "data": [x['average'] for x in subj_avg]},
            "top_performing": top_subjects,
            "lowest_performing": lowest_subjects,
            "department_pass": {"labels": [x['department'] for x in dept_pass_rates], "data": [x['pass_percentage'] for x in dept_pass_rates]},
            "semester_performance": {"labels": [x['semester'] for x in sem_performance], "data": [x['pass_percentage'] for x in sem_performance]},
            "sgpa_distribution": {"labels": list(sgpa_dist.keys()), "data": list(sgpa_dist.values())},
            "percentage_distribution": {"labels": list(pct_dist.keys()), "data": list(pct_dist.values())}
        }

    @staticmethod
    def get_merit_list(filters):
        """Generate rankings and merit details."""
        filtered_subs = AnalyticsService.get_filtered_subjects(filters)
        subject_ids = [s['subject'].id for s in filtered_subs]
        if not subject_ids:
            return []

        marks = Mark.query.filter(Mark.subject_id.in_(subject_ids)).all()
        student_marks = {}
        for m in marks:
            if m.student_id not in student_marks:
                student_marks[m.student_id] = []
            student_marks[m.student_id].append(m)

        student_ids = list(student_marks.keys())
        students = Student.query.filter(Student.id.in_(student_ids)).all()
        student_map = {s.id: s for s in students}

        results = Result.query.filter(Result.student_id.in_(student_ids)).all()
        result_map = {r.student_id: r for r in results}

        raw_list = []
        for st_id, st_marks in student_marks.items():
            st = student_map.get(st_id)
            if not st: continue
            
            res_obj = result_map.get(st_id)
            if res_obj and res_obj.sgpa > 0:
                sgpa = res_obj.sgpa
            else:
                total_gp = sum(m.grade_point * m.subject.credits for m in st_marks if m.subject)
                total_credits = sum(m.subject.credits for m in st_marks if m.subject)
                sgpa = round(total_gp / total_credits, 2) if total_credits > 0 else 0.0

            total_obtained = sum(m.total for m in st_marks)
            max_possible = len(st_marks) * 100.0
            percentage = round((total_obtained / max_possible * 100.0), 2) if max_possible > 0 else 0.0

            dept_name, _ = TabulationRegisterService.get_department_and_branch(st_marks[0].subject.code if st_marks and st_marks[0].subject else "")

            raw_list.append({
                "student_id": st.id,
                "roll_no": st.roll_no,
                "name": st.name,
                "department": dept_name,
                "semester": st.semester,
                "sgpa": sgpa,
                "percentage": percentage
            })

        # Calculate Rankings (ordered by SGPA desc, then percentage desc)
        raw_list.sort(key=lambda x: (x['sgpa'], x['percentage']), reverse=True)
        
        # Semester Rank
        sem_groups = {}
        for x in raw_list:
            sem = x['semester']
            if sem not in sem_groups:
                sem_groups[sem] = []
            sem_groups[sem].append(x)
        for sem, group in sem_groups.items():
            for idx, item in enumerate(group, start=1):
                item['semester_rank'] = idx

        # Department Rank
        dept_groups = {}
        for x in raw_list:
            dept = x['department']
            if dept not in dept_groups:
                dept_groups[dept] = []
            dept_groups[dept].append(x)
        for dept, group in dept_groups.items():
            for idx, item in enumerate(group, start=1):
                item['department_rank'] = idx

        # Overall Rank in merit list
        for idx, item in enumerate(raw_list, start=1):
            item['rank'] = idx

        return raw_list[:10]  # Top 10

    @staticmethod
    def get_subject_analytics(filters):
        """Subject-wise statistical metrics."""
        filtered_subs = AnalyticsService.get_filtered_subjects(filters)
        subject_ids = [s['subject'].id for s in filtered_subs]
        if not subject_ids:
            return []

        marks = Mark.query.filter(Mark.subject_id.in_(subject_ids)).all()
        
        results = []
        for item in filtered_subs:
            sub = item['subject']
            sub_marks = [m for m in marks if m.subject_id == sub.id]
            appeared = len(sub_marks)
            
            passed = sum(1 for m in sub_marks if m.grade != 'F')
            failed = appeared - passed
            pass_rate = round((passed / appeared * 100.0), 2) if appeared > 0 else 0.0

            totals = [m.total for m in sub_marks]
            avg_marks = round(sum(totals) / appeared, 2) if appeared > 0 else 0.0
            highest = max(totals) if totals else 0.0
            lowest = min(totals) if totals else 0.0

            grade_dist = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
            for m in sub_marks:
                grade_dist[m.grade] = grade_dist.get(m.grade, 0) + 1

            results.append({
                "id": sub.id,
                "code": sub.code,
                "name": sub.name,
                "appeared": appeared,
                "passed": passed,
                "failed": failed,
                "pass_percentage": pass_rate,
                "average_marks": avg_marks,
                "highest_marks": highest,
                "lowest_marks": lowest,
                "grade_distribution": grade_dist
            })
        return results

    @staticmethod
    def get_teacher_dashboard_stats(teacher_id, filters=None):
        """Stats for Teacher Dashboard Analytics section (restricted to their assigned subjects)."""
        if filters is None:
            filters = {}
        filters['teacher_id'] = teacher_id
        
        filtered_subs = AnalyticsService.get_filtered_subjects(filters)
        subject_ids = [s['subject'].id for s in filtered_subs]

        # Aggregation values
        assigned_subjects = len(filtered_subs)
        
        # Status counts
        processed_results = sum(1 for s in filtered_subs if s['subject'].processing_status != 'NOT_PROCESSED')
        submitted_results = sum(1 for s in filtered_subs if s['subject'].processing_status == 'SUBMITTED')
        pending_uploads = sum(1 for s in filtered_subs if s['subject'].processing_status in ['NOT_PROCESSED', 'DRAFT'])

        if not subject_ids:
            return {
                "assigned_subjects": assigned_subjects,
                "processed_results": processed_results,
                "submitted_results": submitted_results,
                "pending_uploads": pending_uploads,
                "average_marks": 0.0,
                "pass_percentage": 0.0,
                "fail_percentage": 0.0,
                "subject_performance": []
            }

        marks = Mark.query.filter(Mark.subject_id.in_(subject_ids)).all()
        appeared = len(marks)
        passed = sum(1 for m in marks if m.grade != 'F')
        failed = appeared - passed

        pass_percentage = round((passed / appeared * 100.0), 2) if appeared > 0 else 0.0
        fail_percentage = round((failed / appeared * 100.0), 2) if appeared > 0 else 0.0
        
        avg_marks = round(sum(m.total for m in marks) / appeared, 2) if appeared > 0 else 0.0

        # Subject wise performance list
        subject_performance = []
        for item in filtered_subs:
            sub = item['subject']
            sub_marks = [m for m in marks if m.subject_id == sub.id]
            sub_app = len(sub_marks)
            sub_pass = sum(1 for m in sub_marks if m.grade != 'F')
            sub_fail = sub_app - sub_pass
            sub_pass_rate = round((sub_pass / sub_app * 100.0), 2) if sub_app > 0 else 0.0
            sub_avg = round(sum(m.total for m in sub_marks) / sub_app, 2) if sub_app > 0 else 0.0

            subject_performance.append({
                "code": sub.code,
                "name": sub.name,
                "appeared": sub_app,
                "pass_percentage": sub_pass_rate,
                "fail_percentage": round(100.0 - sub_pass_rate, 2) if sub_app > 0 else 0.0,
                "average_marks": sub_avg
            })

        return {
            "assigned_subjects": assigned_subjects,
            "processed_results": processed_results,
            "submitted_results": submitted_results,
            "pending_uploads": pending_uploads,
            "average_marks": avg_marks,
            "pass_percentage": pass_percentage,
            "fail_percentage": fail_percentage,
            "subject_performance": subject_performance
        }


