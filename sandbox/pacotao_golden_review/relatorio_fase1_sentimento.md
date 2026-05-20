# Relatório de Execução: Fase 1 (Classificação de Sentimentos)

## 📌 Resumo do que foi feito

Durante esta etapa, completamos a primeira metade do **Pipeline Duplo de NLP** para o projeto Golden Reviews. Abandonamos a abordagem baseada em regras (spaCy) e passamos a utilizar IA baseada em Transformers para analisar o sentimento granular das avaliações da Steam.

### 1. Amostragem e Limpeza (Safe Data Cleaning)

- Extraímos amostras balanceadas de avaliações em Português-BR para diversos gêneros (Ação, RPG, Horror, etc).
- Limpamos ruídos que poderiam atrapalhar o modelo (ASCII Art, URLs, reviews muito curtas e repetições excessivas de pontuação).
- Mantivemos a pontuação nativa intacta, algo fundamental para o processamento de linguagem baseada em contexto.

### 2. Segmentação de Sentenças

- Utilizamos o módulo `sent_tokenize` da biblioteca NLTK para transformar blocos de texto longo em frases unitárias avaliáveis com maior precisão.
- Criamos e exportamos um Corpus massivo com foco em ML armazenando cerca de **190.000 frases**.
- Formato de salvamento adotado: `.parquet` (Engine `fastparquet`), focado em alta compactação e velocidade de leitura para ferramentas de ML.

### 3. Modelo Escolhido

- Selecionado o modelo `pysentimiento/bertweet-pt-sentiment` (BERTabaporu), focado em redes sociais e PT-BR informal, ideal para lidar com a linguagem gamer de reviews.
- Adicionada a dependência `emoji==0.6.0` para que o modelo entenda os emojis contidos nas avaliações.

### 4. Processamento no Google Colab (Batching na GPU)

- Devido à limitação do método nativo `.apply()` do Pandas em GPUs (enviar uma frase de cada vez é ineficiente), refatoramos o código para envio em Lote (_Batching_).
- O dataset inteiro de sentenças foi processado pela T4 GPU no Google Colab usando `batch_size=128`.
- O resultado foi retornado e inserido no ecossistema (`steam_reviews_sentences_COM_SENTIMENTO.parquet`).

### 5. Curiosidade: Viés de Domínio

- Observamos que palavras como _“horripilante”_ ou _“assustador”_ são lidas pelo modelo como contexto `NEG` (Negativo) devido ao seu treinamento genérico.
- Como esperado na arquitetura do Golden Reviews, **este viés não é um problema**. A correção interpretativa será feita usando o BERTopic e rotulagem manual de Tópicos (a inteligência saberá quando "assustador" é um elogio ao ver o gênero do jogo).

### 6. Resultados Preliminares: Sentimentos e Clusterização (BERTopic)

- **Distribuição de Sentimentos:** A análise revelou que **55.1%** das frases foram classificadas como Neutras (`NEU`), enquanto **28.8%** são Positivas (`POS`) e **16.0%** Negativas (`NEG`). Este alto volume de frases neutras é esperado e positivo, pois demonstra que o modelo isolou corretamente constatações de fatos ("Comprei na promoção", "O jogo é de tiro") de opiniões reais.
- **Início do BERTopic:** Testamos a clusterização primeiramente nas frases `NEG` para identificar queixas comuns.
- **Tópicos Identificados:** O modelo encontrou reclamações válidas e bem definidas, como "abandono do jogo" (Tópico 0), "preço/reais" (Tópico 1), "história rasas" (Tópico 2) e "multiplayer morto" (Tópico 12).
- **Desafio com Ruído:** Aproximadamente **48.9%** das sentenças caíram no Tópico -1 (Ruído/Outliers). Isso ocorre devido ao comportamento rigoroso do algoritmo HDBSCAN utilizado pelo BERTopic.

## 7. O Desafio da Clusterização (BERTopic) e Redução de Ruído

Iniciamos a Modelagem de Tópicos focando nas sentenças com a tag de sentimento "NEG". Confirmamos a eficácia do uso de sentenças isoladas eliminando ~55% da massa de dados identificada como puramente descritiva ("NEU").
A qualidade dos tópicos gerados foi altíssima (extraindo problemas como bugs, quedas de FPS e críticas à história). O maior gargalo foi o rigor estatístico do algoritmo HDBSCAN, que relegou ~49% do material ao Tópico -1 (Outliers).

Ações mitigadoras executadas:

- **Limpeza Textual:** Implementação customizada de _Stop Words_ iterativas via CountVectorizer para despoluir clusters de jargões inócuos como "jogo", "pra", "jogar".
- **Resgate Matemático:** Utilização da função agressiva "reduce_outliers(strategy='probabilities', threshold=0.05)", responsável por resgatar milhares de frases para clusters saudáveis.

**Ação Pendente (Iteração Atualizada):**
Amostragens manuais mostraram a existência de frases vitais soltas no ruído. Originalmente estipulamos aplicar Zeroshot Topic Modeling, mas mudamos a rota para uma abordagem puramente baseada em Similaridade Espacial de Alta Confiança.

## 8. Otimização Espacial Absoluta (Descarte do Zero-Shot)

Apesar do planejamento inicial apontar para a utilização de **Zeroshot Topic Modeling (NLI)** para forçar a classificação do ruído, nossa bateria de testes revelou uma abordagem muito superior, natural e orgânica utilizando os próprios algoritmos da pipeline.

Concluímos que forçar categorias através de NLI (Zero-shot) inibiria o modelo de descobrir sub-nichos altamente relevantes por conta própria, como de fato ele descobriu ao relaxarmos as regras: grupos isolados reclamando especificamente de "bola/gols" (FIFA), "carros/volantes" (jogos de corrida), barreiras de idioma, e etc.

**A Nova e Definitiva Estratégia Adotada:**

1. **Afrouxamento do Agrupador:** Tornamos os parâmetros do UMAP (`n_neighbors=20`, `min_dist=0.0`) e HDBSCAN (`min_cluster_size=10`, `min_samples=5`) matematicamente mais permissivos para encorajar a formação orgânica de grupos menores.
2. **Resgate por Similaridade Vetorial:** Substituímos a redução de outliers anterior (via previsões estritas) por um resgate agressivo através de coordenadas no espaço hiper-dimensional, utilizando `strategy="embeddings"` com `threshold=0.15`.

**Resultados Obtidos e Auditados:**

- O Ruído (Tópico -1) foi **totalmente zerado (caiu de ~36.5% para 0.0%)**.
- Todas as sentenças residuais foram alocadas de volta validamente, realocadas por estarem mais próximas das massas gravitacionais originais.
- A auditoria da "Cauda Longa" (menores tópicos gerados do dataset) assustou positivamente indicando extrema coesão: o modelo não criou "lixeiras", mas agrupou reclamações perfeitamente afuniladas (Pay-to-win, promessas falsas de free-to-play, gráficos ultrapassados e erros diretos com atualizações).

## 🚀 Próximos Passos (Fase Integradora - O Backend)

1. **Mapeamento Oficial:** Escolher, consolidar e nomear de forma limpa os IDs dos tópicos gerados (usando como base as prioridades como Bugs/Hardware, Tradução, Preço, etc) para servirem como as "Tags Alerta" na UI final.
2. **Exportação ML (Fim da Etapa Offline):** Finalizar a amarração, salvar e exportar os arquivos do modelo BERTopic treinado localmente (`.safetensors` ou similar) para consumo ágil em produção. Em ambiente Online, nós **não** rodaremos `.fit()`, apenas `.transform()`.
3. **Refatoração da Fase 2 (Online):** Refatorar o backend principal em Flask (`app.py`), substituindo inteiramente a lógica léxica do spaCy pela arquitetura híbrida assíncrona (usando filas, jobs, status code HTTP 202) e plugar definitivamente nossos cérebros de predição (Sentimento + Tópico).
