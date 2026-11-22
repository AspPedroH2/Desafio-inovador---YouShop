"""Camada de Inteligência Artificial (Gemini 2.5 Flash): leitura, relatório direto de normalização e auditoria."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None
    types = None

MODELO_GEMINI = "gemini-2.5-flash"

APELIDOS_TABELAS: dict[str, str] = {
    "dim_produtos": "dProdutos",
    "dim_creators": "dCreators",
    "vendas_recebidas": "fVendas",
    "repasses_recebidos": "fRepasses",
    "estornos_recebidos": "fEstornos",
}

ESQUEMA_BASE_CENTRAL = {
    "dim_produtos": {
        "setor": "Controladoria",
        "apelido": "dProdutos",
        "colunas": [
            "cod_produto", "nome_produto", "tipo_produto", "marca_produtor",
            "preco_venda", "comissao_creator_pct", "status_produto",
        ],
    },
    "dim_creators": {
        "setor": "Financeiro",
        "apelido": "dCreators",
        "colunas": [
            "id_creator", "handle_social", "nome_civil_protegido",
            "cpf_cnpj_protegido", "email_pix_protegido", "tier_creator",
        ],
    },
    "vendas_recebidas": {
        "setor": "Controladoria",
        "apelido": "fVendas",
        "colunas": [
            "id_transacao", "data_pedido", "cod_produto", "id_creator",
            "cpf_comprador_protegido", "email_cliente_protegido",
            "valor_bruto", "taxa_youshop_pct", "status_checkout",
        ],
    },
    "repasses_recebidos": {
        "setor": "Financeiro",
        "apelido": "fRepasses",
        "colunas": [
            "lote_pagamento", "id_transacao", "destinatario_id",
            "categoria_repasse", "valor_pago", "data_liquidacao", "status_banco",
        ],
    },
    "estornos_recebidos": {
        "setor": "Controladoria",
        "apelido": "fEstornos",
        "colunas": [
            "protocolo_risco", "id_transacao", "data_ocorrencia",
            "tipo_incidente", "valor_estornado", "motivo_detalhado",
        ],
    },
}


class ColunaMapeada(BaseModel):
    coluna_origem: str = Field(description="Nome exato da coluna na planilha enviada.")
    coluna_padrao: str = Field(description="Nome padronizado correspondente na Base Central da YouShop.")


class PontoIncerteza(BaseModel):
    coluna: str = Field(description="Nome da coluna desconhecida fora do padrão.")
    motivo_incerteza: str = Field(description="Explicação clara do motivo da revisão.")
    solucao_proposta: str = Field(description="Como o sistema propõe padronizar esse ponto.")


class LeituraPlanilhaIA(BaseModel):
    arquivo: str = Field(description="Nome do arquivo analisado.")
    tabela_destino: str = Field(description="Tabela destino na Base Central.")
    setor_origem: str = Field(description="Setor de origem (Controladoria ou Financeiro).")
    pontos_incerteza: list[PontoIncerteza] = Field(description="Colunas realmente desconhecidas.")
    mapeamento: list[ColunaMapeada] = Field(description="Correspondência de colunas.")
    observacoes: str = Field(description="Resumo curto sobre a leitura da planilha.")


class RespostaLeituraPlanilhas(BaseModel):
    arquivos: list[LeituraPlanilhaIA]


class FraseAlteracaoTabela(BaseModel):
    tabela_destino: str = Field(description="Nome da tabela normalizada: dProdutos, dCreators, fVendas, fRepasses ou fEstornos.")
    arquivo: str = Field(description="Nome do arquivo de origem.")
    frase: str = Field(
        description=(
            "Frase bem direta no formato: 'Tabela <arquivo>: a coluna <origem> virou a coluna <destino>, "
            "que traz <o que o dado representa>, e virou a <dProdutos/dCreators/fVendas/fRepasses/fEstornos>.'"
        )
    )


class RespostaRelatorioNormalizacao(BaseModel):
    frases: list[FraseAlteracaoTabela]


class DiagnosticoDivergencia(BaseModel):
    id_transacao: str = Field(description="Código da venda com divergência.")
    tipo_divergencia: str = Field(description="Classificação do problema encontrado.")
    causa_raiz: str = Field(description="Explicação executiva da causa do erro.")
    acao_recomendada: str = Field(description="Ação prática para resolver o problema.")
    setor_responsavel: str = Field(description="Setor responsável pela correção (Financeiro ou Controladoria).")
    severidade: str = Field(description="Alta, Média ou Baixa.")


class RespostaAuditoriaIA(BaseModel):
    diagnosticos: list[DiagnosticoDivergencia]
    briefing_diretoria: str = Field(
        description="Resumo executivo consolidado em 3 parágrafos claros para a Diretoria da YouShop."
    )


def _obter_cliente_gemini(chave_api: str | None = None):
    chave = (chave_api or os.environ.get("GEMINI_API_KEY", "")).strip()
    if not chave or genai is None:
        return None
    try:
        return genai.Client(api_key=chave)
    except Exception:
        return None


def _identificar_destino_por_colunas(colunas: list[str], nome_arquivo: str) -> tuple[str, str]:
    cols_min = {c.lower() for c in colunas}
    nome_min = nome_arquivo.lower()

    if any(k in cols_min for k in ("cod_prod", "nome_item", "comissao_creator_pct")) or "produto" in nome_min:
        return "dim_produtos", "Controladoria"
    if any(k in cols_min for k in ("id_afiliado", "handle_social", "tier_creator")) or "creator" in nome_min:
        return "dim_creators", "Financeiro"
    if any(k in cols_min for k in ("lote_pgto", "categoria_repasse", "vlr_pago_brl")) or "repasse" in nome_min:
        return "repasses_recebidos", "Financeiro"
    if any(k in cols_min for k in ("protocolo_risco", "tipo_incidente", "valor_estornado")) or "estorno" in nome_min or "chargeback" in nome_min:
        return "estornos_recebidos", "Controladoria"
    return "vendas_recebidas", "Controladoria"


def _mapear_coluna_local(col: str, tabela_destino: str) -> str:
    c = re.sub(r"[^a-z0-9]+", "_", col.lower()).strip("_")
    regras: dict[str, dict[str, str]] = {
        "dim_produtos": {
            "cod_prod": "cod_produto", "codigo_produto": "cod_produto",
            "nome_item": "nome_produto", "produto": "nome_produto",
            "tipo_produto": "tipo_produto", "marca_produtor": "marca_produtor",
            "marca": "marca_produtor", "preco_venda": "preco_venda",
            "comissao_creator_pct": "comissao_creator_pct", "status_produto": "status_produto",
        },
        "dim_creators": {
            "id_afiliado": "id_creator", "id_creator": "id_creator",
            "handle_social": "handle_social", "nome_civil": "nome_civil_protegido",
            "cpf_cnpj": "cpf_cnpj_protegido", "email_pix": "email_pix_protegido",
            "tier_creator": "tier_creator",
        },
        "vendas_recebidas": {
            "id_transacao": "id_transacao", "dt_pedido": "data_pedido",
            "data_pedido": "data_pedido", "ref_produto": "cod_produto",
            "cod_prod": "cod_produto", "codigo_link_creator": "id_creator",
            "id_creator": "id_creator", "cpf_comprador": "cpf_comprador_protegido",
            "email_cliente": "email_cliente_protegido", "valor_bruto_venda": "valor_bruto",
            "valor_bruto": "valor_bruto", "taxa_takerate_youshop": "taxa_youshop_pct",
            "status_checkout": "status_checkout",
        },
        "repasses_recebidos": {
            "lote_pgto": "lote_pagamento", "venda_origem_id": "id_transacao",
            "destinatario_id": "destinatario_id", "categoria_repasse": "categoria_repasse",
            "vlr_pago_brl": "valor_pago", "data_liquidacao": "data_liquidacao",
            "status_banco": "status_banco",
        },
        "estornos_recebidos": {
            "protocolo_risco": "protocolo_risco", "id_venda_ref": "id_transacao",
            "data_ocorrencia": "data_ocorrencia", "tipo_incidente": "tipo_incidente",
            "valor_estornado": "valor_estornado", "motivo_detalhado": "motivo_detalhado",
        },
    }
    return regras.get(tabela_destino, {}).get(c, c)


def _detectar_pontos_incerteza(tabela_destino: str, pares: list[dict[str, str]]) -> list[dict[str, str]]:
    """A IA resolve automaticamente formatos conhecidos; só aponta incerteza para colunas desconhecidas."""
    colunas_validas = set(ESQUEMA_BASE_CENTRAL.get(tabela_destino, {}).get("colunas", []))
    pontos: list[dict[str, str]] = []
    for par in pares:
        col_orig = par["coluna_origem"]
        col_pad = par["coluna_padrao"]
        if col_pad not in colunas_validas:
            pontos.append({
                "coluna": col_orig,
                "motivo_incerteza": f"Coluna '{col_orig}' não corresponde diretamente ao padrão esperado de '{tabela_destino}'.",
                "solucao_proposta": f"Manter como '{col_pad}' na importação ou revisar manualmente.",
            })
    return pontos


def _leitura_local_sem_ia(amostras_protegidas: list[dict[str, Any]]) -> dict[str, Any]:
    arquivos_lidos = []
    for amostra in amostras_protegidas:
        nome = amostra["arquivo"]
        colunas = amostra["colunas"]
        tabela, setor = _identificar_destino_por_colunas(colunas, nome)
        pares = [{"coluna_origem": col, "coluna_padrao": _mapear_coluna_local(col, tabela)} for col in colunas]
        pontos = _detectar_pontos_incerteza(tabela, pares)
        protegidas = amostra.get("colunas_protegidas", [])
        obs = f"Destino: '{APELIDOS_TABELAS.get(tabela, tabela)}'. " + (
            f"LGPD: {', '.join(protegidas)}." if protegidas else "Sem dados pessoais."
        )
        arquivos_lidos.append({
            "arquivo": nome,
            "tabela_destino": tabela,
            "setor_origem": setor,
            "pontos_incerteza": pontos,
            "mapeamento": pares,
            "mapeamento_dict": {p["coluna_origem"]: p["coluna_padrao"] for p in pares},
            "observacoes": obs,
        })

    return {"modo_motor": "Regras Automáticas Locais (Sem Chave Gemini)", "arquivos": arquivos_lidos}


def ler_e_mapear_planilhas(
    amostras_protegidas: list[dict[str, Any]],
    chave_api: str | None = None,
) -> dict[str, Any]:
    """Lê as amostras protegidas via Gemini 2.5 Flash (ou fallback local) atribuindo apenas Controladoria e Financeiro."""
    cliente = _obter_cliente_gemini(chave_api)
    if cliente is None:
        return _leitura_local_sem_ia(amostras_protegidas)

    instrucao = (
        "Você é um Especialista de Dados da YouShop. Analise as amostras protegidas (LGPD) abaixo e faça a correspondência "
        "exata das colunas para a Base Central da YouShop. Utilize APENAS os setores 'Controladoria' ou 'Financeiro' em setor_origem. "
        "Não inclua pontuações de confiabilidade.\n\n"
        f"ESQUEMA DA BASE CENTRAL:\n{json.dumps(ESQUEMA_BASE_CENTRAL, ensure_ascii=False, indent=2)}\n\n"
        f"AMOSTRAS PROTEGIDAS:\n{json.dumps(amostras_protegidas, ensure_ascii=False, indent=2)}"
    )

    try:
        resposta = cliente.models.generate_content(
            model=MODELO_GEMINI,
            contents=instrucao,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RespostaLeituraPlanilhas,
                temperature=0.1,
            ),
        )
        validado = RespostaLeituraPlanilhas.model_validate_json(resposta.text)
        arquivos_saida = []
        for item in validado.arquivos:
            d = item.model_dump()
            if d["setor_origem"] not in ("Controladoria", "Financeiro"):
                _, setor_corrigido = _identificar_destino_por_colunas(
                    [p["coluna_origem"] for p in d["mapeamento"]],
                    d["arquivo"],
                )
                d["setor_origem"] = setor_corrigido
            d["mapeamento_dict"] = {p["coluna_origem"]: p["coluna_padrao"] for p in d["mapeamento"]}
            arquivos_saida.append(d)
        return {"modo_motor": "Gemini 2.5 Flash (Conectado)", "arquivos": arquivos_saida}
    except Exception:
        return _leitura_local_sem_ia(amostras_protegidas)


def gerar_relatorio_normalizacao(
    alteracoes_detalhadas: list[dict[str, Any]],
    chave_api: str | None = None,
) -> dict[str, Any]:
    """Gera frases bem diretas explicando cada coluna alterada e em qual tabela normalizada virou."""
    cliente = _obter_cliente_gemini(chave_api)
    if cliente is None or not alteracoes_detalhadas:
        return {
            "modo_motor": "Relatório Direto Local",
            "frases": alteracoes_detalhadas,
        }

    instrucao = (
        "Você é o Engenheiro de Dados da YouShop. Transforme os registros de normalização abaixo em frases bem diretas "
        "em português, seguindo exatamente o padrão:\n"
        "'Tabela <arquivo>: a coluna <original> virou a coluna <padronizada>, que traz <descrição do dado>, e virou a <dProdutos/dCreators/fVendas/fRepasses/fEstornos>.'\n"
        "Não mencione confiabilidade nem termos técnicos em inglês.\n\n"
        f"ALTERAÇÕES APLICADAS:\n{json.dumps(alteracoes_detalhadas, ensure_ascii=False, indent=2)}"
    )
    try:
        resposta = cliente.models.generate_content(
            model=MODELO_GEMINI,
            contents=instrucao,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RespostaRelatorioNormalizacao,
                temperature=0.1,
            ),
        )
        validado = RespostaRelatorioNormalizacao.model_validate_json(resposta.text)
        return {
            "modo_motor": "Gemini 2.5 Flash (Conectado)",
            "frases": [f.model_dump() for f in validado.frases],
        }
    except Exception:
        return {
            "modo_motor": "Relatório Direto Local",
            "frases": alteracoes_detalhadas,
        }


def _auditoria_local_sem_ia(df_excecoes: pd.DataFrame, resumo_indicadores: dict[str, Any]) -> dict[str, Any]:
    diagnosticos = []
    for _, linha in df_excecoes.iterrows():
        id_tx = str(linha.get("id_transacao", "N/A"))
        tipo = str(linha.get("tipo_divergencia", "Divergência"))
        detalhe = str(linha.get("detalhe_tecnico", ""))
        impacto = float(linha.get("impacto_financeiro", 0.0) or 0.0)

        if "Contestação" in tipo or "Chargeback" in tipo:
            causa = f"Venda {id_tx} paga pelo Financeiro antes do prazo de segurança; contestação registrada posteriormente ({detalhe})."
            acao = "Descontar comissão do creator e repasse do produtor nos próximos lotes."
            setor, sev = "Financeiro e Controladoria", "Alta"
        elif "Comissão" in tipo:
            causa = f"Percentual pago diferente da regra de Produtos na venda {id_tx} ({detalhe})."
            acao = "Ajustar diferença no próximo lote e corrigir alíquota cadastrada."
            setor, sev = "Financeiro", "Alta"
        elif "Bloqueado" in tipo:
            causa = f"Venda {id_tx} aprovada para item marcado como 'Bloqueado' ({detalhe})."
            acao = "Reter repasse na Controladoria e bloquear novas vendas do item."
            setor, sev = "Controladoria", "Alta"
        elif "Ausência de Repasse" in tipo:
            causa = f"Venda {id_tx} aprovada no checkout, mas ausente no Financeiro ({detalhe})."
            acao = "Incluir em lote extra de pagamento e checar fila de integração."
            setor, sev = "Financeiro", "Média"
        elif "Saque" in tipo:
            causa = f"Solicitação de saque {id_tx} ultrapassa o saldo conciliado disponível do creator ({detalhe})."
            acao = "Bloquear pagamento do saque antes da liquidação bancária e auditar extrato do creator."
            setor, sev = "Financeiro", "Alta"
        else:
            causa = f"Diferença de arredondamento de R$ {impacto:,.2f} na venda {id_tx} ({detalhe})."
            acao = "Padronizar arredondamento em 2 casas decimais."
            setor, sev = "Controladoria e Financeiro", "Baixa"

        diagnosticos.append({
            "id_transacao": id_tx,
            "tipo_divergencia": tipo,
            "causa_raiz": causa,
            "acao_recomendada": acao,
            "setor_responsavel": setor,
            "severidade": sev,
        })

    vol_vendas = resumo_indicadores.get("volume_vendas_aprovadas", 0.0)
    receita = resumo_indicadores.get("receita_youshop", 0.0)
    qtd_div = len(diagnosticos)
    impacto_total = resumo_indicadores.get("impacto_divergencias", 0.0)
    taxa_acerto = resumo_indicadores.get("taxa_conciliacao_pct", 0.0)

    briefing = (
        f"No fechamento consolidado da YouShop, o volume de vendas aprovadas somou R$ {vol_vendas:,.2f}, "
        f"gerando receita líquida de R$ {receita:,.2f} com taxa de conciliação de {taxa_acerto:.1f}% entre Controladoria e Financeiro.\n\n"
        f"A auditoria isolou {qtd_div} ocorrências com divergências, somando R$ {impacto_total:,.2f} em risco ou diferença "
        f"(contestação pós-pagamento, comissão incorreta, item bloqueado, repasse omitido, centavos e saque acima do saldo).\n\n"
        f"Recomenda-se reter o repasse do item bloqueado e o saque acima do saldo, recuperar valores de contestação no próximo lote e regularizar o repasse omitido."
    )

    return {"modo_motor": "Regras Automáticas Locais (Sem Chave Gemini)", "diagnosticos": diagnosticos, "briefing_diretoria": briefing}


def auditar_divergencias(
    df_excecoes: pd.DataFrame,
    resumo_indicadores: dict[str, Any],
    chave_api: str | None = None,
) -> dict[str, Any]:
    """Analisa apenas as vendas com erro via Gemini 2.5 Flash (ou fallback local)."""
    if df_excecoes.empty:
        return {
            "modo_motor": "Conferência Automática (Sem Erros)",
            "diagnosticos": [],
            "briefing_diretoria": "Todas as vendas aprovadas foram 100% conferidas sem divergências.",
        }

    colunas_seguras = [
        c for c in df_excecoes.columns
        if c in (
            "id_transacao", "data_pedido", "cod_produto", "nome_produto",
            "marca_produtor", "id_creator", "valor_bruto", "tipo_divergencia",
            "impacto_financeiro", "valor_esperado", "valor_pago", "detalhe_tecnico",
        )
    ]
    payload_excecoes = df_excecoes[colunas_seguras].to_dict(orient="records")

    cliente = _obter_cliente_gemini(chave_api)
    if cliente is None:
        return _auditoria_local_sem_ia(df_excecoes, resumo_indicadores)

    instrucao = (
        "Você é o Auditor Chefe de Controladoria da YouShop. Analise apenas as vendas com erro abaixo "
        "(sem dados pessoais) e o resumo de indicadores.\n"
        "Para cada venda com erro, explique a causa e a ação recomendada em português claro, indicando como setor_responsavel "
        "apenas 'Financeiro', 'Controladoria' ou 'Financeiro e Controladoria'.\n"
        "Depois, escreva um resumo executivo de 3 parágrafos para a Diretoria.\n\n"
        f"INDICADORES:\n{json.dumps(resumo_indicadores, ensure_ascii=False, indent=2)}\n\n"
        f"VENDAS COM ERRO:\n{json.dumps(payload_excecoes, ensure_ascii=False, indent=2)}"
    )

    try:
        resposta = cliente.models.generate_content(
            model=MODELO_GEMINI,
            contents=instrucao,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RespostaAuditoriaIA,
                temperature=0.2,
            ),
        )
        validado = RespostaAuditoriaIA.model_validate_json(resposta.text)
        return {
            "modo_motor": "Gemini 2.5 Flash (Conectado)",
            "diagnosticos": [d.model_dump() for d in validado.diagnosticos],
            "briefing_diretoria": validado.briefing_diretoria,
        }
    except Exception:
        return _auditoria_local_sem_ia(df_excecoes, resumo_indicadores)
