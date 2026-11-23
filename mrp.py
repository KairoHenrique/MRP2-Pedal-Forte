"""Calculo MRP e exibicao de registros por item (RF08, RF09)."""

import mps
import ordens
import persistencia
import utils


HORIZONTE = mps.HORIZONTE_SEMANAS
ORDEM_TIPOS = ("PA", "SA", "MP")


def _recebimentos_programados_item(dados, codigo_item):
    """Calcula RP (semanas 1..8) de ordens FIRME ou LIBERADA (RN08)."""
    rp = [0.0] * HORIZONTE
    for ordem in dados["ordens"].values():
        if ordem["item"] != codigo_item:
            continue
        if ordem["status"] not in ("FIRME", "LIBERADA"):
            continue
        sem_ent = int(ordem["semana_entrega"])
        if 1 <= sem_ent <= HORIZONTE:
            rp[sem_ent - 1] += float(ordem["quantidade"])
    return rp


def _liberacoes_confirmadas_pai(dados, codigo_pai):
    """Retorna quantidades de OPs FIRME/LIBERADA por semana de liberacao."""
    libs = [0.0] * HORIZONTE
    for ordem in dados["ordens"].values():
        if ordem["item"] != codigo_pai or ordem["tipo"] != "OP":
            continue
        if ordem["status"] not in ("FIRME", "LIBERADA"):
            continue
        sem_lib = max(1, min(HORIZONTE, int(ordem["semana_liberacao"])))
        libs[sem_lib - 1] += float(ordem["quantidade"])
    return libs


def executar_mrp(dados):
    """Executa o calculo completo do MRP na ordem PA -> SA -> MP (RN04-RN08).

    Returns:
        Tupla (registros_mrp, novas_ordens, excecoes).
    """
    ordens.limpar_ordens_planejadas(dados, salvar=False)

    necessidades_brutas = {}
    for cod, item in dados["itens"].items():
        if item["tipo"] == "PA":
            necessidades_brutas[cod] = mps.obter_demanda_mps(dados, cod)
        else:
            necessidades_brutas[cod] = [0.0] * HORIZONTE

    registros = {}
    novas_ordens = []
    excecoes = []

    for tipo_atual in ORDEM_TIPOS:
        codigos = sorted(
            cod
            for cod, item in dados["itens"].items()
            if item["tipo"] == tipo_atual
        )
        for cod in codigos:
            item = dados["itens"][cod]
            nb = list(necessidades_brutas[cod])
            rp = _recebimentos_programados_item(dados, cod)
            estoque_inicial = float(dados["estoque"].get(cod, 0.0))
            es = float(item["estoque_seguranca"])
            lote_min = float(item["lote_minimo"])
            lead_time = int(item["lead_time"])

            ep = [0.0] * HORIZONTE
            nl = [0.0] * HORIZONTE
            rec_plan = [0.0] * HORIZONTE
            lib_plan = [0.0] * HORIZONTE
            # Demanda efetiva por semana (1..8) para explodir aos filhos
            demanda_filhos = [0.0] * HORIZONTE

            for t in range(HORIZONTE):
                ep_ant = estoque_inicial if t == 0 else ep[t - 1]
                nl_t = max(0.0, nb[t] + es - (ep_ant + rp[t]))
                rec_t = max(nl_t, lote_min) if nl_t > 0 else 0.0
                ep_t = ep_ant + rp[t] + rec_t - nb[t]

                nl[t] = nl_t
                rec_plan[t] = rec_t
                ep[t] = ep_t

                if rec_t > 0:
                    sem_entrega = t + 1
                    sem_liberacao = sem_entrega - lead_time
                    if 1 <= sem_liberacao <= HORIZONTE:
                        lib_plan[sem_liberacao - 1] += rec_t

                    bucket_filho = max(1, min(HORIZONTE, sem_liberacao))
                    demanda_filhos[bucket_filho - 1] += rec_t

                    tipo_ordem = "OC" if tipo_atual == "MP" else "OP"
                    ordem = ordens.gerar_ordem(
                        dados,
                        tipo_ordem,
                        cod,
                        rec_t,
                        sem_liberacao,
                        sem_entrega,
                        salvar=False,
                    )
                    novas_ordens.append(ordem)
                    if sem_liberacao < 1:
                        excecoes.append(
                            f"{ordem['numero']} ({cod} - "
                            f"{item['descricao']}): liberacao em "
                            f"S{sem_liberacao} para entrega em S{sem_entrega}."
                        )

            registros[cod] = {
                "codigo": cod,
                "descricao": item["descricao"],
                "lead_time": lead_time,
                "estoque_seguranca": es,
                "lote_minimo": lote_min,
                "estoque_inicial": estoque_inicial,
                "nb": nb,
                "rp": rp,
                "ep": ep,
                "nl": nl,
                "rec_plan": rec_plan,
                "lib_plan": lib_plan,
            }

            if tipo_atual in ("PA", "SA"):
                libs_conf = _liberacoes_confirmadas_pai(dados, cod)
                for comp in dados["estrutura"].get(cod, []):
                    cod_comp = comp["componente"]
                    if cod_comp not in necessidades_brutas:
                        continue
                    fator = float(comp["quantidade"])
                    for idx in range(HORIZONTE):
                        total_pai = demanda_filhos[idx] + libs_conf[idx]
                        necessidades_brutas[cod_comp][idx] += total_pai * fator

    persistencia.salvar_json("ordens.json", dados["ordens"])
    return registros, novas_ordens, excecoes


def exibir_registro_mrp(dados, registros_mrp, codigo_item):
    """Exibe o quadro MRP de 8 semanas para um item escolhido (Mockup 6.4)."""
    cod = utils.validar_codigo_item(codigo_item)
    if cod not in registros_mrp:
        print(f"ERRO: item '{cod}' nao encontrado no calculo MRP.")
        return

    reg = registros_mrp[cod]
    print(f"\nREGISTRO MRP - {cod} {reg['descricao']}")
    print(
        f"Lead time: {reg['lead_time']} sem | "
        f"Est. seguranca: {utils.formatar_numero(reg['estoque_seguranca'])} | "
        f"Lote min.: {utils.formatar_numero(reg['lote_minimo'])} | "
        f"Estoque: {utils.formatar_numero(reg['estoque_inicial'])}"
    )
    print("-" * 72)

    semanas = " ".join(f"{s:>6}" for s in range(1, HORIZONTE + 1))
    print(f"{'Semana':<20} {semanas}")

    linhas = [
        ("Necessidade bruta", reg["nb"]),
        ("Receb. programados", reg["rp"]),
        ("Estoque projetado", reg["ep"]),
        ("Necessidade liquida", reg["nl"]),
        ("Receb. planejados", reg["rec_plan"]),
        ("Liberacao planejada", reg["lib_plan"]),
    ]
    for rotulo, valores in linhas:
        vals_fmt = " ".join(
            f"{utils.formatar_numero(v):>6}" for v in valores
        )
        print(f"{rotulo:<20} {vals_fmt}")

    atrasadas = [
        o
        for o in dados["ordens"].values()
        if o["item"] == cod and o["status"] == "ATRASADA"
    ]
    if atrasadas:
        print("\nAVISO: existem ordens ATRASADAS para este item:")
        for ord_a in atrasadas:
            qtd_a = utils.formatar_numero(ord_a["quantidade"])
            print(
                f"  - {ord_a['numero']}: {qtd_a} "
                f"(liberar em S{ord_a['semana_liberacao']}, "
                f"entrega S{ord_a['semana_entrega']})"
            )


def _exibir_resumo_execucao(novas_ordens, excecoes):
    """Exibe resumo das ordens planejadas e mensagens de excecao."""
    print(
        f"\nMRP executado com sucesso! "
        f"{len(novas_ordens)} ordem(ns) planejada(s) gerada(s)."
    )
    if excecoes:
        print(
            f"\n{len(excecoes)} mensagem(ns) de excecao "
            "(ordens com liberacao antes da semana 1):"
        )
        for msg in excecoes:
            print(f"  ! {msg}")


def menu_mrp(dados, estado_mrp):
    """Submenu para execucao do MRP e consulta dos registros por item."""
    while True:
        utils.imprimir_cabecalho("CALCULO MRP")
        print("1. Executar calculo MRP (recalcular todas as necessidades)")
        print("2. Exibir registro MRP de um item")
        print("3. Listar resumo MRP de todos os itens")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            registros, novas_ordens, excecoes = executar_mrp(dados)
            estado_mrp["registros"] = registros
            estado_mrp["excecoes"] = excecoes
            _exibir_resumo_execucao(novas_ordens, excecoes)
            utils.pausar()
        elif opcao == "2":
            if not estado_mrp.get("registros"):
                registros, _, excecoes = executar_mrp(dados)
                estado_mrp["registros"] = registros
                estado_mrp["excecoes"] = excecoes
            bruto = utils.ler_texto("Codigo do item (ex.: SA-020)")
            try:
                exibir_registro_mrp(dados, estado_mrp["registros"], bruto)
            except ValueError as exc:
                print(f"ERRO: {exc}")
            utils.pausar()
        elif opcao == "3":
            if not estado_mrp.get("registros"):
                registros, _, excecoes = executar_mrp(dados)
                estado_mrp["registros"] = registros
                estado_mrp["excecoes"] = excecoes
            print(
                "\nCodigo   Tipo  Est.Inic   Total NB   Total NL  "
                "Total RecPlan"
            )
            print("-" * 64)
            for cod in sorted(estado_mrp["registros"]):
                reg = estado_mrp["registros"][cod]
                tipo = dados["itens"][cod]["tipo"]
                nb_tot = sum(reg["nb"])
                nl_tot = sum(reg["nl"])
                rp_tot = sum(reg["rec_plan"])
                print(
                    f"{cod:<8} {tipo:<5} "
                    f"{utils.formatar_numero(reg['estoque_inicial']):>8}  "
                    f"{utils.formatar_numero(nb_tot):>9}  "
                    f"{utils.formatar_numero(nl_tot):>9}  "
                    f"{utils.formatar_numero(rp_tot):>13}"
                )
            utils.pausar()
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")
