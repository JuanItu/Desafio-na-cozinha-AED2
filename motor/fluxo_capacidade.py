# motor/fluxo_capacidade.py

from modelos.rede_fluxo import NoFluxo, ArestaFluxo
from motor.roteador_logistico import RoteadorLogistico

class MotorFluxoMCMF:
    def __init__(self, cache_rotas: dict = None):
        self.grafo: dict[str, NoFluxo] = {}
        # Se não passarem um cache, cria um local, mas o ideal é vir compartilhado do Kruskal!
        self.cache_rotas = cache_rotas if cache_rotas is not None else {}
        
    def _obter_ou_criar_no(self, id_nome: str) -> NoFluxo:
        if id_nome not in self.grafo:
            self.grafo[id_nome] = NoFluxo(id_nome)
        return self.grafo[id_nome]

    def construir_grafo_virtual(self, cozinhas: list, hubs: list):
        super_fonte = self._obter_ou_criar_no("SUPER_FONTE")
        super_sumidouro = self._obter_ou_criar_no("SUPER_SUMIDOURO")
        INF = 999999999
        
        # [ Trecho de Vertex Splitting de Cozinhas e Hubs permanece igual, custo=0 ]
        for coz in cozinhas:
            id_in, id_out = f"COZ_IN_{coz.no_basico.coordenadas}", f"COZ_OUT_{coz.no_basico.coordenadas}"
            self._obter_ou_criar_no(id_in).adicionar_aresta(self._obter_ou_criar_no(id_out), coz.capacidade_pratos_hora, 0)
            super_fonte.adicionar_aresta(self._obter_ou_criar_no(id_in), INF, 0)
            
        for hub in hubs:
            id_in, id_out = f"HUB_IN_{hub.no_basico.coordenadas}", f"HUB_OUT_{hub.no_basico.coordenadas}"
            self._obter_ou_criar_no(id_in).adicionar_aresta(self._obter_ou_criar_no(id_out), hub.capacidade_entregadores, 0)
            self._obter_ou_criar_no(id_out).adicionar_aresta(super_sumidouro, INF, 0)
            
        # O SEU PASSO SEGURO: Conectar Cozinhas aos Hubs de forma PREGUIÇOSA
        for coz in cozinhas:
            for hub in hubs:
                id_coz_out = f"COZ_OUT_{coz.no_basico.coordenadas}"
                id_hub_in = f"HUB_IN_{hub.no_basico.coordenadas}"
                
                par_chave = (coz.no_basico, hub.no_basico)
                
                # REAPROVEITAMENTO DA MST: Se já foi calculado pelo Kruskal, usa de graça!
                if par_chave in self.cache_rotas:
                    custo_inicial = self.cache_rotas[par_chave]
                    ja_tem_real = True
                else:
                    # Se não tem, assume a linha reta como estimativa temporária! Zero A* rodados aqui!
                    custo_inicial = RoteadorLogistico.distancia_euclidiana(coz.no_basico, hub.no_basico)
                    ja_tem_real = False
                
                no_coz_out = self._obter_ou_criar_no(id_coz_out)
                no_hub_in = self._obter_ou_criar_no(id_hub_in)
                
                no_coz_out.adicionar_aresta(
                    no_hub_in, capacidade=INF, custo=custo_inicial,
                    no_orig_real=coz.no_basico, no_dest_real=hub.no_basico,
                    possui_custo_real=ja_tem_real
                )

    def _bellman_ford(self, origem: str, destino: str):
        distancias = {no: float('inf') for no in self.grafo}
        distancias[origem] = 0
        pai_aresta = {no: None for no in self.grafo}
        
        for _ in range(len(self.grafo) - 1):
            relaxou = False
            for no_u in self.grafo.values():
                if distancias[no_u.id_nome] == float('inf'): continue
                    
                for aresta in no_u.arestas:
                    if aresta.capacidade_residual > 0:
                        v = aresta.destino
                        
                        # A SUA SACADA DE MESTRE: O A* disparado estritamente SOB DEMANDA
                        if not aresta.possui_custo_real:
                            par_chave = (aresta.no_origem_real, aresta.no_destino_real)
                            
                            # Dupla checagem (pode ter sido calculado por outro ramo nesta mesma execução)
                            if par_chave in self.cache_rotas:
                                custo_real = self.cache_rotas[par_chave]
                            else:
                                # Calcula o A* real pela primeira vez apenas porque o Bellman-Ford bateu na porta!
                                _, custo_real = RoteadorLogistico.buscar_rota_a_estrela(aresta.no_origem_real, aresta.no_destino_real, 1.0)
                                self.cache_rotas[par_chave] = custo_real
                            
                            # Atualiza a aresta definitiva e a sua reversa residual na malha de fluxo
                            aresta.custo = custo_real
                            aresta.reversa.custo = -custo_real
                            aresta.possui_custo_real = True
                            aresta.reversa.possui_custo_real = True
                        
                        novo_custo = distancias[no_u.id_nome] + aresta.custo
                        # CORREÇÃO: Ignora ruídos de precisão de ponto flutuante (1e-7)
                        if novo_custo < distancias[v] - 1e-7:
                            distancias[v] = novo_custo
                            pai_aresta[v] = aresta
                            relaxou = True
            if not relaxou: break
            
        return pai_aresta, distancias[destino]

    def calcular_fluxo_maximo_custo_minimo(self) -> tuple[int, float]:
        """Empurra fluxo pela rede priorizando sempre os caminhos mais baratos"""
        fluxo_maximo = 0
        custo_total = 0.0
        
        while True:
            # 1. Acha o caminho mais barato disponível
            pai_aresta, custo_caminho = self._bellman_ford("SUPER_FONTE", "SUPER_SUMIDOURO")
            
            # Se não há mais caminho até o sumidouro, a rede está no limite absoluto
            if pai_aresta["SUPER_SUMIDOURO"] is None:
                break
                
            # 2. Descobre o "gargalo" (capacidade mínima) deste caminho
            gargalo = float('inf')
            aresta_atual = pai_aresta["SUPER_SUMIDOURO"]
            
            # PROTEÇÃO: Detecção de ciclos para impedir congelamento
            visitados = set() 
            
            while aresta_atual is not None:
                if aresta_atual.origem in visitados:
                    break # Corta o loop infinito instantaneamente!
                visitados.add(aresta_atual.origem)
                
                gargalo = min(gargalo, aresta_atual.capacidade_residual)
                aresta_atual = pai_aresta[aresta_atual.origem]
                
            # Se não achou gargalo válido, a rede saturou
            if gargalo == float('inf') or gargalo == 0:
                break
                
            # 3. Empurra o fluxo pelo caminho e atualiza a rede residual
            aresta_atual = pai_aresta["SUPER_SUMIDOURO"]
            visitados.clear() # Limpa para usar na segunda passada
            
            while aresta_atual is not None:
                if aresta_atual.origem in visitados: 
                    break # Corta o loop infinito
                visitados.add(aresta_atual.origem)
                
                aresta_atual.fluxo += gargalo
                aresta_atual.reversa.fluxo -= gargalo # Devolve na residual!
                custo_total += (gargalo * aresta_atual.custo)
                aresta_atual = pai_aresta[aresta_atual.origem]
                
            fluxo_maximo += gargalo
            
        return fluxo_maximo, custo_total