import json
import sys
from pathlib import Path
from datetime import datetime

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from modelos.receita      import Receita
from modelos.ingredientes import Ingredientes
from modelos.categoria    import Categoria

_CAMINHO_FONTE  = Path(__file__).parent / "dados_fonte.json"
_CAMINHO_SALVOS = Path(__file__).parent / "dados_salvos.json"

def carregar_dados(usar_salvos: bool = False):
    if usar_salvos and _CAMINHO_SALVOS.exists():
        caminho_usado, print_msg = _CAMINHO_SALVOS, "  -> Lendo do arquivo de dados salvos..."
    else:
        caminho_usado, print_msg = _CAMINHO_FONTE, "  -> Lendo da base de fábrica original..."
    print(print_msg)

    with open(caminho_usado, encoding="utf-8") as f:
        dados_json = json.load(f)

    lista_receitas = []

    # --- SUPORTE AOS DOIS FORMATOS DE JSON ---
    if isinstance(dados_json, dict) and "receitas" in dados_json:
        # Novo formato: Dicionário. Carregamos o estoque global primeiro!
        lista_r_json = dados_json["receitas"]
        for ing_data in dados_json.get("estoque_ingredientes", []):
            ing = Ingredientes.get_ou_criar(ing_data["nome"])
            ing.quantidade_estoque = ing_data.get("quantidade", 0.0)
            ing.unidade_estoque = ing_data.get("unidade", "und")
    else:
        # Formato antigo: Lista pura (ex: dados_fonte.json)
        lista_r_json = dados_json

    # O resto continua exatamente igual para as receitas
    for r_json in lista_r_json:
        try:
            receita = Receita(
                nome_receita=r_json["nome"],
                custo=r_json["custo_centavos_dolar"],
                tempo_preparo=r_json["tempo_preparo_minutos"],
                fator_recomendacao=r_json["popularidade_likes"]
            )
        except ValueError:
            continue
            
        if "historico_estados" in r_json:
            receita.historico_estados = r_json["historico_estados"]
        if "ultima_atualizacao" in r_json:
            receita.ultima_atualizacao = datetime.fromisoformat(r_json["ultima_atualizacao"])

        for nome_cat in r_json.get("categorias", []):
            receita.adicionar_categoria(nome_cat)

        for ing_data in r_json.get("ingredientes", []):
            if isinstance(ing_data, dict):
                receita.adicionar_ingrediente(ing_data["nome"], ing_data.get("unidade", "und"), ing_data.get("quantidade", 1))
            else:
                receita.adicionar_ingrediente(ing_data, unidade="und", quantidade=1)

        if not receita.historico_estados:
            receita.salvar_snapshot("Criação da Receita (Original)")

        if r_json.get("excluida", False):
            receita.data_exclusao = datetime.fromisoformat(r_json["data_exclusao"]) if r_json.get("data_exclusao") else datetime.now()
            nome_key = receita.nome_receita.lower()
            if nome_key in Receita.registro_global:
                del Receita.registro_global[nome_key]
            Receita.registro_excluidas[nome_key] = receita
        else:
            lista_receitas.append(receita)

    lista_categorias = list(Categoria.registro_global.values())
    lista_ingredientes = list(Ingredientes.registro_global.values())

    return lista_receitas, lista_ingredientes, lista_categorias, {}


def salvar_dados(lista_receitas, lista_ingredientes, lista_categorias, mapa_id_ingrediente=None, caminho: Path = _CAMINHO_SALVOS):
    dados_receitas = []
    todas_as_receitas = list(lista_receitas) + list(Receita.registro_excluidas.values())
    
    for r in todas_as_receitas:
        nomes_cats = [cat.nome_categoria for cat in r.lista_categoria_receitas]
        dados_ings = [
            {
                "nome": qi.ingrediente.nome_ingrediente,
                "quantidade": qi.quantidade_necessaria,
                "unidade": qi.unidade_utilizada
            } 
            for qi in r.lista_quantidade_ingredientes
        ]
        
        dados_receitas.append({
            "nome": r.nome_receita,
            "categorias": nomes_cats,
            "ingredientes": dados_ings,
            "tempo_preparo_minutos": r.tempo_preparo,
            "custo_centavos_dolar": r.custo,
            "popularidade_likes": r.fator_recomendacao,
            "historico_estados": r.historico_estados,
            "ultima_atualizacao": r.ultima_atualizacao.isoformat(),
            "data_exclusao": r.data_exclusao.isoformat() if r.data_exclusao else None,
            "excluida": r.data_exclusao is not None
        })
        
    # --- NOVO: SALVA O ESTOQUE GLOBAL ---
    dados_estoque = []
    for ing in Ingredientes.registro_global.values():
        dados_estoque.append({
            "nome": ing.nome_ingrediente,
            "quantidade": ing.quantidade_estoque,
            "unidade": ing.unidade_estoque
        })
        
    # Empacota as duas gavetas
    dados_completos = {
        "receitas": dados_receitas,
        "estoque_ingredientes": dados_estoque
    }
        
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados_completos, f, ensure_ascii=False, indent=4)
        
    print(f"\n  ✓ {len(dados_receitas)} receitas e {len(dados_estoque)} estoques de ingredientes salvos com sucesso!")