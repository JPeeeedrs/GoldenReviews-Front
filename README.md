<!-- Melhorar e atualizar o README.md para refletir as mudanças recentes no projeto. Adicionar as imagens da estrutura que defini ou explicação textual -->


# GOLDEN REVIEWS — Análise Inteligente de Reviews da Steam

O **Golden Reviews** é uma aplicação Fullstack (React + FastAPI) que automatiza a coleta, o cruzamento e a interpretação em larga escala de comentários de jogadores publicados na loja da Steam.

O sistema resolve o problema da desinformação na hora da compra: em vez de forçar o usuário a ler paredes de texto de milhares de pessoas, a inteligência artificial segmenta os dados para extrair quais são as reais dores e elos fortes do jogo (ex: "Bugs constantes", "Trilha sonora impecável", "Problemas de servidor").

---

## 🧠 Arquitetura de Machine Learning (Híbrida)

Nós evoluímos o projeto de uma simples identificação léxica (dicionários e validações fixas via spaCy) para um Pipeline Robusto de **Processamento de Linguagem Natural (NLP) Baseado em Aspectos (ABSA)** usando Transformers.

O projeto atual trabalha em duas Fases essenciais:

### 1. Fase Offline (Treinamento do Base)

O arquivo `train_offline.py` é responsável pelo aprendizado. Ele:

- Acessa grandes volumes históricos de análises da Steam.
- Segmenta os textos usando `nltk`.
- Gera representações textuais avançadas em Vetores usando `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Treina dinamicamente o agrupamento de Tópicos e Similaridades utilizando a biblioteca **BERTopic** (`.fit()`).
- Salva os neurônios do modelo treinado no disco local na pasta `steam_bertopic_model` (contendo `.safetensors`, `config.json`, etc.).

### 2. Fase Online (Inferência em Tempo Real)

O coração da nossa API é o FastAPI consumindo o `backend/pipeline_online.py`. Ele atende o painel React assim:

- **Catraca Automática:** Faz o scrapping dinâmico sobre um ID de Jogo requisitado e valida no `SQLite`.
- **Score Duplo:** Calcula um score "contínuo" ponderado utilizando classificação probabilística com o modelo pretreinado `tabularisai/multilingual-sentiment-analysis`.
- **Inferência Veloz:** Quebra as reviews e, por meio da função `.transform()` do `BERTopic`, distribui essas matrizes semânticas em tempo real pelas caixas conceituais aprendidas previamente. Tudo usando agregação robusta em Pandas.
- **Assincronicidade:** A computação não barra o frontend. Respostas rodam em `BackgroundTasks` via polling (HTTP 202) melhorando drasticamente a latência e a percepção de performance na Ui.

---

## 🚀 Como Executar o Projeto

**1. Ambiente Virtual (Python)**

```bash
# Ativar venv e instalar as libs necessárias
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**2. Subir o Backend (FastAPI)**

```bash
cd backend
python app.py
# Fica online em http://localhost:8000
```

**3. Subir o Frontend (React + Vite)**

```bash
# Na raiz do projeto, instale os pacotes npm, se necessário
npm install
npm run dev
```

---

## 📅 O Que Fizemos Hoje (27 de Maio de 2026) - Atualizações e Bugfixes

Hoje lidamos com a transição da modelagem local (Jupyter) para a **Injeção Estrutural na API de produção**.

Focamos muito em deixar a arquitetura pronta, modular e com contratos de dados bem definidos. **Se você está assumindo a parte de Banco de Dados (SQLite)** para profissionalizar o cache e a persistência, leia esta seção com atenção, pois ela dita como o Backend cospe os dados para o seu banco e para o Frontend.

### 1. Auditoria e Contrato JSON do Pipeline Online

Reestruturamos o arquivo `pipeline_online.py` para garantir que o output de IA (`ABSAPipeline`) devolva **estritamente** um JSON limpo, sem lixo. O colega do Backend/SQLite deve esperar que a função `process_reviews` devolva um dicionário neste exato formato:

```json
{
  "game": { "name": "Nome do Jogo" },
  "summary": { "overall_score": 4.6, "reviews_analyzed": 1250 },
  "topics": {
    "positive": [
      {
        "topic": "graficos e arte",
        "mentions": 53,
        "score": 4.5,
        "keywords": ["lindo", "arte", "visual"],
        "quotes": ["Exemplo"]
      }
    ],
    "negative": [
      {
        "topic": "bugs e crash",
        "mentions": 12,
        "score": 1.2,
        "keywords": ["fechando", "trava", "crash"],
        "quotes": ["Exemplo"]
      }
    ]
  },
  "metadata": {
    "processing_time_seconds": 2.5,
    "model_version": "v2.0-transform-only"
  }
}
```

_💡 **Nota para o dev do SQLite:** Esse é o JSON que atualmente estamos serializando (`json.dumps`) para salvar na coluna `data` da tabela `game_cache`._

### 2. O Fluxo de Assincronicidade Atual (Frontend -> BD -> Pipeline)

Hoje o `app.py` integra banco de dados e ML num esquema de Fila/Background Task (Polling HTTP 202):

1. O React bate em `/reviews?appid=123`.
2. O Backend confere no SQlite (`game_cache`). Se não tem, ele insere o Jogo com status `processing` e devolve um HTTP 202 pro front.
3. Em Background, ele aciona a Steam, baixa as reviews, roda a Pipeline Pesada (`pipeline_online.py`) e então **faz um UPDATE no SQLite** pra status `completed`, jogando o JSON de resultado dentro do Blob/Text `data` do banco.
4. O React continua fazendo _Polling_ até receber status 200 com os dados lidos do seu banco.
   Sua missão com o SQLite pode expandir ou otimizar essa tabela (que hoje só tem `appid`, `status`, `data` e `updated_at`).

### 3. Melhorias no Motor de Inteligência Artificial

- **Correção da Matemática Tensorial:** Subimos as validações preditivas do HuggingFace com PyTorch de forma oficial (`.to(device)` e `model.eval()`). Se a máquina tiver GPU (CUDA), as predições de sentimento agora farão uso dela.
- **Limpeza de Bias no Overall Score:** Ajustamos a média do classificador estelar. O score agora volta a ser calculado por Review Única e não "por frase fatiada", garantindo que usuários prolixos (que escrevem testões) não distorçam a nota geral do jogo artificialmente.

### 🚨 4. Hotfix Crítico: O Desalinhamento Semântico do BERTopic (Bug de Offset do Array)

**O Problema que rolou hoje de tarde:** No painel React, percebemos que as _Tags_ estavam agrupando frases erradas (Ex: Sentenças de _Palworld_ caindo no invólucro do tópico de _Life is Strange_).
**Por quê?** Nós herdamos um código de otimização antigo (um `[t - 1]`) usado quando aplicávamos o algoritmo punitivo HDBSCAN. Mas agora, nosso script `train_offline.py` treina da raiz e não precisa mais dessa compensação matricial. Se usássemos o `[t - 1]`, quebrávamos todo o índice pra trás.
**Solução final:** Revertemos as alterações de array dentro da rota `pipeline_online.py` para extrair nativamente os arrays puros com `topics, _ = self.topic_model.transform(sentences_to_infer)`! A UI agora voltou ao normal e a clusterização semântica está tinindo.
