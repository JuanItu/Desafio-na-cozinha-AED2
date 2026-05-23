# data/load_source.py

import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from modelos.receita      import Receita
from modelos.ingredientes import Ingredientes
from modelos.categoria    import Categoria

_CAMINHO_FONTE  = Path(__file__).parent / "dados_fonte.json"
_CAMINHO_SALVOS = Path(__file__).parent / "dados_salvos.json"


def carregar_dados(caminho: Path = _CAMINHO_FONTE):
    """
    Lê o JSON e constrói as instâncias. 
    Graças ao Registro Global das classes, não precisamos mais gerenciar IDs!
    """
    with open(caminho, encoding="utf-8") as f:
        dados_json = json.load(f)

    lista_receitas = []

    for r_json in dados_json:
        # 1. Tenta criar a receita (se o nome já existir, ele pula)
        try:
            receita = Receita(
                nome_receita=r_json["nome"],
                custo=r_json["custo_centavos_dolar"],
                tempo_preparo=r_json["tempo_preparo_minutos"],
                fator_recomendacao=r_json["popularidade_likes"]
            )
        except ValueError:
            continue # Ignora duplicatas

        # 2. Registra categorias (A própria classe verifica se já existe e cria se não)
        for nome_cat in r_json.get("categorias", []):
            receita.adicionar_categoria(nome_cat)

        # 3. Registra ingredientes 
        # (O JSON fonte não possui quantidades, então usamos valores genéricos)
        for nome_ing in r_json.get("ingredientes", []):
            receita.adicionar_ingrediente(nome_ing, unidade="und", quantidade=1)

        lista_receitas.append(receita)

    # 4. Coletamos as listas de categorias e ingredientes criados "magicamente" 
    # nos registros globais de cada classe!
    lista_categorias = list(Categoria.registro_global.values())
    lista_ingredientes = list(Ingredientes.registro_global.values())

    # Retornamos {} no final apenas para não quebrar o desempacotamento de 4 variáveis do main.py
    return lista_receitas, lista_ingredientes, lista_categorias, {}


def salvar_dados(lista_receitas, lista_ingredientes, lista_categorias,
                 mapa_id_ingrediente=None, caminho: Path = _CAMINHO_SALVOS):
    """
    Serializa o estado atual para dados_salvos.json extraindo os nomes 
    direto dos objetos nas listas (sem usar IDs).
    """
    dados = []
    
    for r in lista_receitas:
        # Extrai os nomes dos objetos Categoria para uma lista de strings
        nomes_cats = [cat.nome_categoria for cat in r.lista_categoria_receitas]
        
        # Extrai os nomes dos objetos Ingrediente dentro das Quantidades
        nomes_ings = [qi.ingrediente.nome_ingrediente for qi in r.lista_quantidade_ingredientes]
        
        dados.append({
            "versao_hash": r.historico_versoes_hash[-1] if hasattr(r, 'historico_versoes_hash') else "1.0",
            "nome": r.nome_receita,
            "categorias": nomes_cats,
            "ingredientes": nomes_ings,
            "tempo_preparo_minutos": r.tempo_preparo,
            "custo_centavos_dolar": r.custo,
            "popularidade_likes": r.fator_recomendacao,
        })
        
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)
        
    print(f"[dados] {len(dados)} receitas salvas em '{caminho}'.")