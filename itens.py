"""Cadastro, listagem e alteracao de itens (RF02, RN01)."""

import persistencia
import utils


TIPOS_VALIDOS = ("PA", "SA", "MP")


def cadastrar_item(
    dados,
    codigo,
    descricao,
    tipo,
    unidade,
    custo_unitario,
    lead_time,
    estoque_seguranca,
    lote_minimo,
):
    """Valida e cadastra um novo item no catalogo."""
    tipo_norm = tipo.strip().upper()
    if tipo_norm not in TIPOS_VALIDOS:
        raise ValueError("Tipo invalido. Use PA, SA ou MP.")
    codigo_norm = utils.validar_codigo_item(codigo, tipo_esperado=tipo_norm)
    if codigo_norm in dados["itens"]:
        raise ValueError(
            f"Ja existe um item cadastrado com codigo {codigo_norm}."
        )
    if not descricao.strip():
        raise ValueError("A descricao nao pode ser vazia.")
    if not unidade.strip():
        raise ValueError("A unidade de medida nao pode ser vazia.")
    if custo_unitario < 0:
        raise ValueError("O custo unitario nao pode ser negativo.")
    if lead_time < 0:
        raise ValueError("O lead time nao pode ser negativo.")
    if estoque_seguranca < 0:
        raise ValueError("O estoque de seguranca nao pode ser negativo.")
    if lote_minimo < 0:
        raise ValueError("O lote minimo nao pode ser negativo.")

    item = {
        "codigo": codigo_norm,
        "descricao": descricao.strip(),
        "tipo": tipo_norm,
        "unidade": unidade.strip(),
        "custo_unitario": float(custo_unitario),
        "lead_time": int(lead_time),
        "estoque_seguranca": float(estoque_seguranca),
        "lote_minimo": float(lote_minimo),
    }
    dados["itens"][codigo_norm] = item
    dados["estoque"].setdefault(codigo_norm, 0.0)
    if tipo_norm == "PA":
        dados["mps"].setdefault(codigo_norm, [0.0] * 8)
    persistencia.salvar_json("itens.json", dados["itens"])
    persistencia.salvar_json("estoque.json", dados["estoque"])
    persistencia.salvar_json("mps.json", dados["mps"])
    return item


def alterar_item(
    dados,
    codigo,
    descricao=None,
    unidade=None,
    custo_unitario=None,
    lead_time=None,
    estoque_seguranca=None,
    lote_minimo=None,
):
    """Altera os atributos editaveis de um item existente."""
    codigo_norm = utils.validar_codigo_item(codigo)
    if codigo_norm not in dados["itens"]:
        raise KeyError(f"Item '{codigo_norm}' nao encontrado.")
    item = dados["itens"][codigo_norm]
    if descricao is not None:
        if not descricao.strip():
            raise ValueError("A descricao nao pode ser vazia.")
        item["descricao"] = descricao.strip()
    if unidade is not None:
        if not unidade.strip():
            raise ValueError("A unidade de medida nao pode ser vazia.")
        item["unidade"] = unidade.strip()
    if custo_unitario is not None:
        if custo_unitario < 0:
            raise ValueError("O custo unitario nao pode ser negativo.")
        item["custo_unitario"] = float(custo_unitario)
    if lead_time is not None:
        if lead_time < 0:
            raise ValueError("O lead time nao pode ser negativo.")
        item["lead_time"] = int(lead_time)
    if estoque_seguranca is not None:
        if estoque_seguranca < 0:
            raise ValueError("O estoque de seguranca nao pode ser negativo.")
        item["estoque_seguranca"] = float(estoque_seguranca)
    if lote_minimo is not None:
        if lote_minimo < 0:
            raise ValueError("O lote minimo nao pode ser negativo.")
        item["lote_minimo"] = float(lote_minimo)

    persistencia.salvar_json("itens.json", dados["itens"])
    return item


def listar_itens(dados, filtro_tipo=None):
    """Exibe a tabela formatada dos itens cadastrados."""
    itens = sorted(dados["itens"].values(), key=lambda i: i["codigo"])
    if filtro_tipo:
        itens = [i for i in itens if i["tipo"] == filtro_tipo.upper()]

    if not itens:
        print("\nNenhum item encontrado.")
        return

    print(
        "\nCodigo   Tipo  Descricao                     Un   "
        "Custo Un.    LT  Est.Seg  Lote Min"
    )
    print("-" * 86)
    for item in itens:
        desc = item["descricao"][:28]
        custo = utils.formatar_moeda(item["custo_unitario"])
        es = utils.formatar_numero(item["estoque_seguranca"])
        lote = utils.formatar_numero(item["lote_minimo"])
        print(
            f"{item['codigo']:<8} {item['tipo']:<5} {desc:<29} "
            f"{item['unidade']:<4} {custo:>11}  {item['lead_time']:>2}  "
            f"{es:>7}  {lote:>8}"
        )


def _fluxo_cadastrar_item(dados):
    """Interface de texto para cadastro de um novo item."""
    print("\n--- Cadastrar Item ---")
    tipo = utils.ler_opcao("Tipo [PA/SA/MP]", TIPOS_VALIDOS)
    while True:
        bruto = utils.ler_texto(f"Codigo (ex.: {tipo}-001)")
        try:
            codigo = utils.validar_codigo_item(bruto, tipo_esperado=tipo)
            if codigo in dados["itens"]:
                print(f"ERRO: o codigo {codigo} ja esta cadastrado.")
                continue
            break
        except ValueError as exc:
            print(f"ERRO: {exc}")

    descricao = utils.ler_texto("Descricao")
    unidade = utils.ler_texto("Unidade de medida (ex.: un, m, L, kg)")
    custo = utils.ler_float("Custo unitario (R$)", minimo=0.0)
    lead_time = utils.ler_int("Lead time (semanas)", minimo=0)
    est_seg = utils.ler_float("Estoque de seguranca", minimo=0.0)
    lote_min = utils.ler_float("Lote minimo", minimo=0.0)

    item = cadastrar_item(
        dados,
        codigo,
        descricao,
        tipo,
        unidade,
        custo,
        lead_time,
        est_seg,
        lote_min,
    )
    print(f"\nItem {item['codigo']} - {item['descricao']} cadastrado.")


def _fluxo_alterar_item(dados):
    """Interface de texto para alteracao de um item existente."""
    print("\n--- Alterar Item ---")
    listar_itens(dados)
    bruto = utils.ler_texto("\nCodigo do item a alterar")
    try:
        codigo = utils.validar_codigo_item(bruto)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    if codigo not in dados["itens"]:
        print(f"ERRO: item '{codigo}' nao encontrado.")
        return

    atual = dados["itens"][codigo]
    print(
        f"Editando {codigo} ({atual['tipo']}). "
        "Pressione Enter para manter o valor atual."
    )
    descricao = utils.ler_texto("Descricao", padrao=atual["descricao"])
    unidade = utils.ler_texto("Unidade", padrao=atual["unidade"])
    custo = utils.ler_float(
        "Custo unitario (R$)",
        minimo=0.0,
        padrao=atual["custo_unitario"],
    )
    lead_time = utils.ler_int(
        "Lead time (semanas)",
        minimo=0,
        padrao=atual["lead_time"],
    )
    est_seg = utils.ler_float(
        "Estoque de seguranca",
        minimo=0.0,
        padrao=atual["estoque_seguranca"],
    )
    lote_min = utils.ler_float(
        "Lote minimo",
        minimo=0.0,
        padrao=atual["lote_minimo"],
    )

    alterar_item(
        dados,
        codigo,
        descricao=descricao,
        unidade=unidade,
        custo_unitario=custo,
        lead_time=lead_time,
        estoque_seguranca=est_seg,
        lote_minimo=lote_min,
    )
    print(f"\nItem {codigo} atualizado com sucesso.")


def menu_itens(dados):
    """Submenu de gestao do cadastro de itens."""
    while True:
        utils.imprimir_cabecalho("CADASTRO DE ITENS")
        print("1. Listar todos os itens")
        print("2. Listar itens por tipo (PA / SA / MP)")
        print("3. Cadastrar novo item")
        print("4. Alterar item existente")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            listar_itens(dados)
            utils.pausar()
        elif opcao == "2":
            tipo = utils.ler_opcao(
                "Filtrar por tipo [PA/SA/MP]", TIPOS_VALIDOS
            )
            listar_itens(dados, filtro_tipo=tipo)
            utils.pausar()
        elif opcao == "3":
            _fluxo_cadastrar_item(dados)
            utils.pausar()
        elif opcao == "4":
            _fluxo_alterar_item(dados)
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")
