"""Ordens de producao (OP), compra (OC) e apontamento (RF09, RF10, RF11)."""

import estoque
import persistencia
import utils


STATUS_PLANEJADOS = ("PLANEJADA", "ATRASADA")
STATUS_VALIDOS = (
    "PLANEJADA",
    "ATRASADA",
    "FIRME",
    "LIBERADA",
    "ENCERRADA",
)


def proximo_numero_ordem(ordens, tipo):
    """Retorna o proximo codigo sequencial OP-XXXX ou OC-XXXX."""
    prefixo = f"{tipo}-"
    maior = 0
    for numero in ordens:
        if numero.startswith(prefixo):
            parte = numero[len(prefixo):]
            if parte.isdigit():
                maior = max(maior, int(parte))
    return f"{prefixo}{maior + 1:04d}"


def limpar_ordens_planejadas(dados, salvar=False):
    """Remove ordens nao firmadas (PLANEJADA e ATRASADA) antes do MRP."""
    remover = [
        num
        for num, ord_data in dados["ordens"].items()
        if ord_data["status"] in STATUS_PLANEJADOS
    ]
    for num in remover:
        del dados["ordens"][num]
    if salvar:
        persistencia.salvar_json("ordens.json", dados["ordens"])
    return len(remover)


def gerar_ordem(
    dados,
    tipo,
    codigo_item,
    quantidade,
    semana_liberacao,
    semana_entrega,
    salvar=False,
):
    """Cria uma nova ordem planejada (ou ATRASADA se liberacao < S1)."""
    tipo_norm = tipo.upper()
    if tipo_norm not in ("OP", "OC"):
        raise ValueError("Tipo de ordem invalido. Use OP ou OC.")
    if quantidade <= 0:
        raise ValueError("A quantidade da ordem deve ser maior que zero.")

    numero = proximo_numero_ordem(dados["ordens"], tipo_norm)
    status = "ATRASADA" if semana_liberacao < 1 else "PLANEJADA"
    ordem = {
        "numero": numero,
        "tipo": tipo_norm,
        "item": codigo_item,
        "quantidade": float(quantidade),
        "semana_liberacao": int(semana_liberacao),
        "semana_entrega": int(semana_entrega),
        "status": status,
        "data_criacao": utils.data_hoje(),
    }
    dados["ordens"][numero] = ordem
    if salvar:
        persistencia.salvar_json("ordens.json", dados["ordens"])
    return ordem


def firmar_ordem(dados, numero):
    """Transiciona uma ordem PLANEJADA/ATRASADA para FIRME (RF10)."""
    num = numero.strip().upper()
    if num not in dados["ordens"]:
        raise KeyError(f"Ordem '{num}' nao encontrada.")
    ordem = dados["ordens"][num]
    if ordem["status"] not in STATUS_PLANEJADOS:
        raise ValueError(
            f"Ordem '{num}' esta com status '{ordem['status']}'. "
            "Apenas ordens PLANEJADA ou ATRASADA podem ser firmadas."
        )
    ordem["status"] = "FIRME"
    persistencia.salvar_json("ordens.json", dados["ordens"])
    return ordem


def liberar_ordem(dados, numero):
    """Transiciona uma ordem FIRME para LIBERADA (RF10)."""
    num = numero.strip().upper()
    if num not in dados["ordens"]:
        raise KeyError(f"Ordem '{num}' nao encontrada.")
    ordem = dados["ordens"][num]
    if ordem["status"] != "FIRME":
        raise ValueError(
            f"Ordem '{num}' esta com status '{ordem['status']}'. "
            "Apenas ordens FIRME podem ser liberadas."
        )
    ordem["status"] = "LIBERADA"
    persistencia.salvar_json("ordens.json", dados["ordens"])
    return ordem


def apontar_producao(dados, numero, data_str=None):
    """Aponta a producao total de uma OP liberada (RF11).

    Verifica integralmente os saldos dos componentes antes de baixar o estoque,
    da entrada no item produzido e encerra a OP.
    """
    num = numero.strip().upper()
    if num not in dados["ordens"]:
        raise KeyError(f"Ordem '{num}' nao encontrada.")
    ordem = dados["ordens"][num]
    if ordem["tipo"] != "OP":
        raise ValueError(
            f"Ordem '{num}' e uma OC. Use o recebimento/encerramento de OC."
        )
    if ordem["status"] != "LIBERADA":
        raise ValueError(
            f"Ordem '{num}' esta com status '{ordem['status']}'. "
            "Apenas OPs LIBERADAS podem ser apontadas."
        )

    data_apont = (
        utils.validar_data(data_str) if data_str else utils.data_hoje()
    )
    cod_pai = ordem["item"]
    qtd_op = float(ordem["quantidade"])
    componentes = dados["estrutura"].get(cod_pai, [])

    faltas = []
    consumos = []
    for comp in componentes:
        cod_comp = comp["componente"]
        qtd_nec = qtd_op * float(comp["quantidade"])
        saldo_disp = estoque.obter_saldo(dados, cod_comp)
        if saldo_disp + 1e-9 < qtd_nec:
            un = dados["itens"].get(cod_comp, {}).get("unidade", "un")
            faltas.append(
                f"{cod_comp}: necessario {utils.formatar_numero(qtd_nec)} "
                f"{un}, disponivel {utils.formatar_numero(saldo_disp)} {un}"
            )
        else:
            consumos.append((cod_comp, qtd_nec))

    if faltas:
        detalhes = "; ".join(faltas)
        raise ValueError(
            f"Apontamento rejeitado por falta de componente(s): {detalhes}."
        )

    for cod_comp, qtd_nec in consumos:
        estoque.registrar_movimentacao(
            dados,
            cod_comp,
            "SAIDA",
            qtd_nec,
            f"{num} ({cod_pai})",
            data_str=data_apont,
            salvar=False,
        )

    estoque.registrar_movimentacao(
        dados,
        cod_pai,
        "ENTRADA",
        qtd_op,
        f"Apontamento {num}",
        data_str=data_apont,
        salvar=False,
    )

    ordem["status"] = "ENCERRADA"
    persistencia.salvar_json("estoque.json", dados["estoque"])
    persistencia.salvar_movimentos(dados["movimentos"])
    persistencia.salvar_json("ordens.json", dados["ordens"])
    return ordem


def encerrar_ordem_compra(dados, numero, data_str=None):
    """Recebe uma OC liberada, da entrada no estoque e encerra a ordem."""
    num = numero.strip().upper()
    if num not in dados["ordens"]:
        raise KeyError(f"Ordem '{num}' nao encontrada.")
    ordem = dados["ordens"][num]
    if ordem["tipo"] != "OC":
        raise ValueError(
            f"Ordem '{num}' e uma OP. Use o apontamento de producao."
        )
    if ordem["status"] != "LIBERADA":
        raise ValueError(
            f"Ordem '{num}' esta com status '{ordem['status']}'. "
            "Apenas OCs LIBERADAS podem ser encerradas."
        )

    data_rec = utils.validar_data(data_str) if data_str else utils.data_hoje()
    estoque.registrar_movimentacao(
        dados,
        ordem["item"],
        "ENTRADA",
        ordem["quantidade"],
        f"Recebimento {num}",
        data_str=data_rec,
        salvar=False,
    )
    ordem["status"] = "ENCERRADA"
    persistencia.salvar_json("estoque.json", dados["estoque"])
    persistencia.salvar_movimentos(dados["movimentos"])
    persistencia.salvar_json("ordens.json", dados["ordens"])
    return ordem


def listar_ordens(dados, filtro_status=None, filtro_tipo=None):
    """Exibe a lista de ordens de producao e compra."""
    ordens = sorted(
        dados["ordens"].values(),
        key=lambda o: (o["semana_entrega"], o["numero"]),
    )
    if filtro_status:
        ordens = [o for o in ordens if o["status"] == filtro_status]
    if filtro_tipo:
        ordens = [o for o in ordens if o["tipo"] == filtro_tipo]

    print(f"\nORDENS DE PRODUCAO E COMPRA ({len(ordens)} exibida(s))")
    if not ordens:
        print("Nenhuma ordem encontrada.")
        return

    print("Ordem     Tipo  Item       Qtde  Liberar  Entregar  Status")
    print("-" * 62)
    atrasadas = 0
    for ordem in ordens:
        if ordem["status"] == "ATRASADA":
            atrasadas += 1
        qtd_fmt = utils.formatar_numero(ordem["quantidade"])
        lib_fmt = f"S{ordem['semana_liberacao']}"
        ent_fmt = f"S{ordem['semana_entrega']}"
        print(
            f"{ordem['numero']:<9} {ordem['tipo']:<5} {ordem['item']:<8} "
            f"{qtd_fmt:>6}  {lib_fmt:<7}  {ent_fmt:<8}  {ordem['status']}"
        )

    if atrasadas:
        print(
            f"\n{atrasadas} ordem(ns) com liberacao antes da semana 1 "
            "(ATRASADA)."
        )


def menu_ordens(dados):
    """Submenu interativo para consulta e ciclo de vida das ordens."""
    filtro_status = None
    while True:
        utils.imprimir_cabecalho("ORDENS DE PRODUCAO E COMPRA")
        listar_ordens(dados, filtro_status=filtro_status)
        if filtro_status:
            print(f"\n[Filtro ativo: status = {filtro_status}]")
        print(
            "\n[F] Firmar  [L] Liberar  [A] Apontar producao (OP)  "
            "[E] Receber/Encerrar OC  [T] Filtrar  [V] Voltar"
        )
        acao = input("Escolha uma acao: ").strip().upper()
        if acao == "V":
            break
        elif acao == "T":
            print(
                "Status: TODOS, PLANEJADA, ATRASADA, "
                "FIRME, LIBERADA, ENCERRADA"
            )
            esc = utils.ler_texto("Filtrar por status", padrao="TODOS").upper()
            if esc == "TODOS":
                filtro_status = None
            elif esc in STATUS_VALIDOS:
                filtro_status = esc
            else:
                print("ERRO: status invalido.")
                utils.pausar()
        elif acao in ("F", "L", "A", "E"):
            numero = utils.ler_texto("Numero da ordem (ex.: OP-0001)")
            try:
                if acao == "F":
                    ord_atu = firmar_ordem(dados, numero)
                    print(f"Ordem {ord_atu['numero']} firmada com sucesso.")
                elif acao == "L":
                    ord_atu = liberar_ordem(dados, numero)
                    print(f"Ordem {ord_atu['numero']} liberada com sucesso.")
                elif acao == "A":
                    ord_atu = apontar_producao(dados, numero)
                    print(
                        f"Apontamento da {ord_atu['numero']} concluido e "
                        "OP encerrada!"
                    )
                elif acao == "E":
                    ord_atu = encerrar_ordem_compra(dados, numero)
                    print(
                        f"Recebimento da {ord_atu['numero']} registrado e "
                        "OC encerrada!"
                    )
            except (ValueError, KeyError) as exc:
                print(f"ERRO: {exc}")
            utils.pausar()
        else:
            print("ERRO: acao invalida.")
