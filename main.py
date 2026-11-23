"""Ponto de entrada do Sistema MRP II - Pedal Forte Bicicletas."""

from pathlib import Path
import sys


DIRETORIO_PROJETO = Path(__file__).resolve().parent
if str(DIRETORIO_PROJETO) not in sys.path:
    sys.path.insert(0, str(DIRETORIO_PROJETO))

import menu  # noqa: E402
import persistencia  # noqa: E402


def main():
    """Carrega os dados persistidos e inicia a interface em modo texto."""
    dados = persistencia.carregar_todos_dados()
    try:
        menu.executar_menu_principal(dados)
    except (EOFError, KeyboardInterrupt):
        persistencia.salvar_todos_dados(dados)
        print("\nExecucao interrompida. Dados salvos com sucesso.")


if __name__ == "__main__":
    main()
