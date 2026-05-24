class Categoria:
    registro_global = {}

    def __init__(self, nome_categoria):
        self.nome_categoria = nome_categoria
        # Começa sempre vazia internamente para evitar o bug do argumento padrão mutável
        self.lista_categoria_receitas = [] 
        
        # Salva no registro usando o nome em minúsculo como chave única
        Categoria.registro_global[nome_categoria.lower()] = self

    @classmethod
    def get_ou_criar(cls, nome_categoria):
        nome_key = nome_categoria.lower()
        if nome_key not in cls.registro_global:
            return cls(nome_categoria)
        return cls.registro_global[nome_key]

    def adicionar_receita(self, receita):
        if receita not in self.lista_categoria_receitas:
            self.lista_categoria_receitas.append(receita)

    def remover_receita(self, receita):
        if receita in self.lista_categoria_receitas:
            self.lista_categoria_receitas.remove(receita)

    def mudar_nome(self, novo_nome, trie_global=None):
        #Muda o nome e atualiza o registro. Recebe a Trie opcionalmente para mantê-la sincronizada.
        nome_antigo_key = self.nome_categoria.lower()
        novo_nome_key = novo_nome.lower()
        
        if novo_nome_key in Categoria.registro_global:
            raise ValueError(f"A categoria '{novo_nome}' já existe!")
            
        if trie_global:
            trie_global.remove(nome_antigo_key, self) # Poda o caminho antigo
            
        del Categoria.registro_global[nome_antigo_key]
        self.nome_categoria = novo_nome
        Categoria.registro_global[novo_nome_key] = self
        
        if trie_global:
            trie_global.insert(novo_nome_key, self) # Insere o caminho novo

    def __str__(self): return self.nome_categoria
    def __repr__(self): return self.nome_categoria