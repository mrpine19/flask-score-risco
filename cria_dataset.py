import pandas as pd
import numpy as np

# =============================================================================
# 1. GERAR DATASET COM BALANCEAMENTO CORRETO E SINAIS ADEQUADOS
# =============================================================================
np.random.seed(42)
N = 2000


def gerar_dataset():
    df = pd.DataFrame()

    # Features base (mantendo distribuição realista)
    df['idade_paciente'] = np.random.normal(loc=65, scale=15, size=N).astype(int).clip(18, 100)

    # Bairro
    bairro_categoria = np.random.choice(['Baixa Renda', 'Média Renda', 'Alta Renda'],
                                        size=N, p=[0.4, 0.35, 0.25])

    bairros_baixa_renda = ['Grajaú', 'Marsilac', 'Brasilândia', 'Parelheiros', 'Lajeado', 'Cidade Tiradentes']
    bairros_media_renda = ['Tatuapé', 'Mooca', 'Santana', 'Vila Mariana', 'Saúde', 'Butantã']
    bairros_alta_renda = ['Jardins', 'Itaim Bibi', 'Pinheiros', 'Moema', 'Higienópolis', 'Morumbi']

    df['bairro_paciente'] = ''
    df.loc[bairro_categoria == 'Baixa Renda', 'bairro_paciente'] = np.random.choice(
        bairros_baixa_renda, size=(bairro_categoria == 'Baixa Renda').sum())
    df.loc[bairro_categoria == 'Média Renda', 'bairro_paciente'] = np.random.choice(
        bairros_media_renda, size=(bairro_categoria == 'Média Renda').sum())
    df.loc[bairro_categoria == 'Alta Renda', 'bairro_paciente'] = np.random.choice(
        bairros_alta_renda, size=(bairro_categoria == 'Alta Renda').sum())

    # Afinidade Digital - Sinal adequado
    base_score = np.random.normal(loc=60, scale=20, size=N)
    idade_penalidade = (df['idade_paciente'] - 60).clip(0) * 0.6
    bairro_penalidade = np.where(bairro_categoria == 'Baixa Renda', -20,
                                 np.where(bairro_categoria == 'Alta Renda', 15, 0))
    df['afinidade_digital_score'] = (base_score - idade_penalidade + bairro_penalidade).clip(0, 100).astype(int)

    # Outras features
    prob_cuidador = np.where(df['idade_paciente'] > 75, 0.6,
                             np.where(df['idade_paciente'] > 65, 0.4, 0.2))
    df['tem_cuidador'] = np.random.binomial(1, prob_cuidador, size=N)

    especialidades_alto_risco = ['Fonoaudiologia', 'Terapia Ocupacional', 'Psicologia']
    especialidades_normal = ['Fisioterapia', 'Neurologia', 'Serviço Social', 'Condicionamento Físico',
                             'Tecnologias Assistivas', 'Odontologia', 'Enfermagem', 'Nutrição']

    especialidade_tipo = np.random.choice(['Alto Risco', 'Normal'], size=N, p=[0.3, 0.7])
    df['especialidade_consulta'] = ''
    df.loc[especialidade_tipo == 'Alto Risco', 'especialidade_consulta'] = np.random.choice(
        especialidades_alto_risco, size=(especialidade_tipo == 'Alto Risco').sum())
    df.loc[especialidade_tipo == 'Normal', 'especialidade_consulta'] = np.random.choice(
        especialidades_normal, size=(especialidade_tipo == 'Normal').sum())

    df['faltas_consecutivas_historico'] = np.random.poisson(0.5, size=N).clip(0, 3)
    df['taxa_absenteismo_historica'] = np.random.beta(a=0.9, b=5, size=N)  # Voltar ao original

    # Tempos realistas
    df['tempo_desde_ultima_consulta_dias'] = np.random.triangular(7, 12, 30, size=N).astype(int)
    df['tempo_desde_primeira_consulta_dias'] = np.random.triangular(30, 65, 120, size=N).astype(int)

    # TARGET COM SINAIS ADEQUADOS E BALANCEAMENTO CORRETO
    risco_base = np.zeros(N)

    # SINAIS COM FORÇA ADEQUADA (similar ao V2 mas com limites)
    risco_base += (df['idade_paciente'] - 60).clip(0) * 0.05

    # Afinidade: efeito moderado
    risco_base += (df['afinidade_digital_score'] - 50) * -0.02

    # Cuidador: efeito forte
    risco_base += (df['tem_cuidador'] == 0) * 0.5

    # Bairro: efeitos moderados
    risco_base += (bairro_categoria == 'Baixa Renda') * 0.3
    risco_base += (bairro_categoria == 'Alta Renda') * -0.3

    # Especialidade: efeito moderado
    risco_base += (df['especialidade_consulta'].isin(especialidades_alto_risco)) * 0.25

    # Histórico: efeitos importantes
    risco_base += df['faltas_consecutivas_historico'] * 0.2
    risco_base += df['taxa_absenteismo_historica'] * 1.5

    # Tempos: efeitos pequenos
    risco_base += (df['tempo_desde_ultima_consulta_dias'] - 14).clip(0) * 0.02
    risco_base += (70 - df['tempo_desde_primeira_consulta_dias']).clip(0) * 0.01

    # RUÍDO MODERADO
    risco_base += np.random.normal(0, 0.3, size=N)

    # CALIBRAR PARA TER ~23% DE ABSENTEÍSMO
    from scipy.special import expit
    probabilidade = expit(risco_base)

    # Ajustar o intercept para ter ~23% de faltas
    current_rate = probabilidade.mean()
    target_rate = 0.23
    ajuste_intercept = np.log(target_rate / (1 - target_rate)) - np.log(current_rate / (1 - current_rate))
    probabilidade_ajustada = expit(risco_base + ajuste_intercept)

    df['TARGET_FALTA_BINARIA'] = (probabilidade_ajustada > np.random.rand(N)).astype(int)

    return df


print("Gerando dataset...")
df = gerar_dataset()
df.to_csv('dataset_treinamento_carelink.csv', index=False)
print(f"Dataset gerado! Taxa de absenteísmo: {df['TARGET_FALTA_BINARIA'].mean():.3f}")