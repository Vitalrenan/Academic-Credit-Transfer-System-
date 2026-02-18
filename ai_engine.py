import google.generativeai as genai
import json

def analyze_equivalence_high_accuracy(api_key, txt_student, txt_matrix):
    """
    Motor de análise utilizando Gemini 2.5 Pro para máxima precisão em equivalências.
    """
    try:
        # Configuração da API
        genai.configure(api_key=api_key)
        
        # Instanciando o Gemini 2.5 Pro
        # O modelo 2.5 Pro lida melhor com contextos longos de históricos e matrizes
        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,  # Baixa temperatura para evitar alucinações acadêmicas
            }
        )

        prompt = f"""
        Você é o Coordenador de IA da Cruzeiro do Sul, especialista em análise curricular.
        Sua tarefa é cruzar os dados do Histórico Escolar com a Matriz Curricular Alvo.

        DIRETRIZES TÉCNICAS:
        1. Compare as ementas e nomes das disciplinas. 
        2. Considere similaridade fonética e semântica (ex: "Cálculo I" e "Cálculo Diferencial e Integral I" são equivalentes).
        3. DEFERIDO: Se houver correspondência clara (>= 70%).
        4. INDEFERIDO: Se não houver correspondência ou a carga horária for drasticamente menor.

        CONTEXTO DO ESTUDANTE:
        {txt_student[:20000]} 

        MATRIZ DE REFERÊNCIA (CRUZEIRO DO SUL):
        {txt_matrix[:20000]}

        SAÍDA OBRIGATÓRIA EM JSON:
        {{
          "nome_aluno": "Nome extraído do documento",
          "analise": [
            {{
              "Disciplina_Origem": "Nome da matéria cursada no histórico",
              "Disciplina_Destino": "Nome da matéria equivalente na matriz alvo",
              "Similaridade": 0.0 a 1.0,
              "Veredito": "DEFERIDO" ou "INDEFERIDO",
              "Justificativa": "Racional técnico da decisão"
            }}
          ]
        }}
        """

        response = model.generate_content(prompt)
        
        if not response.text:
            return {"analise": [], "erro": "A API não retornou texto."}, None

        # Parsing seguro do JSON
        try:
            data = json.loads(response.text)
            return data, response.usage_metadata
        except json.JSONDecodeError:
            # Fallback para limpeza de caracteres caso a IA envie markdown
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text), response.usage_metadata

    except Exception as e:
        # Se o erro 404 persistir, o sistema reportará exatamente o modelo tentado
        error_msg = str(e)
        if "404" in error_msg:
            error_msg = f"Modelo gemini-2.5-pro não encontrado ou acesso não autorizado para esta API Key. {error_msg}"
        return {"analise": [], "erro": error_msg}, None