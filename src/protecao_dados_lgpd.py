"""Camada de Proteção de Dados (LGPD): leitura segura, amostragem e ocultação irreversível."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

import pandas as pd

SELO_PROTECAO_LGPD = "***PROTEGIDO_LGPD***"

PADRAO_COLUNA_SENSIVEL = re.compile(
    r"(cpf|cnpj|e[-_]?mail|nome_civil|nome_completo|pix|telefone|celular|whatsapp|rg|documento)",
    re.IGNORECASE,
)
PADRAO_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
PADRAO_CNPJ = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
PADRAO_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def ler_planilha(origem: Any, nome_arquivo: str | None = None) -> tuple[str, pd.DataFrame]:
    """Lê planilhas .xlsx ou .csv (detectando separador automaticamente) e retorna (nome, tabela)."""
    if isinstance(origem, (str, Path)):
        caminho = Path(origem)
        nome = nome_arquivo or caminho.name
        conteudo_bytes = caminho.read_bytes()
    else:
        nome = nome_arquivo or getattr(origem, "name", "planilha_sem_nome")
        if hasattr(origem, "seek"):
            origem.seek(0)
        conteudo_bytes = origem.read()
        if hasattr(origem, "seek"):
            origem.seek(0)

    extensao = Path(nome).suffix.lower()
    if extensao in (".xlsx", ".xls"):
        df = pd.read_excel(io.BytesIO(conteudo_bytes))
        return nome, df

    if extensao == ".csv":
        trecho = conteudo_bytes[:4096].decode("utf-8", errors="ignore")
        primeira_linha = trecho.splitlines()[0] if trecho.splitlines() else ""
        separador = ";" if primeira_linha.count(";") >= primeira_linha.count(",") else ","
        for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                df = pd.read_csv(io.BytesIO(conteudo_bytes), sep=separador, encoding=codificacao)
                return nome, df
            except UnicodeDecodeError:
                continue
        df = pd.read_csv(io.BytesIO(conteudo_bytes), sep=separador, encoding="latin-1", errors="replace")
        return nome, df

    raise ValueError(f"Formato não suportado para '{nome}'. Envie arquivos .xlsx ou .csv.")


def _coluna_possui_dados_pessoais(nome_col: str, serie: pd.Series) -> bool:
    """Identifica se uma coluna contém dados pessoais pelo nome ou pelo conteúdo."""
    if PADRAO_COLUNA_SENSIVEL.search(str(nome_col)):
        return True

    exemplos = serie.dropna().astype(str).head(5).tolist()
    for valor in exemplos:
        if PADRAO_CPF.search(valor) or PADRAO_CNPJ.search(valor) or PADRAO_EMAIL.search(valor):
            return True
    return False


def ocultar_dados_pessoais(df: pd.DataFrame, limite_linhas: int = 3) -> dict[str, Any]:
    """Extrai cabeçalhos e até 3 linhas aplicando ocultação irreversível de dados pessoais (LGPD)."""
    amostra = df.head(limite_linhas).copy()
    colunas_protegidas: list[str] = []

    for col in amostra.columns:
        if _coluna_possui_dados_pessoais(str(col), df[col]):
            colunas_protegidas.append(str(col))
            amostra[col] = SELO_PROTECAO_LGPD

    amostra_segura = []
    for _, linha in amostra.iterrows():
        registro = {}
        for col in amostra.columns:
            val = linha[col]
            if pd.isna(val):
                registro[str(col)] = None
            elif hasattr(val, "isoformat"):
                registro[str(col)] = val.isoformat()
            else:
                registro[str(col)] = str(val)
        amostra_segura.append(registro)

    return {
        "colunas": [str(c) for c in df.columns],
        "colunas_protegidas": colunas_protegidas,
        "amostra_protegida": amostra_segura,
        "total_linhas": int(len(df)),
    }


def preparar_pacote_seguro(arquivos: list[Any] | dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, pd.DataFrame]]:
    """Lê múltiplas planilhas, retorna amostras protegidas (para IA/tela) e tabelas completas (para cálculo)."""
    amostras: list[dict[str, Any]] = []
    tabelas_brutas: dict[str, pd.DataFrame] = {}

    itens = arquivos.items() if isinstance(arquivos, dict) else [(None, a) for a in arquivos]

    for dica_nome, fonte in itens:
        nome_arq, df = ler_planilha(
            fonte,
            nome_arquivo=dica_nome if isinstance(dica_nome, str) and "." in dica_nome else None,
        )
        tabelas_brutas[nome_arq] = df
        info_protecao = ocultar_dados_pessoais(df, limite_linhas=3)
        amostras.append({"arquivo": nome_arq, **info_protecao})

    return amostras, tabelas_brutas
