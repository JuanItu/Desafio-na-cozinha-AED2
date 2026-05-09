class Ingredientes:
    def __init__(self, id_ingredientes, nome_ingrediente, quantidade_estoque, lista_receitas_ingredientes):
        self.id_ingredientes = id_ingredientes
        self.nome_ingrediente = nome_ingrediente
        self.quantidade_estoque = quantidade_estoque
        self.lista_receitas_ingredientes = lista_receitas_ingredientes

class QuantidadeIngredientes:
    def __init__(self, id_ingredientes, unidade_utilizada, quantidade_necessaria):
        self.id_ingredientes = id_ingredientes
        self.unidade_utilizada = unidade_utilizada
        self.quantidade_necessaria = quantidade_necessaria