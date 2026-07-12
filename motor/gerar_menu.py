import heapq
from modelos.menu import Menu

# ══════════════════════════════════════════════════════════════════════
# 1. ESTADO DO MENU (A partícula que trafega no Max-Heap)
# ══════════════════════════════════════════════════════════════════════
class EstadoMenu:
    __slots__ = ['assinatura_ids', 'lucro_total', 'custo_total', 'tempo_total', 'semantica', 'valores_por_cat']

    def __init__(self, assinatura_ids: tuple, lucro_total: float, custo_total: float, tempo_total: int, semantica: tuple, valores_por_cat: list):
        self.assinatura_ids = assinatura_ids 
        self.lucro_total = lucro_total
        self.custo_total = custo_total
        self.tempo_total = tempo_total
        self.semantica = semantica           
        self.valores_por_cat = valores_por_cat 

    def __lt__(self, outro: 'EstadoMenu'):
        # Mantém a mágica do Max-Heap priorizando o maior lucro
        return self.lucro_total > outro.lucro_total
        
    def __repr__(self):
        return f"<EstadoMenu Lucro:{self.lucro_total} Custo:{self.custo_total} IDs:{self.assinatura_ids}>"


# ══════════════════════════════════════════════════════════════════════
# 2. NÓ DA TRIE DINÂMICA
# ══════════════════════════════════════════════════════════════════════
class NodeTrieVIP:
    __slots__ = ['soma_lucro', 'soma_custo', 'soma_tempo', 'id_folha', 'filhos']

    def __init__(self, soma_lucro: float, soma_custo: float, soma_tempo: int):
        self.soma_lucro = soma_lucro
        self.soma_custo = soma_custo
        self.soma_tempo = soma_tempo
        self.id_folha = None 
        self.filhos = None   


# ══════════════════════════════════════════════════════════════════════
# 3. A TRIE DA CATEGORIA (Geradora Contínua com Poda Segura)
# ══════════════════════════════════════════════════════════════════════
class TrieCategoria:
    def __init__(self, lista_receitas_ordenada: list, qtd_exigida: int, teto_custo_item: float, teto_tempo_item: int, extrator_metrica):
        self.receitas = lista_receitas_ordenada 
        self.qtd_exigida = qtd_exigida
        self.teto_custo_item = teto_custo_item
        self.teto_tempo_item = teto_tempo_item
        self.extrator_metrica = extrator_metrica # Guarda a função que sabe extrair o valor
        
        self.root = NodeTrieVIP(0.0, 0.0, 0)
        self.contador_id = 0
        
    def obter_dados_no_inicial(self, semantica_inicial: tuple) -> tuple:
        return self._registrar_caminho_na_trie(list(semantica_inicial))
        
    def obter_vizinhos_validos(self, semantica_base: tuple) -> list:
        vizinhos_descobertos = []

        for pos_alvo in range(self.qtd_exigida):
            idx_atual = semantica_base[pos_alvo]
            
            # Limite para não encostar no próximo índice (Regra da Desigualdade)
            if pos_alvo < self.qtd_exigida - 1:
                limite_indice = semantica_base[pos_alvo + 1] 
            else:
                limite_indice = len(self.receitas)           

            # A GERAÇÃO DE ONDA CONTÍNUA: Avança apenas para o PRÓXIMO prato válido
            for idx_candidato in range(idx_atual + 1, limite_indice):
                rec_candidato = self.receitas[idx_candidato]
                
                # PODA MÁXIMA SEGURA O(1): O prato estoura o limite do universo?
                if rec_candidato.custo > self.teto_custo_item or rec_candidato.tempo_preparo > self.teto_tempo_item:
                    continue # "Passa reto". O prato é impossível, mas o próximo pode ser mais barato!
                
                # Se chegou aqui, achou o vizinho imediato viável.
                nova_semantica = list(semantica_base)
                nova_semantica[pos_alvo] = idx_candidato
                
                id_folha, n_luc, n_cus, n_tem = self._registrar_caminho_na_trie(nova_semantica)
                vizinhos_descobertos.append((tuple(nova_semantica), id_folha, n_luc, n_cus, n_tem))
                
                # PARA IMEDIATAMENTE (break). Deixa o Heap pedir o próximo vizinho no futuro.
                break 

        return vizinhos_descobertos

    def _registrar_caminho_na_trie(self, semantica_nova: list) -> tuple:
        no_atual = self.root
        for idx in semantica_nova:
            if no_atual.filhos is None: no_atual.filhos = {}
            if idx not in no_atual.filhos:
                rec = self.receitas[idx]
                no_atual.filhos[idx] = NodeTrieVIP(
                    # AQUI ESTÁ A MÁGICA: Usa a função lambda para extrair o valor correto
                    no_atual.soma_lucro + self.extrator_metrica(rec), 
                    no_atual.soma_custo + rec.custo,
                    no_atual.soma_tempo + rec.tempo_preparo
                )
            no_atual = no_atual.filhos[idx]
            
        if no_atual.id_folha is None:
            self.contador_id += 1
            no_atual.id_folha = self.contador_id
            
        return no_atual.id_folha, no_atual.soma_lucro, no_atual.soma_custo, no_atual.soma_tempo


# ══════════════════════════════════════════════════════════════════════
# 4. O ORQUESTRADOR GLOBAL (Setup O(N) e Execução Inquebrável)
# ══════════════════════════════════════════════════════════════════════
class OtimizadorMenuVIP:
    # Novo parâmetro 'criterio_maximizacao' com valor default garantindo compatibilidade
    def __init__(self, categorias_solicitadas: list, pesos_categorias: list, limite_custo: float, limite_tempo: int, criterio_maximizacao: str = 'fator_recomendacao'):
        self.categorias_solicitadas = categorias_solicitadas
        self.limite_custo = limite_custo
        self.limite_tempo = limite_tempo
        self.num_cats = len(categorias_solicitadas)
        self.impossivel_de_fabrica = False
        self.criterio_maximizacao = criterio_maximizacao

        # Define qual atributo será otimizado de forma dinâmica (Estratégia)
        if self.criterio_maximizacao == 'lucro':
            # Lucro financeiro = Preço de venda - Custo de produção
            self.extrator_metrica = lambda r: (r.preco - r.custo)
        else:
            # Padrão: popularidade/fator do chef
            self.extrator_metrica = lambda r: r.fator_recomendacao
        
        # --- 1. SETUP DE PERFORMANCE: (Continua exatamente IGUAL) ---
        soma_minima_custo_global = 0.0
        soma_minima_tempo_global = 0
        minimos_por_cat = []
        
        for i, cat in enumerate(categorias_solicitadas):
            qtd = pesos_categorias[i]
            if qtd > len(cat.lista_categoria_receitas):
                self.impossivel_de_fabrica = True
                return
                
            custos = sorted([r.custo for r in cat.lista_categoria_receitas])
            tempos = sorted([r.tempo_preparo for r in cat.lista_categoria_receitas])
            
            min_custo_cat = sum(custos[:qtd])
            min_tempo_cat = sum(tempos[:qtd])
            min_custo_outros = sum(custos[:qtd-1]) if qtd > 1 else 0.0
            min_tempo_outros = sum(tempos[:qtd-1]) if qtd > 1 else 0
            
            minimos_por_cat.append((min_custo_cat, min_custo_outros, min_tempo_cat, min_tempo_outros))
            soma_minima_custo_global += min_custo_cat
            soma_minima_tempo_global += min_tempo_cat
            
        if soma_minima_custo_global > limite_custo or soma_minima_tempo_global > limite_tempo:
            self.impossivel_de_fabrica = True
            return

        # --- 2. INJEÇÃO DOS TETOS NAS TRIES ---
        self.tries = []
        for i, cat in enumerate(categorias_solicitadas):
            # A ordenação agora usa a lambda dinâmica!
            lista_ordenada = sorted(cat.lista_categoria_receitas, key=self.extrator_metrica, reverse=True)
            
            m_custo_cat, m_custo_outros, m_tempo_cat, m_tempo_outros = minimos_por_cat[i]
            
            teto_custo_item = limite_custo - (soma_minima_custo_global - m_custo_cat) - m_custo_outros
            teto_tempo_item = limite_tempo - (soma_minima_tempo_global - m_tempo_cat) - m_tempo_outros
            
            # Repassamos a lambda para a Trie saber como somar os valores
            self.tries.append(TrieCategoria(
                lista_ordenada, pesos_categorias[i], 
                teto_custo_item, teto_tempo_item, 
                self.extrator_metrica # <--- Passando o extrator
            ))

    def buscar_menu_otimo(self):
        if self.impossivel_de_fabrica:
            print("  ⚠ IMPOSSÍVEL: O orçamento/tempo não compra nem as opções mais baratas disponíveis.")
            return None
        
        semantica_inicial = []
        assinatura_inicial = []
        valores_por_cat_inicial = []
        lucro_global = custo_global = tempo_global = 0
        
        for i, trie in enumerate(self.tries):
            sub_tupla_inicial = tuple(range(trie.qtd_exigida))
            semantica_inicial.append(sub_tupla_inicial)
            
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

        heap = [estado_raiz]
        seen = {estado_raiz.assinatura_ids}

        while heap:
            atual: EstadoMenu = heapq.heappop(heap)
    
            # VALIDAÇÃO GLOBAL: Como não pulamos estados, o primeiro que passar aqui é a solução perfeita!
            if atual.custo_total <= self.limite_custo and atual.tempo_total <= self.limite_tempo:
                menu_final = Menu(nome_menu="Menu Degustação Otimizado")
                pratos_dict = {}
                for c in range(self.num_cats):
                    nome_categoria = self.categorias_solicitadas[c].nome_categoria
                    pratos_dict[nome_categoria] = []
                    for idx in atual.semantica[c]:
                        pratos_dict[nome_categoria].append(self.tries[c].receitas[idx])
                menu_final.definir_pratos(pratos_dict)
                return menu_final 

            # EXPANSÃO CONTÍNUA (Muito mais limpa e focada no avanço topológico)
            for c in range(self.num_cats):
                trie_alvo = self.tries[c]
                
                # A Trie agora gerencia a própria segurança internamente usando os tetos fixos!
                vizinhos_da_categoria = trie_alvo.obter_vizinhos_validos(atual.semantica[c])
                
                for nova_sub, id_folha, n_lucro, n_custo, n_tempo in vizinhos_da_categoria:
                    nova_assinatura = list(atual.assinatura_ids)
                    nova_assinatura[c] = id_folha
                    nova_assinatura_tupla = tuple(nova_assinatura)
                    
                    if nova_assinatura_tupla in seen:
                        continue 
                        
                    lucro_antigo, custo_antigo, tempo_antigo = atual.valores_por_cat[c]
                    
                    novo_lucro = atual.lucro_total - lucro_antigo + n_lucro
                    novo_custo = atual.custo_total - custo_antigo + n_custo
                    novo_tempo = atual.tempo_total - tempo_antigo + n_tempo
                    
                    nova_semantica = list(atual.semantica)
                    nova_semantica[c] = nova_sub
                    
                    novos_valores = list(atual.valores_por_cat)
                    novos_valores[c] = (n_lucro, n_custo, n_tempo)
                    
                    novo_estado = EstadoMenu(
                        nova_assinatura_tupla, novo_lucro, novo_custo, novo_tempo,
                        tuple(nova_semantica), novos_valores
                    )
                    
                    seen.add(nova_assinatura_tupla)
                    heapq.heappush(heap, novo_estado)

        return None