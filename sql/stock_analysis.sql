WITH RECURSIVE stock AS (
    -- Агрегируем остатки по номенклатуре
    SELECT "Номенклатура" AS item, SUM("Количество") AS stock
    FROM current_stocks
    GROUP BY "Номенклатура"
),
work_days_calc AS (
    -- Рассчитываем рабочие дни с текущей даты по конец месяца
    SELECT
        s.item,
        s.ds,
        s.timesfm,
        COUNT(*) FILTER (WHERE EXTRACT(DOW FROM d.day) NOT IN (0, 6) AND h.holiday_date IS NULL) AS work_days_full_month, -- Все рабочие дни в месяце
        COUNT(*) FILTER (WHERE EXTRACT(DOW FROM d.day) NOT IN (0, 6) AND h.holiday_date IS NULL AND d.day >= CURRENT_DATE) AS work_days_remaining -- Рабочие дни с текущей даты по конец месяца
    FROM sales_forecast s
    CROSS JOIN LATERAL generate_series(
        DATE_TRUNC('month', s.ds)::DATE, -- Начало месяца
        DATE_TRUNC('month', s.ds) + INTERVAL '1 month' - INTERVAL '1 day', -- Конец месяца
        '1 day'::INTERVAL
    ) AS d(day)
    LEFT JOIN holidays h ON d.day = h.holiday_date -- Проверяем праздники
    GROUP BY s.item, s.ds, s.timesfm
),
daily_sales AS (
    -- Определяем дневной расход исходя из полных рабочих дней в месяце
    SELECT
        item,
        ds,
        timesfm,
        work_days_full_month,
        work_days_remaining,
        (timesfm / NULLIF(work_days_full_month, 0)) AS daily_rate -- Защита от деления на ноль
    FROM work_days_calc
    WHERE work_days_full_month > 0 -- Исключаем месяцы без рабочих дней
),
ordered_sales AS (
    -- Упорядочиваем месяцы по дате для каждой номенклатуры
    SELECT
        item,
        ds,
        daily_rate,
        work_days_full_month,
        work_days_remaining,
        ROW_NUMBER() OVER (PARTITION BY item ORDER BY ds) AS month_order
    FROM daily_sales
    WHERE ds >= CURRENT_DATE -- Ограничиваем только текущими и будущими месяцами
),
cte AS (
    -- Рекурсивно накапливаем расход по месяцам
    SELECT
        os.item,
        os.month_order,
        os.ds,
        os.daily_rate,
        os.work_days_full_month,
        os.work_days_remaining, -- Используем только рабочие дни, начиная с текущей даты
        s.stock,
        CASE
            WHEN s.stock >= os.daily_rate * os.work_days_remaining
                THEN os.work_days_remaining
                ELSE LEAST(s.stock / os.daily_rate, os.work_days_remaining)
        END AS days_covered,
        s.stock - (os.daily_rate * os.work_days_remaining) AS remaining_stock
    FROM ordered_sales os
    JOIN stock s ON os.item = s.item
    WHERE os.month_order = 1 -- Начинаем с первого месяца

    UNION ALL

    SELECT
        os.item,
        os.month_order,
        os.ds,
        os.daily_rate,
        os.work_days_full_month,
        os.work_days_remaining,
        c.remaining_stock,
        CASE
            WHEN c.remaining_stock >= os.daily_rate * os.work_days_remaining
                THEN os.work_days_remaining
                ELSE GREATEST(c.remaining_stock / os.daily_rate, 0)
        END AS days_covered,
        c.remaining_stock - (os.daily_rate * os.work_days_remaining) AS remaining_stock
    FROM cte c
    JOIN ordered_sales os
        ON os.item = c.item
        AND os.month_order = c.month_order + 1
    WHERE c.remaining_stock > 0 -- Продолжаем, пока остаток не исчерпан
)
-- Выводим детализированную информацию
SELECT
    cte.item AS "Номенклатура",
    cte.ds AS "Дата прогноза",
    cte.daily_rate AS "Дневной расход",
    cte.work_days_full_month AS "Рабочих дней в месяце (всего)",
    cte.work_days_remaining AS "Рабочих дней до конца месяца",
    cte.days_covered AS "Дней покрыто",
    cte.remaining_stock AS "Остаток после покрытия"
FROM cte
WHERE cte.ds >= CURRENT_DATE -- Исключаем предыдущие месяца из результатов
ORDER BY cte.item, cte.ds;



WITH RECURSIVE stock AS (
    -- Агрегируем остатки по номенклатуре
    SELECT "Номенклатура" AS item, SUM("Количество") AS stock
    FROM current_stocks
    GROUP BY "Номенклатура"
),
work_days_calc AS (
    -- Рассчитываем рабочие дни с текущей даты по конец месяца
    SELECT
        s.item,
        s.ds,
        s.timesfm,
        COUNT(*) FILTER (WHERE EXTRACT(DOW FROM d.day) NOT IN (0, 6) AND h.holiday_date IS NULL) AS work_days_full_month, -- Все рабочие дни в месяце
        COUNT(*) FILTER (WHERE EXTRACT(DOW FROM d.day) NOT IN (0, 6) AND h.holiday_date IS NULL AND d.day >= CURRENT_DATE) AS work_days_remaining -- Рабочие дни с текущей даты по конец месяца
    FROM sales_forecast s
    CROSS JOIN LATERAL generate_series(
        DATE_TRUNC('month', s.ds)::DATE, -- Начало месяца
        DATE_TRUNC('month', s.ds) + INTERVAL '1 month' - INTERVAL '1 day', -- Конец месяца
        '1 day'::INTERVAL
    ) AS d(day)
    LEFT JOIN holidays h ON d.day = h.holiday_date -- Проверяем праздники
    GROUP BY s.item, s.ds, s.timesfm
),
daily_sales AS (
    -- Определяем дневной расход исходя из полных рабочих дней в месяце
    SELECT
        item,
        ds,
        timesfm,
        work_days_full_month,
        work_days_remaining,
        (timesfm / NULLIF(work_days_full_month, 0)) AS daily_rate -- Защита от деления на ноль
    FROM work_days_calc
    WHERE work_days_full_month > 0 -- Исключаем месяцы без рабочих дней
),
ordered_sales AS (
    -- Упорядочиваем месяцы по дате для каждой номенклатуры
    SELECT
        item,
        ds,
        daily_rate,
        work_days_full_month,
        work_days_remaining,
        ROW_NUMBER() OVER (PARTITION BY item ORDER BY ds) AS month_order
    FROM daily_sales
    WHERE ds >= CURRENT_DATE -- Ограничиваем только текущими и будущими месяцами
),
cte AS (
    -- Рекурсивно накапливаем расход по месяцам
    SELECT
        os.item,
        os.month_order,
        os.ds,
        os.daily_rate,
        os.work_days_remaining, -- Используем только рабочие дни, начиная с текущей даты
        s.stock,
        CASE
            WHEN s.stock >= os.daily_rate * os.work_days_remaining
                THEN os.work_days_remaining
                ELSE LEAST(s.stock / os.daily_rate, os.work_days_remaining)
        END AS days_covered,
        s.stock - (os.daily_rate * os.work_days_remaining) AS remaining_stock
    FROM ordered_sales os
    JOIN stock s ON os.item = s.item
    WHERE os.month_order = 1 -- Начинаем с первого месяца

    UNION ALL

    SELECT
        os.item,
        os.month_order,
        os.ds,
        os.daily_rate,
        os.work_days_remaining,
        c.remaining_stock,
        CASE
            WHEN c.remaining_stock >= os.daily_rate * os.work_days_remaining
                THEN os.work_days_remaining
                ELSE GREATEST(c.remaining_stock / os.daily_rate, 0)
        END AS days_covered,
        c.remaining_stock - (os.daily_rate * os.work_days_remaining) AS remaining_stock
    FROM cte c
    JOIN ordered_sales os
        ON os.item = c.item
        AND os.month_order = c.month_order + 1
    WHERE c.remaining_stock > 0 -- Продолжаем, пока остаток не исчерпан
)
-- Выводим только итоговую информацию по дням до исчерпания запасов
SELECT
    cte.item AS "Номенклатура",
    CEIL(SUM(cte.days_covered)) AS "Дней до исчерпания"
FROM cte
GROUP BY cte.item
ORDER BY cte.item;