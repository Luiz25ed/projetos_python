"""
Painel de Priorização de Perdas — Validade
Lê o relatório de validade (PDF do ERP), extrai os itens com previsão de
perda, categoriza por tipo de produto e mostra um painel priorizado com
checkbox de "verificado" que persiste entre sessões (arquivo local).

Como rodar:
    pip install -r requirements.txt
    streamlit run app.py

Como publicar de graça (acessível de qualquer lugar, sem servidor seu):
    1. Suba esta pasta num repositório do GitHub (gratuito).
    2. Entre em https://share.streamlit.io, conecte sua conta GitHub.
    3. Aponte para o repositório e o arquivo app.py.
    4. Pronto — você recebe uma URL pública (ex: seuapp.streamlit.app).
"""

import io
import json
import re
from pathlib import Path

import pandas as pd
import pdfplumber
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Painel de Priorização de Perdas",
    page_icon="📉",
    layout="wide",
)

VERIFICADOS_PATH = Path("verificados.json")

CATEGORIAS_KEYWORDS = {
    "Café": ["CAFE "],
    "Iogurte": ["IOG "],
    "Pão/Padaria": ["PAO ", "PANCO", "WICKBOLD", "PULLMAN", "BISNAGU"],
    "Biscoito": ["BISC "],
    "Refrigerante": ["REFR "],
    "Leite Fermentado": ["LEITE FERMENTADO", "YAKULT"],
    "Frios/Embutidos": ["MORTADELA", "PRESUNTO", "LINGUICA", "SALAME", "APRESUNTADO"],
    "Ovos": ["OVOS ", "OVO "],
}

CORES_CATEGORIA = {
    "Café": "#E3A23D",
    "Iogurte": "#4FA98C",
    "Carnes/Aves": "#C24A3F",
    "Frios/Embutidos": "#B589C9",
    "Leite Fermentado": "#7C9CC4",
    "Refrigerante": "#5FB8D9",
    "Biscoito": "#D9A5C0",
    "Pão/Padaria": "#C9A26B",
    "Ovos": "#D9C25F",
    "Outros": "#7D8590",
}


# ---------------------------------------------------------------------------
# Extração e categorização
# ---------------------------------------------------------------------------

def clean_num(s):
    """Converte string em formato BR ('R$ 1.234,56') para float."""
    if s is None:
        return 0.0
    s = str(s).replace("\n", "").replace("R$", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def categoriza(descricao: str) -> str:
    d = str(descricao).upper()
    for categoria, palavras in CATEGORIAS_KEYWORDS.items():
        if any(p in d for p in palavras):
            return categoria
    if d.endswith(" KG") or " KG" in d:
        return "Carnes/Aves"
    return "Outros"


@st.cache_data(show_spinner=False)
def extrair_pdf(arquivo_bytes: bytes) -> pd.DataFrame:
    rows = []
    with pdfplumber.open(io.BytesIO(arquivo_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for r in table:
                    # Permite leitura dinâmica se o relatório tiver variações de colunas na impressão
                    if r and len(r) >= 18:
                        rows.append(r)

    registros = []
    for r in rows:
        try:
            desc = str(r[3] or "").replace("\n", " ").strip()
            if not desc or desc.upper() == "DESCRIÇÃO":
                continue
            
            dias_raw = str(r[13] or "").replace("\n", "").strip()
            try:
                dias = int(dias_raw)
            except ValueError:
                dias = 0
                
            perda_qtde = clean_num(r[16]) if len(r) > 16 else 0.0
            perda_rs = clean_num(r[17]) if len(r) > 17 else 0.0
            custo_liquido = clean_num(r[19]) if len(r) > 19 else 0.0
            setor_erp = str(r[26] or "").replace("\n", "").strip() if len(r) > 26 else "Geral"

            registros.append({
                "descricao": desc.title(),
                "dias_vencer": dias,
                "perda_qtde": perda_qtde,
                "perda_rs": perda_rs,
                "custo_liquido": custo_liquido,
                "setor_erp": setor_erp,
            })
        except Exception:
            continue

    df = pd.DataFrame(registros)
    if df.empty:
        return df
    df["categoria"] = df["descricao"].apply(categoriza)
    return df


# ---------------------------------------------------------------------------
# Persistência local do estado "verificado"
# ---------------------------------------------------------------------------

def carrega_verificados() -> dict:
    if VERIFICADOS_PATH.exists():
        try:
            return json.loads(VERIFICADOS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def salva_verificados(d: dict):
    try:
        VERIFICADOS_PATH.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        st.error(f"Erro ao salvar banco de verificações: {e}")


def chave_item(row) -> str:
    return f"{row['descricao']}|{row['dias_vencer']}|{row['perda_rs']}"


# ---------------------------------------------------------------------------
# Funções auxiliares para Exportação
# ---------------------------------------------------------------------------

def df_para_excel(df_export):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Priorização')
    return output.getvalue()


def df_para_txt(df_export):
    output = io.StringIO()
    df_export.to_string(output, index=False)
    return output.getvalue()


def gatilho_upload_pdf():
    """Gerencia a extração disparada unicamente pelo evento de mudança do arquivo."""
    if st.session_state["uploader_pdf"] is not None:
        try:
            conteudo_bytes = st.session_state["uploader_pdf"].getvalue()
            st.session_state["df_extraido"] = extrair_pdf(conteudo_bytes)
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
            st.session_state["df_extraido"] = None
    else:
        st.session_state["df_extraido"] = None


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

def main():
    st.title("📉 Painel de Priorização de Perdas — Validade")
    st.caption(
        "Sobe o relatório de validade em PDF do ERP, o app extrai os itens "
        "com previsão de perda e monta a lista de prioridade."
    )

    if "df_extraido" not in st.session_state:
        st.session_state["df_extraido"] = None

    st.file_uploader(
        "Relatório de validade (PDF)", 
        type=["pdf"], 
        key="uploader_pdf", 
        on_change=gatilho_upload_pdf
    )

    if st.session_state["df_extraido"] is None:
        st.info("Aguardando o PDF do relatório de validade para começar.")
        st.stop()

    df = st.session_state["df_extraido"].copy()

    if df.empty:
        st.error(
            "Não consegui extrair linhas válidas do PDF. O layout pode ser "
            "diferente do esperado ou os valores de perda estão zerados."
        )
        st.stop()

    # Prepara identificadores únicos estáveis e remove itens zerados
    df = df[df["perda_rs"] > 0].copy()
    
    if df.empty:
        st.info("Todos os produtos deste relatório estão com Previsão de Perda zerada.")
        st.stop()
        
    df["chave"] = df.apply(chave_item, axis=1)

    # Carrega dados locais de persistência
    verificados = carrega_verificados()
    df["verificado"] = df["chave"].map(lambda k: verificados.get(k, False))

    def define_criticidade(dias):
        if dias <= 15:
            return "1. Crítico (Até 15 dias)"
        elif dias <= 30:
            return "2. Alerta Alto (16 a 30 dias)"
        elif dias <= 60:
            return "3. Atenção (31 a 60 dias)"
        else:
            return "4. Planejado (Acima de 60 dias)"

    df["faixa_criticidade"] = df["dias_vencer"].apply(define_criticidade)

    # --- Alerta de Produtos Não Verificados Críticos ---------------------
    nao_verificados_criticos = df[
        (~df["verificado"]) & (df["dias_vencer"] <= 30)
    ]
    
    if not nao_verificados_criticos.empty:
        total_critico_rs = nao_verificados_criticos["perda_rs"].sum()
        st.warning(
            f"⚠️ **Alerta de Atenção:** Existem **{len(nao_verificados_criticos)} itens críticos** "
            f"(vencimento em menos de 30 dias) que ainda **não foram verificados**. "
            f"Risco acumulado de **R$ {total_critico_rs:,.2f}**."
        )
    else:
        st.success("✅ Excelente! Todos os produtos com vencimento até 30 dias já foram auditados.")

    # --- Resumo geral -------------------------------------------------
    total_geral = df["perda_rs"].sum()
    total_verificado = df.loc[df["verificado"], "perda_rs"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Previsão total de perda", f"R$ {total_geral:,.2f}")
    col2.metric(
        "Verificado / resolvido",
        f"R$ {total_verificado:,.2f}",
        f"{(total_verificado / total_geral * 100) if total_geral else 0:.1f}% do total",
    )
    col3.metric("Itens com perda prevista", len(df))

    # --- Layout Visual: Gráficos --------------------------------------
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        resumo_cat = (
            df.groupby("categoria")["perda_rs"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        fig_cat = px.bar(
            resumo_cat,
            x="perda_rs",
            y="categoria",
            orientation="h",
            color="categoria",
            color_discrete_map=CORES_CATEGORIA,
            labels={"perda_rs": "Previsão de perda (R$)", "categoria": ""},
            title="Perda prevista por categoria",
        )
        fig_cat.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_graf2:
        resumo_crit = (
            df.groupby("faixa_criticidade")["perda_rs"]
            .sum()
            .reset_index()
            .sort_values("faixa_criticidade")
        )
        
        fig_crit = px.bar(
            resumo_crit,
            x="faixa_criticidade",
            y="perda_rs",
            color="faixa_criticidade",
            color_discrete_map={
                "1. Crítico (Até 15 dias)": "#C24A3F",
                "2. Alerta Alto (16 a 30 dias)": "#E3A23D",
                "3. Atenção (31 a 60 dias)": "#D9C25F",
                "4. Planejado (Acima de 60 dias)": "#7C9CC4"
            },
            labels={"perda_rs": "Previsão de perda (R$)", "faixa_criticidade": "Faixa de Vencimento"},
            title="Mapa de Criticidade (Impacto Financeiro por Faixa)",
        )
        fig_crit.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_crit, use_container_width=True)

    # --- Filtros ---------------------------------------------------------
    st.subheader("Lista de priorização")
    col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 1])
    with col_a:
        categoria_sel = st.multiselect(
            "Categoria", options=sorted(df["categoria"].unique()), default=[]
        )
    with col_b:
        criticidade_sel = st.multiselect(
            "Faixa de Criticidade", options=sorted(df["faixa_criticidade"].unique()), default=[]
        )
    with col_c:
        busca = st.text_input("Buscar produto")
    with col_d:
        ocultar_verificados = st.checkbox("Ocultar verificados")

    ordenar_por = st.radio(
        "Ordenar por", ["Maior R$", "Mais urgente (dias)"], horizontal=True
    )

    filtrado = df.copy()
    if categoria_sel:
        filtrado = filtrado[filtrado["categoria"].isin(categoria_sel)]
    if criticidade_sel:
        filtrado = filtrado[filtrado["faixa_criticidade"].isin(criticidade_sel)]
    if busca:
        filtrado = filtrado[filtrado["descricao"].str.contains(busca, case=False)]
    if ocultar_verificados:
        filtrado = filtrado[~filtrado["verificado"]]

    if ordenar_por == "Maior R$":
        filtrado = filtrado.sort_values("perda_rs", ascending=False)
    else:
        filtrado = filtrado.sort_values("dias_vencer", ascending=True)

    # --- Tabela editável inteligente -------------------------------------
    exibir = filtrado[["chave", "descricao", "categoria", "faixa_criticidade", "dias_vencer", "perda_rs", "verificado"]].copy()
    exibir = exibir.rename(columns={
        "descricao": "Produto",
        "categoria": "Categoria",
        "faixa_criticidade": "Criticidade",
        "dias_vencer": "Dias a vencer",
        "perda_rs": "Perda (R$)",
        "verificado": "Verificado",
    })

    editado = st.data_editor(
        exibir,
        column_config={
            "chave": None,
            "Perda (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Verificado": st.column_config.CheckboxColumn(),
        },
        hide_index=True,
        use_container_width=True,
        height=450,
        key="tabela_prioridade",
    )

    # Validação inteligente de persistência (evita loops infinitos de Rerun)
    houve_mudanca = False
    for _, row in editado.iterrows():
        k = row["chave"]
        v_novo = bool(row["Verificado"])
        if verificados.get(k, False) != v_novo:
            verificados[k] = v_novo
            houve_mudanca = True

    if houve_mudanca:
        salva_verificados(verificados)
        st.rerun()

    st.caption(
        f"{len(filtrado)} de {len(df)} itens exibidos. "
        "Marque como verificado ao tratar o item."
    )

    # --- Seção de Download / Exportação ---------------------------------
    st.markdown("---")
    st.subheader("📥 Exportar Relatório Atual")
    
    df_export = filtrado[["descricao", "categoria", "faixa_criticidade", "dias_vencer", "perda_rs", "verificado"]].rename(
        columns={
            "descricao": "Produto",
            "categoria": "Categoria",
            "faixa_criticidade": "Criticidade",
            "dias_vencer": "Dias a vencer",
            "perda_rs": "Perda (R$)",
            "verificado": "Verificado"
        }
    )

    exp_col1, exp_col2, exp_col3, _ = st.columns([1, 1, 1, 4])
    
    with exp_col1:
        st.download_button(
            label="📊 Baixar Excel",
            data=df_para_excel(df_export),
            file_name="relatorio_perdas_priorizado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    with exp_col2:
        st.download_button(
            label="📄 Baixar CSV",
            data=df_export.to_csv(index=False).encode('utf-8'),
            file_name="relatorio_perdas_priorizado.csv",
            mime="text/csv"
        )
        
    with exp_col3:
        st.download_button(
            label="📝 Baixar TXT",
            data=df_para_txt(df_export),
            file_name="relatorio_perdas_priorizado.txt",
            mime="text/plain"
        )


if __name__ == "__main__":
    main()