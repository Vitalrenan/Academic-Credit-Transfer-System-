import streamlit as st
import pandas as pd
import os
import PyPDF2
from ai_engine import analyze_equivalence_high_accuracy
import re

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sistema de Equivalência - Cruzeiro do Sul",
    page_icon="🎓",
    layout="wide"
)

# --- 2. GESTÃO DE ESTADO (SESSION STATE) ---
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "analise_confirmada" not in st.session_state:
    st.session_state.analise_confirmada = False
if "dados_finais" not in st.session_state:
    st.session_state.dados_finais = None
if "raw_result" not in st.session_state:
    st.session_state.raw_result = None
if "usage_data" not in st.session_state:
    st.session_state.usage_data = None
if "student_name" not in st.session_state:
    st.session_state.student_name = ""

# --- 3. MODAL DE LOGIN ---
@st.dialog("Acesso ao Sistema DataEDUCA")
def login_modal():
    st.markdown("### 🔐 Área Restrita")
    nome = st.text_input("Nome do Validador", placeholder="Ex: Renan")
    email = st.text_input("E-mail Corporativo", placeholder="seu@email.com")
    
    if st.button("Entrar", type="primary", use_container_width=True):
        if nome and "@" in email:
            st.session_state.user_info = {"nome": nome, "email": email}
            st.rerun()

if not st.session_state.user_info:
    login_modal()
    st.stop()

# --- 4. FUNÇÕES UTILITÁRIAS ---
def extract_text(uploaded_file):
    if not uploaded_file: return ""
    uploaded_file.seek(0)
    try:
        text = ""
        if uploaded_file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            text = "".join([page.extract_text() or "" for page in reader.pages])
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            text = df.to_string()
        elif uploaded_file.name.endswith('.txt'):
            text = uploaded_file.read().decode("utf-8")
        
        text = text.replace('\x00', '')
        text = re.sub(r'\s+', ' ', text) 
        return text.strip()
    except Exception as e:
        return f"Erro: {str(e)}"

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configurações")
    api_key = st.text_input("Gemini API Key", type="password")
    file_student = st.file_uploader("Histórico do Aluno (PDF/TXT)", type=['pdf', 'txt'])
    file_matrix = st.file_uploader("Matriz de Referência (XLSX)", type=['xlsx'])
    
    btn_run = st.button("🚀 Iniciar Análise IA", type="primary", use_container_width=True)
    
    if st.button("🗑️ Reiniciar Sessão", use_container_width=True):
        for key in ["raw_result", "analise_confirmada", "dados_finais", "student_name"]:
            st.session_state[key] = None if key != "analise_confirmada" else False
        st.rerun()

# --- 6. LÓGICA DE PROCESSAMENTO ---
if btn_run:
    if not api_key or not file_student or not file_matrix:
        st.warning("Carregue os arquivos e insira a API Key.")
    else:
        with st.spinner("🤖 O Gemini 2.5 Pro está a processar..."):
            txt_student = extract_text(file_student)
            txt_matrix = extract_text(file_matrix)
            data, usage = analyze_equivalence_high_accuracy(api_key, txt_student, txt_matrix)
            
            if data and "analise" in data and len(data["analise"]) > 0:
                df = pd.DataFrame(data["analise"])
                df.columns = [c.strip() for c in df.columns]
                col_v = next((c for c in df.columns if "Veredito" in c), "Veredito")
                df["Aprovar"] = df[col_v].apply(lambda x: True if str(x).upper() == "DEFERIDO" else False)
                
                st.session_state.raw_result = df
                st.session_state.student_name = data.get("nome_aluno", "Não Identificado")
                st.session_state.usage_data = usage
                st.session_state.analise_confirmada = False
                st.rerun()

# --- 7. INTERFACE DE ABAS ---
if file_student or file_matrix or st.session_state.raw_result is not None:
    # Lógica de abas dinâmicas
    titulos = ["📄 Documentos"]
    if st.session_state.raw_result is not None:
        titulos.append("🤖 Validação IA")
    if st.session_state.analise_confirmada:
        titulos.append("✅ Relatório Final")
    
    tabs = st.tabs(titulos)

    # --- ABA 1: DOCUMENTOS (APENAS CARDS) ---
    with tabs[0]:
        c1, c2 = st.columns([0.6, 0.4])
        with c1:
            st.subheader("📑 Disciplinas Identificadas")
            texto_raw = extract_text(file_student)
            
            with st.container(border=True):
                nome_aluno = re.search(r"Nome:\s*(.*)", texto_raw)
                #st.markdown(f"#### 👤 {nome_aluno.group(1) if nome_aluno else 'Estudante'}")
                #st.divider()
                
                # Renderiza apenas os cards, sem o texto bruto acima
                itens = texto_raw.split("DISCIPLINA:")[1:]
                for item in itens:
                    linhas = item.strip().split('\n')
                    nome_d = linhas[0].split("NOTA:")[0].split("---")[0].strip()
                    status_cor = "#28a745" if "APROVADO" in item.upper() else "#dc3545"
                    detalhes = linhas[0].split(nome_d)[-1].strip() if "NOTA:" in linhas[0] else ""
                    
                    st.markdown(f"""
                    <div style="background-color: #262730; padding: 12px; border-radius: 8px; border-left: 6px solid {status_cor}; margin-bottom: 12px;">
                        <div style="font-weight: bold; color: #ffffff; font-size: 16px;">{nome_d}</div>
                        <div style="font-size: 13px; color: #bdc3c7; margin-top: 4px;">{detalhes}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with c2:
            st.subheader("📋 Matriz Alvo")
            if file_matrix:
                file_matrix.seek(0)
                st.dataframe(pd.read_excel(file_matrix), use_container_width=True, height=600)

    # --- ABA 2: VALIDAÇÃO IA ---
    if st.session_state.raw_result is not None:
        with tabs[1]:
            st.subheader(f"Análise: {st.session_state.student_name}")
            edited_df = st.data_editor(
                st.session_state.raw_result, 
                use_container_width=True, 
                hide_index=True,
                column_config={"Aprovar": st.column_config.CheckboxColumn("Deferir?")}
            )
            if st.button("🔒 Finalizar Parecer"):
                st.session_state.dados_finais = edited_df
                st.session_state.analise_confirmada = True
                st.rerun()

    # --- ABA 3: RELATÓRIO FINAL (CORREÇÃO DE TELA PRETA) ---
    if st.session_state.analise_confirmada and st.session_state.dados_finais is not None:
        with tabs[-1]:
            st.title("📊 Parecer de Equivalência")
            df_f = st.session_state.dados_finais
            col_d = next((c for c in df_f.columns if "Destino" in c), "Disciplina_Destino")
            aprovadas = df_f[df_f["Aprovar"] == True]
            
            if file_matrix:
                file_matrix.seek(0)
                df_m = pd.read_excel(file_matrix)
                col_n = next((c for c in df_m.columns if any(x in c.lower() for x in ["disciplina", "nome"])), df_m.columns[0])
                
                aprovados_list = [str(x).strip().upper() for x in aprovadas[col_d].tolist()]
                df_p = df_m[~df_m[col_n].astype(str).str.strip().str.upper().isin(aprovados_list)]

                m1, m2, m3 = st.columns(3)
                m1.metric("Dispensadas", len(aprovadas))
                m2.metric("Pendentes", len(df_p))
                m3.metric("Aproveitamento", f"{(len(aprovadas)/len(df_m)*100):.1f}%" if len(df_m)>0 else "0%")
                
                st.divider()
                r1, r2 = st.columns(2)
                with r1:
                    st.success("### ✅ Matérias Aproveitadas")
                    st.dataframe(aprovadas, use_container_width=True, hide_index=True)
                with r2:
                    st.warning("### 📚 Plano de Estudos")
                    st.dataframe(df_p[[col_n]], use_container_width=True, hide_index=True)