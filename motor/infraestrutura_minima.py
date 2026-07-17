# motor/infraestrutura_minima.py

import heapq
from modelos.logistica import NoLogistico
from motor.roteador_logistico import RoteadorLogistico

# =====================================================================
# 1. UNION-FIND (Para controle de Ciclos na MST)
# =====================================================================
class UnionFind:
    def __init__(self, elementos: list):
        self.pai = {e: e for e in elementos}
        self.rank = {e: 0 for e in elementos}
        self.componentes_ativos = len(elementos)

    def find(self, i):
        if self.pai[i] != i:
            self.pai[i] = self.find(self.pai[i])
        return self.pai[i]

    def union(self, i, j) -> bool:
        raiz_i = self.find(i)
        raiz_j = self.find(j)

        if raiz_i == raiz_j: return False

        if self.rank[raiz_i] < self.rank[raiz_j]:
            self.pai[raiz_i] = raiz_j
        elif self.rank[raiz_i] > self.rank[raiz_j]:
            self.pai[raiz_j] = raiz_i
        else:
            self.pai[raiz_j] = raiz_i
            self.rank[raiz_i] += 1
            
        self.componentes_ativos -= 1
        return True


# =====================================================================
# 2. LAZY KRUSKAL ENGINE
# =====================================================================
class OtimizadorInfraestrutura:
    
    @staticmethod
    def gerar_mst_logistica(pontos_interesse: list[NoLogistico], cache_rotas: dict = None) -> tuple[list[tuple], float, int]:
        """
        Gera a Árvore Geradora Mínima usando Lazy Kruskal.
        Se 'cache_rotas' for fornecido, armazena os custos reais dos A* calculados nele.
        """
        if cache_rotas is None:
            cache_rotas = {}
            
        n_pontos = len(pontos_interesse)
        if n_pontos <= 1:
            return [], 0.0, 0
            
        uf = UnionFind(pontos_interesse)
        heap = []
        contador = 0 
        
        # 1. GERAÇÃO PREGUIÇOSA (Apenas Linha Reta)
        for i in range(n_pontos):
            for j in range(i + 1, n_pontos):
                p1 = pontos_interesse[i]
                p2 = pontos_interesse[j]
                
                # Custo otimista! Assume que a cidade é perfeita (Distância Euclidiana)
                custo_estimado = RoteadorLogistico.distancia_euclidiana(p1, p2)
                
                # Tupla do Heap: (Custo, Astar_Calculado_Flag, Contador, P1, P2, Rota_Real)
                contador += 1
                heapq.heappush(heap, (custo_estimado, False, contador, p1, p2, []))

        mst_final = []
        custo_total_mst = 0.0
        astars_executados = 0

        # 2. O LOOP DO KRUSKAL
        while heap and uf.componentes_ativos > 1:
            custo_atual, astar_ok, _, p1, p2, rota_caminho = heapq.heappop(heap)
            
            # PROTEÇÃO DE CICLOS ANTECIPADA: Se os pontos já estão na mesma ilha, descarta!
            if uf.find(p1) == uf.find(p2):
                continue
                
            # Aresta promissora, mas ainda é baseada em "Linha Reta"
            if not astar_ok:
                astars_executados += 1
                
                # Executa o A* Real com PESO 1.0 ABSOLUTO (Garantia de Corretude!)
                rota_real, custo_real = RoteadorLogistico.buscar_rota_a_estrela(p1, p2, peso_heuristica=1.0)
                
                if not rota_real:
                    continue # Se for impossível chegar fisicamente, a aresta morre aqui
                    
                # Injeta no cache compartilhado (Bidirecional)
                cache_rotas[(p1, p2)] = custo_real
                cache_rotas[(p2, p1)] = custo_real
                    
                # Devolve pro Heap com o custo real! (Mesmo se for igual à euclidiana, temos que provar)
                contador += 1
                heapq.heappush(heap, (custo_real, True, contador, p1, p2, rota_real))
            
            # É a Aresta Real Campeã! (Astar_ok == True)    
            else:
                if uf.union(p1, p2):
                    mst_final.append((p1, p2, custo_atual, rota_caminho))
                    custo_total_mst += custo_atual
        
        return mst_final, custo_total_mst, astars_executados