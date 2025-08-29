-- VeriPay Bot - Supabase Database Setup
-- Run this SQL in your Supabase SQL Editor

-- Create tables for VeriPay
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'waiter',
    restaurant_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address TEXT,
    owner_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tables (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id),
    table_number VARCHAR(20) NOT NULL,
    capacity INTEGER DEFAULT 4,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS table_assignments (
    id SERIAL PRIMARY KEY,
    table_id INTEGER REFERENCES tables(id),
    waiter_id VARCHAR(50),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    waiter_id VARCHAR(50),
    restaurant_id INTEGER REFERENCES restaurants(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ETB',
    transaction_id VARCHAR(100),
    bank_name VARCHAR(50),
    verification_status VARCHAR(20) DEFAULT 'pending',
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bank_statements (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id),
    statement_date DATE,
    total_amount DECIMAL(10,2),
    transaction_count INTEGER,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reconciliation_reports (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id),
    report_date DATE,
    total_transactions INTEGER,
    verified_transactions INTEGER,
    pending_transactions INTEGER,
    total_amount DECIMAL(10,2),
    report_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(10),
    message TEXT,
    user_id VARCHAR(50),
    action VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_transactions_waiter_id ON transactions(waiter_id);
CREATE INDEX IF NOT EXISTS idx_transactions_restaurant_id ON transactions(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(verification_status);

-- Enable Row Level Security (RLS) for better security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE restaurants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE table_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

-- Create policies for public access (for demo purposes)
-- In production, you should create more restrictive policies
CREATE POLICY "Allow all operations for demo" ON users FOR ALL USING (true);
CREATE POLICY "Allow all operations for demo" ON restaurants FOR ALL USING (true);
CREATE POLICY "Allow all operations for demo" ON tables FOR ALL USING (true);
CREATE POLICY "Allow all operations for demo" ON table_assignments FOR ALL USING (true);
CREATE POLICY "Allow all operations for demo" ON transactions FOR ALL USING (true);
CREATE POLICY "Allow all operations for demo" ON bank_statements FOR ALL USING (true);
CREATE POLICY "Allow all operations for demo" ON reconciliation_reports FOR ALL USING (true);
CREATE POLICY "Allow all operations for demo" ON system_logs FOR ALL USING (true);

-- Insert demo data
INSERT INTO restaurants (name, address, owner_id, created_at) 
VALUES ('Demo Restaurant', 'Addis Ababa, Ethiopia', '123456789', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Get the restaurant ID for demo data
DO $$
DECLARE
    restaurant_id INTEGER;
BEGIN
    SELECT id INTO restaurant_id FROM restaurants WHERE name = 'Demo Restaurant' LIMIT 1;
    
    -- Insert demo users
    INSERT INTO users (telegram_id, name, phone, role, restaurant_id, created_at)
    VALUES 
        ('123456789', 'Demo Admin', '+251911234567', 'admin', restaurant_id, CURRENT_TIMESTAMP),
        ('369249230', 'Demo Waiter', '+251922345678', 'waiter', restaurant_id, CURRENT_TIMESTAMP)
    ON CONFLICT (telegram_id) DO NOTHING;
    
    -- Insert demo tables
    INSERT INTO tables (restaurant_id, table_number, capacity, is_active, created_at)
    SELECT restaurant_id, 'T' || i, 4, true, CURRENT_TIMESTAMP
    FROM generate_series(1, 5) i
    ON CONFLICT DO NOTHING;
    
    -- Insert demo transactions
    INSERT INTO transactions (waiter_id, restaurant_id, amount, currency, transaction_id, bank_name, verification_status, created_at)
    VALUES 
        ('369249230', restaurant_id, 150.00, 'ETB', 'TXN001', 'CBE', 'verified', CURRENT_TIMESTAMP),
        ('369249230', restaurant_id, 250.00, 'ETB', 'TXN002', 'Dashen', 'pending', CURRENT_TIMESTAMP),
        ('369249230', restaurant_id, 300.00, 'ETB', 'TXN003', 'Telebirr', 'verified', CURRENT_TIMESTAMP)
    ON CONFLICT DO NOTHING;
    
    -- Insert demo system logs
    INSERT INTO system_logs (level, message, user_id, action, created_at)
    VALUES 
        ('INFO', 'System initialized', '123456789', 'system_start', CURRENT_TIMESTAMP),
        ('INFO', 'Demo data created', '123456789', 'demo_setup', CURRENT_TIMESTAMP),
        ('INFO', 'Database setup completed', '123456789', 'db_setup', CURRENT_TIMESTAMP)
    ON CONFLICT DO NOTHING;
END $$;

-- Show summary
SELECT 
    'Tables created successfully!' as status,
    (SELECT COUNT(*) FROM users) as users_count,
    (SELECT COUNT(*) FROM restaurants) as restaurants_count,
    (SELECT COUNT(*) FROM transactions) as transactions_count; 