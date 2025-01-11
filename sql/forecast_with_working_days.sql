SELECT
    ds::date AS current_date, -- Преобразуем ds, чтобы учитывать только дату
    timesfm,
    item,
    (
        SELECT COUNT(*)
        FROM generate_series(
            date_trunc('month', ds)::date, -- Начало месяца
            LEAST(ds::date, CURRENT_DATE)::date, -- Ограничиваем текущую дату или сегодняшним днём
            '1 day'
        ) AS day_series(day)
        WHERE
            EXTRACT(dow FROM day_series.day) NOT IN (0, 6) -- Исключаем субботу (6) и воскресенье (0)
            AND day_series.day NOT IN (
                SELECT holiday_date::date FROM holidays -- Приводим holiday_date к типу date
            ) -- Исключаем праздничные дни
    ) AS passed_working_days, -- Количество рабочих дней, которые уже прошли
    (
        SELECT COUNT(*)
        FROM generate_series(
            date_trunc('month', ds)::date, -- Начало месяца
            (date_trunc('month', ds) + interval '1 month - 1 day')::date, -- Конец месяца
            '1 day'
        ) AS day_series(day)
        WHERE
            EXTRACT(dow FROM day_series.day) NOT IN (0, 6) -- Исключаем субботу и воскресенье
            AND day_series.day NOT IN (
                SELECT holiday_date::date FROM holidays -- Приводим holiday_date к типу date
            ) -- Исключаем праздничные дни
    ) AS total_working_days -- Общее количество рабочих дней в месяце
FROM sales_forecast;