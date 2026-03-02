CREATE OR REPLACE FUNCTION get_features_for_txn(p_txn_id BIGINT)
RETURNS TABLE (
    txn_id BIGINT,
    amount NUMERIC,
    hour_of_day INT,
    day_of_week INT,
    account_age_days NUMERIC,
    current_balance NUMERIC,
    txn_count_last_1h INT,
    txn_count_last_24h INT,
    txn_count_last_7d INT,
    total_amount_last_24h NUMERIC,
    avg_amount_last_7d NUMERIC,
    max_amount_last_7d NUMERIC,
    hours_since_last_txn NUMERIC,
    amount_to_avg_ratio NUMERIC,
    amount_to_balance_ratio NUMERIC,
    txn_type_DEPOSIT INT,
    txn_type_TRANSFER_OUT INT
) AS $$
BEGIN

RETURN QUERY
SELECT
    t.txn_id,
    t.amount,
    EXTRACT(HOUR FROM t.created_at)::INT,
    EXTRACT(DOW FROM t.created_at)::INT,
    EXTRACT(DAY FROM (t.created_at - a.created_at))::NUMERIC,
    a.balance,
    
    COUNT(*) FILTER (
        WHERE t2.created_at >= t.created_at - INTERVAL '1 hour'
    )::INT,

    COUNT(*) FILTER (
        WHERE t2.created_at >= t.created_at - INTERVAL '24 hours'
    )::INT,

    COUNT(*) FILTER (
        WHERE t2.created_at >= t.created_at - INTERVAL '7 days'
    )::INT,

    COALESCE(SUM(t2.amount) FILTER (
        WHERE t2.created_at >= t.created_at - INTERVAL '24 hours'
    ),0),

    COALESCE(AVG(t2.amount) FILTER (
        WHERE t2.created_at >= t.created_at - INTERVAL '7 days'
    ),0),

    COALESCE(MAX(t2.amount) FILTER (
        WHERE t2.created_at >= t.created_at - INTERVAL '7 days'
    ),0),

    EXTRACT(EPOCH FROM (
        t.created_at - LAG(t.created_at) OVER (
            PARTITION BY t.account_id ORDER BY t.created_at
        )
    ))/3600.0,

    CASE
        WHEN AVG(t2.amount) FILTER (
            WHERE t2.created_at >= t.created_at - INTERVAL '7 days'
        ) > 0
        THEN t.amount / AVG(t2.amount) FILTER (
            WHERE t2.created_at >= t.created_at - INTERVAL '7 days'
        )
        ELSE 1
    END,

    CASE
        WHEN a.balance > 0
        THEN t.amount / a.balance
        ELSE 0
    END,

    CASE WHEN t.txn_type = 'DEPOSIT' THEN 1 ELSE 0 END,
    CASE WHEN t.txn_type = 'TRANSFER_OUT' THEN 1 ELSE 0 END

FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
LEFT JOIN transactions t2 
    ON t.account_id = t2.account_id
    AND t2.created_at <= t.created_at
WHERE t.txn_id = p_txn_id
GROUP BY t.txn_id, a.balance, a.created_at, t.created_at, t.amount, t.txn_type;

END;
$$ LANGUAGE plpgsql;