# modelos/logistica.py

# ══════════════════════════════════════════════════════════════════════
# 1. ARESTA VIÁRIA (A rua física que conecta dois pontos)
# ══════════════════════════════════════════════════════════════════════
class ArestaViaria:
    __slots__ = ['destino', 'peso']

    def __init__(self, destino: 'NoLogistico', peso: float):
        self.destino = destino  # Referência direta em memória para o nó de destino
        self.peso = peso        # Tempo de viagem ou distância real da via

    def __repr__(self):
        return f"-({self.peso})-> ({self.destino.x}, {self.destino.y})"


# ══════════════════════════════════════════════════════════════════════
# 2. NÓ LOGÍSTICO BÁSICO (A entidade geométrica pura - Spatial Hashing)
# ══════════════════════════════════════════════════════════════════════
class NoLogistico:
    __slots__ = ['x', 'y', 'adjacencias']

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.adjacencias: list[ArestaViaria] = [] # Lista de adjacências clássica

    @property
    def coordenadas(self) -> tuple[float, float]:
        return (self.x, self.y)

    def adicionar_via(self, destino: 'NoLogistico', peso: float):
        self.adjacencias.append(ArestaViaria(destino, peso))

    def __repr__(self):
        return f"NoLogistico({self.x}, {self.y}) [Vias: {len(self.adjacencias)}]"


# ══════════════════════════════════════════════════════════════════════
# 3. GERENCIADORES E COMPONENTES CENTRALIZADOS (A sua ideia de Hash Central)
# ══════════════════════════════════════════════════════════════════════

class CozinhaRegisto:
    """Controle Central de todas as Cozinhas do sistema"""
    banco: dict[tuple[float, float], 'CozinhaRegisto'] = {}

    def __init__(self, no_basico: NoLogistico, capacidade_pratos_hora: int):
        self.no_basico = no_basico
        self.capacidade_pratos_hora = capacidade_pratos_hora
        # Associa as coordenadas do nó básico com as informações da Cozinha
        CozinhaRegisto.banco[no_basico.coordenadas] = self


class PontoRetiradaRegisto:
    """Controle Central de todas as Estações de Distribuição / Hubs"""
    banco: dict[tuple[float, float], 'PontoRetiradaRegisto'] = {}

    def __init__(self, no_basico: NoLogistico, capacidade_entregadores: int):
        self.no_basico = no_basico
        self.capacidade_entregadores = capacidade_entregadores
        # Associa as coordenadas do nó básico com as informações do Hub
        PontoRetiradaRegisto.banco[no_basico.coordenadas] = self


class ClienteRegisto:
    """Controle Central dos Clientes ativos no Delivery"""
    banco: dict[tuple[float, float], 'ClienteRegisto'] = {}

    def __init__(self, no_basico: NoLogistico, nome_cliente: str, pedido_pendente: bool = False):
        self.no_basico = no_basico
        self.nome_cliente = nome_cliente
        self.pedido_pendente = pedido_pendente
        ClienteRegisto.banco[no_basico.coordenadas] = self