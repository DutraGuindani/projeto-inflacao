"""
Coleta de dados da API do Banco Central (SGS 1619) e do IBGE/SIDRA (Tabelas 7060 e 7063).

Para contornar o limite de 50.000 registros por chamada na API do SIDRA,
a extração é feita em blocos anuais e unificada localmente.
"""

import json
import os
import sys
import time
from datetime import datetime
import pandas as pd
import requests
import sidrapy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
RAW_DIR = os.path.join(PROJECT_DIR, "data", "raw")

os.makedirs(RAW_DIR, exist_ok=True)


def coletar_salario_minimo(data_inicial="01/01/2020") -> str:
    """Coleta a série do salário mínimo na API do Banco Central."""
    print("Coletando salario minimo no BCB (SGS 1619)...")
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.1619/dados?formato=json&dataInicial={data_inicial}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        res.raise_for_status()
        dados = res.json()
        
        caminho = os.path.join(RAW_DIR, "salario_minimo_raw.json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            
        print(f"Salario minimo coletado ({len(dados)} registros).")
        return caminho
    except Exception as e:
        print(f"Erro ao consultar API do BCB: {e}", file=sys.stderr)
        raise


def coletar_sidra_por_ano(tabela: str, variaveis: str, nome_arquivo: str) -> str:
    """
    Baixa tabelas do SIDRA particionando por ano para não exceder o limite de 50k registros.
    """
    ano_atual = datetime.now().year
    anos = list(range(2020, ano_atual + 1))
    dfs = []
    
    print(f"Baixando tabela {tabela} ({nome_arquivo}) do SIDRA...")
    
    for ano in anos:
        periodo = f"{ano}01-{ano}12"
        for tentativa in range(1, 4):
            try:
                df_temp = sidrapy.get_table(
                    table_code=tabela,
                    territorial_level="1",
                    ibge_territorial_code="all",
                    variable=variaveis,
                    period=periodo,
                    classification="315",
                    categories="all"
                )
                
                # O SIDRA retorna o nome das colunas na primeira linha.
                # Mantemos apenas no primeiro ano e descartamos nos seguintes.
                if len(dfs) == 0:
                    df_ano = df_temp
                else:
                    df_ano = df_temp.iloc[1:].copy()
                    
                dfs.append(df_ano)
                print(f" - Ano {ano}: {len(df_ano)} linhas.")
                break
            except Exception as e:
                if tentativa == 3:
                    print(f" - Ano {ano}: sem dados ou falha ({e}).")
                time.sleep(2)
                
    if not dfs:
        raise RuntimeError(f"Nenhum dado retornado para a tabela {tabela}")
        
    df_final = pd.concat(dfs, ignore_index=True)
    caminho = os.path.join(RAW_DIR, f"{nome_arquivo}_raw.csv")
    df_final.to_csv(caminho, index=False, encoding="utf-8")
    print(f"Tabela {tabela} salva em {caminho} ({len(df_final)} linhas).")
    return caminho


def executar():
    coletar_salario_minimo()
    # IPCA (63=mensal, 66=peso, 2265=acumulada 12m)
    coletar_sidra_por_ano("7060", "63,66,2265", "ipca")
    # INPC (44=mensal, 45=peso, 2292=acumulada 12m)
    coletar_sidra_por_ano("7063", "44,45,2292", "inpc")


if __name__ == "__main__":
    executar()
