-- Compara a inflação acumulada em 12 meses contra o mesmo mês do ano anterior usando LAG(12).

SELECT 
    data,
    ano_mes,
    codigo_hierarquico,
    nome_categoria,
    acumulada_12m AS inflacao_12m_atual,
    LAG(acumulada_12m, 12) OVER (
        PARTITION BY codigo_hierarquico 
        ORDER BY data
    ) AS inflacao_12m_ano_anterior,
    ROUND(
        acumulada_12m - LAG(acumulada_12m, 12) OVER (
            PARTITION BY codigo_hierarquico 
            ORDER BY data
        ), 
        2
    ) AS diferenca_ritmo_pp
FROM ipca
WHERE nivel IN ('indice_geral', 'grupo')
  AND acumulada_12m IS NOT NULL
ORDER BY 
    codigo_hierarquico, 
    data DESC;
