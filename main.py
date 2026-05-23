# main.py  —  Ponto de entrada do sistema Desafio na Cozinha

import sys
from pathlib import Path

# Garante que a raiz do projeto está no path
_RAIZ = Path(__file__).resolve().parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from data.load_source                  import carregar_dados, salvar_dados
from motor.algoritmo_recomendações     import AlgoritmoRecomendacao


def montar_motor(lista_receitas, mapa_id_ingrediente) -> AlgoritmoRecomendacao:
    """Cria e popula o motor de recomendação com todas as receitas."""
    motor = AlgoritmoRecomendacao(mapa_id_ingrediente)
    for receita in lista_receitas:
        motor.adicionar_receita(receita)
    # força ordenação inicial (abaixa o flag)
    motor._reordenar_se_necessario()
    return motor


def _pedir_lista(prompt: str) -> list[str]:
    """Lê uma linha e devolve lista de itens separados por vírgula."""
    entrada = input(prompt).strip()
    if not entrada:
        return []
    return [item.strip() for item in entrada.split(",") if item.strip()]


def _pedir_inteiro(prompt: str) -> int | None:
    entrada = input(prompt).strip()
    if not entrada:
        return None
    try:
        return int(entrada)
    except ValueError:
        print("  ⚠ Valor inválido, ignorado.")
        return None


def menu_recomendacao(motor: AlgoritmoRecomendacao) -> None:
    print("\n" + "═" * 55)
    print("  RECOMENDAÇÃO DE RECEITAS")
    print("═" * 55)
    print("  Deixe em branco para ignorar um filtro.\n")

    tempo   = _pedir_inteiro("  Tempo máximo de preparo (min): ")
    custo   = _pedir_inteiro("  Custo máximo (centavos de dólar): ")
    qtd     = _pedir_inteiro("  Quantas recomendações? [padrão=1]: ") or 1
    proib   = _pedir_lista("  Ingredientes proibidos (sep. vírgula): ")
    exig    = _pedir_lista("  Ingredientes exigidos  (sep. vírgula): ")
    cats    = _pedir_lista("  Categorias exigidas    (sep. vírgula): ")

    print()
    resultados = motor.recomendar(
        quantidade=qtd,
        tempo_maximo=tempo,
        custo_maximo=custo,
        ingredientes_proibidos=proib,
        ingredientes_exigidos=exig,
        categorias_exigidas=cats,
    )
    motor.exibir_recomendacao(resultados)


def menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente):
    while True:
        print("╔" + "═" * 43 + "╗")
        print("║     DESAFIO NA COZINHA — MENU PRINCIPAL    ║")
        print("╠" + "═" * 43 + "╣")
        print("║  1. Ver vetor de recomendações (ordenado)  ║")
        print("║  2. Obter recomendação                     ║")
        print("║  3. Salvar estado atual                    ║")
        print("║  0. Sair                                   ║")
        print("╚" + "═" * 43 + "╝")
        opcao = input("  Opção: ").strip()

        if opcao == "1":
            motor.exibir_lista(limite=15)

        elif opcao == "2":
            menu_recomendacao(motor)

        elif opcao == "3":
            salvar_dados(lista_receitas, lista_ingredientes,
                         lista_categorias, mapa_id_ingrediente)

        elif opcao == "0":
            print("  Encerrando. Até logo!")
            break
        else:
            print("  Opção inválida.\n")


def main():
    print("\nCarregando dados...")
    lista_receitas, lista_ingredientes, lista_categorias, mapa_id_ingrediente = \
        carregar_dados()
    print(f"  ✓ {len(lista_receitas)} receitas | "
          f"{len(lista_ingredientes)} ingredientes | "
          f"{len(lista_categorias)} categorias\n")

    motor = montar_motor(lista_receitas, mapa_id_ingrediente)

    menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente)


if __name__ == "__main__":
    main()