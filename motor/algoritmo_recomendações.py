# motor/algoritmo_recomendações.py
# Algoritmo guloso de recomendação de receitas

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from modelos.receita import Receita


# ══════════════════════════════════════════════════════════════════════
class AlgoritmoRecomendacao:
    """
    Mantém um vetor de referências a objetos Receita ordenado por
    fator_recomendacao (decrescente).

    flag_reordenar é levantado sempre que uma receita é
    adicionada/removida ou quando o main notifica uma alteração de fator.
    """

    def __init__(self):
        # Não precisamos mais do mapa_id_ingrediente! Tudo funciona por referência.
        self.lista_recomendacao: list[Receita] = []
        self.flag_reordenar: bool = False

    # ── Gerenciamento do vetor ─────────────────────────────────────────

    def adicionar_receita(self, receita: Receita) -> None:
        """Adiciona referência à receita e levanta o flag."""
        self.lista_recomendacao.append(receita)
        self.flag_reordenar = True

    def remover_receita(self, receita: Receita) -> None:
        """Remove referência à receita e levanta o flag."""
        try:
            self.lista_recomendacao.remove(receita)
            self.flag_reordenar = True
        except ValueError:
            pass

    def notificar_atualizacao(self) -> None:
        """Chamado pelo main.py quando a flag 'recomendacao_desatualizada' da receita disparar."""
        self.flag_reordenar = True

    def _reordenar_se_necessario(self) -> None:
        """Ordena por fator_recomendacao desc apenas se flag estiver ativo."""
        if self.flag_reordenar:
            self.lista_recomendacao.sort(
                key=lambda r: r.fator_recomendacao,
                reverse=True
            )
            self.flag_reordenar = False

    # ── Helpers internos ───────────────────────────────────────────────

    def _nomes_ingredientes(self, receita: Receita) -> set[str]:
        """Retorna set de nomes (lowercase) dos objetos ingrediente da receita."""
        return {
            qi.ingrediente.nome_ingrediente.lower()
            for qi in receita.lista_quantidade_ingredientes
        }

    # ── Filtros (True = receita PASSA no critério) ─────────────────────

    def _ok_tempo(self, receita: Receita, tempo_maximo) -> bool:
        if tempo_maximo is None:
            return True
        return receita.tempo_preparo <= int(tempo_maximo)

    def _ok_custo(self, receita: Receita, custo_maximo) -> bool:
        if custo_maximo is None:
            return True
        return receita.custo <= int(custo_maximo)

    def _ok_ing_proibido(self, receita: Receita, proibidos: list) -> bool:
        if not proibidos:
            return True
        nomes = self._nomes_ingredientes(receita)
        return all(p.lower() not in nomes for p in proibidos)

    def _ok_ing_exigido(self, receita: Receita, exigidos: list) -> bool:
        if not exigidos:
            return True
        nomes = self._nomes_ingredientes(receita)
        return all(e.lower() in nomes for e in exigidos)

    def _ok_categoria_exigida(self, receita: Receita, categorias: list) -> bool:
        if not categorias:
            return True
        # Agora lemos o nome_categoria do objeto Categoria diretamente
        cats_receita = {c.nome_categoria.lower() for c in receita.lista_categoria_receitas}
        return all(c.lower() in cats_receita for c in categorias)

    # ── Algoritmo guloso principal ─────────────────────────────────────

    def recomendar(
        self,
        quantidade: int = 1,
        tempo_maximo=None,
        custo_maximo=None,
        ingredientes_proibidos: list | None = None,
        ingredientes_exigidos:  list | None = None,
        categorias_exigidas:    list | None = None,
    ) -> list[Receita]:
        
        proibidos = ingredientes_proibidos or []
        exigidos  = ingredientes_exigidos  or []
        categorias = categorias_exigidas   or []

        none_guloso = (
            tempo_maximo is None
            and custo_maximo is None
            and not proibidos
            and not exigidos
            and not categorias
        )

        self._reordenar_se_necessario()
        recomendadas: list[Receita] = []

        for receita in self.lista_recomendacao:
            if none_guloso:
                recomendadas.append(receita)
            else:
                if not self._ok_tempo(receita, tempo_maximo): continue
                if not self._ok_custo(receita, custo_maximo): continue
                if not self._ok_ing_proibido(receita, proibidos): continue
                if not self._ok_ing_exigido(receita, exigidos): continue
                if not self._ok_categoria_exigida(receita, categorias): continue

                recomendadas.append(receita)

            if len(recomendadas) == quantidade:
                break

        return recomendadas

    # ── Exibição ───────────────────────────────────────────────────────

    def exibir_lista(self, limite: int = 20) -> None:
        self._reordenar_se_necessario()
        total = len(self.lista_recomendacao)
        print(f"\n{'#':<5} {'Nome':<42} {'Fator':>6} {'Custo(¢$)':>10} {'Tempo':>7}")
        print("─" * 74)
        for i, r in enumerate(self.lista_recomendacao[:limite], 1):
            print(
                f"{i:<5} {r.nome_receita[:41]:<42} "
                f"{r.fator_recomendacao:>6} "
                f"{r.custo:>10.2f} "
                f"{r.tempo_preparo:>5}min"
            )
        if total > limite:
            print(f"  ... ({total - limite} receitas omitidas)")
        print(f"  Total: {total} receitas | flag_reordenar={self.flag_reordenar}\n")

    def exibir_recomendacao(self, receitas: list[Receita]) -> None:
        if not receitas:
            print("  ✗ Nenhuma receita encontrada para os parâmetros informados.\n")
            return
        for i, r in enumerate(receitas, 1):
            # Agora extraímos os nomes diretamente dos objetos nas listas
            ingredientes = [qi.ingrediente.nome_ingrediente for qi in r.lista_quantidade_ingredientes]
            categorias = [c.nome_categoria for c in r.lista_categoria_receitas]
            
            print(f"  [{i}] {r.nome_receita}")
            print(f"      Fator: {r.fator_recomendacao} | "
                  f"Custo: {r.custo:.0f}¢$ | "
                  f"Tempo: {r.tempo_preparo}min")
            print(f"      Categorias: {', '.join(categorias)}")
            print(f"      Ingredientes: {', '.join(ingredientes)}\n")