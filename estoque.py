"""Movimentacoes de estoque, saldo e kardex (RF04, RF05, RN02, RN10)."""

import persistencia
import utils


MAPA_TIPO_MOV = {
    "E": "ENTRADA",
    "ENTRADA": "ENTRADA",
    "S": "SAIDA",
    "SAIDA": "SAIDA",
    "A": "AJUSTE",
    "AJUSTE": "AJUSTE",
}


def obter_saldo(dados, codigo):
    """Retorna o saldo atual em estoque de um item."""
    return float(dados["estoque"].get(codigo, 0.0))


def registrar_movimentacao(
    dados,
    codigo,
    tipo,
    quantidade,
    documento,
    data_str=None,
    salvar=True,
):
    """Registra uma movimentacao de estoque e atualiza o saldo (RN02, RN10)."""
    codigo_norm = utils.validar_codigo_item(codigo)
    if codigo_norm not in dados["itens"]:
        raise KeyError(f"Item '{codigo_norm}' nao encontrado.")

    tipo_norm = MAPA_TIPO_MOV.get(tipo.strip().upper())
    if not tipo_norm:
        raise ValueError("Tipo invalido. Use [E]ntrada, [S]aida ou [A]juste.")

    if not documento.strip():
        raise ValueError("O documento/motivo e obrigatorio.")

    data_mov = utils.validar_data(data_str) if data_str else utils.data_hoje()
    unidade = dados["itens"][codigo_norm]["unidade"]
    saldo_atual = obter_saldo(dados, codigo_norm)

    if tipo_norm == "ENTRADA":
        if quantidade <= 0:
            raise ValueError("A quantidade de entrada deve ser positiva.")
        variacao = float(quantidade)
        qtde_registro = float(quantidade)
    elif tipo_norm == "SAIDA":
        if quantidade <= 0:
            raise ValueError("A quantidade de saida deve ser positiva.")
        variacao = -float(quantidade)
        qtde_registro = float(quantidade)
    else:
        if quantidade == 0:
            raise ValueError("A quantidade de ajuste nao pode ser zero.")
        variacao = float(quantidade)
        qtde_registro = float(quantidade)

    novo_saldo = saldo_atual + variacao
    if novo_saldo < -1e-9:
        saldo_fmt = utils.formatar_numero(saldo_atual)
        raise ValueError(
            f"saldo insuficiente (saldo atual: {saldo_fmt} {unidade}). "
            "Operacao cancelada."
        )
    if abs(novo_saldo) < 1e-9:
        novo_saldo = 0.0

    dados["estoque"][codigo_norm] = novo_saldo
    movimento = {
        "data": data_mov,
        "codigo": codigo_norm,
        "tipo": tipo_norm,
        "quantidade": qtde_registro,
        "saldo_apos": novo_saldo,
        "documento": documento.strip(),
    }
    dados["movimentos"].append(movimento)

    if salvar:
        persistencia.salvar_json("estoque.json", dados["estoque"])
        persistencia.salvar_movimentos(dados["movimentos"])

    return movimento


def consultar_saldo_kardex(dados, codigo):
    """Exibe o kardex completo de um item e alerta de estoque minimo."""
    codigo_norm = utils.validar_codigo_item(codigo)
    if codigo_norm not in dados["itens"]:
        print(f"ERRO: item '{codigo_norm}' nao encontrado.")
        return

    item = dados["itens"][codigo_norm]
    saldo = obter_saldo(dados, codigo_norm)
    est_seg = item["estoque_seguranca"]
    un = item["unidade"]

    print(
        f"\nKARDEX - {codigo_norm} {item['descricao']} ({un})"
    )
    print(f"{'Data':<12} {'Tipo':<9} {'Qtde':>8} {'Saldo':>8}  Documento")
    print("-" * 66)

    movs = [m for m in dados["movimentos"] if m["codigo"] == codigo_norm]
    if not movs:
        print("Nenhuma movimentacao registrada.")
    else:
        for mov in movs:
            qtd = mov["quantidade"]
            if mov["tipo"] == "ENTRADA":
                sinal = "+"
            elif mov["tipo"] == "SAIDA":
                sinal = "-"
            else:
                sinal = "+" if qtd >= 0 else ""
            qtd_fmt = f"{sinal}{utils.formatar_numero(qtd)}"
            saldo_fmt = utils.formatar_numero(mov["saldo_apos"])
            print(
                f"{mov['data']:<12} {mov['tipo']:<9} {qtd_fmt:>8} "
                f"{saldo_fmt:>8}  {mov['documento']}"
            )

    print(
        f"\nSaldo atual: {utils.formatar_numero(saldo)} {un} | "
        f"Estoque de seguranca: {utils.formatar_numero(est_seg)} {un}"
    )
    if saldo < est_seg:
        print(
            f"ALERTA: saldo ({utils.formatar_numero(saldo)} {un}) "
            f"abaixo do estoque de seguranca "
            f"({utils.formatar_numero(est_seg)} {un})."
        )


def listar_posicoes_estoque(dados):
    """Exibe a posicao atual de estoque de todos os itens."""
    itens = sorted(dados["itens"].values(), key=lambda i: i["codigo"])
    if not itens:
        print("\nNenhum item cadastrado.")
        return

    print(
        "\nCodigo   Descricao                     Un     Saldo   "
        "Est.Seg  Situacao"
    )
    print("-" * 74)
    for item in itens:
        cod = item["codigo"]
        saldo = obter_saldo(dados, cod)
        es = item["estoque_seguranca"]
        situacao = "ABAIXO ES!" if saldo < es else "OK"
        print(
            f"{cod:<8} {item['descricao'][:28]:<29} {item['unidade']:<4} "
            f"{utils.formatar_numero(saldo):>7}  "
            f"{utils.formatar_numero(es):>8}  {situacao}"
        )


def _fluxo_movimentar(dados):
    """Interface de texto para registrar entrada, saida ou ajuste."""
    print("\n--- Movimentar Estoque ---")
    bruto_cod = utils.ler_texto("Codigo do item")
    try:
        codigo = utils.validar_codigo_item(bruto_cod)
    except ValueError as exc:
        print(f"ERRO: {exc}")
        return
    if codigo not in dados["itens"]:
        print(f"ERRO: item '{codigo}' nao encontrado.")
        return

    item = dados["itens"][codigo]
    saldo_atual = obter_saldo(dados, codigo)
    print(
        f"Item: {codigo} - {item['descricao']} | "
        f"Saldo atual: {utils.formatar_numero(saldo_atual)} {item['unidade']}"
    )

    tipo_op = utils.ler_opcao(
        "Tipo [E]ntrada [S]aida [A]juste",
        ("E", "S", "A", "ENTRADA", "SAIDA", "AJUSTE"),
    )
    tipo = MAPA_TIPO_MOV[tipo_op]

    if tipo == "AJUSTE":
        qtd = utils.ler_float(
            "Quantidade de ajuste (positiva ou negativa)",
            permitir_zero=False,
        )
    else:
        qtd = utils.ler_float(
            "Quantidade",
            minimo=0.0,
            permitir_zero=False,
        )

    while True:
        data_bruta = utils.ler_texto(
            "Data (DD/MM/AAAA)",
            padrao=utils.data_hoje(),
        )
        try:
            data_ok = utils.validar_data(data_bruta)
            break
        except ValueError as exc:
            print(f"ERRO: {exc}")

    documento = utils.ler_texto("Documento / motivo")
    try:
        mov = registrar_movimentacao(
            dados,
            codigo,
            tipo,
            qtd,
            documento,
            data_str=data_ok,
        )
        print(
            f"\nMovimentacao registrada! Novo saldo: "
            f"{utils.formatar_numero(mov['saldo_apos'])} {item['unidade']}."
        )
        if mov["saldo_apos"] < item["estoque_seguranca"]:
            print(
                f"ALERTA: saldo ({utils.formatar_numero(mov['saldo_apos'])} "
                f"{item['unidade']}) abaixo do estoque de seguranca "
                f"({utils.formatar_numero(item['estoque_seguranca'])} "
                f"{item['unidade']})."
            )
    except (ValueError, KeyError) as exc:
        print(f"ERRO: {exc}")


def menu_estoque(dados):
    """Submenu de gestao de estoques e consulta de kardex."""
    while True:
        utils.imprimir_cabecalho("GESTAO DE ESTOQUES E KARDEX")
        print("1. Registrar movimentacao (Entrada / Saida / Ajuste)")
        print("2. Consultar saldo e kardex de um item")
        print("3. Listar posicao geral de estoques")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            _fluxo_movimentar(dados)
            utils.pausar()
        elif opcao == "2":
            bruto = utils.ler_texto("Codigo do item")
            try:
                consultar_saldo_kardex(dados, bruto)
            except ValueError as exc:
                print(f"ERRO: {exc}")
            utils.pausar()
        elif opcao == "3":
            listar_posicoes_estoque(dados)
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")

