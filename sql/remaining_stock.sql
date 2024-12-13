WITH combined_data AS (
    SELECT
        cs.Номенклатура,
        cs.Количество AS initial_stock,
        sf.ds,
        sf.timesfm
    FROM
        current_stocks cs
    INNER JOIN
        sales_forecast sf
    ON
        cs.Номенклатура = sf.item
),
running_stock AS (
    SELECT
        Номенклатура,
        ds,
        GREATEST(initial_stock - SUM(timesfm) OVER (PARTITION BY Номенклатура ORDER BY ds), 0) AS remaining_stock
    FROM
        combined_data
)
SELECT
    Номенклатура,
    ds,
    remaining_stock
FROM
    running_stock
ORDER BY
    Номенклатура, ds;