import joblib
import pandas as pd
from flask import Flask, request, jsonify

# 1. Configuração Inicial e Carregamento do Modelo
app = Flask(__name__)
try:
    # O pipeline completo com Scaler, Encoder e Modelo
    pipeline_completo = joblib.load('model_carelink.joblib')
    print("✅ Modelo 'model_carelink.joblib' carregado com sucesso.")
except FileNotFoundError:
    print("❌ ERRO: Arquivo do modelo não encontrado. Verifique se ele está na mesma pasta que 'app.py'.")
    pipeline_completo = None

# --- Rota Principal da API ---
# A rota /predict_risk aceitará requisições POST com os dados do paciente
@app.route('/predict_risk', methods=['POST'])
def predict_risk():
    # 0. Verificação de Integridade
    if pipeline_completo is None:
        return jsonify({'error': 'Modelo de IA não carregado no servidor.'}), 500
    
    # 2. Receber e Formatar os Dados
    try:
        # Recebe o JSON da requisição (ex: de um novo agendamento no CareLink)
        data = request.get_json(force=True)
        
        # O pipeline PRECISA de um DataFrame para funcionar.
        new_patient_df = pd.DataFrame([data])
        
    except Exception as e:
        return jsonify({'error': f'Erro ao processar a entrada JSON: {e}'}), 400

    # 3. Geração do Score de Risco
    try:
        # 3.1. Obter a Probabilidade de Falta (Classe 1)
        prob_falta = pipeline_completo.predict_proba(new_patient_df)[:, 1]
        
        # 3.2. Conversão para o Score de Risco (0-1000)
        score_risco = int(round(prob_falta[0] * 1000))

        # No retorno do endpoint, adicione:
        if score_risco <= 300:
            nivel_risco = "BAIXO"
        elif score_risco <= 600:
            nivel_risco = "MÉDIO" 
        elif score_risco <= 800:
            nivel_risco = "ALTO"
        else:
            nivel_risco = "CRÍTICO"

        # 4. Retornar o Resultado
        return jsonify({
            'status': 'success',
            'score_risco_carelink': score_risco,
            'nivel_risco': nivel_risco,
            'probabilidade_falta': float(prob_falta[0]),
            'interpretacao': f'Paciente classificado como risco {nivel_risco}'
        })

    except Exception as e:
        # Este erro acontece se as colunas estiverem faltando ou desordenadas
        return jsonify({'error': f'Erro de Previsão! Verifique as 9 colunas e a ordem: {e}'}), 500

if __name__ == '__main__':
    # Roda a aplicação Flask no ambiente de desenvolvimento
    print("Servidor CareLink iniciado. Use CTRL+C para parar.")
    app.run(host='0.0.0.0', port=5000)