"""Fábrica de Componentes de Visualização Avançada com Plotly."""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config import CORES_CATEGORIA

def plot_barra_categorias(df: pd.DataFrame) -> go.Figure:
    resumo_cat = df.groupby("categoria")["perda_rs"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(
        resumo_cat, x="perda_rs", y="categoria", orientation="h",
        color="categoria", color_discrete_map=CORES_CATEGORIA,
        labels={"perda_rs": "Previsão (R$)", "categoria": ""},
        title="Impacto por Categoria"
    )
    fig.update_layout(showlegend=False, height=330, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def plot_pareto_criticidade(df: pd.DataFrame) -> go.Figure:
    resumo = df.groupby("faixa_criticidade")["perda_rs"].sum().reset_index().sort_values("perda_rs", ascending=False)
    resumo["cum_percentage"] = (resumo["perda_rs"].cumsum() / resumo["perda_rs"].sum()) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=resumo["faixa_criticidade"], y=resumo["perda_rs"], name="Custo Perda (R$)", marker_color="#C24A3F"))
    fig.add_trace(go.Scatter(x=resumo["faixa_criticidade"], y=resumo["cum_percentage"], name="% Acumulado", yaxis="y2", line=dict(color="#E3A23D", width=3)))
    
    fig.update_layout(
        title="Análise de Pareto por Faixa de Vencimento",
        yaxis=dict(title="Perda Financeira (R$)"),
        yaxis2=dict(title="Percentual Acumulado (%)", overlaying="y", side="right", range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=330, margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

def plot_gauge_resolucao(percentual: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=percentual,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Eficiência de Tratamento do Estoque"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#4FA98C"}}
    ))
    fig.update_layout(height=240, margin=dict(l=10, r=10, t=40, b=10))
    return fig