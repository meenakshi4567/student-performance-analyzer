import mysql.connector
import csv, hashlib, datetime, os, getpass
import sys

# Fix Windows terminal encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ==========================================
#  DATABASE CONNECTION
# ==========================================

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "mysql",       # Change if needed
    "database": "spa_db"
}

# ==========================================
#  GLOBAL SESSION
# ==========================================

current_user = {
    "id":         None,
    "username":   None,
    "role":       None,
    "student_id": None
}

# ==========================================
#  HELPERS
# ==========================================

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def print_line(char="-", width=60):
    print(char * width)

def print_table(headers, rows):
    """Print a simple terminal table."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print_line()
    print(fmt.format(*headers))
    print_line()
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))
    print_line()

# ==========================================
#  AUDIT LOG
# ==========================================

def log_audit(action, details=''):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_log (user_id, action, details) VALUES (%s, %s, %s)",
            (current_user['id'], action, details)
        )
        conn.commit()
    except Exception as e:
        pass   # Audit must never crash the app
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# ==========================================
#  LOGIN SYSTEM
# ==========================================

def login():
    print_line("=")
    print("  STUDENT PERFORMANCE ANALYZER -- LOGIN")
    print_line("=")
    username = input("  Username: ").strip()
    password = getpass.getpass("  Password: ")
    hashed   = hash_password(password)

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND is_active = 1",
            (username,)
        )
        user = cursor.fetchone()

        if user and user['password_hash'] == hashed:
            current_user['id']       = user['id']
            current_user['username'] = user['username']
            current_user['role']     = user['role']

            # Fetch student_id if role is student
            if user['role'] == 'student':
                cursor.execute(
                    "SELECT id FROM students WHERE user_id = %s", (user['id'],)
                )
                s = cursor.fetchone()
                current_user['student_id'] = s['id'] if s else None

            log_audit('LOGIN', f"{username} logged in successfully")
            print(f"\n  [OK] Welcome, {username}! Role: {user['role'].upper()}\n")
            return True
        else:
            log_audit('LOGIN_FAILED', f"{username} failed login attempt")
            print("\n  [ERR] Invalid username or password.\n")
            return False

    except Exception as e:
        print(f"\n  Database error: {e}\n")
        return False
    finally:
        cursor.close()
        conn.close()

# ==========================================
#  STUDENT CRUD
# ==========================================

def add_student():
    print_line()
    print("  ADD STUDENT")
    print_line()
    name       = input("  Name       : ").strip()
    department = input("  Department : ").strip()
    try:
        marks = float(input("  Marks      : ").strip())
    except ValueError:
        print("  [ERR] Invalid marks value.")
        return
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (name, department, marks) VALUES (%s, %s, %s)",
            (name, department, marks)
        )
        conn.commit()
        log_audit('ADD_STUDENT', f"Added {name} to {department}")
        print(f"\n  [OK] Student '{name}' added successfully!\n")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def view_students():
    print_line()
    print("  ALL STUDENTS")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, department, marks, enrolled_at FROM students ORDER BY id")
        rows = cursor.fetchall()
        if not rows:
            print("  No students found.")
            return
        print_table(
            ["ID", "Name", "Department", "Marks", "Enrolled At"],
            [[r['id'], r['name'], r['department'], r['marks'], r['enrolled_at']] for r in rows]
        )
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def search_by_dept():
    print_line()
    print("  SEARCH BY DEPARTMENT")
    print_line()
    dept = input("  Enter department (leave blank for all): ").strip()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        if dept:
            cursor.execute(
                "SELECT id, name, department, marks FROM students WHERE LOWER(department) = LOWER(%s) ORDER BY marks DESC",
                (dept,)
            )
        else:
            cursor.execute("SELECT id, name, department, marks FROM students ORDER BY marks DESC")
        rows = cursor.fetchall()
        if not rows:
            print("  No students found.")
            return
        print_table(
            ["ID", "Name", "Department", "Marks"],
            [[r['id'], r['name'], r['department'], r['marks']] for r in rows]
        )
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def update_student():
    print_line()
    print("  UPDATE STUDENT")
    print_line()
    try:
        sid = int(input("  Enter Student ID to update: ").strip())
    except ValueError:
        print("  [ERR] Invalid ID.")
        return
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE id = %s", (sid,))
        student = cursor.fetchone()
        if not student:
            print("  [ERR] Student not found.")
            return
        print(f"  Current -> Name: {student['name']}  Dept: {student['department']}  Marks: {student['marks']}")
        name       = input(f"  New Name [{student['name']}]: ").strip() or student['name']
        department = input(f"  New Dept [{student['department']}]: ").strip() or student['department']
        marks_in   = input(f"  New Marks [{student['marks']}]: ").strip()
        marks      = float(marks_in) if marks_in else student['marks']

        cursor2 = conn.cursor()
        cursor2.execute(
            "UPDATE students SET name=%s, department=%s, marks=%s WHERE id=%s",
            (name, department, marks, sid)
        )
        conn.commit()
        log_audit('UPDATE_STUDENT', f"Updated student ID {sid}")
        print(f"\n  [OK] Student ID {sid} updated successfully!\n")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def delete_student():
    print_line()
    print("  DELETE STUDENT  [Admin Only]")
    print_line()
    try:
        sid = int(input("  Enter Student ID to delete: ").strip())
    except ValueError:
        print("  [ERR] Invalid ID.")
        return
    confirm = input(f"  Are you sure you want to delete student ID {sid}? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("  Deletion cancelled.")
        return
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE id = %s", (sid,))
        conn.commit()
        log_audit('DELETE_STUDENT', f"Deleted student ID {sid}")
        print(f"\n  [OK] Student ID {sid} deleted.\n")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def view_own_record():
    print_line()
    print("  MY RECORD")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE user_id = %s", (current_user['id'],))
        record = cursor.fetchone()
        if not record:
            print("  No student record linked to your account.")
            return
        print(f"  Name       : {record['name']}")
        print(f"  Department : {record['department']}")
        print(f"  Marks      : {record['marks']}")
        print(f"  Enrolled   : {record['enrolled_at']}")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

# ==========================================
#  ANALYTICS
# ==========================================

def dashboard():
    print_line("=")
    print("  LIVE ANALYTICS DASHBOARD")
    print_line("=")
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT COUNT(*) AS total, ROUND(AVG(marks),2) AS average,
                   MAX(marks) AS highest, MIN(marks) AS lowest
            FROM students
        """)
        s = cursor.fetchone()
        print(f"  Total Students : {s['total']}")
        print(f"  Average Marks  : {s['average']}")
        print(f"  Highest Marks  : {s['highest']}")
        print(f"  Lowest Marks   : {s['lowest']}")

        print_line()
        print("  TOP 3 PERFORMERS")
        print_line()
        cursor.execute("""
            SELECT name, department, marks
            FROM students ORDER BY marks DESC LIMIT 3
        """)
        top = cursor.fetchall()
        print_table(["Name", "Department", "Marks"],
                    [[r['name'], r['department'], r['marks']] for r in top])

        print("  GRADE DISTRIBUTION")
        cursor.execute("""
            SELECT
                SUM(CASE WHEN marks >= 90                THEN 1 ELSE 0 END) AS grade_A,
                SUM(CASE WHEN marks >= 75 AND marks < 90 THEN 1 ELSE 0 END) AS grade_B,
                SUM(CASE WHEN marks >= 60 AND marks < 75 THEN 1 ELSE 0 END) AS grade_C,
                SUM(CASE WHEN marks >= 40 AND marks < 60 THEN 1 ELSE 0 END) AS grade_D,
                SUM(CASE WHEN marks < 40                 THEN 1 ELSE 0 END) AS grade_F
            FROM students
        """)
        g = cursor.fetchone()
        print_table(["A (>=90)", "B (75-89)", "C (60-74)", "D (40-59)", "F (<40)"],
                    [[g['grade_A'], g['grade_B'], g['grade_C'], g['grade_D'], g['grade_F']]])

        print("  DEPARTMENT SUMMARY")
        cursor.execute("""
            SELECT department, COUNT(*) AS total, ROUND(AVG(marks),2) AS avg_marks,
                   MAX(marks) AS highest, MIN(marks) AS lowest
            FROM students GROUP BY department ORDER BY avg_marks DESC
        """)
        dept = cursor.fetchall()
        print_table(["Department", "Total", "Avg", "Highest", "Lowest"],
                    [[r['department'], r['total'], r['avg_marks'], r['highest'], r['lowest']] for r in dept])

    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def view_analytics():
    dashboard()

def marks_distribution():
    print_line()
    print("  MARKS DISTRIBUTION REPORT")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                SUM(CASE WHEN marks >= 90                THEN 1 ELSE 0 END) AS A,
                SUM(CASE WHEN marks >= 75 AND marks < 90 THEN 1 ELSE 0 END) AS B,
                SUM(CASE WHEN marks >= 60 AND marks < 75 THEN 1 ELSE 0 END) AS C,
                SUM(CASE WHEN marks >= 40 AND marks < 60 THEN 1 ELSE 0 END) AS D,
                SUM(CASE WHEN marks < 40                 THEN 1 ELSE 0 END) AS F
            FROM students
        """)
        g = cursor.fetchone()
        print_table(
            ["Grade", "Range",    "Count"],
            [
                ["A", ">= 90",    g['A']],
                ["B", "75 - 89", g['B']],
                ["C", "60 - 74", g['C']],
                ["D", "40 - 59", g['D']],
                ["F", "< 40",    g['F']],
            ]
        )
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def show_top_performers():
    print_line()
    print("  TOP 3 PERFORMERS")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT name, department, marks
            FROM students ORDER BY marks DESC LIMIT 3
        """)
        rows = cursor.fetchall()
        print_table(["Name", "Department", "Marks"],
                    [[r['name'], r['department'], r['marks']] for r in rows])
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def dept_leaderboard():
    print_line()
    print("  DEPARTMENT LEADERBOARD")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT department, ROUND(AVG(marks),2) AS avg_marks, COUNT(*) AS students
            FROM students GROUP BY department ORDER BY avg_marks DESC
        """)
        rows = cursor.fetchall()
        print_table(["Rank", "Department", "Avg Marks", "Students"],
                    [[i+1, r['department'], r['avg_marks'], r['students']] for i, r in enumerate(rows)])
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def add_bonus_marks():
    print_line()
    print("  ADD BONUS MARKS")
    print_line()
    department = input("  Department : ").strip()
    try:
        bonus = float(input("  Bonus marks to add: ").strip())
    except ValueError:
        print("  [ERR] Invalid bonus value.")
        return
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE students SET marks = LEAST(marks + %s, 100)
            WHERE LOWER(department) = LOWER(%s)
        """, (bonus, department))
        conn.commit()
        log_audit('BONUS_MARKS', f"Added {bonus} bonus to {department}")
        print(f"\n  [OK] Bonus marks added to '{department}' (capped at 100).\n")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def export_high_performers():
    print_line()
    print("  EXPORT HIGH PERFORMERS TO CSV")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT name, department, marks FROM students
            WHERE marks > (SELECT AVG(marks) FROM students)
            ORDER BY marks DESC
        """)
        rows = cursor.fetchall()
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename  = f"high_performers_{timestamp}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'department', 'marks'])
            writer.writeheader()
            writer.writerows(rows)
        log_audit('EXPORT_CSV', f"Exported {len(rows)} students to {filename}")
        print(f"\n  [OK] Exported {len(rows)} students to '{filename}'\n")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

# ==========================================
#  USER MANAGEMENT  (Admin only)
# ==========================================

def create_user():
    print_line()
    print("  CREATE NEW USER  [Admin Only]")
    print_line()
    username = input("  Username   : ").strip()
    password = getpass.getpass("  Password   : ")
    role     = input("  Role (admin/faculty/student): ").strip().lower()
    if role not in ('admin', 'faculty', 'student'):
        print("  [ERR] Invalid role.")
        return
    hashed = hash_password(password)
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, hashed, role)
        )
        conn.commit()
        new_id = cursor.lastrowid
        if role == 'student':
            name  = input("  Student Name       : ").strip()
            dept  = input("  Student Department : ").strip()
            try:
                marks = float(input("  Student Marks      : ").strip())
            except ValueError:
                marks = 0
            cursor.execute(
                "INSERT INTO students (name, department, marks, user_id) VALUES (%s,%s,%s,%s)",
                (name, dept, marks, new_id)
            )
            conn.commit()
        log_audit('CREATE_USER', f"Created user {username} with role {role}")
        print(f"\n  [OK] User '{username}' created successfully!\n")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def list_users():
    print_line()
    print("  ALL USERS  [Admin Only]")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, role, is_active, created_at FROM users ORDER BY id"
        )
        rows = cursor.fetchall()
        print_table(
            ["ID", "Username", "Role", "Active", "Created At"],
            [[r['id'], r['username'], r['role'], r['is_active'], r['created_at']] for r in rows]
        )
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def toggle_user():
    print_line()
    print("  TOGGLE USER ACTIVE STATUS  [Admin Only]")
    print_line()
    try:
        uid = int(input("  Enter User ID to toggle: ").strip())
    except ValueError:
        print("  [ERR] Invalid ID.")
        return
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = NOT is_active WHERE id = %s", (uid,)
        )
        conn.commit()
        log_audit('TOGGLE_USER', f"Toggled user ID {uid}")
        print(f"\n  [OK] User ID {uid} status toggled.\n")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def create_mysql_users():
    print_line()
    print("  CREATE MySQL APPLICATION USERS  [Admin Only]")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        statements = [
            # spa_admin -- full privileges
            "CREATE USER IF NOT EXISTS 'spa_admin'@'localhost' IDENTIFIED BY 'admin_pass'",
            "GRANT ALL PRIVILEGES ON spa_db.* TO 'spa_admin'@'localhost'",
            # spa_faculty -- read + write students, no user mgmt
            "CREATE USER IF NOT EXISTS 'spa_faculty'@'localhost' IDENTIFIED BY 'faculty_pass'",
            "GRANT SELECT, INSERT, UPDATE ON spa_db.students TO 'spa_faculty'@'localhost'",
            "GRANT SELECT ON spa_db.users TO 'spa_faculty'@'localhost'",
            "GRANT INSERT ON spa_db.audit_log TO 'spa_faculty'@'localhost'",
            # spa_student -- read only own record
            "CREATE USER IF NOT EXISTS 'spa_student'@'localhost' IDENTIFIED BY 'student_pass'",
            "GRANT SELECT ON spa_db.students TO 'spa_student'@'localhost'",
            "GRANT SELECT ON spa_db.users TO 'spa_student'@'localhost'",
            "FLUSH PRIVILEGES",
        ]
        for stmt in statements:
            cursor.execute(stmt)
            print(f"  [OK] {stmt[:60]}...")
        conn.commit()
        log_audit('CREATE_MYSQL_USERS', "Created MySQL application users")
        print("\n  [OK] MySQL application users created successfully!\n")
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

def view_audit_log():
    print_line()
    print("  AUDIT LOG -- Last 20 Entries  [Admin Only]")
    print_line()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, user_id, action, details, timestamp FROM audit_log ORDER BY timestamp DESC LIMIT 20"
        )
        rows = cursor.fetchall()
        if not rows:
            print("  No audit entries found.")
            return
        print_table(
            ["ID", "User ID", "Action", "Details", "Timestamp"],
            [[r['id'], r['user_id'], r['action'], r['details'], r['timestamp']] for r in rows]
        )
    except Exception as e:
        print(f"\n  [ERR] Error: {e}\n")
    finally:
        cursor.close()
        conn.close()

# ==========================================
#  MENUS
# ==========================================

def menu_admin():
    options = {
        '1':  ("Dashboard (Live Stats)",           dashboard),
        '2':  ("View All Students",                 view_students),
        '3':  ("Add Student",                       add_student),
        '4':  ("Update Student",                    update_student),
        '5':  ("Delete Student",                    delete_student),
        '6':  ("Search by Department",              search_by_dept),
        '7':  ("Analytics",                         view_analytics),
        '8':  ("Marks Distribution",                marks_distribution),
        '9':  ("Top 3 Performers",                  show_top_performers),
        '10': ("Department Leaderboard",            dept_leaderboard),
        '11': ("Add Bonus Marks",                   add_bonus_marks),
        '12': ("Export High Performers to CSV",     export_high_performers),
        '13': ("Create User Account",               create_user),
        '14': ("List All Users",                    list_users),
        '15': ("Toggle User Active Status",         toggle_user),
        '16': ("Create MySQL Application Users",    create_mysql_users),
        '17': ("View Audit Log",                    view_audit_log),
        '0':  ("Logout",                            None),
    }
    _run_menu("ADMIN MENU", options)

def menu_faculty():
    options = {
        '1':  ("Dashboard (Live Stats)",            dashboard),
        '2':  ("View All Students",                 view_students),
        '3':  ("Add Student",                       add_student),
        '4':  ("Update Student",                    update_student),
        '5':  ("Search by Department",              search_by_dept),
        '6':  ("Analytics",                         view_analytics),
        '7':  ("Marks Distribution",                marks_distribution),
        '8':  ("Top 3 Performers",                  show_top_performers),
        '9':  ("Department Leaderboard",            dept_leaderboard),
        '10': ("Add Bonus Marks",                   add_bonus_marks),
        '11': ("Export High Performers to CSV",     export_high_performers),
        '0':  ("Logout",                            None),
    }
    _run_menu("FACULTY MENU", options)

def menu_student():
    options = {
        '1':  ("My Record",                         view_own_record),
        '2':  ("Top 3 Performers",                  show_top_performers),
        '3':  ("Department Leaderboard",            dept_leaderboard),
        '0':  ("Logout",                            None),
    }
    _run_menu("STUDENT MENU", options)

def _run_menu(title, options):
    while True:
        print_line("=")
        print(f"  {title}  --  Logged in as: {current_user['username']}")
        print_line("=")
        for key, (label, _) in options.items():
            print(f"  [{key}] {label}")
        print_line()
        choice = input("  Choose an option: ").strip()
        if choice == '0':
            log_audit('LOGOUT', f"{current_user['username']} logged out")
            print(f"\n  Goodbye, {current_user['username']}!\n")
            break
        elif choice in options:
            options[choice][1]()
        else:
            print("  [ERR] Invalid option. Try again.\n")

# ==========================================
#  MAIN
# ==========================================

def main():
    if not login():
        return
    role = current_user['role']
    if   role == 'admin':   menu_admin()
    elif role == 'faculty': menu_faculty()
    elif role == 'student': menu_student()
    else:
        print("  [ERR] Unknown role. Contact administrator.")

if __name__ == '__main__':
    main()
