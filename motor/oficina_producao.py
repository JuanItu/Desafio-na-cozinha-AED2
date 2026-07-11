# motor/oficina_producao.py
# Módulo 5 — Oficina de Produção
#
# Grafo dirigido de dependências entre preparos: aresta (u -> v) significa
# "u tem v como preparo direto" (u.lista_preparos contém v).
#
# Verificação Geral (roda na inicialização / sob demanda):
#   1. Corte de autodependências (receita que depende de si mesma)
#   2. Tarjan — Componentes Fortemente Conexos (SCCs), O(V + E)
#   3. DFS de pilha restrita a cada SCC problemático -> sugere UM corte
#   4. Se o grafo é um DAG: gera a ordenação topológica de produção
#   5. Varredura linear O(V + E) de coerência de custo / tempo / preço
#
# Verificação de Manutenção (roda ao editar as dependências de uma receita):
#   Reaplica apenas os passos 5.1–5.3 para aquela receita e seus preparos diretos.

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from modelos.receita import Receita


# ══════════════════════════════════════════════════════════════════════
class CorteSugerido:
    """Sugestão de remoção de uma aresta de dependência (origem -> destino),
    gerada pela varredura de autodependências ou pela DFS de pilha nos SCCs."""

    def __init__(self, origem: Receita, destino: Receita, motivo: str):
        self.origem = origem
        self.destino = destino
        self.motivo = motivo

    def aplicar(self) -> None:
        self.origem.remover_preparo(self.destino.nome_receita)
        self.origem.salvar_snapshot(f"Corte de dependência aplicado: {self.motivo}")

    def __repr__(self):
        return f"[Corte] {self.origem.nome_receita} -x-> {self.destino.nome_receita} ({self.motivo})"


class SugestaoAjuste:
    """Sugestão de correção de um atributo numérico (custo, tempo ou preço),
    gerada pela verificação de coerência (seção 5)."""

    TIPOS_LABEL = {
        "custo": "Custo",
        "tempo_paralelo": "Tempo (modelo paralelo)",
        "tempo_serial": "Tempo (modelo serial)",
        "preco": "Preço de venda",
    }

    def __init__(self, receita: Receita, tipo: str, valor_atual, valor_sugerido, motivo: str):
        self.receita = receita
        self.tipo = tipo
        self.valor_atual = valor_atual
        self.valor_sugerido = valor_sugerido
        self.motivo = motivo

    def aplicar(self) -> None:
        if self.tipo == "custo":
            self.receita.atualizar_custo(self.valor_sugerido)
        elif self.tipo in ("tempo_paralelo", "tempo_serial"):
            self.receita.atualizar_tempo(self.valor_sugerido)
        elif self.tipo == "preco":
            self.receita.atualizar_preco(self.valor_sugerido)
        self.receita.salvar_snapshot(f"Ajuste de coerência ({self.TIPOS_LABEL.get(self.tipo, self.tipo)})")

    def __repr__(self):
        label = self.TIPOS_LABEL.get(self.tipo, self.tipo)
        return (f"[Sugestão] {self.receita.nome_receita} • {label}: "
                f"{self.valor_atual} -> {self.valor_sugerido} ({self.motivo})")


# ══════════════════════════════════════════════════════════════════════
class OficinaProducao:

    def __init__(self, lista_receitas: list):
        self.lista_receitas = lista_receitas
        self.lista_cortes_sugeridos: list[CorteSugerido] = []
        self.lista_sugestoes_coerencia: list[SugestaoAjuste] = []
        self.componentes_problematicos: list[list[Receita]] = []
        self.eh_dag: bool = True

    # ── 1. Auto-dependências ────────────────────────────────────────────
    def _verificar_autodependencias(self) -> None:
        for r in self.lista_receitas:
            if r in r.lista_preparos:
                self.lista_cortes_sugeridos.append(
                    CorteSugerido(r, r, "Autodependência (a receita depende de si mesma)")
                )

    # ── 2. Tarjan — SCCs em O(V + E), versão iterativa ──────────────────
    def tarjan_scc(self) -> list:
        indice_atual = [0]
        index_de, lowlink_de, na_pilha = {}, {}, {}
        pilha = []
        sccs = []

        for origem in self.lista_receitas:
            if origem in index_de:
                continue

            index_de[origem] = lowlink_de[origem] = indice_atual[0]
            indice_atual[0] += 1
            pilha.append(origem)
            na_pilha[origem] = True

            # Pilha de simulação de recursão: (nó, iterador de vizinhos)
            pilha_execucao = [(origem, iter(origem.lista_preparos))]

            while pilha_execucao:
                atual, vizinhos = pilha_execucao[-1]
                avancou = False

                for vizinho in vizinhos:
                    if vizinho not in index_de:
                        index_de[vizinho] = lowlink_de[vizinho] = indice_atual[0]
                        indice_atual[0] += 1
                        pilha.append(vizinho)
                        na_pilha[vizinho] = True
                        pilha_execucao.append((vizinho, iter(vizinho.lista_preparos)))
                        avancou = True
                        break
                    elif na_pilha.get(vizinho, False):
                        lowlink_de[atual] = min(lowlink_de[atual], index_de[vizinho])

                if avancou:
                    continue

                pilha_execucao.pop()
                if pilha_execucao:
                    pai, _ = pilha_execucao[-1]
                    lowlink_de[pai] = min(lowlink_de[pai], lowlink_de[atual])

                if lowlink_de[atual] == index_de[atual]:
                    scc = []
                    while True:
                        nodo = pilha.pop()
                        na_pilha[nodo] = False
                        scc.append(nodo)
                        if nodo is atual:
                            break
                    sccs.append(scc)

        return sccs

    # ── 3. DFS de pilha restrita ao SCC, para sugerir UM corte ──────────
    def _dfs_pilha_scc(self, scc: list) -> None:
        membros = set(scc)
        visitados = set()

        def dfs(no, pilha_caminho):
            visitados.add(no)
            pilha_caminho.append(no)

            for vizinho in no.lista_preparos:
                if vizinho not in membros:
                    continue  # navegação restrita ao SCC avaliado
                if vizinho in pilha_caminho:
                    # 'vizinho' já está no caminho -> a aresta (no -> vizinho) fecha o ciclo
                    self.lista_cortes_sugeridos.append(
                        CorteSugerido(no, vizinho, "Ciclo de dependências detectado (SCC)")
                    )
                    return True  # interrompe a busca para este SCC
                if vizinho not in visitados:
                    if dfs(vizinho, pilha_caminho):
                        return True

            pilha_caminho.pop()
            return False

        dfs(scc[0], [])

    # ── 4. Ordenação topológica (só é chamada quando o grafo é DAG) ─────
    def ordenacao_topologica(self) -> list:
        """Pós-ordem de DFS: cada preparo aparece antes de quem depende dele."""
        visitados = set()
        ordem = []

        def dfs(no):
            visitados.add(no)
            for prep in no.lista_preparos:
                if prep not in visitados:
                    dfs(prep)
            ordem.append(no)

        for r in self.lista_receitas:
            if r not in visitados:
                dfs(r)

        return ordem

    # ── 5. Coerência de custo / tempo / preço — O(V + E) ─────────────────
    def _verificar_coerencia_receita(self, receita: Receita) -> list:
        sugestoes = []
        preparos = receita.lista_preparos
        if not preparos:
            return sugestoes

        # 5.1 Coerência de Custo
        custo_minimo = sum(p.custo for p in preparos)
        if receita.custo < custo_minimo:
            sugestoes.append(SugestaoAjuste(
                receita, "custo", receita.custo, round(custo_minimo, 2),
                "Custo abaixo da soma dos preparos diretos"
            ))

        # 5.2 Coerência de Tempo — modelo Paralelo (tempo >= maior preparo)
        tempo_max_dep = max(p.tempo_preparo for p in preparos)
        if receita.tempo_preparo < tempo_max_dep:
            sugestoes.append(SugestaoAjuste(
                receita, "tempo_paralelo", receita.tempo_preparo, tempo_max_dep,
                "Tempo menor que o maior preparo direto"
            ))

        # 5.2 Coerência de Tempo — modelo Serial (tempo >= soma dos preparos)
        tempo_soma_dep = sum(p.tempo_preparo for p in preparos)
        if receita.tempo_preparo < tempo_soma_dep:
            sugestoes.append(SugestaoAjuste(
                receita, "tempo_serial", receita.tempo_preparo, tempo_soma_dep,
                "Tempo menor que a soma de todos os preparos diretos"
            ))

        # 5.3 Coerência de Preço (só se a receita está à venda, preco != 0)
        if receita.preco != 0 and receita.preco < receita.custo:
            sugestoes.append(SugestaoAjuste(
                receita, "preco", receita.preco, round(receita.custo * 1.2, 2),
                "Preço de venda abaixo do custo (sem margem de lucro)"
            ))

        return sugestoes

    def _verificar_coerencia(self, receitas: list) -> list:
        sugestoes = []
        for r in receitas:
            sugestoes.extend(self._verificar_coerencia_receita(r))
        return sugestoes

    def verificacao_manutencao(self, receita: Receita) -> list:
        """Verificação de Manutenção: chamada ao editar as dependências de UMA receita.
        Reaplica apenas a checagem de coerência (5.1-5.3) para ela e seus preparos diretos."""
        sugestoes = self._verificar_coerencia_receita(receita)
        self.lista_sugestoes_coerencia = sugestoes
        return sugestoes

    # ── Verificação Geral — orquestra os passos 1 a 5 ────────────────────
    def verificacao_geral(self) -> dict:
        self.lista_cortes_sugeridos.clear()
        self.lista_sugestoes_coerencia.clear()
        self.componentes_problematicos.clear()

        self._verificar_autodependencias()

        sccs = self.tarjan_scc()
        self.componentes_problematicos = [scc for scc in sccs if len(scc) >= 2]
        for scc in self.componentes_problematicos:
            self._dfs_pilha_scc(scc)

        tem_autodependencia = any(
            corte.origem is corte.destino for corte in self.lista_cortes_sugeridos
        )
        self.eh_dag = (not self.componentes_problematicos) and (not tem_autodependencia)

        if self.eh_dag:
            self.lista_sugestoes_coerencia = self._verificar_coerencia(self.lista_receitas)

        return {
            "eh_dag": self.eh_dag,
            "cortes_sugeridos": list(self.lista_cortes_sugeridos),
            "ordem_producao": self.ordenacao_topologica() if self.eh_dag else None,
            "sugestoes_coerencia": list(self.lista_sugestoes_coerencia),
        }

    # ── Aplicação de cortes (3 modos descritos na seção 4) ───────────────
    def aplicar_corte(self, corte: CorteSugerido) -> None:
        corte.aplicar()
        if corte in self.lista_cortes_sugeridos:
            self.lista_cortes_sugeridos.remove(corte)

    def aplicar_todos_cortes(self) -> None:
        for corte in list(self.lista_cortes_sugeridos):
            self.aplicar_corte(corte)

    # ── Aplicação de sugestões de coerência (3 modos da seção 5.4) ───────
    def aplicar_sugestao(self, sugestao: SugestaoAjuste) -> None:
        sugestao.aplicar()
        if sugestao in self.lista_sugestoes_coerencia:
            self.lista_sugestoes_coerencia.remove(sugestao)

    def aplicar_todas_sugestoes(self) -> None:
        for sugestao in list(self.lista_sugestoes_coerencia):
            self.aplicar_sugestao(sugestao)

    # ── Consultas (mínimo de duas exigidas pelo enunciado) ───────────────
    def existe_erro_dependencia(self) -> bool:
        """'Existe algum erro de dependência?'"""
        return not self.eh_dag

    def sequencia_producao(self):
        """'Qual a sequência correta para produzir o menu do dia?'
        Retorna None se ainda houver ciclos/autodependências não resolvidos."""
        return self.ordenacao_topologica() if self.eh_dag else None

    def preparos_necessarios_antes_de(self, receita: Receita) -> list:
        """'Quais preparos precisam ser concluídos antes da receita X?'
        Retorna todos os preparos diretos e transitivos, via BFS."""
        visitados = set()
        fila = list(receita.lista_preparos)
        resultado = []
        while fila:
            atual = fila.pop(0)
            if atual in visitados:
                continue
            visitados.add(atual)
            resultado.append(atual)
            fila.extend(atual.lista_preparos)
        return resultado
