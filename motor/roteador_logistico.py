# motor/roteador_logistico.py

import heapq
import math
from modelos.logistica import NoLogistico

class RoteadorLogistico:
    
    @staticmethod
    def distancia_euclidiana(no_a: NoLogistico, no_b: NoLogistico) -> float:
        """Heurística baseada em linha reta para a malha urbana."""
        return math.hypot(no_a.x - no_b.x, no_a.y - no_b.y)

    @staticmethod
    def buscar_rota_a_estrela(origem: NoLogistico, destino: NoLogistico, peso_heuristica: float = 1.0) -> tuple[list[NoLogistico], float]:
        """
        Encontra o caminho mais curto usando A* (ou Dijkstra se peso_heuristica = 0).
        Retorna: (lista_do_caminho, custo_total)
        """
        # Se origem e destino forem o mesmo ponto
        if origem is destino:
            return [origem], 0.0

        # Fila de prioridade e contador de desempate
        contador = 0
        # Tupla do Heap: (f_score_estimado, contador_desempate, no_atual)
        fila = [(0.0, contador, origem)]
        
        # Estruturas de rastreamento
        came_from = {}
        g_score = {origem: 0.0} # Custo real percorrido desde a origem
        
        while fila:
            _, _, atual = heapq.heappop(fila)
            
            # Condição de Parada: Chegamos no destino!
            if atual is destino:
                caminho_final = RoteadorLogistico._reconstruir_caminho(came_from, atual)
                return caminho_final, g_score[atual]
                
            # Varredura dos vizinhos (Arestas)
            for aresta in atual.adjacencias:
                vizinho = aresta.destino
                custo_tentativo = g_score[atual] + aresta.peso
                
                # Se achamos um caminho melhor (ou inédito) para este vizinho
                if vizinho not in g_score or custo_tentativo < g_score[vizinho]:
                    came_from[vizinho] = atual
                    g_score[vizinho] = custo_tentativo
                    
                    # f(n) = g(n) + w * h(n)
                    h_score = RoteadorLogistico.distancia_euclidiana(vizinho, destino)
                    f_score = custo_tentativo + (peso_heuristica * h_score)
                    
                    contador += 1
                    heapq.heappush(fila, (f_score, contador, vizinho))
                    
        # Se a fila esvaziar e não achar o destino, não existe caminho físico
        return [], float('inf')

    @staticmethod
    def _reconstruir_caminho(came_from: dict, atual: NoLogistico) -> list[NoLogistico]:
        """Faz o caminho reverso do destino até a origem e inverte a lista."""
        caminho = [atual]
        while atual in came_from:
            atual = came_from[atual]
            caminho.append(atual)
        caminho.reverse()
        return caminho