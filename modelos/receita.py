class Receita:
    def __init__(self, id_ingredientes, nome_receita, custo, tempo_preparo, fator_recomendacao, lista_categoria_receitas, lista_quantidade_ingredientes, lista_id_hash_ingredientes):
        self.id_ingredientes = id_ingredientes
        self.nome_receita = nome_receita
        self.custo = custo
        self.tempo_preparo = tempo_preparo
        self.fator_recomendacao = fator_recomendacao
        self.lista_categoria_receitas = lista_categoria_receitas
        self.lista_quantidade_ingredientes = lista_quantidade_ingredientes
        self.lista_id_hash_ingredientes = lista_id_hash_ingredientes