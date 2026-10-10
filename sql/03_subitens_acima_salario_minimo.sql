-- Identifica subitens e grupos cuja inflação acumulada superou o reajuste do salário mínimo no período.

WITH limites_datas AS (
    SELECT MIN(data) AS dt_ini, MAX(data) AS dt_fim FROM ipca
),
reajuste_sm AS (
    SELECT 
        sm_ini.valor AS valor_inicial,
        sm_fim.valor AS valor_final,
        ROUND(((sm_fim.valor / sm_ini.valor) - 1.0) * 100.0, 2) AS reajuste_sm_pct
    FROM limites_datas ld
    JOIN salario_minimo sm_ini ON sm_ini.data = ld.dt_ini
    JOIN salario_minimo sm_fim ON sm_fim.data = ld.dt_fim
),
acumulado AS (
    SELECT 
        nivel,
        codigo_hierarquico,
        nome_categoria,
        ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct,
        ROUND(AVG(peso_mensal), 4) AS peso_medio_pct
    FROM ipca
    WHERE variacao_mensal IS NOT NULL
      AND (1.0 + (variacao_mensal / 100.0)) > 0
    GROUP BY nivel, codigo_hierarquico, nome_categoria
)
SELECT 
    a.nivel,
    a.codigo_hierarquico,
    a.nome_categoria,
    a.inflacao_acumulada_pct,
    r.reajuste_sm_pct AS reajuste_salario_minimo_pct,
    ROUND(a.inflacao_acumulada_pct - r.reajuste_sm_pct, 2) AS diferenca_pp,
    ROUND(a.inflacao_acumulada_pct / r.reajuste_sm_pct, 2) AS razao_alta_vs_salario,
    a.peso_medio_pct
FROM acumulado a
CROSS JOIN reajuste_sm r
WHERE a.inflacao_acumulada_pct > r.reajuste_sm_pct
  AND a.nivel IN ('grupo', 'subitem')
ORDER BY diferenca_pp DESC;
