# motor/busca_id.py  —  Tabela Hash com Redimensionamento Dinâmico
#
# Desafio A: Tabela Hash + Análise Amortizada
# ─────────────────────────────────────────────────────────────────────────────
# Como o projeto não usa mais IDs numéricos, a "busca por id" vira uma
# busca por nome exato via Tabela Hash.
#
# Vantagem sobre a Trie: O(1) amortizado para inserção e busca.
# Limitação: NÃO captura prefixos — retorna apenas com matching exato.
#
# Redimensionamento dinâmico:
#   - Fator de carga máximo: 0.7 (estrito)
#   - Ao ultrapassar: dobra o tamanho e assume o próximo número primo
#   - Rehashing completo de todas as chaves existentes
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _RAIZ not in sys.path:
    sys.path.append(_RAIZ)

sys.stdout.reconfigure(encoding='utf-8')

from modelos.receita import Receita
from modelos.ingredientes import Ingredientes
from modelos.categoria import Categoria


# ──────────────────────────────────────────────
# Utilitário: próximo número primo >= n
# ──────────────────────────────────────────────

def _proximo_primo(n: int) -> int:
    """Retorna o menor número primo >= n."""
    if n < 2:
        return 2
    candidato = n if n % 2 != 0 else n + 1
    while True:
        eh_primo = all(candidato % d != 0 for d in range(3, int(candidato**0.5) + 1, 2))
        if eh_primo:
            return candidato
        candidato += 2


# ──────────────────────────────────────────────
# Slot da Tabela Hash (encadeamento separado)
# ──────────────────────────────────────────────

class _Slot:
    """Um nó da lista encadeada dentro de cada bucket. Guarda múltiplos objetos se compartilharem o mesmo nome exato."""
    __slots__ = ['chave', 'objetos', 'proximo']

    def __init__(self, chave: str, objeto, proximo=None):
        self.chave = chave
        self.objetos = [objeto]
        self.proximo = proximo


# ──────────────────────────────────────────────
# Tabela Hash Principal
# ──────────────────────────────────────────────

class TabelaHashNomes:
    """
    Tabela Hash de nome -> objeto (Receita | Ingredientes | Categoria).

    Resolucao de colisoes: encadeamento separado (listas ligadas por bucket).
    Redimensionamento: automatico quando fator_de_carga > FATOR_MAXIMO (0.7).
    Tamanho apos rehash: proximo primo >= 2 * tamanho_atual.
    """

    FATOR_MAXIMO = 0.7
    TAMANHO_INICIAL = 11  # Primo pequeno para inicio

    def __init__(self, tamanho_inicial: int = None):
        self._capacidade = _proximo_primo(tamanho_inicial or self.TAMANHO_INICIAL)
        self._buckets: list = [None] * self._capacidade
        self._total = 0          # elementos inseridos
        self._colisoes = 0       # colisoes acumuladas (para diagnostico)
        self._rehashes = 0       # quantas vezes redimensionou

    # ── Funcao Hash ──────────────────────────────

    def _hash(self, chave: str) -> int:
        """
        Polinomial rolling hash com base 31 e modulo primo.
        Chave e sempre lowercased antes de entrar aqui.
        """
        h = 0
        base = 31
        for ch in chave:
            h = (h * base + ord(ch)) % self._capacidade
        return h

    # ── Insercao ─────────────────────────────────

    def inserir(self, nome: str, objeto) -> None:
        chave = nome.lower()
        idx = self._hash(chave)

        # Verifica se ja existe
        no = self._buckets[idx]
        while no:
            if no.chave == chave:
                # Se a chave existe, apenas adiciona o objeto à lista (se já não estiver lá)
                if objeto not in no.objetos:
                    no.objetos.append(objeto)
                return
            no = no.proximo

        # Colisao: bucket ja tinha algo?
        if self._buckets[idx] is not None:
            self._colisoes += 1

        # Encadeamento: novo no na frente do bucket
        self._buckets[idx] = _Slot(chave, objeto, self._buckets[idx])
        self._total += 1

        # Gatilho de redimensionamento
        if self.fator_de_carga > self.FATOR_MAXIMO:
            self._redimensionar()

    # ── Busca ────────────────────────────────────

    def buscar(self, nome: str) -> list:
        """Retorna uma LISTA de objetos que compartilham este nome (receita, categoria e/ou ingrediente), ou [] se não achar."""
        chave = nome.lower()
        idx = self._hash(chave)
        no = self._buckets[idx]
        while no:
            if no.chave == chave:
                return no.objetos
            no = no.proximo
        return []

    # ── Remocao ──────────────────────────────────

    def remover(self, nome: str, objeto) -> bool:
        """Remove o objeto específico da lista do Slot. Retorna True se removeu, False se nao achou."""
        chave = nome.lower()
        idx = self._hash(chave)
        anterior = None
        no = self._buckets[idx]

        while no:
            if no.chave == chave:
                if objeto in no.objetos:
                    no.objetos.remove(objeto)
                
                # Se a lista esvaziou, deletamos o Slot inteiro da Tabela Hash
                if not no.objetos:
                    if anterior:
                        anterior.proximo = no.proximo
                    else:
                        self._buckets[idx] = no.proximo
                    self._total -= 1
                return True
            anterior = no
            no = no.proximo
        return False

    # ── Redimensionamento ────────────────────────

    def _redimensionar(self) -> None:
        """
        Dobra o tamanho (+ proximo primo) e refaz o hash de todos os elementos.
        Custo: O(n) — amortizado O(1) por insercao ao longo do tempo.
        """
        nova_capacidade = _proximo_primo(self._capacidade * 2)
        novos_buckets = [None] * nova_capacidade
        colisoes_novas = 0

        # Reinserir tudo na nova tabela
        for bucket in self._buckets:
            no = bucket
            while no:
                proximo = no.proximo
                # Recalcula hash com nova capacidade
                h = 0
                for ch in no.chave:
                    h = (h * 31 + ord(ch)) % nova_capacidade

                if novos_buckets[h] is not None:
                    colisoes_novas += 1
                no.proximo = novos_buckets[h]
                novos_buckets[h] = no
                no = proximo

        self._capacidade = nova_capacidade
        self._buckets = novos_buckets
        self._colisoes = colisoes_novas  # reseta para refletir estado real pos-rehash
        self._rehashes += 1

    # ── Diagnostico ──────────────────────────────

    @property
    def fator_de_carga(self) -> float:
        return self._total / self._capacidade if self._capacidade else 0.0

    def diagnostico(self, titulo: str = "DIAGNOSTICO DA TABELA HASH") -> None:
        """
        Exibe no terminal o estado fisico completo da tabela.
        Mostra: capacidade, elementos, fator de carga, colisoes e indices ocupados.
        """
        print(f"\n{'=' * 60}")
        print(f"  {titulo}")
        print(f"{'=' * 60}")
        print(f"  Capacidade (buckets) : {self._capacidade}")
        print(f"  Elementos inseridos  : {self._total}")
        print(f"  Fator de carga       : {self.fator_de_carga:.4f}  (limite: {self.FATOR_MAXIMO})")
        print(f"  Colisoes acumuladas  : {self._colisoes}")
        print(f"  Rehashes realizados  : {self._rehashes}")
        print(f"{'-' * 60}")

        # Mapa visual dos buckets (mostra os 30 primeiros para nao poluir)
        limite_exibicao = min(self._capacidade, 30)
        print(f"  Mapa dos primeiros {limite_exibicao} buckets:")
        for i in range(limite_exibicao):
            no = self._buckets[i]
            if no is None:
                estado = "[ vazio ]"
            else:
                nomes = []
                while no:
                    nomes.append(f'"{no.chave}"')
                    no = no.proximo
                colisao_marker = " <- COLISAO" if len(nomes) > 1 else ""
                estado = " -> ".join(nomes) + colisao_marker
            print(f"    [{i:3d}] {estado}")

        if self._capacidade > limite_exibicao:
            print(f"    ... (e mais {self._capacidade - limite_exibicao} buckets)")
        print(f"{'=' * 60}\n")

    def __len__(self) -> int:
        return self._total

    def __contains__(self, nome: str) -> bool:
        return self.buscar(nome) is not None


# ──────────────────────────────────────────────
# Construtor Rapido
# ──────────────────────────────────────────────

def construir_tabela_hash(lista_receitas, lista_ingredientes, lista_categorias) -> TabelaHashNomes:
    """
    Cria e popula uma TabelaHashNomes com todos os objetos do sistema.
    Usado na inicializacao do main.py.
    """
    tabela = TabelaHashNomes()
    for r in lista_receitas:
        tabela.inserir(r.nome_receita, r)
    for i in lista_ingredientes:
        tabela.inserir(i.nome_ingrediente, i)
    for c in lista_categorias:
        tabela.inserir(c.nome_categoria, c)
    return tabela


# ──────────────────────────────────────────────
# Teste Standalone
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== DEMO: Redimensionamento Dinamico ===\n")

    tabela = TabelaHashNomes(tamanho_inicial=7)  # Comeca pequena pra forcar rehash rapido

    nomes_teste = [
        ("Bolo de Chocolate", "receita"),
        ("Farinha de Trigo", "ingrediente"),
        ("Sobremesas", "categoria"),
        ("Torta de Limao", "receita"),
        ("Acucar Refinado", "ingrediente"),
        ("Salgados", "categoria"),
        ("Lasanha Bolonhesa", "receita"),
    ]

    print("-- ANTES do carregamento em lote --")
    tabela.diagnostico("ESTADO INICIAL")

    print("Inserindo elementos...")
    for nome, tipo in nomes_teste:
        tabela.inserir(nome, f"<objeto_{tipo}:{nome}>")
        print(f"  + '{nome}' | fator={tabela.fator_de_carga:.3f} | capacidade={tabela._capacidade}")

    print("\n-- DEPOIS do carregamento em lote --")
    tabela.diagnostico("ESTADO FINAL")

    print("-- Testes de busca --")
    for nome, _ in nomes_teste[:3]:
        resultado = tabela.buscar(nome)
        print(f"  buscar('{nome}') -> {resultado}")

    print(f"\n  buscar('inexistente') -> {tabela.buscar('inexistente')}")
    print(f"  'bolo de chocolate' in tabela -> {'bolo de chocolate' in tabela}")