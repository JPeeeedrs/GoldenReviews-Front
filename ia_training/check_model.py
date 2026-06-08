from bertopic import BERTopic

def auditar_modelo():
    print("⏳ Carregando o modelo treinado...")
    # Carrega a pasta salva pelo train_offline
    topic_model = BERTopic.load("steam_bertopic_model")
    
    # Extrai a tabela de informações dos tópicos
    df_topics = topic_model.get_topic_info()
    
    # O tópico -1 é sempre o Ruído/Outlier
    num_topicos_reais = len(df_topics) - 1
    
    print("\n" + "="*40)
    print("📊 DIAGNÓSTICO DO MODELO BERTopic")
    print("="*40)
    print(f"Total de Tópicos Úteis Criados: {num_topicos_reais}")
    
    print("\n🏆 TOP 15 TÓPICOS MAIS FREQUENTES:")
    # Mostra o ID, a quantidade de frases e as principais palavras-chave
    print(df_topics[['Topic', 'Count', 'Name']].head(16).to_string(index=False))

if __name__ == "__main__":
    auditar_modelo()