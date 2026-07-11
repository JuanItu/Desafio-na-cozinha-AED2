# main.py  —  Ponto de entrada do sistema Desafio na Cozinha

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

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
from motor.oficina_producao import OficinaProducao

def montar_motor(lista_receitas) -> AlgoritmoRecomendacao:
    motor = AlgoritmoRecomendacao()
    for receita in lista_receitas:
        motor.adicionar_receita(receita)
    motor._reordenar_se_necessario()
    return motor

def _pedir_lista(prompt: str) -> list[str]:
    entrada = input(prompt).strip()
    if not entrada: return []
    return [item.strip() for item in entrada.split(",") if item.strip()]

def _pedir_inteiro(prompt: str) -> int | None:
    entrada = input(prompt).strip()
    if not entrada: return None
    try: return int(entrada)
    except ValueError:
        print("  ⚠ Valor inválido, ignorado.")
        return None
    
def _pedir_float(prompt: str) -> float | None:
    entrada = input(prompt).strip()
    if not entrada: return None
    try: return float(entrada)
    except ValueError:
        print("  ⚠ Valor inválido, ignorado.")
        return None

def _resolver_sugestoes_coerencia(oficina: OficinaProducao, sugestoes: list) -> None:
    """Oferece as 3 opções de interação da seção 5.4: aceitar tudo, selecionar
    individualmente ou ajustar manualmente (deixando como está, para edição livre)."""
    if not sugestoes:
        print("  ✓ Nenhuma inconsistência de custo/tempo/preço encontrada.")
        return

    print(f"\n  ⚠ {len(sugestoes)} sugestão(ões) de ajuste de coerência encontrada(s):")
    for i, s in enumerate(sugestoes, 1):
        print(f"    {i}. {s}")

    print("\n  1. Aceitar todas as sugestões")
    print("  2. Selecionar sugestões aceitas (uma a uma)")
    print("  3. Ajustar custo/tempo/preço manualmente (não aplica nada agora)")
    print("  0. Ignorar por enquanto")
    opcao = input("  Opção: ").strip()

    if opcao == '1':
        for s in list(sugestoes):
            oficina.aplicar_sugestao(s)
        print("  ✓ Todas as sugestões foram aplicadas!")
    elif opcao == '2':
        for s in list(sugestoes):
            resp = input(f"    Aplicar '{s.receita.nome_receita}' • {s.tipo}: {s.valor_atual} -> {s.valor_sugerido}? (S/N): ").strip().upper()
            if resp == 'S':
                oficina.aplicar_sugestao(s)
        print("  ✓ Sugestões selecionadas aplicadas!")
    elif opcao == '3':
        print("  → Use a opção de edição da receita (Alterar Custo/Tempo/Preço) para ajustar manualmente.")
    else:
        print("  Nenhuma sugestão aplicada.")


def _resolver_cortes_sugeridos(oficina: OficinaProducao, cortes: list) -> None:
    """Oferece as 3 opções de interação da seção 4: aplicar todos, escolher
    dentre os sugeridos, ou cortar manualmente digitando o nome do preparo."""
    if not cortes:
        print("  ✓ Nenhuma autodependência ou ciclo de dependências encontrado.")
        return

    print(f"\n  ⚠ {len(cortes)} corte(s) sugerido(s) para desfazer ciclos/autodependências:")
    for i, c in enumerate(cortes, 1):
        print(f"    {i}. {c}")

    print("\n  1. Aplicar todos os cortes sugeridos")
    print("  2. Escolher cortes dentre os sugeridos (um a um)")
    print("  3. Escolher cortes manualmente (digitar receita e preparo)")
    print("  0. Ignorar por enquanto")
    opcao = input("  Opção: ").strip()

    if opcao == '1':
        oficina.aplicar_todos_cortes()
        print("  ✓ Todos os cortes foram aplicados!")
    elif opcao == '2':
        for c in list(cortes):
            resp = input(f"    Cortar '{c.origem.nome_receita}' -x-> '{c.destino.nome_receita}'? (S/N): ").strip().upper()
            if resp == 'S':
                oficina.aplicar_corte(c)
        print("  ✓ Cortes selecionados aplicados!")
    elif opcao == '3':
        nome_origem = input("    Nome da receita: ").strip().lower()
        nome_destino = input("    Nome do preparo a remover: ").strip().lower()
        origem = Receita.registro_global.get(nome_origem)
        if origem and origem.remover_preparo(nome_destino):
            origem.salvar_snapshot("Corte manual de dependência (Modo Investigação)")
            print("  ✓ Dependência removida manualmente!")
        else:
            print("  ⚠ Receita ou dependência não encontrada.")
    else:
        print("  Nenhum corte aplicado.")


def menu_recomendacao(motor: AlgoritmoRecomendacao, lista_receitas, trie_global, tabela_hash, oficina: OficinaProducao) -> None:
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
        quantidade=qtd, tempo_maximo=tempo, custo_maximo=custo,
        ingredientes_proibidos=proib, ingredientes_exigidos=exig, categorias_exigidas=cats
    )
    
    while True:
        motor.exibir_recomendacao(resultados)
        if not resultados: break
            
        escolha = _pedir_inteiro("  Digite o número da receita para explorar (0 para voltar): ")
        if escolha == 0 or escolha is None: break
        elif 1 <= escolha <= len(resultados):
            menu_visualizar_receita(resultados[escolha - 1], motor, lista_receitas, trie_global, tabela_hash, oficina)
        else: print("  ⚠ Opção inválida.\n")

def menu_busca_geral(motor, lista_receitas, trie_global: TrieBuscaGeral, tabela_hash, oficina: OficinaProducao) -> None:
    print("\n" + "═" * 55)
    print("  BUSCA GERAL (NOME OU PREFIXO)")
    print("═" * 55)
    
    prefixo = input("  Digite o termo de busca: ").strip().lower()
    if not prefixo: return
        
    no_resultado = trie_global.get_node(prefixo)
    if not no_resultado:
        print(f"\n  ✗ Nenhum resultado encontrado para '{prefixo}'.")
        return
        
    dados = trie_global.get_all_separated_alphabetically(no_resultado)
    total = len(dados['Receita']) + len(dados['Ingredientes']) + len(dados['Categoria'])
    
    if total == 0:
        print(f"\n  ✗ Nenhum resultado encontrado para '{prefixo}'.")
        return

    while True:
        print(f"\n  ✓ {total} resultado(s) encontrado(s) para '{prefixo}':\n")
        
        opcoes = {}
        contador = 1
        
        if dados['Receita']:
            print("  [ RECEITAS ]")
            for r in dados['Receita']:
                print(f"   {contador}. {r.nome_receita}")
                opcoes[str(contador)] = ('receita', r)
                contador += 1
                
        if dados['Categoria']:
            print("\n  [ CATEGORIAS ]")
            for c in dados['Categoria']:
                print(f"   {contador}. {c.nome_categoria}")
                opcoes[str(contador)] = ('categoria', c)
                contador += 1
                
        if dados['Ingredientes']:
            print("\n  [ INGREDIENTES ]")
            for i in dados['Ingredientes']:
                print(f"   {contador}. {i.nome_ingrediente}")
                opcoes[str(contador)] = ('ingrediente', i)
                contador += 1

        escolha = input("\n  Digite o número para inspecionar (0 para sair): ").strip()
        
        if escolha == '0': break
        elif escolha in opcoes:
            tipo, obj = opcoes[escolha]
            if tipo == 'receita': menu_visualizar_receita(obj, motor, lista_receitas, trie_global, tabela_hash, oficina)
            elif tipo == 'categoria': menu_visualizar_categoria(obj, motor, lista_receitas, trie_global, tabela_hash, oficina)
            elif tipo == 'ingrediente': menu_visualizar_ingrediente(obj, motor, lista_receitas, trie_global, tabela_hash, oficina)
        else: print("  ⚠ Opção inválida.")

def menu_busca_hash(motor, lista_receitas, trie_global, tabela_hash: TabelaHashNomes, oficina: OficinaProducao) -> None:
    print("\n" + "=" * 55)
    print("  BUSCA POR NOME EXATO (TABELA HASH)")
    print("=" * 55)

    nome = input("  Digite o nome exato: ").strip()
    if not nome: return

    resultados = tabela_hash.buscar(nome) 

    if not resultados:
        print(f"\n  ✗ Nenhum resultado para '{nome}'.")
        return

    while True:
        print(f"\n  ✓ {len(resultados)} resultado(s) encontrado(s) para '{nome}':\n")
        
        opcoes = {}
        contador = 1
        
        for obj in resultados:
            if isinstance(obj, Receita): print(f"   {contador}. [RECEITA] {obj.nome_receita}")
            elif isinstance(obj, Categoria): print(f"   {contador}. [CATEGORIA] {obj.nome_categoria}")
            elif isinstance(obj, Ingredientes): print(f"   {contador}. [INGREDIENTE] {obj.nome_ingrediente}")
                
            opcoes[str(contador)] = obj
            contador += 1
            
        escolha = input("\n  Digite o número para inspecionar (0 para sair): ").strip()
        
        if escolha == '0': break
        elif escolha in opcoes:
            obj_escolhido = opcoes[escolha]
            if isinstance(obj_escolhido, Receita): menu_visualizar_receita(obj_escolhido, motor, lista_receitas, trie_global, tabela_hash, oficina)
            elif isinstance(obj_escolhido, Categoria): menu_visualizar_categoria(obj_escolhido, motor, lista_receitas, trie_global, tabela_hash, oficina)
            elif isinstance(obj_escolhido, Ingredientes): menu_visualizar_ingrediente(obj_escolhido, motor, lista_receitas, trie_global, tabela_hash, oficina)
        else: print("  ⚠ Opção inválida.")

def menu_diagnostico_hash(tabela_hash: TabelaHashNomes) -> None:
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
    preco = _pedir_float("  Preço de venda [0 = apenas preparo intermediário, padrão=0]: ") or 0.0

    try:
        nova_receita = Receita(nome_receita=nome, custo=custo, tempo_preparo=tempo, fator_recomendacao=0.0, preco=preco, trie_global=trie_global, tabela_hash=tabela_hash)
    except ValueError as e:
        print(f"  ⚠ Erro: {e}")
        return 

    cats = _pedir_lista("  Categorias (sep. vírgula) [deixe em branco para pular]: ")
    for cat in cats: nova_receita.adicionar_categoria(cat, trie_global, tabela_hash)

    print("\n  -- Ingredientes -- (Deixe o nome em branco para encerrar)")
    while True:
        ing_nome = input("  Nome do ingrediente: ").strip()
        if not ing_nome: break
            
        qtd = _pedir_inteiro("  Quantidade (número) [padrão=1]: ") or 1
        unidade = input("  Unidade (ex: g, ml, xícara) [padrão=und]: ").strip() or "und"
        
        nova_receita.adicionar_ingrediente(nome_ingrediente=ing_nome, unidade=unidade, quantidade=qtd, trie_global=trie_global, tabela_hash=tabela_hash)

    lista_receitas.append(nova_receita)
    motor.adicionar_receita(nova_receita)
    nova_receita.salvar_snapshot("Criação da Receita (Original)")
    print(f"\n  ✓ Receita '{nome}' criada com sucesso!")

def menu_visualizar_categoria(categoria: Categoria, motor, lista_receitas, trie_global, tabela_hash, oficina: OficinaProducao) -> None:
    while True:
        print("\n" + "═" * 55)
        print(f"  CATEGORIA: {categoria.nome_categoria.upper()}")
        print("═" * 55)
        
        opcoes = {}
        contador = 1
        
        print("  Receitas nesta categoria:")
        if not categoria.lista_categoria_receitas: print("   - Nenhuma receita encontrada.")
        else:
            for rec in categoria.lista_categoria_receitas:
                print(f"   {contador}. {rec.nome_receita}")
                opcoes[str(contador)] = rec
                contador += 1
                
        print("\n  [E] Renomear Categoria | [X] Excluir Categoria | [0] Voltar")
        escolha = input("  Ação: ").strip().upper()
        
        if escolha == '0': break
        elif escolha == 'E':
            novo_nome = input("  Novo nome da categoria: ").strip()
            if novo_nome:
                try:
                    categoria.mudar_nome(novo_nome, trie_global, tabela_hash)
                    print("  ✓ Categoria renomeada!")
                except ValueError as e: print(f"  ⚠ Erro: {e}")
        elif escolha == 'X':
            confirmar = input("  Certeza que deseja excluir? (S/N): ").upper()
            if confirmar == 'S':
                categoria.excluir(trie_global, tabela_hash)
                print("  ✓ Categoria excluída!")
                break
        elif escolha in opcoes:
            menu_visualizar_receita(opcoes[escolha], motor, lista_receitas, trie_global, tabela_hash, oficina)
        else: print("  ⚠ Opção inválida.")

def menu_visualizar_ingrediente(ingrediente: Ingredientes, motor, lista_receitas, trie_global, tabela_hash, oficina: OficinaProducao) -> None:
    while True:
        print("\n" + "═" * 55)
        print(f"  INGREDIENTE: {ingrediente.nome_ingrediente.upper()}")
        print("═" * 55)
        # --- EXIBE O ESTOQUE ---
        print(f"  Estoque atual: {ingrediente.quantidade_estoque} {ingrediente.unidade_estoque}")
        
        opcoes = {}
        contador = 1
        
        print("\n  Receitas que usam este ingrediente:")
        if not ingrediente.lista_receitas_ingredientes: print("   - Nenhuma receita encontrada.")
        else:
            for rec in ingrediente.lista_receitas_ingredientes:
                print(f"   {contador}. {rec.nome_receita}")
                opcoes[str(contador)] = rec
                contador += 1
                
        print("\n  [E] Editar Ingrediente | [X] Excluir Ingrediente | [0] Voltar")
        escolha = input("  Ação ou Número para explorar: ").strip().upper()
        
        if escolha == '0': break
        
        # --- MODO DE EDIÇÃO DO INGREDIENTE ---
        elif escolha == 'E':
            print("\n  [ MODO DE EDIÇÃO ]")
            print("  1. Renomear Ingrediente")
            print("  2. Atualizar Estoque Global")
            print("  0. Cancelar")
            ed = input("  Opção: ").strip()
            
            if ed == '1':
                novo_nome = input("  Novo nome do ingrediente: ").strip()
                if novo_nome:
                    try:
                        ingrediente.mudar_nome(novo_nome, trie_global, tabela_hash)
                        print("  ✓ Ingrediente renomeado!")
                    except ValueError as e: print(f"  ⚠ Erro: {e}")
            elif ed == '2':
                nova_qtd = _pedir_float("  Nova quantidade (número): ")
                if nova_qtd is not None:
                    nova_und = input("  Nova unidade (ex: kg, ml, und): ").strip() or "und"
                    ingrediente.atualizar_estoque(nova_qtd, nova_und)
                    print("  ✓ Estoque atualizado com sucesso!")
                    
        elif escolha == 'X':
            confirmar = input("  Certeza que deseja excluir? (S/N): ").upper()
            if confirmar == 'S':
                ingrediente.excluir(trie_global, tabela_hash)
                print("  ✓ Ingrediente excluído!")
                break
        elif escolha in opcoes:
            menu_visualizar_receita(opcoes[escolha], motor, lista_receitas, trie_global, tabela_hash, oficina)
        else: print("  ⚠ Opção inválida.")

def menu_visualizar_receita(receita: Receita, motor, lista_receitas, trie_global, tabela_hash, oficina: OficinaProducao) -> None:
    while True:
        print("\n" + "═" * 55)
        print(f"  RECEITA: {receita.nome_receita.upper()}")
        print("═" * 55)
        print(f"  Tempo: {receita.tempo_preparo} min | Custo: {receita.custo}¢$ | Preço: {receita.preco}¢$ | Fator: {receita.fator_recomendacao}")
        
        opcoes = {}
        contador = 1
        
        print("\n  [ Categorias ]")
        if not receita.lista_categoria_receitas: print("   - Nenhuma categoria")
        else:
            for cat in receita.lista_categoria_receitas:
                print(f"   {contador}. {cat.nome_categoria}")
                opcoes[str(contador)] = ('categoria', cat)
                contador += 1
                
        print("\n  [ Ingredientes ]")
        if not receita.lista_quantidade_ingredientes: print("   - Nenhum ingrediente")
        else:
            for rel in receita.lista_quantidade_ingredientes:
                print(f"   {contador}. {rel.quantidade_necessaria} {rel.unidade_utilizada} de {rel.ingrediente.nome_ingrediente}")
                opcoes[str(contador)] = ('ingrediente', rel.ingrediente)
                contador += 1

        print("\n  [ Preparos (Módulo 5) ]")
        if not receita.lista_preparos: print("   - Nenhum preparo cadastrado")
        else:
            for prep in receita.lista_preparos:
                print(f"   {contador}. {prep.nome_receita}")
                opcoes[str(contador)] = ('receita', prep)
                contador += 1

        print("\n  [E] Editar Receita | [X] Excluir Receita | [0] Voltar")
        escolha = input("  Ação ou Número para explorar: ").strip().upper()
        
        if escolha == '0': break
        elif escolha == 'E':
            alteracoes_feitas = []
            while True:
                print("\n  [ MODO DE EDIÇÃO ]")
                print("  1. Renomear Receita")
                print("  2. Alterar Custo")
                print("  3. Alterar Tempo")
                print("  4. Alterar Fator de Recomendação")
                print("  5. Adicionar Ingrediente")
                print("  6. Remover Ingrediente")
                print("  7. Adicionar Categoria")
                print("  8. Remover Categoria")
                print("  9. Alterar Preço de Venda")
                print("  10. Adicionar Preparo (dependência — Módulo 5)")
                print("  11. Remover Preparo (dependência — Módulo 5)")
                print("  0. Salvar e Sair do Modo de Edição")
                edicao = input("  Opção: ").strip()
                
                if edicao == '0':
                    if alteracoes_feitas:
                        motivo = "Edição: " + ", ".join(alteracoes_feitas)
                        receita.salvar_snapshot(motivo)
                        print("  ✓ Alterações salvas no histórico de versões!")
                    break
                elif edicao == '1':
                    n_nome = input("  Novo Nome: ")
                    try: 
                        receita.mudar_nome(n_nome, trie_global, tabela_hash)
                        alteracoes_feitas.append("Nome")
                    except ValueError as e: print(f"  ⚠ Erro: {e}")
                elif edicao == '2':
                    novo_c = _pedir_inteiro("  Novo Custo: ")
                    if novo_c is not None:
                        receita.atualizar_custo(novo_c)
                        alteracoes_feitas.append("Custo")
                elif edicao == '3':
                    novo_t = _pedir_inteiro("  Novo Tempo: ")
                    if novo_t is not None:
                        receita.atualizar_tempo(novo_t)
                        alteracoes_feitas.append("Tempo")
                elif edicao == '4':
                    novo_f = _pedir_float("  Novo Fator (ex: 4.5): ")
                    if novo_f is not None:
                        receita.atualizar_fator_recomendacao(novo_f)
                        alteracoes_feitas.append("Fator")
                elif edicao == '5':
                    ing_nome = input("  Nome do ingrediente a adicionar: ").strip()
                    if ing_nome:
                        qtd = _pedir_inteiro("  Quantidade (número) [padrão=1]: ") or 1
                        und = input("  Unidade (ex: g, ml) [padrão=und]: ").strip() or "und"
                        receita.adicionar_ingrediente(ing_nome, und, qtd, trie_global, tabela_hash)
                        alteracoes_feitas.append(f"+Ingrediente ({ing_nome})")
                elif edicao == '6':
                    if not receita.lista_quantidade_ingredientes:
                        print("  ✗ Esta receita não tem ingredientes para remover.")
                    else:
                        print("\n  Qual ingrediente deseja remover?")
                        for i, rel in enumerate(receita.lista_quantidade_ingredientes, 1):
                            print(f"    {i}. {rel.ingrediente.nome_ingrediente}")
                        
                        idx = _pedir_inteiro("  Número do ingrediente: ")
                        if idx and 1 <= idx <= len(receita.lista_quantidade_ingredientes):
                            rel_alvo = receita.lista_quantidade_ingredientes[idx - 1]
                            nome_ing_alvo = rel_alvo.ingrediente.nome_ingrediente
                            receita.remover_ingrediente(nome_ing_alvo)
                            alteracoes_feitas.append(f"-Ingrediente ({nome_ing_alvo})")
                        else:
                            print("  ⚠ Seleção inválida.")
                elif edicao == '7':
                    cat_nome = input("  Nome da categoria a adicionar: ").strip()
                    if cat_nome:
                        receita.adicionar_categoria(cat_nome, trie_global, tabela_hash)
                        alteracoes_feitas.append(f"+Categoria ({cat_nome})")
                elif edicao == '8':
                    if not receita.lista_categoria_receitas:
                        print("  ✗ Esta receita não tem categorias para remover.")
                    else:
                        print("\n  Qual categoria deseja remover?")
                        for i, cat in enumerate(receita.lista_categoria_receitas, 1):
                            print(f"    {i}. {cat.nome_categoria}")
                        
                        idx = _pedir_inteiro("  Número da categoria: ")
                        if idx and 1 <= idx <= len(receita.lista_categoria_receitas):
                            cat_alvo = receita.lista_categoria_receitas[idx - 1]
                            nome_cat_alvo = cat_alvo.nome_categoria
                            receita.remover_categoria(nome_cat_alvo)
                            alteracoes_feitas.append(f"-Categoria ({nome_cat_alvo})")
                        else:
                            print("  ⚠ Seleção inválida.")
                elif edicao == '9':
                    novo_p = _pedir_float("  Novo Preço de Venda [0 = apenas preparo intermediário]: ")
                    if novo_p is not None:
                        receita.atualizar_preco(novo_p)
                        alteracoes_feitas.append("Preço")
                        # Verificação de Manutenção (seção 5.1-5.3), pois o preço mudou
                        sugestoes = oficina.verificacao_manutencao(receita)
                        _resolver_sugestoes_coerencia(oficina, sugestoes)
                elif edicao == '10':
                    prep_nome = input("  Nome do preparo a adicionar como dependência: ").strip().lower()
                    preparo_obj = Receita.registro_global.get(prep_nome)
                    if preparo_obj is None:
                        print("  ⚠ Receita não encontrada. Cadastre-a primeiro.")
                    else:
                        receita.adicionar_preparo(preparo_obj)
                        alteracoes_feitas.append(f"+Preparo ({preparo_obj.nome_receita})")
                        # Verificação de Manutenção: coerência de custo/tempo/preço
                        sugestoes = oficina.verificacao_manutencao(receita)
                        _resolver_sugestoes_coerencia(oficina, sugestoes)
                elif edicao == '11':
                    if not receita.lista_preparos:
                        print("  ✗ Esta receita não tem preparos para remover.")
                    else:
                        print("\n  Qual preparo deseja remover?")
                        for i, prep in enumerate(receita.lista_preparos, 1):
                            print(f"    {i}. {prep.nome_receita}")

                        idx = _pedir_inteiro("  Número do preparo: ")
                        if idx and 1 <= idx <= len(receita.lista_preparos):
                            prep_alvo = receita.lista_preparos[idx - 1]
                            nome_prep_alvo = prep_alvo.nome_receita
                            receita.remover_preparo(nome_prep_alvo)
                            alteracoes_feitas.append(f"-Preparo ({nome_prep_alvo})")
                        else:
                            print("  ⚠ Seleção inválida.")
                else:
                    print("  ⚠ Opção inválida.")
        elif escolha == 'X':
            confirm = input("  Excluir Receita (Mover para Arquivo Morto)? (S/N): ").upper()
            if confirm == 'S':
                receita.excluir(trie_global, tabela_hash)
                if receita in lista_receitas: lista_receitas.remove(receita)
                motor.remover_receita(receita)
                print("  ✓ Receita Excluída!")
                break
        elif escolha in opcoes:
            tipo, obj = opcoes[escolha]
            if tipo == 'categoria': menu_visualizar_categoria(obj, motor, lista_receitas, trie_global, tabela_hash, oficina)
            elif tipo == 'receita': menu_visualizar_receita(obj, motor, lista_receitas, trie_global, tabela_hash, oficina)
            else: menu_visualizar_ingrediente(obj, motor, lista_receitas, trie_global, tabela_hash, oficina)
        else: print("  ⚠ Opção inválida.")


def menu_oficina_producao(oficina: OficinaProducao) -> None:
    while True:
        print("\n" + "═" * 55)
        print("  MÓDULO 5 — OFICINA DE PRODUÇÃO")
        print("═" * 55)
        print("  1. Rodar Verificação Geral (autodependências, ciclos, coerência)")
        print("  2. Ver / Aplicar cortes sugeridos pendentes")
        print("  3. Ver / Aplicar sugestões de coerência pendentes")
        print("  4. Consulta: Existe algum erro de dependência?")
        print("  5. Consulta: Sequência correta de produção do menu")
        print("  6. Consulta: Preparos necessários antes de uma receita X")
        print("  0. Voltar")

        opcao = input("  Escolha: ").strip()

        if opcao == "0": break

        elif opcao == "1":
            resultado = oficina.verificacao_geral()
            print(f"\n  Grafo é um DAG (sem ciclos)? {'SIM' if resultado['eh_dag'] else 'NÃO'}")
            _resolver_cortes_sugeridos(oficina, resultado["cortes_sugeridos"])
            if resultado["eh_dag"]:
                _resolver_sugestoes_coerencia(oficina, resultado["sugestoes_coerencia"])
            else:
                print("  → Resolva os cortes acima e rode a Verificação Geral novamente")
                print("    para liberar a checagem de coerência e a ordem de produção.")

        elif opcao == "2":
            _resolver_cortes_sugeridos(oficina, oficina.lista_cortes_sugeridos)

        elif opcao == "3":
            _resolver_sugestoes_coerencia(oficina, oficina.lista_sugestoes_coerencia)

        elif opcao == "4":
            if oficina.existe_erro_dependencia():
                print("\n  ⚠ SIM: existem autodependências e/ou ciclos de dependência não resolvidos.")
            else:
                print("\n  ✓ NÃO: o grafo de dependências está consistente (DAG).")

        elif opcao == "5":
            ordem = oficina.sequencia_producao()
            if ordem is None:
                print("\n  ✗ Não é possível gerar a sequência: existem ciclos/autodependências pendentes.")
                print("    Rode a opção 1 (Verificação Geral) e resolva os cortes primeiro.")
            else:
                print("\n  ✓ Sequência correta de produção (preparos antes de quem os utiliza):")
                for i, r in enumerate(ordem, 1):
                    print(f"    {i}. {r.nome_receita}")

        elif opcao == "6":
            nome = input("  Nome da receita X: ").strip().lower()
            r = Receita.registro_global.get(nome)
            if r is None:
                print("  ⚠ Receita não encontrada.")
            else:
                preparos = oficina.preparos_necessarios_antes_de(r)
                if not preparos:
                    print(f"\n  '{r.nome_receita}' não depende de nenhum preparo.")
                else:
                    print(f"\n  Preparos necessários antes de '{r.nome_receita}' (diretos + transitivos):")
                    for p in preparos:
                        print(f"    - {p.nome_receita}")
        else:
            print("  ⚠ Opção inválida.")


def menu_investigacao() -> None:
    while True:
        print("\n" + "═" * 55)
        print("  MODO INVESTIGAÇÃO (HISTÓRICO E ARQUIVO MORTO)")
        print("═" * 55)
        print("  1. Ver Atuais e Versões (Mais recentes primeiro)")
        print("  2. Ver Receitas Excluídas (Mais recentes primeiro)")
        print("  0. Voltar")
        
        opcao = input("  Escolha: ").strip()
        
        if opcao == "0": break
        elif opcao == "1":
            atuais = sorted(list(Receita.registro_global.values()), key=lambda r: r.ultima_atualizacao, reverse=True)
            _exibir_lista_investigacao(atuais, "RECEITAS ATUAIS")
        elif opcao == "2":
            excluidas = sorted(list(Receita.registro_excluidas.values()), key=lambda r: r.data_exclusao, reverse=True)
            _exibir_lista_investigacao(excluidas, "RECEITAS EXCLUÍDAS")
        else: print("  ⚠ Opção inválida.")

def _exibir_lista_investigacao(lista_receitas: list, titulo: str):
    if not lista_receitas:
        print(f"\n  ✗ Nenhuma receita encontrada em {titulo}.")
        return
        
    while True:
        print("\n" + "-" * 55)
        print(f"  {titulo}")
        print("-" * 55)
        
        opcoes = {}
        for i, rec in enumerate(lista_receitas, 1):
            data_str = rec.data_exclusao.strftime('%d/%m %H:%M') if rec.data_exclusao else rec.ultima_atualizacao.strftime('%d/%m %H:%M')
            print(f"  {i}. [{data_str}] {rec.nome_receita}")
            opcoes[str(i)] = rec
            
        escolha = input("\n  Digite o número para ver o histórico (0 para voltar): ").strip()
        
        if escolha == '0': break
        elif escolha in opcoes:
            rec_escolhida = opcoes[escolha]
            print("\n  [ HISTÓRICO DE ESTADOS ]")
            for versao in reversed(rec_escolhida.historico_estados):
                print(f"\n  • Data: {versao['data']} | Motivo: {versao['motivo']}")
                print(f"    Nome: {versao['nome']} | Custo: {versao['custo']}¢$ | Tempo: {versao['tempo']}min")
                print(f"    Categorias: {', '.join(versao['categorias']) if versao['categorias'] else 'Nenhuma'}")
                print(f"    Ingredientes: {', '.join(versao['ingredientes']) if versao['ingredientes'] else 'Nenhum'}")
            input("\n  [ Pressione ENTER para voltar à lista ]")
        else: print("  ⚠ Opção inválida.")


def menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente, trie_global, tabela_hash, oficina: OficinaProducao):
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
        print("║  8. Modo Investigação (Histórico/Lixeira)      ║")
        print("║  9. Oficina de Produção (Módulo 5)             ║")
        print("║  0. Sair                                       ║")
        print("╚" + "═" * 48 + "╝")
        opcao = input("  Opção: ").strip()

        if opcao == "1": motor.exibir_lista(limite=15)
        elif opcao == "2": menu_recomendacao(motor, lista_receitas, trie_global, tabela_hash, oficina)
        elif opcao == "3": menu_busca_geral(motor, lista_receitas, trie_global, tabela_hash, oficina)
        elif opcao == "4": menu_busca_hash(motor, lista_receitas, trie_global, tabela_hash, oficina)
        elif opcao == "5": menu_diagnostico_hash(tabela_hash)
        elif opcao == "6": menu_adicionar_receita(motor, lista_receitas, trie_global, tabela_hash)
        elif opcao == "7": salvar_dados(lista_receitas, lista_ingredientes, lista_categorias, mapa_id_ingrediente)
        elif opcao == "8": menu_investigacao()
        elif opcao == "9": menu_oficina_producao(oficina)
        elif opcao == "0":
            print("  Encerrando. Até logo!")
            break
        else: print("  Opção inválida.\n")


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
    motor = montar_motor(lista_receitas)
    
    trie_global = TrieBuscaGeral()
    for r in lista_receitas: trie_global.insert(r.nome_receita.lower(), r)
    for c in lista_categorias: trie_global.insert(c.nome_categoria.lower(), c)
    for i in lista_ingredientes: trie_global.insert(i.nome_ingrediente.lower(), i)
        
    tabela_hash = construir_tabela_hash(lista_receitas, lista_ingredientes, lista_categorias)
    print("  ✓ Motores prontos!\n")

    # --- MÓDULO 5: OFICINA DE PRODUÇÃO — Verificação Geral na inicialização ---
    oficina = OficinaProducao(lista_receitas)
    resultado_inicial = oficina.verificacao_geral()
    print("Rodando Verificação Geral da Oficina de Produção (Módulo 5)...")
    if resultado_inicial["eh_dag"]:
        print(f"  ✓ Grafo de dependências é um DAG. "
              f"{len(resultado_inicial['sugestoes_coerencia'])} sugestão(ões) de coerência pendente(s).")
    else:
        print(f"  ⚠ {len(resultado_inicial['cortes_sugeridos'])} corte(s) sugerido(s) "
              f"para desfazer ciclos/autodependências. Veja no menu 'Oficina de Produção'.")

    menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente, trie_global, tabela_hash, oficina)

if __name__ == "__main__":
    main()