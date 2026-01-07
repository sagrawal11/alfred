-- Supabase Database Schema for SMS Assistant
-- Run this SQL in your Supabase SQL Editor to create all required tables

-- Food logs table
CREATE TABLE IF NOT EXISTS food_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    food_name TEXT NOT NULL,
    calories NUMERIC NOT NULL,
    protein NUMERIC NOT NULL,
    carbs NUMERIC NOT NULL,
    fat NUMERIC NOT NULL,
    restaurant TEXT,
    portion_multiplier NUMERIC DEFAULT 1.0
);

-- Water logs table
CREATE TABLE IF NOT EXISTS water_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    amount_ml NUMERIC NOT NULL,
    amount_oz NUMERIC NOT NULL
);

-- Gym logs table
CREATE TABLE IF NOT EXISTS gym_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    exercise TEXT NOT NULL,
    sets INTEGER,
    reps INTEGER,
    weight NUMERIC,
    notes TEXT
);

-- Reminders and todos table
CREATE TABLE IF NOT EXISTS reminders_todos (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    type TEXT NOT NULL CHECK (type IN ('reminder', 'todo')),
    content TEXT NOT NULL,
    due_date TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    sent_at TIMESTAMP,
    follow_up_sent BOOLEAN DEFAULT FALSE,
    decay_check_sent BOOLEAN DEFAULT FALSE
);

-- Used quotes table (composite primary key)
CREATE TABLE IF NOT EXISTS used_quotes (
    date DATE NOT NULL,
    quote TEXT NOT NULL,
    author TEXT,
    PRIMARY KEY (date, quote)
);

-- Water goals table
CREATE TABLE IF NOT EXISTS water_goals (
    date DATE PRIMARY KEY,
    goal_ml NUMERIC NOT NULL
);

-- Sleep logs table
CREATE TABLE IF NOT EXISTS sleep_logs (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    sleep_time TIME NOT NULL,
    wake_time TIME NOT NULL,
    duration_hours NUMERIC NOT NULL
);

-- Facts (information recall) table
CREATE TABLE IF NOT EXISTS facts (
    id SERIAL PRIMARY KEY,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    context TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_food_logs_timestamp ON food_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_water_logs_timestamp ON water_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_gym_logs_timestamp ON gym_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_reminders_todos_type ON reminders_todos(type);
CREATE INDEX IF NOT EXISTS idx_reminders_todos_completed ON reminders_todos(completed);
CREATE INDEX IF NOT EXISTS idx_reminders_todos_due_date ON reminders_todos(due_date);
CREATE INDEX IF NOT EXISTS idx_sleep_logs_date ON sleep_logs(date);
CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key);
CREATE INDEX IF NOT EXISTS idx_facts_timestamp ON facts(timestamp);

