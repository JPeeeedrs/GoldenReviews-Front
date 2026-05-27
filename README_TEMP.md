# GoldenReviews-Front

GOLDEN REVIEWS — Análise Inteligente de
Reviews da Steam
Trabalho Prático — Tópicos de Big Data em Python

1. Área e aplicação escolhidas
   O projeto desenvolvido está voltado para a área de análise de dados aplicada ao mercado de jogos
   digitais. A aplicação criada, chamada Golden Reviews, realiza a coleta e análise automática de reviews
   de jogos da plataforma Steam, utilizando Python no backend e React no frontend.
   A motivação do projeto surgiu da dificuldade dos usuários em interpretar milhares de análises
   presentes na Steam. Muitos jogos possuem uma enorme quantidade de reviews, tornando difícil
   identificar rapidamente os principais pontos positivos e negativos relatados pela comunidade.
   A solução proposta automatiza esse processo por meio de técnicas de processamento e análise textual,
   permitindo extrair tendências, tópicos recorrentes e indicadores relevantes sobre os jogos.
2. Objetivos
   Objetivo geral
   Desenvolver uma aplicação capaz de coletar, processar e analisar reviews da Steam, transformando
   grandes volumes de texto em informações organizadas e interpretáveis.
   Objetivos específicos
   Coletar reviews de jogos através da API da Steam;
   Processar textos utilizando Python;
   Identificar palavras e tópicos recorrentes;
   Separar aspectos positivos e negativos das análises;
   Exibir os resultados de forma visual e intuitiva;
   Facilitar a interpretação das opiniões dos jogadores.
   Perguntas de análise
   Quais são os principais problemas relatados pelos jogadores?
   Quais aspectos positivos aparecem com maior frequência?
   Existe predominância de reviews positivas ou negativas?
   Quais temas são mais comentados em determinados jogos?
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   1
3. Requisitos da aplicação
   Requisitos funcionais
   Buscar jogos da Steam através do nome;
   Coletar reviews utilizando APIs públicas;
   Processar textos automaticamente;
   Identificar tópicos relevantes;
   Exibir estatísticas e indicadores;
   Mostrar os jogos mais buscados;
   Permitir visualização dinâmica no frontend.
   Requisitos não funcionais
   Interface responsiva;
   Processamento eficiente de grandes quantidades de reviews;
   Integração entre frontend e backend;
   Organização modular do código;
   Facilidade de manutenção;
   Compatibilidade com diferentes navegadores.
4. Bases de dados
   Origem dos dados
   Os dados utilizados no projeto são obtidos principalmente através de APIs públicas relacionadas à
   Steam:
   Steam Store API;
   Steam Reviews API;
   SteamSpy API.
   Formato dos dados
   Os dados são retornados principalmente em formato JSON.
   Principais variáveis utilizadas
   Nome do jogo;
   Quantidade de reviews;
   Texto das análises;
   Avaliação positiva/negativa;
   Tempo de jogo;
   Frequência de palavras;
   Categorias de tópicos.
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   •
   2
   Volume esperado
   Dependendo do jogo pesquisado, a aplicação pode processar centenas ou milhares de reviews.
   Observações sobre qualidade dos dados
   Os dados podem apresentar:
   Reviews duplicadas;
   Textos curtos ou irrelevantes;
   Linguagens diferentes;
   Uso excessivo de gírias;
   Ironias difíceis de interpretar automaticamente.
   Mesmo com essas limitações, a base apresenta valor significativo para análise comportamental e
   identificação de tendências.
5. Arquitetura proposta
   A arquitetura do sistema foi dividida em frontend e backend.
   Fluxo da aplicação
   O usuário pesquisa um jogo no frontend;
   O frontend envia uma requisição para o backend Flask;
   O backend consulta as APIs da Steam;
   Os dados recebidos passam por tratamento e análise textual;
   Os resultados são organizados em métricas e indicadores;
   O frontend exibe gráficos, rankings e análises.
   Tecnologias utilizadas
   Frontend
   ReactJS;
   CSS;
   JavaScript.
   Backend
   Python;
   Flask;
   Flask-CORS;
   Requests;
   SpaCy.
   •
   •
   •
   •
   •
6.
7.
8.
9.
10.
11. •
    •
    •
    •
    •
    •
    •
    •
    3
    Estrutura simplificada
    Usuário → Frontend React → Backend Flask → APIs da Steam → Processamento → Resultado visual
12. Metodologia
    O projeto utiliza principalmente a metodologia CRISP-DM (Cross Industry Standard Process for Data
    Mining), aplicada junto de técnicas de análise exploratória de dados (EDA), processamento de
    linguagem natural (NLP) e classificação textual.
    A escolha do CRISP-DM ocorreu porque o projeto segue um fluxo muito próximo das etapas clássicas
    dessa metodologia, começando pelo entendimento do problema até a entrega dos resultados
    analisados no frontend.
    A aplicação segue um fluxo dividido em etapas:
    Coleta de dados através das APIs da Steam;
    Limpeza e preparação das reviews;
    Processamento textual utilizando SpaCy;
    Separação das frases por sentimento;
    Classificação automática em tópicos;
    Extração de palavras-chave relevantes;
    Organização dos resultados para visualização no frontend.
    Além disso, o sistema utiliza uma abordagem híbrida de análise, combinando:
    regras manuais baseadas em palavras-chave;
    técnicas de NLP;
    filtragem de relevância;
    deduplicação de frases semelhantes.
    Futuramente, a metodologia será expandida com modelos de inteligência artificial capazes de
    identificar reviews úteis e interpretar automaticamente o significado das análises dos usuários.
    6.1 Entendimento do negócio
    O problema identificado foi a dificuldade de interpretar grandes quantidades de reviews em
    plataformas digitais.
    A solução auxilia jogadores a entender rapidamente os principais pontos comentados sobre um jogo.
    6.2 Entendimento dos dados
    Os dados coletados possuem natureza textual e semiestruturada.
13.
14.
15.
16.
17.
18.
19. •
    •
    •
    •
    4
    Foi necessário compreender:
    Estrutura das APIs;
    Campos relevantes;
    Quantidade de reviews;
    Limitações de idioma;
    Problemas de inconsistência textual.
    6.3 Preparação dos dados
    Durante o tratamento dos dados foram realizadas:
    Remoção de caracteres especiais;
    Padronização textual;
    Filtragem de palavras irrelevantes;
    Limpeza de duplicatas;
    Organização dos tópicos.
    Também foram utilizadas técnicas de NLP com a biblioteca SpaCy.
    6.4 Modelagem e análise
    A aplicação realiza diferentes tipos de análise:
20. Frequência de palavras
    Identificação das palavras mais utilizadas nas reviews.
21. Análise de tópicos
    Classificação automática de temas recorrentes, como:
    Bugs e crashes;
    Desempenho;
    Gameplay;
    História;
    Preço;
    Servidores;
    Gráficos.
22. Análise de polaridade
    Separação entre opiniões positivas e negativas.
23. Indicadores
    Geração de métricas relacionadas à qualidade percebida do jogo.
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    5
    6.5 Avaliação
    Os resultados obtidos mostraram que a aplicação consegue identificar corretamente tendências gerais
    nas reviews.
    Os tópicos mais frequentes normalmente refletem os principais problemas ou qualidades apontados
    pela comunidade.
    A análise textual ainda possui limitações relacionadas a sarcasmo, contexto e linguagem informal.
    6.6 Implantação
    A aplicação foi desenvolvida em arquitetura web, separando frontend e backend.
    O frontend foi construído em React para exibir os resultados das análises de forma visual e dinâmica,
    enquanto o backend em Flask é responsável pela coleta, processamento e análise das reviews.
    Durante o desenvolvimento, o sistema foi executado localmente para testes e validações das
    funcionalidades.
    A comunicação entre frontend e backend ocorre através de requisições HTTP, permitindo que os dados
    processados sejam enviados em formato JSON para visualização na interface.
24. Implementação prática
    O projeto foi dividido em módulos organizados.
    Estrutura do frontend
    SearchBox.jsx;
    GameCard.jsx;
    Results.jsx;
    ReviewAnalysis.jsx;
    SelectedGame.jsx.
    Estrutura do backend
    O backend centraliza:
    Coleta de dados;
    Comunicação com APIs;
    Processamento textual;
    Classificação de tópicos;
    Geração de métricas.
    •
    •
    •
    •
    •
    •
    •
    •
    •
    •
    6
    Principais bibliotecas utilizadas
    Flask;
    Requests;
    SpaCy;
    React;
    Vite.
25. Resultados
    A aplicação conseguiu:
    Coletar reviews automaticamente;
    Processar grandes volumes de texto;
    Identificar padrões recorrentes;
    Gerar indicadores relevantes;
    Exibir resultados de forma visual.
    Os resultados demonstraram que técnicas de análise textual podem auxiliar significativamente na
    interpretação de opiniões em plataformas digitais.
26. Conclusão
    O projeto Golden Reviews demonstrou a aplicação prática de conceitos de Big Data, processamento
    textual e análise de dados utilizando Python.
    A solução desenvolvida conseguiu transformar grandes volumes de reviews em informações
    organizadas e úteis para os usuários.
    Além da análise de dados, o projeto também proporcionou experiência prática com APIs,
    desenvolvimento web, NLP e integração entre frontend e backend.
    O trabalho evidencia como técnicas de análise de dados podem gerar valor real em aplicações
    modernas voltadas para entretenimento digital.
27. Referências
    Documentação da Steam API;
    Documentação Flask;
    Documentação React;
    Documentação SpaCy;
    Python Software Foundation
