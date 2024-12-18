SELECT
    ds::date,
    forecast,
    item,
    (SELECT COUNT(*)
     FROM generate_series(
        date_trunc('month', ds)::date,
        (date_trunc('month', ds) + interval '1 month - 1 day')::date,
        '1 day'
     ) AS day
     WHERE EXTRACT(dow FROM day::date) NOT IN (0, 6) -- Явное приведение к дате
    ) AS working_days
FROM sarima_forecast;