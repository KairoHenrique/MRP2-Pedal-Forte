"""Estrutura de produto (BOM) em ate 3 niveis e recursao (RF03, RN03)."""

import persistencia
import utils


def validar_relacao_bom(itens, codigo_pai, codigo_componente):
    """Valida se o componente pode compor o item pai segundo a RN03."""
    if codigo_pai not in itens:
        raise KeyError(f"Item pai '{codigo_pai}' nao encontrado.")
    if codigo_componente not in itens:
        raise KeyError(f"Componente '{codigo_componente}' nao encontrado.")
    if codigo_pai == codigo_componente:
        raise ValueError("Um item nao pode ser componente de si mesmo.")

    tipo_pai = itens[codigo_pai]["tipo"]
    tipo_comp = itens[codigo_componente]["tipo"]

    if tipo_pai == "MP":
        raise ValueError(
            "Materias-primas (MP) sao compradas e nao possuem estrutura."
        )
    if tipo_pai == "PA" and tipo_comp == "PA":
        raise ValueError(
            "Um produto acabado (PA) pode conter apenas itens SA ou MP."
        )
    if tipo_pai == "SA" and tipo_comp != "MP":
        raise ValueError(
            "Um semiacabado (SA) pode conter apenas materias-primas (MP)."
        )


def adicionar_componente(dados, codigo_pai, codigo_componente, quantidade):
    """Adiciona ou atualiza um componente na estrutura de um item pai."""
    pai = utils.validar_codigo_item(codigo_pai)
    comp = utils.validar_codigo_item(codigo_componente)
    validar_relacao_bom(dados["itens"], pai, comp)
    if quantidade <= 0:
        raise ValueError("A quantidade por unidade deve ser maior que zero.")

    componentes = dados["estrutura"].setdefault(pai, [])
    for entrada in componentes:
        if entrada["componente"] == comp:
            entrada["quantidade"] = float(quantidade)
            persistencia.salvar_json("estrutura.json", dados["estrutura"])
            return "atualizado"

    componentes.append({"componente": comp, "quantidade": float(quantidade)})
    persistencia.salvar_json("estrutura.json", dados["estrutura"])
    return "adicionado"


def remover_componente(dados, codigo_pai, codigo_componente):
    """Remove um componente da estrutura do item pai."""
    pai = utils.validar_codigo_item(codigo_pai)
    comp = utils.validar_codigo_item(codigo_componente)
    componentes = dados["estrutura"].get(pai, [])
    novos = [c for c in componentes if c["componente"] != comp]
    if len(novos) == len(componentes):
        raise KeyError(
            f"Componente '{comp}' nao encontrado na estrutura de '{pai}'."
        )
    if novos:
        dados["estrutura"][pai] = novos
    else:
        dados["estrutura"].pop(pai, None)
    persistencia.salvar_json("estrutura.json", dados["estrutura"])


def explodir_bom(estrutura, itens, codigo_pai, nivel=0, fator=1.0):
    """Explode recursivamente a BOM de um item retornando nos com nivel.

    Args:
        estrutura: Dicionario pai -> lista de componentes.
        itens: Dicionario de itens cadastrados.
        codigo_pai: Codigo do item atual na recursao.
        nivel: Nivel hierarquico atual (0 = raiz).
        fator: Quantidade acumulada em relacao ao produto raiz.

    Returns:
        Lista de dicionarios com codigo, nivel, qtd_unitaria e qtd_total.
    """
    nos = []
    if nivel == 0:
        nos.append(
            {
                "codigo": codigo_pai,
                "nivel": 0,
                "qtd_unitaria": 1.0,
                "qtd_total": 1.0,
            }
        )
    for comp in estrutura.get(codigo_pai, []):
        cod_comp = comp["componente"]
        if cod_comp not in itens:
            continue
        qtd_unit = comp["quantidade"]
        qtd_tot = fator * qtd_unit
        nos.append(
            {
                "codigo": cod_comp,
                "nivel": nivel + 1,
                "qtd_unitaria": qtd_unit,
                "qtd_total": qtd_tot,
            }
        )
        if nivel + 1 < 2 and cod_comp in estrutura:
            nos.extend(
                explodir_bom(
                    estrutura,
                    itens,
                    cod_comp,
                    nivel=nivel + 1,
                    fator=qtd_tot,
                )
            )
    return nos


def _imprimir_filhos_recursivo(
    estrutura,
    itens,
    codigo_pai,
    prefixo="",
    nivel=1,
    niveis_dict=None,
):
    """Imprime recursivamente os ramos da arvore BOM com indentacao."""
    filhos = estrutura.get(codigo_pai, [])
    total = len(filhos)
    for idx, comp in enumerate(filhos):
        cod_comp = comp["componente"]
        if cod_comp not in itens:
            continue
        ultimo = idx == total - 1
        conector = "└── " if ultimo else "├── "
        item = itens[cod_comp]
        qtd_fmt = utils.formatar_numero(comp["quantidade"])
        rotulo = f"{cod_comp} {item['descricao']}"
        pontos = "." * max(2, 38 - len(rotulo) - len(prefixo))
        print(
            f"{prefixo}{conector}{rotulo} {pontos} "
            f"{qtd_fmt} {item['unidade']}"
        )

        if niveis_dict is not None:
            niveis_dict.setdefault(nivel, [])
            if cod_comp not in niveis_dict[nivel]:
                niveis_dict[nivel].append(cod_comp)

        extensao = "    " if ultimo else "│   "
        if nivel < 2 and cod_comp in estrutura:
            _imprimir_filhos_recursivo(
                estrutura,
                itens,
                cod_comp,
                prefixo=prefixo + extensao,
                nivel=nivel + 1,
                niveis_dict=niveis_dict,
            )


def exibir_arvore_bom(dados, codigo_pai):
    """Exibe a arvore indentada da BOM e o resumo dos niveis."""
    codigo = utils.validar_codigo_item(codigo_pai)
    if codigo not in dados["itens"]:
        print(f"ERRO: item '{codigo}' nao encontrado.")
        return
    item = dados["itens"][codigo]
    if item["tipo"] == "MP":
        print(f"AVISO: '{codigo}' e materia-prima e nao possui estrutura.")
        return

    print(f"\n{codigo} {item['descricao']}")
    filhos = dados["estrutura"].get(codigo, [])
    if not filhos:
        print("  (sem componentes cadastrados)")
        return

    niveis = {0: [codigo]}
    _imprimir_filhos_recursivo(
        dados["estrutura"],
        dados["itens"],
        codigo,
        niveis_dict=niveis,
    )
    partes = []
    for nv in sorted(niveis):
        codigos = ", ".join(niveis[nv])
        partes.append(f"{nv} = {codigos}")
    print(f"\nNiveis: {' | '.join(partes)}")


def _fluxo_adicionar_componente(dados):
    """Interface de texto para cadastrar componente em uma BOM."""
    print("\n--- Adicionar/Atualizar Componente na BOM ---")
    bruto_pai = utils.ler_texto("Codigo do item pai (PA ou SA)")
    try:
        pai = utils.validar_codigo_item(bruto_pai)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    if pai not in dados["itens"]:
        print(f"ERRO: item '{pai}' nao encontrado.")
        return
    if dados["itens"][pai]["tipo"] == "MP":
        print("ERRO: materias-primas (MP) nao possuem estrutura.")
        return

    bruto_comp = utils.ler_texto("Codigo do componente")
    try:
        comp = utils.validar_codigo_item(bruto_comp)
        validar_relacao_bom(dados["itens"], pai, comp)
    except (ValueError, KeyError) as exc:
        print(f"ERRO: {exc}")
        return

    unidade = dados["itens"][comp]["unidade"]
    qtd = utils.ler_float(
        f"Quantidade por unidade ({unidade})",
        minimo=0.0,
        permitir_zero=False,
    )
    acao = adicionar_componente(dados, pai, comp, qtd)
    print(f"\nComponente {comp} {acao} na estrutura de {pai}.")


def _fluxo_remover_componente(dados):
    """Interface de texto para remover componente de uma BOM."""
    print("\n--- Remover Componente da BOM ---")
    bruto_pai = utils.ler_texto("Codigo do item pai")
    try:
        pai = utils.validar_codigo_item(bruto_pai)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    exibir_arvore_bom(dados, pai)
    if not dados["estrutura"].get(pai):
        return
    bruto_comp = utils.ler_texto("\nCodigo do componente a remover")
    try:
        remover_componente(dados, pai, bruto_comp)
        print(f"Componente {bruto_comp.upper()} removido de {pai}.")
    except (ValueError, KeyError) as exc:
        print(f"ERRO: {exc}")


def menu_estrutura(dados):
    """Submenu de gestao da estrutura de produto (BOM)."""
    while True:
        utils.imprimir_cabecalho("ESTRUTURA DE PRODUTO (BOM)")
        print("1. Exibir arvore indentada (explosao da BOM)")
        print("2. Adicionar ou atualizar componente")
        print("3. Remover componente")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            bruto = utils.ler_texto("Codigo do produto (ex.: PA-001)")
            try:
                exibir_arvore_bom(dados, bruto)
            except ValueError as exc:
                print(f"ERRO: {exc}")
            utils.pausar()
        elif opcao == "2":
            _fluxo_adicionar_componente(dados)
            utils.pausar()
        elif opcao == "3":
            _fluxo_remover_componente(dados)
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")
