"""Motor de Extração e Parsing de Arquivos PDF (ETL)."""

import io
import pandas as pd
import pdfplumber
import streamlit as st
from typing import Optional
from config import CATEGORIAS_KEYWORDS
from utils import clean_num

def categoriza(descricao: str) -> str:
    """Classifica a categoria de produtos baseada em regras léxicas e palavras-chave."""
    d = str(descricao).upper()
    for categoria, palavras in CATEGORIAS_KEYWORDS.items():
        if any(p in d for p in palavras):
            return categoria
    if d.endswith(" KG") or " KG" in d:
        return "Carnes/Aves"
    return "Outros"

@st.cache_data(show_spinner=False)
def extrair_pdf(arquivo_bytes: bytes) -> Optional[pd.DataFrame]:
    """Processa o binário do PDF do ERP e constrói o DataFrame sanitizado."""
    rows = []
    try:
        with pdfplumber.open(io.BytesIO(arquivo_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for r in table:
                        if r and len(r) >= 18:
                            rows.append(r)
                            
        if not rows:
            return None

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
                    
                perda_rs = clean_num(r[17]) if len(r) > 17 else 0.0
                if perda_rs <= 0:
                    continue

                registros.append({
                    "descricao": desc.title(),
                    "dias_vencer": dias,
                    "perda_qtde": clean_num(r[16]) if len(r) > 16 else 0.0,
                    "perda_rs": perda_rs,
                    "custo_liquido": clean_num(r[19]) if len(r) > 19 else 0.0,
                    "setor_erp": str(r[26] or "").replace("\n", "").strip() if len(r) > 26 else "Geral",
                    "fornecedor": "Não Informado" # Preparado para escala futura
                })
            except Exception:
                continue

        df = pd.DataFrame(registros)
        if df.empty:
            return None
            
        df["categoria"] = df["descricao"].apply(categoriza)
        return df
    except Exception as e:
        st.error(f"Falha de arquitetura na leitura do documento: {e}")
        return None