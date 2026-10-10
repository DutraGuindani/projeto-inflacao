"""
Limpeza, estruturação e classificação hierárquica dos dados do IPCA, INPC e Salário Mínimo.
"""

import json
import os
import re
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
RAW_DIR = os.path.join(PROJECT_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_DIR, "data", "processed")

os.makedirs(PROCESSED_DIR, exist_ok=True)


def identificar_hierarquia(texto_categoria: str, codigo_ibge: str):
    """
    Classifica o nível hierárquico pelo padrão de código do IBGE:
    - Índice geral / 7169 -> indice_geral
    - 1 dígito (ex: 1.Alimentação e bebidas) -> grupo
    - 2 dígitos (ex: 11.Alimentação no domicílio) -> subgrupo
    - 4 dígitos (ex: 1101.Cereais...) -> item
    - 7 dígitos (ex: 1101001.Arroz) -> subitem
    """
    texto = str(texto_categoria).strip()
    
    if "ndice geral" in texto or codigo_ibge == "7169":
        return "indice_geral", "0", "Índice Geral"
        
    match = re.match(r"^(\d+)\.(.+)$", texto)
    if match:
        codigo = match.group(1).strip()
        nome = match.group(2).strip()
        tam = len(codigo)
        
        if tam == 1:
            nivel = "grupo"
        elif tam == 2:
            nivel = "subgrupo"
        elif tam == 4:
            nivel = "item"
        elif tam >= 5:
            nivel = "subitem"
        else:
            nivel = "outro"
            
        return nivel, codigo, nome
        
    return "outro", str(codigo_ibge), texto


def tratar_salario_minimo() -> pd.DataFrame:
    caminho = os.path.join(RAW_DIR, "salario_minimo_raw.json")
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)
        
    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.to_period("M").dt.to_timestamp()
    df["ano_mes"] = df["data"].dt.strftime("%Y%m")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    
    df = df.sort_values("data").drop_duplicates(subset=["ano_mes"], keep="last").reset_index(drop=True)
    
    df.to_csv(os.path.join(PROCESSED_DIR, "salario_minimo_tratado.csv"), index=False, encoding="utf-8")
    df.to_parquet(os.path.join(PROCESSED_DIR, "salario_minimo_tratado.parquet"), index=False)
    print(f"Salario minimo tratado: {len(df)} registros.")
    return df


def tratar_indicador(nome: str) -> pd.DataFrame:
    caminho = os.path.join(RAW_DIR, f"{nome.lower()}_raw.csv")
    df = pd.read_csv(caminho, dtype=str, low_memory=False)
    
    # Filtra linhas válidas de datas (formato YYYYMM)
    df = df[df["D2C"].str.match(r"^\d{6}$", na=False)].copy()
    
    # Mapeamento de variáveis conforme a tabela do SIDRA
    if nome.lower() == "ipca":
        mapa = {"63": "variacao_mensal", "66": "peso_mensal", "2265": "acumulada_12m"}
    else:
        mapa = {"44": "variacao_mensal", "45": "peso_mensal", "2292": "acumulada_12m"}
        
    df["variavel"] = df["D3C"].map(mapa)
    df = df[df["variavel"].notna()].copy()
    
    # IBGE usa '..', '-', '...' para valores não disponíveis
    df["valor"] = pd.to_numeric(df["V"], errors="coerce")
    
    hierarquia = [identificar_hierarquia(cat, cod) for cat, cod in zip(df["D4N"], df["D4C"])]
    df["nivel"] = [h[0] for h in hierarquia]
    df["codigo_hierarquico"] = [h[1] for h in hierarquia]
    df["nome_categoria"] = [h[2] for h in hierarquia]
    df["codigo_ibge"] = df["D4C"]
    df["ano_mes"] = df["D2C"]
    df["data"] = pd.to_datetime(df["D2C"], format="%Y%m")
    
    # Pivota as 3 variáveis em colunas separadas
    chaves = ["data", "ano_mes", "codigo_ibge", "codigo_hierarquico", "nome_categoria", "nivel"]
    pivoted = df.pivot_table(index=chaves, columns="variavel", values="valor", aggfunc="first").reset_index()
    
    for col in ["variacao_mensal", "peso_mensal", "acumulada_12m"]:
        if col not in pivoted.columns:
            pivoted[col] = np.nan
            
    pivoted = pivoted.sort_values(["data", "codigo_hierarquico"]).reset_index(drop=True)
    
    pivoted.to_csv(os.path.join(PROCESSED_DIR, f"{nome.lower()}_tratado.csv"), index=False, encoding="utf-8")
    pivoted.to_parquet(os.path.join(PROCESSED_DIR, f"{nome.lower()}_tratado.parquet"), index=False)
    print(f"{nome.upper()} tratado: {len(pivoted)} registros.")
    return pivoted


def executar():
    tratar_salario_minimo()
    tratar_indicador("ipca")
    tratar_indicador("inpc")


if __name__ == "__main__":
    executar()
