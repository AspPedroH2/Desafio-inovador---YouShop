"""Gerador de planilhas de teste realistas e heterogêneas para a YouShop."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_AMOSTRAS = PASTA_RAIZ / "data" / "samples"


def _formatar_moeda_brl(valor: float) -> str:
    """Formata um número para moeda brasileira em texto, ex: 'R$ 1.200,50'."""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _formatar_data_mista(dt: datetime, indice: int) -> str:
    """Alterna formatos de data propositalmente para simular planilhas de setores diferentes."""
    resto = indice % 3
    if resto == 0:
        return dt.strftime("%Y-%m-%d")
    if resto == 1:
        return dt.strftime("%d/%m/%Y")
    return dt.strftime("%d-%m-%Y")


def gerar_planilhas_teste(pasta_destino: Path | None = None) -> dict[str, Path]:
    """Gera as 5 planilhas fictícias da YouShop com 5 divergências propositais para auditoria."""
    aleatorio = random.Random(42)
    destino = Path(pasta_destino) if pasta_destino else PASTA_AMOSTRAS
    destino.mkdir(parents=True, exist_ok=True)

    # 1. Produtos (Operações/Comercial) - 12 itens
    produtos_lista = [
        ("PRD-101", "Whey Protein Isolado 900g", "Físico", "VitaLab Nutrition", 189.90, 0.20, "Aprovado"),
        ("PRD-102", "Creatina Monohidratada 300g", "Físico", "VitaLab Nutrition", 119.90, 0.18, "Aprovado"),
        ("PRD-103", "Termogênico Ultra Burn 60 caps", "Físico", "VitaLab Nutrition", 149.00, 0.25, "Aprovado"),
        ("PRD-104", "Sérum Facial Vitamina C 30ml", "Físico", "Aura Dermocosméticos", 159.90, 0.22, "Aprovado"),
        ("PRD-105", "Kit Skincare Anti-Idade", "Físico", "Aura Dermocosméticos", 329.00, 0.25, "Aprovado"),
        ("PRD-106", "Protetor Solar Toque Seco FPS70", "Físico", "Aura Dermocosméticos", 89.90, 0.15, "Aprovado"),
        ("PRD-107", "Colágeno Hidrolisado Verisol", "Físico", "Aura Dermocosméticos", 139.00, 0.20, "Aprovado"),
        ("PRD-108", "Curso Tráfego Pago para Creators", "Digital", "Academia Creator", 497.00, 0.35, "Aprovado"),
        ("PRD-109", "Mentoria Escala Digital 90D", "Digital", "Academia Creator", 997.00, 0.40, "Aprovado"),
        ("PRD-110", "Curso Edição Viral Reels", "Digital", "Academia Creator", 297.00, 0.30, "Aprovado"),
        ("PRD-111", "Plataforma CRM CreatorFlow (Anual)", "Digital", "FlowTech SaaS", 790.00, 0.20, "Aprovado"),
        ("PRD-112", "SaaS Automação LinkBio Pro (Bloqueado)", "Digital", "FlowTech SaaS", 249.00, 0.25, "Bloqueado"),
    ]
    df_produtos = pd.DataFrame(
        produtos_lista,
        columns=[
            "Cod_Prod",
            "Nome_Item",
            "Tipo_Produto",
            "Marca_Produtor",
            "Preco_Venda",
            "Comissao_Creator_Pct",
            "Status_Produto",
        ],
    )
    arq_produtos = destino / "01_produtos_marcas_operacoes.xlsx"
    df_produtos.to_excel(arq_produtos, index=False)

    # 2. Creators (Marketing/Atendimento) - 15 parceiros
    creators_lista = [
        ("CRT-001", "@camilafit", "Camila Almeida Costa", "124.587.963-10", "camila.almeida@gmail.com", "Embaixador"),
        ("CRT-002", "@lucas.tech", "Lucas Ferreira Rocha", "238.941.520-44", "lucas.rocha@techmail.com", "Pro"),
        ("CRT-003", "@julianabeauty", "Juliana Mendes Silva", "349.102.874-22", "ju.mendes@outlook.com", "Embaixador"),
        ("CRT-004", "@rafael.nutri", "Rafael Nogueira Lima", "451.209.338-91", "rafael.nutri@gmail.com", "Pro"),
        ("CRT-005", "@bia.skincare", "Beatriz Oliveira Santos", "562.398.114-05", "bia.oliveira@icloud.com", "Pro"),
        ("CRT-006", "@thiago.ads", "Thiago Barbosa Martins", "18.432.901/0001-55", "financeiro@thiagoads.com.br", "Embaixador"),
        ("CRT-007", "@marina.wellness", "Marina Souza Ribeiro", "673.441.229-78", "marina.ribeiro@gmail.com", "Iniciante"),
        ("CRT-008", "@pedro.dev", "Pedro Henrique Dias", "784.552.310-19", "pedro.dias@devmail.io", "Pro"),
        ("CRT-009", "@larissa.glow", "Larissa Castro Pereira", "895.663.421-60", "larissa.glow@gmail.com", "Iniciante"),
        ("CRT-010", "@gustavo.performance", "Gustavo Azevedo Cunha", "906.774.532-33", "gustavo.cunha@yahoo.com.br", "Pro"),
        ("CRT-011", "@amanda.digital", "Amanda Teixeira Moraes", "29.543.812/0001-12", "amanda@agenciadigital.com", "Embaixador"),
        ("CRT-012", "@bruno.suplementos", "Bruno Carvalho Gomes", "117.885.643-87", "bruno.gomes@gmail.com", "Iniciante"),
        ("CRT-013", "@fernanda.reels", "Fernanda Duarte Pires", "228.996.754-41", "fernanda.pires@gmail.com", "Pro"),
        ("CRT-014", "@vinicius.saas", "Vinícius Monteiro Lopes", "339.107.865-29", "vinicius.lopes@saas.co", "Iniciante"),
        ("CRT-015", "@sofia.estetica", "Sofia Araújo Fernandes", "440.218.976-08", "sofia.fernandes@gmail.com", "Pro"),
    ]
    df_creators = pd.DataFrame(
        creators_lista,
        columns=[
            "ID_Afiliado",
            "Handle_Social",
            "Nome_Civil",
            "CPF_CNPJ",
            "Email_Pix",
            "Tier_Creator",
        ],
    )
    arq_creators = destino / "02_base_creators_mkt.csv"
    df_creators.to_csv(arq_creators, sep=";", index=False, encoding="utf-8-sig")

    # 3. Vendas (Controladoria) - 80 pedidos
    data_base = datetime(2026, 10, 1)
    aprovados = df_produtos[df_produtos["Status_Produto"] == "Aprovado"].to_dict("records")
    mapa_produtos = df_produtos.set_index("Cod_Prod").to_dict("index")
    ids_creators = df_creators["ID_Afiliado"].tolist()

    ANOMALIA_DEVOLUCAO_POS_PAGO = 5
    ANOMALIA_COMISSAO_ERRADA = 12
    ANOMALIA_PRODUTO_BLOQUEADO = 23
    ANOMALIA_SEM_REPASSE = 34
    ANOMALIA_CENTAVOS = 45

    linhas_vendas: list[dict[str, Any]] = []
    linhas_repasses: list[dict[str, Any]] = []
    linhas_estornos: list[dict[str, Any]] = []
    saldo_creator_conciliado: dict[str, float] = {}
    contador_lote = 100

    for i in range(1, 81):
        id_transacao = f"VND-2026-{i:04d}"
        dt_pedido = data_base + timedelta(days=(i * 45) // 80, hours=aleatorio.randint(8, 22))
        id_creator = aleatorio.choice(ids_creators)

        if i == ANOMALIA_PRODUTO_BLOQUEADO:
            cod_prod = "PRD-112"
            status_checkout = "Aprovada"
        elif i == ANOMALIA_COMISSAO_ERRADA:
            cod_prod = "PRD-101"
            status_checkout = "Aprovada"
        elif i in (ANOMALIA_DEVOLUCAO_POS_PAGO, ANOMALIA_SEM_REPASSE, ANOMALIA_CENTAVOS):
            cod_prod = aleatorio.choice(["PRD-104", "PRD-108", "PRD-111"])
            status_checkout = "Aprovada"
        else:
            cod_prod = aleatorio.choice(aprovados)["Cod_Prod"]
            if i % 16 == 0:
                status_checkout = "Pendente"
            elif i % 19 == 0:
                status_checkout = "Recusada"
            else:
                status_checkout = "Aprovada"

        info_prod = mapa_produtos[cod_prod]
        qtd = 1 if info_prod["Tipo_Produto"] == "Digital" else aleatorio.choice([1, 1, 2])
        valor_bruto = round(float(info_prod["Preco_Venda"]) * qtd, 2)
        taxa_youshop_pct = 0.10

        cpf_comp = f"{aleatorio.randint(100,999)}.{aleatorio.randint(100,999)}.{aleatorio.randint(100,999)}-{aleatorio.randint(10,99)}"
        email_comp = f"cliente.{i:03d}@comprador.com.br"

        linhas_vendas.append(
            {
                "ID_Transacao": id_transacao,
                "Dt_Pedido": _formatar_data_mista(dt_pedido, i),
                "Ref_Produto": cod_prod,
                "Codigo_Link_Creator": id_creator,
                "CPF_Comprador": cpf_comp,
                "Email_Cliente": email_comp,
                "Valor_Bruto_Venda": _formatar_moeda_brl(valor_bruto),
                "Taxa_TakeRate_YouShop": "10%" if i % 2 == 0 else 0.10,
                "Status_Checkout": status_checkout,
            }
        )

        pct_regra = float(info_prod["Comissao_Creator_Pct"])
        taxa_ys = round(valor_bruto * taxa_youshop_pct, 2)
        comissao_esperada = round(valor_bruto * pct_regra, 2)
        repasse_esperado = round(valor_bruto - taxa_ys - comissao_esperada, 2)
        dt_liq = dt_pedido + timedelta(days=2)

        if status_checkout == "Aprovada":
            if i == ANOMALIA_SEM_REPASSE:
                continue

            contador_lote += 1
            lote_id = f"LOT-{dt_liq.strftime('%Y%m')}-{contador_lote:03d}"

            if i == ANOMALIA_COMISSAO_ERRADA:
                comissao_paga = round(valor_bruto * 0.35, 2)
                repasse_pago = repasse_esperado
            elif i == ANOMALIA_CENTAVOS:
                comissao_paga = comissao_esperada
                repasse_pago = round(repasse_esperado - 0.13, 2)
            else:
                comissao_paga = comissao_esperada
                repasse_pago = repasse_esperado
                if i not in (ANOMALIA_DEVOLUCAO_POS_PAGO, ANOMALIA_PRODUTO_BLOQUEADO):
                    saldo_creator_conciliado[id_creator] = round(
                        saldo_creator_conciliado.get(id_creator, 0.0) + comissao_esperada, 2
                    )

            status_banco = "Liquidado" if (i <= 70 or i == ANOMALIA_DEVOLUCAO_POS_PAGO) else "Agendado"

            linhas_repasses.append(
                {
                    "Lote_Pgto": lote_id,
                    "Venda_Origem_ID": id_transacao,
                    "Destinatario_ID": id_creator,
                    "Categoria_Repasse": "Comissao_Creator",
                    "Vlr_Pago_BRL": _formatar_moeda_brl(comissao_paga),
                    "Data_Liquidacao": dt_liq.strftime("%d-%m-%Y"),
                    "Status_Banco": status_banco,
                }
            )
            linhas_repasses.append(
                {
                    "Lote_Pgto": lote_id,
                    "Venda_Origem_ID": id_transacao,
                    "Destinatario_ID": info_prod["Marca_Produtor"],
                    "Categoria_Repasse": "Repasse_Produtor",
                    "Vlr_Pago_BRL": _formatar_moeda_brl(repasse_pago),
                    "Data_Liquidacao": dt_liq.strftime("%d-%m-%Y"),
                    "Status_Banco": status_banco,
                }
            )

            if i == ANOMALIA_DEVOLUCAO_POS_PAGO:
                dt_cb = dt_liq + timedelta(days=3)
                linhas_estornos.append(
                    {
                        "Protocolo_Risco": "RSK-2026-9001",
                        "ID_Venda_Ref": id_transacao,
                        "Data_Ocorrencia": dt_cb.strftime("%d/%m/%Y"),
                        "Tipo_Incidente": "Chargeback",
                        "Valor_Estornado": _formatar_moeda_brl(valor_bruto),
                        "Motivo_Detalhado": (
                            "Contestação bancária (portador não reconhece compra) recebida 3 dias após o pagamento dos repasses."
                        ),
                    }
                )
        elif status_checkout == "Recusada" and len(linhas_estornos) < 3:
            linhas_estornos.append(
                {
                    "Protocolo_Risco": f"RSK-2026-900{len(linhas_estornos) + 1}",
                    "ID_Venda_Ref": id_transacao,
                    "Data_Ocorrencia": (dt_pedido + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "Tipo_Incidente": "Fraude_Confirmada",
                    "Valor_Estornado": _formatar_moeda_brl(valor_bruto),
                    "Motivo_Detalhado": "Tentativa de compra com cartão bloqueado barrada antes do pagamento.",
                }
            )

    # Solicitações de saque dos creators (9 dentro do saldo e 1 acima do saldo para auditoria)
    creators_com_saldo = sorted(
        [(cid, s) for cid, s in saldo_creator_conciliado.items() if s > 0],
        key=lambda x: x[0],
    )[:10]
    for idx_saq, (cid_saq, saldo_disp) in enumerate(creators_com_saldo, start=1):
        eh_anomalia_saque = idx_saq == len(creators_com_saldo)
        if eh_anomalia_saque:
            valor_saque = round(saldo_disp + 450.00, 2)
            status_saq = "Agendado"
            data_saq = "18-11-2026"
        else:
            valor_saque = round(saldo_disp * 0.65, 2)
            status_saq = "Liquidado" if idx_saq % 2 == 1 else "Agendado"
            data_saq = "15-11-2026" if idx_saq <= 5 else "25-10-2026"

        linhas_repasses.append(
            {
                "Lote_Pgto": f"LOT-SAQ-{idx_saq:03d}",
                "Venda_Origem_ID": f"SAQ-2026-{idx_saq:03d}",
                "Destinatario_ID": cid_saq,
                "Categoria_Repasse": "Solicitacao_Saque",
                "Vlr_Pago_BRL": _formatar_moeda_brl(valor_saque),
                "Data_Liquidacao": data_saq,
                "Status_Banco": status_saq,
            }
        )

    arq_vendas = destino / "03_vendas_checkout_controladoria.xlsx"
    pd.DataFrame(linhas_vendas).to_excel(arq_vendas, index=False)

    arq_repasses = destino / "04_repasses_financeiro.csv"
    pd.DataFrame(linhas_repasses).to_csv(arq_repasses, sep=";", index=False, encoding="utf-8-sig")

    arq_estornos = destino / "05_estornos_chargebacks_operacoes.xlsx"
    pd.DataFrame(linhas_estornos).to_excel(arq_estornos, index=False)

    return {
        "produtos": arq_produtos,
        "creators": arq_creators,
        "vendas": arq_vendas,
        "repasses": arq_repasses,
        "estornos": arq_estornos,
    }


if __name__ == "__main__":
    caminhos = gerar_planilhas_teste()
    print("Planilhas de teste YouShop geradas com sucesso:")
    for chave, caminho in caminhos.items():
        print(f"  - {chave}: {caminho}")
