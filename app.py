from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, jsonify, send_file
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os, random, json, io

app = Flask(__name__)
app.secret_key = "super-secret-localhost-key-2026"
app.config['TEMPLATES_AUTO_RELOAD'] = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
FACULTY_FILE = os.path.join(DATA_DIR, "faculty.json")
PRACTICALS_FILE = os.path.join(DATA_DIR, "practicals.json")
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
SUBJECTS_FILE = os.path.join(DATA_DIR, "subjects.json")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

EXAM_DURATION_SECONDS = 30 * 60

def load_json(path):
    if not os.path.exists(path):
        if "users" in path or "faculty" in path:
            return {}
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            content = f.read().strip()
            if not content:
                return {} if "users" in path or "faculty" in path else []
            return json.loads(content)
        except Exception as e:
            print(f"Warning: Could not parse {path}: {e}")
            return {} if "users" in path or "faculty" in path else []

def save_json(path, data):
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def is_student():
    return "roll_no" in session

def is_faculty():
    return "faculty_id" in session

def is_logged_in():
    return is_student() or is_faculty()

def delete_user_results(roll_no):
    """Delete all result files for a specific user"""
    if os.path.exists(RESULTS_DIR):
        for filename in os.listdir(RESULTS_DIR):
            if filename.startswith(f"Result_RollNo_{roll_no}_") and filename.endswith('.txt'):
                filepath = os.path.join(RESULTS_DIR, filename)
                try:
                    os.remove(filepath)
                except:
                    pass

def get_student_results(roll_no):
    results = []
    if os.path.exists(RESULTS_DIR):
        for filename in os.listdir(RESULTS_DIR):
            if filename.startswith(f"Result_RollNo_{roll_no}_") and filename.endswith('.txt'):
                filepath = os.path.join(RESULTS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception:
                    try:
                        with open(filepath, 'r', encoding='latin-1') as f:
                            content = f.read()
                    except Exception:
                        continue
                result_dict = {}
                # Parse ONLY the header section (lines before the ===== separator)
                # to avoid question text polluting the key-value dict
                for line in content.split('\n'):
                    if '==========' in line:
                        break   # stop at question section boundary
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key and key not in ('----------',):
                            result_dict[key] = value
                results.append(result_dict)
    return results

def get_practical_questions(practical_name):
    questions = load_json(QUESTIONS_FILE)
    return [q for q in questions if q.get('practical') == practical_name]

def get_questions_by_ids(id_list):
    """Fetch full question objects from file matching a list of IDs (preserves order)."""
    questions = load_json(QUESTIONS_FILE)
    id_set = {int(i) for i in id_list}
    by_id = {int(q["id"]): q for q in questions if int(q["id"]) in id_set}
    return [by_id[int(i)] for i in id_list if int(i) in by_id]

def get_subject_practicals(subject_id):
    """Get all practicals for a specific subject"""
    subjects = load_json(SUBJECTS_FILE)
    for subject in subjects:
        if subject['id'] == subject_id:
            return subject.get('practicals', [])
    return []

def get_all_practicals_for_subject(subject_name):
    """Get practicals by subject name"""
    subjects = load_json(SUBJECTS_FILE)
    for subject in subjects:
        if subject['name'] == subject_name:
            return subject.get('practicals', [])
    return []

def extract_practical_number(name):
    """Extract the practical number from names like 'Practical No: 1 Write a program...'"""
    import re
    # Match "Practical No: 1" / "Practical No 1" / "Practical 1" (case-insensitive)
    match = re.search(r'(?i)practical\s*(?:no\.?\s*)?:?\s*(\d+)', name)
    if match:
        return int(match.group(1))
    # Fallback: any leading number
    match = re.search(r'^\s*(\d+)', name)
    if match:
        return int(match.group(1))
    return 9999  # No number found — push to end

def insert_practical_sorted(practicals_list, new_practical):
    """Insert new_practical into the list in ascending practical-number order."""
    new_num = extract_practical_number(new_practical)
    for i, p in enumerate(practicals_list):
        if extract_practical_number(p) > new_num:
            practicals_list.insert(i, new_practical)
            return practicals_list
    practicals_list.append(new_practical)
    return practicals_list

def parse_result_file(filepath):
    """Parse result file and extract detailed question-wise results"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract basic info — parse ONLY the header section (stop at ====)
    result_dict = {}
    lines = content.split('\n')
    
    for line in lines:
        if '==========' in line:
            break      # stop before question-wise section
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            if key:
                result_dict[key] = value.strip()
    
    # Extract detailed answers
    detailed_answers = []
    in_questions_section = False
    current_question = {}
    
    for line in lines:
        if "QUESTION WISE RESULT" in line:
            in_questions_section = True
            continue
        
        if in_questions_section:
            line = line.strip()
            
            if line.startswith('Q') and '. ' in line:
                # Save previous question if exists
                if current_question:
                    detailed_answers.append(current_question)
                
                # Start new question
                current_question = {
                    'question': line.split('. ', 1)[1] if '. ' in line else '',
                    'options': []
                }
            elif line.startswith('A) ') or line.startswith('B) ') or line.startswith('C) ') or line.startswith('D) '):
                current_question['options'].append(line)
            elif line.startswith('Your Answer:'):
                current_question['student_answer'] = line.split(':', 1)[1].strip()
            elif line.startswith('Correct Answer:'):
                current_question['correct_answer'] = line.split(':', 1)[1].strip()
            elif line.startswith('Status:'):
                current_question['status'] = line.split(':', 1)[1].strip()
    
    # Add last question
    if current_question:
        detailed_answers.append(current_question)
    
    result_dict['detailed_answers'] = detailed_answers
    return result_dict

@app.route("/", methods=["GET", "POST"])
def index():
    users = load_json(USERS_FILE)
    faculty_data = load_json(FACULTY_FILE)
    
    if request.method == "POST":
        login_type = request.form.get("login_type")
        action = request.form.get("action")
        
        if login_type == "student":
            if action == "login":
                roll = request.form.get("roll_no", "").strip()
                password = request.form.get("password", "").strip()
                user = users.get(roll)
                
                if user and user["password"] == password:
                    session["roll_no"] = roll
                    session["full_name"] = user["full_name"]
                    session["branch"] = user["branch"]
                    session["year"] = user["year"]
                    session["batch"] = user.get("batch", "1")
                    session["email"] = user["email"]
                    session["user_type"] = "student"
                    flash("Login successful.", "success")
                    return redirect(url_for("dashboard"))
                else:
                    flash("Invalid roll number or password.", "error")
            
            elif action == "register":
                roll = request.form.get("roll_no", "").strip()
                password = request.form.get("password", "").strip()
                full_name = request.form.get("full_name", "").strip()
                branch = request.form.get("branch")
                year = request.form.get("year")
                batch = request.form.get("batch", "1")
                email = request.form.get("email", "").strip()
                
                if not roll or not password or len(password) < 6:
                    flash("Roll no + password required, password must be at least 6 characters.", "error")
                elif roll in users:
                    flash("Roll number already exists.", "error")
                else:
                    users[roll] = {
                        "roll_no": roll,
                        "password": password,
                        "full_name": full_name,
                        "branch": branch,
                        "year": year,
                        "batch": batch,
                        "email": email
                    }
                    save_json(USERS_FILE, users)
                    flash("Profile created successfully. Now you can login.", "success")
        
        elif login_type == "faculty":
            if action == "login":
                faculty_id = request.form.get("faculty_id", "").strip()
                password = request.form.get("password", "").strip()
                faculty = faculty_data.get(faculty_id)
                
                if faculty and faculty["password"] == password:
                    session["faculty_id"] = faculty_id
                    session["full_name"] = faculty["full_name"]
                    session["department"] = faculty["department"]
                    session["email"] = faculty["email"]
                    session["user_type"] = "faculty"
                    flash("Login successful.", "success")
                    return redirect(url_for("faculty_dashboard"))
                else:
                    flash("Invalid faculty ID or password.", "error")
            
            elif action == "register":
                faculty_id = request.form.get("faculty_id", "").strip()
                password = request.form.get("password", "").strip()
                full_name = request.form.get("full_name", "").strip()
                department = request.form.get("department")
                email = request.form.get("email", "").strip()
                
                if not faculty_id or not password or len(password) < 6:
                    flash("Faculty ID + password required, password must be at least 6 characters.", "error")
                elif faculty_id in faculty_data:
                    flash("Faculty ID already exists.", "error")
                else:
                    faculty_data[faculty_id] = {
                        "faculty_id": faculty_id,
                        "password": password,
                        "full_name": full_name,
                        "department": department,
                        "email": email
                    }
                    save_json(FACULTY_FILE, faculty_data)
                    flash("Faculty profile created successfully. Now you can login.", "success")
    
    return render_template("login.html")

@app.route("/forgot_password", methods=["POST"])
def forgot_password():
    """Handle forgot password requests"""
    user_type = request.form.get("user_type")
    email = request.form.get("email", "").strip()
    
    if user_type == "student":
        users = load_json(USERS_FILE)
        for roll_no, user in users.items():
            if user.get("email") == email:
                # In production, send email instead
                return jsonify({"success": True, "message": f"Your password is: {user['password']}", "roll_no": roll_no})
        return jsonify({"success": False, "message": "Email not found"})
    
    elif user_type == "faculty":
        faculty = load_json(FACULTY_FILE)
        for fac_id, fac in faculty.items():
            if fac.get("email") == email:
                # In production, send email instead
                return jsonify({"success": True, "message": f"Your password is: {fac['password']}", "faculty_id": fac_id})
        return jsonify({"success": False, "message": "Email not found"})
    
    return jsonify({"success": False, "message": "Invalid request"})

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not is_student():
        return redirect(url_for("index"))
    
    users = load_json(USERS_FILE)
    user = users.get(session["roll_no"])
    subjects = load_json(SUBJECTS_FILE)
    
    # Get selected subject — priority: URL param → session memory → first subject
    first_subject = subjects[0]['name'] if subjects else 'all'
    # Restore subject from session if not in URL (preserves selection across exam round-trips)
    session_subject = session.get('selected_subject', first_subject)
    selected_subject = request.args.get('subject', session_subject)
    # Validate: make sure the subject actually exists
    valid_names = [s['name'] for s in subjects]
    if selected_subject not in valid_names:
        selected_subject = first_subject
    # Always save current selection to session
    session['selected_subject'] = selected_subject

    # Get practicals based on subject
    if selected_subject == 'all':
        practicals = load_json(PRACTICALS_FILE)
    else:
        practicals = get_all_practicals_for_subject(selected_subject)
    
    student_results = get_student_results(session["roll_no"])
    submitted_practicals = {r.get("Practical", "") for r in student_results}
    
    if request.method == "POST":
        practical_name = request.form.get("practical_name")
        
        if practical_name in submitted_practicals:
            flash("You have already submitted this practical.", "error")
            return redirect(url_for("dashboard", subject=selected_subject))
        
        questions = get_practical_questions(practical_name)
        
        if not questions:
            flash(f"No questions available for this practical. Please contact faculty.", "error")
            return redirect(url_for("dashboard", subject=selected_subject))
        
        random.shuffle(questions)
        # Take up to 20 questions (if fewer are available, use all of them)
        selected = questions[:20]
        
        # Clear ALL previous exam/result data — Flask cookie sessions are limited to ~4KB.
        # Storing full question objects overflows the cookie; store IDs only.
        for key in ["last_result", "last_result_file", "exam_question_ids",
                    "exam_questions", "exam_start_time", "exam_duration", "practical_name"]:
            session.pop(key, None)
        
        # Store ONLY question IDs (tiny) — full data fetched from file at exam & submit time
        session["exam_question_ids"] = [int(q["id"]) for q in selected]
        session["exam_start_time"] = datetime.now().timestamp()
        session["exam_duration"] = EXAM_DURATION_SECONDS
        session["practical_name"] = practical_name
        session.modified = True
        return redirect(url_for("exam"))
    
    return render_template("dashboard.html", title="Dashboard", user=user, practicals=practicals, 
                          submitted_practicals=submitted_practicals, student_results=student_results,
                          subjects=subjects, selected_subject=selected_subject)

@app.route("/faculty_dashboard")
def faculty_dashboard():
    if not is_faculty():
        return redirect(url_for("index"))
    
    faculty_data = load_json(FACULTY_FILE)
    faculty = faculty_data.get(session["faculty_id"])
    all_students = load_json(USERS_FILE)
    practicals = load_json(PRACTICALS_FILE)
    subjects = load_json(SUBJECTS_FILE)
    
    selected_batch = request.args.get('batch', 'all')
    # Default to first subject so a subject is always selected
    first_subject = subjects[0]['name'] if subjects else 'all'
    selected_subject = request.args.get('subject', first_subject)
    
    # Filter students by batch
    if selected_batch != 'all':
        students = {k: v for k, v in all_students.items() if v.get('batch', '1') == selected_batch}
    else:
        students = all_students
    
    # Filter practicals by subject
    if selected_subject != 'all':
        practicals = get_all_practicals_for_subject(selected_subject)
    
    all_batches = sorted(set(s.get('batch', '1') for s in all_students.values()))
    
    # Get all results — parse ONLY the header section (stop at ====).
    # Key rule: keep only the LATEST result per (roll_no, practical) pair using
    # the Unix timestamp embedded in the filename: Result_RollNo_<roll>_<ts>.txt
    # This prevents old corrupt submissions from overwriting correct scores.
    _raw_results = {}   # key: (roll_no, practical_name) → (timestamp, result_dict)
    if os.path.exists(RESULTS_DIR):
        for filename in os.listdir(RESULTS_DIR):
            if not filename.endswith('.txt'):
                continue
            filepath = os.path.join(RESULTS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as _f:
                    raw = _f.read()
            except Exception:
                try:
                    with open(filepath, 'r', encoding='latin-1') as _f:
                        raw = _f.read()
                except Exception:
                    continue
            result_dict = {}
            for line in raw.split('\n'):
                if '==========' in line:
                    break          # stop before question-wise section
                if ':' in line:
                    _k, _v = line.split(':', 1)
                    _k = _k.strip()
                    if _k:
                        result_dict[_k] = _v.strip()
            practical_nm = result_dict.get('Practical', '').strip()
            roll_nm      = result_dict.get('Roll No', '').strip()
            if not practical_nm or not roll_nm:
                continue
            # Extract timestamp from filename for "latest wins" logic
            try:
                ts = int(filename.replace('.txt','').rsplit('_', 1)[-1])
            except Exception:
                ts = 0
            dedup_key = (roll_nm, practical_nm)
            if dedup_key not in _raw_results or ts > _raw_results[dedup_key][0]:
                _raw_results[dedup_key] = (ts, result_dict)
    # Flatten to list (guaranteed: one entry per student+practical, always the latest)
    all_results = [v for _, v in _raw_results.values()]
    
    # Calculate student performance
    student_performance = {}
    for student_id, student_data in students.items():
        student_results = [r for r in all_results if r.get("Roll No") == student_id]
        
        practical_scores = {}
        total_score = 0
        count = 0
        
        for result in student_results:
            practical_name = result.get("Practical", "").strip()
            if not practical_name:
                continue
            # Filter by subject — normalize whitespace on both sides of comparison
            practicals_stripped = [p.strip() for p in practicals]
            if selected_subject != 'all' and practical_name not in practicals_stripped:
                continue
            # Use the canonical name from the practicals list (exact match after strip)
            try:
                canonical = practicals[[p.strip() for p in practicals].index(practical_name)]
            except ValueError:
                canonical = practical_name

            score_str = result.get("Score", "0 / 0")
            if '/' in score_str:
                try:
                    score = int(score_str.split('/')[0].strip())
                except ValueError:
                    score = 0
                # Only count each practical once (dedup already done in all_results)
                if canonical not in practical_scores:
                    practical_scores[canonical] = score
                    total_score += score
                    count += 1
        
        avg_score = round(total_score / count, 2) if count > 0 else 0
        
        student_performance[student_id] = {
            "name": student_data["full_name"],
            "branch": student_data["branch"],
            "year": student_data["year"],
            "batch": student_data.get("batch", "1"),
            "email": student_data["email"],
            "practical_scores": practical_scores,
            "total": total_score,
            "average": avg_score,
            "exams_taken": count
        }
    
    # Calculate practical submissions
    practical_submissions = {}
    for practical_name in practicals:
        submitted_students = []
        pname_stripped = practical_name.strip()
        for result in all_results:
            if result.get("Practical", "").strip() == pname_stripped:
                roll_no = result.get("Roll No")
                if roll_no and roll_no in students and roll_no not in [s['roll_no'] for s in submitted_students]:
                    student = students.get(roll_no)
                    if student:
                        submitted_students.append({
                            'roll_no': roll_no, 
                            'name': student['full_name'], 
                            'batch': student.get('batch', '1')
                        })
        practical_submissions[practical_name] = submitted_students
    
    return render_template("faculty_dashboard.html", title="Faculty Dashboard", faculty=faculty, 
                          students=students, all_students=all_students, practicals=practicals, 
                          results=all_results, student_performance=student_performance, 
                          practical_submissions=practical_submissions, all_batches=all_batches, 
                          selected_batch=selected_batch, subjects=subjects, selected_subject=selected_subject)

@app.route("/api/add_subject", methods=["POST"])
def add_subject():
    if not is_faculty():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        subject_name = data.get("name", "").strip()
        
        if not subject_name:
            return jsonify({"success": False, "message": "Subject name required"}), 400
        
        subjects = load_json(SUBJECTS_FILE)
        
        # Check if subject already exists
        for subject in subjects:
            if subject['name'].lower() == subject_name.lower():
                return jsonify({"success": False, "message": "Subject already exists"}), 400
        
        # Generate new ID
        new_id = str(max([int(s['id']) for s in subjects]) + 1) if subjects else "1"
        
        # Add new subject
        subjects.append({
            "id": new_id,
            "name": subject_name,
            "practicals": []
        })
        
        save_json(SUBJECTS_FILE, subjects)
        
        return jsonify({"success": True, "subject": {"id": new_id, "name": subject_name}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/add_practical", methods=["POST"])
def add_practical():
    if not is_faculty():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        practical_name = data.get("name", "").strip()
        subject_id = data.get("subject_id", "1")
        
        if not practical_name:
            return jsonify({"success": False, "message": "Practical name required"}), 400

        practicals = load_json(PRACTICALS_FILE)
        
        if practical_name in practicals:
            return jsonify({"success": False, "message": "Practical already exists"}), 400
        
        # Insert in sorted order by practical number (e.g. "Practical No: 1" before "Practical No: 2")
        practicals = insert_practical_sorted(practicals, practical_name)
        save_json(PRACTICALS_FILE, practicals)
        
        # Add to subject's practicals in sorted order
        subjects = load_json(SUBJECTS_FILE)
        for subject in subjects:
            if subject['id'] == subject_id:
                if practical_name not in subject['practicals']:
                    subject['practicals'] = insert_practical_sorted(subject['practicals'], practical_name)
                break
        save_json(SUBJECTS_FILE, subjects)
        
        return jsonify({"success": True, "practical": practical_name}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/remove_practical", methods=["POST"])
def remove_practical():
    if not is_faculty():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        practical_name = data.get("name", "").strip()
        
        practicals = load_json(PRACTICALS_FILE)
        
        if practical_name not in practicals:
            return jsonify({"success": False, "message": "Practical not found"}), 404
        
        practicals.remove(practical_name)
        save_json(PRACTICALS_FILE, practicals)
        
        # Remove from all subjects
        subjects = load_json(SUBJECTS_FILE)
        for subject in subjects:
            if practical_name in subject['practicals']:
                subject['practicals'].remove(practical_name)
        save_json(SUBJECTS_FILE, subjects)
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/export_excel")
def export_excel():
    """Export all student performance to Excel"""
    if not is_faculty():
        return redirect(url_for("index"))
    
    try:
        all_students = load_json(USERS_FILE)
        practicals = load_json(PRACTICALS_FILE)
        selected_subject = request.args.get('subject', 'all')
        
        # Filter practicals by subject
        if selected_subject != 'all':
            practicals = get_all_practicals_for_subject(selected_subject)
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Student Performance"
        
        # Define styles
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="1976D2", end_color="1976D2", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Headers
        headers = ["Roll No", "Name", "Branch", "Year", "Batch"]
        headers.extend(practicals)
        headers.extend(["Total", "Average"])
        
        # Write and style headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(1, col, header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        # Add data
        row = 2
        for roll_no, student in all_students.items():
            ws.cell(row, 1, roll_no).border = border
            ws.cell(row, 2, student["full_name"]).border = border
            ws.cell(row, 3, student["branch"]).border = border
            ws.cell(row, 4, student["year"]).border = border
            ws.cell(row, 5, student.get("batch", "1")).border = border
            
            # Get all results for this student
            student_results = get_student_results(roll_no)
            scores_dict = {}
            for result in student_results:
                practical_name = result.get("Practical")
                if practical_name and practical_name in practicals:
                    score_str = result.get("Score", "0 / 20")
                    if '/' in score_str:
                        scores_dict[practical_name] = int(score_str.split('/')[0].strip())
            
            # Write scores
            col = 6
            total = 0
            count = 0
            for practical in practicals:
                score = scores_dict.get(practical, "-")
                cell = ws.cell(row, col, score)
                cell.border = border
                if score != "-":
                    total += score
                    count += 1
                    cell.alignment = Alignment(horizontal="center")
                col += 1
            
            # Write total and average
            ws.cell(row, col, total).border = border
            ws.cell(row, col, total).alignment = Alignment(horizontal="center")
            ws.cell(row, col, total).font = Font(bold=True)
            
            avg = round(total/count, 2) if count > 0 else 0
            ws.cell(row, col + 1, avg).border = border
            ws.cell(row, col + 1, avg).alignment = Alignment(horizontal="center")
            ws.cell(row, col + 1, avg).font = Font(bold=True)
            
            row += 1
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            ws.column_dimensions[column].width = adjusted_width
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Generate filename
        subject_suffix = f"_{selected_subject}" if selected_subject != 'all' else ""
        filename = f"student_performance{subject_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        flash(f"Error exporting to Excel: {str(e)}", "error")
        return redirect(url_for("faculty_dashboard"))

@app.route("/delete_account", methods=["POST"])
def delete_account():
    """Delete user account and all associated data"""
    if is_student():
        roll_no = session["roll_no"]
        
        # Delete from users.json
        users = load_json(USERS_FILE)
        if roll_no in users:
            del users[roll_no]
            save_json(USERS_FILE, users)
        
        # Delete all result files
        delete_user_results(roll_no)
        
        # Clear session
        session.clear()
        flash("Your account has been deleted successfully.", "success")
        return redirect(url_for("index"))
    
    elif is_faculty():
        faculty_id = session["faculty_id"]
        
        # Delete from faculty.json
        faculty = load_json(FACULTY_FILE)
        if faculty_id in faculty:
            del faculty[faculty_id]
            save_json(FACULTY_FILE, faculty)
        
        # Clear session
        session.clear()
        flash("Your account has been deleted successfully.", "success")
        return redirect(url_for("index"))
    
    return redirect(url_for("index"))

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if not is_student():
        return redirect(url_for("index"))
    
    users = load_json(USERS_FILE)
    roll_no = session["roll_no"]
    
    full_name = request.form.get("full_name", "").strip()
    branch = request.form.get("branch")
    year = request.form.get("year")
    batch = request.form.get("batch", "1")
    email = request.form.get("email", "").strip()
    
    if roll_no in users:
        users[roll_no]["full_name"] = full_name
        users[roll_no]["branch"] = branch
        users[roll_no]["year"] = year
        users[roll_no]["batch"] = batch
        users[roll_no]["email"] = email
        
        session["full_name"] = full_name
        session["branch"] = branch
        session["year"] = year
        session["batch"] = batch
        session["email"] = email
        
        save_json(USERS_FILE, users)
        flash("Profile updated successfully!", "success")
    
    return redirect(url_for("dashboard"))

@app.route("/faculty/update_profile", methods=["POST"])
def faculty_update_profile():
    if not is_faculty():
        return redirect(url_for("index"))
    
    faculty_data = load_json(FACULTY_FILE)
    faculty_id = session["faculty_id"]
    
    full_name = request.form.get("full_name", "").strip()
    department = request.form.get("department")
    email = request.form.get("email", "").strip()
    
    if faculty_id in faculty_data:
        faculty_data[faculty_id]["full_name"] = full_name
        faculty_data[faculty_id]["department"] = department
        faculty_data[faculty_id]["email"] = email
        
        session["full_name"] = full_name
        session["department"] = department
        session["email"] = email
        
        save_json(FACULTY_FILE, faculty_data)
        flash("Profile updated successfully!", "success")
    
    return redirect(url_for("faculty_dashboard"))

@app.route("/exam")
def exam():
    if not is_student():
        return redirect(url_for("index"))
    
    # Use IDs-only session approach (avoids 4KB cookie overflow)
    if "exam_question_ids" not in session:
        flash("Start exam from dashboard first.", "error")
        return redirect(url_for("dashboard"))
    
    # Fetch full question objects from file by stored IDs
    questions = get_questions_by_ids(session["exam_question_ids"])
    if not questions:
        flash("Exam data missing. Please start again from the dashboard.", "error")
        return redirect(url_for("dashboard"))
    
    start_time = session.get("exam_start_time")
    duration = session.get("exam_duration", EXAM_DURATION_SECONDS)
    now_ts = datetime.now().timestamp()
    remaining = int(start_time + duration - now_ts)
    
    if remaining <= 0:
        return redirect(url_for("submit_exam"))
    
    practical_name = session.get("practical_name", "")
    return render_template("exam.html", questions=questions, remaining=remaining, practical_name=practical_name)

@app.route("/submit_exam", methods=["POST", "GET"])
def submit_exam():
    if not is_student():
        return redirect(url_for("index"))

    # Use IDs-only approach — full question objects are never stored in session
    if "exam_question_ids" not in session:
        return redirect(url_for("dashboard"))

    # Fetch full questions from file using stored IDs (order preserved)
    questions = get_questions_by_ids(session["exam_question_ids"])
    if not questions:
        return redirect(url_for("dashboard"))

    submitted_answers = {}

    if request.method == "POST":
        for q in questions:
            qid = str(q["id"])
            submitted_answers[qid] = request.form.get(f"answer_{qid}")

    # Read practical_name from hidden form field first, fallback to session
    practical_name = (request.form.get("practical_name") or "").strip() or session.get("practical_name", "")

    total = len(questions)
    attempted = 0
    correct = 0
    detailed_answers = []

    for q in questions:
        qid = str(q["id"])
        ans = submitted_answers.get(qid)

        is_correct = ans == q["answer"] if ans else False

        if ans:
            attempted += 1
            if is_correct:
                correct += 1

        detailed_answers.append({
            "question": q["question"],
            "options": q.get("options", {}),
            "student_answer": ans if ans else "NOT ATTEMPTED",
            "correct_answer": q["answer"],
            "status": "CORRECT" if is_correct else ("WRONG" if ans else "NOT ATTEMPTED")
        })

    wrong = total - correct
    score = correct

    users = load_json(USERS_FILE)
    user = users.get(session["roll_no"])
    dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # practical_name already read from POST form at top of this function (with session fallback)

    # Store ONLY compact summary in session (no detailed_answers) to stay under Flask's 4KB cookie limit.
    # detailed_answers are written to the TXT file and read back by the result page via the filename.
    session["last_result"] = {
        "roll_no": user["roll_no"],
        "name": user["full_name"],
        "branch": user["branch"],
        "year": user["year"],
        "batch": user.get("batch", "1"),
        "email": user["email"],
        "practical_name": practical_name,
        "score": f"{score} / {total}",
        "total_questions": total,
        "attempted": attempted,
        "correct": correct,
        "wrong": wrong,
        "datetime": dt_str,
        "detailed_answers": []   # kept empty in session; loaded from file by /result
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    filename = f"Result_RollNo_{user['roll_no']}_{int(datetime.now().timestamp())}.txt"
    filepath = os.path.join(RESULTS_DIR, filename)

    lines = [
        f"Roll No: {user['roll_no']}",
        f"Name: {user['full_name']}",
        f"Branch: {user['branch']}",
        f"Year: {user['year']}",
        f"Batch: {user.get('batch', '1')}",
        f"Email: {user['email']}",
        f"Practical: {practical_name}",
        f"Score: {score} / {total}",
        f"Attempted: {attempted}",
        f"Correct: {correct}",
        f"Wrong: {wrong}",
        f"Date & Time: {dt_str}",
        "",
        "========== QUESTION WISE RESULT =========="
    ]

    q_no = 1
    for item in detailed_answers:
        lines.append("")
        lines.append(f"Q{q_no}. {item['question']}")

        options = item.get("options", {})
        for key in ["A", "B", "C", "D"]:
            lines.append(f"   {key}) {options.get(key, '')}")

        lines.append(f"Your Answer   : {item['student_answer']}")
        lines.append(f"Correct Answer: {item['correct_answer']}")
        lines.append(f"Status        : {item['status']}")
        lines.append("-" * 50)

        q_no += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    session["last_result_file"] = filename
    session.pop("exam_question_ids", None)
    session.pop("exam_start_time", None)
    session.pop("exam_duration", None)
    session.pop("practical_name", None)

    return redirect(url_for("result"))

@app.route("/result")
def result():
    result_data = session.get("last_result")
    filename = session.get("last_result_file")

    if not result_data:
        flash("No result found. Please take an exam first.", "error")
        return redirect(url_for("dashboard"))

    # If detailed_answers was stripped from session to save space, reload from file
    if not result_data.get("detailed_answers") and filename:
        filepath = os.path.join(RESULTS_DIR, filename)
        if os.path.exists(filepath):
            parsed = parse_result_file(filepath)
            result_data["detailed_answers"] = parsed.get("detailed_answers", [])

    return render_template(
        "result.html",
        result=result_data,
        filename=filename
    )

@app.route("/view_result/<practical_name>")
def view_result(practical_name):
    if not is_student():
        return redirect(url_for("index"))
    
    result_data = None
    filename = None
    
    # Find the result file for this practical
    if os.path.exists(RESULTS_DIR):
        for file in os.listdir(RESULTS_DIR):
            if file.startswith(f"Result_RollNo_{session['roll_no']}_") and file.endswith(".txt"):
                filepath = os.path.join(RESULTS_DIR, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if f"Practical: {practical_name}" in content:
                        # Parse the file
                        parsed_result = parse_result_file(filepath)
                        
                        result_data = {
                            "roll_no": parsed_result.get("Roll No"),
                            "name": parsed_result.get("Name"),
                            "branch": parsed_result.get("Branch"),
                            "year": parsed_result.get("Year"),
                            "batch": parsed_result.get("Batch", "1"),
                            "email": parsed_result.get("Email"),
                            "practical_name": parsed_result.get("Practical"),
                            "score": parsed_result.get("Score"),
                            "attempted": parsed_result.get("Attempted"),
                            "correct": parsed_result.get("Correct"),
                            "wrong": parsed_result.get("Wrong"),
                            "datetime": parsed_result.get("Date & Time"),
                            "detailed_answers": parsed_result.get("detailed_answers", [])
                        }
                        filename = file
                        break
    
    if not result_data:
        flash("Result not found.", "error")
        return redirect(url_for("dashboard"))
    
    return render_template(
        "result.html",
        result=result_data,
        filename=filename
    )

@app.route("/download/<filename>")
def download(filename):
    """Download result file"""
    return send_from_directory(RESULTS_DIR, filename, as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/faculty/view_result/<roll_no>/<practical_name>")
def faculty_view_result(roll_no, practical_name):
    """Faculty can view detailed student result"""
    if not is_faculty():
        return redirect(url_for("index"))
    
    result_data = None
    
    # Find the result file
    if os.path.exists(RESULTS_DIR):
        for filename in os.listdir(RESULTS_DIR):
            if filename.startswith(f"Result_RollNo_{roll_no}_") and filename.endswith('.txt'):
                filepath = os.path.join(RESULTS_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if f"Practical: {practical_name}" in content:
                        # Parse the file
                        parsed_result = parse_result_file(filepath)
                        
                        result_data = {
                            "roll_no": parsed_result.get("Roll No"),
                            "name": parsed_result.get("Name"),
                            "branch": parsed_result.get("Branch"),
                            "year": parsed_result.get("Year"),
                            "batch": parsed_result.get("Batch", "1"),
                            "email": parsed_result.get("Email"),
                            "practical_name": parsed_result.get("Practical"),
                            "score": parsed_result.get("Score"),
                            "attempted": parsed_result.get("Attempted"),
                            "correct": parsed_result.get("Correct"),
                            "wrong": parsed_result.get("Wrong"),
                            "datetime": parsed_result.get("Date & Time"),
                            "detailed_answers": parsed_result.get("detailed_answers", [])
                        }
                        break
    
    return render_template("result.html", result=result_data, filename=None, is_faculty_view=True)


@app.route("/faculty/get_result_data/<roll_no>/<practical_name>")
def get_result_data(roll_no, practical_name):
    """Returns result data as JSON for the faculty modal popup"""
    if not is_faculty():
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    if os.path.exists(RESULTS_DIR):
        for filename in os.listdir(RESULTS_DIR):
            if filename.startswith(f"Result_RollNo_{roll_no}_") and filename.endswith('.txt'):
                filepath = os.path.join(RESULTS_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if f"Practical: {practical_name}" in content:
                    parsed = parse_result_file(filepath)
                    result_data = {
                        "roll_no":          parsed.get("Roll No"),
                        "name":             parsed.get("Name"),
                        "branch":           parsed.get("Branch"),
                        "year":             parsed.get("Year"),
                        "batch":            parsed.get("Batch", "1"),
                        "email":            parsed.get("Email"),
                        "practical_name":   parsed.get("Practical"),
                        "score":            parsed.get("Score"),
                        "attempted":        parsed.get("Attempted"),
                        "correct":          parsed.get("Correct"),
                        "wrong":            parsed.get("Wrong"),
                        "datetime":         parsed.get("Date & Time"),
                        "detailed_answers": parsed.get("detailed_answers", [])
                    }
                    return jsonify({"success": True, "result": result_data})

    return jsonify({"success": False, "message": "Result not found"})


@app.route("/faculty/get_result_txt/<roll_no>/<practical_name>")
def get_result_txt(roll_no, practical_name):
    """Returns raw txt file content as JSON for the TXT viewer modal"""
    if not is_faculty():
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    if os.path.exists(RESULTS_DIR):
        for filename in os.listdir(RESULTS_DIR):
            if filename.startswith(f"Result_RollNo_{roll_no}_") and filename.endswith('.txt'):
                filepath = os.path.join(RESULTS_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                if f"Practical: {practical_name}" in file_content:
                    return jsonify({
                        "success":  True,
                        "content":  file_content,
                        "filename": filename
                    })

    return jsonify({"success": False, "message": "File not found"})

@app.route("/api/get_questions")
def get_questions():
    if not is_faculty():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    practical_name = request.args.get("practical", "").strip()
    if not practical_name:
        return jsonify({"success": False, "message": "Practical name required"}), 400
    questions = load_json(QUESTIONS_FILE)
    practical_questions = [q for q in questions if q.get("practical") == practical_name]
    return jsonify({"success": True, "questions": practical_questions, "count": len(practical_questions)})


@app.route("/api/add_question", methods=["POST"])
def add_question():
    if not is_faculty():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        data = request.get_json()
        practical_name = data.get("practical", "").strip()
        question_text  = data.get("question", "").strip()
        options        = data.get("options", {})
        answer         = data.get("answer", "").strip()

        if not practical_name:
            return jsonify({"success": False, "message": "Practical name required"}), 400
        if not question_text:
            return jsonify({"success": False, "message": "Question text required"}), 400
        if not all(options.get(k, "").strip() for k in ["A", "B", "C", "D"]):
            return jsonify({"success": False, "message": "All 4 options are required"}), 400
        if answer not in ["A", "B", "C", "D"]:
            return jsonify({"success": False, "message": "Correct answer must be A, B, C or D"}), 400

        questions = load_json(QUESTIONS_FILE)
        existing = [q for q in questions if q.get("practical") == practical_name]
        if len(existing) >= 20:
            return jsonify({"success": False, "message": "Maximum 20 questions allowed per practical"}), 400

        new_id = max((q.get("id", 0) for q in questions), default=0) + 1
        new_question = {
            "id":        new_id,
            "practical": practical_name,
            "question":  question_text,
            "options":   {
                "A": options.get("A", "").strip(),
                "B": options.get("B", "").strip(),
                "C": options.get("C", "").strip(),
                "D": options.get("D", "").strip()
            },
            "answer": answer
        }
        questions.append(new_question)
        save_json(QUESTIONS_FILE, questions)
        return jsonify({"success": True, "question": new_question, "total": len(existing) + 1}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error: " + str(e)}), 500


@app.route("/api/delete_question", methods=["POST"])
def delete_question():
    if not is_faculty():
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        data = request.get_json()
        question_id = data.get("id")
        questions = load_json(QUESTIONS_FILE)
        original_len = len(questions)
        questions = [q for q in questions if q.get("id") != question_id]
        if len(questions) == original_len:
            return jsonify({"success": False, "message": "Question not found"}), 404
        save_json(QUESTIONS_FILE, questions)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)