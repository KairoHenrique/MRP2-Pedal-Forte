"""Plano Mestre de Producao (MPS) para horizonte de 8 semanas (RF07)."""

import persistencia
import utils


HORIZONTE_SEMANAS = 8


def obter_demanda_mps(dados, codigo_pa):
    """Retorna a lista de 8 demandas semanais de um produto acabado."""
    cod = utils.validar_codigo_item(codigo_pa, tipo_esperado="PA")
    demandas = dados["mps"].get(cod, [0.0] * HORIZONTE_SEMANAS)
    return [float(x) for x in demandas[:HORIZONTE_SEMANAS]]


def atualizar_mps(dados, codigo_pa, demandas):
    """Atualiza as 8 semanas de demanda de um produto acabado."""
    cod = utils.validar_codigo_item(codigo_pa, tipo_esperado="PA")
    if cod not in dados["itens"]:
        raise KeyError(f"Produto acabado '{cod}' nao encontrado.")
    if len(demandas) != HORIZONTE_SEMANAS:
        raise ValueError(
            f"O MPS deve conter exatamente {HORIZONTE_SEMANAS} semanas."
        )
    if any(float(q) < 0 for q in demandas):
        raise ValueError("As quantidades do MPS nao podem ser negativas.")

    dados["mps"][cod] = [float(q) for q in demandas]
    persistencia.salvar_json("mps.json", dados["mps"])
    return dados["mps"][cod]


def atualizar_semana_mps(dados, codigo_pa, semana, quantidade):
    """Atualiza a demanda de uma semana especifica (1..8) de um PA."""
    if not 1 <= semana <= HORIZONTE_SEMANAS:
        raise ValueError("A semana deve estar entre 1 e 8.")
    if quantidade < 0:
        raise ValueError("A quantidade nao pode ser negativa.")
    demandas = obter_demanda_mps(dados, codigo_pa)
    demandas[semana - 1] = float(quantidade)
    return atualizar_mps(dados, codigo_pa, demandas)


def exibir_mps(dados):
    """Exibe a tabela do Plano Mestre de Producao (8 semanas)."""
    pas = sorted(
        i for i in dados["itens"].values() if i["tipo"] == "PA"
    )
    if not pas:
        print("\nNenhum produto acabado (PA) cadastrado.")
        return

    cabecalho_sem = " ".join(
        f"S{s:>4}" for s in range(1, HORIZONTE_SEMANAS + 1)
    )
    print(f"\nProduto  Descricao                {cabecalho_sem}")
    print("-" * 74)
    for pa in pas:
        cod = pa["codigo"]
        demandas = obter_demanda_mps(dados, cod)
        valores = " ".join(
            f"{utils.formatar_numero(d):>5}" for d in demandas
        )
        print(f"{cod:<8} {pa['descricao'][:23]:<24} {valores}")


def _fluxo_alterar_mps_completo(dados):
    """Permite preencher as 8 semanas de demanda de um PA."""
    exibir_mps(dados)
    bruto = utils.ler_texto("\nCodigo do produto acabado (ex.: PA-001)")
    try:
        cod = utils.validar_codigo_item(bruto, tipo_esperado="PA")
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    if cod not in dados["itens"]:
        print(f"ERRO: produto '{cod}' nao encontrado.")
        return

    atuais = obter_demanda_mps(dados, cod)
    novas = []
    print(f"Informe a demanda de {cod} (Enter mantem o valor atual):")
    for idx in range(HORIZONTE_SEMANAS):
        val = utils.ler_float(
            f"  Semana {idx + 1}",
            minimo=0.0,
            padrao=atuais[idx],
        )
        novas.append(val)
    atualizar_mps(dados, cod, novas)
    print(f"\nMPS de {cod} atualizado.")


def _fluxo_alterar_semana_mps(dados):
    """Permite alterar a demanda de uma unica semana no MPS."""
    exibir_mps(dados)
    bruto = utils.ler_texto("\nCodigo do produto acabado (ex.: PA-001)")
    try:
        cod = utils.validar_codigo_item(bruto, tipo_esperado="PA")
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    if cod not in dados["itens"]:
        print(f"ERRO: produto '{cod}' nao encontrado.")
        return

    semana = utils.ler_int("Semana (1 a 8)", minimo=1, maximo=8)
    atuais = obter_demanda_mps(dados, cod)
    qtd = utils.ler_float(
        f"Nova demanda para semana {semana}",
        minimo=0.0,
        padrao=atuais[semana - 1],
    )
    atualizar_semana_mps(dados, cod, semana, qtd)
    print(f"\nDemanda da semana {semana} para {cod} atualizada.")


def menu_mps(dados):
    """Submenu do Plano Mestre de Producao."""
    while True:
        utils.imprimir_cabecalho("PLANO MESTRE DE PRODUCAO (MPS)")
        print("1. Exibir MPS (8 semanas)")
        print("2. Alterar todas as 8 semanas de um produto")
        print("3. Alterar uma semana especifica")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            exibir_mps(dados)
            utils.pausar()
        elif opcao == "2":
            _fluxo_alterar_mps_completo(dados)
            utils.pausar()
        elif opcao == "3":
            _fluxo_alterar_semana_mps(dados)
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")
