"""Geracao de graficos de gestao e acompanhamento com matplotlib (RF16)."""

import matplotlib
import matplotlib.pyplot as plt

import capacidade
import estoque
import mrp
import persistencia
import utils


def _finalizar_grafico(fig, nome_arquivo, exibir=True):
    """Salva o grafico em PNG na pasta docs/graficos/ e exibe na tela."""
    persistencia.garantir_diretorios()
    caminho = persistencia.GRAFICOS_DIR / nome_arquivo
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    if exibir and matplotlib.get_backend().lower() != "agg":
        try:
            plt.show()
        except Exception as exc:
            print(f"AVISO: nao foi possivel exibir a janela grafica ({exc}).")
    plt.close(fig)
    return caminho


def grafico_posicao_estoque(dados, exibir=True):
    """Gera grafico de barras: saldo atual x estoque de seguranca (RF16.1)."""
    itens = sorted(dados["itens"].values(), key=lambda i: i["codigo"])
    if not itens:
        raise ValueError("Nao ha itens cadastrados para gerar o grafico.")

    codigos = [i["codigo"] for i in itens]
    saldos = [estoque.obter_saldo(dados, c) for c in codigos]
    segurancas = [float(i["estoque_seguranca"]) for i in itens]

    posicoes = list(range(len(codigos)))
    largura = 0.38

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(
        [p - largura / 2 for p in posicoes],
        saldos,
        width=largura,
        label="Saldo atual",
        color="#2563eb",
    )
    ax.bar(
        [p + largura / 2 for p in posicoes],
        segurancas,
        width=largura,
        label="Estoque de seguranca",
        color="#f59e0b",
    )

    ax.set_title("Posicao de Estoque: Saldo Atual x Estoque de Seguranca")
    ax.set_xlabel("Itens")
    ax.set_ylabel("Quantidade")
    ax.set_xticks(posicoes)
    ax.set_xticklabels(codigos, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    return _finalizar_grafico(fig, "01_posicao_estoque.png", exibir=exibir)


def grafico_estoque_projetado(dados, registros_mrp, codigo_item, exibir=True):
    """Gera grafico de estoque projetado nas 8 semanas do MRP (RF16.2)."""
    cod = utils.validar_codigo_item(codigo_item)
    if cod not in registros_mrp:
        raise KeyError(f"Item '{cod}' nao encontrado nos registros do MRP.")

    reg = registros_mrp[cod]
    semanas = [f"S{s}" for s in range(1, mrp.HORIZONTE + 1)]
    ep = reg["ep"]
    es = reg["estoque_seguranca"]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(
        semanas,
        ep,
        marker="o",
        linewidth=2.2,
        color="#16a34a",
        label="Estoque projetado",
    )
    ax.axhline(
        y=es,
        color="#dc2626",
        linestyle="--",
        linewidth=1.8,
        label=f"Estoque de seguranca ({utils.formatar_numero(es)})",
    )

    for idx, valor in enumerate(ep):
        ax.annotate(
            utils.formatar_numero(valor),
            (idx, valor),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=9,
        )

    ax.set_title(f"Estoque Projetado (8 semanas) - {cod} {reg['descricao']}")
    ax.set_xlabel("Semana")
    ax.set_ylabel("Quantidade")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    nome = f"02_estoque_projetado_{cod}.png"
    return _finalizar_grafico(fig, nome, exibir=exibir)


def grafico_ordens_por_semana(dados, exibir=True):
    """Gera barras empilhadas de OP e OC por semana de entrega (RF16.3)."""
    semanas_num = list(range(1, mrp.HORIZONTE + 1))
    rotulos = [f"S{s}" for s in semanas_num]
    ops_sem = [0] * mrp.HORIZONTE
    ocs_sem = [0] * mrp.HORIZONTE

    for ordem in dados["ordens"].values():
        if ordem["status"] == "ENCERRADA":
            continue
        ent = int(ordem["semana_entrega"])
        if 1 <= ent <= mrp.HORIZONTE:
            if ordem["tipo"] == "OP":
                ops_sem[ent - 1] += 1
            elif ordem["tipo"] == "OC":
                ocs_sem[ent - 1] += 1

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(rotulos, ops_sem, label="Ordens de Producao (OP)", color="#2563eb")
    ax.bar(
        rotulos,
        ocs_sem,
        bottom=ops_sem,
        label="Ordens de Compra (OC)",
        color="#14b8a6",
    )

    ax.set_title("Ordens por Semana de Entrega (OP x OC)")
    ax.set_xlabel("Semana de Entrega")
    ax.set_ylabel("Quantidade de Ordens")
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    return _finalizar_grafico(fig, "03_ordens_por_semana.png", exibir=exibir)


def grafico_carga_capacidade(dados, codigo_centro, exibir=True):
    """Gera grafico Carga x Capacidade destacando sobrecargas (RF16.4)."""
    cod = utils.validar_codigo_centro(codigo_centro)
    crp = capacidade.calcular_crp(dados)
    if cod not in crp:
        raise KeyError(f"Centro de trabalho '{cod}' nao encontrado.")

    info = crp[cod]
    centro = dados["centros"][cod]
    semanas = [f"S{s}" for s in range(1, mrp.HORIZONTE + 1)]
    cargas = info["cargas"]
    cap = info["capacidade"]
    cores = [
        "#dc2626" if (idx + 1) in info["sobrecargas"] else "#2563eb"
        for idx in range(mrp.HORIZONTE)
    ]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    barras = ax.bar(semanas, cargas, color=cores, label="Carga alocada (h)")
    ax.axhline(
        y=cap,
        color="#f59e0b",
        linestyle="--",
        linewidth=2.0,
        label=f"Capacidade ({utils.formatar_numero(cap)} h/sem)",
    )

    for barra, valor in zip(barras, cargas):
        ax.annotate(
            f"{valor:.1f}h",
            (barra.get_x() + barra.get_width() / 2, valor),
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
            fontsize=8.5,
        )

    ax.set_title(
        f"Carga x Capacidade - {cod} {centro['descricao']} "
        "(vermelho = sobrecarga)"
    )
    ax.set_xlabel("Semana")
    ax.set_ylabel("Horas")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    nome = f"04_crp_{cod}.png"
    return _finalizar_grafico(fig, nome, exibir=exibir)


def menu_graficos(dados, estado_mrp):
    """Submenu para geracao dos graficos gerenciais em PNG."""
    while True:
        utils.imprimir_cabecalho("GRAFICOS DE GESTAO (MATPLOTLIB)")
        print("1. Posicao de estoque (Saldo x Estoque de seguranca)")
        print("2. Estoque projetado de um item (8 semanas do MRP)")
        print("3. Ordens de producao e compra por semana de entrega")
        print("4. Carga x capacidade de um centro de trabalho")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        try:
            if opcao == "1":
                arq = grafico_posicao_estoque(dados)
                print(f"\nGrafico salvo em:\n  {arq}")
                utils.pausar()
            elif opcao == "2":
                if not estado_mrp.get("registros"):
                    regs, _, exc = mrp.executar_mrp(dados)
                    estado_mrp["registros"] = regs
                    estado_mrp["excecoes"] = exc
                bruto = utils.ler_texto("Codigo do item (ex.: SA-020)")
                arq = grafico_estoque_projetado(
                    dados, estado_mrp["registros"], bruto
                )
                print(f"\nGrafico salvo em:\n  {arq}")
                utils.pausar()
            elif opcao == "3":
                if not dados["ordens"]:
                    regs, _, exc = mrp.executar_mrp(dados)
                    estado_mrp["registros"] = regs
                    estado_mrp["excecoes"] = exc
                arq = grafico_ordens_por_semana(dados)
                print(f"\nGrafico salvo em:\n  {arq}")
                utils.pausar()
            elif opcao == "4":
                capacidade.listar_centros(dados)
                bruto = utils.ler_texto("\nCodigo do centro (ex.: CT-03)")
                arq = grafico_carga_capacidade(dados, bruto)
                print(f"\nGrafico salvo em:\n  {arq}")
                utils.pausar()
            elif opcao == "0":
                break
            else:
                print("ERRO: opcao invalida.")
        except (ValueError, KeyError) as exc:
            print(f"ERRO: {exc}")
            utils.pausar()

