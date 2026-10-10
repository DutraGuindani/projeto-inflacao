-- Confronta o comportamento histórico do IPCA (1 a 40 SM) contra o INPC (1 a 5 SM).

WITH serie_mensal AS (
    SELECT 
        ip.data,
        ip.ano_mes,
        ip.variacao_mensal AS ipca_mensal,
        inp.variacao_mensal AS inpc_mensal,
        ROUND(inp.variacao_mensal - ip.variacao_mensal, 2) AS dif_mensal_pp,
        ip.acumulada_12m AS ipca_12m,
        inp.acumulada_12m AS inpc_12m
    FROM ipca ip
    JOIN inpc inp 
      ON ip.data = inp.data 
     AND ip.nivel = inp.nivel 
     AND ip.codigo_hierarquico = inp.codigo_hierarquico
    WHERE ip.nivel = 'indice_geral'
),
acumulado AS (
    SELECT 
        ROUND((EXP(SUM(LN(1.0 + (ipca_mensal / 100.0)))) - 1.0) * 100.0, 2) AS ipca_acumulado,
        ROUND((EXP(SUM(LN(1.0 + (inpc_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inpc_acumulado
    FROM serie_mensal
    WHERE (1.0 + (ipca_mensal / 100.0)) > 0
      AND (1.0 + (inpc_mensal / 100.0)) > 0
)
SELECT 
    s.data,
    s.ano_mes,
    s.ipca_mensal,
    s.inpc_mensal,
    s.dif_mensal_pp,
    s.ipca_12m,
    s.inpc_12m,
    a.ipca_acumulado,
    a.inpc_acumulado,
    ROUND(a.inpc_acumulado - a.ipca_acumulado, 2) AS dif_acumulada_pp
FROM serie_mensal s
CROSS JOIN acumulado a
ORDER BY s.data DESC;
