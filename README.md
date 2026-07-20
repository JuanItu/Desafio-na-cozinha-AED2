# Desafio na Cozinha — AED II

**Disciplina:** Algoritmos e Estruturas de Dados II  
**Integrantes:** Juan Ignacio Iturralde Pereira · Jean Barros Correa  
**Repositório:** https://github.com/JuanItu/Desafio-na-cozinha-AED2

---

## Descrição

Sistema de gerenciamento de receitas e menus desenvolvido para a disciplina de AED II. O sistema permite buscas eficientes por nome e prefixo (Trie), busca por nome exato com O(1) amortizado (Tabela Hash com redimensionamento dinâmico), recomendação de receitas sob restrições (Algoritmo Guloso) e investigação de integridade das receitas (histórico de estados com snapshots).

No **Desafio na Cozinha 2** (Trabalho 2), o sistema foi expandido com 4 novos módulos sobre a mesma base de dados e funcionalidades do Trabalho 1: verificação de dependências entre preparos com detecção de ciclos (Módulo 5), otimização de menus VIP sob restrições (Módulo 6), planejamento de infraestrutura de delivery e análise de capacidade/gargalo via redes de fluxo (Módulo 7), e roteamento inteligente de entregas com TSP híbrido (Módulo 8).

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
  [1] Dados de Fábrica (dados_fonte.json)          ← base original com 50 receitas
  [2] Dados Salvos    (dados_salvos.json)          ← estado salvo pelo usuário
  [3] Dados de Teste — Ciclos Propositais          ← dataset com ciclos de dependência propositais (ver seção "Módulo 5")
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

# Desafio na Cozinha 2 — Módulos 5 a 8

O Trabalho 2 reutiliza integralmente a base de dados e os módulos do Trabalho 1 (Trie, Tabela Hash, Algoritmo Guloso, Histórico) e os expande com 4 novos módulos, focados em modelagem de redes e otimização de decisões. Todos acessíveis a partir do mesmo `main.py`.

## Rede de Logística — Dimensões

Os Módulos 7 e 8 operam sobre uma malha viária carregada de `data/malha_urbana.txt`:

| Métrica | Valor |
|---|---|
| Vértices (cruzamentos) | 36 |
| Arestas viárias (bidirecionais) | 58 |

Atende ao requisito mínimo do enunciado (≥ 30 vértices e ≥ 50 arestas).

---

### 4. Módulo 5 — Oficina de Produção (Grafo de Dependências) — `motor/oficina_producao.py`

**Onde é aplicada:** opção `[9] Oficina de Produção` no menu principal, e automaticamente na inicialização do sistema (Verificação Geral).

**O que faz:** Modela as dependências entre receitas (`receita.lista_preparos`) como um **grafo dirigido**, onde uma aresta `A -> B` significa "A precisa de B como preparo". A partir disso, responde às consultas exigidas pelo enunciado:
- *"Existe algum erro de dependência?"* → `existe_erro_dependencia()`
- *"Qual a sequência correta para produzir o menu do dia?"* → `sequencia_producao()`
- *"Quais preparos precisam ser concluídos antes da receita X?"* → `preparos_necessarios_antes_de(receita)`

**Como foi implementada:**

A Verificação Geral roda 5 passos em sequência:
1. **Autodependências:** varredura O(V) checando se `r in r.lista_preparos`.
2. **Tarjan — Componentes Fortemente Conexos (SCC):** implementado de forma **iterativa** (pilha explícita simulando a recursão, para evitar estouro de pilha em grafos grandes), em `O(V + E)`. Qualquer SCC com 2+ receitas indica um ciclo de dependências.
3. **DFS restrita ao SCC:** para cada componente problemático, uma DFS que anda apenas dentro do SCC identifica a aresta que fecha o ciclo e sugere um `CorteSugerido` (a receita/edge a remover).
4. **Ordenação topológica (Kahn/DFS pós-ordem):** só é executada se o grafo for um DAG (sem ciclos). Garante que cada preparo apareça antes de quem depende dele — a "sequência correta de produção".
5. **Coerência de custo/tempo/preço:** varredura O(V+E) que compara o custo/tempo/preço de cada receita com a soma/máximo dos seus preparos diretos, sugerindo ajustes (`SugestaoAjuste`) quando a receita está "mais barata" ou "mais rápida" do que fisicamente possível.

Toda sugestão (corte de ciclo ou ajuste de coerência) pode ser aplicada individualmente ou em lote pelo usuário.

**Bloqueio de novos ciclos na edição:** para além da detecção retroativa, o `main.py` impede a criação de **novos** ciclos em tempo real: ao adicionar um preparo pela opção `[E] Editar Receita → 10. Adicionar Preparo`, a função `_criaria_ciclo()` reaproveita a BFS de `preparos_necessarios_antes_de()` para checar se a nova aresta fecharia um ciclo, bloqueando a operação se sim.

**Dados de teste com ciclos propositais:** como o bloqueio acima impede criar ciclos pela interface, para continuar demonstrando a detecção retroativa (passos 1-3) existe a opção `[3]` na tela inicial, que carrega `data/dados_teste_ciclos.json` — um dataset pequeno com uma autodependência, um ciclo de 2 receitas e um ciclo de 3 receitas.

**Complexidade:** `O(V + E)` para a Verificação Geral completa (Tarjan é linear; a DFS restrita e a ordenação topológica também são lineares).

**Justificativa:** Tarjan foi escolhido por resolver detecção de ciclos em grafos dirigidos em tempo linear numa única passada, sem precisar de múltiplas execuções de DFS por nó (como uma abordagem ingênua faria). A ordenação topológica por DFS pós-ordem é a forma mais direta de obter uma sequência de produção válida, já que a definição de DAG garante que ela existe.

---

### 5. Módulo 6 — Menu Degustação VIP (Otimização) — `motor/gerar_menu.py`

**Onde é aplicada:** opção `[10] Modo Chef` → `1. Gerar Menu VIP Otimizado`.

**O que faz:** Dado um orçamento e tempo máximos, e uma lista de categorias com a quantidade de pratos exigida em cada uma (ex: 1 entrada + 1 prato principal + 1 sobremesa), encontra a combinação de receitas que **maximiza o lucro ou a popularidade**, respeitando os limites — respondendo a perguntas como *"Qual o melhor menu com orçamento de R$ 500?"*.

**Como foi implementada:**

O problema é combinatório (escolher k receitas de cada categoria dentre várias), então a força bruta seria exponencial. A solução implementada é uma **busca best-first via Max-Heap**, com duas otimizações centrais:

1. **Pré-ordenação gulosa por categoria:** as receitas de cada categoria são ordenadas por `lucro` (ou `fator_recomendacao`) decrescente. Isso garante que o **estado inicial** do heap (pegar os `k` melhores de cada categoria) já é o candidato de maior lucro possível — e cada "vizinho" gerado a partir dele só pode ter lucro igual ou menor.
2. **Geração incremental de vizinhos ("staircase"):** ao expandir um estado, cada categoria avança **apenas para o próximo índice válido** (não para todas as combinações possíveis), com poda O(1) via tetos de custo/tempo pré-calculados por categoria. Isso evita gerar exponencialmente todas as combinações.
3. **Memoização via Trie dinâmica (`TrieCategoria`/`NodeTrieVIP`):** cada caminho de índices já visitado (ex: categoria "entrada" = receitas nos índices `(2, 5)`) é registrado numa Trie, que armazena a soma acumulada de lucro/custo/tempo daquele caminho. Isso evita recalcular somas parciais toda vez que o mesmo sub-estado é revisitado por ramos diferentes do heap.

Como o heap sempre extrai o estado de **maior lucro disponível** (`EstadoMenu.__lt__` inverte a comparação para simular Max-Heap com `heapq`, que é Min-Heap nativo), e os vizinhos gerados só reduzem o lucro, **o primeiro estado que satisfizer as restrições de custo/tempo ao ser retirado do heap é, garantidamente, o menu ótimo global** — sem precisar explorar todas as combinações.

Antes de iniciar a busca, o sistema também faz uma checagem de viabilidade O(n log n) (ordenando custos/tempos por categoria) para detectar de antemão se nem a combinação mais barata cabe no orçamento/tempo, evitando busca desnecessária.

**Complexidade:** `O(K log K)` onde `K` é o número de estados efetivamente expandidos até achar a primeira combinação viável (tipicamente muito menor que o total de combinações possíveis, graças à poda e à ordem gulosa de exploração); cada expansão custa `O(número de categorias)`.

**Justificativa:** Esse problema é uma variação do clássico "k maiores somas combinadas de listas ordenadas" (resolvido classicamente com heap). Usar heap + memoização por Trie é mais adequado que programação dinâmica pura aqui porque as restrições são multidimensionais (custo E tempo simultaneamente) e o espaço de estados é gerado sob demanda, evitando pré-computar tabelas gigantes quando o menu ótimo geralmente é encontrado nas primeiras extrações do heap.

---

### 6. Módulo 7 — O Pesadelo Logístico (MST + Fluxo de Custo Mínimo) — `motor/infraestrutura_minima.py`, `motor/fluxo_capacidade.py`

**Onde é aplicada:** opção `[11] Pesadelo Logístico` no menu principal (submenu com as duas funcionalidades abaixo).

#### 6.1 Infraestrutura Mínima (MST) — *"determinar a menor rede de conexões necessária"*

**O que faz:** Dado um conjunto de pontos operacionais (cozinhas, hubs), calcula a **Árvore Geradora Mínima** — a menor malha de conexões viárias reais que interliga todos eles, minimizando o custo total de infraestrutura.

**Como foi implementada:** **Lazy Kruskal**: em vez de calcular a rota real (A*) entre **todos** os pares de pontos de antemão (caro), o algoritmo:
1. Insere no heap todas as arestas com o custo **estimado** (distância euclidiana / linha reta), que é sempre um limite inferior do custo real.
2. Ao extrair a aresta de menor custo do heap, se ela ainda é só uma estimativa, dispara o **A* real** sob demanda, e a reinsere no heap com o custo verdadeiro.
3. Só quando uma aresta sai do heap **já validada com A* real** é que ela é testada contra o **Union-Find** (com *union by rank* + *path compression*) e, se não fechar ciclo, é adicionada à MST.

Isso garante corretude (o Kruskal só aceita arestas com custo real) evitando rodar A* em pares de pontos que nunca seriam vantajosos de qualquer forma.

**Complexidade:** `O(E log E)` no pior caso (E = pares de pontos), mas o número de A* efetivamente executados costuma ser muito menor que `E`, já que muitas arestas nunca saem do heap por serem descartadas antes (ciclo) ou superadas por opções melhores.

#### 6.2 Capacidade Máxima de Atendimento (Fluxo/Gargalo) — *"existe gargalo operacional?"*

**O que faz:** Modela cozinhas (com capacidade de produção em pratos/hora) e hubs (com capacidade de entregadores) como uma rede de fluxo, calculando **quantos pedidos o sistema atende simultaneamente** e **onde está o gargalo** (produção, entrega ou malha viária).

**Como foi implementada:** **Fluxo Máximo de Custo Mínimo (MCMF)** via **Successive Shortest Paths** com **Bellman-Ford** (necessário pois a rede residual tem arestas de custo negativo):
1. **Vertex splitting:** cada cozinha/hub vira dois nós (`_IN`/`_OUT`) ligados por uma aresta cuja capacidade é a capacidade real (pratos/hora ou nº de entregadores) — a técnica clássica para modelar capacidade **de vértice** (e não só de aresta) em redes de fluxo.
2. Uma super-fonte se conecta a todas as cozinhas, e todos os hubs se conectam a um super-sumidouro.
3. A cada iteração, roda Bellman-Ford para achar o caminho mais barato ainda disponível; o custo das arestas cozinha→hub é resolvido **preguiçosamente** (A* real só é calculado a primeira vez que aquele par é atravessado, e o resultado é cacheado).
4. Empurra o máximo de fluxo possível por esse caminho (o "gargalo" local do caminho), atualiza a rede residual, e repete até não haver mais caminho.

**Compartilhamento de cache:** o dicionário de rotas A* reais (`cache_rotas_global`) é **compartilhado** entre a MST (Módulo 7.1), o Fluxo (7.2) e o TSP (Módulo 8) — uma rota calculada por qualquer um dos três motores fica disponível para os outros, evitando recálculo.

**Complexidade:** `O(F × V × E)` onde F é o valor do fluxo máximo (número de iterações de Bellman-Ford, cada uma `O(V × E)`).

**Justificativa (Módulo 7 como um todo):** MST resolve exatamente "menor rede que conecta tudo" — é o problema clássico para o qual Kruskal/Prim foram desenhados. Para capacidade/gargalo, fluxo em rede é a ferramenta padrão em teoria dos grafos; o MCMF (em vez de fluxo máximo puro) foi escolhido porque o enunciado também pede o "custo operacional", não só a quantidade máxima atendida.

---

### 7. Módulo 8 — Roteamento de Entregas (TSP Híbrido) — `motor/roteador_entregas.py`

**Onde é aplicada:** opção `[12] Roteamento de Entregas` no menu principal.

**O que faz:** Dado um ponto de despacho (restaurante) e uma lista de clientes, encontra uma **rota única** que visita todos os clientes e retorna à origem, **minimizando a distância/tempo total percorrido** — o "Planejamento Inteligente de Entregas" escolhido como desafio do Módulo 8. Esta é a técnica avançada que não foi exigida em nenhum módulo anterior.

**Como foi implementada:** É uma heurística híbrida em 3 fases para o Problema do Caixeiro Viajante (TSP, NP-difícil — resolver de forma exata é inviável para instâncias reais):

1. **Fase 1 — Semente inicial via Convex Hull (Envoltória Convexa):** o algoritmo **Monotone Chain de Andrew**, `O(n log n)`, calcula o contorno externo de todos os pontos (origem + clientes). Esse contorno vira o "esqueleto" inicial do circuito — geometricamente, o hull nunca se auto-intersecta, então é uma base de rota consistente.
2. **Fase 2 — Validação do anel base:** as arestas do hull são avaliadas com **A\*** real (não mais estimativa), usando a malha viária de fato.
3. **Fase 3 — Lazy Farthest/Cheapest Insertion:** os pontos que ficaram **dentro** do hull são inseridos um a um no ponto do anel onde causam o **menor aumento de custo** (`Δ = custo(A,D) + custo(D,B) − custo(A,B)`), usando um **min-heap de propostas**. Assim como no MST, o A\* real só é calculado quando uma proposta chega a ser a melhor candidata do heap (estimativa euclidiana primeiro, validação real depois) — evitando A\* em inserções que nunca seriam escolhidas.

A rota ativa é mantida numa **lista duplamente encadeada circular** (`ListaCircularRota`), o que permite inserir um novo cliente "no meio" do anel em `O(1)`, sem precisar deslocar nenhum outro elemento (como aconteceria com um array/lista Python comum).

**Complexidade:** `O(n log n)` para o Convex Hull, e `O(n log n)` amortizado para as inserções (heap de tamanho proporcional a n × pontos internos, com poda). No total, muito mais rápido que os `O(n!)` de uma busca exaustiva ou mesmo os `O(n² 2ⁿ)` de programação dinâmica exata (Held-Karp), às custas de não garantir o ótimo absoluto — trade-off aceitável e padrão na indústria para roteamento com muitos pontos.

**Justificativa:** TSP exato é inviável mesmo para dezenas de pontos. A combinação Convex Hull + Insertion é uma heurística clássica e bem estudada que produz rotas próximas do ótimo (tipicamente dentro de 10-15% do ótimo) em tempo polinomial, e a estrutura de lista circular evita o custo de reconstrução de array a cada inserção.

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
=== DEMO: Redimensionamento Dinamico ===

-- ANTES do carregamento em lote --

============================================================
  ESTADO INICIAL
============================================================
  Capacidade (buckets) : 7
  Elementos inseridos  : 0
  Fator de carga       : 0.0000  (limite: 0.7)
  Colisoes acumuladas  : 0
  Rehashes realizados  : 0
------------------------------------------------------------
  Mapa dos primeiros 7 buckets:
    [  0] [ vazio ]
    [  1] [ vazio ]
    [  2] [ vazio ]
    [  3] [ vazio ]
    [  4] [ vazio ]
    [  5] [ vazio ]
    [  6] [ vazio ]
============================================================

Inserindo elementos...
  + 'Bolo de Chocolate' | fator=0.143 | capacidade=7
  + 'Farinha de Trigo' | fator=0.286 | capacidade=7
  + 'Sobremesas' | fator=0.429 | capacidade=7
  + 'Torta de Limao' | fator=0.571 | capacidade=7
  + 'Acucar Refinado' | fator=0.294 | capacidade=17
  + 'Salgados' | fator=0.353 | capacidade=17
  + 'Lasanha Bolonhesa' | fator=0.412 | capacidade=17

-- DEPOIS do carregamento em lote --

============================================================
  ESTADO FINAL
============================================================
  Capacidade (buckets) : 17
  Elementos inseridos  : 7
  Fator de carga       : 0.4118  (limite: 0.7)
  Colisoes acumuladas  : 1
  Rehashes realizados  : 1
------------------------------------------------------------
  Mapa dos primeiros 17 buckets:
    [  0] [ vazio ]
    [  1] "torta de limao"
    [  2] "farinha de trigo"
    [  3] [ vazio ]
    [  4] "salgados"
    [  5] [ vazio ]
    [  6] "acucar refinado" -> "bolo de chocolate" <- COLISAO
    [  7] "lasanha bolonhesa"
    [  8] [ vazio ]
    [  9] [ vazio ]
    [ 10] [ vazio ]
    [ 11] [ vazio ]
    [ 12] "sobremesas"
    [ 13] [ vazio ]
    [ 14] [ vazio ]
    [ 15] [ vazio ]
    [ 16] [ vazio ]
============================================================

-- Testes de busca --
  buscar('Bolo de Chocolate') -> ['<objeto_receita:Bolo de Chocolate>']
  buscar('Farinha de Trigo') -> ['<objeto_ingrediente:Farinha de Trigo>']
  buscar('Sobremesas') -> ['<objeto_categoria:Sobremesas>']

  buscar('inexistente') -> []
  'bolo de chocolate' in tabela -> True
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

Isso demonstra visualmente o estado físico da tabela depois que as 50 receitas + ingredientes + categorias foram inseridos — exatamente o cenário de "carregamento em lote que força redimensionamento" descrito na Opção A do enunciado de recuperação.

---
