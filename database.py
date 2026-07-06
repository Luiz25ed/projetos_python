"""Camada de persistência robusta em SQLite3 com tratamento de exceções e logging."""

import sqlite3
import logging
from typing import Dict, Any, List
from datetime import datetime
from config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão ativa com o banco de dados SQLite."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Cria a estrutura das tabelas caso não existam no SQLite (DDL)."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Tabela de Configurações do Sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. Tabela de Usuários (Preparada para Auth/Perfis)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    perfil TEXT NOT NULL CHECK(perfil IN ('Master', 'Auditor', 'Operador')),
                    ativo INTEGER DEFAULT 1
                )
            """)
            
            # 3. Tabela de Produtos Verificados (Estado Atual)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS produtos_verificados (
                    chave_item TEXT PRIMARY KEY,
                    descricao TEXT NOT NULL,
                    dias_vencer INTEGER NOT NULL,
                    perda_rs REAL NOT NULL,
                    verificado INTEGER DEFAULT 0,
                    loja_id TEXT DEFAULT '001',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. Tabela de Histórico e Auditoria de Verificações
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico_verificacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chave_item TEXT NOT NULL,
                    usuario_id INTEGER,
                    status_anterior INTEGER,
                    status_novo INTEGER,
                    data_modificacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(chave_item) REFERENCES produtos_verificados(chave_item)
                )
            """)
            conn.commit()
            logging.info("Banco de dados SQLite inicializado com sucesso.")
    except sqlite3.Error as e:
        logging.error(f"Erro Crítico ao inicializar banco de dados: {e}")

def buscar_verificados() -> Dict[str, bool]:
    """Retorna um dicionário com o estado de verificação atual de todos os itens."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chave_item, verificado FROM produtos_verificados")
            return {row["chave_item"]: bool(row["verificado"]) for row in cursor.fetchall()}
    except sqlite3.Error as e:
        logging.error(f"Erro ao buscar verificados: {e}")
        return {}

def salvar_estado_verificado(chave: str, descricao: str, dias: int, perda: float, verificado: bool) -> None:
    """Atualiza ou insere o estado de um produto e registra no histórico de auditoria."""
    try:
        v_int = 1 if verificado else 0
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Captura o estado anterior para auditoria
            cursor.execute("SELECT verificado FROM produtos_verificados WHERE chave_item = ?", (chave,))
            row = cursor.fetchone()
            status_anterior = row["verificado"] if row else None
            
            if status_anterior != v_int:
                cursor.execute("""
                    INSERT INTO produtos_verificados (chave_item, descricao, dias_vencer, perda_rs, verificado, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(chave_item) DO UPDATE SET 
                        verificado = excluded.verificado,
                        updated_at = CURRENT_TIMESTAMP
                """, (chave, descricao, dias, perda, v_int))
                
                cursor.execute("""
                    INSERT INTO historico_verificacoes (chave_item, usuario_id, status_anterior, status_novo)
                    VALUES (?, 1, ?, ?)
                """, (chave, status_anterior, v_int))
                
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Erro ao salvar estado verificado para a chave {chave}: {e}")

def obter_historico_completo() -> List[Dict[str, Any]]:
    """Retorna a lista completa do log de auditoria do sistema."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h.id, h.chave_item, h.status_anterior, h.status_novo, h.data_modificacao, p.descricao
                FROM historico_verificacoes h
                JOIN produtos_verificados p ON h.chave_item = p.chave_item
                ORDER BY h.data_modificacao DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Erro ao obter histórico: {e}")
        return []