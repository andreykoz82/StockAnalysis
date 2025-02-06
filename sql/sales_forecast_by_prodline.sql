SELECT
    ai."Производственная линия" AS production_line,
    SUM(sf.timesfm) AS total_volume
FROM
    sales_forecast sf
INNER JOIN
    actual_items ai
    ON sf.item = ai."Наименование"
WHERE
    sf.ds BETWEEN '2025-02-01' AND '2025-02-28'
GROUP BY
    ai."Производственная линия"
ORDER BY
    total_volume DESC;