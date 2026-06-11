# Análise do train_offline.py 

## Resumo Geral: 

O script `train_offline.py` está configurado com poucas stopwords e está atualmente lendo uma amostragem de 20.000 reviews de um arquivo CSV. 

O Bertopic está configurado para usar o modelo 'paraphrase-MiniLM-L6-v2' e está com o parâmetro multilingual definido como True, o que pode ser desncessário se o parâmetro embedding_model estiver configurado para um modelo específico. Mais isso não é um erro grave porque o modelo 'paraphrase-MiniLM-L6-v2' é um modelo multilingue, então o parâmetro multilingual=True não causará problemas, mas é redundante. 

O parâmetro nr_topics está definido como auto, o que pode ser instável e gerar amostras diferentes a cada treinamento, porém testes com outros números deram resultados ruins por algum motivo desconhecido. Recomendado manter como está por enquanto .

 O parametro min_topic_size=15, é considerado baixo, porém testes com outros números também deram resultados piores, mais testes são recomendados para ter certeza disso, pois não foi avaliado corretamente. 

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