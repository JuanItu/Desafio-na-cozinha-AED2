# modelos/rede_fluxo.py

class ArestaFluxo:
    __slots__ = ['origem', 'destino', 'capacidade', 'fluxo', 'custo', 'reversa', 
                 'no_origem_real', 'no_destino_real', 'possui_custo_real']

    def __init__(self, origem: str, destino: str, capacidade: int, custo: float,
                 no_origem_real=None, no_destino_real=None, possui_custo_real: bool = True):
        self.origem = origem
        self.destino = destino
        self.capacidade = capacidade
        self.fluxo = 0
        self.custo = custo
        self.reversa: 'ArestaFluxo' = None
        
        # Dados para computação sob demanda (Lazy)
        self.no_origem_real = no_origem_real
        self.no_destino_real = no_destino_real
        self.possui_custo_real = possui_custo_real

    @property
    def capacidade_residual(self) -> int:
        return self.capacidade - self.fluxo


class NoFluxo:
    __slots__ = ['id_nome', 'arestas']

    def __init__(self, id_nome: str):
        self.id_nome = id_nome
        self.arestas: list[ArestaFluxo] = []

    def adicionar_aresta(self, destino: 'NoFluxo', capacidade: int, custo: float,
                         no_orig_real=None, no_dest_real=None, possui_custo_real: bool = True) -> ArestaFluxo:
        """Retorna a aresta de ida criada para controle"""
        aresta_ida = ArestaFluxo(self.id_nome, destino.id_nome, capacidade, custo, no_orig_real, no_dest_real, possui_custo_real)
        aresta_volta = ArestaFluxo(destino.id_nome, self.id_nome, 0, -custo, no_dest_real, no_orig_real, possui_custo_real)
        
        aresta_ida.reversa = aresta_volta
        aresta_volta.reversa = aresta_ida
        
        self.arestas.append(aresta_ida)
        destino.arestas.append(aresta_volta)
        return aresta_ida