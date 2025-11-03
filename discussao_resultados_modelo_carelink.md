# Discussão dos Resultados - Modelo CareLink

## 1. Contexto e Objetivo do Modelo

O projeto CareLink visa solucionar um problema crítico de negócio do IMREA: a alta taxa de absenteísmo (20-25%) em teleconsultas. O custo operacional de um profissional de saúde ocioso é muito superior ao custo de uma intervenção proativa (como uma ligação de confirmação).

**Objetivo do Modelo:**
O objetivo deste notebook não é simplesmente prever "Sim" ou "Não", mas sim desenvolver um modelo de Classificação Binária (Regressão Logística) capaz de calcular uma probabilidade de falta. Essa probabilidade é então convertida em um Score de Risco (0-1000), permitindo que a equipe CareLink priorize e execute intervenções focadas apenas nos pacientes de maior risco.

Este modelo (model_carelink_.joblib) é um dos dois modelos de aprendizado de máquina exigidos pela entrega e será disponibilizado via API REST.

## 2. Metodologia: A Geração do Dataset Sintético

Como não possuíamos dados históricos reais, o primeiro passo foi criar um dataset sintético realista (gerar_dataset). Um modelo de IA só pode aprender os padrões que existem nos dados; portanto, "embutir" correlações realistas foi a etapa mais crítica do projeto.

Nossa metodologia foi muito além de números aleatórios:

*   **Distribuições Realistas:** Em vez de distribuições uniformes, usamos `np.random.normal` e `np.random.triangular` para features como `idade_paciente` e `tempo_desde_ultima_consulta_dias`, refletindo as regras de negócio do IMREA (frequência de tratamento de 8-10 semanas).
*   **Correlações de Causa-Efeito:** Implementamos multicolinearidade intencional. A `idade_paciente` e o `bairro_categoria` (Baixa Renda) foram usados como fatores causais para gerar um `afinidade_digital_score` mais baixo.
*   **Geração de Risco por Gradiente:** A principal inovação foi na geração do `TARGET_FALTA_BINARIA`. Em vez de regras binárias (ex: idade > 80), calculamos um `risco_base` (logit) como uma soma ponderada de gradientes. Por exemplo, `(idade_paciente - 60).clip(0) * 0.05` aplica um risco crescente para cada ano acima de 60, criando um "sinal" estatístico forte e linear que o modelo de regressão pôde aprender.
*   **Calibração Automática:** O `risco_base` foi convertido em probabilidade usando `scipy.special.expit`, e um `ajuste_intercept` foi aplicado para calibrar a taxa de absenteísmo final do dataset (30,1%), garantindo que o modelo fosse treinado em um cenário de desequilíbrio de classe similar ao real.

## 3. Construção do Pipeline de Machine Learning

Para garantir que o modelo seja robusto, reprodutível e pronto para produção (evitando data leakage), todo o processo foi encapsulado em um Pipeline do Scikit-learn.

**ColumnTransformer (Pré-processador):**
*   **Numérico:** Aplicou o `StandardScaler` às 7 colunas numéricas. Isso foi essencial, pois a Regressão Logística é sensível a features em escalas diferentes (ex: idade 18-100 vs. taxa_absenteismo 0-1).
*   **Categórico:** Aplicou o `OneHotEncoder` às colunas `bairro_paciente` e `especialidade_consulta`, transformando strings (ex: 'Grajaú') em colunas binárias que o modelo entende.

**LogisticRegression (O Modelo):**
O modelo foi otimizado com dois hiperparâmetros cruciais identificados durante nossos testes:
*   `class_weight='balanced'`: Esta foi a solução para o desequilíbrio de classe (30% de Faltas). Sem isso, o modelo tenderia a prever "Compareceu" (0) para todos, gerando uma acurácia alta, porém inútil. Este parâmetro força o modelo a dar um peso maior aos erros na classe minoritária ("Falta").
*   `C=0.1`: Esta foi a solução para o overfitting. Nossos testes iniciais com o C padrão (1.0) resultaram em um modelo "tudo ou nada" (scores 0 ou 1000). Ao aplicar uma regularização mais forte (C=0.1), penalizamos pesos extremos, forçando o modelo a ser menos confiante e a gerar os scores graduados e realistas (ex: 166, 458, 677) vistos nos testes de cenário.

## 4. Análise de Desempenho e Resultados

O modelo foi treinado em 80% dos dados (1600 amostras) e avaliado em 20% (400 amostras). Os resultados demonstram um modelo robusto e viável.

*   **AUC-ROC: 0.7408**
    Esta é a métrica mais importante para um modelo de classificação de risco. Um valor de 0.74 (onde 0.50 é aleatório) indica que o modelo tem um forte poder discriminatório; ele é significativamente bom em ranquear pacientes de alto risco acima de pacientes de baixo risco.
*   **Acurácia: 0.7000**
    Uma acurácia de 70% é um resultado "honesto" e esperado. Ela reflete o desempenho do modelo após ser forçado pelo `class_weight='balanced'` a sacrificar a acurácia geral para conseguir identificar corretamente a classe minoritária (Falta).

**O Trade-off: Precisão (50%) vs. Recall (68%)**
O Relatório de Classificação nos dá a visão mais profunda sobre a utilidade do modelo para o IMREA, focando na Classe 1 (Faltou):
*   **Recall (Revocação): 0.68 (68%)**
*   **Precisão (Precision): 0.50 (50%)**

À primeira vista, uma Precisão de 50% parece um problema, pois significa que 50% dos "alarmes" de falta são falsos positivos (a equipe ligaria para pacientes que iriam comparecer).

No entanto, esta não é uma falha, mas sim uma escolha estratégica baseada no custo do erro para o IMREA:
*   **Custo de Falso Positivo (Baixa Precisão):** Uma ligação desnecessária. Custo Baixo.
*   **Custo de Falso Negativo (Baixo Recall):** Um profissional ocioso e um tratamento interrompido. Custo Altíssimo.

Nosso modelo está estrategicamente otimizado para maximizar o Recall (capturando 68% de todas as faltas reais), aceitando o custo baixo de mais ligações para evitar o custo alto de mais faltas.

**Teste de Cenários**
Os testes de cenário validam que a regularização (`C=0.1`) funcionou, e o modelo agora produz scores graduados que refletem o risco real:

| Paciente (Resumo)    | Score Gerado | Nível de Risco |
| :------------------- | :----------- | :------------- |
| Cenário 1 (Baixo Risco) | 166          | BAIXO          |
| Cenário 2 (Médio Risco) | 458          | MÉDIO          |
| Cenário 7 (Alto Risco)  | 677          | ALTO           |
| Cenário 4 (Crítico Risco)| 849          | CRÍTICO        |

## 5. Conclusão e Próximos Passos

O modelo de Regressão Logística (model_carelink.joblib) atende aos requisitos do Sprint. Ele é robusto (AUC 0.74), otimizado para o problema de negócio (Recall > Precision) e produz scores graduados realistas.

O modelo está pronto para ser consumido pelo arquivo `app.py` da API REST, que calculará o Score de Risco para novos agendamentos no IMREA.
