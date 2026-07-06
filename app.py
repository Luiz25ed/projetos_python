"""Ponto de Entrada Único da Aplicação (Main Entrypoint)."""

import streamlit as st
from config import init_page_config
from database import init_db, buscar_verificados
from pdf_reader import extrair_pdf
from utils import gerar_chave_item
from dashboard import (
    render_dashboard_executivo, 
    render_lista_operacional, 
    render_modulo_inteligencia,
    render_historico_auditoria,
    render_exportacao_relatorios
)

def main() -> None:
    # 1. Inicializa Configurações e Banco de Dados (Padrão de Inicialização de Arquitetura)
    init_page_config()
    init_db()

    # 2. Inicialização dos Estados de Sessão do Streamlit
    if "df_extraido" not in st.session_state:
        st.session_state["df_extraido"] = None

    # 3. Construção do Menu Lateral Corporativo (UX/UI Clean)
    st.sidebar.title("Navegação")
    menu = st.sidebar.radio(
        "Ir para:",
        ["Dashboard Executivo", "Lista Operacional", "Recomendações IA", "Histórico de Auditoria", "Configurações & Exportações"]
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Carga de Dados")
    arquivo_pdf = st.sidebar.file_uploader("Upload do PDF de Validade", type=["pdf"])

    # Tratamento Reativo de Upload
    if arquivo_pdf is not None:
        conteudo_bytes = arquivo_pdf.getvalue()
        df_bruto = extrair_pdf(conteudo_bytes)
        if df_bruto is not None and not df_bruto.empty:
            # Sincronização automática do DataFrame em memória com as chaves persistidas no SQLite
            verificados_db = buscar_verificados()
            
            df_bruto["chave"] = df_bruto.apply(lambda r: gerar_chave_item(r["descricao"], r["dias_vencer"], r["perda_rs"]), axis=1)
            df_bruto["verificado"] = df_bruto["chave"].map(lambda k: verificados_db.get(k, False))
            
            # Nova Regra de Negócio: Definição de faixa de criticidade
            def define_criticidade(dias: int) -> str:
                if dias <= 15: return "1. Crítico (Até 15 dias)"
                if dias <= 30: return "2. Alerta Alto (16 a 30 dias)"
                if dias <= 60: return "3. Atenção (31 a 60 dias)"
                return "4. Planejado (Acima de 60 dias)"
                
            df_bruto["faixa_criticidade"] = df_bruto["dias_vencer"].apply(define_criticidade)
            st.session_state["df_extraido"] = df_bruto
        else:
            st.session_state["df_extraido"] = None

    # Redirecionamento de Fluxo de Página Vazia
    if st.session_state["df_extraido"] is None:
        st.info("👋 Bem-vindo! Para iniciar o painel analítico, realize o upload do PDF do ERP no menu à esquerda.")
        st.stop()

    df_sessao = st.session_state["df_extraido"]

    # 4. Roteador de Telas (Router Pattern)
    if menu == "Dashboard Executivo":
        render_dashboard_executivo(df_sessao)
    elif menu == "Lista Operacional":
        render_lista_operacional(df_sessao)
    elif menu == "Recomendações IA":
        render_modulo_inteligencia(df_sessao)
    elif menu == "Histórico de Auditoria":
        render_historico_auditoria()
    elif menu == "Configurações & Exportações":
        render_exportacao_relatorios(df_sessao)

if __name__ == "__main__":
    main()