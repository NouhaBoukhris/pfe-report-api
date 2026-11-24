import os
import hmac

from datetime import date
from flask import Flask, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from dotenv import load_dotenv
from db import get_db_connection
from models import ALLOWED_MAJORS

load_dotenv()

app = Flask(__name__)
for name in ("JWT_SECRET_KEY", "ADMIN_USERNAME", "ADMIN_PASSWORD"):
    if not os.getenv(name):
        raise RuntimeError(f"Missing required setting: {name}")
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
jwt = JWTManager(app)


# Save API requests in MySQL
@app.after_request
def log_request(response):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO request_history
            (method, endpoint, status_code)
            VALUES (%s, %s, %s)
            """,
            (request.method, request.path, response.status_code)
        )

        connection.commit()

    except Exception as error:
        app.logger.error("Request logging failed: %s", error)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    return response

# ==========================================
# AUTHENTICATION
# ==========================================

@app.post("/auth/login")
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"message": "Valid JSON body is required"}, 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return {"message": "Invalid username or password"}, 401

    if (
        not hmac.compare_digest(username, os.getenv("ADMIN_USERNAME", ""))
        or not hmac.compare_digest(password, os.getenv("ADMIN_PASSWORD", ""))
    ):
        return {"message": "Invalid username or password"}, 401

    return {
        "access_token": create_access_token(identity="admin"),
        "refresh_token": create_refresh_token(identity="admin")
    }, 200


@app.post("/auth/refresh")
@jwt_required(refresh=True)
def refresh_token():
    identity = get_jwt_identity()
    return {"access_token": create_access_token(identity=identity)}, 200


# ==========================================
# STUDENT
# ==========================================

# Get all students
@app.get("/students")
@jwt_required()
def get_students():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM student")
        students = cursor.fetchall()
        return {"students": students}, 200
    finally:
        cursor.close()
        connection.close()


# Get student by ID
@app.get("/students/<int:student_id>")
@jwt_required()
def get_student(student_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM student WHERE id_s = %s",
            (student_id,)
        )
        student = cursor.fetchone()

        if student is None:
            return {"message": "Student not found"}, 404

        return student, 200
    finally:
        cursor.close()
        connection.close()


# Create a new student
@app.post("/students")
@jwt_required()
def add_student():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"message": "Valid JSON body is required"}, 400

    required = ["first_name", "last_name", "major", "double_major", "level"]

    if any(field not in data for field in required):
        return {"message": "Missing required student fields"}, 400

    if (
        not isinstance(data["first_name"], str)
        or not data["first_name"].strip()
        or not isinstance(data["last_name"], str)
        or not data["last_name"].strip()
    ):
        return {"message": "Invalid student name"}, 400

    if data["major"] not in ALLOWED_MAJORS:
        return {"message": "Invalid major"}, 400

    if type(data["level"]) is not int or not 1 <= data["level"] <= 4:
        return {"message": "Level must be between 1 and 4"}, 400

    if type(data["double_major"]) is not bool:
        return {"message": "double_major must be true or false"}, 400

    second_major = data.get("second_major")

    if data["double_major"]:
        if second_major not in ALLOWED_MAJORS or second_major == data["major"]:
            return {"message": "Invalid second major"}, 400
    elif second_major is not None:
        return {"message": "Second major is only allowed for double majors"}, 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        query = """
            INSERT INTO student
            (first_name, last_name, major, double_major, level, second_major)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            data["first_name"].strip(),
            data["last_name"].strip(),
            data["major"],
            data["double_major"],
            data["level"],
            second_major
        )

        # Check if the student already exists
        cursor.execute(
            """
            SELECT id_s FROM student
            WHERE LOWER(first_name) = LOWER(%s)
            AND LOWER(last_name) = LOWER(%s)
            """,
            (data["first_name"].strip(), data["last_name"].strip())
        )

        existing_student = cursor.fetchone()

        if existing_student:
            return {"message": "Student already exists"}, 409

        cursor.execute(query, values)
        connection.commit()

        return {"message": "Student created", "id_s": cursor.lastrowid}, 201
    finally:
        cursor.close()
        connection.close()


# Update a student
@app.put("/students/<int:student_id>")
@jwt_required()
def update_student(student_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return {"message": "Request body is required"}, 400

    allowed_fields = {
        "first_name", "last_name", "major",
        "double_major", "level", "second_major"
    }

    if set(data) - allowed_fields:
        return {"message": "Invalid student fields"}, 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Check if student exists
        cursor.execute(
            "SELECT * FROM student WHERE id_s = %s FOR UPDATE",
            (student_id,)
        )
        student = cursor.fetchone()

        if student is None:
            return {"message": "Student not found"}, 404

        # Keep existing values if not provided
        first_name = data.get("first_name", student["first_name"])
        last_name = data.get("last_name", student["last_name"])
        major = data.get("major", student["major"])
        level = data.get("level", student["level"])
        double_major = data.get(
            "double_major", bool(student["double_major"])
        )
        second_major = data.get("second_major", student["second_major"])

        # Validate student information
        if (
            not isinstance(first_name, str) or not first_name.strip()
            or not isinstance(last_name, str) or not last_name.strip()
        ):
            return {"message": "Invalid student name"}, 400

        if major not in ALLOWED_MAJORS:
            return {"message": "Invalid major"}, 400

        if type(level) is not int or not 1 <= level <= 4:
            return {"message": "Level must be between 1 and 4"}, 400

        if type(double_major) is not bool:
            return {"message": "double_major must be true or false"}, 400

        if double_major:
            if second_major not in ALLOWED_MAJORS or second_major == major:
                return {"message": "Invalid second major"}, 400
        else:
            second_major = None

        # Prevent duplicate student names
        cursor.execute(
            """
            SELECT id_s FROM student
            WHERE LOWER(first_name) = LOWER(%s)
              AND LOWER(last_name) = LOWER(%s)
              AND id_s != %s
            """,
            (first_name.strip(), last_name.strip(), student_id)
        )

        if cursor.fetchone():
            return {"message": "Student already exists"}, 409

        # Check existing reports before changing majors
        cursor.execute(
            "SELECT major FROM report WHERE student_id = %s",
            (student_id,)
        )
        reports = cursor.fetchall()

        valid_majors = [major]
        if double_major:
            valid_majors.append(second_major)

        for report in reports:
            if report["major"] not in valid_majors:
                return {
                    "message": "Cannot change major: existing report conflict"
                }, 409

        # Update student in MySQL
        cursor.execute(
            """
            UPDATE student
            SET first_name = %s,
                last_name = %s,
                major = %s,
                double_major = %s,
                level = %s,
                second_major = %s
            WHERE id_s = %s
            """,
            (
                first_name.strip(),
                last_name.strip(),
                major,
                double_major,
                level,
                second_major,
                student_id
            )
        )

        connection.commit()
        return {"message": "Student updated successfully"}, 200

    finally:
        cursor.close()
        connection.close()


# Delete a student
@app.delete("/students/<int:student_id>")
@jwt_required()
def delete_student(student_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM student WHERE id_s = %s",
            (student_id,)
        )

        if cursor.rowcount == 0:
            return {"message": "Student not found"}, 404

        connection.commit()
        return {"message": "Student deleted successfully"}, 200
    finally:
        cursor.close()
        connection.close()

# ==========================================
# REPORT
# ==========================================

# Get all reports
@app.get("/reports")
def get_reports():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM report")
        reports = cursor.fetchall()
        return {"reports": reports}, 200
    finally:
        cursor.close()
        connection.close()


# Get report by ID
@app.get("/reports/<int:report_id>")
def get_report(report_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM report WHERE id_r = %s",
            (report_id,)
        )
        report = cursor.fetchone()

        if report is None:
            return {"message": "Report not found"}, 404

        return report, 200
    finally:
        cursor.close()
        connection.close()


# Search reports by keyword, major, or type
@app.get("/reports/search")
def search_reports():
    keyword = request.args.get("keyword")
    major = request.args.get("major")
    report_type = request.args.get("type")

    if major and major not in ALLOWED_MAJORS:
        return {"message": "Invalid major"}, 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = "SELECT * FROM report WHERE 1=1"
        values = []

        if keyword:
            query += """
                AND (
                    title LIKE %s OR
                    k1 LIKE %s OR
                    k2 LIKE %s OR
                    k3 LIKE %s
                )
            """
            values.extend([f"%{keyword}%"] * 4)

        if major:
            query += " AND major = %s"
            values.append(major)

        if report_type:
            query += " AND type = %s"
            values.append(report_type)

        cursor.execute(query, tuple(values))
        reports = cursor.fetchall()

        return {"reports": reports}, 200

    finally:
        cursor.close()
        connection.close()


# Create a new report
@app.post("/reports")
@jwt_required()
def add_report():
    data = request.get_json(silent=True)

    required = [
        "title", "type", "k1", "k2", "k3",
        "release_date", "major", "student_id"
    ]

    if not isinstance(data, dict) or any(f not in data for f in required):
        return {"message": "Missing or invalid report data"}, 400

    if any(
        not isinstance(data[f], str) or not data[f].strip()
        for f in ["title", "type", "k1", "k2", "k3"]
    ):
        return {"message": "Invalid report information"}, 400

    if data["major"] not in ALLOWED_MAJORS:
        return {"message": "Invalid major"}, 400

    if type(data["student_id"]) is not int or data["student_id"] <= 0:
        return {"message": "Invalid student ID"}, 400

    try:
        release_date = date.fromisoformat(data["release_date"])
    except (ValueError, TypeError):
        return {"message": "Invalid release date. Use YYYY-MM-DD"}, 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Check if the student exists
        cursor.execute(
            "SELECT * FROM student WHERE id_s = %s",
            (data["student_id"],)
        )
        student = cursor.fetchone()

        if student is None:
            return {"message": "Student not found"}, 404

        # Check if the report major belongs to the student
        valid_majors = [student["major"]]

        if student["double_major"]:
            valid_majors.append(student["second_major"])

        if data["major"] not in valid_majors:
            return {"message": "Major does not match student"}, 400

        # Check if the student already has a report for this major
        cursor.execute(
            """
            SELECT id_r FROM report
            WHERE student_id = %s AND major = %s
            """,
            (data["student_id"], data["major"])
        )

        if cursor.fetchone():
            return {"message": "Report already exists for this major"}, 409

        # Check the maximum number of reports
        cursor.execute(
            "SELECT COUNT(*) AS total FROM report WHERE student_id = %s",
            (data["student_id"],)
        )
        report_count = cursor.fetchone()["total"]

        limit = 2 if student["double_major"] else 1

        if report_count >= limit:
            return {"message": "Student has reached the report limit"}, 409

        # Insert the report into MySQL
        cursor.execute(
            """
            INSERT INTO report
            (title, type, k1, k2, k3, release_date, major, student_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["title"].strip(),
                data["type"].strip(),
                data["k1"].strip(),
                data["k2"].strip(),
                data["k3"].strip(),
                release_date,
                data["major"],
                data["student_id"]
            )
        )

        connection.commit()

        return {
            "message": "Report created",
            "id_r": cursor.lastrowid
        }, 201

    finally:
        cursor.close()
        connection.close()


# Update a report
@app.put("/reports/<int:report_id>")
@jwt_required()
def update_report(report_id):
    data = request.get_json(silent=True)

    required = ["title", "type", "k1", "k2", "k3", "release_date"]

    if not isinstance(data, dict) or any(f not in data for f in required):
        return {"message": "Missing or invalid report data"}, 400

    if set(data) != set(required):
        return {"message": "Only report details can be updated"}, 400

    if any(
        not isinstance(data[f], str) or not data[f].strip()
        for f in ["title", "type", "k1", "k2", "k3"]
    ):
        return {"message": "Invalid report information"}, 400

    try:
        release_date = date.fromisoformat(data["release_date"])
    except (ValueError, TypeError):
        return {"message": "Invalid release date. Use YYYY-MM-DD"}, 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Check if the report exists
        cursor.execute(
            "SELECT id_r FROM report WHERE id_r = %s",
            (report_id,)
        )

        if cursor.fetchone() is None:
            return {"message": "Report not found"}, 404

        # Update the report in MySQL
        cursor.execute(
            """
            UPDATE report
            SET title = %s, type = %s, k1 = %s,
                k2 = %s, k3 = %s, release_date = %s
            WHERE id_r = %s
            """,
            (
                data["title"].strip(),
                data["type"].strip(),
                data["k1"].strip(),
                data["k2"].strip(),
                data["k3"].strip(),
                release_date,
                report_id
            )
        )

        connection.commit()
        return {"message": "Report updated successfully"}, 200

    finally:
        cursor.close()
        connection.close()


# Delete a report
@app.delete("/reports/<int:report_id>")
@jwt_required()
def delete_report(report_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM report WHERE id_r = %s",
            (report_id,)
        )

        if cursor.rowcount == 0:
            return {"message": "Report not found"}, 404

        connection.commit()
        return {"message": "Report deleted successfully"}, 200

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
