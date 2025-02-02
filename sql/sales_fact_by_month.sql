SELECT
    DATE_TRUNC('month', Дата) + INTERVAL '1 month - 1 day' AS Дата,
    Номенклатура,
    SUM(Продажи) AS ОбщиеПродажи
FROM
    sales
GROUP BY
    DATE_TRUNC('month', Дата),
    Номенклатура
ORDER BY
    Дата, Номенклатура;