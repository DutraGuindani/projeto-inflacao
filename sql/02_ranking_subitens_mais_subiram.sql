-- Ranking dos 30 subitens do IPCA com maior alta acumulada desde 2020 via RANK() e ROW_NUMBER().

WITH acumulado_subitens AS (
    SELECT 
        codigo_hierarquico,
        nome_categoria,
        ROUND(AVG(peso_mensal), 4) AS peso_medio_pct,
        ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct,
        COUNT(variacao_mensal) AS meses
    FROM ipca
    WHERE nivel = 'subitem'
      AND variacao_mensal IS NOT NULL
      AND (1.0 + (variacao_mensal / 100.0)) > 0
    GROUP BY 
        codigo_hierarquico, 
        nome_categoria
)
SELECT 
    RANK() OVER (ORDER BY inflacao_acumulada_pct DESC) AS ranking,
    ROW_NUMBER() OVER (ORDER BY inflacao_acumulada_pct DESC) AS posicao,
    codigo_hierarquico,
    nome_categoria,
    inflacao_acumulada_pct,
    peso_medio_pct,
    meses
FROM acumulado_subitens
ORDER BY ranking ASC
LIMIT 30;
