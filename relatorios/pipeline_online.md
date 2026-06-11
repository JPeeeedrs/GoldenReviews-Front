# Análise do pipeline_online.py

## Resumo Geral:

No script foi encontrado um erro grave no cálculo do score geral, onde ele estava pegando somente a primeira sentença de um grupo de sentenças da mesma review e jogando todo o resto fora. Foi aplicado o concerto fazendo a média de todas as sentenças da review e depois aplicando os pesos. Isso impede que por exemplo que uma das sentenças do usuário seja positva e tenha várias outras muito negativas que vão ser totalmente desconsideradas. Isso possivelmente estava prejudicando muito a nota geral do jogo feita pelo sistema . 

### Código do cálculo do score geral corrigido:

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

Além disso foi aplicada a mesma lógica no cálculo dos tópicos. Agora, para dar a nota geral dos tópicos ele também faz a média das frases dos jogadores, aplica os pesos e calcula cada tópico. Isso torna a abordagem mais refinida e precisa. 

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
Repara no 'mentions': g['review_id'].nunique()

O código "topic_info = self.topic_model.get_topic_info()" foi comentado pois não estava sendo utilizado. 

Foi adicionado um comentário aproximadamente na linha 161 a partir do "for _, row in agg_df.iterrows()"  explicando que o sistema está definindo o nome dos tópicos, pegando as palavras mais frequentes de cada tópico e utilizando elas para criar o nome. E assim que ele tava fazendo antes ! Só uma curiosidade ! 

A métrica definida foi 3.0 para separar tópicos positivos de negativos, mas talvez seja interessante analisar uma possível mudança do 3.0 para algo como 2.5, já que muitas sentenças negativas com nota um pouco abaixo de 3.0 são mais parecidas com sentenças neutras ou até positivas . 

DICA: No payload exite o campo "keywords" que pode ser usado para criar uma nuvem de palavras de cada tópico, mostrando as palavras mais frequentes de cada tópico. Mais isso não é prioridade agora . 

Mudança do modelo de sentimento para o **BERTweet** baseado no BERTimbau, que é um modelo pré-treinado em tweets brasileiros. Ele é capaz de entender gírias, ironia e caixa alta, o que o torna mais adequado para analisar reviews de jogos, onde os usuários costumam usar uma linguagem mais informal e expressiva. A troca do modelo melhorou significativamente a precisão do sentimento e das notas geradas pelos tópicos, frases, e nota geral. Talvez retirar o produto escalar nessa abordagem pode deixar ele ainda mais incisivo, porém isso tem que ser analisado pois sem o produto escalar ele pode dar uma notas muito altas ou baixas demais. A velocidade do modelo também melhorou e a causa é o fato do BERTweet trabalhar com uma matriz menor e usar no máximo 128 tokens, enquanto o modelo anterior usava 512 tokens. Isso torna o processamento mais rápido, principalmente porque estamos dividindo em frases. 

Códigos : 

## Função __init__ modificada : 

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
## Função __extract_continuous_score__ modificada : 

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