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
from motor.busca_id import TabelaHashNomes, construir_tabela_hash


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
    
    # Loop interativo da recomendação
    while True:
        motor.exibir_recomendacao(resultados)
        
        if not resultados:
            break # Sai direto se a busca não encontrou nada
            
        escolha = _pedir_inteiro("  Digite o número da receita para explorar (0 para voltar): ")
        if escolha == 0 or escolha is None:
            break
        elif 1 <= escolha <= len(resultados):
            menu_visualizar_receita(resultados[escolha - 1])
        else:
            print("  ⚠ Opção inválida.\n")


def menu_busca_geral(trie_global: TrieBuscaGeral) -> None:
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
        
    dados = trie_global.get_all_separated_alphabetically(no_resultado)
    total = len(dados['Receita']) + len(dados['Ingredientes']) + len(dados['Categoria'])
    
    if total == 0:
        print(f"\n  ✗ Nenhum resultado encontrado para '{prefixo}'.")
        return

    # Um loop para permitir que o usuário explore vários itens da busca e volte pra cá
    while True:
        print(f"\n  ✓ {total} resultado(s) encontrado(s) para '{prefixo}':\n")
        
        opcoes = {}
        contador = 1
        
        if dados['Receita']:
            print("  [ RECEITAS ]")
            for r in dados['Receita']:
                print(f"   {contador}. {r.nome_receita}")
                opcoes[contador] = ('receita', r)
                contador += 1
                
        if dados['Categoria']:
            print("\n  [ CATEGORIAS ]")
            for c in dados['Categoria']:
                print(f"   {contador}. {c.nome_categoria}")
                opcoes[contador] = ('categoria', c)
                contador += 1
                
        if dados['Ingredientes']:
            print("\n  [ INGREDIENTES ]")
            for i in dados['Ingredientes']:
                print(f"   {contador}. {i.nome_ingrediente}")
                opcoes[contador] = ('ingrediente', i)
                contador += 1

        escolha = _pedir_inteiro("\n  Digite o número para inspecionar (0 para sair da busca): ")
        
        if escolha == 0 or escolha is None:
            break
        elif escolha in opcoes:
            tipo, obj = opcoes[escolha]
            if tipo == 'receita':
                menu_visualizar_receita(obj)
            elif tipo == 'categoria':
                menu_visualizar_categoria(obj)
            elif tipo == 'ingrediente':
                menu_visualizar_ingrediente(obj)
        else:
            print("  ⚠ Opção inválida.")


def menu_busca_hash(tabela_hash: TabelaHashNomes) -> None:
    """Menu de busca por nome exato via Tabela Hash com suporte interativo."""
    print("\n" + "=" * 55)
    print("  BUSCA POR NOME EXATO (TABELA HASH)")
    print("=" * 55)

    nome = input("  Digite o nome exato: ").strip()
    if not nome:
        return

    resultados = tabela_hash.buscar(nome) # Agora retorna uma lista!

    if not resultados:
        print(f"\n  ✗ Nenhum resultado para '{nome}'.")
        return

    while True:
        print(f"\n  ✓ {len(resultados)} resultado(s) encontrado(s) para '{nome}':\n")
        
        opcoes = {}
        contador = 1
        
        for obj in resultados:
            from modelos.receita import Receita
            from modelos.categoria import Categoria
            from modelos.ingredientes import Ingredientes
            
            if isinstance(obj, Receita):
                print(f"   {contador}. [RECEITA] {obj.nome_receita}")
            elif isinstance(obj, Categoria):
                print(f"   {contador}. [CATEGORIA] {obj.nome_categoria}")
            elif isinstance(obj, Ingredientes):
                print(f"   {contador}. [INGREDIENTE] {obj.nome_ingrediente}")
                
            opcoes[contador] = obj
            contador += 1
            
        escolha = _pedir_inteiro("\n  Digite o número para inspecionar (0 para sair da busca): ")
        
        if escolha == 0 or escolha is None:
            break
        elif escolha in opcoes:
            obj_escolhido = opcoes[escolha]
            if isinstance(obj_escolhido, Receita):
                menu_visualizar_receita(obj_escolhido)
            elif isinstance(obj_escolhido, Categoria):
                menu_visualizar_categoria(obj_escolhido)
            elif isinstance(obj_escolhido, Ingredientes):
                menu_visualizar_ingrediente(obj_escolhido)
        else:
            print("  ⚠ Opção inválida.")


def menu_diagnostico_hash(tabela_hash: TabelaHashNomes) -> None:
    """Exibe o estado fisico da tabela hash (comando de diagnostico)."""
    tabela_hash.diagnostico("DIAGNOSTICO ATUAL DA TABELA HASH")


def menu_adicionar_receita(motor: AlgoritmoRecomendacao, lista_receitas: list, trie_global: TrieBuscaGeral, tabela_hash: TabelaHashNomes) -> None:
    print("\n" + "═" * 55)
    print("  CRIAR NOVA RECEITA")
    print("═" * 55)
    
    nome = input("  Nome da receita: ").strip()
    if not nome:
        print("  ⚠ Operação cancelada: Nome não pode ser vazio.")
        return

    tempo = _pedir_inteiro("  Tempo de preparo (min) [padrão=0]: ") or 0
    custo = _pedir_inteiro("  Custo (centavos de dólar) [padrão=0]: ") or 0

    try:
        nova_receita = Receita(nome_receita=nome, custo=custo, tempo_preparo=tempo, fator_recomendacao=0.0, trie_global=trie_global, tabela_hash=tabela_hash)
    except ValueError as e:
        print(f"  ⚠ Erro: {e}")
        return 

    # 2. ADICIONA CATEGORIAS (Código super limpo agora)
    cats = _pedir_lista("  Categorias (sep. vírgula) [deixe em branco para pular]: ")
    for cat in cats:
        # Passamos os motores, a magia acontece lá dentro!
        nova_receita.adicionar_categoria(cat, trie_global, tabela_hash)

    # 3. ADICIONA INGREDIENTES
    print("\n  -- Ingredientes -- (Deixe o nome em branco para encerrar)")
    while True:
        ing_nome = input("  Nome do ingrediente: ").strip()
        if not ing_nome:
            break
            
        qtd = _pedir_inteiro("  Quantidade (número) [padrão=1]: ") or 1
        unidade = input("  Unidade (ex: g, ml, xícara) [padrão=und]: ").strip() or "und"
        
        # Passamos os motores, a magia acontece lá dentro!
        nova_receita.adicionar_ingrediente(nome_ingrediente=ing_nome, unidade=unidade, quantidade=qtd, trie_global=trie_global, tabela_hash=tabela_hash)

    # 4. SALVAMENTO E SINCRONIA GERAL
    lista_receitas.append(nova_receita)
    motor.adicionar_receita(nova_receita)
    
    print(f"\n  ✓ Receita '{nome}' criada com sucesso!")

def menu_visualizar_categoria(categoria: Categoria) -> None:
    while True:
        print("\n" + "═" * 55)
        print(f"  CATEGORIA: {categoria.nome_categoria.upper()}")
        print("═" * 55)
        
        opcoes = {}
        contador = 1
        
        print("  Receitas nesta categoria:")
        if not categoria.lista_categoria_receitas:
            print("   - Nenhuma receita encontrada.")
        else:
            for rec in categoria.lista_categoria_receitas:
                print(f"   {contador}. {rec.nome_receita}")
                opcoes[contador] = rec
                contador += 1
                
        escolha = _pedir_inteiro("\n  Digite o número da receita para explorar (0 para voltar): ")
        if escolha == 0 or escolha is None:
            break
        elif escolha in opcoes:
            menu_visualizar_receita(opcoes[escolha])
        else:
            print("  ⚠ Opção inválida.")

def menu_visualizar_ingrediente(ingrediente: Ingredientes) -> None:
    while True:
        print("\n" + "═" * 55)
        print(f"  INGREDIENTE: {ingrediente.nome_ingrediente.upper()}")
        print("═" * 55)
        
        opcoes = {}
        contador = 1
        
        print("  Receitas que usam este ingrediente:")
        if not ingrediente.lista_receitas_ingredientes:
            print("   - Nenhuma receita encontrada.")
        else:
            for rec in ingrediente.lista_receitas_ingredientes:
                print(f"   {contador}. {rec.nome_receita}")
                opcoes[contador] = rec
                contador += 1
                
        escolha = _pedir_inteiro("\n  Digite o número da receita para explorar (0 para voltar): ")
        if escolha == 0 or escolha is None:
            break
        elif escolha in opcoes:
            menu_visualizar_receita(opcoes[escolha])
        else:
            print("  ⚠ Opção inválida.")

def menu_visualizar_receita(receita: Receita) -> None:
    while True:
        print("\n" + "═" * 55)
        print(f"  RECEITA: {receita.nome_receita.upper()}")
        print("═" * 55)
        print(f"  Tempo: {receita.tempo_preparo} min | Custo: {receita.custo}¢$ | Fator: {receita.fator_recomendacao}")
        
        opcoes = {}
        contador = 1
        
        print("\n  [ Categorias ]")
        if not receita.lista_categoria_receitas:
            print("   - Nenhuma categoria")
        else:
            for cat in receita.lista_categoria_receitas:
                print(f"   {contador}. {cat.nome_categoria}")
                opcoes[contador] = ('categoria', cat)
                contador += 1
                
        print("\n  [ Ingredientes ]")
        if not receita.lista_quantidade_ingredientes:
            print("   - Nenhum ingrediente")
        else:
            for rel in receita.lista_quantidade_ingredientes:
                print(f"   {contador}. {rel.quantidade_necessaria} {rel.unidade_utilizada} de {rel.ingrediente.nome_ingrediente}")
                opcoes[contador] = ('ingrediente', rel.ingrediente)
                contador += 1
                
        escolha = _pedir_inteiro("\n  Digite o número para explorar a categoria/ingrediente (0 para voltar): ")
        if escolha == 0 or escolha is None:
            break
        elif escolha in opcoes:
            tipo, obj = opcoes[escolha]
            if tipo == 'categoria':
                menu_visualizar_categoria(obj)
            else:
                menu_visualizar_ingrediente(obj)
        else:
            print("  ⚠ Opção inválida.")

def menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente, trie_global, tabela_hash):
    while True:
        print("\n╔" + "═" * 48 + "╗")
        print("║      DESAFIO NA COZINHA — MENU PRINCIPAL       ║")
        print("╠" + "═" * 48 + "╣")
        print("║  1. Ver vetor de recomendações (ordenado)      ║")
        print("║  2. Obter recomendação                         ║")
        print("║  3. Busca Geral (Nome/Prefixo) — Trie          ║")
        print("║  4. Busca por Nome Exato — Tabela Hash         ║")
        print("║  5. Diagnostico da Tabela Hash                 ║")
        print("║  6. Adicionar nova receita                     ║")
        print("║  7. Salvar estado atual                        ║")
        print("║  0. Sair                                       ║")
        print("╚" + "═" * 48 + "╝")
        opcao = input("  Opção: ").strip()

        if opcao == "1":
            motor.exibir_lista(limite=15)
        elif opcao == "2":
            menu_recomendacao(motor)
        elif opcao == "3":
            menu_busca_geral(trie_global)
        elif opcao == "4":
            menu_busca_hash(tabela_hash)
        elif opcao == "5":
            menu_diagnostico_hash(tabela_hash)
        elif opcao == "6":
            menu_adicionar_receita(motor, lista_receitas, trie_global, tabela_hash)
        elif opcao == "7":
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
        
    # Montamos a tabela hash (busca por nome exato)
    tabela_hash = construir_tabela_hash(lista_receitas, lista_ingredientes, lista_categorias)
    print("  ✓ Motores prontos!\n")

    # Iniciamos o loop principal do programa
    menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente, trie_global, tabela_hash)


if __name__ == "__main__":
    main()