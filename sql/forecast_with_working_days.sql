SELECT
    ds::date AS current_date,
    timesfm,
    item,
    (
        SELECT COUNT(*)
        FROM generate_series(
            date_trunc('month', ds::timestamp)::date,         -- <— привели к timestamp
            LEAST(ds::date, CURRENT_DATE)::date,
            '1 day'
        ) AS day_series(day)
        WHERE
            EXTRACT(dow FROM day_series.day) NOT IN (0, 6)
            AND day_series.day NOT IN (
                SELECT holiday_date::date FROM holidays
            )
    ) AS passed_working_days,
    (
        SELECT COUNT(*)
        FROM generate_series(
            date_trunc('month', ds::timestamp)::date,         -- <— привели к timestamp
            (date_trunc('month', ds::timestamp)               -- <— и тут
                + interval '1 month - 1 day')::date,
            '1 day'
        ) AS day_series(day)
        WHERE
            EXTRACT(dow FROM day_series.day) NOT IN (0, 6)
            AND day_series.day NOT IN (
                SELECT holiday_date::date FROM holidays
            )
    ) AS total_working_days
FROM sales_forecast;