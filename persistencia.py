"""Camada de persistencia em JSON e CSV na pasta data/ (RF15, RNF07)."""

import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
GRAFICOS_DIR = DOCS_DIR / "graficos"

COLUNAS_MOVIMENTOS = [
    "data",
    "codigo",
    "tipo",
    "quantidade",
    "saldo_apos",
    "documento",
]


def garantir_diretorios():
    """Garante a existencia das pastas data/, docs/ e docs/graficos/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)


def carregar_json(nome_arquivo, padrao=None):
    """Carrega um arquivo JSON da pasta data/ ou retorna valor padrao."""
    garantir_diretorios()
    caminho = DATA_DIR / nome_arquivo
    if not caminho.exists():
        return {} if padrao is None else padrao
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"AVISO: falha ao ler '{caminho.name}': {exc}")
        return {} if padrao is None else padrao


def salvar_json(nome_arquivo, dados):
    """Salva um dicionario ou lista em JSON formatado na pasta data/."""
    garantir_diretorios()
    caminho = DATA_DIR / nome_arquivo
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def carregar_movimentos():
    """Carrega o historico de movimentacoes (kardex) de movimentos.csv."""
    garantir_diretorios()
    caminho = DATA_DIR / "movimentos.csv"
    if not caminho.exists():
        return []
    movimentos = []
    try:
        with caminho.open("r", encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            for linha in leitor:
                movimentos.append(
                    {
                        "data": linha["data"],
                        "codigo": linha["codigo"],
                        "tipo": linha["tipo"],
                        "quantidade": float(linha["quantidade"]),
                        "saldo_apos": float(linha["saldo_apos"]),
                        "documento": linha["documento"],
                    }
                )
    except (OSError, KeyError, ValueError) as exc:
        print(f"AVISO: falha ao ler 'movimentos.csv': {exc}")
    return movimentos


def salvar_movimentos(movimentos):
    """Grava toda a lista de movimentacoes em data/movimentos.csv."""
    garantir_diretorios()
    caminho = DATA_DIR / "movimentos.csv"
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_MOVIMENTOS)
        escritor.writeheader()
        for mov in movimentos:
            escritor.writerow(
                {
                    "data": mov["data"],
                    "codigo": mov["codigo"],
                    "tipo": mov["tipo"],
                    "quantidade": mov["quantidade"],
                    "saldo_apos": mov["saldo_apos"],
                    "documento": mov["documento"],
                }
            )


def carregar_todos_dados():
    """Carrega todos os arquivos da pasta data/ para memoria."""
    garantir_diretorios()
    dados = {
        "itens": carregar_json("itens.json", {}),
        "estrutura": carregar_json("estrutura.json", {}),
        "estoque": carregar_json("estoque.json", {}),
        "movimentos": carregar_movimentos(),
        "centros": carregar_json("centros.json", {}),
        "roteiros": carregar_json("roteiros.json", {}),
        "mps": carregar_json("mps.json", {}),
        "ordens": carregar_json("ordens.json", {}),
    }
    return dados


def salvar_todos_dados(dados):
    """Persiste todos os dados do sistema na pasta data/."""
    salvar_json("itens.json", dados["itens"])
    salvar_json("estrutura.json", dados["estrutura"])
    salvar_json("estoque.json", dados["estoque"])
    salvar_movimentos(dados["movimentos"])
    salvar_json("centros.json", dados["centros"])
    salvar_json("roteiros.json", dados["roteiros"])
    salvar_json("mps.json", dados["mps"])
    salvar_json("ordens.json", dados["ordens"])

