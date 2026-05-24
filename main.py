# main.py  —  Ponto de entrada do sistema Desafio na Cozinha

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')    # Garante o uso e exibição de acentos e símbolos

# Garante que a raiz do projeto está no path
_RAIZ = Path(__file__).resolve().parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from modelos.receita import Receita
from modelos.categoria import Categoria
from modelos.ingredientes import Ingredientes

from data.data_manager import carregar_dados, salvar_dados
from motor.algoritmo_recomendações import AlgoritmoRecomendacao
from motor.busca_geral import TrieBuscaGeral 


def montar_motor(lista_receitas) -> AlgoritmoRecomendacao:
    """Cria e popula o motor de recomendação com todas as receitas."""
    motor = AlgoritmoRecomendacao()
    for receita in lista_receitas:
        motor.adicionar_receita(receita)
    motor._reordenar_se_necessario()
    return motor


def _pedir_lista(prompt: str) -> list[str]:
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


def menu_busca_geral(trie_global: TrieBuscaGeral) -> None:
    """Menu dedicado a buscar nomes e prefixos instantaneamente na Trie."""
    print("\n" + "═" * 55)
    print("  BUSCA GERAL (NOME OU PREFIXO)")
    print("═" * 55)
    
    prefixo = input("  Digite o termo de busca: ").strip().lower()
    if not prefixo:
        return
        
    no_resultado = trie_global.get_node(prefixo)
    
    if not no_resultado:
        print(f"\n  ✗ Nenhum resultado encontrado para '{prefixo}'.")
        return
        
    # Coleta e separa os dados alfabeticamente
    dados = trie_global.get_all_separated_alphabetically(no_resultado)
    
    total = len(dados['Receita']) + len(dados['Ingredientes']) + len(dados['Categoria'])
    print(f"\n  ✓ {total} resultado(s) encontrado(s) para '{prefixo}':\n")
    
    if dados['Receita']:
        print("  [ RECEITAS ]")
        for r in dados['Receita']:
            print(f"   - {r.nome_receita}")
            
    if dados['Categoria']:
        print("\n  [ CATEGORIAS ]")
        for c in dados['Categoria']:
            print(f"   - {c.nome_categoria}")
            
    if dados['Ingredientes']:
        print("\n  [ INGREDIENTES ]")
        for i in dados['Ingredientes']:
            print(f"   - {i.nome_ingrediente}")
    print()


def menu_adicionar_receita(motor: AlgoritmoRecomendacao, lista_receitas: list, trie_global: TrieBuscaGeral) -> None:
    print("\n" + "═" * 55)
    print("  CRIAR NOVA RECEITA")
    print("═" * 55)
    
    nome = input("  Nome da receita: ").strip()
    if not nome:
        print("  ⚠ Operação cancelada: Nome não pode ser vazio.")
        return

    tempo = _pedir_inteiro("  Tempo de preparo (min) [padrão=0]: ") or 0
    custo = _pedir_inteiro("  Custo (centavos de dólar) [padrão=0]: ") or 0

    # 1. TENTA CRIAR A RECEITA (Passando a Trie para inserção automática)
    try:
        nova_receita = Receita(nome_receita=nome, custo=custo, tempo_preparo=tempo, fator_recomendacao=0.0, trie_global=trie_global)
    except ValueError as e:
        print(f"  ⚠ Erro: {e}")
        return 

    # 2. ADICIONA CATEGORIAS
    cats = _pedir_lista("  Categorias (sep. vírgula) [deixe em branco para pular]: ")
    for cat in cats:
        nova_receita.adicionar_categoria(cat)
        # Sincronia: Garante que se a categoria for nova, ela vai para a Trie
        c_obj = Categoria.registro_global[cat.lower()]
        no_cat = trie_global.get_node(cat.lower())
        if not no_cat or c_obj not in (no_cat.objetos or []):
            trie_global.insert(cat.lower(), c_obj)

    # 3. ADICIONA INGREDIENTES
    print("\n  -- Ingredientes -- (Deixe o nome em branco para encerrar)")
    while True:
        ing_nome = input("  Nome do ingrediente: ").strip()
        if not ing_nome:
            break
            
        qtd = _pedir_inteiro("  Quantidade (número) [padrão=1]: ") or 1
        unidade = input("  Unidade (ex: g, ml, xícara) [padrão=und]: ").strip() or "und"
        
        nova_receita.adicionar_ingrediente(nome_ingrediente=ing_nome, unidade=unidade, quantidade=qtd)
        # Sincronia: Garante que se o ingrediente for novo, ele vai para a Trie
        i_obj = Ingredientes.registro_global[ing_nome.lower()]
        no_ing = trie_global.get_node(ing_nome.lower())
        if not no_ing or i_obj not in (no_ing.objetos or []):
            trie_global.insert(ing_nome.lower(), i_obj)

    # 4. SALVAMENTO E SINCRONIA GERAL
    lista_receitas.append(nova_receita)
    motor.adicionar_receita(nova_receita)
    
    print(f"\n  ✓ Receita '{nome}' criada com sucesso!")


def menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente, trie_global):
    while True:
        print("\n╔" + "═" * 44 + "╗")
        print("║     DESAFIO NA COZINHA — MENU PRINCIPAL    ║")
        print("╠" + "═" * 44 + "╣")
        print("║  1. Ver vetor de recomendações (ordenado)  ║")
        print("║  2. Obter recomendação                     ║")
        print("║  3. Busca Geral (Nome/Prefixo)             ║")
        print("║  4. Adicionar nova receita                 ║")
        print("║  5. Salvar estado atual                    ║")
        print("║  0. Sair                                   ║")
        print("╚" + "═" * 44 + "╝")
        opcao = input("  Opção: ").strip()

        if opcao == "1":
            motor.exibir_lista(limite=15)
        elif opcao == "2":
            menu_recomendacao(motor)
        elif opcao == "3":
            menu_busca_geral(trie_global)
        elif opcao == "4":
            menu_adicionar_receita(motor, lista_receitas, trie_global)
        elif opcao == "5":
            salvar_dados(lista_receitas, lista_ingredientes,
                         lista_categorias, mapa_id_ingrediente)
        elif opcao == "0":
            print("  Encerrando. Até logo!")
            break
        else:
            print("  Opção inválida.\n")


def main():
    print("\n" + "═" * 55)
    print("  INICIALIZAÇÃO DO SISTEMA")
    print("═" * 55)
    print("  Qual base de dados você deseja carregar?")
    print("  [1] Dados de Fábrica (dados_fonte.json)")
    print("  [2] Dados Salvos (dados_salvos.json)")
    
    escolha = input("  Opção [padrão=1]: ").strip()
    carregar_dados_salvos = (escolha == "2")
    
    print("\nCarregando dados do disco...")
    lista_receitas, lista_ingredientes, lista_categorias, mapa_id_ingrediente = \
        carregar_dados(usar_salvos=carregar_dados_salvos)
        
    print(f"  ✓ {len(lista_receitas)} receitas | "
          f"{len(lista_ingredientes)} ingredientes | "
          f"{len(lista_categorias)} categorias")

    print("\nMontando os motores de processamento...")
    # Montamos o motor de recomendação
    motor = montar_motor(lista_receitas)
    
    # Montamos o motor de busca (Trie)
    trie_global = TrieBuscaGeral()
    for r in lista_receitas:
        trie_global.insert(r.nome_receita.lower(), r)
    for c in lista_categorias:
        trie_global.insert(c.nome_categoria.lower(), c)
    for i in lista_ingredientes:
        trie_global.insert(i.nome_ingrediente.lower(), i)
        
    print("  ✓ Motores prontos!\n")

    # Iniciamos o loop principal do programa
    menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente, trie_global)


if __name__ == "__main__":
    main()