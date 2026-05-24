class Ingredientes:
    registro_global = {}

    def __init__(self, nome_ingrediente, quantidade_estoque=0.0, trie_global=None, tabela_hash=None):
        self.nome_ingrediente = nome_ingrediente
        self.quantidade_estoque = quantidade_estoque
        self.lista_receitas_ingredientes = []
        
        Ingredientes.registro_global[nome_ingrediente.lower()] = self
        
        # O próprio ingrediente se insere nos motores de busca
        if trie_global:
            trie_global.insert(nome_ingrediente.lower(), self)
        if tabela_hash:
            tabela_hash.inserir(nome_ingrediente.lower(), self)

    @classmethod
    def get_ou_criar(cls, nome_ingrediente, trie_global=None, tabela_hash=None):
        nome_key = nome_ingrediente.lower()
        if nome_key not in cls.registro_global:
            # Lembre de passar 0.0 para o estoque ao repassar os parâmetros
            return cls(nome_ingrediente, 0.0, trie_global, tabela_hash)
        return cls.registro_global[nome_key]

    def adicionar_receita(self, receita):
        if receita not in self.lista_receitas_ingredientes:
            self.lista_receitas_ingredientes.append(receita)

    def remover_receita(self, receita):
        if receita in self.lista_receitas_ingredientes:
            self.lista_receitas_ingredientes.remove(receita)

    def mudar_nome(self, novo_nome, trie_global=None, tabela_hash=None):
        nome_antigo_key = self.nome_ingrediente.lower()
        novo_nome_key = novo_nome.lower()
        
        if novo_nome_key in Ingredientes.registro_global:
            raise ValueError(f"O ingrediente '{novo_nome}' já existe!")
            
        # Remove dos motores antigos
        if trie_global: trie_global.remove(nome_antigo_key, self)
        if tabela_hash: tabela_hash.remover(nome_antigo_key, self)
        
        del Ingredientes.registro_global[nome_antigo_key]
        self.nome_ingrediente = novo_nome
        Ingredientes.registro_global[novo_nome_key] = self
        
        # Insere nos motores novos
        if trie_global: trie_global.insert(novo_nome_key, self)
        if tabela_hash: tabela_hash.inserir(novo_nome_key, self)

    def __str__(self): return self.nome_ingrediente
    def __repr__(self): return self.nome_ingrediente


class QuantidadeIngredientes:
    # Esta classe não precisa de registro global pois ela é apenas um "elo" de ligação.
    def __init__(self, ingrediente_obj, unidade_utilizada, quantidade_necessaria):
        # Recebe o objeto Inteiro em vez do ID!
        self.ingrediente = ingrediente_obj 
        self.unidade_utilizada = unidade_utilizada
        self.quantidade_necessaria = quantidade_necessaria
        
    def __repr__(self):
        return f"{self.quantidade_necessaria}{self.unidade_utilizada} de {self.ingrediente.nome_ingrediente}"