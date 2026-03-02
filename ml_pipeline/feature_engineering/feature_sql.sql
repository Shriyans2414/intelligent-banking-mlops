-- Advanced Fraud Feature View

DROP MATERIALIZED VIEW IF EXISTS fraud_features;

CREATE MATERIALIZED VIEW fraud_features AS

WITH base AS (
    SELECT
        t.txn_id,
        t.account_id,
        t.txn_type,
        t.amount,
        t.created_at,
        t.is_fraud,
        a.balance AS current_balance,
        a.opened_at,
        EXTRACT(HOUR FROM t.created_at) AS hour_of_day,
        EXTRACT(DOW FROM t.created_at) AS day_of_week,
        GREATEST(
            DATE_PART('day', t.created_at - a.opened_at),
            0
        ) AS account_age_days
    FROM transactions t
    JOIN accounts a ON t.account_id = a.account_id
),

rolling AS (
    SELECT
        b.*,

        -- Count last 1 hour
        COUNT(*) OVER (
            PARTITION BY account_id
            ORDER BY created_at
            RANGE BETWEEN INTERVAL '1 hour' PRECEDING AND CURRENT ROW
        ) AS txn_count_last_1h,

        -- Count last 24 hours
        COUNT(*) OVER (
            PARTITION BY account_id
            ORDER BY created_at
            RANGE BETWEEN INTERVAL '24 hours' PRECEDING AND CURRENT ROW
        ) AS txn_count_last_24h,

        -- Count last 7 days
        COUNT(*) OVER (
            PARTITION BY account_id
            ORDER BY created_at
            RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW
        ) AS txn_count_last_7d,

        -- Total amount last 24h
        SUM(amount) OVER (
            PARTITION BY account_id
            ORDER BY created_at
            RANGE BETWEEN INTERVAL '24 hours' PRECEDING AND CURRENT ROW
        ) AS total_amount_last_24h,

        -- Avg amount last 7d
        AVG(amount) OVER (
            PARTITION BY account_id
            ORDER BY created_at
            RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW
        ) AS avg_amount_last_7d,

        -- Max amount last 7d
        MAX(amount) OVER (
            PARTITION BY account_id
            ORDER BY created_at
            RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW
        ) AS max_amount_last_7d,

        -- Previous transaction time
        LAG(created_at) OVER (
            PARTITION BY account_id
            ORDER BY created_at
        ) AS prev_txn_time

    FROM base b
)

SELECT
    txn_id,
    account_id,
    txn_type,
    amount,
    hour_of_day,
    day_of_week,
    account_age_days,
    current_balance,

    txn_count_last_1h,
    txn_count_last_24h,
    txn_count_last_7d,

    total_amount_last_24h,
    avg_amount_last_7d,
    max_amount_last_7d,

    -- Time difference feature
    EXTRACT(EPOCH FROM (created_at - prev_txn_time)) / 3600
        AS hours_since_last_txn,

    -- Deviation features
    amount / NULLIF(avg_amount_last_7d, 0)
        AS amount_to_avg_ratio,

    amount / NULLIF(current_balance, 0)
        AS amount_to_balance_ratio,

    is_fraud

FROM rolling;