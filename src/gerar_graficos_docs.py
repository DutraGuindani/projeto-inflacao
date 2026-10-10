"""
Geração de Gráficos em Alta Resolução para Documentação (docs/)
---------------------------------------------------------------
Projeto: Inflação e Poder de Compra no Brasil (2020-Hoje)

Este script consulta o SQLite e renderiza os 3 gráficos essenciais do projeto
em formato PNG de alta qualidade para inclusão no README.md e redes sociais.
"""

import math
import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# Configurações de estilo
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"]
plt.rcParams["axes.edgecolor"] = "#CBD5E1"
plt.rcParams["axes.linewidth"] = 0.8

DIRETORIO_PROJETO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAMINHO_DB = os.path.join(DIRETORIO_PROJETO, "data", "inflacao_brasil.db")
PASTA_DOCS = os.path.join(DIRETORIO_PROJETO, "docs")
os.makedirs(PASTA_DOCS, exist_ok=True)

con = sqlite3.connect(CAMINHO_DB)
# Registra LN e EXP em Python (nem todo SQLite traz funcoes matematicas nativas)
con.create_function("LN", 1, lambda x: math.log(x) if x is not None and x > 0 else None)
con.create_function("EXP", 1, lambda x: math.exp(x) if x is not None else None)


def fmt_pct(valor):
    """Formata percentual no padrão brasileiro com 1 casa (ex: 44,7)."""
    return f"{valor:.1f}".replace(".", ",")


def grafico_1_top_subitens():
    """Gráfico 1: Barras horizontais dos subitens com maior alta acumulada vs Salário Mínimo."""
    query = """
    WITH subitens AS (
        SELECT 
            nome_categoria,
            ROUND(AVG(peso_mensal), 4) AS peso_medio,
            ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct
        FROM ipca
        WHERE nivel = 'subitem'
          AND variacao_mensal IS NOT NULL
          AND (1.0 + (variacao_mensal / 100.0)) > 0
        GROUP BY codigo_hierarquico, nome_categoria
    )
    SELECT nome_categoria, inflacao_acumulada_pct, peso_medio
    FROM subitens
    ORDER BY inflacao_acumulada_pct DESC
    LIMIT 10;
    """
    df = pd.read_sql_query(query, con).sort_values("inflacao_acumulada_pct", ascending=True)
    
    # Reajuste do SM calculado a partir do banco (primeiro e ultimo mes)
    df_sm_g1 = pd.read_sql_query("SELECT valor FROM salario_minimo ORDER BY data;", con)
    sm_pct = (df_sm_g1["valor"].iloc[-1] / df_sm_g1["valor"].iloc[0] - 1.0) * 100.0
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    
    bars = ax.barh(df["nome_categoria"], df["inflacao_acumulada_pct"], color="#E11D48", height=0.65, zorder=3)
    
    # Linha vertical do Salário Mínimo
    ax.axvline(x=sm_pct, color="#1E3A8A", linestyle="--", linewidth=2.0, zorder=4)
    # Rótulo abaixo da última barra, para não cobrir nenhum dado
    ax.text(sm_pct + 4, -0.95, f"Reajuste Salário Mínimo (+{fmt_pct(sm_pct)}%)", color="#1E3A8A", 
            fontweight="bold", fontsize=10, va="center")
    ax.set_ylim(-1.4, len(df) - 0.4)
    
    # Rótulos nas barras
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 4, bar.get_y() + bar.get_height() / 2, f"+{w:.1f}%", 
                va="center", ha="left", fontsize=9.5, fontweight="bold", color="#1E293B")
        
    ax.set_title("Café e Hortifrúti Subiram Muito Acima do Salário Mínimo (Top 10 Subitens)", 
                 fontsize=13, fontweight="bold", pad=18, color="#0F172A", loc="left")
    ax.set_xlabel("Inflação Acumulada Composta (2020 a 2026) (%)", fontsize=10, color="#475569", labelpad=10)
    ax.set_xlim(0, max(df["inflacao_acumulada_pct"]) * 1.15)
    ax.grid(axis="x", linestyle=":", alpha=0.6, color="#94A3B8")
    ax.grid(axis="y", visible=False)
    
    plt.tight_layout()
    caminho = os.path.join(PASTA_DOCS, "top10_subitens_vs_salario_minimo.png")
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f" -> Gráfico 1 salvo: {caminho}")


def grafico_2_evolucao_temporal():
    """Gráfico 2: Evolução Acumulada IPCA vs INPC vs Salário Mínimo."""
    query_ipca = "SELECT data, variacao_mensal FROM ipca WHERE nivel = 'indice_geral' ORDER BY data;"
    query_inpc = "SELECT data, variacao_mensal FROM inpc WHERE nivel = 'indice_geral' ORDER BY data;"
    query_sm = "SELECT data, valor FROM salario_minimo ORDER BY data;"
    
    df_ipca = pd.read_sql_query(query_ipca, con)
    df_inpc = pd.read_sql_query(query_inpc, con)
    df_sm = pd.read_sql_query(query_sm, con)
    
    df_evol = pd.merge(df_ipca, df_inpc, on="data", suffixes=("_ipca", "_inpc"))
    df_evol = pd.merge(df_evol, df_sm, on="data", how="left")
    df_evol["data"] = pd.to_datetime(df_evol["data"])
    
    df_evol["ipca_acum"] = ((1.0 + df_evol["variacao_mensal_ipca"] / 100.0).cumprod() - 1.0) * 100.0
    df_evol["inpc_acum"] = ((1.0 + df_evol["variacao_mensal_inpc"] / 100.0).cumprod() - 1.0) * 100.0
    df_evol["sm_acum"] = ((df_evol["valor"] / df_evol["valor"].iloc[0]) - 1.0) * 100.0
    
    # Valores finais calculados dos dados (evita numeros digitados a mao na legenda)
    fim_sm = df_evol["sm_acum"].iloc[-1]
    fim_inpc = df_evol["inpc_acum"].iloc[-1]
    fim_ipca = df_evol["ipca_acum"].iloc[-1]
    
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)
    
    ax.plot(df_evol["data"], df_evol["sm_acum"], label=f"Salário Mínimo (+{fmt_pct(fim_sm)}%)", color="#2563EB", linewidth=2.5, linestyle="--", drawstyle="steps-post")
    ax.plot(df_evol["data"], df_evol["inpc_acum"], label=f"INPC - Baixa Renda (+{fmt_pct(fim_inpc)}%)", color="#D97706", linewidth=2.2)
    ax.plot(df_evol["data"], df_evol["ipca_acum"], label=f"IPCA - Geral (+{fmt_pct(fim_ipca)}%)", color="#0F172A", linewidth=2.0)
    
    ax.set_title("Trajetória Acumulada: Reajustes Salariais vs Inflação Oficial (2020-2026)", 
                 fontsize=13, fontweight="bold", pad=18, color="#0F172A", loc="left")
    ax.set_ylabel("Variação Acumulada Composta (%)", fontsize=10, color="#475569")
    ax.grid(True, linestyle=":", alpha=0.6, color="#94A3B8")
    ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=9.5)
    
    plt.tight_layout()
    caminho = os.path.join(PASTA_DOCS, "ipca_vs_inpc_tempo.png")
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f" -> Gráfico 2 salvo: {caminho}")


def grafico_3_pesos_orcamento():
    """Gráfico 3: Comparação de Pesos dos Grupos no Orçamento (IPCA vs INPC)."""
    query = """
    SELECT 
        ipca.nome_categoria,
        ROUND(AVG(ipca.peso_mensal), 2) AS peso_ipca,
        ROUND(AVG(inpc.peso_mensal), 2) AS peso_inpc
    FROM ipca
    JOIN inpc 
      ON ipca.data = inpc.data 
     AND ipca.codigo_hierarquico = inpc.codigo_hierarquico
    WHERE ipca.nivel = 'grupo'
    GROUP BY ipca.nome_categoria
    ORDER BY peso_inpc ASC;
    """
    df = pd.read_sql_query(query, con)
    
    y = np.arange(len(df))
    height = 0.38
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    
    rects1 = ax.barh(y + height/2, df["peso_inpc"], height, label="INPC (Baixa Renda, 1 a 5 SM)", color="#D97706")
    rects2 = ax.barh(y - height/2, df["peso_ipca"], height, label="IPCA (População Geral, 1 a 40 SM)", color="#1E293B")
    
    ax.set_yticks(y)
    ax.set_yticklabels(df["nome_categoria"], fontsize=10)
    ax.set_title("Alimentos e Habitação Consomem 41,5% do Orçamento na Baixa Renda (INPC) vs 36,6% no IPCA", 
                 fontsize=12, fontweight="bold", pad=18, color="#0F172A", loc="left")
    ax.set_xlabel("Peso Médio no Orçamento Familiar (%)", fontsize=10, color="#475569")
    ax.grid(axis="x", linestyle=":", alpha=0.6, color="#94A3B8")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=9.5)
    
    # Adiciona rótulos de dados
    for r in rects1:
        w = r.get_width()
        ax.text(w + 0.3, r.get_y() + r.get_height()/2, f"{w:.1f}%", va="center", fontsize=8.5, color="#D97706", fontweight="bold")
    for r in rects2:
        w = r.get_width()
        ax.text(w + 0.3, r.get_y() + r.get_height()/2, f"{w:.1f}%", va="center", fontsize=8.5, color="#1E293B", fontweight="bold")
        
    ax.set_xlim(0, max(df["peso_inpc"].max(), df["peso_ipca"].max()) * 1.15)
    
    plt.tight_layout()
    caminho = os.path.join(PASTA_DOCS, "peso_grupos_orcamento.png")
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f" -> Gráfico 3 salvo: {caminho}")


if __name__ == "__main__":
    print("\nRenderizando gráficos de alta resolução em docs/...")
    grafico_1_top_subitens()
    grafico_2_evolucao_temporal()
    grafico_3_pesos_orcamento()
    con.close()
    print("Gráficos gerados com sucesso!")
