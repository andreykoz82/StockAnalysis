WITH RECURSIVE
    stock AS (
        SELECT
            "Номенклатура" AS item,
            SUM("Количество") AS stock
        FROM current_stocks
        GROUP BY "Номенклатура"
    ),
    work_days_calc AS (
        SELECT
            s.item,
            s.ds,
            s.timesfm,
            COUNT(*) FILTER (
                WHERE EXTRACT(DOW FROM d.day) NOT IN (0, 6)
                  AND h.holiday_date IS NULL
            ) AS work_days_full_month,
            COUNT(*) FILTER (
                WHERE EXTRACT(DOW FROM d.day) NOT IN (0, 6)
                  AND h.holiday_date IS NULL
                  AND d.day >= CURRENT_DATE
            ) AS work_days_remaining
        FROM sales_forecast s
        CROSS JOIN LATERAL generate_series(
            DATE_TRUNC('month', s.ds)::DATE,
            DATE_TRUNC('month', s.ds) + INTERVAL '1 month' - INTERVAL '1 day',
            INTERVAL '1 day'
        ) AS d(day)
        LEFT JOIN holidays h ON d.day = h.holiday_date
        GROUP BY s.item, s.ds, s.timesfm
    ),
    daily_sales AS (
        SELECT
            item,
            ds,
            timesfm,
            work_days_full_month,
            work_days_remaining,
            timesfm / NULLIF(work_days_full_month, 0) AS daily_rate
        FROM work_days_calc
        WHERE work_days_full_month > 0
    ),
    ordered_sales AS (
        SELECT
            item,
            ds,
            daily_rate,
            work_days_remaining,
            ROW_NUMBER() OVER (PARTITION BY item ORDER BY ds) AS month_order
        FROM daily_sales
        WHERE ds >= CURRENT_DATE
    ),
    cte AS (
        SELECT
            os.item,
            os.month_order,
            os.ds,
            os.daily_rate,
            os.work_days_remaining,
            s.stock,
            CASE
                WHEN s.stock <= 0 THEN 0
                WHEN s.stock >= os.daily_rate * os.work_days_remaining
                    THEN os.work_days_remaining
                ELSE LEAST(s.stock / os.daily_rate, os.work_days_remaining)
            END AS days_covered,
            CASE
                WHEN s.stock <= 0 THEN 0
                ELSE s.stock - (os.daily_rate * os.work_days_remaining)
            END AS remaining_stock
        FROM ordered_sales os
        JOIN stock s ON os.item = s.item
        WHERE os.month_order = 1
          AND s.stock > 0 -- <--- Добавлено условие чтобы НЕ стартовать, если stock = 0

        UNION ALL

        SELECT
            os.item,
            os.month_order,
            os.ds,
            os.daily_rate,
            os.work_days_remaining,
            c.remaining_stock,
            CASE
                WHEN c.remaining_stock <= 0 THEN 0
                WHEN c.remaining_stock >= os.daily_rate * os.work_days_remaining
                    THEN os.work_days_remaining
                ELSE GREATEST(c.remaining_stock / os.daily_rate, 0)
            END AS days_covered,
            CASE
                WHEN c.remaining_stock <= 0 THEN 0
                ELSE c.remaining_stock - (os.daily_rate * os.work_days_remaining)
            END AS remaining_stock
        FROM cte c
        JOIN ordered_sales os
            ON os.item = c.item
            AND os.month_order = c.month_order + 1
        WHERE c.remaining_stock > 0
    )

SELECT
    s.item AS "Номенклатура",
    CASE
        WHEN s.stock <= 0 THEN 0
        ELSE COALESCE(CEIL(SUM(cte.days_covered)), 0)
    END AS "Дней до исчерпания"
FROM stock s
LEFT JOIN cte
    ON s.item = cte.item
GROUP BY s.item, s.stock
ORDER BY s.item;