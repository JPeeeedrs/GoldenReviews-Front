# Golden Reviews

GOLDEN REVIEWS — Analise Inteligente de Reviews da Steam
Trabalho Pratico — Topicos de Big Data em Python

## 1. Area e aplicacao escolhidas

O projeto desenvolvido esta voltado para a area de analise de dados aplicada ao mercado de jogos digitais. A aplicacao criada, chamada Golden Reviews, realiza a coleta e analise automatica de reviews de jogos da plataforma Steam, utilizando Python no backend e React no frontend.

A motivacao do projeto surgiu da dificuldade dos usuarios em interpretar milhares de analises presentes na Steam. Muitos jogos possuem uma enorme quantidade de reviews, tornando dificil identificar rapidamente os principais pontos positivos e negativos relatados pela comunidade.

A solucao proposta automatiza esse processo por meio de tecnicas de processamento e analise textual, permitindo extrair tendencias, topicos recorrentes e indicadores relevantes sobre os jogos.

## 2. Objetivos

### Objetivo geral

Desenvolver uma aplicacao capaz de coletar, processar e analisar reviews da Steam, transformando grandes volumes de texto em informacoes organizadas e interpretaveis.

### Objetivos especificos

- Coletar reviews de jogos atraves da API da Steam.
- Processar textos utilizando Python.
- Identificar palavras e topicos recorrentes.
- Separar aspectos positivos e negativos das analises.
- Exibir os resultados de forma visual e intuitiva.
- Facilitar a interpretacao das opinioes dos jogadores.

### Perguntas de analise

- Quais sao os principais problemas relatados pelos jogadores?
- Quais aspectos positivos aparecem com maior frequencia?
- Existe predominancia de reviews positivas ou negativas?
- Quais temas sao mais comentados em determinados jogos?

## 3. Requisitos da aplicacao

### Requisitos funcionais

- Buscar jogos da Steam atraves do nome.
- Coletar reviews utilizando APIs publicas.
- Processar textos automaticamente.
- Identificar topicos relevantes.
- Exibir estatisticas e indicadores.
- Mostrar os jogos mais buscados.
- Permitir visualizacao dinamica no frontend.

### Requisitos nao funcionais

- Interface responsiva.
- Processamento eficiente de grandes quantidades de reviews.
- Integracao entre frontend e backend.
- Organizacao modular do codigo.
- Facilidade de manutencao.
- Compatibilidade com diferentes navegadores.

## 4. Bases de dados

### Origem dos dados

Os dados utilizados no projeto sao obtidos principalmente atraves de APIs publicas relacionadas a Steam:

- Steam Store API.
- Steam Reviews API.
- SteamSpy API.

### Formato dos dados

Os dados sao retornados principalmente em formato JSON.

### Principais variaveis utilizadas

- Nome do jogo.
- Quantidade de reviews.
- Texto das analises.
- Avaliacao positiva e negativa.
- Tempo de jogo.
- Frequencia de palavras.
- Categorias de topicos.

### Volume esperado

Dependendo do jogo pesquisado, a aplicacao pode processar centenas ou milhares de reviews.

### Observacoes sobre qualidade dos dados

Os dados podem apresentar:

- Reviews duplicadas.
- Textos curtos ou irrelevantes.
- Linguagens diferentes.
- Uso excessivo de girias.
- Ironias dificeis de interpretar automaticamente.

Mesmo com essas limitacoes, a base apresenta valor significativo para analise comportamental e identificacao de tendencias.

## 5. Arquitetura proposta

A arquitetura do sistema foi dividida em frontend e backend.

### Fluxo da aplicacao

- O usuario pesquisa um jogo no frontend.
- O frontend envia uma requisicao para o backend Flask.
- O backend consulta as APIs da Steam.
- Os dados recebidos passam por tratamento e analise textual.
- Os resultados sao organizados em metricas e indicadores.
- O frontend exibe graficos, rankings e analises.

### Tecnologias utilizadas

**Frontend**

- ReactJS.
- CSS.
- JavaScript.

**Backend**

- Python.
- Flask.
- Flask-CORS.
- Requests.
- SpaCy.

### Estrutura simplificada

Usuario -> Frontend React -> Backend Flask -> APIs da Steam -> Processamento -> Resultado visual

## 6. Metodologia

O projeto utiliza principalmente a metodologia CRISP-DM (Cross Industry Standard Process for Data Mining), aplicada junto de tecnicas de analise exploratoria de dados (EDA), processamento de linguagem natural (NLP) e classificacao textual.

A escolha do CRISP-DM ocorreu porque o projeto segue um fluxo muito proximo das etapas classicas dessa metodologia, comecando pelo entendimento do problema ate a entrega dos resultados analisados no frontend.

A aplicacao segue um fluxo dividido em etapas:

- Coleta de dados atraves das APIs da Steam.
- Limpeza e preparacao das reviews.
- Processamento textual utilizando SpaCy.
- Separacao das frases por sentimento.
- Classificacao automatica em topicos.
- Extracao de palavras-chave relevantes.
- Organizacao dos resultados para visualizacao no frontend.

Além disso, o sistema utiliza uma abordagem hibrida de analise, combinando:

- Regras manuais baseadas em palavras-chave.
- Tecnicas de NLP.
- Filtragem de relevancia.
- Deduplicacao de frases semelhantes.

Futuramente, a metodologia sera expandida com modelos de inteligencia artificial capazes de identificar reviews uteis e interpretar automaticamente o significado das analises dos usuarios.

### 6.1 Entendimento do negocio

O problema identificado foi a dificuldade de interpretar grandes quantidades de reviews em plataformas digitais. A solucao auxilia jogadores a entender rapidamente os principais pontos comentados sobre um jogo.

### 6.2 Entendimento dos dados

Os dados coletados possuem natureza textual e semiestruturada. Foi necessario compreender:

- Estrutura das APIs.
- Campos relevantes.
- Quantidade de reviews.
- Limitacoes de idioma.
- Problemas de inconsistência textual.

### 6.3 Preparacao dos dados

Durante o tratamento dos dados foram realizadas:

- Remocao de caracteres especiais.
- Padronizacao textual.
- Filtragem de palavras irrelevantes.
- Limpeza de duplicatas.
- Organizacao dos topicos.

Tambem foram utilizadas tecnicas de NLP com a biblioteca SpaCy.

### 6.4 Modelagem e analise

A aplicacao realiza diferentes tipos de analise:

**Frequencia de palavras**

Identificacao das palavras mais utilizadas nas reviews.

**Analise de topicos**

Classificacao automatica de temas recorrentes, como:

- Bugs e crashes.
- Desempenho.
- Gameplay.
- Historia.
- Preco.
- Servidores.
- Graficos.

**Analise de polaridade**

Separacao entre opinioes positivas e negativas.

**Indicadores**

Geracao de metricas relacionadas a qualidade percebida do jogo.

### 6.5 Avaliacao

Os resultados obtidos mostraram que a aplicacao consegue identificar corretamente tendencias gerais nas reviews. Os topicos mais frequentes normalmente refletem os principais problemas ou qualidades apontados pela comunidade. A analise textual ainda possui limitacoes relacionadas a sarcasmo, contexto e linguagem informal.

### 6.6 Implantacao

A aplicacao foi desenvolvida em arquitetura web, separando frontend e backend. O frontend foi construido em React para exibir os resultados das analises de forma visual e dinamica, enquanto o backend em Flask e responsavel pela coleta, processamento e analise das reviews.

Durante o desenvolvimento, o sistema foi executado localmente para testes e validacoes das funcionalidades. A comunicacao entre frontend e backend ocorre atraves de requisicoes HTTP, permitindo que os dados processados sejam enviados em formato JSON para visualizacao na interface.

## 7. Implementacao pratica

O projeto foi dividido em modulos organizados.

### Estrutura do frontend

- SearchBox.jsx
- GameCard.jsx
- Results.jsx
- ReviewAnalysis.jsx
- SelectedGame.jsx

### Estrutura do backend

O backend centraliza:

- Coleta de dados.
- Comunicacao com APIs.
- Processamento textual.
- Classificacao de topicos.
- Geracao de metricas.

### Principais bibliotecas utilizadas

- Flask.
- Requests.
- SpaCy.
- React.
- Vite.

## 8. Resultados

A aplicacao conseguiu:

- Coletar reviews automaticamente.
- Processar grandes volumes de texto.
- Identificar padroes recorrentes.
- Gerar indicadores relevantes.
- Exibir resultados de forma visual.

Os resultados demonstraram que tecnicas de analise textual podem auxiliar significativamente na interpretacao de opinioes em plataformas digitais.

## 9. Conclusao

O projeto Golden Reviews demonstrou a aplicacao pratica de conceitos de Big Data, processamento textual e analise de dados utilizando Python. A solucao desenvolvida conseguiu transformar grandes volumes de reviews em informacoes organizadas e uteis para os usuarios.

Além da analise de dados, o projeto tambem proporcionou experiencia pratica com APIs, desenvolvimento web, NLP e integracao entre frontend e backend. O trabalho evidencia como tecnicas de analise de dados podem gerar valor real em aplicacoes modernas voltadas para entretenimento digital.

## 10. Referencias

- Documentacao da Steam API.
- Documentacao Flask.
- Documentacao React.
- Documentacao SpaCy.
- Python Software Foundation.

## 11. Mudancas no fluxo atual (registro separado)

Este topico documenta o que mudou no fluxo atual em relacao a arquitetura original. Serve como historico para entender as alteracoes feitas.

### Backend

- Migracao de Flask para FastAPI.
- Inclusao de cache persistente em SQLite com WAL.
- Endpoint de analise assincrona com polling via GET /analyze/{game_name}.
- Processamento pesado executado em thread separada para evitar bloqueio do event loop.
- Respostas de status: 202 (processando), 200 (concluido), 500 (erro).

### Frontend

- Polling a cada 2s no endpoint /analyze/{game_name} ate status 200.
- Reestruturacao do payload de resposta (summary, highlights, topics, metadata).
- Ajustes de layout na pagina de analise para refletir o novo payload.

### Utilitarios e paginas extras

- Pagina dedicada para analise de topicos via topics.html.
- Pagina dedicada para SteamSpy (games.html) usando request=all e ordenacao por popularidade nas ultimas 2 semanas.
- Proxy no Vite para acessar SteamSpy no ambiente de desenvolvimento.
