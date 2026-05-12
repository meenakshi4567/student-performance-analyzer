-- ══════════════════════════════════════════════════════════════
--  PRN_setup.sql  —  Student Performance Analyzer Database Setup
-- ══════════════════════════════════════════════════════════════

-- 1. CREATE & SELECT DATABASE
DROP DATABASE IF EXISTS spa_db;
CREATE DATABASE spa_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;   -- Case-insensitive username matching
USE spa_db;

-- ──────────────────────────────────────────
--  TABLE: users
-- ──────────────────────────────────────────
CREATE TABLE users (
    id            INT           AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)   NOT NULL UNIQUE
                                COLLATE utf8mb4_unicode_ci,  -- case-insensitive
    password_hash VARCHAR(64)   NOT NULL,                    -- SHA-256 hex
    role          ENUM('admin','faculty','student') NOT NULL,
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────
--  TABLE: students
-- ──────────────────────────────────────────
CREATE TABLE students (
    id          INT           AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL,
    department  VARCHAR(50)   NOT NULL,
    marks       DECIMAL(5,2)  NOT NULL CHECK (marks >= 0 AND marks <= 100),
    user_id     INT           DEFAULT NULL,
    enrolled_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ──────────────────────────────────────────
--  TABLE: audit_log
-- ──────────────────────────────────────────
CREATE TABLE audit_log (
    id        INT          AUTO_INCREMENT PRIMARY KEY,
    user_id   INT          DEFAULT NULL,
    action    VARCHAR(50)  NOT NULL,
    details   TEXT,
    timestamp DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ──────────────────────────────────────────
--  VIEWS
-- ──────────────────────────────────────────

-- View: top performers per department
CREATE VIEW vw_dept_leaderboard AS
    SELECT department,
           ROUND(AVG(marks), 2) AS avg_marks,
           MAX(marks)           AS highest,
           MIN(marks)           AS lowest,
           COUNT(*)             AS total_students
    FROM students
    GROUP BY department
    ORDER BY avg_marks DESC;

-- View: grade summary
CREATE VIEW vw_grade_distribution AS
    SELECT
        SUM(CASE WHEN marks >= 90                THEN 1 ELSE 0 END) AS grade_A,
        SUM(CASE WHEN marks >= 75 AND marks < 90 THEN 1 ELSE 0 END) AS grade_B,
        SUM(CASE WHEN marks >= 60 AND marks < 75 THEN 1 ELSE 0 END) AS grade_C,
        SUM(CASE WHEN marks >= 40 AND marks < 60 THEN 1 ELSE 0 END) AS grade_D,
        SUM(CASE WHEN marks < 40                 THEN 1 ELSE 0 END) AS grade_F
    FROM students;

-- ──────────────────────────────────────────
--  SAMPLE DATA
--  Passwords are SHA-256 of the plain text shown in comments
-- ──────────────────────────────────────────

-- admin123   → SHA-256: 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
-- faculty123 → SHA-256: f9d58d7ca5f7c16f4bcaed2db91fb3b51a49e68f1e0c5bccbb5c3d97bde12e8a
-- student123 → SHA-256: ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f

INSERT INTO users (username, password_hash, role) VALUES
('admin',   '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin'),
('faculty1','f9d58d7ca5f7c16f4bcaed2db91fb3b51a49e68f1e0c5bccbb5c3d97bde12e8a', 'faculty'),
('stu_ravi', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'student'),
('stu_priya','ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'student');

INSERT INTO students (name, department, marks, user_id) VALUES
('Ravi Kumar',   'CSE', 88.0, 3),
('Priya Sharma', 'CST', 95.5, 4);

INSERT INTO students (name, department, marks) VALUES
('Arjun Reddy',  'CSE', 72.0),
('Meena Pillai', 'CST', 61.5),
('Suresh Babu',  'ECE', 45.0),
('Lakshmi Devi', 'ECE', 55.0),
('Kiran Rao',    'CSE', 91.0),
('Divya Nair',   'CST', 38.0),
('Anil Teja',    'ECE', 82.5),
('Sneha Varma',  'CSE', 67.0);

-- ──────────────────────────────────────────
--  MySQL APPLICATION USERS & GRANTS
-- ──────────────────────────────────────────

-- spa_admin: full access to the database
CREATE USER IF NOT EXISTS 'spa_admin'@'localhost'   IDENTIFIED BY 'admin_pass';
GRANT ALL PRIVILEGES ON spa_db.* TO 'spa_admin'@'localhost';

-- spa_faculty: can read/write students, read users, write audit
CREATE USER IF NOT EXISTS 'spa_faculty'@'localhost' IDENTIFIED BY 'faculty_pass';
GRANT SELECT, INSERT, UPDATE ON spa_db.students   TO 'spa_faculty'@'localhost';
GRANT SELECT                  ON spa_db.users      TO 'spa_faculty'@'localhost';
GRANT INSERT                  ON spa_db.audit_log  TO 'spa_faculty'@'localhost';

-- spa_student: read-only access
CREATE USER IF NOT EXISTS 'spa_student'@'localhost' IDENTIFIED BY 'student_pass';
GRANT SELECT ON spa_db.students  TO 'spa_student'@'localhost';
GRANT SELECT ON spa_db.users     TO 'spa_student'@'localhost';

FLUSH PRIVILEGES;
