-- Schema for SmartAPI Database (PostgreSQL compatible)

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS apis (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(255) NOT NULL,
    interval_seconds INT NOT NULL DEFAULT 60,
    threshold_ms INT NOT NULL DEFAULT 1000
);

CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    api_id INT NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status_code INT,
    response_time INT,
    state VARCHAR(20) NOT NULL
);
