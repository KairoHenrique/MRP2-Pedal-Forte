"""Exportacao de relatorios em CSV (RF14)."""

import csv
from pathlib import Path

import estoque
import persistencia
import utils


def exportar_estoque_csv(dados, caminho=None):
    """Exporta a posicao atual de estoque para um arquivo CSV."""
    persistencia.garantir_diretorios()
    destino = (
        Path(caminho)
        if caminho
        else persistencia.DOCS_DIR / "posicao_estoque.csv"
    )
    colunas = [
        "codigo",
        "tipo",
        "descricao",
        "unidade",
        "saldo_atual",
        "estoque_seguranca",
        "situacao",
    ]
    itens = sorted(dados["itens"].values(), key=lambda i: i["codigo"])
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        for item in itens:
            cod = item["codigo"]
            saldo = estoque.obter_saldo(dados, cod)
            es = float(item["estoque_seguranca"])
            situacao = "ABAIXO_ES" if saldo < es else "OK"
            escritor.writerow(
                {
                    "codigo": cod,
                    "tipo": item["tipo"],
                    "descricao": item["descricao"],
                    "unidade": item["unidade"],
                    "saldo_atual": saldo,
                    "estoque_seguranca": es,
                    "situacao": situacao,
                }
            )
    return destino


def exportar_ordens_csv(dados, caminho=None):
    """Exporta a lista de ordens de producao e compra para CSV."""
    persistencia.garantir_diretorios()
    destino = (
        Path(caminho)
        if caminho
        else persistencia.DOCS_DIR / "ordens.csv"
    )
    colunas = [
        "numero",
        "tipo",
        "item",
        "descricao",
        "quantidade",
        "semana_liberacao",
        "semana_entrega",
        "status",
        "data_criacao",
    ]
    ordens = sorted(
        dados["ordens"].values(),
        key=lambda o: (o["semana_entrega"], o["numero"]),
    )
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        for ordem in ordens:
            desc = dados["itens"].get(ordem["item"], {}).get("descricao", "")
            escritor.writerow(
                {
                    "numero": ordem["numero"],
                    "tipo": ordem["tipo"],
                    "item": ordem["item"],
                    "descricao": desc,
                    "quantidade": ordem["quantidade"],
                    "semana_liberacao": ordem["semana_liberacao"],
                    "semana_entrega": ordem["semana_entrega"],
                    "status": ordem["status"],
                    "data_criacao": ordem.get("data_criacao", ""),
                }
            )
    return destino


def menu_relatorios(dados):
    """Submenu de exportacao de relatorios em CSV."""
    while True:
        utils.imprimir_cabecalho("RELATORIOS (EXPORTAR CSV)")
        print("1. Exportar posicao de estoque (CSV)")
        print("2. Exportar lista de ordens (CSV)")
        print("3. Exportar ambos os relatorios")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            arq = exportar_estoque_csv(dados)
            print(f"\nPosicao de estoque exportada para:\n  {arq}")
            utils.pausar()
        elif opcao == "2":
            arq = exportar_ordens_csv(dados)
            print(f"\nLista de ordens exportada para:\n  {arq}")
            utils.pausar()
        elif opcao == "3":
            arq1 = exportar_estoque_csv(dados)
            arq2 = exportar_ordens_csv(dados)
            print("\nRelatorios exportados com sucesso:")
            print(f"  - {arq1}")
            print(f"  - {arq2}")
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")

