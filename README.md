# Desafio na Cozinha — AED II

**Disciplina:** Algoritmos e Estruturas de Dados II  
**Integrantes:** Juan Ignacio Iturralde Pereira · Jean Barros Correa  
**Repositório:** https://github.com/JuanItu/Desafio-na-cozinha-AED2

---

## Descrição

Sistema de gerenciamento de receitas e menus desenvolvido para a disciplina de AED II. O sistema permite buscas eficientes por nome e prefixo (Trie), busca por nome exato com O(1) amortizado (Tabela Hash com redimensionamento dinâmico), recomendação de receitas sob restrições (Algoritmo Guloso) e investigação de integridade das receitas (histórico de estados com snapshots).

---

## Como Executar

### Pré-requisitos

- Python 3.10 ou superior
- Nenhuma biblioteca externa necessária (apenas bibliotecas padrão do Python)

### Execução

```bash
# Clone o repositório (ou descompacte o .zip)
cd Desafio-na-cozinha-AED2-main

# Execute o sistema
python main.py
```

Ao iniciar, o sistema pergunta qual base de dados carregar:

```
  [1] Dados de Fábrica (dados_fonte.json)   ← base original com 50 receitas
  [2] Dados Salvos    (dados_salvos.json)   ← estado salvo pelo usuário
```

Escolha `1` para começar com os dados originais.l 

---

## Fonte de Dados

### API Utilizada: Spoonacular Food API

**URL:** https://spoonacular.com/food-api

Os dados foram coletados via API REST da Spoonacular, que retorna receitas em formato JSON. Para cada receita, extraímos os seguintes campos:

| Campo na API Spoonacular | Campo no sistema          | Descrição                             |
|--------------------------|---------------------------|---------------------------------------|
| `title`                  | `nome`                    | Nome da receita                       |
| `dishTypes`              | `categorias`              | Tipos de prato (ex: lunch, dinner)    |
| `extendedIngredients[].name` | `ingredientes`        | Lista de ingredientes                 |
| `readyInMinutes`         | `tempo_preparo_minutos`   | Tempo total de preparo em minutos     |
| `pricePerServing`        | `custo_centavos_dolar`    | Custo estimado por porção em centavos |
| `aggregateLikes`         | `popularidade_likes`      | Número de curtidas/avaliações         |

### Exemplo de registro no banco de dados (`dados_fonte.json`)

```json
{
  "id": 631868,
  "nome": "4 Ingredient Chicken Pot Pie",
  "categorias": [
    "lunch",
    "main course",
    "main dish",
    "dinner"
  ],
  "ingredientes": [
    "pie crust",
    "campbell's chicken gravy",
    "cut-up vegetables",
    "cans swanson premium chicken breast in water"
  ],
  "tempo_preparo_minutos": 45,
  "custo_centavos_dolar": 440.62,
  "popularidade_likes": 24
}
```

### Adaptações realizadas

- O campo `pricePerServing` (já em centavos de dólar) foi mantido como inteiro/float no campo `custo_centavos_dolar`.
- O campo `dishTypes` foi mapeado para `categorias` como lista de strings.
- Apenas o nome do ingrediente (`name`) foi extraído de `extendedIngredients`, descartando informações de quantidade da API (geridas internamente pelo sistema).
- Os dados foram salvos localmente no arquivo `data/dados_fonte.json` com 50 receitas para garantir funcionamento offline.

---

## Estruturas de Dados Implementadas

O projeto utiliza as sevuintes **3 técnicas**: **Trie**, **Tabela Hash** e **Algoritmo Guloso**.

---

### 1. Árvore Trie — `motor/busca_geral.py`

**Onde é aplicada:** Módulo 2 (Busca Rápida) → opção `[3] Busca Geral (Nome/Prefixo)` no menu.

**O que faz:** Permite busca por prefixo em receitas, ingredientes e categorias simultaneamente. Digitando `"ch"`, o sistema retorna tudo que começa com esse prefixo (ex: *Chicken Pot Pie*, *chocolate*, *cheese*), já separado por tipo e em ordem alfabética.

**Como foi implementada:**

A Trie é composta por dois nós:

- `TrieNode`: cada nó guarda um dicionário `children` (mapeamento char → filho) e uma lista `objetos` (objetos que terminam naquele nó). Usa `__slots__` para economizar memória.
- `TrieBuscaGeral`: árvore completa com métodos `insert`, `get_node`, `get_all_separated_alphabetically` e `remove`.

A inserção percorre os caracteres da chave, criando nós conforme necessário. A busca por prefixo usa `get_node(prefixo)` para chegar ao nó correto, depois `_coletar_em_ordem` faz uma DFS(Deep Find Search) recursiva com `sorted(node.children.keys())`, garantindo retorno alfabético.

A remoção é recursiva com poda automática: nós que ficam sem objetos e sem filhos são deletados da memória (`del node.children[char]`).

**Complexidade:** `O(m)` para inserção e busca, onde `m` é o comprimento da chave — independente do número de receitas.

**Justificativa:** A Trie foi escolhida por ser a estrutura ideal para buscas por prefixo. Um dicionário ou lista simples exigiria varredura linear O(n) a cada busca. A Trie resolve isso em O(m), onde m é o tamanho do prefixo digitado.

---

### 2. Tabela Hash com Redimensionamento Dinâmico — `motor/busca_id.py`

**Onde é aplicada:** Módulo 2 (Busca Rápida) → opção `[4] Busca por Nome Exato` e `[5] Diagnóstico da Tabela Hash` no menu.

**O que faz:** Permite recuperar qualquer receita, ingrediente ou categoria pelo nome exato em tempo O(1) amortizado. Também detecta quando dois objetos diferentes compartilham o mesmo nome (colisão semântica).

**Como foi implementada:**

A tabela usa **encadeamento separado** (listas ligadas por bucket) para resolução de colisões. Cada bucket pode conter uma lista ligada de `_Slot`s, onde cada `_Slot` guarda a chave e uma lista de objetos com aquele nome.

A função hash é um **polinomial rolling hash** com base 31 — mesmo algoritmo base do `String.hashCode()` do Java, eficiente e com boa distribuição.

O **redimensionamento automático** é ativado sempre que `fator_de_carga > 0.7`. Ao disparar:
1. Calcula `nova_capacidade = próximo_primo(capacidade_atual × 2)`
2. Cria novo array de buckets
3. Reinserir todos os slots com novo hash (rehashing completo)
4. Incrementa o contador interno `_rehashes`

**Complexidade:** O(1) amortizado para inserção e busca. O rehashing custa O(n) pontualmente, mas como dobra o tamanho, ocorre cada vez mais raramente — o custo amortizado por inserção continua O(1).

**Justificativa:** A Tabela Hash complementa a Trie: enquanto a Trie resolve buscas por prefixo, a Hash resolve buscas por nome exato de forma ainda mais rápida. A combinação das duas cobre os dois padrões mais comuns de busca do sistema.

---

### 3. Algoritmo Guloso — `motor/algoritmo_recomendações.py`

**Onde é aplicada:** Módulo 5 (Recomendação do Chef) → opção `[2] Obter Recomendação` no menu.

**O que faz:** Sugere as melhores receitas dados filtros de tempo máximo, custo máximo, ingredientes exigidos/proibidos e categorias desejadas, priorizando sempre pela maior `popularidade_likes`.

**Como foi implementada:**

O `AlgoritmoRecomendacao` mantém internamente um **vetor de receitas pré-ordenado** por `popularidade_likes` (decrescente). O método `recomendar()` percorre esse vetor de forma gulosa: para cada receita, verifica se ela passa em todos os filtros. Se passa, a inclui no resultado. Quando atinge a quantidade solicitada, para imediatamente.


**Complexidade:** O(n log n) para construção (ordenação inicial) e O(n) para cada consulta, onde n é o número de receitas.

**Justificativa:** O algoritmo guloso é adequado aqui porque o critério de otimização (maximizar popularidade) tem a propriedade de escolha gulosa: a receita mais popular válida jamais prejudica a escolha das seguintes, pois cada slot de recomendação é independente.

---

## Modos de Interação

### 🕵️ Modo Investigação
Acessado pela opção `[8]` no menu principal. Permite ver o **histórico completo de versões** de cada receita (cada edição gera um snapshot com data, motivo e estado completo) e consultar o **arquivo morto** de receitas excluídas. O sistema usa um registro global em memória (`Receita.registro_global` e `Receita.registro_excluidas`) para detectar duplicatas e rastrear alterações.

### 🍲 Modo Chef
Acessado pela opção `[2]` no menu principal. Usa o algoritmo guloso para recomendar receitas sob múltiplas restrições simultâneas (tempo, custo, ingredientes, categorias).

### 🔍 Modo Consulta Rápida
Acessado pelas opções [3] (Trie, prefixo) e [4] (Hash, nome exato) no menu principal, permite visualizar e editar os dados das receitas, ingredientes e categorias.
### Adição de receitas 
Permite adicionar receitas ao catálogo, elas podem ser inicializadas com nome, custo, tempo de preparo, lista de categorias e lista de ingredientes. O fator de recomendação é iniciado em 0, pois uma receita recém adicionada não teria ainda avaliações do público, além disso, colocar receitas ou ingredientes ausentes no sistema os adiciona automaticamente.

---

## [RECUPERAÇÃO P1]

### 1. Questão escolhida para recuperação

A dupla escolheu recuperar a **Questão 2** da Prova 1, referente a **Tabelas Hash**.

A atividade de recuperação escolhida foi a **Opção A: Tabelas Hash e Análise Amortizada**.

---

### 2. Arquitetura da implementação


#### O que foi implementado — `motor/busca_id.py`

A classe `TabelaHashNomes` implementa do zero uma Tabela Hash com as seguintes propriedades:

**Função hash — polinomial rolling hash:**
```python
def _hash(self, chave: str) -> int:
    h = 0
    base = 31
    for ch in chave:
        h = (h * base + ord(ch)) % self._capacidade
    return h
```
Essa função distribui as chaves uniformemente pelos buckets, minimizando colisões.

**Resolução de colisões — encadeamento separado:**  
Cada bucket é uma lista ligada de `_Slot`s. Quando dois nomes diferentes produzem o mesmo índice hash (colisão de bucket), ambos coexistem no mesmo bucket encadeados. Quando o mesmo nome é inserido duas vezes (colisão semântica), os objetos são agrupados na mesma lista interna do `_Slot`.

**Fator de carga e gatilho de redimensionamento:**
```python
FATOR_MAXIMO = 0.7   # limite estrito

# Após cada inserção:
if self.fator_de_carga > self.FATOR_MAXIMO:
    self._redimensionar()
```
O fator de carga é `elementos_inseridos / capacidade_total`. Mantê-lo abaixo de 0.7 garante que a maioria dos buckets tenha no máximo 1 elemento, preservando o O(1) de busca.

**Redimensionamento dinâmico — rehashing:**
```python
def _redimensionar(self) -> None:
    nova_capacidade = _proximo_primo(self._capacidade * 2)
    novos_buckets = [None] * nova_capacidade
    for bucket in self._buckets:
        no = bucket
        while no:
            proximo = no.proximo
            h = 0
            for ch in no.chave:
                h = (h * 31 + ord(ch)) % nova_capacidade
            no.proximo = novos_buckets[h]
            novos_buckets[h] = no
            no = proximo
    self._capacidade = nova_capacidade
    self._buckets = novos_buckets
    self._rehashes += 1
```

O tamanho dobra e assume o próximo número primo, calculado pela função auxiliar `_proximo_primo(n)`. Usar primos reduz padrões de colisão que surgiriam com capacidades potências de 2.

**Análise amortizada — por que ainda é O(1):**  
Considere n inserções. Os rehashings ocorrem quando a tabela atinge capacidades 11 → 23 → 47 → 97 → ... Cada rehashing custa O(tamanho_atual). Somando todos esses custos ao longo de n inserções, o total é proporcional a `11 + 23 + 47 + ... ≤ 2n` (série geométrica). Portanto, o custo **amortizado por inserção** é `O(2n/n) = O(1)`.

---

### 3. Passo a passo para testar a funcionalidade na avaliação

#### Opção A — Teste direto

Execute diretamente o módulo da Tabela Hash, que possui um bloco `__main__` de demonstração:

```bash
cd Desafio-na-cozinha-AED2-main
python motor/busca_id.py
```

**Saída esperada no terminal utilizando os dados fonte:**

```
============================================================
  DIAGNOSTICO ATUAL DA TABELA HASH
============================================================
  Capacidade (buckets) : 797
  Elementos inseridos  : 356
  Fator de carga       : 0.4467  (limite: 0.7)
  Colisoes acumuladas  : 53
  Rehashes realizados  : 6
------------------------------------------------------------
  Mapa dos primeiros 30 buckets:
    [  0] [ vazio ]
    [  1] "garlic powder"
    [  2] [ vazio ]
    [  3] [ vazio ]
    [  4] [ vazio ]
    [  5] [ vazio ]
    [  6] [ vazio ]
    [  7] "tap water" -> "oreo mini cheesecake" <- COLISAO
    [  8] [ vazio ]
    [  9] [ vazio ]
    [ 10] [ vazio ]
    [ 11] [ vazio ]
    [ 12] [ vazio ]
    [ 13] [ vazio ]
    [ 14] [ vazio ]
    [ 15] [ vazio ]
    [ 16] [ vazio ]
    [ 17] [ vazio ]
    [ 18] "linguini" -> "asparagus" <- COLISAO
    [ 19] "evaporated skim milk"
    [ 20] [ vazio ]
    [ 21] [ vazio ]
    [ 22] "xanthan gum" -> "ginger- 1" <- COLISAO
    [ 23] "guacamole"
    [ 24] [ vazio ]
    [ 25] "appetizer"
    [ 26] [ vazio ]
    [ 27] [ vazio ]
    [ 28] "upside down chicken cake"
    [ 29] [ vazio ]
    ... (e mais 767 buckets)
============================================================
```

O log mostra exatamente o momento em que o fator de carga ultrapassa 0.7 e a tabela dobra de tamanho automaticamente.

#### Opção B — Teste via menu interativo do sistema completo

```bash
python main.py
```

1. Selecione `[1]` para carregar os dados de fábrica (50 receitas → força múltiplos rehashings na construção)
2. No menu principal, escolha `[5] Diagnostico da Tabela Hash`
3. O terminal exibirá o estado físico completo da tabela **após** o carregamento em lote:

```
============================================================
  DIAGNOSTICO ATUAL DA TABELA HASH
============================================================
  Capacidade (buckets) : 193
  Elementos inseridos  : 130
  Fator de carga       : 0.6736  (limite: 0.7)
  Colisoes acumuladas  : 8
  Rehashes realizados  : 3
------------------------------------------------------------
  Mapa dos primeiros 30 buckets:
    [  0] [ vazio ]
    [  1] "lunch"
    [  2] [ vazio ]
    [  3] "butter" -> "buttered noodles" <- COLISAO
    ...
```

Isso demonstra visualmente o estado físico da tabela depois que as 50 receitas + ingredientes + categorias foram inseridos — exatamente o cenário de "carregamento em lote que força redimensionamento" descrito na Opção A do enunciado de recuperação.

---
