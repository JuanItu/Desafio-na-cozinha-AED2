# data/load_source.py
# Carrega dados_fonte.json e monta os três vetores do sistema:
#   lista_receitas, lista_ingredientes, lista_categorias
# Também devolve um dicionário id_ingrediente→nome para uso do motor.

import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from modelos.receita      import Receita
from modelos.ingredientes import Ingredientes, QuantidadeIngredientes
from modelos.categoria    import Categoria

_CAMINHO_FONTE  = Path(__file__).parent / "dados_fonte.json"
_CAMINHO_SALVOS = Path(__file__).parent / "dados_salvos.json"


def carregar_dados(caminho: Path = _CAMINHO_FONTE):
    """
    Lê o JSON e constrói os três vetores de objetos.

    Retorna
    -------
    lista_receitas    : list[Receita]
    lista_ingredientes: list[Ingredientes]
    lista_categorias  : list[Categoria]
    mapa_id_ingrediente: dict[int, str]   id → nome  (usado pelo motor)
    """
    with open(caminho, encoding="utf-8") as f:
        dados_json = json.load(f)

    # ── 1. Monta ingredientes únicos ─────────────────────────────────
    nome_para_id_ing: dict[str, int] = {}
    lista_ingredientes: list[Ingredientes] = []

    for receita_json in dados_json:
        for nome_ing in receita_json.get("ingredientes", []):
            if nome_ing not in nome_para_id_ing:
                novo_id = len(lista_ingredientes) + 1
                nome_para_id_ing[nome_ing] = novo_id
                lista_ingredientes.append(
                    Ingredientes(
                        id_ingredientes=novo_id,
                        nome_ingrediente=nome_ing,
                        quantidade_estoque=0,          # não disponível no JSON
                        lista_receitas_ingredientes=[] # preenchido depois
                    )
                )

    mapa_id_ingrediente: dict[int, str] = {
        ing.id_ingredientes: ing.nome_ingrediente
        for ing in lista_ingredientes
    }

    # ── 2. Monta categorias únicas ────────────────────────────────────
    nome_para_cat: dict[str, Categoria] = {}
    lista_categorias: list[Categoria] = []

    for receita_json in dados_json:
        for nome_cat in receita_json.get("categorias", []):
            if nome_cat not in nome_para_cat:
                cat = Categoria(
                    id_categoria=len(lista_categorias) + 1,
                    nome_categoria=nome_cat,
                    lista_categoria_receitas=[]
                )
                nome_para_cat[nome_cat] = cat
                lista_categorias.append(cat)

    # ── 3. Monta receitas ─────────────────────────────────────────────
    lista_receitas: list[Receita] = []

    for receita_json in dados_json:
        # Constrói lista de QuantidadeIngredientes (sem qtd/unidade no JSON)
        lista_qi = [
            QuantidadeIngredientes(
                id_ingredientes=nome_para_id_ing[nome_ing],
                unidade_utilizada="",  # não disponível
                quantidade_necessaria=0
            )
            for nome_ing in receita_json.get("ingredientes", [])
        ]

        receita = Receita(
            id_ingredientes=receita_json["id"],          # id da receita
            nome_receita=receita_json["nome"],
            custo=receita_json["custo_centavos_dolar"],
            tempo_preparo=receita_json["tempo_preparo_minutos"],
            fator_recomendacao=receita_json["popularidade_likes"],
            lista_categoria_receitas=receita_json.get("categorias", []),
            lista_quantidade_ingredientes=lista_qi,
            lista_id_hash_ingredientes=[
                nome_para_id_ing[n] for n in receita_json.get("ingredientes", [])
            ]
        )
        lista_receitas.append(receita)

        # Registra a receita em cada categoria
        for nome_cat in receita_json.get("categorias", []):
            nome_para_cat[nome_cat].lista_categoria_receitas.append(receita)

        # Registra a receita em cada ingrediente
        for nome_ing in receita_json.get("ingredientes", []):
            id_ing = nome_para_id_ing[nome_ing]
            lista_ingredientes[id_ing - 1].lista_receitas_ingredientes.append(receita)

    return lista_receitas, lista_ingredientes, lista_categorias, mapa_id_ingrediente


def salvar_dados(lista_receitas, lista_ingredientes, lista_categorias,
                 mapa_id_ingrediente, caminho: Path = _CAMINHO_SALVOS):
    """Serializa o estado atual para dados_salvos.json."""
    dados = []
    for r in lista_receitas:
        dados.append({
            "id": r.id_ingredientes,
            "nome": r.nome_receita,
            "categorias": r.lista_categoria_receitas,
            "ingredientes": [
                mapa_id_ingrediente[qi.id_ingredientes]
                for qi in r.lista_quantidade_ingredientes
            ],
            "tempo_preparo_minutos": r.tempo_preparo,
            "custo_centavos_dolar": r.custo,
            "popularidade_likes": r.fator_recomendacao,
        })
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)
    print(f"[dados] {len(dados)} receitas salvas em '{caminho}'.")