SELECT
    "Номенклатура",
    SUM(CASE WHEN "Склад" = 'Склад готовой продукции' THEN "Количество" ELSE 0 END) AS "Склад готовой продукции",
    SUM(CASE WHEN "Склад" = 'Склад оптовой торговли ЛС' THEN "Количество" ELSE 0 END) AS "Склад оптовой торговли ЛС"
FROM
    current_stocks
GROUP BY
    "Номенклатура"
ORDER BY
    "Номенклатура";