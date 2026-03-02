-- ============================================================
-- INTELLIGENT BANKING PLATFORM - POSTGRESQL PRODUCTION SCHEMA
-- Phase 1 Upgrade: Transaction Lifecycle + Model Registry
-- ============================================================

-- =============================
-- ENUM TYPES
-- =============================

CREATE TYPE customer_status AS ENUM ('ACTIVE','INACTIVE','KYC_PENDING');
CREATE TYPE user_role AS ENUM ('ADMIN','TELLER','AUDITOR','OPS');
CREATE TYPE account_status AS ENUM ('ACTIVE','FROZEN','CLOSED');
CREATE TYPE account_type_enum AS ENUM ('SAVINGS','CURRENT','LOAN','FIXED_DEPOSIT');
CREATE TYPE txn_type_enum AS ENUM ('DEPOSIT','WITHDRAWAL','TRANSFER_OUT','TRANSFER_IN','FEE','INTEREST');
CREATE TYPE txn_status_enum AS ENUM ('PENDING','APPROVED','REJECTED_FRAUD');
CREATE TYPE alert_severity AS ENUM ('LOW','MEDIUM','HIGH');
CREATE TYPE alert_status AS ENUM ('OPEN','INVESTIGATING','RESOLVED','FALSE_POSITIVE');

-- =============================
-- CORE TABLES
-- =============================

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    date_of_birth DATE,
    email VARCHAR(150) UNIQUE,
    phone VARCHAR(20),
    pan_number VARCHAR(20) UNIQUE,
    address VARCHAR(255),
    city VARCHAR(80),
    state VARCHAR(80),
    country VARCHAR(80) DEFAULT 'India',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status customer_status DEFAULT 'ACTIVE'
);

CREATE TABLE branches (
    branch_id SERIAL PRIMARY KEY,
    branch_name VARCHAR(120) NOT NULL,
    ifsc_code VARCHAR(20) UNIQUE NOT NULL,
    address VARCHAR(255),
    city VARCHAR(80),
    state VARCHAR(80),
    contact_phone VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150),
    email VARCHAR(150) UNIQUE,
    role user_role DEFAULT 'TELLER',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounts (
    account_id BIGSERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    branch_id INT REFERENCES branches(branch_id),
    account_number VARCHAR(34) UNIQUE NOT NULL,
    account_type account_type_enum NOT NULL,
    status account_status DEFAULT 'ACTIVE',
    balance NUMERIC(18,2) DEFAULT 0.00,
    currency CHAR(3) DEFAULT 'INR',
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_transaction_date TIMESTAMP
);

-- =============================
-- TRANSACTIONS (UPGRADED)
-- =============================

CREATE TABLE transactions (
    txn_id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(account_id) ON DELETE CASCADE,
    txn_type txn_type_enum NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    related_account_id BIGINT REFERENCES accounts(account_id),
    balance_after_txn NUMERIC(18,2) NOT NULL,
    description VARCHAR(255),

    -- NEW FIELDS (Phase 1)
    status txn_status_enum NOT NULL DEFAULT 'PENDING',
    fraud_score NUMERIC,
    model_version TEXT,
    idempotency_key UUID UNIQUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    device_info VARCHAR(255)
);

CREATE TABLE fraud_alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    txn_id BIGINT REFERENCES transactions(txn_id) ON DELETE CASCADE,
    account_id BIGINT REFERENCES accounts(account_id),
    alert_type VARCHAR(100),
    severity alert_severity DEFAULT 'MEDIUM',
    status alert_status DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    action VARCHAR(120),
    table_name VARCHAR(80),
    record_id BIGINT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================
-- MODEL REGISTRY (NEW)
-- =============================

CREATE TABLE model_registry (
    model_version TEXT PRIMARY KEY,
    threshold NUMERIC NOT NULL,
    roc_auc NUMERIC,
    pr_auc NUMERIC,
    training_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK (status IN ('ACTIVE','INACTIVE'))
);

-- =============================
-- SYSTEM CONFIG
-- =============================

CREATE TABLE system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value TEXT
);

-- =============================
-- TRANSACTION FUNCTIONS (UPDATED)
-- =============================

-- Deposit
CREATE OR REPLACE FUNCTION fn_deposit(
    p_account_id BIGINT,
    p_amount NUMERIC,
    p_description TEXT,
    p_idempotency_key UUID
)
RETURNS BIGINT AS $$
DECLARE
    v_balance NUMERIC;
    v_txn_id BIGINT;
BEGIN
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'Deposit must be positive';
    END IF;

    -- Idempotency check
    SELECT txn_id INTO v_txn_id
    FROM transactions
    WHERE idempotency_key = p_idempotency_key;

    IF FOUND THEN
        RETURN v_txn_id;
    END IF;

    SELECT balance INTO v_balance
    FROM accounts
    WHERE account_id = p_account_id
    FOR UPDATE;

    v_balance := v_balance + p_amount;

    UPDATE accounts
    SET balance = v_balance,
        last_transaction_date = NOW()
    WHERE account_id = p_account_id;

    INSERT INTO transactions(
        account_id, txn_type, amount, balance_after_txn,
        description, status, idempotency_key
    )
    VALUES (
        p_account_id, 'DEPOSIT', p_amount, v_balance,
        p_description, 'PENDING', p_idempotency_key
    )
    RETURNING txn_id INTO v_txn_id;

    RETURN v_txn_id;
END;
$$ LANGUAGE plpgsql;

-- Withdraw
CREATE OR REPLACE FUNCTION fn_withdraw(
    p_account_id BIGINT,
    p_amount NUMERIC,
    p_description TEXT,
    p_idempotency_key UUID
)
RETURNS BIGINT AS $$
DECLARE
    v_balance NUMERIC;
    v_txn_id BIGINT;
BEGIN
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'Invalid withdrawal amount';
    END IF;

    SELECT txn_id INTO v_txn_id
    FROM transactions
    WHERE idempotency_key = p_idempotency_key;

    IF FOUND THEN
        RETURN v_txn_id;
    END IF;

    SELECT balance INTO v_balance
    FROM accounts
    WHERE account_id = p_account_id
    FOR UPDATE;

    IF v_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds';
    END IF;

    v_balance := v_balance - p_amount;

    UPDATE accounts
    SET balance = v_balance,
        last_transaction_date = NOW()
    WHERE account_id = p_account_id;

    INSERT INTO transactions(
        account_id, txn_type, amount, balance_after_txn,
        description, status, idempotency_key
    )
    VALUES (
        p_account_id, 'WITHDRAWAL', p_amount, v_balance,
        p_description, 'PENDING', p_idempotency_key
    )
    RETURNING txn_id INTO v_txn_id;

    RETURN v_txn_id;
END;
$$ LANGUAGE plpgsql;

-- Transfer (DEADLOCK SAFE)
CREATE OR REPLACE FUNCTION fn_transfer(
    p_from BIGINT,
    p_to BIGINT,
    p_amount NUMERIC,
    p_description TEXT,
    p_idempotency_key UUID
)
RETURNS BIGINT AS $$
DECLARE
    v_from_balance NUMERIC;
    v_to_balance NUMERIC;
    v_txn_id BIGINT;
BEGIN
    IF p_from = p_to THEN
        RAISE EXCEPTION 'Cannot transfer to same account';
    END IF;

    -- Idempotency check
    SELECT txn_id INTO v_txn_id
    FROM transactions
    WHERE idempotency_key = p_idempotency_key;

    IF FOUND THEN
        RETURN v_txn_id;
    END IF;

    -- DEADLOCK SAFE LOCKING
    IF p_from < p_to THEN
        SELECT balance INTO v_from_balance
        FROM accounts WHERE account_id = p_from FOR UPDATE;

        SELECT balance INTO v_to_balance
        FROM accounts WHERE account_id = p_to FOR UPDATE;
    ELSE
        SELECT balance INTO v_to_balance
        FROM accounts WHERE account_id = p_to FOR UPDATE;

        SELECT balance INTO v_from_balance
        FROM accounts WHERE account_id = p_from FOR UPDATE;
    END IF;

    IF v_from_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds';
    END IF;

    v_from_balance := v_from_balance - p_amount;
    v_to_balance := v_to_balance + p_amount;

    UPDATE accounts SET balance = v_from_balance WHERE account_id = p_from;
    UPDATE accounts SET balance = v_to_balance WHERE account_id = p_to;

    INSERT INTO transactions(
        account_id, txn_type, amount, related_account_id,
        balance_after_txn, description,
        status, idempotency_key
    )
    VALUES (
        p_from, 'TRANSFER_OUT', p_amount, p_to,
        v_from_balance, p_description,
        'PENDING', p_idempotency_key
    )
    RETURNING txn_id INTO v_txn_id;

    INSERT INTO transactions(
        account_id, txn_type, amount, related_account_id,
        balance_after_txn, description,
        status, idempotency_key
    )
    VALUES (
        p_to, 'TRANSFER_IN', p_amount, p_from,
        v_to_balance, p_description,
        'PENDING', p_idempotency_key
    );

    RETURN v_txn_id;
END;
$$ LANGUAGE plpgsql;

-- =============================
-- INDEXES
-- =============================

CREATE INDEX idx_transactions_account_time
ON transactions(account_id, created_at);

CREATE INDEX idx_transactions_amount
ON transactions(amount);

CREATE INDEX idx_transactions_status
ON transactions(status);

CREATE INDEX idx_fraud_status
ON fraud_alerts(status);

-- ============================================================
-- END OF PHASE 1 UPGRADED SCHEMA
-- ============================================================