# Relatório de Integração - Fase 2 (Backend ML Pipeline)

## Visão Geral

Durante a etapa de plugar os cérebros (Modelos de Sentimento + BERTopic) gerados na Fase 1 dentro da Fase 2 (o servidor Flask on-the-fly), nos deparamos com dois bloqueadores gravíssimos de infraestrutura e comportamento matemático. Este documento histórico serve como documentação de como solucionamos isso para o projeto Golden Reviews.

---

## Bloqueador 1: O "Inferno" de Dependências do NLP

**Sintoma:** O backend apresentava estouro de `500 Internal Server Error` logo ao rodar a análise, com a stack de erro finalizando em dentro da lib `pysentimiento` com a mensagem `TypeError: demojize() got an unexpected keyword argument 'language'`.

**Causa Raiz:** O modelo PySentimiento foi construído baseando-se em uma versão específica (legada) da biblioteca `emoji`. Quando instalamos os pacotes do zero na máquina de desenvolvimento com `pip install emoji`, o PyPI baixou a versão `2.15.0`, a qual removeu brutalmente o suporte ao parâmetro `language` utilizado na limpeza pré-inferência do Transformer.

**Resolução:**
Fizemos um downgrade hardcoded travando a versão para manter a compatibilidade interna do modelo.

```bash
pip install emoji==1.7.0
```

Isso estabilizou o interpretador e a inferência de `.predict()` voltou a ser executada com sucesso.

---

## Bloqueador 2: O Deslocamento Bizarro de Tópicos (Off-by-One do BERTopic)

**Sintoma:** Ao renderizar o output no frontend (`ReviewAnalysis.jsx` / `topics-grid`), as frases perfeitamente clusterizadas estavam caindo na label do tópico IMEDIATAMENTE ANTERIOR no ranking (ex: frases sobre "desafios e boss" caindo no invólucro do tópico sobre "comprar e vale a pena").

**Causa Raiz Parte A (Arquitetura do App):**
Os IDs dos tópicos para o Dicionário Negativo e Positivo estavam colidindo no dicionário (`topic_ids = {**pos_groups, **neg_groups}`) forçando um merge literal onde o ID `1` Positivo (ex: Gráficos) sobrepunha ou misturava com o ID `1` Negativo (ex: Bugs).
_Correção:_ Quebramos o payload em laços independentes para o construtor isolando o output baseando-se no namespace correto.

**Causa Raiz Parte B (Engine do Model / HDBSCAN):**
Em decorrência das otimizações de `reduce_outliers` realizadas no Jupyter da Fase 1, a função `BERTopic.transform()` passou a operar de maneira literal na matriz sem processar a abstração nominal. Em matrizes, a posição index `0` sempre guarda os dados do Tópico `-1` (Ruído). Logo:

- `.transform()` emitia o ID Matriz `162`.
- `app.py` aceitava `162` e pedia por `get_topic(162)`.
- Porém, o Tópico `162` "nominalmente" era, na verdade, o Index Matriz `163`. O Index Matriz `162` guardava os dados do Tópico Nominal `161`.
  Tudo ficava deslocado no código.

**Resolução:**
Compensamos a defasagem subtraindo `1` do índice bruto estonado pelo `.transform()` imediatamente antes de mapear no nosso dicionário agrupador, trazendo harmonia comemorativa aos dados lidos pelo frontend:

```python
pos_topics_raw, _ = self._topic_model_pos.transform(pos_sents)
pos_topics = [t - 1 for t in pos_topics_raw] # Fix mágico matemático!
```
