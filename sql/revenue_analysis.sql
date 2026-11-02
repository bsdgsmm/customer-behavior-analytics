CREATE OR REPLACE VIEW monthly_revenue AS
SELECT
    order_month AS month,
    ROUND(SUM(revenue), 2) AS revenue,
    COUNT(*) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(revenue) / COUNT(*), 2) AS average_order_value
FROM orders
GROUP BY order_month
ORDER BY month;

CREATE OR REPLACE VIEW quarterly_revenue AS
SELECT
    STRFTIME(order_month, '%Y') || 'Q' || CAST(QUARTER(order_month) AS VARCHAR) AS quarter,
    ROUND(SUM(revenue), 2) AS revenue,
    COUNT(*) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(revenue) / COUNT(*), 2) AS average_order_value
FROM orders
GROUP BY quarter
ORDER BY quarter;

CREATE OR REPLACE VIEW country_revenue AS
SELECT
    country,
    ROUND(SUM(revenue), 2) AS revenue,
    COUNT(*) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(revenue) / SUM(SUM(revenue)) OVER (), 4) AS revenue_share,
    ROUND(SUM(revenue) / COUNT(*), 2) AS average_order_value
FROM orders
GROUP BY country
ORDER BY revenue DESC;

CREATE OR REPLACE VIEW top_products_by_revenue AS
SELECT
    product_id,
    product_name,
    SUM(quantity) AS units_sold,
    ROUND(SUM(revenue), 2) AS revenue,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_id) AS customers
FROM transactions
GROUP BY product_id, product_name
ORDER BY revenue DESC, product_id
LIMIT 10;

CREATE OR REPLACE VIEW frequently_purchased_products AS
SELECT
    product_id,
    product_name,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(COUNT(DISTINCT order_id) / (SELECT COUNT(DISTINCT order_id) FROM transactions), 4) AS order_penetration
FROM transactions
GROUP BY product_id, product_name
ORDER BY orders DESC, product_id
LIMIT 10;

CREATE OR REPLACE VIEW top_customers_by_revenue AS
SELECT
    customer_id,
    orders,
    revenue,
    ROUND(revenue / SUM(revenue) OVER (), 4) AS revenue_share,
    average_order_value
FROM customer_summary
ORDER BY revenue DESC, customer_id
LIMIT 10;

CREATE OR REPLACE VIEW revenue_concentration AS
WITH ranked AS (
    SELECT
        revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC, customer_id) AS revenue_rank,
        COUNT(*) OVER () AS customer_count,
        SUM(revenue) OVER () AS total_revenue
    FROM customer_summary
),
tiers AS (
    SELECT UNNEST([0.01, 0.05, 0.10, 0.20, 0.50]) AS top_customer_share
)
SELECT
    t.top_customer_share,
    GREATEST(1, ROUND(MAX(r.customer_count) * t.top_customer_share))::INTEGER AS customers,
    ROUND(SUM(r.revenue), 2) AS revenue,
    ROUND(SUM(r.revenue) / MAX(r.total_revenue), 4) AS revenue_share
FROM tiers AS t
JOIN ranked AS r ON r.revenue_rank <= GREATEST(1, ROUND(r.customer_count * t.top_customer_share))
GROUP BY t.top_customer_share
ORDER BY t.top_customer_share;
