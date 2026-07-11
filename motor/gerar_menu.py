import heapq
from modelos.menu import Menu

# ══════════════════════════════════════════════════════════════════════
# 1. ESTADO DO MENU (A partícula que trafega no Max-Heap)
# ══════════════════════════════════════════════════════════════════════
class EstadoMenu:
    __slots__ = ['assinatura_ids', 'lucro_total', 'custo_total', 'tempo_total', 'semantica', 'valores_por_cat']

    def __init__(self, assinatura_ids: tuple, lucro_total: float, custo_total: float, tempo_total: int, semantica: tuple, valores_por_cat: list):
        self.assinatura_ids = signature_ids = assinatura_ids # Ex: (15, 3, 42) -> Para o HashSet O(1)
        self.lucro_total = lucro_total
        self.custo_total = custo_total
        self.tempo_total = tempo_total
        self.semantica = semantica           # Ex: ((0,2), (1), (0,3)) -> Índices das receitas
        self.valores_por_cat = valores_por_cat # Guarda [(lucro, custo, tempo)] de cada categoria para transição O(1)

    def __lt__(self, outro: 'EstadoMenu'):
        # MÁGICA DO MAX-HEAP: Inverte a lógica para o heapq do Python priorizar o maior lucro
        return self.lucro_total > outro.lucro_total
        
    def __repr__(self):
        return f"<EstadoMenu Lucro:{self.lucro_total} Custo:{self.custo_total} IDs:{self.assinatura_ids}>"


# ══════════════════════════════════════════════════════════════════════
# 2. NÓ DA TRIE DINÂMICA
# ══════════════════════════════════════════════════════════════════════
class NodeTrieVIP:
    __slots__ = ['soma_lucro', 'soma_custo', 'soma_tempo', 'prefix_invalid', 'id_folha', 'filhos']

    def __init__(self, soma_lucro: float, soma_custo: float, soma_tempo: int):
        self.soma_lucro = soma_lucro
        self.soma_custo = soma_custo
        self.soma_tempo = soma_tempo
        self.prefix_invalid = False
        self.id_folha = None 
        self.filhos = None   


# ══════════════════════════════════════════════════════════════════════
# 3. A TRIE DA CATEGORIA (Geradora Ativa de Vizinhos locais via DFS)
# ══════════════════════════════════════════════════════════════════════
class TrieCategoria:
    def __init__(self, lista_receitas_ordenada: list, qtd_exigida: int):
        self.receitas = lista_receitas_ordenada 
        self.qtd_exigida = qtd_exigida          
        self.root = NodeTrieVIP(0.0, 0.0, 0)
        self.contador_id = 0 
        
    def obter_dados_no_inicial(self, semantica_inicial: tuple) -> tuple:
        """Helper para construir a raiz inicial (0,1,2...) e cadastrá-la na árvore física."""
        # Reaproveita a função que já temos para instanciar a tupla na Trie e pegar os totais
        return self._registrar_caminho_na_trie(list(semantica_inicial))
        
    def obter_vizinhos_validos(self, semantica_base: tuple, custo_atual_cat: float, tempo_atual_cat: int, max_custo_cat: float, max_tempo_cat: int) -> list:
        vizinhos_descobertos = []

        # Tenta gerar 1 vizinho válido avançando cada uma das posições
        for pos_alvo in range(self.qtd_exigida):
            idx_atual = semantica_base[pos_alvo]
            
            # 1. A MATEMÁTICA MILIMÉTRICA: Isola o custo/tempo apenas das receitas que ficarão FIXAS
            custo_itens_fixos = custo_atual_cat - self.receitas[idx_atual].custo
            tempo_itens_fixos = tempo_atual_cat - self.receitas[idx_atual].tempo_preparo
            
            # O que sobrou é o teto máximo absoluto para a receita que vamos testar
            orcamento_item = max_custo_cat - custo_itens_fixos
            tempo_max_item = max_tempo_cat - tempo_itens_fixos
            
            # 2. A REGRA DA DESIGUALDADE (n < a): Define o limite do laço sem precisar de 'ifs'
            if pos_alvo < self.qtd_exigida - 1:
                limite_indice = semantica_base[pos_alvo + 1] # Não pode encostar no próximo índice
            else:
                limite_indice = len(self.receitas)           # Se for o último, vai até o fim do cardápio

            # 3. O SCAN LINEAR CONGELADO (Acha o primeiro que cabe no orçamento)
            for idx_candidato in range(idx_atual + 1, limite_indice):
                rec_candidato = self.receitas[idx_candidato]
                
                # Passou no limite milimétrico? Achamos o vizinho exato!
                if rec_candidato.custo <= orcamento_item and rec_candidato.tempo_preparo <= tempo_max_item:
                    
                    nova_semantica = list(semantica_base)
                    nova_semantica[pos_alvo] = idx_candidato
                    
                    # Registra a nova tupla na Trie física apenas para gerar o ID e cachear os valores
                    id_folha, n_luc, n_cus, n_tem = self._registrar_caminho_na_trie(nova_semantica)
                    
                    vizinhos_descobertos.append((tuple(nova_semantica), id_folha, n_luc, n_cus, n_tem))
                    
                    # Para a busca nesta 'pos_alvo', pois o Max-Heap cuidará de pedir o próximo!
                    break 

        return vizinhos_descobertos

    def _registrar_caminho_na_trie(self, semantica_nova: list) -> tuple:
        """Cria os nós faltantes na Trie e retorna os dados da folha (id, lucro, custo, tempo)"""
        no_atual = self.root
        for idx in semantica_nova:
            if no_atual.filhos is None: no_atual.filhos = {}
            if idx not in no_atual.filhos:
                rec = self.receitas[idx]
                no_atual.filhos[idx] = NodeTrieVIP(
                    no_atual.soma_lucro + rec.fator_recomendacao,
                    no_atual.soma_custo + rec.custo,
                    no_atual.soma_tempo + rec.tempo_preparo
                )
            no_atual = no_atual.filhos[idx]
            
        if no_atual.id_folha is None:
            self.contador_id += 1
            no_atual.id_folha = self.contador_id
            
        return no_atual.id_folha, no_atual.soma_lucro, no_atual.soma_custo, no_atual.soma_tempo


# ══════════════════════════════════════════════════════════════════════
# 4. O ORQUESTRADOR GLOBAL (O Maestro do Max-Heap e das Tries)
# ══════════════════════════════════════════════════════════════════════
class OtimizadorMenuVIP:
    def __init__(self, categorias_solicitadas: list, pesos_categorias: list, limite_custo: float, limite_tempo: int):
        """
        categorias_solicitadas: lista de objetos Categoria
        pesos_categorias: lista de inteiros com a quantidade exigida (ex: [2, 1, 3])
        """
        self.categorias_solicitadas = categorias_solicitadas
        self.limite_custo = limite_custo
        self.limite_tempo = limite_tempo
        self.num_cats = len(categorias_solicitadas)
        
        # Constrói as Tries gulosas alimentadas pelas listas das Categorias
        self.tries: list[TrieCategoria] = []
        for i, cat in enumerate(categorias_solicitadas):
            # Garante a ordenação decrescente por Fator de Recomendação/Lucro
            lista_ordenada = sorted(cat.lista_categoria_receitas, key=lambda r: r.fator_recomendacao, reverse=True)
            self.tries.append(TrieCategoria(lista_ordenada, pesos_categorias[i]))

    def buscar_menu_otimo(self):
        # PROTEÇÃO: Verifica se o restaurante tem pratos suficientes para a exigência
        for trie in self.tries:
            if trie.qtd_exigida > len(trie.receitas):
                print(f"  ⚠ IMPOSSÍVEL: Você pediu {trie.qtd_exigida} pratos, mas uma das categorias só possui {len(trie.receitas)} receita(s) válida(s).")
                return None
        
        # 1. Monta o Estado Inicial Base (0, 1, 2...) respeitando as desigualdades de cada categoria
        semantica_inicial = []
        assinatura_inicial = []
        valores_por_cat_inicial = []
        
        lucro_global = 0.0
        custo_global = 0.0
        tempo_global = 0
        
        for i, trie in enumerate(self.tries):
            sub_tupla_inicial = tuple(range(trie.qtd_exigida))
            semantica_inicial.append(sub_tupla_inicial)
            
            # Inicializa fisicamente a árvore e resgata os custos/lucros parciais
            id_folha, lucro_cat, custo_cat, tempo_cat = trie.obter_dados_no_inicial(sub_tupla_inicial)
            assinatura_inicial.append(id_folha)
            valores_por_cat_inicial.append((lucro_cat, custo_cat, tempo_cat))
            
            lucro_global += lucro_cat
            custo_global += custo_cat
            tempo_global += tempo_cat

        estado_raiz = EstadoMenu(
            tuple(assinatura_inicial), lucro_global, custo_global, tempo_global, 
            tuple(semantica_inicial), valores_por_cat_inicial
        )

        # Inicializa o Max-Heap e o HashSet de segurança antecipada (Marcar no Push)
        heap = [estado_raiz]
        seen = {estado_raiz.assinatura_ids}

        while heap:
            # Pop da combinação com maior lucro global teórico disponível
            atual: EstadoMenu = heapq.heappop(heap)
    
            # VALIDAÇÃO GLOBAL FINAL: Se passou por aqui, achou!
            if atual.custo_total <= self.limite_custo and atual.tempo_total <= self.limite_tempo:
                
                # --- O OTIMIZADOR SE COMPORTA COMO UMA FÁBRICA DE MENUS ---
                menu_final = Menu(nome_menu="Menu Degustação Otimizado")
                pratos_dict = {}
                
                # Traduz as posições matemáticas para as receitas reais
                for c in range(self.num_cats):
                    nome_categoria = self.categorias_solicitadas[c].nome_categoria
                    pratos_dict[nome_categoria] = []
                    
                    indices_vencedores = atual.semantica[c]
                    for idx in indices_vencedores:
                        receita_real = self.tries[c].receitas[idx]
                        pratos_dict[nome_categoria].append(receita_real)
                        
                # Entrega os pratos pro modelo e ele recalcula tudo sozinho!
                menu_final.definir_pratos(pratos_dict)
                return menu_final # Retorna um objeto limpo e independente da classe Menu!

            # EXPANSÃO DE VIZINHOS: Varia uma categoria por vez
            for c in range(self.num_cats):
                trie_alvo = self.tries[c]
                sub_tupla_atual_cat = atual.semantica[c]
                
                # A SUA SACADA: Subtrai o custo/tempo das OUTRAS categorias para achar o limite exato desta!
                custo_outras_cats = atual.custo_total - atual.valores_por_cat[c][1]
                tempo_outras_cats = atual.tempo_total - atual.valores_por_cat[c][2]
                
                limite_custo_cat = self.limite_custo - custo_outras_cats
                limite_tempo_cat = self.limite_tempo - tempo_outras_cats
                
                # Chama a Trie passando o orçamento espremido
                vizinhos_da_categoria = trie_alvo.obter_vizinhos_validos(
                    sub_tupla_atual_cat, 
                    atual.valores_por_cat[c][1], # Custo atual SÓ desta categoria
                    atual.valores_por_cat[c][2], # Tempo atual SÓ desta categoria
                    limite_custo_cat, 
                    limite_tempo_cat
                )
                
                for nova_sub, id_folha, n_lucro, n_custo, n_tempo in vizinhos_da_categoria:
                    
                    # Constrói a assinatura de IDs para checar o HashSet em O(1)
                    nova_assinatura = list(atual.assinatura_ids)
                    nova_assinatura[c] = id_folha
                    nova_assinatura_tupla = tuple(nova_assinatura)
                    
                    if nova_assinatura_tupla in seen:
                        continue # Evita Queue Explosion na raiz!
                        
                    # TRANSIÇÃO DE ESTADO EM O(1): Aproveita o cálculo anterior e troca apenas a fatia da cat 'c'
                    lucro_antigo_cat, custo_antigo_cat, tempo_antigo_cat = atual.valores_por_cat[c]
                    
                    novo_lucro_global = atual.lucro_total - lucro_antigo_cat + n_lucro
                    novo_custo_global = atual.custo_total - custo_antigo_cat + n_custo
                    novo_tempo_global = atual.tempo_total - tempo_antigo_cat + n_tempo
                    
                    nova_semantica = list(atual.semantica)
                    nova_semantica[c] = nova_sub
                    
                    novos_valores_cat = list(atual.valores_por_cat)
                    novos_valores_cat[c] = (n_lucro, n_custo, n_tempo)
                    
                    novo_estado = EstadoMenu(
                        nova_assinatura_tupla, novo_lucro_global, novo_custo_global, novo_tempo_global,
                        tuple(nova_semantica), novos_valores_cat
                    )
                    
                    # Cadastro antecipado e injeção na fila
                    seen.add(nova_assinatura_tupla)
                    heapq.heappush(heap, novo_estado)

        return None # Caso não exista nenhuma combinação viável no restaurante inteiro