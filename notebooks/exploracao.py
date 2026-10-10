"""
Exploração dos dados consolidados no banco SQLite (inflacao_brasil.db).
"""

import os
import sqlite3
import pandas as pd

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_DIR, "data", "inflacao_brasil.db")

con = sqlite3.connect(DB_PATH)

print("--- Reajuste do Salário Mínimo (2020 a 2026) ---")
query_sm = """
SELECT 
    (SELECT valor FROM salario_minimo WHERE data = '2020-01-01') AS sm_inicial,
    (SELECT valor FROM salario_minimo WHERE data = (SELECT MAX(data) FROM ipca)) AS sm_final,
    ROUND((( (SELECT valor FROM salario_minimo WHERE data = (SELECT MAX(data) FROM ipca)) / (SELECT valor FROM salario_minimo WHERE data = '2020-01-01') ) - 1.0) * 100.0, 2) AS reajuste_sm_pct;
"""
print(pd.read_sql_query(query_sm, con).to_string(index=False))

print("\n--- Inflação Acumulada Composta por Grupo (IPCA) ---")
query_grupos = """
SELECT 
    codigo_hierarquico,
    nome_categoria,
    ROUND(AVG(peso_mensal), 2) AS peso_medio_pct,
    ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct
FROM ipca
WHERE nivel = 'grupo'
GROUP BY codigo_hierarquico, nome_categoria
ORDER BY inflacao_acumulada_pct DESC;
"""
print(pd.read_sql_query(query_grupos, con).to_string(index=False))

print("\n--- Top 15 Subitens com Maior Alta Acumulada ---")
query_top = """
WITH subitens AS (
    SELECT 
        codigo_hierarquico,
        nome_categoria,
        ROUND(AVG(peso_mensal), 4) AS peso_medio_pct,
        ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct
    FROM ipca
    WHERE nivel = 'subitem'
      AND variacao_mensal IS NOT NULL
      AND (1.0 + (variacao_mensal / 100.0)) > 0
    GROUP BY codigo_hierarquico, nome_categoria
)
SELECT 
    RANK() OVER (ORDER BY inflacao_acumulada_pct DESC) AS ranking,
    nome_categoria,
    inflacao_acumulada_pct,
    peso_medio_pct
FROM subitens
ORDER BY ranking ASC
LIMIT 15;
"""
print(pd.read_sql_query(query_top, con).to_string(index=False))

print("\n--- Comparação de Pesos no Orçamento: IPCA vs INPC ---")
query_pesos = """
SELECT 
    ipca.nome_categoria,
    ROUND(AVG(ipca.peso_mensal), 2) AS peso_ipca,
    ROUND(AVG(inpc.peso_mensal), 2) AS peso_inpc,
    ROUND(AVG(inpc.peso_mensal) - AVG(ipca.peso_mensal), 2) AS diferenca_pp
FROM ipca
JOIN inpc 
  ON ipca.data = inpc.data 
 AND ipca.codigo_hierarquico = inpc.codigo_hierarquico
WHERE ipca.nivel = 'grupo'
GROUP BY ipca.nome_categoria
ORDER BY diferenca_pp DESC;
"""
print(pd.read_sql_query(query_pesos, con).to_string(index=False))

con.close()
