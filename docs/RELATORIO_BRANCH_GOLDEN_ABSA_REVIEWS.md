

# Relatório da branch `golden-absa-reviews`

**Projeto:** Golden Reviews

**Objetivo deste documento:**
registrar, em linguagem simples e completa, tudo o que foi alterado nesta branch, para facilitar:

1. entender o que mudou;
2. integrar depois com a `main` principal;
3. integrar com a branch do banco SQL do seu amigo;
4. evitar perda de contexto quando o projeto voltar a ser mexido no futuro.

---

## 1) Visão geral da branch

Esta branch representa a virada do projeto para uma arquitetura mais madura de **ABSA (Aspect-Based Sentiment Analysis)**.

Antes, o sistema dependia mais de regras, dicionários e caminhos experimentais. Nesta branch, a ideia central passou a ser:

- buscar reviews da Steam;
- quebrar o texto em frases;
- classificar cada frase com um modelo de sentimento;
- agrupar as frases semanticamente com BERTopic;
- devolver um JSON organizado para o frontend;
- guardar o resultado em cache SQLite para evitar reprocessamento.

Em resumo: a branch trocou uma análise mais “manual” por uma análise mais “inteligente”, com modelos de NLP já treinados.

---

## 2) Resumo rápido das mudanças no diff

Comparando `main...HEAD`, a branch trouxe:

- **29 arquivos alterados**;
- **muita adição de novos artefatos de ML**;
- **remoção de código antigo experimental**;
- **adaptação do frontend para o novo formato de resposta**;
- **inclusão de cache local em SQLite**;
- **novo pipeline offline de treinamento**;
- **novo pipeline online de inferência**.

Também houve bastante movimentação de arquivos grandes de modelo e dataset:

- modelos BERTopic antigos saíram de pastas de sandbox;
- o modelo final passou para `steam_bertopic_model/`;
- entrou um dataset `steam_reviews.csv`;
- entrou um banco local `backend/cache.db`;
- entrou um output de análise `backend/analysis_output/reviews_analysis.json`.

---

## 3) O que mudou por camada

### 3.1 Backend principal (`backend/app.py`)

O backend virou um **FastAPI** com:

- CORS liberado para o frontend;
- consulta à Steam para buscar jogos e reviews;
- consulta à SteamSpy para enriquecer os dados do jogo;
- cache em SQLite na tabela `game_cache`;
- execução em background para não travar a interface;
- retorno via polling com status `202` enquanto a análise está em andamento.

#### O que esse arquivo faz agora

- `GET /search`: busca jogos na Steam pelo nome;
- `GET /reviews`: dispara ou consulta a análise;
- cria cache no SQLite quando um jogo ainda não foi processado;
- executa a análise pesada em background;
- devolve o resultado final já montado quando o processamento termina.

#### Estrutura do cache SQLite

A tabela `game_cache` passou a ter:

- `appid` como chave primária;
- `status`;
- `data`;
- `updated_at`.

#### Fluxo de execução

1. o frontend chama `/reviews`;
2. o backend verifica se já existe resultado no cache;
3. se existir e estiver pronto, devolve o JSON final;
4. se ainda estiver processando, devolve `202`;
5. se não existir, cria o registro e agenda a análise em background;
6. o worker busca reviews, roda o pipeline e salva o resultado no banco.

#### O que isso resolve

- evita reprocessar a mesma análise toda hora;
- melhora a sensação de responsividade no frontend;
- separa melhor a coleta de dados da exibição.

---

### 3.2 Pipeline online de inferência (`backend/pipeline_online.py`)

Este foi um dos pontos mais importantes da branch.

O arquivo passou a concentrar a lógica de ABSA em tempo real.

#### O que ele carrega na memória

- modelo de sentimento: `tabularisai/multilingual-sentiment-analysis`;
- tokenizer do mesmo modelo;
- embeddings com `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`;
- modelo BERTopic salvo localmente em `steam_bertopic_model`.

#### O que ele faz com as reviews

1. recebe a lista de reviews brutas;
2. quebra cada review em frases;
3. descarta frases muito curtas;
4. roda `topic_model.transform()` para descobrir o tópico de cada frase;
5. calcula o score contínuo de sentimento para cada frase;
6. monta um DataFrame com `review_id`, `sentence`, `review_score` e `topic_id`;
7. agrega os dados por tópico;
8. separa tópicos positivos e negativos com base no score médio;
9. retorna um JSON final com resumo, tópicos, palavras-chave e frases de exemplo.

#### Regra de polaridade

A branch usa o seguinte raciocínio:

- se o score médio do tópico for **maior ou igual a 3.0**, o tópico é tratado como **positivo**;
- se for **menor que 3.0**, o tópico é tratado como **negativo**.

#### Melhoria importante na extração das `quotes`

Foi corrigido um problema prático na geração de frases de exemplo.

Antes, o sistema pegava exemplos de forma mais cega e isso podia misturar frases positivas e negativas no mesmo tópico.

Agora a lógica ficou assim:

- para tópicos **positivos**, pega só frases com `review_score >= 3.0`, ordenadas da maior nota para a menor;
- para tópicos **negativos**, pega só frases com `review_score < 3.0`, ordenadas da menor nota para a maior;
- se esse filtro vier vazio, o sistema faz **fallback** e pega as 2 primeiras frases do tópico original.

#### Por que isso é importante

Isso deixa o front mais coerente.

Exemplo simples:

- se o tópico é de “Gráficos” e o cluster foi classificado como negativo, as frases exibidas também devem ser negativas;
- se o tópico é positivo, os exemplos precisam reforçar esse tom.

Assim, o usuário não vê um card negativo com frases de elogio perdidas no meio.

#### Resultado final entregue pelo pipeline

O JSON final inclui:

- nome do jogo;
- score geral;
- quantidade de reviews analisadas;
- tópicos positivos;
- tópicos negativos;
- tempo de processamento;
- versão do modelo.

---

### 3.3 Treinamento offline (`train_offline.py`)

Este arquivo criou a base do modelo final.

Ele faz o papel do treinamento fora da API, para não pesar o backend em produção.

#### O que ele faz

- carrega o dataset `steam_reviews.csv`;
- lê reviews históricas;
- divide os textos em frases;
- cria embeddings com MiniLM;
- treina o BERTopic;
- usa `CountVectorizer` com stop words em português e termos genéricos de jogos;
- reduz outliers com `reduce_outliers`;
- salva o modelo treinado em `steam_bertopic_model`.

#### O que mudou conceitualmente

A branch consolidou a ideia de que o treinamento é **offline** e a inferência é **online**.

Isso é ótimo para produção, porque:

- o treinamento fica caro e pesado, mas acontece uma vez;
- o backend só carrega o modelo pronto;
- a aplicação fica muito mais rápida na hora do uso.

---

### 3.4 Frontend principal (`src/App.jsx`)

O frontend foi adaptado para conversar com o backend novo.

#### Comportamento atual

- pesquisa jogos por nome;
- mostra os resultados da busca;
- permite escolher quantidade máxima de reviews;
- permite escolher idioma;
- dispara a análise ao clicar no botão;
- fica em polling enquanto o backend responde `processing`;
- mostra o resultado quando o cache retorna `completed`.

#### Mudança de UX importante

O botão de análise agora deixa claro que o processo é pesado:

- “Analisando com Golden Reviews...”
- “Processando reviews...”

Isso melhora a experiência do usuário e evita a sensação de travamento.

---

### 3.5 Componente de análise (`src/components/ReviewAnalysis.jsx`)

Este componente foi ajustado para o novo contrato de dados.

#### O que ele exibe agora

- nome do jogo;
- score geral;
- data de lançamento;
- preço;
- descrição curta;
- número de reviews processadas;
- tempo de processamento;
- versão do modelo;
- estimativa de cópias da SteamSpy;
- total de reviews da Steam;
- lista de tópicos positivos ou negativos;
- frases de exemplo (`quotes`).

#### Como a tela foi organizada

O componente tem um seletor para alternar entre:

- tópicos positivos;
- tópicos negativos.

Isso ajuda a ler o resultado com mais clareza, sem misturar tudo numa tela só.

#### Compatibilidade com o novo JSON

O componente já espera algo nessa linha:

- `data.topics.positive`
- `data.topics.negative`
- `data.summary`
- `data.game`
- `data.metadata`

Ou seja: o frontend foi ajustado para consumir exatamente a estrutura produzida pelo backend novo.

---

### 3.6 Serviço de API do frontend (`src/services/steamApi.js`)

Esse arquivo é simples, mas importante.

Ele passou a apontar para:

- `http://localhost:8000/search`
- `http://localhost:8000/reviews`

#### Funções expostas

- `searchSteamGames(term)`
- `getReviews(appid, maxReviews, language)`

#### O que isso garante

- o frontend fala diretamente com o backend local;
- a URL está centralizada em um único lugar;
- fica mais fácil trocar a base depois, se necessário.

---

### 3.7 Script de auditoria do modelo (`check_model.py`)

Esse arquivo serve para inspecionar o modelo BERTopic salvo.

Ele:

- carrega `steam_bertopic_model`;
- lê a tabela de tópicos;
- mostra quantos tópicos úteis foram criados;
- exibe os 15 tópicos mais frequentes.

#### Finalidade prática

É um script de verificação, útil para responder perguntas como:

- o modelo foi salvo corretamente?
- quantos tópicos reais ele tem?
- qual é o nome dos tópicos mais fortes?

---

### 3.8 Script de correção de encoding (`fix_enc.cjs`)

Esse arquivo foi criado como um utilitário rápido para corrigir texto quebrado por encoding e alguns valores antigos de porta.

#### O que ele faz

- ajusta a porta no arquivo `src/services/steamApi.js`;
- corrige trechos com encoding ruim em `src/App.jsx`;
- corrige encoding ruim em `src/components/ReviewAnalysis.jsx`.

#### Observação

Esse tipo de script costuma ser um hotfix pontual.

Se o projeto for consolidado depois, vale a pena revisar se ele ainda é necessário ou se os textos já ficaram normalizados de forma permanente.

---

## 4) Arquivos adicionados, removidos e reorganizados

### Arquivos adicionados

- `README_TEMP.md`
- `backend/cache.db`
- `backend/pipeline_online.py`
- `check_model.py`
- `fix_enc.cjs`
- `steam_bertopic_model/config.json` _(movido/renomeado a partir da estrutura antiga)_
- `steam_bertopic_model/topic_embeddings.safetensors`
- `steam_bertopic_model/topics.json`
- `steam_reviews.csv`
- `train_offline.py`

### Arquivos modificados

- `README.md`
- `backend/analysis_output/reviews_analysis.json`
- `backend/app.py`
- `requirements.txt`
- `src/App.jsx`
- `src/components/ReviewAnalysis.jsx`
- `src/services/steamApi.js`

### Arquivos removidos

- `backend/bert_pipeline.py`
- vários arquivos antigos de sandbox do BERTopic dentro de `sandbox/pacotao_golden_review/models/bertopic/...`

### Reorganização de modelos

Os artefatos do BERTopic que antes estavam espalhados em pastas experimentais foram consolidados para:

- `steam_bertopic_model/`

Isso é um sinal claro de que a branch saiu do modo “experimento” e entrou no modo “modelo oficial” para integração.

---

## 5) O que essa branch quer resolver de verdade

Esta branch não é só uma troca de arquivos.

Ela tenta resolver estes problemas:

1. **Análise mais inteligente das reviews**
   - sai a lógica mais manual;
   - entra sentimento + tópicos semânticos.

2. **Menos travamento na interface**
   - backend processa em background;
   - frontend usa polling.

3. **Menos retrabalho**
   - reviews já analisadas ficam em cache no SQLite.

4. **Melhor leitura para o usuário final**
   - tópicos positivos e negativos ficam separados;
   - frases de exemplo combinam com a polaridade do card.

---

## 6) Como integrar isso com a `main`

Se a ideia é levar isso para a branch principal, eu recomendo esta ordem:

### Passo 1 — consolidar o backend

Levar junto:

- `backend/app.py`
- `backend/pipeline_online.py`
- `train_offline.py`
- `steam_bertopic_model/`

Esses são os blocos que definem o novo comportamento da IA e da API.

### Passo 2 — validar o contrato JSON

Antes de mesclar com o frontend final, confirmar que o backend entrega sempre:

- `game`
- `summary`
- `topics.positive`
- `topics.negative`
- `metadata`

Isso evita quebra de tela depois.

### Passo 3 — alinhar o frontend

Levar junto:

- `src/App.jsx`
- `src/components/ReviewAnalysis.jsx`
- `src/services/steamApi.js`

E testar se o frontend continua enxergando corretamente:

- busca de jogos;
- consulta de reviews;
- status de processamento;
- resultado final.

### Passo 4 — decidir o que fazer com os arquivos grandes

Antes de mergir de vez, vale decidir se estes arquivos devem mesmo entrar no repositório principal:

- `steam_reviews.csv`
- `backend/cache.db`
- modelos BERTopic serializados

Eles são úteis para rodar o projeto, mas podem aumentar bastante o peso do repositório.

### Passo 5 — remover o que ficou obsoleto

Se a `main` ainda tiver lógica antiga, os alvos mais prováveis de limpeza são:

- `backend/bert_pipeline.py`;
- qualquer chamada antiga que dependa de regras por palavras-chave;
- qualquer tela que espere um JSON velho.

---

## 7) Como integrar isso com a branch do banco SQL do seu amigo

Como você comentou que existe uma parte do banco SQL em outra branch, o ponto mais importante é este:

**o backend desta branch já trabalha com cache e status de processamento, então a integração com o SQL precisa respeitar esse contrato.**

### O que já existe aqui

A branch usa SQLite com a tabela:

- `appid`
- `status`
- `data`
- `updated_at`

### Como encaixar com um banco SQL mais estruturado

Se a outra branch for para persistência mais séria, a migração ideal seria:

- manter o conceito de cache por jogo;
- talvez separar em tabelas menores;
- guardar o JSON final em uma coluna própria ou em tabelas relacionadas;
- registrar status de processamento;
- registrar timestamps;
- talvez registrar versão do modelo usado.

### Sugestão prática de integração

Uma forma segura de unir as duas frentes é:

1. **manter esta branch como produtora do JSON final**;
2. **fazer o SQL da outra branch consumir esse JSON**;
3. **salvar o resultado no banco relacional sem mudar o formato de resposta da API**.

Assim, você evita misturar duas responsabilidades ao mesmo tempo.

### O que eu consideraria importante no banco

Se vocês forem para um SQL mais formal, eu recomendaria ter pelo menos:

- tabela de jogos;
- tabela de análises;
- tabela de tópicos;
- tabela de frases de exemplo;
- tabela de status de jobs.

Mas isso é a evolução natural — não precisa quebrar a branch atual para isso.

---

## 8) Pontos de atenção antes de mesclar

### 8.1 Arquivos gerados e peso do repositório

Alguns arquivos parecem mais artefato de execução do que código-fonte puro.

Exemplos:

- `backend/cache.db`
- `steam_reviews.csv`
- arquivos do modelo BERTopic serializado

Se a equipe quiser manter o repositório mais leve, vale avaliar o que fica versionado e o que vai para armazenamento externo.

### 8.2 Limpeza de arquivos antigos

Foi removido `backend/bert_pipeline.py`, então é importante garantir que nada mais chame esse arquivo.

### 8.3 Contrato entre backend e frontend

Se o backend mudar o formato do JSON, o frontend quebra.

Então o contrato atual precisa ser tratado como algo estável.

### 8.4 Versão do modelo

O frontend mostra `model_version`.

Isso é ótimo, porque ajuda a rastrear qual versão da IA gerou aquele resultado.

---

## 9) Leitura simples do fluxo atual do sistema

Em linguagem bem direta:

1. o usuário digita o nome do jogo;
2. o frontend busca os jogos na Steam;
3. o usuário escolhe um jogo;
4. o backend busca as reviews;
5. o backend salva/consulta o cache;
6. o pipeline separa as frases em tópicos;
7. o modelo calcula sentimento e score;
8. o backend monta o JSON final;
9. o frontend mostra os tópicos positivos e negativos separadamente.

---

## 10) Conclusão

Esta branch foi o ponto de virada do Golden Reviews para uma arquitetura mais séria e mais próxima de produção.

O que ela trouxe de mais importante foi:

- **ABSA de verdade**, com sentimento + tópicos;
- **pipeline offline/online separado**;
- **backend assíncrono com cache SQLite**;
- **frontend ajustado para o novo JSON**;
- **modelos e dataset organizados para reutilização**.

Se a próxima etapa for integrar com a `main` e com a branch do banco SQL, o caminho mais seguro é manter o contrato de dados estável e encaixar a persistência como uma camada acima do resultado final da IA.

---

## 11) Arquivo recomendado para próxima leitura

Se você quiser continuar a documentação ou fazer a integração, os arquivos mais importantes para abrir depois são:

- `backend/app.py`
- `backend/pipeline_online.py`
- `src/components/ReviewAnalysis.jsx`
- `src/App.jsx`
- `train_offline.py`

Eles contam praticamente toda a história da branch.
