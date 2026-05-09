class Receita:
    def __init__(self, id_ingredientes, nome_receita, custo, tempo_preparo, fator_recomendacao,nivel_dificuldade, lista_categoria_receitas, lista_quantidade_ingredientes):
        self.id_ingredientes = id_ingredientes
        self.nome_receita = nome_receita
        self.custo = custo
        self.tempo_preparo = tempo_preparo
        self.fator_recomendacao = fator_recomendacao
        self.nivel_dificuldade = nivel_dificuldade
        self.lista_categoria_receitas = lista_categoria_receitas
        self.lista_quantidade_ingredientes = lista_quantidade_ingredientes