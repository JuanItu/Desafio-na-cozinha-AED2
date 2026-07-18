# motor/roteador_entregas.py

import heapq
from modelos.logistica import NoLogistico
from motor.roteador_logistico import RoteadorLogistico

# ══════════════════════════════════════════════════════════════════════
# 1. ESTRUTURA AUXILIAR: LISTA DUPLAMENTE ENCADEADA CIRCULAR
# ══════════════════════════════════════════════════════════════════════
class NoRota:
    __slots__ = ['no_logistico', 'prox', 'ant']
    
    def __init__(self, no_logistico: NoLogistico):
        self.no_logistico = no_logistico
        self.prox = self
        self.ant = self


class ListaCircularRota:
    """Representa a rota ativa permitindo inserções estruturais em O(1)"""
    def __init__(self):
        self.head = None
        self.tamanho = 0

    def inicializar_com_hull(self, lista_nos: list[NoLogistico]):
        if not lista_nos: 
            return
        
        self.head = NoRota(lista_nos[0])
        atual = self.head
        
        for no in lista_nos[1:]:
            novo = NoRota(no)
            novo.ant = atual
            atual.prox = novo
            atual = novo
            
        atual.prox = self.head
        self.head.ant = atual
        self.tamanho = len(lista_nos)

    def inserir_entre(self, no_isolado: NoLogistico, no_a: NoRota, no_b: NoRota) -> NoRota:
        """Estilhaça a ligação A -> B e intromete o nó isolado no meio em O(1)"""
        novo = NoRota(no_isolado)
        novo.ant = no_a
        novo.prox = no_b
        
        no_a.prox = novo
        no_b.ant = novo
        
        self.tamanho += 1
        return novo

    def obter_arestas_ativas(self) -> list[tuple[NoRota, NoRota]]:
        """Retorna todas as conexões ativas que compõem o anel atual"""
        if not self.head: 
            return []
        
        arestas = []
        atual = self.head
        for _ in range(self.tamanho):
            arestas.append((atual, atual.prox))
            atual = atual.prox
        return arestas


# ══════════════════════════════════════════════════════════════════════
# 2. MOTOR DO CAIXEIRO VIAJANTE HÍBRIDO (CONVEX HULL + LAZY INSERTION)
# ══════════════════════════════════════════════════════════════════════
class RoteadorEntregasTSP:

    @staticmethod
    def calcular_convex_hull(pontos: list[NoLogistico]) -> list[NoLogistico]:
        """
        Algoritmo Monotone Chain de Andrew para determinar a Envoltória Convexa.
        Complexidade: O(X log X) baseado estritamente na geometria (X, Y).
        """
        pontos = sorted(set(pontos), key=lambda p: (p.x, p.y))
        if len(pontos) <= 3:
            return pontos

        def produto_vetorial(o, a, b):
            # Retorna > 0 se curva à esquerda, < 0 se curva à direita
            return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

        # Construção do contorno inferior
        inferior = []
        for p in pontos:
            while len(inferior) >= 2 and produto_vetorial(inferior[-2], inferior[-1], p) <= 0:
                inferior.pop()
            inferior.append(p)

        # Construção do contorno superior
        superior = []
        for p in reversed(pontos):
            while len(superior) >= 2 and produto_vetorial(superior[-2], superior[-1], p) <= 0:
                superior.pop()
            superior.append(p)

        return inferior[:-1] + superior[:-1]

    @staticmethod
    def resolver_tsp_hibrido(origem: NoLogistico, clientes: list[NoLogistico], cache_global: dict = None) -> tuple[list[NoLogistico], float, int]:
        """
        Determina o circuito Hamiltoniano completo de entregas usando Lazy Farthest Insertion.
        Retorna: (Lista_de_Passos_da_Rota, Custo_Real_Total, Quantidade_de_A_Estrelas_Executados)
        """
        cache_rotas = cache_global.copy() if cache_global else {}

        todos_pontos = [origem] + clientes
        if len(todos_pontos) <= 1:
            return todos_pontos, 0.0, 0

        astars_executados = 0

        # ═════════════════════════════════════════════════════════════
        # FASE 1: SEMENTE INICIAL (Envoltória Convexa Externa)
        # ═════════════════════════════════════════════════════════════
        hull_geometrico = RoteadorEntregasTSP.calcular_convex_hull(todos_pontos)
        
        rota_circular = ListaCircularRota()
        rota_circular.inicializar_com_hull(hull_geometrico)

        # Descobre os nós isolados que ficaram confinados no interior do anel
        set_hull = set(hull_geometrico)
        nos_isolados = [p for p in todos_pontos if p not in set_hull]

        # ═════════════════════════════════════════════════════════════
        # FASE 2: ANEL BASE (Validação das arestas do Hull via A* Real)
        # ═════════════════════════════════════════════════════════════
        arestas_iniciais = rota_circular.obter_arestas_ativas()
        for no_a, no_b in arestas_iniciais:
            p1, p2 = no_a.no_logistico, no_b.no_logistico
            if (p1, p2) not in cache_rotas:
                astars_executados += 1
                _, custo_real = RoteadorLogistico.buscar_rota_a_estrela(p1, p2, 1.0)
                cache_rotas[(p1, p2)] = custo_real
                cache_rotas[(p2, p1)] = custo_real

        # ═════════════════════════════════════════════════════════════
        # FASE 3: INTROMISSÃO PREGUIÇOSA (Lazy Insertion com Min-Heap)
        # ═════════════════════════════════════════════════════════════
        heap_propostas = []
        contador = 0

        def gerar_propostas_para_aresta(no_a: NoRota, no_b: NoRota, lista_isolados: list[NoLogistico]):
            nonlocal contador
            p1, p2 = no_a.no_logistico, no_b.no_logistico
            custo_ab = cache_rotas[(p1, p2)]
            
            for isolado in lista_isolados:
                # Estimativa Euclidiana (Preguiçosa) para AD e DB
                est_ad = RoteadorLogistico.distancia_euclidiana(p1, isolado)
                est_db = RoteadorLogistico.distancia_euclidiana(isolado, p2)
                
                # Δ Estimado = AD + DB - AB (Linha Reta)
                delta_estimado = est_ad + est_db - custo_ab
                
                contador += 1
                # Tupla: (Delta, Nó_Isolado, No_A_Alvo, No_B_Alvo, Flag_AStar_Ok)
                heapq.heappush(heap_propostas, (delta_estimado, contador, isolado, no_a, no_b, False))

        # Popula a fila inicial com os nós internos contra o contorno da envoltória
        for no_a, no_b in arestas_iniciais:
            gerar_propostas_para_aresta(no_a, no_b, nos_isolados)

        inseridos = set(set_hull)

        # Loop de Intromissão
        while heap_propostas and len(inseridos) < len(todos_pontos):
            delta_atual, _, isolado, no_a, no_b, astar_ok = heapq.heappop(heap_propostas)

            if isolado in inseridos: 
                continue
                
            # VALIDAÇÃO DE EXISTÊNCIA: A aresta alvo ainda está intacta ou foi quebrada?
            if no_a.prox is not no_b: 
                continue

            p1, p2 = no_a.no_logistico, no_b.no_logistico

            if not astar_ok:
                # PAUSA E AVALIAÇÃO REAL: Dispara o A* apenas para a melhor proposta teórica
                astars_executados += 2
                
                if (p1, isolado) not in cache_rotas:
                    _, c_ad = RoteadorLogistico.buscar_rota_a_estrela(p1, isolado, 1.0)
                    cache_rotas[(p1, isolado)] = c_ad
                    cache_rotas[(isolado, p1)] = c_ad
                else:
                    c_ad = cache_rotas[(p1, isolado)]

                if (isolado, p2) not in cache_rotas:
                    _, c_db = RoteadorLogistico.buscar_rota_a_estrela(isolado, p2, 1.0)
                    cache_rotas[(isolado, p2)] = c_db
                    cache_rotas[(p2, isolado)] = c_db
                else:
                    c_db = cache_rotas[(isolado, p2)]
                    
                if c_ad == float('inf') or c_db == float('inf'):
                    continue

                custo_ab = cache_rotas[(p1, p2)]
                delta_real = c_ad + c_db - custo_ab

                contador += 1
                # Reinsere na fila marcado como validado real (True)
                heapq.heappush(heap_propostas, (delta_real, contador, isolado, no_a, no_b, True))
                
            else:
                # EFETIVAÇÃO DA INTROMISSÃO
                no_novo = rota_circular.inserir_entre(isolado, no_a, no_b)
                inseridos.add(isolado)
                nos_isolados.remove(isolado)

                # Alimenta o Heap com propostas para as duas novas sub-arestas geradas
                gerar_propostas_para_aresta(no_a, no_novo, nos_isolados)
                gerar_propostas_para_aresta(no_novo, no_b, nos_isolados)

        # ═════════════════════════════════════════════════════════════
        # RECONSTRUÇÃO DO CIRCUITO FINAL PARTINDO DA ORIGEM
        # ═════════════════════════════════════════════════════════════
        caminho_final_nos = []
        atual = rota_circular.head
        cabeca_origem = rota_circular.head
        
        # Rotaciona o anel para que a rota comece fisicamente no Restaurante/Origem
        for _ in range(rota_circular.tamanho):
            if atual.no_logistico is origem:
                cabeca_origem = atual
                break
            atual = atual.prox

        atual = cabeca_origem
        custo_total_real = 0.0
        for _ in range(rota_circular.tamanho):
            caminho_final_nos.append(atual.no_logistico)
            custo_total_real += cache_rotas[(atual.no_logistico, atual.prox.no_logistico)]
            atual = atual.prox
            
        caminho_final_nos.append(origem) # Fecha o circuito voltando ao ponto de despacho
        return caminho_final_nos, custo_total_real, astars_executados