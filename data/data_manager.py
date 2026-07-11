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
from modelos.menu         import Menu

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
    pendentes_preparos = []  # [(receita, [nomes_dos_preparos])] -> ligado após criar todas as receitas

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
                fator_recomendacao=r_json["popularidade_likes"],
                preco=r_json.get("preco_venda", 0.0)
            )
        except ValueError:
            continue

        if r_json.get("preparos"):
            pendentes_preparos.append((receita, r_json["preparos"]))

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

    # --- LIGAÇÃO DAS DEPENDÊNCIAS (PREPAROS) — 2ª passada ---
    # Precisa ser feita depois que TODAS as receitas existem, pois um preparo
    # pode estar cadastrado mais adiante na lista do JSON.
    for receita, nomes_preparos in pendentes_preparos:
        for nome_prep in nomes_preparos:
            preparo_obj = Receita.registro_global.get(nome_prep.lower()) \
                or Receita.registro_excluidas.get(nome_prep.lower())
            if preparo_obj is not None:
                receita.adicionar_preparo(preparo_obj)
                
    if isinstance(dados_json, dict) and "menus" in dados_json:
        Menu.registro_global.clear()  # Limpa o banco em memória para evitar duplicações
        
        for m_json in dados_json["menus"]:
            novo_menu = Menu(m_json["nome_menu"])
            dict_pratos_objs = {}
            
            # Reconecta as strings (nomes) de volta aos objetos Receita em memória
            for cat_nome, nomes_receitas in m_json.get("pratos_por_categoria", {}).items():
                dict_pratos_objs[cat_nome] = []
                for nome_rec in nomes_receitas:
                    rec_obj = Receita.registro_global.get(nome_rec.lower())
                    if rec_obj:
                        dict_pratos_objs[cat_nome].append(rec_obj)
                        
            # O próprio Menu calcula as estatísticas sozinho ao definir os pratos
            novo_menu.definir_pratos(dict_pratos_objs)

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
        
        nomes_preparos = [p.nome_receita for p in r.lista_preparos]

        dados_receitas.append({
            "nome": r.nome_receita,
            "categorias": nomes_cats,
            "ingredientes": dados_ings,
            "tempo_preparo_minutos": r.tempo_preparo,
            "custo_centavos_dolar": r.custo,
            "popularidade_likes": r.fator_recomendacao,
            "preco_venda": r.preco,
            "preparos": nomes_preparos,
            "historico_estados": r.historico_estados,
            "ultima_atualizacao": r.ultima_atualizacao.isoformat(),
            "data_exclusao": r.data_exclusao.isoformat() if r.data_exclusao else None,
            "excluida": r.data_exclusao is not None
        })
        
    # --- SALVA O ESTOQUE GLOBAL ---
    dados_estoque = []
    for ing in Ingredientes.registro_global.values():
        dados_estoque.append({
            "nome": ing.nome_ingrediente,
            "quantidade": ing.quantidade_estoque,
            "unidade": ing.unidade_estoque
        })
        
    dados_menus = []
    for menu in Menu.registro_global.values():
        # Converte a lista de objetos Receita para uma lista de Nomes (Strings)
        pratos_nomes = {}
        for cat, lista_recs in menu.pratos_por_categoria.items():
            pratos_nomes[cat] = [r.nome_receita for r in lista_recs]
        
        dados_menus.append({
            "nome_menu": menu.nome_menu,
            "pratos_por_categoria": pratos_nomes
        })
        
    # Empacota as três gavetas
    dados_completos = {
        "receitas": dados_receitas,
        "estoque_ingredientes": dados_estoque,
        "menus": dados_menus # <-- ADICIONAR OS MENUS AQUI
    }
    
    with open(_CAMINHO_SALVOS, "w", encoding="utf-8") as f:
        json.dump(dados_completos, f, indent=4, ensure_ascii=False)
        
    print(f"\n  ✓ {len(dados_receitas)} receitas e {len(dados_estoque)} estoques de ingredientes salvos com sucesso!")