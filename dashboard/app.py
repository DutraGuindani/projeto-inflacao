import math
import os
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Inflação e Poder de Compra no Brasil",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-color);
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: var(--text-color);
        opacity: 0.75;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
        padding: 1rem 1.2rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--text-color);
    }
    .metric-label {
        font-size: 0.8rem;
        color: var(--text-color);
        opacity: 0.7;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-sub {
        font-size: 0.85rem;
        color: var(--text-color);
        opacity: 0.75;
        margin-top: 0.2rem;
    }
    .callout {
        background-color: var(--secondary-background-color);
        border-left: 4px solid #3b82f6;
        padding: 0.8rem 1rem;
        border-radius: 0 6px 6px 0;
        margin-bottom: 1.5rem;
        font-size: 0.95rem;
        color: var(--text-color);
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "inflacao_brasil.db")


def conectar():
    """Abre o SQLite e registra LN e EXP em Python.
    Nem todo SQLite (principalmente no Windows) traz funcoes matematicas nativas;
    registrando aqui, as consultas com EXP(SUM(LN(...))) funcionam em qualquer ambiente."""
    con = sqlite3.connect(DB_PATH)
    con.create_function("LN", 1, lambda x: math.log(x) if x is not None and x > 0 else None)
    con.create_function("EXP", 1, lambda x: math.exp(x) if x is not None else None)
    return con


@st.cache_data(ttl=3600)
def carregar_dados_iniciais():
    if not os.path.exists(DB_PATH):
        st.error(f"Banco de dados não encontrado em {DB_PATH}.")
        st.stop()
        
    con = conectar()
    
    df_sm = pd.read_sql_query("SELECT data, ano_mes, valor FROM salario_minimo ORDER BY data;", con)
    df_sm["data"] = pd.to_datetime(df_sm["data"])
    
    datas = pd.read_sql_query("SELECT DISTINCT data FROM ipca ORDER BY data;", con)["data"].tolist()
    datas = [pd.to_datetime(d) for d in datas]
    
    query_pesos = """
    SELECT 
        ipca.codigo_hierarquico,
        ipca.nome_categoria,
        ROUND(AVG(ipca.peso_mensal), 2) AS peso_ipca,
        ROUND(AVG(inpc.peso_mensal), 2) AS peso_inpc
    FROM ipca
    JOIN inpc 
      ON ipca.data = inpc.data 
     AND ipca.codigo_hierarquico = inpc.codigo_hierarquico
    WHERE ipca.nivel = 'grupo'
    GROUP BY ipca.codigo_hierarquico, ipca.nome_categoria
    ORDER BY peso_inpc DESC;
    """
    df_pesos = pd.read_sql_query(query_pesos, con)
    con.close()
    
    return df_sm, datas, df_pesos


df_sm_completo, datas_disponiveis, df_pesos_grupos = carregar_dados_iniciais()

# Sidebar
st.sidebar.title("Filtros")

periodo = st.sidebar.select_slider(
    "Intervalo de análise:",
    options=datas_disponiveis,
    value=(min(datas_disponiveis), max(datas_disponiveis)),
    format_func=lambda d: d.strftime("%m/%Y")
)

dt_inicio, dt_fim = periodo
str_inicio = dt_inicio.strftime("%Y-%m-%d")
str_fim = dt_fim.strftime("%Y-%m-%d")

top_n = st.sidebar.slider("Subitens no ranking:", min_value=5, max_value=25, value=10, step=5)

st.sidebar.markdown("---")
st.sidebar.caption("Fontes: IBGE (IPCA/INPC) e Banco Central (SGS 1619).")


@st.cache_data
def carregar_metricas(d_ini: str, d_fim: str, n_itens: int):
    con = conectar()
    
    # Salário mínimo no intervalo
    query_sm = f"""
    SELECT 
        (SELECT valor FROM salario_minimo WHERE data <= '{d_ini}' ORDER BY data DESC LIMIT 1) AS sm_ini,
        (SELECT valor FROM salario_minimo WHERE data <= '{d_fim}' ORDER BY data DESC LIMIT 1) AS sm_fim;
    """
    res_sm = pd.read_sql_query(query_sm, con).iloc[0]
    sm_ini = float(res_sm["sm_ini"])
    sm_fim = float(res_sm["sm_fim"])
    reajuste_sm_exato = ((sm_fim / sm_ini) - 1.0) * 100.0
    reajuste_sm_pct = round(reajuste_sm_exato, 2)
    
    # Acumulados gerais
    query_acum = f"""
    SELECT 
        'IPCA' AS indicador,
        ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct
    FROM ipca
    WHERE nivel = 'indice_geral'
      AND data >= '{d_ini}' AND data <= '{d_fim}'
      AND variacao_mensal IS NOT NULL
      AND (1.0 + (variacao_mensal / 100.0)) > 0
    UNION ALL
    SELECT 
        'INPC' AS indicador,
        ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct
    FROM inpc
    WHERE nivel = 'indice_geral'
      AND data >= '{d_ini}' AND data <= '{d_fim}'
      AND variacao_mensal IS NOT NULL
      AND (1.0 + (variacao_mensal / 100.0)) > 0;
    """
    df_acum = pd.read_sql_query(query_acum, con)
    ipca_acum = float(df_acum[df_acum["indicador"] == "IPCA"]["inflacao_acumulada_pct"].values[0])
    inpc_acum = float(df_acum[df_acum["indicador"] == "INPC"]["inflacao_acumulada_pct"].values[0])
    
    # Ranking
    query_sub = f"""
    WITH subitens AS (
        SELECT 
            nome_categoria,
            ROUND(AVG(peso_mensal), 4) AS peso_medio,
            ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS inflacao_acumulada_pct
        FROM ipca
        WHERE nivel = 'subitem'
          AND data >= '{d_ini}' AND data <= '{d_fim}'
          AND variacao_mensal IS NOT NULL
          AND (1.0 + (variacao_mensal / 100.0)) > 0
        GROUP BY codigo_hierarquico, nome_categoria
    )
    SELECT nome_categoria, inflacao_acumulada_pct, peso_medio
    FROM subitens
    ORDER BY inflacao_acumulada_pct DESC
    LIMIT {n_itens};
    """
    df_sub = pd.read_sql_query(query_sub, con)
    
    # Contagem de subitens acima do salário
    query_acima = f"""
    WITH subitens AS (
        SELECT 
            codigo_hierarquico,
            (EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0 AS inflacao_acumulada_pct
        FROM ipca
        WHERE nivel = 'subitem'
          AND data >= '{d_ini}' AND data <= '{d_fim}'
          AND variacao_mensal IS NOT NULL
          AND (1.0 + (variacao_mensal / 100.0)) > 0
        GROUP BY codigo_hierarquico
    )
    SELECT 
        COUNT(*) AS total,
        SUM(CASE WHEN inflacao_acumulada_pct > {reajuste_sm_exato} THEN 1 ELSE 0 END) AS acima
    FROM subitens;
    """
    res_acima = pd.read_sql_query(query_acima, con).iloc[0]
    total_sub = int(res_acima["total"])
    acima_sub = int(res_acima["acima"])
    
    # Séries temporais mensais
    q_s_ipca = f"SELECT data, variacao_mensal FROM ipca WHERE nivel = 'indice_geral' AND data >= '{d_ini}' AND data <= '{d_fim}' ORDER BY data;"
    q_s_inpc = f"SELECT data, variacao_mensal FROM inpc WHERE nivel = 'indice_geral' AND data >= '{d_ini}' AND data <= '{d_fim}' ORDER BY data;"
    
    df_si = pd.read_sql_query(q_s_ipca, con)
    df_sn = pd.read_sql_query(q_s_inpc, con)
    con.close()
    
    df_evol = pd.merge(df_si, df_sn, on="data", suffixes=("_ipca", "_inpc"))
    df_evol["data"] = pd.to_datetime(df_evol["data"])
    df_evol["ipca_acum"] = ((1.0 + df_evol["variacao_mensal_ipca"] / 100.0).cumprod() - 1.0) * 100.0
    df_evol["inpc_acum"] = ((1.0 + df_evol["variacao_mensal_inpc"] / 100.0).cumprod() - 1.0) * 100.0
    
    df_evol = pd.merge(df_evol, df_sm_completo[["data", "valor"]], on="data", how="left")
    base_sm = df_evol["valor"].iloc[0]
    df_evol["sm_acum"] = ((df_evol["valor"] / base_sm) - 1.0) * 100.0
    
    return {
        "sm_ini": sm_ini,
        "sm_fim": sm_fim,
        "reajuste_sm_pct": reajuste_sm_pct,
        "ipca_acum": ipca_acum,
        "inpc_acum": inpc_acum,
        "df_sub": df_sub,
        "total_sub": total_sub,
        "acima_sub": acima_sub,
        "df_evol": df_evol
    }


dados = carregar_metricas(str_inicio, str_fim, top_n)

# Header
st.markdown("<div class='main-title'>Inflação e Poder de Compra no Brasil</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='sub-title'>Análise empírica de {dt_inicio.strftime('%b/%Y')} a {dt_fim.strftime('%b/%Y')} baseada no IPCA, INPC e Salário Mínimo</div>",
    unsafe_allow_html=True
)

pct_acima = round((dados["acima_sub"] / dados["total_sub"]) * 100, 1)

# Ganho (ou perda) real do salário mínimo frente ao IPCA geral no intervalo
ganho_real = ((1 + dados["reajuste_sm_pct"] / 100) / (1 + dados["ipca_acum"] / 100) - 1) * 100
if ganho_real >= 0:
    texto_real = f"um ganho real de <b>{ganho_real:+.1f}%</b> frente ao IPCA geral (<b>+{dados['ipca_acum']}%</b>)"
else:
    texto_real = f"uma perda real de <b>{ganho_real:.1f}%</b> frente ao IPCA geral (<b>+{dados['ipca_acum']}%</b>)"

st.markdown(f"""
<div class='callout'>
    O Salário Mínimo teve reajuste nominal de <b>+{dados['reajuste_sm_pct']}%</b> (de R$ {dados['sm_ini']:,.2f} para R$ {dados['sm_fim']:,.2f}), 
    {texto_real}. Ao mesmo tempo, <b>{dados['acima_sub']} dos {dados['total_sub']} subitens avaliados ({pct_acima}%)</b> 
    registraram inflação superior ao reajuste do salário mínimo.
</div>
""", unsafe_allow_html=True)

# KPI Cards
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Salário Mínimo</div>
        <div class='metric-value' style='color: #2563eb;'>+{dados['reajuste_sm_pct']}%</div>
        <div class='metric-sub'>De R$ {dados['sm_ini']:.0f} para R$ {dados['sm_fim']:.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>IPCA Acumulado</div>
        <div class='metric-value'>+{dados['ipca_acum']}%</div>
        <div class='metric-sub'>População geral (1 a 40 SM)</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>INPC Acumulado</div>
        <div class='metric-value' style='color: #d97706;'>+{dados['inpc_acum']}%</div>
        <div class='metric-sub'>Menor renda (1 a 5 SM)</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    maior_item = dados['df_sub']['nome_categoria'].iloc[0]
    maior_alta = dados['df_sub']['inflacao_acumulada_pct'].iloc[0]
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Maior alta da cesta</div>
        <div class='metric-value' style='color: #dc2626;'>+{maior_alta}%</div>
        <div class='metric-sub'>{maior_item}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Gráfico 1: Barras horizontais
st.markdown(f"### Subitens com maior alta acumulada vs Salário Mínimo (+{dados['reajuste_sm_pct']}%)")
st.caption("A linha vertical tracejada representa o percentual de reajuste do salário mínimo no intervalo selecionado.")

df_chart_sub = dados["df_sub"].sort_values("inflacao_acumulada_pct", ascending=True).copy()
cores = ["#dc2626" if val > dados["reajuste_sm_pct"] else "#64748b" for val in df_chart_sub["inflacao_acumulada_pct"]]

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    y=df_chart_sub["nome_categoria"],
    x=df_chart_sub["inflacao_acumulada_pct"],
    orientation="h",
    marker=dict(color=cores),
    text=[f"+{v:.1f}%" for v in df_chart_sub["inflacao_acumulada_pct"]],
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>Alta: +%{x:.2f}%<br>Peso médio: %{customdata:.2f}%<extra></extra>",
    customdata=df_chart_sub["peso_medio"]
))

fig_bar.add_vline(
    x=dados["reajuste_sm_pct"],
    line_width=2,
    line_dash="dash",
    line_color="#3b82f6",
    annotation_text=f"Salário Mínimo (+{dados['reajuste_sm_pct']}%)",
    annotation_position="bottom right",
    annotation_font=dict(size=11, color="#3b82f6")
)

fig_bar.update_layout(
    xaxis_title="Variação Composta Acumulada (%)",
    yaxis_title="",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=460,
    margin=dict(l=10, r=40, t=10, b=40),
    xaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.2)")
)
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

col_l, col_r = st.columns(2)

with col_l:
    st.markdown("### Trajetória temporal: IPCA vs INPC vs Salário Mínimo")
    st.caption("Evolução composta mensal da inflação acumulada e do salário mínimo nominal. "
               "O salário mínimo usa como base o valor do primeiro mês do intervalo, e a inflação já inclui a variação desse mês.")
    
    df_evol = dados["df_evol"]
    fig_line = go.Figure()
    
    fig_line.add_trace(go.Scatter(
        x=df_evol["data"], y=df_evol["sm_acum"],
        mode="lines", name="Salário Mínimo",
        line=dict(color="#3b82f6", width=2.5, dash="dash", shape="hv")
    ))
    fig_line.add_trace(go.Scatter(
        x=df_evol["data"], y=df_evol["inpc_acum"],
        mode="lines", name="INPC (1 a 5 SM)",
        line=dict(color="#f59e0b", width=2.2)
    ))
    fig_line.add_trace(go.Scatter(
        x=df_evol["data"], y=df_evol["ipca_acum"],
        mode="lines", name="IPCA (1 a 40 SM)",
        line=dict(color="#38bdf8", width=2)
    ))
    
    fig_line.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=10, r=10, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.2)"),
        yaxis=dict(title="Variação acumulada (%)", showgrid=True, gridcolor="rgba(128, 128, 128, 0.2)")
    )
    st.plotly_chart(fig_line, use_container_width=True)

with col_r:
    st.markdown("### Peso de cada grupo no orçamento: IPCA vs INPC")
    st.caption("Comparação da proporção média gasta por famílias de menor renda (INPC) e da média nacional (IPCA).")
    
    df_p_sorted = df_pesos_grupos.sort_values("peso_inpc", ascending=True)
    fig_grp = go.Figure()
    
    fig_grp.add_trace(go.Bar(
        y=df_p_sorted["nome_categoria"], x=df_p_sorted["peso_inpc"],
        name="INPC (1 a 5 SM)", orientation="h",
        marker_color="#f59e0b", text=[f"{v:.1f}%" for v in df_p_sorted["peso_inpc"]],
        textposition="inside"
    ))
    fig_grp.add_trace(go.Bar(
        y=df_p_sorted["nome_categoria"], x=df_p_sorted["peso_ipca"],
        name="IPCA (1 a 40 SM)", orientation="h",
        marker_color="#38bdf8", text=[f"{v:.1f}%" for v in df_p_sorted["peso_ipca"]],
        textposition="inside"
    ))
    
    fig_grp.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=10, r=10, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Participação no orçamento (%)", showgrid=True, gridcolor="rgba(128, 128, 128, 0.2)"),
        yaxis=dict(title="")
    )
    st.plotly_chart(fig_grp, use_container_width=True)

# Tabela interativa
st.markdown("---")
st.markdown("### Consulta de itens específicos")
termo = st.text_input("Filtrar por nome de produto ou serviço (ex: arroz, óleo, gás, energia, aluguel):")

con = conectar()
query_busca = f"""
SELECT 
    nome_categoria AS "Item / Serviço",
    ROUND(AVG(peso_mensal), 4) AS "Peso médio (%)",
    ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0, 2) AS "Inflação acumulada (%)",
    ROUND((EXP(SUM(LN(1.0 + (variacao_mensal / 100.0)))) - 1.0) * 100.0 - {dados['reajuste_sm_pct']}, 2) AS "Diferença vs Salário Mínimo (pp)"
FROM ipca
WHERE nivel = 'subitem'
  AND data >= '{str_inicio}' AND data <= '{str_fim}'
  AND variacao_mensal IS NOT NULL
  AND (1.0 + (variacao_mensal / 100.0)) > 0
  AND LOWER(nome_categoria) LIKE ?
GROUP BY codigo_hierarquico, nome_categoria
ORDER BY "Inflação acumulada (%)" DESC;
"""
# Termo digitado vai como parâmetro (evita erro com aspas e SQL injection)
df_busca = pd.read_sql_query(query_busca, con, params=[f"%{termo.lower().strip()}%"])
con.close()

st.dataframe(df_busca, use_container_width=True, height=220)
