"""Funções Utilitárias e de Limpeza de Dados de Entrada."""

import re
from typing import Any

def clean_num(s: Any) -> float:
    """Converte valores brutos em strings financeiras pt-BR para float nativo de forma segura."""
    if s is None:
        return 0.0
    s = str(s).replace("\n", "").replace("R$", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

def gerar_chave_item(descricao: str, dias_vencer: int, perda_rs: float) -> str:
    """Gera hash estável de identificação única para cada registro do relatório."""
    desc_limpa = re.sub(r'\s+', '', descricao).upper()
    return f"{desc_limpa}|{dias_vencer}|{perda_rs:.2f}"