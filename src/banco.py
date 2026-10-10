"""
Criação do banco de dados SQLite e carga das tabelas tratadas.
"""

import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
PROCESSED_DIR = os.path.join(PROJECT_DIR, "data", "processed")
DB_PATH = os.path.join(PROJECT_DIR, "data", "inflacao_brasil.db")


def criar_tabelas(con: sqlite3.Connection):
    cur = con.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS salario_minimo (
        data TEXT NOT NULL,
        ano_mes TEXT PRIMARY KEY,
        valor REAL NOT NULL
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ipca (
        data TEXT NOT NULL,
        ano_mes TEXT NOT NULL,
        codigo_ibge TEXT NOT NULL,
        codigo_hierarquico TEXT NOT NULL,
        nome_categoria TEXT NOT NULL,
        nivel TEXT NOT NULL,
        variacao_mensal REAL,
        peso_mensal REAL,
        acumulada_12m REAL,
        PRIMARY KEY (ano_mes, codigo_ibge)
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inpc (
        data TEXT NOT NULL,
        ano_mes TEXT NOT NULL,
        codigo_ibge TEXT NOT NULL,
        codigo_hierarquico TEXT NOT NULL,
        nome_categoria TEXT NOT NULL,
        nivel TEXT NOT NULL,
        variacao_mensal REAL,
        peso_mensal REAL,
        acumulada_12m REAL,
        PRIMARY KEY (ano_mes, codigo_ibge)
    );
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ipca_nivel_data ON ipca(nivel, data);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ipca_categoria ON ipca(codigo_hierarquico, nivel);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inpc_nivel_data ON inpc(nivel, data);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inpc_categoria ON inpc(codigo_hierarquico, nivel);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sm_data ON salario_minimo(data);")
    con.commit()


def carregar_dados(con: sqlite3.Connection):
    df_sm = pd.read_parquet(os.path.join(PROCESSED_DIR, "salario_minimo_tratado.parquet"))
    df_sm["data"] = df_sm["data"].dt.strftime("%Y-%m-%d")
    df_sm[["data", "ano_mes", "valor"]].to_sql("salario_minimo", con, if_exists="replace", index=False)
    
    df_ipca = pd.read_parquet(os.path.join(PROCESSED_DIR, "ipca_tratado.parquet"))
    df_ipca["data"] = df_ipca["data"].dt.strftime("%Y-%m-%d")
    df_ipca.to_sql("ipca", con, if_exists="replace", index=False)
    
    df_inpc = pd.read_parquet(os.path.join(PROCESSED_DIR, "inpc_tratado.parquet"))
    df_inpc["data"] = df_inpc["data"].dt.strftime("%Y-%m-%d")
    df_inpc.to_sql("inpc", con, if_exists="replace", index=False)
    
    # Recria índices após replace
    cur = con.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ipca_nivel_data ON ipca(nivel, data);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ipca_categoria ON ipca(codigo_hierarquico, nivel);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inpc_nivel_data ON inpc(nivel, data);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inpc_categoria ON inpc(codigo_hierarquico, nivel);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sm_data ON salario_minimo(data);")
    con.commit()


def executar():
    con = sqlite3.connect(DB_PATH)
    try:
        criar_tabelas(con)
        carregar_dados(con)
        
        cur = con.cursor()
        for tab in ["salario_minimo", "ipca", "inpc"]:
            cur.execute(f"SELECT COUNT(*) FROM {tab};")
            print(f"Tabela {tab}: {cur.fetchone()[0]:,} registros.")
    finally:
        con.close()


if __name__ == "__main__":
    executar()
