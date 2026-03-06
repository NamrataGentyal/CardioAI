-- ============================================================
-- CardioAI  –  MySQL Database Setup
-- Run this entire script in MySQL Workbench once.
-- ============================================================

-- 1. Create the database
CREATE DATABASE IF NOT EXISTS cardioai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 2. Switch to it
USE cardioai;

-- 3. Create the users table
CREATE TABLE IF NOT EXISTS users (
    id            INT          NOT NULL AUTO_INCREMENT,
    name          VARCHAR(100) NOT NULL,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_username (username),
    INDEX idx_email    (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Verify
SELECT 'Database and table created successfully!' AS status;
DESCRIBE users;
