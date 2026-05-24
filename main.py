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

def menu_recomendacao(motor: AlgoritmoRecomendacao, lista_receitas, trie_global, tabela_hash) -> None:
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
            menu_visualizar_receita(resultados[escolha - 1], motor, lista_receitas, trie_global, tabela_hash)
        else: print("  ⚠ Opção inválida.\n")

def menu_busca_geral(motor, lista_receitas, trie_global: TrieBuscaGeral, tabela_hash) -> None:
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
            if tipo == 'receita': menu_visualizar_receita(obj, motor, lista_receitas, trie_global, tabela_hash)
            elif tipo == 'categoria': menu_visualizar_categoria(obj, motor, lista_receitas, trie_global, tabela_hash)
            elif tipo == 'ingrediente': menu_visualizar_ingrediente(obj, motor, lista_receitas, trie_global, tabela_hash)
        else: print("  ⚠ Opção inválida.")

def menu_busca_hash(motor, lista_receitas, trie_global, tabela_hash: TabelaHashNomes) -> None:
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
            if isinstance(obj_escolhido, Receita): menu_visualizar_receita(obj_escolhido, motor, lista_receitas, trie_global, tabela_hash)
            elif isinstance(obj_escolhido, Categoria): menu_visualizar_categoria(obj_escolhido, motor, lista_receitas, trie_global, tabela_hash)
            elif isinstance(obj_escolhido, Ingredientes): menu_visualizar_ingrediente(obj_escolhido, motor, lista_receitas, trie_global, tabela_hash)
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

    try:
        nova_receita = Receita(nome_receita=nome, custo=custo, tempo_preparo=tempo, fator_recomendacao=0.0, trie_global=trie_global, tabela_hash=tabela_hash)
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

def menu_visualizar_categoria(categoria: Categoria, motor, lista_receitas, trie_global, tabela_hash) -> None:
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
            menu_visualizar_receita(opcoes[escolha], motor, lista_receitas, trie_global, tabela_hash)
        else: print("  ⚠ Opção inválida.")

def menu_visualizar_ingrediente(ingrediente: Ingredientes, motor, lista_receitas, trie_global, tabela_hash) -> None:
    while True:
        print("\n" + "═" * 55)
        print(f"  INGREDIENTE: {ingrediente.nome_ingrediente.upper()}")
        print("═" * 55)
        
        opcoes = {}
        contador = 1
        
        print("  Receitas que usam este ingrediente:")
        if not ingrediente.lista_receitas_ingredientes: print("   - Nenhuma receita encontrada.")
        else:
            for rec in ingrediente.lista_receitas_ingredientes:
                print(f"   {contador}. {rec.nome_receita}")
                opcoes[str(contador)] = rec
                contador += 1
                
        print("\n  [E] Renomear Ingrediente | [X] Excluir Ingrediente | [0] Voltar")
        escolha = input("  Ação: ").strip().upper()
        
        if escolha == '0': break
        elif escolha == 'E':
            novo_nome = input("  Novo nome do ingrediente: ").strip()
            if novo_nome:
                try:
                    ingrediente.mudar_nome(novo_nome, trie_global, tabela_hash)
                    print("  ✓ Ingrediente renomeado!")
                except ValueError as e: print(f"  ⚠ Erro: {e}")
        elif escolha == 'X':
            confirmar = input("  Certeza que deseja excluir? (S/N): ").upper()
            if confirmar == 'S':
                ingrediente.excluir(trie_global, tabela_hash)
                print("  ✓ Ingrediente excluído!")
                break
        elif escolha in opcoes:
            menu_visualizar_receita(opcoes[escolha], motor, lista_receitas, trie_global, tabela_hash)
        else: print("  ⚠ Opção inválida.")

def menu_visualizar_receita(receita: Receita, motor, lista_receitas, trie_global, tabela_hash) -> None:
    while True:
        print("\n" + "═" * 55)
        print(f"  RECEITA: {receita.nome_receita.upper()}")
        print("═" * 55)
        print(f"  Tempo: {receita.tempo_preparo} min | Custo: {receita.custo}¢$ | Fator: {receita.fator_recomendacao}")
        
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
            if tipo == 'categoria': menu_visualizar_categoria(obj, motor, lista_receitas, trie_global, tabela_hash)
            else: menu_visualizar_ingrediente(obj, motor, lista_receitas, trie_global, tabela_hash)
        else: print("  ⚠ Opção inválida.")


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
        else: print("  ⚠ Opção inválida.")


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
        print("║  8. Modo Investigação (Histórico/Lixeira)      ║")
        print("║  0. Sair                                       ║")
        print("╚" + "═" * 48 + "╝")
        opcao = input("  Opção: ").strip()

        if opcao == "1": motor.exibir_lista(limite=15)
        elif opcao == "2": menu_recomendacao(motor, lista_receitas, trie_global, tabela_hash)
        elif opcao == "3": menu_busca_geral(motor, lista_receitas, trie_global, tabela_hash)
        elif opcao == "4": menu_busca_hash(motor, lista_receitas, trie_global, tabela_hash)
        elif opcao == "5": menu_diagnostico_hash(tabela_hash)
        elif opcao == "6": menu_adicionar_receita(motor, lista_receitas, trie_global, tabela_hash)
        elif opcao == "7": salvar_dados(lista_receitas, lista_ingredientes, lista_categorias, mapa_id_ingrediente)
        elif opcao == "8": menu_investigacao()
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

    menu_principal(motor, lista_receitas, lista_ingredientes,
                   lista_categorias, mapa_id_ingrediente, trie_global, tabela_hash)

if __name__ == "__main__":
    main()