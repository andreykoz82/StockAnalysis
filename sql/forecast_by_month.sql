SELECT
    DATE_TRUNC('month', ds) + INTERVAL '1 month - 1 day' AS Дата,
    SUM(timesfm) AS ОбщиеПродажи
FROM
    sales_forecast
GROUP BY
    DATE_TRUNC('month', ds) + INTERVAL '1 month - 1 day'
ORDER BY
    Дата;