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
    if not s:
        return 0.0
    s = s.replace("\n", "").replace("R$", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def categoriza(descricao: str) -> str:
    d = descricao.upper()
    for categoria, palavras in CATEGORIAS_KEYWORDS.items():
        if any(p in d for p in palavras):
            return categoria
    if d.endswith(" KG") or " KG" in d:
        return "Carnes/Aves"
    return "Outros"


@st.cache_data(show_spinner=False)
def extrair_pdf(arquivo_bytes: bytes) -> pd.DataFrame:
    """Extrai as linhas do relatório de validade do ERP (layout Bluesoft).

    Ajuste os índices de coluna abaixo se o layout do seu ERP for diferente
    — rode `debug_colunas()` (mais abaixo) numa página de teste pra conferir.
    """
    rows = []
    with pdfplumber.open(arquivo_bytes) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for r in table:
                    if r and len(r) >= 27:
                        rows.append(r)

    registros = []
    for r in rows:
        desc = (r[3] or "").replace("\n", " ").strip()
        if not desc or desc.upper() == "DESCRIÇÃO":
            continue
        dias_raw = (r[13] or "").replace("\n", "").strip()
        try:
            dias = int(dias_raw)
        except ValueError:
            dias = 0
        registros.append({
            "descricao": desc.title(),
            "dias_vencer": dias,
            "perda_qtde": clean_num(r[16]),
            "perda_rs": clean_num(r[17]),
            "custo_liquido": clean_num(r[19]),
            "setor_erp": (r[26] or "").replace("\n", "").strip(),
        })

    df = pd.DataFrame(registros)
    if df.empty:
        return df
    df["categoria"] = df["descricao"].apply(categoriza)
    return df


def debug_colunas(arquivo_bytes: bytes, pagina: int = 1):
    """Ajuda a conferir o índice das colunas se o layout do seu ERP mudar.
    Chame manualmente durante o desenvolvimento, não faz parte do fluxo do app.
    """
    with pdfplumber.open(arquivo_bytes) as pdf:
        tabela = pdf.pages[pagina].extract_tables()[0]
        for i, valor in enumerate(tabela[0]):
            print(i, repr(valor))


# ---------------------------------------------------------------------------
# Persistência local do estado "verificado"
# ---------------------------------------------------------------------------

def carrega_verificados() -> dict:
    if VERIFICADOS_PATH.exists():
        return json.loads(VERIFICADOS_PATH.read_text())
    return {}


def salva_verificados(d: dict):
    VERIFICADOS_PATH.write_text(json.dumps(d, ensure_ascii=False))


def chave_item(row) -> str:
    """Chave estável por item — usa descrição + dias, já que o relatório
    não traz um ID único explícito nas colunas extraídas."""
    return f"{row['descricao']}|{row['dias_vencer']}|{row['perda_rs']}"


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

def main():
    st.title("📉 Painel de Priorização de Perdas — Validade")
    st.caption(
        "Sobe o relatório de validade em PDF do ERP, o app extrai os itens "
        "com previsão de perda e monta a lista de prioridade."
    )

    arquivo = st.file_uploader("Relatório de validade (PDF)", type=["pdf"])

    if arquivo is None:
        st.info("Aguardando o PDF do relatório de validade para começar.")
        st.stop()

    with st.spinner("Extraindo dados do PDF..."):
        df = extrair_pdf(arquivo)

    if df.empty:
        st.error(
            "Não consegui extrair linhas do PDF. O layout pode ser "
            "diferente do esperado — avise que ajustamos os índices de coluna."
        )
        st.stop()

    df = df[df["perda_rs"] > 0].copy()
    df["chave"] = df.apply(chave_item, axis=1)

    verificados = carrega_verificados()
    df["verificado"] = df["chave"].map(lambda k: verificados.get(k, False))

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

    # --- Gráfico por categoria -----------------------------------------
    resumo_cat = (
        df.groupby("categoria")["perda_rs"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    fig = px.bar(
        resumo_cat,
        x="perda_rs",
        y="categoria",
        orientation="h",
        color="categoria",
        color_discrete_map=CORES_CATEGORIA,
        labels={"perda_rs": "Previsão de perda (R$)", "categoria": ""},
        title="Perda prevista por categoria",
    )
    fig.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig, use_container_width=True)

    # --- Filtros ---------------------------------------------------------
    st.subheader("Lista de priorização")
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        categoria_sel = st.multiselect(
            "Categoria", options=sorted(df["categoria"].unique()), default=[]
        )
    with col_b:
        busca = st.text_input("Buscar produto")
    with col_c:
        ocultar_verificados = st.checkbox("Ocultar verificados")

    ordenar_por = st.radio(
        "Ordenar por", ["Maior R$", "Mais urgente (dias)"], horizontal=True
    )

    filtrado = df.copy()
    if categoria_sel:
        filtrado = filtrado[filtrado["categoria"].isin(categoria_sel)]
    if busca:
        filtrado = filtrado[filtrado["descricao"].str.contains(busca, case=False)]
    if ocultar_verificados:
        filtrado = filtrado[~filtrado["verificado"]]

    if ordenar_por == "Maior R$":
        filtrado = filtrado.sort_values("perda_rs", ascending=False)
    else:
        filtrado = filtrado.sort_values("dias_vencer", ascending=True)

    # --- Tabela editável (checkbox de verificado) ------------------------
    exibir = filtrado[["chave", "descricao", "categoria", "dias_vencer", "perda_rs", "verificado"]].copy()
    exibir = exibir.rename(columns={
        "descricao": "Produto",
        "categoria": "Categoria",
        "dias_vencer": "Dias a vencer",
        "perda_rs": "Perda (R$)",
        "verificado": "Verificado",
    })

    editado = st.data_editor(
        exibir,
        column_config={
            "chave": None,  # oculta a coluna de chave interna
            "Perda (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Verificado": st.column_config.CheckboxColumn(),
        },
        hide_index=True,
        use_container_width=True,
        height=560,
        key="tabela_prioridade",
    )

    # Salva qualquer mudança de checkbox
    for _, row in editado.iterrows():
        verificados[row["chave"]] = bool(row["Verificado"])
    salva_verificados(verificados)

    st.caption(
        f"{len(filtrado)} de {len(df)} itens exibidos. "
        "Marque como verificado ao tratar o item (retirar, promover ou devolver)."
    )


if __name__ == "__main__":
    main()