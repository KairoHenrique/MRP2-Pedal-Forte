"""Menus e navegacao principal do sistema MRP II (RF01)."""

import capacidade
import custos
import estoque
import estrutura
import graficos
import itens
import mps
import mrp
import ordens
import persistencia
import relatorios
import utils


def menu_cadastros(dados):
    """Submenu de cadastros basicos (itens, BOM, centros e roteiros)."""
    while True:
        utils.imprimir_cabecalho("CADASTROS")
        print("1. Itens (PA, SA, MP)")
        print("2. Estrutura de Produto (BOM)")
        print("3. Centros de Trabalho e Roteiros")
        print("0. Voltar")
        opcao = input("\nEscolha uma opcao: ").strip()
        if opcao == "1":
            itens.menu_itens(dados)
        elif opcao == "2":
            estrutura.menu_estrutura(dados)
        elif opcao == "3":
            capacidade.menu_cadastros_capacidade(dados)
        elif opcao == "0":
            break
        else:
            print("ERRO: opcao invalida.")


def exibir_menu_principal():
    """Exibe as opcoes do menu principal conforme referencia do projeto."""
    print("\n" + "=" * 54)
    print("  MRP II - PEDAL FORTE BICICLETAS")
    print("=" * 54)
    print("1. Cadastros (itens, estrutura, centros, roteiros)")
    print("2. Estoque (movimentar, saldo, kardex)")
    print("3. Plano Mestre de Producao (MPS)")
    print("4. Executar MRP")
    print("5. Ordens de producao e de compra")
    print("6. Carga x capacidade (CRP)")
    print("7. Custo padrao dos produtos")
    print("8. Relatorios (exportar CSV)")
    print("9. Graficos de gestao (matplotlib)")
    print("0. Sair")
    print("-" * 54)


def executar_menu_principal(dados):
    """Loop principal de navegacao do sistema."""
    estado_mrp = {"registros": {}, "excecoes": []}

    while True:
        exibir_menu_principal()
        try:
            opcao = input("Escolha uma opcao: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando sistema e salvando dados...")
            persistencia.salvar_todos_dados(dados)
            break

        if opcao == "1":
            menu_cadastros(dados)
        elif opcao == "2":
            estoque.menu_estoque(dados)
        elif opcao == "3":
            mps.menu_mps(dados)
        elif opcao == "4":
            mrp.menu_mrp(dados, estado_mrp)
        elif opcao == "5":
            ordens.menu_ordens(dados)
        elif opcao == "6":
            capacidade.menu_crp(dados)
        elif opcao == "7":
            custos.menu_custos(dados)
        elif opcao == "8":
            relatorios.menu_relatorios(dados)
        elif opcao == "9":
            graficos.menu_graficos(dados, estado_mrp)
        elif opcao == "0":
            persistencia.salvar_todos_dados(dados)
            print("\nDados salvos com sucesso. Ate logo!")
            break
        else:
            print("ERRO: opcao invalida. Escolha um numero de 0 a 9.")

