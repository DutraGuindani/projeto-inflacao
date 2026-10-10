# Relatório de Validação e Integridade Técnica

Este documento registra os testes de integridade, auditoria de fontes e validação matemática executados em todas as etapas do projeto **Inflação e Poder de Compra no Brasil (2020–Hoje)**.

---

## 1. Auditoria das Fontes e Dados Brutos

| Fonte | Endpoint / Tabela Oficial | Registros Coletados | Período Coberto | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Banco Central do Brasil** | SGS 1619 (Salário Mínimo) | 84 meses | 01/01/2020 a 01/12/2026 | Aprovado |
| **IBGE / SIDRA** | Tabela 7060 (IPCA completo) | 111.052 linhas brutas | 202001 a 202609 | Aprovado |
| **IBGE / SIDRA** | Tabela 7063 (INPC completo) | 108.622 linhas brutas | 202001 a 202609 | Aprovado |

### Verificações realizadas:
- **Contorno de limite da API:** A coleta particionada por anos (2020 a 2026) evitou o erro de bloqueio da API do SIDRA (teto de 50.000 células).
- **Tratamento de WAF/Firewall:** Requisições ao Banco Central utilizaram cabeçalho `User-Agent` com timeout configurado, eliminando respostas vazias.

---

## 2. Validação da Engenharia e Tratamento de Dados

Após o processamento dos dados brutos (`src/tratamento.py`), foram consolidados os seguintes volumes e classificações:

### Estrutura Hierárquica da Cesta (IPCA):
- **Índice Geral:** 81 meses
- **Grupos (1 dígito):** 729 registros (9 grupos x 81 meses)
- **Subgrupos (2 dígitos):** 1.539 registros (19 subgrupos x 81 meses)
- **Itens (4 dígitos):** 4.131 registros (51 itens x 81 meses)
- **Subitens (7 dígitos):** 30.537 registros (377 subitens x 81 meses)
- **Total de registros consolidados:** 37.017 linhas

### Estrutura Hierárquica da Cesta (INPC):
- **Índice Geral:** 81 meses
- **Grupos (1 dígito):** 729 registros
- **Subgrupos (2 dígitos):** 1.539 registros
- **Itens (4 dígitos):** 4.131 registros
- **Subitens (7 dígitos):** 29.727 registros
- **Total de registros consolidados:** 36.207 linhas

### Integridade de valores:
- Todos os caracteres especiais do IBGE (`..`, `-`, `...`) foram convertidos para `NaN` e tipados numericamente como `float`.
- Zero valores nulos na chave primária temporal (`data`).

---

## 3. Validação do Banco de Dados SQLite

O banco `data/inflacao_brasil.db` foi inspecionado via consultas DDL e índices:

- **Tabela `salario_minimo`:** 84 registros | Chave primária: `ano_mes`.
- **Tabela `ipca`:** 37.017 registros | Chave primária composta: `(ano_mes, codigo_ibge)`.
- **Tabela `inpc`:** 36.207 registros | Chave primária composta: `(ano_mes, codigo_ibge)`.
- **Índices ativos:** `idx_ipca_nivel_data`, `idx_ipca_categoria`, `idx_inpc_nivel_data`, `idx_inpc_categoria`, `idx_sm_data`.

---

## 4. Prova Matemática de Cálculo Composto (SQL vs Pandas)

Para garantir que a implementação em SQL puro não sofresse desvios de arredondamento ou erro de formulação, comparamos o acumulado do IPCA Geral calculado via SQLite contra a função vetorial de produto acumulado do Pandas (`cumprod`):

- **Fórmula SQL (`sql/01_inflacao_acumulada_periodo.sql`):**  
  `(EXP(SUM(LN(1.0 + variacao_mensal / 100.0))) - 1.0) * 100.0`
- **Resultado SQL:** `44.651100049119165%`
- **Resultado Pandas (`(1 + v/100).prod() - 1`):** `44.651100049119190%`
- **Discrepância:** `2.13 x 10^-14` (zero absoluto dentro do limite de precisão de ponto flutuante de 64 bits).

A formulação matemática em SQL está comprovadamente exata.

---

## 5. Testes das Consultas Analíticas (SQL)

Todas as 5 consultas da pasta `sql/` foram executadas contra o banco SQLite local:

1. `01_inflacao_acumulada_periodo.sql`: Executada com sucesso (457 categorias acumuladas).
2. `02_ranking_subitens_mais_subiram.sql`: Executada com sucesso (Top 30 subitens ranqueados via `RANK()`).
3. `03_subitens_acima_salario_minimo.sql`: Executada com sucesso (124 linhas: 123 subitens e o grupo Alimentação e bebidas acima do salário mínimo).
4. `04_variacao_12m_lag.sql`: Executada com sucesso (700 observações analisadas via `LAG(12)`).
5. `05_diferenca_ipca_inpc.sql`: Executada com sucesso (81 meses de comparação temporal consolidada).

---

## 6. Validação do Dashboard (Streamlit)

- **Arquivo:** `dashboard/app.py`
- **Sintaxe e compilação:** Validada via `py_compile` com código de retorno 0.
- **Execução real:** o app foi renderizado com o `streamlit.testing` sem exceções, e a busca por produto foi testada com termos que contêm aspas (consulta parametrizada).
- **Portabilidade:** `LN` e `EXP` são registradas em Python na conexão (`conectar()`), pois nem todo SQLite traz funções matemáticas nativas.
- **Conferência externa:** o IPCA anual de 2020 a 2025 recalculado a partir do banco coincide com os valores oficiais do IBGE (4,52 / 10,06 / 5,79 / 4,62 / 4,83 / 4,26) e os valores do salário mínimo coincidem com os decretos de cada ano.
- **Carregamento de dados:** Utiliza decorador `@st.cache_data` para resposta instantânea ao manipular os sliders de data e filtros.
- **Gráficos interativos:** Renderização testada nos 3 componentes Plotly (barras horizontais com linha de referência, dispersão temporal e barras agrupadas de participação).

---

## 7. Parecer Final

O projeto foi auditado e executado do zero sem dados simulados, sem atalhos metodológicos e com integridade matemática e relacional confirmada.
