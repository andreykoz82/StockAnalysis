WITH RECURSIVE
    -- Остатки на складе
    stock AS (
        SELECT
            "Номенклатура" AS item,
            SUM("Количество")::numeric AS stock -- приводим к numeric для единообразия
        FROM current_stocks
        GROUP BY "Номенклатура"
    ),

    -- Расчёт рабочих дней (в полном месяце и оставшихся с сегодня)
    work_days_calc AS (
        SELECT
            s.item,
            s.ds,          -- ожидается тип date
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
        -- Генерируем дни месяца, где находится ds
        CROSS JOIN LATERAL (
            SELECT gs::date AS day
            FROM generate_series(
                date_trunc('month', s.ds::timestamp)::date,                          -- ds -> timestamp для date_trunc
                (date_trunc('month', s.ds::timestamp) + interval '1 month - 1 day')::date,
                interval '1 day'
            ) AS gs
        ) d
        LEFT JOIN holidays h ON d.day = h.holiday_date::date
        GROUP BY s.item, s.ds, s.timesfm
    ),

    -- Среднедневная продажа по месяцу
    daily_sales AS (
        SELECT
            item,
            ds,
            timesfm,
            work_days_full_month,
            work_days_remaining,
            (timesfm::numeric / NULLIF(work_days_full_month, 0)) AS daily_rate  -- numeric-деление
        FROM work_days_calc
        WHERE work_days_full_month > 0
    ),

    -- Только будущие/текущие месяцы, упорядочивание по ds
    ordered_sales AS (
        SELECT
            item,
            ds,
            daily_rate,
            work_days_remaining,
            ROW_NUMBER() OVER (PARTITION BY item ORDER BY ds) AS month_order
        FROM daily_sales
        WHERE ds::date >= CURRENT_DATE  -- явное приведение, чтобы избежать 'text >= date'
    ),

    -- Рекурсивный проход по месяцам: списываем склад по дневной норме
    cte AS (
        -- Первый месяц
        SELECT
            os.item,
            os.month_order,
            os.ds,
            os.daily_rate,
            os.work_days_remaining,
            s.stock::numeric AS stock,
            CASE
                WHEN s.stock <= 0 THEN 0::numeric
                WHEN s.stock >= os.daily_rate * os.work_days_remaining
                    THEN os.work_days_remaining::numeric
                ELSE LEAST(s.stock / os.daily_rate, os.work_days_remaining::numeric)
            END AS days_covered,
            CASE
                WHEN s.stock <= 0 THEN 0::numeric
                ELSE s.stock - (os.daily_rate * os.work_days_remaining)
            END AS remaining_stock
        FROM ordered_sales os
        JOIN stock s ON os.item = s.item
        WHERE os.month_order = 1
          AND s.stock > 0

        UNION ALL

        -- Последующие месяцы
        SELECT
            os.item,
            os.month_order,
            os.ds,
            os.daily_rate,
            os.work_days_remaining,
            c.remaining_stock AS stock,
            CASE
                WHEN c.remaining_stock <= 0 THEN 0::numeric
                WHEN c.remaining_stock >= os.daily_rate * os.work_days_remaining
                    THEN os.work_days_remaining::numeric
                ELSE GREATEST(c.remaining_stock / os.daily_rate, 0)
            END AS days_covered,
            CASE
                WHEN c.remaining_stock <= 0 THEN 0::numeric
                ELSE c.remaining_stock - (os.daily_rate * os.work_days_remaining)
            END AS remaining_stock
        FROM cte c
        JOIN ordered_sales os
          ON os.item = c.item
         AND os.month_order = c.month_order + 1
        WHERE c.remaining_stock > 0
    )

-- Финальный вывод: сколько дней покрывает текущий склад
SELECT
    s.item AS "Номенклатура",
    CASE
            WHEN s.stock <= 0 THEN 0
            ELSE COALESCE(CEIL(SUM(cte.days_covered))::int, 0)
        END AS "Дней до исчерпания"
FROM stock s
LEFT JOIN cte
  ON s.item = cte.item
GROUP BY s.item, s.stock
ORDER BY s.item;