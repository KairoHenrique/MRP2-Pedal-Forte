"""Centros de trabalho, roteiros e calculo CRP (RF06, RF12, RN09)."""

import persistencia
import utils


STATUS_OP_ATIVOS = ("PLANEJADA", "ATRASADA", "FIRME", "LIBERADA")


def cadastrar_centro(
    dados,
    codigo,
    descricao,
    capacidade_semanal,
    custo_hora,
):
    """Cadastra um novo centro de trabalho."""
    cod_norm = utils.validar_codigo_centro(codigo)
    if cod_norm in dados["centros"]:
        raise ValueError(f"Centro '{cod_norm}' ja cadastrado.")
    if not descricao.strip():
        raise ValueError("A descricao do centro e obrigatoria.")
    if capacidade_semanal <= 0:
        raise ValueError("A capacidade semanal deve ser maior que zero.")
    if custo_hora < 0:
        raise ValueError("O custo-hora nao pode ser negativo.")

    centro = {
        "codigo": cod_norm,
        "descricao": descricao.strip(),
        "capacidade_semanal": float(capacidade_semanal),
        "custo_hora": float(custo_hora),
    }
    dados["centros"][cod_norm] = centro
    persistencia.salvar_json("centros.json", dados["centros"])
    return centro


def alterar_centro(
    dados,
    codigo,
    descricao=None,
    capacidade_semanal=None,
    custo_hora=None,
):
    """Atualiza um centro de trabalho existente."""
    cod_norm = utils.validar_codigo_centro(codigo)
    if cod_norm not in dados["centros"]:
        raise KeyError(f"Centro '{cod_norm}' nao encontrado.")
    centro = dados["centros"][cod_norm]
    if descricao is not None:
        if not descricao.strip():
            raise ValueError("A descricao nao pode ser vazia.")
        centro["descricao"] = descricao.strip()
    if capacidade_semanal is not None:
        if capacidade_semanal <= 0:
            raise ValueError("A capacidade semanal deve ser maior que zero.")
        centro["capacidade_semanal"] = float(capacidade_semanal)
    if custo_hora is not None:
        if custo_hora < 0:
            raise ValueError("O custo-hora nao pode ser negativo.")
        centro["custo_hora"] = float(custo_hora)

    persistencia.salvar_json("centros.json", dados["centros"])
    return centro


def cadastrar_roteiro(dados, codigo_item, codigo_centro, tempo_unitario):
    """Associa um item fabricado (PA ou SA) a um centro e tempo unitario."""
    item_norm = utils.validar_codigo_item(codigo_item)
    if item_norm not in dados["itens"]:
        raise KeyError(f"Item '{item_norm}' nao encontrado.")
    if dados["itens"][item_norm]["tipo"] == "MP":
        raise ValueError(
            "Apenas itens fabricados (PA ou SA) possuem roteiro de producao."
        )
    centro_norm = utils.validar_codigo_centro(codigo_centro)
    if centro_norm not in dados["centros"]:
        raise KeyError(f"Centro '{centro_norm}' nao encontrado.")
    if tempo_unitario <= 0:
        raise ValueError("O tempo unitario deve ser maior que zero.")

    roteiro = {
        "item": item_norm,
        "centro": centro_norm,
        "tempo_unitario": float(tempo_unitario),
    }
    dados["roteiros"][item_norm] = roteiro
    persistencia.salvar_json("roteiros.json", dados["roteiros"])
    return roteiro


def listar_centros(dados):
    """Lista todos os centros de trabalho cadastrados."""
    centros = sorted(dados["centros"].values(), key=lambda c: c["codigo"])
    if not centros:
        print("\nNenhum centro de trabalho cadastrado.")
        return
    print("\nCodigo  Descricao                 Capacidade (h/sem)  Custo-hora")
    print("-" * 66)
    for centro in centros:
        cap = utils.formatar_numero(centro["capacidade_semanal"])
        custo = utils.formatar_moeda(centro["custo_hora"])
        print(
            f"{centro['codigo']:<7} {centro['descricao'][:25]:<25} "
            f"{cap:>18}  {custo:>10}"
        )


def listar_roteiros(dados):
    """Lista os roteiros de operacao unica dos itens fabricados."""
    roteiros = sorted(dados["roteiros"].values(), key=lambda r: r["item"])
    if not roteiros:
        print("\nNenhum roteiro cadastrado.")
        return
    print("\nItem     Descricao                     Centro   Tempo/un (h)")
    print("-" * 66)
    for rot in roteiros:
        item = dados["itens"].get(rot["item"], {})
        desc = item.get("descricao", "-")[:28]
        tempo = utils.formatar_numero(rot["tempo_unitario"])
        print(
            f"{rot['item']:<8} {desc:<29} {rot['centro']:<7} {tempo:>12}"
        )


def calcular_crp(dados):
    """Calcula a carga semanal (semanas 1..8) por centro de trabalho (RN09).

    Returns:
        Dicionario codigo_centro -> {
            "capacidade": float,
            "cargas": list[float] (8 posicoes),
            "usos_pct": list[float] (8 posicoes),
            "sobrecargas": list[int] (numeros das semanas),
            "carga_atrasada": float,
        }
    """
    resultado = {}
    for cod_centro, centro in sorted(dados["centros"].items()):
        resultado[cod_centro] = {
            "capacidade": float(centro["capacidade_semanal"]),
            "cargas": [0.0] * 8,
            "usos_pct": [0.0] * 8,
            "sobrecargas": [],
            "carga_atrasada": 0.0,
        }

    for ordem in dados["ordens"].values():
        if ordem["tipo"] != "OP":
            continue
        if ordem["status"] not in STATUS_OP_ATIVOS:
            continue
        roteiro = dados["roteiros"].get(ordem["item"])
        if not roteiro:
            continue
        cod_centro = roteiro["centro"]
        if cod_centro not in resultado:
            continue

        horas = float(ordem["quantidade"]) * float(roteiro["tempo_unitario"])
        sem = int(ordem["semana_liberacao"])
        if 1 <= sem <= 8:
            resultado[cod_centro]["cargas"][sem - 1] += horas
        elif sem < 1:
            resultado[cod_centro]["carga_atrasada"] += horas

    for cod_centro, info in resultado.items():
        cap = info["capacidade"]
        for idx in range(8):
            carga = info["cargas"][idx]
            uso = (carga / cap * 100.0) if cap > 0 else 0.0
            info["usos_pct"][idx] = uso
            if carga > cap + 1e-9:
                info["sobrecargas"].append(idx + 1)

    return resultado


def exibir_crp(dados, codigo_centro=None):
    """Exibe o relatorio Carga x Capacidade (CRP) em modo texto."""
    crp = calcular_crp(dados)
    if not crp:
        print("\nNenhum centro de trabalho cadastrado.")
        return

    if codigo_centro:
        cod = utils.validar_codigo_centro(codigo_centro)
        if cod not in crp:
            print(f"ERRO: centro '{cod}' nao encontrado.")
            return
        alvos = [cod]
    else:
        alvos = list(crp.keys())

    for cod in alvos:
        centro = dados["centros"][cod]
        info = crp[cod]
        cap_fmt = utils.formatar_numero(info["capacidade"])
        print(
            f"\nCARGA x CAPACIDADE - {cod} {centro['descricao']} "
            f"({cap_fmt} h/semana)"
        )
        print("Sem  Carga(h)  Uso(%)")
        for idx in range(8):
            carga = info["cargas"][idx]
            uso = round(info["usos_pct"][idx])
            blocos = min(20, max(0, round(uso / 10)))
            barra = "#" * blocos
            alerta = " SOBRECARGA" if (idx + 1) in info["sobrecargas"] else ""
            carga_fmt = f"{carga:.1f}".replace(".", ",")
            print(f" {idx + 1}   {carga_fmt:>7}  {uso:>5}  {barra}{alerta}")

        if info["carga_atrasada"] > 0:
            atr_fmt = f"{info['carga_atrasada']:.1f}".replace(".", ",")
            print(
                f"AVISO: ha {atr_fmt} h em OPs ATRASADAS (liberacao <= S0)."
            )
        if info["sobrecargas"]:
            sems = " e ".join(str(s) for s in info["sobrecargas"])
            print(
                f"Sugestao: antecipar OPs ou programar hora extra nas "
                f"semanas {sems}."
            )


def _fluxo_cadastrar_centro(dados):
    """Interface de texto para cadastrar centro de trabalho."""
    print("\n--- Cadastrar Centro de Trabalho ---")
    while True:
        bruto = utils.ler_texto("Codigo (ex.: CT-01)")
        try:
            cod = utils.validar_codigo_centro(bruto)
            if cod in dados["centros"]:
                print(f"ERRO: centro '{cod}' ja existe.")
                continue
            break
        except ValueError as exc:
            print(f"ERRO: {exc}")

    descricao = utils.ler_texto("Descricao")
    cap = utils.ler_float(
        "Capacidade semanal (horas)",
        minimo=0.0,
        permitir_zero=False,
    )
    custo = utils.ler_float("Custo-hora (R$)", minimo=0.0)
    cadastrar_centro(dados, cod, descricao, cap, custo)
    print(f"\nCentro {cod} cadastrado com sucesso.")


def _fluxo_alterar_centro(dados):
    """Interface de texto para alterar centro de trabalho."""
    print("\n--- Alterar Centro de Trabalho ---")
    listar_centros(dados)
    bruto = utils.ler_texto("\nCodigo do centro")
    try:
        cod = utils.validar_codigo_centro(bruto)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    if cod not in dados["centros"]:
        print(f"ERRO: centro '{cod}' nao encontrado.")
        return

    atual = dados["centros"][cod]
    desc = utils.ler_texto("Descricao", padrao=atual["descricao"])
    cap = utils.ler_float(
        "Capacidade semanal (h)",
        minimo=0.0,
        permitir_zero=False,
        padrao=atual["capacidade_semanal"],
    )
    custo = utils.ler_float(
        "Custo-hora (R$)",
        minimo=0.0,
        padrao=atual["custo_hora"],
    )
    alterar_centro(dados, cod, desc, cap, custo)
    print(f"\nCentro {cod} atualizado.")


def _fluxo_cadastrar_roteiro(dados):
    """Interface de texto para cadastrar/alterar roteiro de fabricacao."""
    print("\n--- Cadastrar / Alterar Roteiro ---")
    bruto_item = utils.ler_texto("Codigo do item fabricado (PA ou SA)")
    try:
        cod_item = utils.validar_codigo_item(bruto_item)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    if cod_item not in dados["itens"]:
        print(f"ERRO: item '{cod_item}' nao encontrado.")
        return
    if dados["itens"][cod_item]["tipo"] == "MP":
        print("ERRO: materias-primas (MP) nao possuem roteiro.")
        return

    listar_centros(dados)
    bruto_centro = utils.ler_texto("\nCodigo do centro de trabalho")
    try:
        cod_centro = utils.validar_codigo_centro(bruto_centro)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    if cod_centro not in dados["centros"]:
        print(f"ERRO: centro '{cod_centro}' nao encontrado.")
        return

    tempo = utils.ler_float(
        "Tempo por unidade (horas)",
        minimo=0.0,
        permitir_zero=False,
    )
    cadastrar_roteiro(dados, cod_item, cod_centro, tempo)
    print(f"\nRoteiro de {cod_item} no centro {cod_centro} salvo.")


def menu_cadastros_capacidade(dados):
    """Submenu de cadastro de centros de trabalho e roteiros."""
    while True:
        utils.imprimir_cabecalho("CENTROS DE TRABALHO E ROTEIROS")
        print("1. Listar centros de trabalho")
        print("2. Cadastrar centro de trabalho")
        print("3. Alterar centro de trabalho")
        print("4. Listar roteiros de fabricacao")
        print("5. Cadastrar ou alterar roteiro")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            listar_centros(dados)
            utils.pausar()
        elif opcao == "2":
            _fluxo_cadastrar_centro(dados)
            utils.pausar()
        elif opcao == "3":
            _fluxo_alterar_centro(dados)
            utils.pausar()
        elif opcao == "4":
            listar_roteiros(dados)
            utils.pausar()
        elif opcao == "5":
            _fluxo_cadastrar_roteiro(dados)
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")


def menu_crp(dados):
    """Submenu de analise Carga x Capacidade (CRP)."""
    while True:
        utils.imprimir_cabecalho("CARGA x CAPACIDADE (CRP)")
        print("1. Exibir CRP de todos os centros")
        print("2. Exibir CRP de um centro especifico")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            exibir_crp(dados)
            utils.pausar()
        elif opcao == "2":
            bruto = utils.ler_texto("Codigo do centro (ex.: CT-01)")
            try:
                exibir_crp(dados, codigo_centro=bruto)
            except ValueError as exc:
                print(f"ERRO: {exc}")
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")
