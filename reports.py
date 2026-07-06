"""Módulo gerador de artefatos de dados e relatórios corporativos."""

import io
import pandas as pd

def gerar_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dashboard Executivo')
    return output.getvalue()

def gerar_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8')