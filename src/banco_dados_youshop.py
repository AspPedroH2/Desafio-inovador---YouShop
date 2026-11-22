"""Base Central de Dados (SQLite) & Registros de Conferência por Setor."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

PASTA_RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_BANCO_PADRAO = PASTA_RAIZ / "data" / "youshop_dw.db"

CONSULTAS_PRONTAS: dict[str, str] = {
    "Ranking de Creators por Comissão Líquida": """SELECT
    c.id_creator AS codigo_creator,
    c.handle_social AS perfil_social,
    c.tier_creator AS categoria,
    COUNT(f.id_transacao) AS vendas_conferidas,
    ROUND(SUM(f.valor_bruto), 2) AS volume_vendas_brl,
    ROUND(SUM(f.comissao_creator), 2) AS comissao_liquida_brl
FROM fato_conciliacao_vendas f
LEFT JOIN dim_creators c ON f.id_creator = c.id_creator
GROUP BY c.id_creator, c.handle_social, c.tier_creator
ORDER BY comissao_liquida_brl DESC;""",
    "Margem Real por Marca descontando Estornos": """WITH estornos_marca AS (
    SELECT
        marca_produtor,
        ROUND(SUM(impacto_financeiro), 2) AS total_estornos
    FROM fato_divergencias
    WHERE tipo_divergencia LIKE '%Contestação%' OR tipo_divergencia LIKE '%Estorno%'
    GROUP BY marca_produtor
)
SELECT
    f.marca_produtor AS marca,
    COUNT(f.id_transacao) AS vendas_validas,
    ROUND(SUM(f.valor_bruto), 2) AS volume_bruto_brl,
    ROUND(SUM(f.taxa_youshop), 2) AS receita_youshop_brl,
    ROUND(SUM(f.repasse_produtor), 2) AS repasse_produtor_brl,
    COALESCE(e.total_estornos, 0.0) AS estornos_e_contestacoes_brl,
    ROUND(SUM(f.repasse_produtor) - COALESCE(e.total_estornos, 0.0), 2) AS margem_real_liquida_brl
FROM fato_conciliacao_vendas f
LEFT JOIN estornos_marca e ON f.marca_produtor = e.marca_produtor
GROUP BY f.marca_produtor, e.total_estornos
ORDER BY margem_real_liquida_brl DESC;""",
    "Produtos com Maior Índice de Problemas/Estorno": """WITH vendas_por_prod AS (
    SELECT cod_produto, nome_produto, marca_produtor, COUNT(*) AS vendas_ok
    FROM fato_conciliacao_vendas
    GROUP BY cod_produto, nome_produto, marca_produtor
),
div_estorno AS (
    SELECT cod_produto, nome_produto, marca_produtor,
           COUNT(*) AS qtd_ocorrencias,
           ROUND(SUM(impacto_financeiro), 2) AS valor_impactado
    FROM fato_divergencias
    GROUP BY cod_produto, nome_produto, marca_produtor
)
SELECT
    d.cod_produto AS codigo_produto,
    d.nome_produto AS produto,
    d.marca_produtor AS marca,
    d.qtd_ocorrencias,
    COALESCE(v.vendas_ok, 0) AS vendas_conferidas,
    ROUND(100.0 * d.qtd_ocorrencias / (d.qtd_ocorrencias + COALESCE(v.vendas_ok, 0)), 2) AS indice_erro_pct,
    d.valor_impactado AS impacto_financeiro_brl
FROM div_estorno d
LEFT JOIN vendas_por_prod v ON d.cod_produto = v.cod_produto
ORDER BY indice_erro_pct DESC, impacto_financeiro_brl DESC;""",
    "Resumo de Erros por Tipo e Impacto": """SELECT
    tipo_divergencia AS tipo_de_erro,
    COUNT(*) AS quantidade,
    ROUND(SUM(impacto_financeiro), 2) AS impacto_total_brl,
    GROUP_CONCAT(id_transacao, ', ') AS vendas_afetadas
FROM fato_divergencias
GROUP BY tipo_divergencia
ORDER BY impacto_total_brl DESC;""",
    "Histórico de Conferências por Setor": """SELECT
    setor_origem AS setor,
    modo_ingestao AS origem_envio,
    COUNT(*) AS total_envios,
    SUM(total_registros) AS linhas_recebidas,
    SUM(registros_conciliados) AS linhas_corretas,
    SUM(registros_divergentes) AS linhas_com_erro,
    ROUND(AVG(taxa_acuracia_pct), 2) AS taxa_acerto_media_pct
FROM logs_apuracao_setores
WHERE setor_origem IN ('Financeiro', 'Controladoria', 'Diretoria')
GROUP BY setor_origem, modo_ingestao
ORDER BY setor_origem;""",
    "Auditoria de Solicitações de Saque vs. Saldo": """SELECT
    id_saque AS codigo_saque,
    data_solicitacao AS data,
    id_creator AS codigo_creator,
    handle_social AS perfil_social,
    ROUND(saldo_disponivel, 2) AS saldo_disponivel_brl,
    ROUND(valor_solicitado, 2) AS valor_solicitado_brl,
    status_banco AS situacao_banco,
    situacao_saque AS analise_ia
FROM fato_saques
ORDER BY valor_solicitado DESC;""",
}


class GerenciadorBaseCentral:
    """Gerencia a Base Central de Dados em SQLite e os registros de conferência por setor."""

    def __init__(self, caminho_banco: Path | str | None = None):
        self.caminho_banco = Path(caminho_banco) if caminho_banco else CAMINHO_BANCO_PADRAO
        self.caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        self.inicializar_banco()

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(self.caminho_banco)

    def inicializar_banco(self) -> None:
        with self._conectar() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS logs_apuracao_setores (
                    id_log INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora_execucao TEXT NOT NULL,
                    data_competencia TEXT NOT NULL,
                    setor_origem TEXT NOT NULL,
                    modo_ingestao TEXT NOT NULL,
                    arquivo_origem TEXT NOT NULL,
                    total_registros INTEGER NOT NULL,
                    registros_conciliados INTEGER NOT NULL,
                    registros_divergentes INTEGER NOT NULL,
                    taxa_acuracia_pct REAL NOT NULL,
                    colunas_normalizadas TEXT,
                    status_governanca TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "UPDATE logs_apuracao_setores SET setor_origem = 'Controladoria' WHERE setor_origem = 'Operações'"
            )
            conn.execute(
                "UPDATE logs_apuracao_setores SET setor_origem = 'Financeiro' WHERE setor_origem = 'Comercial/Mkt'"
            )
            conn.commit()

    def gravar_conferencia(
        self,
        resultado_conciliacao: dict[str, Any],
        resumo_arquivos: dict[str, dict[str, Any]],
        modo_envio: str,
        data_competencia: str | None = None,
    ) -> list[dict[str, Any]]:
        """Grava cadastros, vendas conferidas, divergências e histórico por setor na Base Central."""
        df_prod = resultado_conciliacao["df_dim_produtos"]
        df_creat = resultado_conciliacao["df_dim_creators"]
        df_fato = resultado_conciliacao["df_fato_conciliado"]
        df_div = resultado_conciliacao["df_divergencias"]
        df_saques = resultado_conciliacao.get("df_saques", pd.DataFrame())
        df_resumo_vendas = resultado_conciliacao.get("df_resumo_vendas", pd.DataFrame())

        agora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not data_competencia:
            if not df_fato.empty and "data_competencia" in df_fato.columns:
                comps = sorted(df_fato["data_competencia"].dropna().unique().tolist())
                data_competencia = comps[-1] if comps else datetime.now().strftime("%Y-%m")
            else:
                data_competencia = datetime.now().strftime("%Y-%m")

        with self._conectar() as conn:
            if not df_prod.empty:
                df_prod.to_sql("dim_produtos", conn, if_exists="replace", index=False)
            if not df_creat.empty:
                df_creat.to_sql("dim_creators", conn, if_exists="replace", index=False)
            if not df_resumo_vendas.empty:
                df_resumo_vendas.to_sql("fato_resumo_vendas", conn, if_exists="replace", index=False)
            if df_saques.empty:
                df_saques = pd.DataFrame(
                    columns=[
                        "id_saque", "lote_pagamento", "data_solicitacao", "data_competencia",
                        "id_creator", "handle_social", "tier_creator", "valor_solicitado",
                        "saldo_disponivel", "status_banco", "situacao_saque",
                    ]
                )
            df_saques.to_sql("fato_saques", conn, if_exists="replace", index=False)

            if df_fato.empty:
                df_fato = pd.DataFrame(
                    columns=[
                        "id_transacao", "data_pedido", "data_competencia", "cod_produto",
                        "nome_produto", "tipo_produto", "marca_produtor", "status_produto",
                        "id_creator", "handle_social", "tier_creator", "status_checkout",
                        "valor_bruto", "taxa_youshop", "comissao_creator", "repasse_produtor",
                        "comissao_paga", "repasse_pago", "valor_estornado", "status_banco",
                        "lote_pagamento", "status_conciliacao",
                    ]
                )
            df_fato.to_sql("fato_conciliacao_vendas", conn, if_exists="replace", index=False)

            if df_div.empty:
                df_div = pd.DataFrame(
                    columns=[
                        "id_transacao", "data_pedido", "data_competencia", "cod_produto",
                        "nome_produto", "tipo_produto", "marca_produtor", "status_produto",
                        "id_creator", "handle_social", "tier_creator", "status_checkout",
                        "valor_bruto", "taxa_youshop", "comissao_creator", "repasse_produtor",
                        "comissao_paga", "repasse_pago", "valor_estornado", "status_banco",
                        "lote_pagamento", "tipo_divergencia", "valor_esperado", "valor_pago",
                        "impacto_financeiro", "detalhe_tecnico",
                    ]
                )
            df_div.to_sql("fato_divergencias", conn, if_exists="replace", index=False)

            qtd_conc = int(len(df_fato))
            qtd_div = int(len(df_div))

            registros_log: list[dict[str, Any]] = []
            mapa_setor_escopo = {
                "Controladoria": "Controladoria",
                "Financeiro": "Financeiro",
                "Operações": "Controladoria",
                "Comercial/Mkt": "Financeiro",
            }
            for chave_tab, meta in resumo_arquivos.items():
                total_reg = int(meta["total_registros"])
                setor = mapa_setor_escopo.get(meta["setor_origem"], "Controladoria")
                arq = meta["arquivo_origem"]
                cols_norm = meta["colunas_normalizadas"]

                if chave_tab == "vendas_recebidas":
                    conc_reg = qtd_conc
                    div_reg = qtd_div
                    base_val = conc_reg + div_reg
                    acuracia = round((conc_reg / base_val) * 100, 2) if base_val > 0 else 100.0
                    situacao = "Atenção: Divergências Detectadas" if div_reg > 0 else "Aprovado (100% Correto)"
                elif chave_tab == "repasses_recebidos":
                    div_rep = (
                        int(
                            df_div["tipo_divergencia"]
                            .str.contains("Repasse|Comissão|Centavos|Pós-Pagamento|Saque", case=False, na=False)
                            .sum()
                        )
                        if not df_div.empty
                        else 0
                    )
                    conc_reg = max(total_reg - div_rep, 0)
                    div_reg = div_rep
                    acuracia = round((conc_reg / total_reg) * 100, 2) if total_reg > 0 else 100.0
                    situacao = "Atenção: Divergências Detectadas" if div_reg > 0 else "Aprovado (100% Correto)"
                elif chave_tab == "estornos_recebidos":
                    div_est = (
                        int(
                            df_div["tipo_divergencia"]
                            .str.contains("Contestação|Estorno", case=False, na=False)
                            .sum()
                        )
                        if not df_div.empty
                        else 0
                    )
                    conc_reg = max(total_reg - div_est, 0)
                    div_reg = div_est
                    acuracia = round((conc_reg / total_reg) * 100, 2) if total_reg > 0 else 100.0
                    situacao = "Alerta de Risco / Devolução" if div_reg > 0 else "Monitorado"
                elif chave_tab == "dim_produtos":
                    div_prod = (
                        int(df_div["tipo_divergencia"].str.contains("Bloqueado", case=False, na=False).sum())
                        if not df_div.empty
                        else 0
                    )
                    conc_reg = max(total_reg - div_prod, 0)
                    div_reg = div_prod
                    acuracia = round((conc_reg / total_reg) * 100, 2) if total_reg > 0 else 100.0
                    situacao = "Alerta: Item Bloqueado Vendido" if div_reg > 0 else "Aprovado (100% Correto)"
                else:
                    conc_reg = total_reg
                    div_reg = 0
                    acuracia = 100.0
                    situacao = "Aprovado (100% Correto)"

                conn.execute(
                    """
                    INSERT INTO logs_apuracao_setores (
                        data_hora_execucao, data_competencia, setor_origem, modo_ingestao,
                        arquivo_origem, total_registros, registros_conciliados,
                        registros_divergentes, taxa_acuracia_pct, colunas_normalizadas, status_governanca
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        agora_str, data_competencia, setor, modo_envio,
                        arq, total_reg, conc_reg, div_reg, acuracia, cols_norm, situacao,
                    ),
                )
                registros_log.append(
                    {
                        "data_hora_execucao": agora_str,
                        "data_competencia": data_competencia,
                        "setor_origem": setor,
                        "modo_ingestao": modo_envio,
                        "arquivo_origem": arq,
                        "total_registros": total_reg,
                        "registros_conciliados": conc_reg,
                        "registros_divergentes": div_reg,
                        "taxa_acuracia_pct": acuracia,
                        "status_governanca": situacao,
                    }
                )

            # Registro consolidado da Diretoria (alimentada pela Controladoria e Financeiro)
            total_dir = qtd_conc + qtd_div
            acuracia_dir = round((qtd_conc / total_dir) * 100, 2) if total_dir > 0 else 100.0
            conn.execute(
                """
                INSERT INTO logs_apuracao_setores (
                    data_hora_execucao, data_competencia, setor_origem, modo_ingestao,
                    arquivo_origem, total_registros, registros_conciliados,
                    registros_divergentes, taxa_acuracia_pct, colunas_normalizadas, status_governanca
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agora_str,
                    data_competencia,
                    "Diretoria",
                    modo_envio,
                    "consolidado_executivo_diretoria",
                    total_dir,
                    qtd_conc,
                    qtd_div,
                    acuracia_dir,
                    "Indicadores Consolidados",
                    "Painel Executivo Atualizado",
                ),
            )
            registros_log.append(
                {
                    "data_hora_execucao": agora_str,
                    "data_competencia": data_competencia,
                    "setor_origem": "Diretoria",
                    "modo_ingestao": modo_envio,
                    "arquivo_origem": "consolidado_executivo_diretoria",
                    "total_registros": total_dir,
                    "registros_conciliados": qtd_conc,
                    "registros_divergentes": qtd_div,
                    "taxa_acuracia_pct": acuracia_dir,
                    "status_governanca": "Painel Executivo Atualizado",
                }
            )
            conn.commit()

        return registros_log

    def buscar_historico_conferencias(
        self, setor: str | None = None, data_filtro: str | None = None
    ) -> pd.DataFrame:
        sql = "SELECT * FROM logs_apuracao_setores WHERE setor_origem IN ('Financeiro', 'Controladoria', 'Diretoria')"
        parametros: list[Any] = []
        if setor and setor != "Todos":
            sql += " AND setor_origem = ?"
            parametros.append(setor)
        if data_filtro and data_filtro != "Todas":
            sql += " AND (data_competencia = ? OR substr(data_hora_execucao, 1, 10) = ?)"
            parametros.extend([data_filtro, data_filtro])
        sql += " ORDER BY id_log DESC"

        with self._conectar() as conn:
            return pd.read_sql_query(sql, conn, params=parametros)

    def listar_tabelas_base(self) -> list[dict[str, Any]]:
        nomes_amigaveis = {
            "dim_produtos": "Cadastro de Produtos (dProdutos)",
            "dim_creators": "Cadastro de Creators (dCreators)",
            "fato_conciliacao_vendas": "Vendas Conferidas (100% Corretas)",
            "fato_divergencias": "Vendas com Divergência (Auditoria)",
            "fato_saques": "Solicitações de Saque (Financeiro)",
            "fato_resumo_vendas": "Resumo Geral de Pedidos (Controladoria)",
            "logs_apuracao_setores": "Histórico de Cargas por Setor",
        }
        resultado: list[dict[str, Any]] = []
        with self._conectar() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            nomes = [r[0] for r in cur.fetchall()]
            for nome in nomes:
                qtd = conn.execute(f'SELECT COUNT(*) FROM "{nome}"').fetchone()[0]
                cols_info = conn.execute(f'PRAGMA table_info("{nome}")').fetchall()
                colunas = [c[1] for c in cols_info]
                resultado.append(
                    {
                        "tabela": nome,
                        "nome_amigavel": nomes_amigaveis.get(nome, nome),
                        "linhas": int(qtd),
                        "colunas": colunas,
                    }
                )
        return resultado

    def executar_consulta_leitura(self, consulta_sql: str) -> pd.DataFrame:
        sql_limpo = consulta_sql.strip().lstrip(";").strip()
        if not sql_limpo:
            raise ValueError("A consulta está vazia.")
        primeira_palavra = sql_limpo.split()[0].upper()
        if primeira_palavra not in ("SELECT", "WITH", "PRAGMA", "EXPLAIN"):
            raise ValueError("Por segurança, apenas consultas de leitura (SELECT / WITH) são permitidas.")
        with self._conectar() as conn:
            return pd.read_sql_query(sql_limpo, conn)

    def carregar_tabela(self, nome_tabela: str) -> pd.DataFrame:
        with self._conectar() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (nome_tabela,)
            )
            if not cur.fetchone():
                return pd.DataFrame()
            return pd.read_sql_query(f'SELECT * FROM "{nome_tabela}"', conn)

    def limpar_base_dados(self) -> None:
        """Apaga todas as tabelas e zera completamente a Base Central, o histórico e a sequência de IDs."""
        with self._conectar() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            for (nome_tabela,) in cur.fetchall():
                conn.execute(f'DROP TABLE IF EXISTS "{nome_tabela}"')
            try:
                conn.execute("DELETE FROM sqlite_sequence")
            except sqlite3.OperationalError:
                pass
            conn.commit()
        self.inicializar_banco()
