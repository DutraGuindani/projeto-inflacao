-- Inflação acumulada composta por categoria no período.
-- Como o SQLite não possui função de produto agregado (PROD), usamos EXP(SUM(LN(1 + v/100))).

SELECT 
    nivel,
    codigo_hierarquico,
    nome_categoria,
    COUNT(variacao_mensal) AS qtd_meses,
    ROUND(AVG(peso_mensal), 2) AS peso_medio_pct,
    ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct
FROM ipca
WHERE variacao_mensal IS NOT NULL
  AND (1.0 + (variacao_mensal / 100.0)) > 0
GROUP BY 
    nivel, 
    codigo_hierarquico, 
    nome_categoria
ORDER BY 
    nivel, 
    inflacao_acumulada_pct DESC;
