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
from modelos.menu import Menu

from data.data_manager import carregar_dados, salvar_dados
from motor.algoritmo_recomendações import AlgoritmoRecomendacao
from motor.busca_geral import TrieBuscaGeral
from motor.busca_id import TabelaHashNomes, construir_tabela_hash
from motor.oficina_producao import OficinaProducao
from motor.gerar_menu import OtimizadorMenuVIP

# --- MÓDULO 7/8: LOGÍSTICA (MST, FLUXO E ROTEAMENTO DE ENTREGAS) ---
from data.mapa_manager import carregar_malha_urbana
from motor.roteador_entregas import RoteadorEntregasTSP
from motor.infraestrutura_minima import OtimizadorInfraestrutura
from motor.fluxo_capacidade import MotorFluxoMCMF
from modelos.logistica import CozinhaRegisto, PontoRetiradaRegisto

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

def _buscar_com_sugestao_trie(trie_global: TrieBuscaGeral, texto: str, tipo_chave: str):
    """
    Usado quando uma busca por nome EXATO (via hash / dict) falha. Reaproveita
    a Trie do Módulo 2 (Busca Geral) para sugerir o que o usuário talvez quisesse
    digitar: reduz progressivamente o texto digitado até achar um prefixo válido
    na árvore e lista as opções encontradas a partir dali (ordem alfabética).

    tipo_chave: 'Receita' ou 'Categoria' (chaves do dict de get_all_separated_alphabetically).
    Retorna o objeto escolhido pelo usuário, ou None se nada foi encontrado/escolhido.
    """
    texto = texto.lower().strip()
    if not texto:
        return None

    prefixo_testado = texto
    no = trie_global.get_node(prefixo_testado)

    # Vai cortando a última letra até achar um prefixo que exista na Trie
    while no is None and len(prefixo_testado) > 1:
        prefixo_testado = prefixo_testado[:-1]
        no = trie_global.get_node(prefixo_testado)

    if no is None:
        return None

    candidatos = trie_global.get_all_separated_alphabetically(no)[tipo_chave]
    if not candidatos:
        return None

    rotulo = "nome_receita" if tipo_chave == "Receita" else "nome_categoria"

    print(f"\n  ⚠ '{texto}' não encontrado exatamente. Você quis dizer (prefixo '{prefixo_testado}'):")
    for i, obj in enumerate(candidatos[:10], 1):
        print(f"    {i}. {getattr(obj, rotulo)}")
    print("    0. Nenhuma das opções")

    escolha = _pedir_inteiro("  Escolha uma opção: ")
    if escolha and 1 <= escolha <= min(len(candidatos), 10):
        return candidatos[escolha - 1]
    return None


def _criaria_ciclo(oficina: OficinaProducao, origem: "Receita", destino: "Receita") -> bool:
    """
    Verifica, ANTES de efetivar a aresta origem -> destino (origem passa a ter
    destino como preparo), se isso fecharia um ciclo de dependências.

    Reaproveita a BFS do Módulo 5 (preparos_necessarios_antes_de): se 'origem' já
    está entre os preparos diretos/transitivos de 'destino', então 'destino' já
    depende de 'origem' — adicionar origem -> destino fecharia o ciclo.
    """
    if origem is destino:
        return True
    dependentes_de_destino = oficina.preparos_necessarios_antes_de(destino)
    return origem in dependentes_de_destino


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
    custo   = _pedir_float("  Custo máximo (centavos de dólar): ")
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

def _buscar_com_sugestao_trie_generico(trie_global: TrieBuscaGeral, texto: str):
    """
    Igual a _buscar_com_sugestao_trie, mas para buscas genéricas (como a Busca
    por Nome Exato / Tabela Hash) que podem envolver Receita, Categoria OU
    Ingrediente ao mesmo tempo. Retorna o objeto escolhido, ou None.
    """
    texto_lower = texto.lower().strip()
    if not texto_lower:
        return None

    prefixo_testado = texto_lower
    no = trie_global.get_node(prefixo_testado)

    while no is None and len(prefixo_testado) > 1:
        prefixo_testado = prefixo_testado[:-1]
        no = trie_global.get_node(prefixo_testado)

    if no is None:
        return None

    dados = trie_global.get_all_separated_alphabetically(no)
    candidatos = []
    for r in dados['Receita']:
        candidatos.append(('RECEITA', r.nome_receita, r))
    for c in dados['Categoria']:
        candidatos.append(('CATEGORIA', c.nome_categoria, c))
    for i in dados['Ingredientes']:
        candidatos.append(('INGREDIENTE', i.nome_ingrediente, i))

    if not candidatos:
        return None

    print(f"\n  ⚠ '{texto}' não encontrado exatamente. Você quis dizer (prefixo '{prefixo_testado}'):")
    for idx, (tipo, nome_obj, _obj) in enumerate(candidatos[:10], 1):
        print(f"    {idx}. [{tipo}] {nome_obj}")
    print("    0. Nenhuma das opções")

    escolha = _pedir_inteiro("  Escolha uma opção: ")
    if escolha and 1 <= escolha <= min(len(candidatos), 10):
        return candidatos[escolha - 1][2]
    return None


def menu_busca_hash(motor, lista_receitas, trie_global, tabela_hash: TabelaHashNomes, oficina: OficinaProducao) -> None:
    print("\n" + "=" * 55)
    print("  BUSCA POR NOME EXATO (TABELA HASH)")
    print("=" * 55)

    nome = input("  Digite o nome exato: ").strip()
    if not nome: return

    resultados = tabela_hash.buscar(nome)

    if not resultados:
        # Nome exato não achado na hash: pede ajuda à Trie (Módulo 2)
        sugestao = _buscar_com_sugestao_trie_generico(trie_global, nome)
        if sugestao is not None:
            resultados = [sugestao]
        else:
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
    custo = _pedir_float("  Custo (centavos de dólar) [padrão=0]: ") or 0
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
                    novo_c = _pedir_float("  Novo Custo: ")
                    if novo_c is not None:
                        receita.atualizar_custo(novo_c)
                        alteracoes_feitas.append("Custo")
                elif edicao == '3':
                    novo_t = _pedir_inteiro("  Novo Tempo: ")
                    if novo_t is not None:
                        receita.atualizar_tempo(novo_t)
                        alteracoes_feitas.append("Tempo")
                elif edicao == '4':
                    novo_f = _pedir_inteiro("  Novo Fator (ex: 110): ")
                    if novo_f is not None:
                        receita.atualizar_fator_recomendacao(novo_f)
                        alteracoes_feitas.append("Fator")
                elif edicao == '5':
                    ing_nome = input("  Nome do ingrediente a adicionar: ").strip()
                    if ing_nome:
                        qtd = _pedir_float("  Quantidade (número) [padrão=1]: ") or 1
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
                        # Nome exato não achado na hash: pede ajuda à Trie (Módulo 2)
                        preparo_obj = _buscar_com_sugestao_trie(trie_global, prep_nome, 'Receita')

                    if preparo_obj is None:
                        print("  ⚠ Receita não encontrada. Cadastre-a primeiro.")
                    elif _criaria_ciclo(oficina, receita, preparo_obj):
                        print(f"  ⛔ Operação bloqueada: '{receita.nome_receita}' -> "
                              f"'{preparo_obj.nome_receita}' criaria um ciclo de dependências "
                              f"(a Oficina de Produção/Módulo 5 não permite ciclos ao editar).")
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
        
def menu_modo_chef(motor, trie_global: TrieBuscaGeral) -> None:
    while True:
        print("\n" + "═" * 55)
        print("  MODO CHEF (MÓDULO 6 — MENU DEGUSTAÇÃO VIP)")
        print("═" * 55)
        print("  1. Gerar Menu VIP Otimizado (Automático)")
        print("  2. Ver Banco de Menus Salvos")
        print("  0. Voltar")
        
        opcao = input("  Escolha: ").strip()
        
        if opcao == "0":
            break
            
        elif opcao == "1":
            print("\n  [ CONFIGURAÇÃO DAS RESTRIÇÕES ]")
            limite_custo = _pedir_float("  Custo máximo total (centavos de dólar): ")
            if limite_custo is None: continue
                
            limite_tempo = _pedir_inteiro("  Tempo máximo de preparo (min): ")
            if limite_tempo is None: continue
                
            categorias_solicitadas = []
            pesos_categorias = []
            
            print("\n  [ COMPOSIÇÃO DO MENU ]")
            print("  Adicione as categorias desejadas (ex: Entradas, Pratos Principais, Sobremesas).")
            print("  Deixe o nome em branco para terminar a composição e iniciar a busca.\n")
            
            while True:
                nome_cat = input("  Nome da Categoria: ").strip()
                if not nome_cat: 
                    break
                    
                # Procura a categoria no registo global (nome exato)
                cat_obj = Categoria.registro_global.get(nome_cat.lower())
                if cat_obj is None:
                    # Nome exato não achado na hash: pede ajuda à Trie (Módulo 2)
                    cat_obj = _buscar_com_sugestao_trie(trie_global, nome_cat, 'Categoria')

                if not cat_obj or not cat_obj.lista_categoria_receitas:
                    print("    ⚠ Categoria não encontrada ou sem receitas. Tente novamente.")
                    continue
                    
                qtd = _pedir_inteiro(f"    Quantos pratos da categoria '{cat_obj.nome_categoria}'? [padrão=1]: ") or 1
                categorias_solicitadas.append(cat_obj)
                pesos_categorias.append(qtd)
                
            if not categorias_solicitadas:
                print("  ⚠ Operação cancelada: Nenhuma categoria foi adicionada.")
                continue
                
            print("\n  A calcular o menu perfeito... (Isto pode demorar alguns milissegundos 🚀)")
            
            # Instancia o motor e inicia a busca!
            otimizador = OtimizadorMenuVIP(categorias_solicitadas, pesos_categorias, limite_custo, limite_tempo)
            novo_menu = otimizador.buscar_menu_otimo()
            
            if novo_menu:
                novo_menu.exibir_recibo()
                print("  ✓ Menu gerado com sucesso!")
                
                guardar = input("  Deseja dar um nome e guardar este menu no sistema? (S/N): ").strip().upper()
                if guardar == 'S':
                    nome_customizado = input("  Digite o nome do Menu: ").strip()
                    if nome_customizado:
                        # Apaga a chave temporária e guarda com o nome definitivo
                        del Menu.registro_global[novo_menu.nome_menu.lower()]
                        novo_menu.nome_menu = nome_customizado
                        Menu.registro_global[nome_customizado.lower()] = novo_menu
                        print(f"  ✓ Menu '{nome_customizado}' guardado na memória!")
                else:
                    # Se não quiser guardar, removemos do banco de memória
                    del Menu.registro_global[novo_menu.nome_menu.lower()]
            else:
                print("\n  ✗ IMPOSSÍVEL! Nenhuma combinação de pratos atende a estas restrições.")
                print("    Tente aumentar o orçamento, o tempo, ou verificar as receitas disponíveis.")

        elif opcao == "2":
            if not Menu.registro_global:
                print("\n  ✗ Nenhum menu guardado no sistema.")
            else:
                while True:
                    print("\n  [ BANCO DE MENUS SALVOS ]")
                    lista_menus = list(Menu.registro_global.values())
                    for idx, menu_obj in enumerate(lista_menus, 1):
                        print(f"  {idx}. {menu_obj.nome_menu} (Custo: {menu_obj.custo_total:.2f}¢$ | Tempo: {menu_obj.tempo_total}m)")
                    print("  0. Voltar")
                    
                    escolha = _pedir_inteiro("\n  Escolha um menu para abrir (0 para voltar): ")
                    if escolha == 0 or escolha is None:
                        break
                    
                    if 1 <= escolha <= len(lista_menus):
                        menu_selecionado = lista_menus[escolha - 1]
                        menu_selecionado.exibir_recibo() # Imprime o layout chique do cardápio
                        
                        # --- SUB-MENU PARA INSPECIONAR AS RECEITAS ---
                        while True:
                            print("\n  [ OPÇÕES DO MENU ABERTO ]")
                            print("  1. Inspecionar uma receita específica deste menu")
                            print("  0. Voltar à lista de menus")
                            sub_opcao = input("  Escolha: ").strip()
                            
                            if sub_opcao == "0":
                                break
                            elif sub_opcao == "1":
                                # Achata (flatten) as receitas para listar tudo de forma numerada
                                pratos_flat = []
                                for pratos in menu_selecionado.pratos_por_categoria.values():
                                    pratos_flat.extend(pratos)
                                    
                                print("\n  [ PRATOS DO MENU ]")
                                for i, prato in enumerate(pratos_flat, 1):
                                    print(f"  {i}. {prato.nome_receita}")
                                print("  0. Cancelar")
                                
                                prato_idx = _pedir_inteiro("\n  Qual prato deseja inspecionar? ")
                                if prato_idx and 1 <= prato_idx <= len(pratos_flat):
                                    prato_selecionado = pratos_flat[prato_idx - 1]
                                    print(f"\n  --- DETALHES DA RECEITA: {prato_selecionado.nome_receita.upper()} ---")
                                    # Aproveita a função linda do motor para mostrar todos os dados!
                                    motor.exibir_recomendacao([prato_selecionado])
                            else:
                                print("  ⚠ Opção inválida.")
                    else:
                        print("  ⚠ Número de menu inválido.")


def _selecionar_pontos_malha(pontos: list, prompt: str, indice_excluir: int = None) -> list:
    """Mostra os índices já numerados de 'pontos' e devolve a lista de NoLogistico
    escolhidos a partir de uma entrada separada por vírgula. Usado pelos menus
    de logística (Módulos 7 e 8) para não repetir a mesma lógica de parsing."""
    entrada = input(prompt).strip()
    if not entrada:
        return []

    selecionados = []
    for token in entrada.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            idx = int(token)
        except ValueError:
            continue
        if 1 <= idx <= len(pontos) and idx != indice_excluir:
            selecionados.append(pontos[idx - 1])
    return selecionados


def menu_infraestrutura_minima(malha_urbana: dict, cache_rotas_global: dict) -> None:
    """MÓDULO 7 (parte 1) — 'A menor rede de conexões necessária para interligar
    todos os pontos operacionais.' Usa MST via Lazy Kruskal (Union-Find + heap,
    com A* real disparado só sob demanda para as arestas realmente promissoras)."""
    print("\n" + "═" * 55)
    print("  MÓDULO 7 — INFRAESTRUTURA MÍNIMA (MST)")
    print("═" * 55)

    if not malha_urbana:
        print("  ✗ Nenhuma malha urbana carregada (verifique data/malha_urbana.txt).")
        return

    print("  Determina a menor rede de conexões viárias necessária para ligar")
    print("  todos os pontos operacionais informados (cozinhas, hubs, etc.).\n")

    pontos = list(malha_urbana.values())
    print("  [ CRUZAMENTOS DISPONÍVEIS NA MALHA ]")
    for i, no in enumerate(pontos, 1):
        print(f"   {i:3d}. ({no.x:.0f}, {no.y:.0f})")

    pontos_operacionais = _selecionar_pontos_malha(
        pontos, "\n  Números dos pontos operacionais a conectar (separados por vírgula): "
    )
    if len(pontos_operacionais) < 2:
        print("  ⚠ Selecione ao menos 2 pontos para calcular uma infraestrutura.")
        return

    print("\n  Calculando infraestrutura mínima (Lazy Kruskal)...")
    mst, custo_total, astars_executados = OtimizadorInfraestrutura.gerar_mst_logistica(
        pontos_operacionais, cache_rotas_global
    )

    max_arestas_possiveis = (len(pontos_operacionais) * (len(pontos_operacionais) - 1)) // 2
    poupados = max_arestas_possiveis - astars_executados

    print("\n  " + "═" * 55)
    print(f"  📍 Pontos Conectados        : {len(pontos_operacionais)}")
    print(f"  💰 Custo Total da Rede      : {custo_total:.2f}")
    print(f"  🧠 A* Executados / Poupados : {astars_executados} / {max(poupados, 0)}")

    if not mst:
        print("  ⚠ Não foi possível conectar todos os pontos (malha desconexa).")
    else:
        adj = {}
        for p1, p2, custo_aresta, _rota in mst:
            adj.setdefault(p1, []).append((p2, custo_aresta))
            adj.setdefault(p2, []).append((p1, custo_aresta))

        print("\n  [ ÁRVORE GERADORA MÍNIMA — LISTA DE ADJACÊNCIA ]")
        for no in sorted(adj.keys(), key=lambda n: (n.x, n.y)):
            vizinhos_str = " | ".join(f"({v.x:.0f},{v.y:.0f}) [{c:.1f}]" for v, c in adj[no])
            print(f"    ({no.x:.0f},{no.y:.0f}) ➔ {vizinhos_str}")
    print("  " + "═" * 55)


def menu_capacidade_atendimento(malha_urbana: dict, cache_rotas_global: dict) -> None:
    """MÓDULO 7 (parte 2) — 'Qual a capacidade máxima de atendimento? Existe
    gargalo operacional?' Modela cozinhas (produção) e hubs (entregadores) como
    uma rede de Fluxo Máximo de Custo Mínimo (MCMF, via Bellman-Ford)."""
    print("\n" + "═" * 55)
    print("  MÓDULO 7 — CAPACIDADE MÁXIMA DE ATENDIMENTO (FLUXO)")
    print("═" * 55)

    if not malha_urbana:
        print("  ✗ Nenhuma malha urbana carregada (verifique data/malha_urbana.txt).")
        return

    print("  Calcula quantos pedidos o sistema consegue atender simultaneamente,")
    print("  dadas as capacidades de produção das cozinhas e de entrega dos hubs.\n")

    pontos = list(malha_urbana.values())
    print("  [ CRUZAMENTOS DISPONÍVEIS NA MALHA ]")
    for i, no in enumerate(pontos, 1):
        print(f"   {i:3d}. ({no.x:.0f}, {no.y:.0f})")

    indices_cozinhas = _selecionar_pontos_malha(
        pontos, "\n  Números dos pontos que serão COZINHAS (produção) — sep. vírgula: "
    )
    if not indices_cozinhas:
        print("  ⚠ Nenhuma cozinha informada.")
        return

    indices_hubs = _selecionar_pontos_malha(
        pontos, "\n  Números dos pontos que serão HUBS de entrega — sep. vírgula: "
    )
    if not indices_hubs:
        print("  ⚠ Nenhum hub informado.")
        return

    cozinhas = []
    for no in indices_cozinhas:
        cap = _pedir_inteiro(f"    Capacidade de produção (pratos/hora) em ({no.x:.0f},{no.y:.0f}) [padrão=30]: ") or 30
        cozinhas.append(CozinhaRegisto(no, cap))

    hubs = []
    for no in indices_hubs:
        cap = _pedir_inteiro(f"    Capacidade de entregadores em ({no.x:.0f},{no.y:.0f}) [padrão=10]: ") or 10
        hubs.append(PontoRetiradaRegisto(no, cap))

    print("\n  Construindo grafo virtual de fluxo (Vertex Splitting)...")
    motor_fluxo = MotorFluxoMCMF(cache_rotas=cache_rotas_global)
    motor_fluxo.construir_grafo_virtual(cozinhas, hubs)

    print("  Calculando fluxo máximo de custo mínimo (Bellman-Ford)...")
    fluxo_total, custo_total = motor_fluxo.calcular_fluxo_maximo_custo_minimo()

    cap_coz_max = sum(c.capacidade_pratos_hora for c in cozinhas)
    cap_hub_max = sum(h.capacidade_entregadores for h in hubs)

    print("\n  " + "═" * 55)
    print(f"  🍳 Teto de Produção   : {cap_coz_max} pratos/hora")
    print(f"  🛵 Teto Logístico     : {cap_hub_max} entregadores")
    print("  " + "─" * 55)
    print(f"  ✅ PEDIDOS ATENDIDOS  : {fluxo_total} pratos (Fluxo Máximo)")
    print(f"  💸 CUSTO OPERACIONAL  : {custo_total:.2f} ¢$ (Custo Mínimo)")

    if fluxo_total == 0:
        print("  ⚠ GARGALO DA REDE: nenhuma rota viária liga cozinhas a hubs.")
    elif fluxo_total == cap_coz_max:
        print("  ⚠ GARGALO DA REDE: a produção das cozinhas esgotou primeiro.")
    elif fluxo_total == cap_hub_max:
        print("  ⚠ GARGALO DA REDE: faltaram entregadores nos hubs.")
    else:
        print("  ⚠ GARGALO DA REDE: limitações viárias isolaram parte da capacidade.")

    print(f"\n  🧠 Cache de rotas A* compartilhado: {len(cache_rotas_global)} conexões memorizadas")
    print("  " + "═" * 55)


def menu_pesadelo_logistico(malha_urbana: dict, cache_rotas_global: dict) -> None:
    """MÓDULO 7 — O Pesadelo Logístico: agrupa a Infraestrutura Mínima (MST) e
    a Capacidade Máxima de Atendimento (Fluxo/Gargalo)."""
    while True:
        print("\n" + "═" * 55)
        print("  MÓDULO 7 — O PESADELO LOGÍSTICO")
        print("═" * 55)
        print("  1. Infraestrutura Mínima (MST — menor rede de conexões)")
        print("  2. Capacidade Máxima de Atendimento (Fluxo / Gargalo)")
        print("  0. Voltar")

        opcao = input("  Escolha: ").strip()
        if opcao == "0":
            break
        elif opcao == "1":
            menu_infraestrutura_minima(malha_urbana, cache_rotas_global)
        elif opcao == "2":
            menu_capacidade_atendimento(malha_urbana, cache_rotas_global)
        else:
            print("  ⚠ Opção inválida.")


def menu_roteamento_entregas(malha_urbana: dict, cache_rotas_global: dict) -> None:
    """MÓDULO 8 — Planejamento Inteligente de Entregas (TSP Híbrido).
    Determina uma rota única e eficiente para um entregador visitar vários
    clientes, minimizando a distância/tempo total percorrido."""
    print("\n" + "═" * 55)
    print("  MÓDULO 8 — ROTEAMENTO DE ENTREGAS (TSP HÍBRIDO)")
    print("═" * 55)

    if not malha_urbana:
        print("  ✗ Nenhuma malha urbana carregada (verifique data/malha_urbana.txt).")
        return

    print("  Monta uma rota única de entrega para vários clientes, minimizando")
    print("  a distância/tempo total percorrido (Convex Hull + Lazy Insertion + A*).\n")

    pontos = list(malha_urbana.values())
    print("  [ CRUZAMENTOS DISPONÍVEIS NA MALHA ]")
    for i, no in enumerate(pontos, 1):
        print(f"   {i:3d}. ({no.x:.0f}, {no.y:.0f})")

    idx_origem = _pedir_inteiro("\n  Número do ponto de DESPACHO (restaurante/hub): ")
    if not idx_origem or not (1 <= idx_origem <= len(pontos)):
        print("  ⚠ Ponto de despacho inválido.")
        return
    origem = pontos[idx_origem - 1]

    print("\n  Agora escolha os clientes a visitar (números separados por vírgula).")
    clientes = _selecionar_pontos_malha(pontos, "  Clientes: ", indice_excluir=idx_origem)

    if not clientes:
        print("  ⚠ Nenhum cliente válido informado.")
        return

    print("\n  Calculando o circuito de entregas...")
    circuito, custo_total, astars_executados = RoteadorEntregasTSP.resolver_tsp_hibrido(
        origem, clientes, cache_rotas_global
    )

    print("\n  " + "═" * 55)
    if not circuito or custo_total == float('inf'):
        print("  ❌ ROTA IMPOSSÍVEL: algum ponto está isolado na malha viária.")
    else:
        clientes_visitados = set(circuito) - {origem}
        clientes_isolados = set(clientes) - clientes_visitados

        print(f"  📍 Origem do Despacho    : ({origem.x:.0f}, {origem.y:.0f})")
        print(f"  📦 Clientes Visitados    : {len(clientes_visitados)} de {len(clientes)}")
        if clientes_isolados:
            print(f"  ⚠  Clientes Isolados     : {len(clientes_isolados)} (sem acesso viário)")
        print(f"  💰 Distância/Tempo Total : {custo_total:.2f}")
        print(f"  🧠 Caminhos A* Executados: {astars_executados} | Cache global: {len(cache_rotas_global)} rotas")

        itinerario_str = " ➔ ".join(f"({no.x:.0f},{no.y:.0f})" for no in circuito)
        print("\n  Itinerário sequencial do entregador:")
        print(f"    {itinerario_str}")
    print("  " + "═" * 55)


def menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente, trie_global, tabela_hash, oficina: OficinaProducao,
                   malha_urbana: dict, cache_rotas_global: dict):
    while True:
        print("\n╔" + "═" * 48 + "╗")
        print("║      DESAFIO NA COZINHA — MENU PRINCIPAL       ║")
        print("╠" + "═" * 48 + "╣")
        print("║  1. Ver vetor de recomendações (ordenado)      ║")
        print("║  2. Obter recomendação                         ║")
        print("║  3. Busca Geral (Nome/Prefixo) — Trie          ║")
        print("║  4. Busca por Nome Exato — Tabela Hash         ║")
        print("║  5. Diagnóstico da Tabela Hash                 ║")
        print("║  6. Adicionar nova receita                     ║")
        print("║  7. Salvar estado atual                        ║")
        print("║  8. Modo Investigação (Histórico/Lixeira)      ║")
        print("║  9. Oficina de Produção (Módulo 5)             ║")
        print("║ 10. Modo Chef (Módulo 6 - Menu Degustação VIP) ║")
        print("║ 11. Pesadelo Logístico (Módulo 7 - MST/Fluxo)  ║")
        print("║ 12. Roteamento de Entregas (Módulo 8 - TSP)    ║") # <-- NOVA OPÇÃO
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
        elif opcao == "10": menu_modo_chef(motor, trie_global)
        elif opcao == "11": menu_pesadelo_logistico(malha_urbana, cache_rotas_global)
        elif opcao == "12": menu_roteamento_entregas(malha_urbana, cache_rotas_global)
        elif opcao == "0":
            print("  A encerrar o sistema. Até logo!")
            break
        else: print("  Opção inválida.\n")


def main():
    print("\n" + "═" * 55)
    print("  INICIALIZAÇÃO DO SISTEMA")
    print("═" * 55)
    print("  Qual base de dados você deseja carregar?")
    print("  [1] Dados de Fábrica (dados_fonte.json)")
    print("  [2] Dados Salvos (dados_salvos.json)")
    print("  [3] Dados de Teste — Ciclos Propositais (dados_teste_ciclos.json)")

    escolha = input("  Opção [padrão=1]: ").strip()
    carregar_dados_salvos = (escolha == "2")
    carregar_teste_ciclos = (escolha == "3")

    print("\nCarregando dados do disco...")
    lista_receitas, lista_ingredientes, lista_categorias, mapa_id_ingrediente = \
        carregar_dados(usar_salvos=carregar_dados_salvos, usar_teste_ciclos=carregar_teste_ciclos)

    if carregar_teste_ciclos:
        print("  ⚠ Modo de TESTE: este dataset contém ciclos de dependência propositais")
        print("    (autodependência, ciclo de 2 e ciclo de 3) para demonstrar o Módulo 5.")
        
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

    # --- MÓDULO 7/8: LOGÍSTICA — Carrega a malha urbana para o Roteamento de Entregas ---
    caminho_malha = str(_RAIZ / "data" / "malha_urbana.txt")
    malha_urbana = carregar_malha_urbana(caminho_malha)
    cache_rotas_global: dict = {}  # cache de rotas A* compartilhado entre chamadas do Módulo 8
    print(f"  ✓ Malha urbana carregada: {len(malha_urbana)} cruzamentos (Módulo 8 pronto).")

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
                   lista_categorias, mapa_id_ingrediente, trie_global, tabela_hash, oficina,
                   malha_urbana, cache_rotas_global)

if __name__ == "__main__":
    main()