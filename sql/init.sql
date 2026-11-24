-- Student table
CREATE TABLE IF NOT EXISTS student (
    id_s INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    major VARCHAR(100) NOT NULL,
    double_major BOOLEAN NOT NULL,
    level INT NOT NULL,
    second_major VARCHAR(100)
);

-- Report table
CREATE TABLE IF NOT EXISTS report (
    id_r INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    type VARCHAR(100) NOT NULL,
    k1 VARCHAR(100) NOT NULL,
    k2 VARCHAR(100) NOT NULL,
    k3 VARCHAR(100) NOT NULL,
    release_date DATE NOT NULL,
    major VARCHAR(100) NOT NULL,
    student_id INT NOT NULL,

    FOREIGN KEY (student_id)
        REFERENCES student(id_s)
        ON DELETE CASCADE,

    UNIQUE (student_id, major)
);

-- Request history table
CREATE TABLE IF NOT EXISTS request_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    method VARCHAR(10) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    status_code INT NOT NULL,
    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
