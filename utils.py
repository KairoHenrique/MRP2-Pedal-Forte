"""Utilitarios de validacao de entradas e formatacao para o sistema MRP II."""

from datetime import datetime
import re


PADRAO_CODIGO_ITEM = re.compile(r"^(PA|SA|MP)-(\d+)$")
PADRAO_CODIGO_CENTRO = re.compile(r"^CT-(\d+)$")


def validar_codigo_item(codigo, tipo_esperado=None):
    """Valida se o codigo do item segue o padrao Tipo-Numero (RN01).

    Args:
        codigo: String informada pelo usuario.
        tipo_esperado: Tipo esperado ('PA', 'SA' ou 'MP'), se aplicavel.

    Returns:
        Codigo normalizado em maiusculas.

    Raises:
        ValueError: Se o formato ou o tipo for invalido.
    """
    codigo_norm = codigo.strip().upper()
    match = PADRAO_CODIGO_ITEM.match(codigo_norm)
    if not match:
        raise ValueError(
            "Codigo invalido. Use o formato Tipo-Numero "
            "(ex.: PA-001, SA-020, MP-201)."
        )
    tipo_codigo = match.group(1)
    if tipo_esperado and tipo_codigo != tipo_esperado:
        raise ValueError(
            f"O codigo '{codigo_norm}' nao corresponde ao tipo "
            f"'{tipo_esperado}'."
        )
    return codigo_norm


def validar_codigo_centro(codigo):
    """Valida o codigo de um centro de trabalho no formato CT-Numero."""
    codigo_norm = codigo.strip().upper()
    if not PADRAO_CODIGO_CENTRO.match(codigo_norm):
        raise ValueError(
            "Codigo de centro invalido. Use o formato CT-Numero "
            "(ex.: CT-01)."
        )
    return codigo_norm


def validar_data(texto_data):
    """Valida uma data no formato DD/MM/AAAA."""
    texto = texto_data.strip()
    try:
        datetime.strptime(texto, "%d/%m/%Y")
    except ValueError as exc:
        raise ValueError("Data invalida. Use o formato DD/MM/AAAA.") from exc
    return texto


def data_hoje():
    """Retorna a data atual formatada em DD/MM/AAAA."""
    return datetime.now().strftime("%d/%m/%Y")


def ler_texto(mensagem, obrigatorio=True, padrao=None):
    """Le uma string do usuario com suporte a valor padrao."""
    while True:
        sufixo = f" [{padrao}]" if padrao is not None else ""
        valor = input(f"{mensagem}{sufixo}: ").strip()
        if not valor and padrao is not None:
            return padrao
        if obrigatorio and not valor:
            print("ERRO: este campo e obrigatorio.")
            continue
        return valor


def ler_opcao(mensagem, opcoes_validas):
    """Le uma opcao dentre um conjunto de strings validas."""
    validas = {op.upper() for op in opcoes_validas}
    while True:
        valor = input(f"{mensagem}: ").strip().upper()
        if valor in validas:
            return valor
        opcoes_fmt = ", ".join(sorted(validas))
        print(f"ERRO: opcao invalida. Escolha entre: {opcoes_fmt}.")


def ler_float(
    mensagem,
    minimo=None,
    maximo=None,
    permitir_zero=True,
    padrao=None,
):
    """Le um numero decimal validando faixa e formato (aceita virgula)."""
    while True:
        sufixo = f" [{formatar_numero(padrao)}]" if padrao is not None else ""
        bruto = input(f"{mensagem}{sufixo}: ").strip()
        if not bruto and padrao is not None:
            return float(padrao)
        try:
            valor = float(bruto.replace(",", "."))
        except ValueError:
            print("ERRO: informe um numero valido.")
            continue
        if not permitir_zero and valor == 0:
            print("ERRO: o valor nao pode ser zero.")
            continue
        if minimo is not None and valor < minimo:
            print(f"ERRO: o valor deve ser maior ou igual a {minimo}.")
            continue
        if maximo is not None and valor > maximo:
            print(f"ERRO: o valor deve ser menor ou igual a {maximo}.")
            continue
        return valor


def ler_int(mensagem, minimo=None, maximo=None, padrao=None):
    """Le um numero inteiro validando faixa."""
    while True:
        sufixo = f" [{padrao}]" if padrao is not None else ""
        bruto = input(f"{mensagem}{sufixo}: ").strip()
        if not bruto and padrao is not None:
            return int(padrao)
        try:
            valor = int(bruto)
        except ValueError:
            print("ERRO: informe um numero inteiro valido.")
            continue
        if minimo is not None and valor < minimo:
            print(f"ERRO: o valor deve ser maior ou igual a {minimo}.")
            continue
        if maximo is not None and valor > maximo:
            print(f"ERRO: o valor deve ser menor ou igual a {maximo}.")
            continue
        return valor


def ler_sim_nao(mensagem, padrao="N"):
    """Le confirmacao S/N do usuario e retorna booleano."""
    while True:
        resp = input(f"{mensagem} (S/N) [{padrao}]: ").strip().upper()
        if not resp:
            resp = padrao.upper()
        if resp in ("S", "SIM"):
            return True
        if resp in ("N", "NAO", "NÃO"):
            return False
        print("ERRO: responda com S ou N.")


def formatar_numero(valor):
    """Formata numero com virgula decimal sem zeros desnecessarios."""
    if abs(valor - round(valor)) < 1e-9:
        return str(int(round(valor)))
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def formatar_moeda(valor):
    """Formata valor monetario no padrao brasileiro (R$ 0,00)."""
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def imprimir_cabecalho(titulo):
    """Imprime um cabecalho padronizado para telas de modo texto."""
    linha = "=" * 62
    print(f"\n{linha}")
    print(f"  {titulo}")
    print(linha)


def pausar():
    """Aguarda o usuario pressionar Enter para continuar."""
    input("\nPressione Enter para continuar...")

