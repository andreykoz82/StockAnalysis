SELECT
    DATE_TRUNC('month', Дата) AS Дата,
    Номенклатура,
    SUM(Продажи) AS ОбщиеПродажи
FROM
    sales
GROUP BY
    DATE_TRUNC('month', Дата),
    Номенклатура
ORDER BY
    Дата, Номенклатура;