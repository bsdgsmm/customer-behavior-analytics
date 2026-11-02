CREATE OR REPLACE VIEW orders AS
SELECT
    order_id,
    MIN(customer_id) AS customer_id,
    MIN(order_date) AS order_date,
    CAST(DATE_TRUNC('month', MIN(order_date)) AS DATE) AS order_month,
    MIN(country) AS country,
    COUNT(*) AS line_items,
    SUM(quantity) AS units,
    ROUND(SUM(revenue), 2) AS revenue
FROM transactions
GROUP BY order_id;

CREATE OR REPLACE VIEW customer_summary AS
SELECT
    customer_id,
    MIN(order_date) AS first_order_date,
    MAX(order_date) AS last_order_date,
    COUNT(DISTINCT order_id) AS orders,
    SUM(units) AS units,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(SUM(revenue) / COUNT(DISTINCT order_id), 2) AS average_order_value,
    COUNT(DISTINCT order_id) >= 2 AS is_repeat_customer
FROM orders
GROUP BY customer_id;

CREATE OR REPLACE VIEW repeat_purchase_metrics AS
SELECT
    COUNT(*) AS customers,
    COUNT(*) FILTER (WHERE is_repeat_customer) AS repeat_customers,
    COUNT(*) FILTER (WHERE NOT is_repeat_customer) AS one_time_customers,
    ROUND(COUNT(*) FILTER (WHERE is_repeat_customer) / COUNT(*), 4) AS repeat_purchase_rate,
    ROUND(SUM(revenue) FILTER (WHERE is_repeat_customer), 2) AS repeat_customer_revenue,
    ROUND(SUM(revenue) FILTER (WHERE is_repeat_customer) / SUM(revenue), 4) AS repeat_customer_revenue_share
FROM customer_summary;

CREATE OR REPLACE VIEW monthly_customer_activity AS
WITH first_months AS (
    SELECT customer_id, MIN(order_month) AS acquisition_month
    FROM orders
    GROUP BY customer_id
)
SELECT
    o.order_month AS month,
    COUNT(DISTINCT o.customer_id) AS active_customers,
    COUNT(DISTINCT o.customer_id) FILTER (WHERE o.order_month = f.acquisition_month) AS new_customers,
    COUNT(DISTINCT o.customer_id) FILTER (WHERE o.order_month > f.acquisition_month) AS returning_customers,
    ROUND(SUM(o.revenue) FILTER (WHERE o.order_month > f.acquisition_month), 2) AS returning_customer_revenue
FROM orders AS o
JOIN first_months AS f USING (customer_id)
GROUP BY o.order_month
ORDER BY month;

CREATE OR REPLACE VIEW rfm_scores AS
WITH snapshot AS (
    SELECT CAST(MAX(order_date) AS DATE) + INTERVAL 1 DAY AS snapshot_date
    FROM transactions
),
base AS (
    SELECT
        c.customer_id,
        DATE_DIFF('day', CAST(c.last_order_date AS DATE), CAST(s.snapshot_date AS DATE)) AS recency_days,
        c.orders AS frequency,
        c.revenue AS monetary
    FROM customer_summary AS c
    CROSS JOIN snapshot AS s
),
ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY recency_days DESC) AS recency_rank,
        RANK() OVER (ORDER BY frequency) AS frequency_rank,
        RANK() OVER (ORDER BY monetary) AS monetary_rank,
        COUNT(*) OVER () AS customer_count
    FROM base
)
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    LEAST(5, GREATEST(1, CEIL(5.0 * recency_rank / customer_count)))::INTEGER AS r_score,
    LEAST(5, GREATEST(1, CEIL(5.0 * frequency_rank / customer_count)))::INTEGER AS f_score,
    LEAST(5, GREATEST(1, CEIL(5.0 * monetary_rank / customer_count)))::INTEGER AS m_score
FROM ranked
ORDER BY customer_id;

CREATE OR REPLACE VIEW cohort_retention AS
WITH first_months AS (
    SELECT customer_id, MIN(order_month) AS cohort_month
    FROM orders
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT
        f.cohort_month,
        DATE_DIFF('month', f.cohort_month, o.order_month) AS months_since_acquisition,
        o.customer_id
    FROM orders AS o
    JOIN first_months AS f USING (customer_id)
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM first_months
    GROUP BY cohort_month
)
SELECT
    a.cohort_month,
    a.months_since_acquisition,
    s.cohort_size,
    COUNT(*) AS active_customers,
    ROUND(COUNT(*) / s.cohort_size, 4) AS retention_rate
FROM activity AS a
JOIN cohort_sizes AS s USING (cohort_month)
GROUP BY a.cohort_month, a.months_since_acquisition, s.cohort_size
ORDER BY a.cohort_month, a.months_since_acquisition;
