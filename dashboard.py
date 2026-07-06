"""Motor de renderização e controle de visões e telas (Views)."""

import streamlit as st
import pandas as pd
from database import salvar_estado_verificado, obter_historico_completo
from filters import aplicar_filtros_universais
from ai import gerar_insights_negocio
from charts import plot_barra_categorias, plot_pareto_criticidade, plot_gauge_resolucao
from reports import gerar_excel, gerar_csv

def render_dashboard_executivo(df: pd.DataFrame) -> None:
    st.subheader("📊 Centro de Controle Executivo")
    insights = gerar_insights_negocio(df)
    
    total_geral = df["perda_rs"].sum()
    economia_obtida = insights.get("economia_obtida", 0.0)
    economia_potencial = insights.get("economia_potencial", 0.0)
    tx_resolucao = (economia_obtida / total_geral * 100) if total_geral else 0.0

    # KPI Layout Metas Avançadas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Impacto Financeiro Bruto", f"R$ {total_geral:,.2f}")
    m2.metric("Perda Evitada (Economia)", f"R$ {economia_obtida:,.2f}", f"{tx_resolucao:.1f}% Salvo", delta_color="normal")
    m3.metric("Risco de Perda em Aberto", f"R$ {economia_potencial:,.2f}", f"-{100-tx_resolucao:.1f}% Pendente", delta_color="inverse")
    m4.metric("Categoria de Maior Risco", str(insights.get("categoria_maior_risco", "N/A")))

    st.markdown("---")
    g1, g2, g3 = st.columns([1, 1, 1])
    with g1:
        st.plotly_chart(plot_gauge_resolucao(tx_resolucao), use_container_width=True)
    with g2:
        st.plotly_chart(plot_barra_categorias(df), use_container_width=True)
    with g3:
        st.plotly_chart(plot_pareto_criticidade(df), use_container_width=True)

def render_lista_operacional(df: pd.DataFrame) -> None:
    st.subheader("⚡ Tabela de Operação e Auditoria Dinâmica")
    
    # Filtros Avançados
    col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 1])
    with col_a:
        cat_sel = st.multiselect("Filtrar por Categoria", options=sorted(df["categoria"].unique()))
    with col_b:
        crit_sel = st.multiselect("Filtrar por Faixa de Vencimento", options=sorted(df["faixa_criticidade"].unique()))
    with col_c:
        busca = st.text_input("Filtrar por Nome do Item")
    with col_d:
        ocultar = st.checkbox("Ocultar Itens Auditados")

    ordem = st.radio("Ordenar Listagem por:", ["Maior R$", "Mais urgente (dias)"], horizontal=True)

    df_filtrado = aplicar_filtros_universais(df, cat_sel, crit_sel, busca, ocultar, ordem)

    exibir = df_filtrado[["chave", "descricao", "categoria", "faixa_criticidade", "dias_vencer", "perda_rs", "verificado"]].copy()
    exibir = exibir.rename(columns={
        "descricao": "Produto", "categoria": "Categoria", "faixa_criticidade": "Criticidade",
        "dias_vencer": "Dias a Vencer", "perda_rs": "Perda Prevista (R$)", "verificado": "Auditado"
    })

    # Data Editor Inteligente com chave fixa segura
    editado = st.data_editor(
        exibir,
        column_config={
            "chave": None,
            "Perda Prevista (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Auditado": st.column_config.CheckboxColumn(),
        },
        hide_index=True, 
        use_container_width=True, 
        height=400, 
        key="editor_tabela_operacional_unica"
    )

    # Processamento das mudanças no banco de dados
    houve_mudanca = False
    for _, row in editado.iterrows():
        chave_atual = row["chave"]
        v_novo = bool(row["Auditado"])
        
        # Encontra correspondência original de forma segura usando o df original
        linhas_originais = df[df["chave"] == chave_atual]
        if not linhas_originais.empty:
            original = linhas_originais.iloc[0]
            if bool(original["verificado"]) != v_novo:
                salvar_estado_verificado(
                    chave=chave_atual,
                    descricao=original["descricao"],
                    dias=int(original["dias_vencer"]),
                    perda=float(original["perda_rs"]),
                    verificado=v_novo
                )
                houve_mudanca = True

    # Atualiza o estado da sessão global se algo mudou
    if houve_mudanca:
        st.session_state["df_extraido"]["verificado"] = st.session_state["df_extraido"]["chave"].map(
            lambda k: v_novo if k == chave_atual else st.session_state["df_extraido"].loc[st.session_state["df_extraido"]["chave"] == k, "verificado"].values[0]
        )
        st.rerun()
        
def render_modulo_inteligencia(df: pd.DataFrame) -> None:
    st.subheader("💡 Recomendações e Insights do Motor de IA")
    insights = gerar_insights_negocio(df)
    
    st.info(f"🎯 **Produto com Maior Índice de Desperdício:** {insights.get('produto_maior_perda')}")
    
    c1, c2, c3 = st.columns(3)
    
    # Configuração visual padrão para reaproveitamento de código nas 3 colunas
    config_colunas = {
        "descricao": st.column_config.TextColumn("Descrição", width="large"),
        "dias_vencer": st.column_config.NumberColumn("Dias", width="small"),
        "perda_rs": st.column_config.NumberColumn("Perda (R$)", format="R$ %.2f", width="medium")
    }

    with c1:
        st.write("🛑 **Perda Total Imediata (Até 7 dias):**")
        df_p1 = insights.get("produtos_proximos_perda_total", pd.DataFrame())
        if not df_p1.empty:
            st.dataframe(
                df_p1[["descricao", "dias_vencer", "perda_rs"]], 
                column_config=config_colunas,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.caption("Nenhum produto nesta faixa crítica.")

    with c2:
        st.write("🏷️ **Desconto Promocional Urgente (8 a 20 dias):**")
        df_p2 = insights.get("produtos_para_promocao", pd.DataFrame())
        if not df_p2.empty:
            st.dataframe(
                df_p2[["descricao", "dias_vencer", "perda_rs"]], 
                column_config=config_colunas,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.caption("Nenhum produto recomendado para promoção.")

    with c3:
        st.write("🚚 **Produtos Aptos para Transferência entre Lojas:**")
        df_p3 = insights.get("produtos_para_transferencia", pd.DataFrame())
        if not df_p3.empty:
            st.dataframe(
                df_p3[["descricao", "dias_vencer", "perda_rs"]], 
                column_config=config_colunas,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.caption("Nenhum produto recomendado para transferência.")

def render_historico_auditoria() -> None:
    st.subheader("📜 Log de Auditoria e Histórico de Alterações")
    dados_historico = obter_historico_completo()
    if dados_historico:
        st.dataframe(pd.DataFrame(dados_historico), use_container_width=True, hide_index=True)
    else:
        st.write("Nenhuma movimentação registrada nas sessões atuais.")

def render_exportacao_relatorios(df: pd.DataFrame) -> None:
    st.subheader("📥 Exportação Corporativa de Relatórios")
    st.write("Faça download dos dados do painel atual formatados:")
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label="📊 Baixar Relatório em Excel (XLSX)", 
            data=gerar_excel(df), 
            file_name="relatorio_validade.xlsx"
        )
    with c2:
        st.download_button(
            label="📄 Baixar Relatório em CSV", 
            data=gerar_csv(df), 
            file_name="relatorio_validade.csv"
        )