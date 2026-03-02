-- ===============================================
-- STRUCTURAL SEED DATA
-- Intelligent Banking Platform
-- Minimal Bootstrapping Data Only
-- ===============================================

-- =========================
-- Insert Branches
-- =========================

INSERT INTO branches (branch_name, ifsc_code, city, state, contact_phone)
VALUES
('Delhi Main Branch', 'IFSC0001', 'Delhi', 'Delhi', '+91-11-0000001'),
('Mumbai Central', 'IFSC0002', 'Mumbai', 'Maharashtra', '+91-22-0000002'),
('Bangalore Tech Park', 'IFSC0003', 'Bangalore', 'Karnataka', '+91-80-0000003')
ON CONFLICT (ifsc_code) DO NOTHING;

-- =========================
-- Insert Admin User
-- =========================
-- Password: admin123 (hash should be generated properly later in backend)
-- For now placeholder hash

INSERT INTO users (username, password_hash, full_name, email, role)
VALUES (
    'admin',
    'admin_placeholder_hash',
    'System Administrator',
    'admin@bank.com',
    'ADMIN'
)
ON CONFLICT (username) DO NOTHING;

-- =========================
-- Insert System Config Values
-- =========================

INSERT INTO system_config (config_key, config_value)
VALUES
('DAILY_WITHDRAWAL_LIMIT', '50000'),
('LARGE_TXN_THRESHOLD', '100000'),
('TRANSFER_FEE', '10'),
('FRAUD_MODEL_THRESHOLD', '0.85')
ON CONFLICT (config_key) DO NOTHING;

-- ===============================================
-- END OF STRUCTURAL SEED
-- ===============================================