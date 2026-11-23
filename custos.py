"""Calculo recursivo do custo padrao dos itens fabricados (RF13)."""

import utils


def calcular_custo_padrao(dados, codigo_item, visitados=None):
    """Calcula recursivamente o custo padrao (materiais + mao de obra).

    Args:
        dados: Dicionario completo de dados do sistema.
        codigo_item: Codigo do item a custear.
        visitados: Conjunto auxiliar de protecao contra ciclos.

    Returns:
        Dicionario com custo_materiais, custo_mao_obra, custo_total,
        linhas_componentes e info_mao_obra.
    """
    cod = utils.validar_codigo_item(codigo_item)
    if cod not in dados["itens"]:
        raise KeyError(f"Item '{cod}' nao encontrado.")

    if visitados is None:
        visitados = set()
    if cod in visitados:
        raise ValueError(f"Ciclo detectado na estrutura ao custear '{cod}'.")

    item = dados["itens"][cod]
    if item["tipo"] == "MP":
        custo_mp = float(item["custo_unitario"])
        return {
            "codigo": cod,
            "custo_materiais": custo_mp,
            "custo_mao_obra": 0.0,
            "custo_total": custo_mp,
            "linhas_componentes": [],
            "info_mao_obra": None,
        }

    visitados_ramo = visitados | {cod}
    linhas = []
    custo_materiais = 0.0

    for comp in dados["estrutura"].get(cod, []):
        cod_comp = comp["componente"]
        if cod_comp not in dados["itens"]:
            continue
        qtd = float(comp["quantidade"])
        res_comp = calcular_custo_padrao(dados, cod_comp, visitados_ramo)
        custo_un = res_comp["custo_total"]
        subtotal = qtd * custo_un
        custo_materiais += subtotal
        linhas.append(
            {
                "codigo": cod_comp,
                "descricao": dados["itens"][cod_comp]["descricao"],
                "unidade": dados["itens"][cod_comp]["unidade"],
                "quantidade": qtd,
                "custo_unitario": custo_un,
                "total": subtotal,
            }
        )

    custo_mao_obra = 0.0
    info_mo = None
    roteiro = dados["roteiros"].get(cod)
    if roteiro:
        cod_centro = roteiro["centro"]
        centro = dados["centros"].get(cod_centro)
        if centro:
            tempo = float(roteiro["tempo_unitario"])
            custo_h = float(centro["custo_hora"])
            custo_mao_obra = tempo * custo_h
            info_mo = {
                "centro": cod_centro,
                "tempo": tempo,
                "custo_hora": custo_h,
                "total": custo_mao_obra,
            }

    return {
        "codigo": cod,
        "custo_materiais": custo_materiais,
        "custo_mao_obra": custo_mao_obra,
        "custo_total": custo_materiais + custo_mao_obra,
        "linhas_componentes": linhas,
        "info_mao_obra": info_mo,
    }


def _fmt_valor_tabela(valor):
    """Formata valor decimal com 2 casas e virgula sem simbolo R$."""
    texto = f"{valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def exibir_custo_padrao(dados, codigo_item):
    """Exibe o detalhamento do custo padrao de um item (Mockup 6.7)."""
    cod = utils.validar_codigo_item(codigo_item)
    if cod not in dados["itens"]:
        print(f"ERRO: item '{cod}' nao encontrado.")
        return

    item = dados["itens"][cod]
    if item["tipo"] == "MP":
        custo_fmt = utils.formatar_moeda(item["custo_unitario"])
        print(
            f"\n{cod} {item['descricao']} e materia-prima comprada "
            f"(custo unitario: {custo_fmt})."
        )
        return

    res = calcular_custo_padrao(dados, cod)
    print(f"\nCUSTO PADRAO - {cod} {item['descricao']}")
    print(
        f"{'Item':<8} {'Descricao':<27} {'Qtde':>6} "
        f"{'Custo un.':>10} {'Total':>10}"
    )
    print("-" * 65)

    for linha in res["linhas_componentes"]:
        desc = linha["descricao"][:26]
        qtd_fmt = utils.formatar_numero(linha["quantidade"])
        cu_fmt = _fmt_valor_tabela(linha["custo_unitario"])
        tot_fmt = _fmt_valor_tabela(linha["total"])
        print(
            f"{linha['codigo']:<8} {desc:<27} {qtd_fmt:>6} "
            f"{cu_fmt:>10} {tot_fmt:>10}"
        )

    if res["info_mao_obra"]:
        mo = res["info_mao_obra"]
        rotulo_mo = f"Mao de obra {mo['centro']}"
        tempo_fmt = f"{utils.formatar_numero(mo['tempo'])} h"
        ch_fmt = _fmt_valor_tabela(mo["custo_hora"])
        tot_mo_fmt = _fmt_valor_tabela(mo["total"])
        print(
            f"         {rotulo_mo:<27} {tempo_fmt:>6} "
            f"{ch_fmt:>10} {tot_mo_fmt:>10}"
        )
    else:
        print("         (sem roteiro de mao de obra cadastrado)")

    print("-" * 65)
    print(
        f"{'CUSTO PADRAO TOTAL':<52} "
        f"{utils.formatar_moeda(res['custo_total']):>12}"
    )


def listar_custos_fabricados(dados):
    """Exibe um resumo de custo padrao de todos os itens fabricados."""
    fabricados = sorted(
        i for i in dados["itens"].values() if i["tipo"] in ("PA", "SA")
    )
    if not fabricados:
        print("\nNenhum item fabricado (PA ou SA) cadastrado.")
        return

    print(
        "\nCodigo   Tipo  Descricao                  Materiais   "
        "Mao Obra    Custo Total"
    )
    print("-" * 76)
    for item in fabricados:
        res = calcular_custo_padrao(dados, item["codigo"])
        mat = utils.formatar_moeda(res["custo_materiais"])
        mo = utils.formatar_moeda(res["custo_mao_obra"])
        tot = utils.formatar_moeda(res["custo_total"])
        print(
            f"{item['codigo']:<8} {item['tipo']:<5} "
            f"{item['descricao'][:25]:<25} {mat:>11} {mo:>10} {tot:>14}"
        )


def menu_custos(dados):
    """Submenu de calculo e consulta de custo padrao."""
    while True:
        utils.imprimir_cabecalho("CUSTO PADRAO DOS PRODUTOS")
        print("1. Detalhar custo padrao de um item (PA ou SA)")
        print("2. Listar resumo de custo padrao de todos os fabricados")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            bruto = utils.ler_texto("Codigo do item (ex.: PA-001)")
            try:
                exibir_custo_padrao(dados, bruto)
            except (ValueError, KeyError) as exc:
                print(f"ERRO: {exc}")
            utils.pausar()
        elif opcao == "2":
            listar_custos_fabricados(dados)
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")
