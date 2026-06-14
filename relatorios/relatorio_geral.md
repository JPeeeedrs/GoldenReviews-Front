# RELATÓRIO GERAL CONSOLIDADO

## Introdução

Este relatório apresenta a estrutura lógica do projeto e documenta as mudanças e análises feitas durante o desenvolvimento. Também explica de forma clara o funcionamento do código, as decisões tomadas e os resultados obtidos. Inclui uma análise geral e uma análise mais específica dos principais scripts utilizados.

## Script analisados:

- `train_offline.py`
- `train_online.py`
- `app.py`
- `steamApi.js`
- `llm_summary.py`
- `debug_cache.py`

## train_offline.py

O script `train_offline.py` é responsável por realizar o treinamento do modelo de tópicos BERTopic através de um dataset em formato CSV. Está configurado para usar o modelo de embedding 'paraphrase-MiniLM-L6-v2'. O script lê uma amostragem de 20.000 reviews, processa os textos e treina o modelo de tópicos, que é então salvo para uso posterior. Possui uma lista de stopwords reduzidas e o parâmetro `nr_topics` está definido como "auto", o que pode levar a resultados instáveis, mas testes com outros valores deram resultados piores. O parâmetro `min_topic_size` está definido como 15, o que é considerado baixo, mas o teste com outros valores também não apresentou resultados esperados.

```python

topic_model = BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer_model,
        language="multilingual",
        nr_topics="auto",
        min_topic_size=15,
        verbose=True
    )

```

## pipeline_online.py

O script `pipeline_online.py` é o responsável por fazer o processamento sob demanda das reviews extraídas pela API e alocar as sentenças em tópicos com sentimento anexado.

Um erro importante foi corrigido nas funções responsáveis por calcular as notas dos tópicos e a nota geral do jogo. O sistema usava uma função que descartava sentenças que pertenciam ao mesmo id exceto a primeira. Isso causava perda de contexto e informações referentes a cada review/jogador. A correção aplicada faz a média de todas as sentenças de um mesmo id antes de prosseguir para as próximas etapas, o que torna a abordagem mais refinada e precisa. Foi aplicado tanto na nota geral quanto na nota dos tópicos.

### Nota geral corrigida:

```python

if not df.empty:
            df_por_review = df.groupby('review_id').agg({
                'review_score': 'mean',
                'weight': 'first'
            })
            df_por_review['weighted_score'] = df_por_review['review_score'] * df_por_review['weight']
            overall_score = df_por_review['weighted_score'].sum() / df_por_review['weight'].sum() if df_por_review['weight'].sum() > 0 else 0
        else:
            overall_score = 0

```

### Nota dos tópicos corrigida:

```python

        # Aplicando a abordagem da média dos jogadores para a nota dos tópicos também .
        # O código abaixo tá basicamente usando o Pandas para criar uma "nova" tabela onde todas as frases de uma review/id são fundidas em uma média.
        df_topico_por_review = df_valid.groupby(['review_id', 'topic_id']).agg({
            'review_score': 'mean',
            'weight': 'first'
        }).reset_index()

        # Aqui ta calculando a nota ponderada com os pesos(tempo de jogo) dessa tabela temporária com as notas unificadas
        df_topico_por_review['weighted_score'] = df_topico_por_review['review_score'] * df_topico_por_review['weight']

        # Aqui ele ta fazendo a média que da o resultado da nota do tópico
        agg_df = df_topico_por_review.groupby('topic_id').apply(
            lambda g: pd.Series({
                'score': g['weighted_score'].sum() / g['weight'].sum() if g['weight'].sum() > 0 else g['review_score'].mean(),
                'mentions': len(g)  # Como cada linha já é um jogador único, len(g) é o total de pessoas!
            })
        ).reset_index()

```

Na função `_aggregate_results` existe a lógica que define o nome dos tópicos, pegando as palavras mais frequentes de cada tópico e utilizando elas para criar o nome. Essa lógica foi mantida, mas uma possível mudança poderia melhorar significativamente a qualidade dos nomes dos tópicos.

### Trecho do código onde é definido o nome dos tópicos:

```python

# É aqui que o sistema da definindo o nome dos tópicos, pegando as palavras mais frequentes de cada tópico e utilizando elas para criar um nome mais amigável. Bom saber!
        for _, row in agg_df.iterrows():
            tid = int(row['topic_id'])
            score = float(row['score'])
            mentions = int(row['mentions'])
            is_positive_topic = score >= 3.0

            words_freq = self.topic_model.get_topic(tid)
            keywords = [w[0] for w in words_freq[:3]] if words_freq else [f"Topico {tid}"]


            df_topic_all = df_valid[df_valid['topic_id'] == tid]

            if is_positive_topic:
                df_topic_filtered = df_topic_all[df_topic_all['review_score'] >= 3.0] \
                    .sort_values(by='review_score', ascending=False) # Analisar possível mudança do 3.0 para algo como 2.5 ?
            else:
                df_topic_filtered = df_topic_all[df_topic_all['review_score'] < 3.0] \
                    .sort_values(by='review_score', ascending=True)

            if df_topic_filtered.empty:
                quotes = df_topic_all['sentence'].head(2).tolist()
            else:
                quotes = df_topic_filtered['sentence'].head(2).tolist()

            topic_name = " | ".join([k.capitalize() for k in keywords[:3]])

            topic_payload = {
                "topic": topic_name,
                "topic_id": tid,
                "mentions": mentions,
                "score": round(score, 1),
                "keywords": keywords, # pode ser usado para nuvem de palavras
                "quotes": quotes
            }

            if is_positive_topic:
                positive_topics.append(topic_payload)
            else:
                negative_topics.append(topic_payload)

```

O código usa métricas para separar tópicos positivos de negativos, e a métrica definida foi 3.0. Contudo seria interessante analisar uma possível mudança do 3.0 para valores inferiores(2.5 por exemplo), para refletir melhor o sentimento dos jogadores .

No topic_payload existe o campo "keywords" que mostra as palavras mais frequentes de cada tópico. Isso pode ser usado para criar gráficos e elementos visuais como nuvem de palavras.

### Mudanças importantes:

- O modelo de sentimento principal _tabularisai/multilingual-sentiment-analysis_ foi substituido pelo **BERTweet** baseado no BERTimbau, que é um modelo pré-treinado em tweets brasileiros. Ele é capaz de entender gírias, ironia e caixa alta, o que o torna mais adequado para analisar reviews de jogos, onde os usuários costumam usar uma linguagem mais informal e expressiva. A troca do modelo melhorou significativamente a precisão do sentimento e das notas geradas pelos tópicos, frases, e nota geral. Talvez retirar o produto escalar nessa abordagem pode deixar ele ainda mais incisivo, porém isso tem que ser analisado pois sem o produto escalar ele pode dar uma notas mais polarizadas. A velocidade do modelo também melhorou e a causa é o fato do BERTweet trabalhar com uma matriz menor e usar no máximo 128 tokens, enquanto o modelo anterior usava 512 tokens. Isso torna o processamento mais rápido, principalmente porque estamos dividindo em frases.

#### Códigos relacionados a mudança do modelo de sentimento:

```python

  def __init__(self, bertopic_model_path: str):
        print("Iniciando carregamento dos modelos na memória...")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Adicionando o modelo BERTweet baseado no BERTimbau
        self.sentiment_model_name = "pysentimiento/bertweet-pt-sentiment"

        self.sentiment_tokenizer = AutoTokenizer.from_pretrained(self.sentiment_model_name)
        self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(self.sentiment_model_name)
        self.sentiment_model.eval()
        self.sentiment_model.to(self.device)


        # O modelo retorna POS, NEG, NEU. Nós lemos a ordem exata da rede neural
        # e criamos os multiplicadores: NEG=1.0, NEU=3.0, POS=5.0
        label_to_score = {"NEG": 1.0, "NEU": 3.0, "POS": 5.0}

        weights_list = []
        for i in range(len(self.sentiment_model.config.id2label)):
            label_name = self.sentiment_model.config.id2label[i]
            weights_list.append(label_to_score.get(label_name, 3.0))

        self.score_weights = torch.tensor(weights_list).to(self.device)

        self.embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.topic_model = BERTopic.load(bertopic_model_path, embedding_model=self.embedding_model)


```

#### Produto escalar :

```python

    def extract_continuous_score(self, text: str) -> float:
        inputs = self.sentiment_tokenizer(text, return_tensors='pt', truncation=True, max_length=128).to(self.device)

        with torch.no_grad():
            outputs = self.sentiment_model(**inputs)

        probs = F.softmax(outputs.logits, dim=-1).squeeze()

        # Produto escalar
        # Mistura as porcentagens de POS/NEG/NEU com os pesos (1, 3 e 5) para gerar a nota quebrada
        score = torch.dot(probs, self.score_weights).item()
        return score

```

## app.py

O script `app.py` é o backend do sistema, responsável por lidar com as requisições, extrair as reviews usando a API da Steam, processar os dados e retornar os resultados para o frontend. O script recebe o ID do jogo, extrai as reviews, processa os dados usando o pipeline online e retorna um resumo em linguagem natural gerado por uma LLM (Language Model) ou um resumo estatístico padrão caso a LLM não esteja disponível. O código também inclui uma trava de segurança para limitar a quantidade máxima de reviews processadas a 1000, garantindo que o sistema não seja sobrecarregado.

As configurações do CORS estão totalmente liberadas para facilitar o desenvolvimento, mas devem ser ajustadas para a produção, garantindo assim a segurança do sistema. O parâmetro de filtro para as reviews está definido como "recent", o que pode resultar em uma amostragem desbalanceada, mas mudar para "all" pode trazer reviews muito antigas que não refletem a qualidade atual do jogo.

### Código do resumo estatístico padrão (Plano B):

```python

#FIX: Melhorando a lógica da LLM . Se não tiver chave api ou não funcionar ele vai para o plano B que usa as informações da própria ia interna .
        print(f"[Worker] Gerando resumo em linguagem natural via LLM...")

        try:
            texto_resumo = gerar_resumo(analysis_result)
        except Exception as llm_err:
            print(f"[Worker] LLM indisponível ({llm_err}). Gerando resumo estatístico padrão...")

            score_final = analysis_result["summary"].get("overall_score", 0.0)
            total_revs = analysis_result["summary"].get("reviews_analyzed", 0)
            pct_pos = analysis_result["summary"].get("positive_percentage", 0)

            texto_resumo = (
                f"Análise baseada em {total_revs} reviews recentes da Steam. "
                f"O jogo apresenta um índice de aprovação de {pct_pos}% pelos usuários, "
                f"com uma nota de sentimento calculada em {score_final}/5.0 baseada nos tópicos identificados."
            )

        analysis_result["summary"]["ai_text_summary"] = texto_resumo

```

## Outras alterações importantes:

- A quantidade de reviews padrão também foi alterada nos scripts `steamApi.js` e `App.jsx` para garantir consistência em todo o sistema.

- O input onde o usuário poderia escolher a quantidade de reviews processadas foi removido do `App.jsx` para evitar desbalanceamento no banco de dados e dar mais controle para o sistema.

- O tempo do polling no `App.jsx` foi alterado para 10 segundos, o que é mais do que suficiente para a maioria dos casos e ajuda a reduzir a carga no servidor. Mudanças para outros valores podem ser testadas conforme necessário.

- O script `llm_summary.py` foi refatorado para permitir que o sistema funcione sem uma chave de API e acione o Plano B automaticamente, sem causar falhas no backend. O código agora inclui um bloco try-catch que tenta gerar o resumo usando a LLM, e se ocorrer um erro (como falta de chave de API ou falha na LLM), ele gera um resumo estatístico padrão usando as informações disponíveis na análise.

- O script `debug_cache.py` foi criado para extrair informações do cache SQLite e gerar um JSON simples para análise do desempenho do modelo. Quando executado, ele solicita o ID do jogo e, se o jogo estiver presente no banco de dados, cria um arquivo JSON com a análise.
