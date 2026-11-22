"""Motor de Normalização dos Dados e Conciliação Financeira."""

from __future__ import annotations

import hashlib
import re
from typing import Any

import pandas as pd

from src.inteligencia_artificial import APELIDOS_TABELAS
from src.protecao_dados_lgpd import SELO_PROTECAO_LGPD

DESCRICAO_COLUNAS: dict[str, str] = {
    "cod_produto": "o código identificador do produto",
    "nome_produto": "o nome comercial do produto",
    "tipo_produto": "a categoria Físico ou Digital",
    "marca_produtor": "a marca ou produtor responsável",
    "preco_venda": "o preço de venda convertido para número em reais",
    "comissao_creator_pct": "o percentual de comissão do creator em decimal",
    "status_produto": "a situação de liberação ou bloqueio do produto",
    "id_creator": "o código identificador do creator",
    "handle_social": "o perfil social do creator",
    "nome_civil_protegido": "o nome civil ocultado conforme LGPD",
    "cpf_cnpj_protegido": "o CPF/CNPJ ocultado conforme LGPD",
    "email_pix_protegido": "o e-mail Pix ocultado conforme LGPD",
    "tier_creator": "o nível do creator (Iniciante, Pro ou Embaixador)",
    "id_transacao": "o código único da venda",
    "data_pedido": "a data do pedido padronizada em AAAA-MM-DD",
    "cpf_comprador_protegido": "o CPF do comprador ocultado conforme LGPD",
    "email_cliente_protegido": "o e-mail do cliente ocultado conforme LGPD",
    "valor_bruto": "o valor bruto da venda convertido de texto R$ para número",
    "taxa_youshop_pct": "a taxa da YouShop padronizada para decimal",
    "status_checkout": "a situação da compra no checkout",
    "lote_pagamento": "o código do lote bancário",
    "destinatario_id": "o código do beneficiário do repasse",
    "categoria_repasse": "o tipo de movimentação (Comissão Creator, Repasse Produtor ou Solicitação de Saque)",
    "valor_pago": "o valor efetivamente pago convertido de texto R$ para número",
    "data_liquidacao": "a data de pagamento padronizada em AAAA-MM-DD",
    "status_banco": "a situação bancária (Liquidado ou Agendado)",
    "protocolo_risco": "o protocolo da ocorrência",
    "data_ocorrencia": "a data do estorno/contestação padronizada em AAAA-MM-DD",
    "tipo_incidente": "o tipo de incidente (Chargeback, Estorno ou Fraude)",
    "valor_estornado": "o valor estornado convertido para número",
    "motivo_detalhado": "a descrição do motivo da ocorrência",
}


def converter_moeda_para_numero(valor: Any) -> float:
    """Converte textos monetários ('R$ 1.200,50') ou números para decimal."""
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return round(float(valor), 2)

    texto = str(valor).strip()
    if not texto:
        return 0.0
    texto = re.sub(r"[R$\s]", "", texto)

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return round(float(texto), 2)
    except ValueError:
        return 0.0


def converter_percentual_para_decimal(valor: Any) -> float:
    """Converte '10%', '0.10' ou '10' para decimal (0.10)."""
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        num = float(valor)
        return num / 100.0 if num > 1.0 else num

    texto = str(valor).strip().replace("%", "").replace(",", ".")
    try:
        num = float(texto)
        return num / 100.0 if num > 1.0 or "%" in str(valor) else num
    except ValueError:
        return 0.0


def _interpretar_data_unica(valor: Any) -> pd.Timestamp | pd.NaT:
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, pd.Timestamp):
        return valor.normalize()
    texto = str(valor).strip()
    if not texto:
        return pd.NaT
    if re.match(r"^\d{4}-\d{2}-\d{2}", texto):
        return pd.to_datetime(texto[:10], format="%Y-%m-%d", errors="coerce")
    if re.match(r"^\d{2}/\d{2}/\d{4}", texto):
        return pd.to_datetime(texto[:10], format="%d/%m/%Y", errors="coerce")
    if re.match(r"^\d{2}-\d{2}-\d{4}", texto):
        return pd.to_datetime(texto[:10], format="%d-%m-%Y", errors="coerce")
    return pd.to_datetime(texto, dayfirst=True, errors="coerce")


def normalizar_coluna_datas(serie: pd.Series) -> pd.Series:
    """Padroniza datas em formatos variados para o padrão único AAAA-MM-DD."""
    convertida = serie.apply(_interpretar_data_unica)
    return convertida.dt.strftime("%Y-%m-%d").fillna("")


def _gerar_id_anonimo(valor: Any) -> str:
    texto = str(valor or "").strip()
    if not texto or texto == SELO_PROTECAO_LGPD:
        return "CLI-ANON"
    return "CLI-" + hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8].upper()


def normalizar_planilhas(
    tabelas_brutas: dict[str, pd.DataFrame],
    leitura_ia: dict[str, Any],
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Renomeia colunas conforme leitura, padroniza datas/moedas e gera frases diretas das alterações."""
    tabelas_normalizadas: dict[str, pd.DataFrame] = {}
    resumo_arquivos: dict[str, dict[str, Any]] = {}
    alteracoes: list[dict[str, Any]] = []

    for arq_info in leitura_ia.get("arquivos", []):
        nome_arq = arq_info["arquivo"]
        tabela_destino = arq_info["tabela_destino"]
        apelido = APELIDOS_TABELAS.get(tabela_destino, tabela_destino)
        setor = arq_info["setor_origem"]
        mapa = arq_info.get("mapeamento_dict") or {
            p["coluna_origem"]: p["coluna_padrao"] for p in arq_info.get("mapeamento", [])
        }

        if nome_arq not in tabelas_brutas:
            continue

        df = tabelas_brutas[nome_arq].copy()
        df = df.rename(columns=mapa)

        # Gera chave anônima de cliente antes de ocultar CPF/E-mail (para contagem na Controladoria)
        if tabela_destino == "vendas_recebidas":
            if "cpf_comprador_protegido" in df.columns:
                df["id_cliente_anonimo"] = df["cpf_comprador_protegido"].apply(_gerar_id_anonimo)
            elif "email_cliente_protegido" in df.columns:
                df["id_cliente_anonimo"] = df["email_cliente_protegido"].apply(_gerar_id_anonimo)
            else:
                df["id_cliente_anonimo"] = df.get("id_transacao", "").astype(str)

        for col in [c for c in df.columns if c.endswith("_protegido")]:
            df[col] = SELO_PROTECAO_LGPD

        if tabela_destino == "dim_produtos":
            if "preco_venda" in df.columns:
                df["preco_venda"] = df["preco_venda"].apply(converter_moeda_para_numero)
            if "comissao_creator_pct" in df.columns:
                df["comissao_creator_pct"] = df["comissao_creator_pct"].apply(converter_percentual_para_decimal)

        elif tabela_destino == "vendas_recebidas":
            if "data_pedido" in df.columns:
                df["data_pedido"] = normalizar_coluna_datas(df["data_pedido"])
                df["data_competencia"] = df["data_pedido"].str.slice(0, 7)
            if "valor_bruto" in df.columns:
                df["valor_bruto"] = df["valor_bruto"].apply(converter_moeda_para_numero)
            if "taxa_youshop_pct" in df.columns:
                df["taxa_youshop_pct"] = df["taxa_youshop_pct"].apply(converter_percentual_para_decimal)

        elif tabela_destino == "repasses_recebidos":
            if "data_liquidacao" in df.columns:
                df["data_liquidacao"] = normalizar_coluna_datas(df["data_liquidacao"])
            if "valor_pago" in df.columns:
                df["valor_pago"] = df["valor_pago"].apply(converter_moeda_para_numero)

        elif tabela_destino == "estornos_recebidos":
            if "data_ocorrencia" in df.columns:
                df["data_ocorrencia"] = normalizar_coluna_datas(df["data_ocorrencia"])
            if "valor_estornado" in df.columns:
                df["valor_estornado"] = df["valor_estornado"].apply(converter_moeda_para_numero)

        for col_orig, col_dest in mapa.items():
            desc_dado = DESCRICAO_COLUNAS.get(col_dest, f"o campo padronizado {col_dest}")
            alteracoes.append({
                "tabela_destino": apelido,
                "arquivo": nome_arq,
                "frase": (
                    f"Tabela {nome_arq}: a coluna {col_orig} virou a coluna {col_dest}, "
                    f"que traz {desc_dado}, e virou a {apelido}."
                ),
            })

        if tabela_destino in tabelas_normalizadas:
            tabelas_normalizadas[tabela_destino] = pd.concat(
                [tabelas_normalizadas[tabela_destino], df], ignore_index=True
            )
        else:
            tabelas_normalizadas[tabela_destino] = df

        resumo_arquivos[tabela_destino] = {
            "arquivo_origem": nome_arq,
            "setor_origem": setor,
            "total_registros": int(len(df)),
            "colunas_normalizadas": ", ".join(list(df.columns)),
        }

    return tabelas_normalizadas, resumo_arquivos, alteracoes


def conciliar_operacoes(tabelas: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Cruza as 5 bases normalizadas, confere as regras de divisão e separa acertos e divergências."""
    df_prod = tabelas.get("dim_produtos", pd.DataFrame()).copy()
    df_creat = tabelas.get("dim_creators", pd.DataFrame()).copy()
    df_vendas = tabelas.get("vendas_recebidas", pd.DataFrame()).copy()
    df_rep = tabelas.get("repasses_recebidos", pd.DataFrame()).copy()
    df_est = tabelas.get("estornos_recebidos", pd.DataFrame()).copy()

    if df_vendas.empty:
        raise ValueError("Nenhuma planilha de vendas foi carregada para conferência.")

    if not df_rep.empty:
        df_rep_vendas = df_rep[
            df_rep["categoria_repasse"].isin(["Comissao_Creator", "Repasse_Produtor"])
        ].copy()
        df_saques_raw = df_rep[df_rep["categoria_repasse"] == "Solicitacao_Saque"].copy()
    else:
        df_rep_vendas = pd.DataFrame()
        df_saques_raw = pd.DataFrame()

    if not df_rep_vendas.empty:
        rep_com = (
            df_rep_vendas[df_rep_vendas["categoria_repasse"] == "Comissao_Creator"]
            .groupby("id_transacao", as_index=False)
            .agg(
                comissao_paga=("valor_pago", "sum"),
                data_liquidacao_creator=("data_liquidacao", "first"),
                status_banco_creator=("status_banco", "first"),
                lote_pagamento=("lote_pagamento", "first"),
            )
        )
        rep_prod = (
            df_rep_vendas[df_rep_vendas["categoria_repasse"] == "Repasse_Produtor"]
            .groupby("id_transacao", as_index=False)
            .agg(
                repasse_pago=("valor_pago", "sum"),
                data_liquidacao_produtor=("data_liquidacao", "first"),
                status_banco_produtor=("status_banco", "first"),
            )
        )
        rep_qtd = (
            df_rep_vendas.groupby("id_transacao", as_index=False)
            .size()
            .rename(columns={"size": "qtd_repasses"})
        )
    else:
        rep_com = pd.DataFrame(columns=["id_transacao", "comissao_paga", "data_liquidacao_creator", "status_banco_creator", "lote_pagamento"])
        rep_prod = pd.DataFrame(columns=["id_transacao", "repasse_pago", "data_liquidacao_produtor", "status_banco_produtor"])
        rep_qtd = pd.DataFrame(columns=["id_transacao", "qtd_repasses"])

    if not df_est.empty:
        est_agr = (
            df_est.groupby("id_transacao", as_index=False)
            .agg(
                protocolo_risco=("protocolo_risco", "first"),
                tipo_incidente=("tipo_incidente", "first"),
                data_ocorrencia_estorno=("data_ocorrencia", "first"),
                valor_estornado=("valor_estornado", "sum"),
                motivo_estorno=("motivo_detalhado", "first"),
            )
        )
    else:
        est_agr = pd.DataFrame(columns=["id_transacao", "protocolo_risco", "tipo_incidente", "data_ocorrencia_estorno", "valor_estornado", "motivo_estorno"])

    df = df_vendas.merge(df_prod, on="cod_produto", how="left", suffixes=("", "_prod"))
    if not df_creat.empty:
        df = df.merge(
            df_creat[["id_creator", "handle_social", "tier_creator"]],
            on="id_creator",
            how="left",
        )
    else:
        df["handle_social"] = ""
        df["tier_creator"] = ""

    df = df.merge(rep_com, on="id_transacao", how="left")
    df = df.merge(rep_prod, on="id_transacao", how="left")
    df = df.merge(rep_qtd, on="id_transacao", how="left")
    df = df.merge(est_agr, on="id_transacao", how="left")

    df["qtd_repasses"] = df["qtd_repasses"].fillna(0).astype(int)
    df["comissao_paga"] = df["comissao_paga"].fillna(0.0).round(2)
    df["repasse_pago"] = df["repasse_pago"].fillna(0.0).round(2)
    df["valor_estornado"] = df["valor_estornado"].fillna(0.0).round(2)
    df["comissao_creator_pct"] = df["comissao_creator_pct"].fillna(0.0)
    df["taxa_youshop_pct"] = df["taxa_youshop_pct"].fillna(0.10)

    df["taxa_youshop_esperada"] = (df["valor_bruto"] * df["taxa_youshop_pct"]).round(2)
    df["comissao_esperada"] = (df["valor_bruto"] * df["comissao_creator_pct"]).round(2)
    df["repasse_produtor_esperado"] = (
        df["valor_bruto"] - df["taxa_youshop_esperada"] - df["comissao_esperada"]
    ).round(2)

    conciliados: list[dict[str, Any]] = []
    divergencias: list[dict[str, Any]] = []

    for _, linha in df.iterrows():
        sit_venda = str(linha.get("status_checkout", "")).strip()
        sit_prod = str(linha.get("status_produto", "")).strip()
        tem_estorno = pd.notna(linha.get("tipo_incidente")) and str(linha.get("tipo_incidente")).strip() != ""
        qtd_rep = int(linha.get("qtd_repasses", 0))

        com_esp = float(linha["comissao_esperada"])
        com_pag = float(linha["comissao_paga"])
        rep_esp = float(linha["repasse_produtor_esperado"])
        rep_pag = float(linha["repasse_pago"])

        dif_com = round(com_pag - com_esp, 2)
        dif_rep = round(rep_pag - rep_esp, 2)

        registro_base = {
            "id_transacao": linha["id_transacao"],
            "id_cliente_anonimo": linha.get("id_cliente_anonimo", ""),
            "data_pedido": linha["data_pedido"],
            "data_competencia": linha.get("data_competencia", str(linha["data_pedido"])[:7]),
            "cod_produto": linha["cod_produto"],
            "nome_produto": linha.get("nome_produto", ""),
            "tipo_produto": linha.get("tipo_produto", ""),
            "marca_produtor": linha.get("marca_produtor", ""),
            "status_produto": sit_prod,
            "id_creator": linha["id_creator"],
            "handle_social": linha.get("handle_social", ""),
            "tier_creator": linha.get("tier_creator", ""),
            "status_checkout": sit_venda,
            "valor_bruto": float(linha["valor_bruto"]),
            "taxa_youshop": float(linha["taxa_youshop_esperada"]),
            "comissao_creator": com_esp,
            "repasse_produtor": rep_esp,
            "comissao_paga": com_pag,
            "repasse_pago": rep_pag,
            "valor_estornado": float(linha["valor_estornado"]),
            "status_banco": linha.get("status_banco_creator") or linha.get("status_banco_produtor") or "Sem Registro",
            "lote_pagamento": linha.get("lote_pagamento") or "",
        }

        if sit_venda != "Aprovada":
            if qtd_rep > 0:
                divergencias.append({
                    **registro_base,
                    "tipo_divergencia": "Repasse Indevido em Venda Não Aprovada",
                    "valor_esperado": 0.0,
                    "valor_pago": round(com_pag + rep_pag, 2),
                    "impacto_financeiro": round(com_pag + rep_pag, 2),
                    "detalhe_tecnico": f"Pedido '{sit_venda}' possui repasse lançado.",
                })
            continue

        if tem_estorno:
            if qtd_rep > 0 and (
                linha.get("status_banco_creator") == "Liquidado"
                or linha.get("status_banco_produtor") == "Liquidado"
            ):
                total_liq = round(com_pag + rep_pag, 2)
                divergencias.append({
                    **registro_base,
                    "tipo_divergencia": "Contestação Pós-Pagamento (Devolução Necessária)",
                    "valor_esperado": 0.0,
                    "valor_pago": total_liq,
                    "impacto_financeiro": round(float(linha["valor_estornado"]), 2),
                    "detalhe_tecnico": (
                        f"{linha['tipo_incidente']} ({linha['protocolo_risco']}) em {linha['data_ocorrencia_estorno']} "
                        f"após pagamento em {linha['data_liquidacao_creator']}."
                    ),
                })
            else:
                divergencias.append({
                    **registro_base,
                    "tipo_divergencia": "Estorno / Contestação Antes do Pagamento",
                    "valor_esperado": 0.0,
                    "valor_pago": 0.0,
                    "impacto_financeiro": round(float(linha["valor_estornado"]), 2),
                    "detalhe_tecnico": f"{linha['tipo_incidente']} ({linha['protocolo_risco']}) registrado.",
                })
        elif sit_prod == "Bloqueado":
            divergencias.append({
                **registro_base,
                "tipo_divergencia": "Venda de Produto Bloqueado",
                "valor_esperado": 0.0,
                "valor_pago": round(com_pag + rep_pag, 2),
                "impacto_financeiro": float(linha["valor_bruto"]),
                "detalhe_tecnico": f"Produto {linha['cod_produto']} ({linha.get('nome_produto','')}) está com situação Bloqueado no catálogo.",
            })
        elif qtd_rep == 0:
            total_esp = round(com_esp + rep_esp, 2)
            divergencias.append({
                **registro_base,
                "tipo_divergencia": "Ausência de Repasse Financeiro",
                "valor_esperado": total_esp,
                "valor_pago": 0.0,
                "impacto_financeiro": total_esp,
                "detalhe_tecnico": "Venda aprovada sem nenhum registro de pagamento no Financeiro.",
            })
        elif abs(dif_com) > 1.00:
            pct_pago = (com_pag / float(linha["valor_bruto"])) * 100 if linha["valor_bruto"] else 0.0
            pct_regra = float(linha["comissao_creator_pct"]) * 100
            divergencias.append({
                **registro_base,
                "tipo_divergencia": "Erro de Percentual de Comissão",
                "valor_esperado": com_esp,
                "valor_pago": com_pag,
                "impacto_financeiro": round(abs(dif_com), 2),
                "detalhe_tecnico": (
                    f"Financeiro pagou {pct_pago:.1f}% (R$ {com_pag:.2f}), mas a regra vigente é "
                    f"{pct_regra:.1f}% (R$ {com_esp:.2f})."
                ),
            })
        elif (0.01 <= abs(dif_com) <= 1.00) or (0.01 <= abs(dif_rep) <= 1.00):
            dif_total = round(abs(dif_com) + abs(dif_rep), 2)
            divergencias.append({
                **registro_base,
                "tipo_divergencia": "Divergência de Centavos",
                "valor_esperado": round(com_esp + rep_esp, 2),
                "valor_pago": round(com_pag + rep_pag, 2),
                "impacto_financeiro": dif_total,
                "detalhe_tecnico": (
                    f"Diferença residual de R$ {dif_total:.2f} (Esperado R$ {com_esp + rep_esp:.2f} "
                    f"vs Pago R$ {com_pag + rep_pag:.2f})."
                ),
            })
        elif abs(dif_rep) > 1.00:
            divergencias.append({
                **registro_base,
                "tipo_divergencia": "Divergência de Valor de Repasse",
                "valor_esperado": rep_esp,
                "valor_pago": rep_pag,
                "impacto_financeiro": round(abs(dif_rep), 2),
                "detalhe_tecnico": f"Repasse ao produtor esperado R$ {rep_esp:.2f}, pago R$ {rep_pag:.2f}.",
            })
        else:
            conciliados.append({
                **registro_base,
                "status_conciliacao": "Conferido 100%",
            })

    df_fato_conc = pd.DataFrame(conciliados)

    # Conciliação de Solicitações de Saque dos Creators contra o saldo conciliado
    saques_rows: list[dict[str, Any]] = []
    if not df_saques_raw.empty:
        saldo_por_creator = (
            df_fato_conc.groupby("id_creator")["comissao_creator"].sum().to_dict()
            if not df_fato_conc.empty
            else {}
        )
        mapa_creators = (
            df_creat.set_index("id_creator")[["handle_social", "tier_creator"]].to_dict("index")
            if not df_creat.empty and "id_creator" in df_creat.columns
            else {}
        )
        for _, sq in df_saques_raw.iterrows():
            id_saque = str(sq.get("id_transacao", ""))
            id_creat = str(sq.get("destinatario_id", ""))
            data_sol = str(sq.get("data_liquidacao", ""))
            comp_sq = data_sol[:7] if len(data_sol) >= 7 else ""
            valor_sol = round(float(sq.get("valor_pago", 0.0)), 2)
            status_bco = str(sq.get("status_banco", "Agendado"))
            lote_sq = str(sq.get("lote_pagamento", ""))
            info_c = mapa_creators.get(id_creat, {})
            handle_c = str(info_c.get("handle_social", id_creat))
            tier_c = str(info_c.get("tier_creator", ""))
            saldo_disp = round(float(saldo_por_creator.get(id_creat, 0.0)), 2)

            if valor_sol > saldo_disp + 0.01:
                situacao_sq = "Bloqueado: Acima do Saldo"
                divergencias.append({
                    "id_transacao": id_saque,
                    "id_cliente_anonimo": "",
                    "data_pedido": data_sol,
                    "data_competencia": comp_sq,
                    "cod_produto": "SAQUE",
                    "nome_produto": "Solicitação de Saque Creator",
                    "tipo_produto": "Financeiro",
                    "marca_produtor": "YouShop Financeiro",
                    "status_produto": "N/A",
                    "id_creator": id_creat,
                    "handle_social": handle_c,
                    "tier_creator": tier_c,
                    "status_checkout": "Solicitação Saque",
                    "valor_bruto": valor_sol,
                    "taxa_youshop": 0.0,
                    "comissao_creator": saldo_disp,
                    "repasse_produtor": 0.0,
                    "comissao_paga": valor_sol,
                    "repasse_pago": 0.0,
                    "valor_estornado": 0.0,
                    "status_banco": status_bco,
                    "lote_pagamento": lote_sq,
                    "tipo_divergencia": "Saque Acima do Saldo Disponível",
                    "valor_esperado": saldo_disp,
                    "valor_pago": valor_sol,
                    "impacto_financeiro": round(valor_sol - saldo_disp, 2),
                    "detalhe_tecnico": (
                        f"Creator {id_creat} ({handle_c}) solicitou R$ {valor_sol:.2f}, "
                        f"mas tem saldo conciliado de R$ {saldo_disp:.2f}."
                    ),
                })
            else:
                situacao_sq = "Liberado (Dentro do Saldo)"

            saques_rows.append({
                "id_saque": id_saque,
                "lote_pagamento": lote_sq,
                "data_solicitacao": data_sol,
                "data_competencia": comp_sq,
                "id_creator": id_creat,
                "handle_social": handle_c,
                "tier_creator": tier_c,
                "valor_solicitado": valor_sol,
                "saldo_disponivel": saldo_disp,
                "status_banco": status_bco,
                "situacao_saque": situacao_sq,
            })

    df_saques = pd.DataFrame(saques_rows)

    # Resumo de todas as vendas (para o painel da Controladoria)
    df_resumo_vendas = df[
        [
            "id_transacao",
            "id_cliente_anonimo",
            "data_competencia",
            "cod_produto",
            "tipo_produto",
            "marca_produtor",
            "status_checkout",
            "valor_bruto",
        ]
    ].copy()

    return {
        "df_fato_conciliado": df_fato_conc,
        "df_divergencias": pd.DataFrame(divergencias),
        "df_saques": df_saques,
        "df_resumo_vendas": df_resumo_vendas,
        "df_dim_produtos": df_prod,
        "df_dim_creators": df_creat,
        "df_estornos": df_est,
        "tabelas_normalizadas": tabelas,
        "total_vendas_aprovadas": int((df["status_checkout"] == "Aprovada").sum()),
        "total_vendas_geral": int(len(df)),
    }
