"""Módulo de regras de filtragem e ordenação dinâmica de dados."""

import pandas as pd
from typing import List

def aplicar_filtros_universais(
    df: pd.DataFrame, 
    categorias: List[str], 
    criticidades: List[str], 
    busca: str, 
    ocultar_verificados: bool, 
    ordenar_por: str
) -> pd.DataFrame:
    """Aplica múltiplos filtros sequenciais e regras de negócio de ordenação."""
    filtrado = df.copy()
    
    if categorias:
        filtrado = filtrado[filtrado["categoria"].isin(categorias)]
    if criticidades:
        filtrado = filtrado[filtrado["faixa_criticidade"].isin(criticidades)]
    if busca:
        filtrado = filtrado[filtrado["descricao"].str.contains(busca, case=False)]
    if ocultar_verificados:
        filtrado = filtrado[~filtrado["verificado"]]

    if ordenar_por == "Maior R$":
        filtrado = filtrado.sort_values("perda_rs", ascending=False)
    else:
        filtrado = filtrado.sort_values("dias_vencer", ascending=True)
        
    return filtrado