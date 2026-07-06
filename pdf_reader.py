"""Motor de Extração e Parsing de Arquivos PDF (ETL) - Versão Ultra Tolerante."""

import io
import pandas as pd
import pdfplumber
import streamlit as st
from typing import Optional
from config import CATEGORIAS_KEYWORDS
from utils import clean_num

def categoriza(descricao: str) -> str:
    """Classifica a categoria de produtos baseada em regras léxicas."""
    d = str(descricao).upper()
    for categoria, palavras in CATEGORIAS_KEYWORDS.items():
        if any(p in d for p in palavras):
            return categoria
    if d.endswith(" KG") or " KG" in d:
        return "Carnes/Aves"
    return "Outros"

@st.cache_data(show_spinner=False)
def extrair_pdf(arquivo_bytes: bytes) -> Optional[pd.DataFrame]:
    """Processa o binário do PDF do ERP de forma dinâmica e flexível."""
    rows = []
    try:
        with pdfplumber.open(io.BytesIO(arquivo_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for r in table:
                        # Remove a trava rígida de tamanho e aceita qualquer linha preenchida
                        if r and any(r):
                            rows.append(r)
                            
        if not rows:
            return None

        registros = []
        for r in rows:
            try:
                # Localiza dinamicamente as colunas baseado no tamanho real da linha extraída
                tamanho_linha = len(r)
                if tamanho_linha < 5: 
                    continue # Linha irrelevante ou quebra de página
                
                # Mapeamento seguro baseado nas posições relativas do relatório original
                desc = str(r[3] if tamanho_linha > 3 else r[0] or "").replace("\n", " ").strip()
                if not desc or desc.upper() in ["DESCRIÇÃO", "DESCRIÇÃO DO PRODUTO", "PRODUTO"]:
                    continue
                
                # Captura de dias a vencer de forma resiliente
                idx_dias = 13 if tamanho_linha > 13 else (tamanho_linha - 5 if tamanho_linha > 5 else 1)
                dias_raw = str(r[idx_dias] or "").replace("\n", "").strip()
                try:
                    dias = int(dias_raw)
                except ValueError:
                    dias = 0
                    
                # Captura de valores financeiros
                idx_perda = 17 if tamanho_linha > 17 else (tamanho_linha - 1)
                perda_rs = clean_num(r[idx_perda])
                
                # Ignorar linhas totalmente zeradas
                if perda_rs <= 0:
                    continue

                registros.append({
                    "descricao": desc.title(),
                    "dias_vencer": dias,
                    "perda_qtde": clean_num(r[16]) if tamanho_linha > 16 else 1.0,
                    "perda_rs": perda_rs,
                    "custo_liquido": clean_num(r[19]) if tamanho_linha > 19 else perda_rs,
                    "setor_erp": str(r[26] or "").replace("\n", "").strip() if tamanho_linha > 26 else "Geral",
                    "fornecedor": "Não Informado"
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