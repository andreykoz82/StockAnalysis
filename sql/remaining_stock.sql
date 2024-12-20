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
    WHERE
        sf.ds >= CURRENT_DATE -- Условие для выбора данных только с текущей даты
),
running_stock AS (
    SELECT
        Номенклатура,
        ds,
        GREATEST(
            initial_stock - SUM(timesfm) OVER (
                PARTITION BY Номенклатура
                ORDER BY ds
            ),
            0
        ) AS remaining_stock
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
