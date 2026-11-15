"""
TechCommerce - Funções AWS Lambda para Automação de Processos Orientada a Eventos
Disciplina: Cloud Computing for Software Development

Este módulo implementa as 4 funções Serverless (AWS Lambda) acionadas pelo Amazon EventBridge:
1. validar_pedido            -> Acionada pelo evento 'OrderCreated' (source: com.techcommerce.orders)
2. atualizar_status_transacao -> Acionada pelos eventos 'OrderValidated' e 'PaymentApproved'
3. notificar_equipes          -> Acionada pelos eventos 'OrderStatusUpdated' e 'OrderRejected'
4. gerar_relatorio_vendas     -> Acionada por agendamento Cron/Rate no Amazon EventBridge
"""

import csv
import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

# Configuração de logs estruturados compatíveis com o Amazon CloudWatch Logs (Unidade 2)
logger = logging.getLogger("TechCommerceLambda")
logger.setLevel(logging.INFO)

# Variáveis de ambiente seguras (Unidade 2 - Aula 2)
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "techcommerce-event-bus-prod")
REPORTS_BUCKET_NAME = os.environ.get("REPORTS_BUCKET_NAME", "techcommerce-relatorios-vendas-prod")
SNS_TOPIC_LOGISTICA_ARN = os.environ.get(
    "SNS_TOPIC_LOGISTICA_ARN", "arn:aws:sns:sa-east-1:123456789012:techcommerce-notificacoes-logistica-prod"
)
SNS_TOPIC_ATENDIMENTO_ARN = os.environ.get(
    "SNS_TOPIC_ATENDIMENTO_ARN", "arn:aws:sns:sa-east-1:123456789012:techcommerce-notificacoes-atendimento-prod"
)
RDS_READ_REPLICA_ENDPOINT = os.environ.get(
    "RDS_READ_REPLICA_ENDPOINT", "techcommerce-db-read-replica.c9akciq32.sa-east-1.rds.amazonaws.com"
)


def _obter_clientes_aws(context: Any = None):
    """
    Retorna os clientes AWS (boto3) em ambiente de produção ou os adaptadores
    do simulador local durante a execução de demonstração.
    """
    if hasattr(context, "aws_simulator") and context.aws_simulator is not None:
        return context.aws_simulator
    import boto3  # Importado sob demanda em produção na AWS
    return {
        "events": boto3.client("events", region_name="sa-east-1"),
        "s3": boto3.client("s3", region_name="sa-east-1"),
        "sns": boto3.client("sns", region_name="sa-east-1"),
    }


# ==============================================================================
# 1. FUNÇÃO LAMBDA: VALIDAÇÃO AUTOMÁTICA DE PEDIDOS
# Gatilho EventBridge: source="com.techcommerce.orders", detail-type="OrderCreated"
# ==============================================================================
def validar_pedido(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Recebe o evento 'OrderCreated' do Amazon EventBridge, valida integridade dos itens,
    disponibilidade em estoque e score antifraude, e publica 'OrderValidated' ou 'OrderRejected'.
    """
    detail = event.get("detail", {})
    pedido_id = detail.get("order_id", "ORD-UNKNOWN")
    cliente = detail.get("customer", {})
    itens = detail.get("items", [])
    valor_total = float(detail.get("total_amount", 0.0))
    pagamento = detail.get("payment", {})

    logger.info(
        f"[VALIDADOR_PEDIDOS] Iniciando validação automática do pedido {pedido_id} | "
        f"Cliente: {cliente.get('name')} | Valor Total: R$ {valor_total:.2f}"
    )

    erros_validacao = []

    # Regra 1: Verificar se o pedido possui itens válidos e estoque disponível
    if not itens:
        erros_validacao.append("Pedido não contém itens.")
    for item in itens:
        if item.get("quantity", 0) <= 0:
            erros_validacao.append(f"Quantidade inválida para o SKU {item.get('sku')}.")
        if item.get("stock_available", 0) < item.get("quantity", 0):
            erros_validacao.append(
                f"Estoque insuficiente para o produto '{item.get('name')}' (SKU {item.get('sku')})."
            )

    # Regra 2: Verificação de valor e score de risco antifraude
    risco_score = pagamento.get("fraud_risk_score", 0)
    if valor_total <= 0:
        erros_validacao.append("Valor total do pedido inválido.")
    if risco_score > 80:
        erros_validacao.append(f"Score de risco antifraude elevado ({risco_score}/100). Requer revisão.")

    aws = _obter_clientes_aws(context)
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    if erros_validacao:
        novo_detail_type = "OrderRejected"
        status_validacao = "REJEITADO_NA_VALIDACAO"
        logger.warning(
            f"[VALIDADOR_PEDIDOS] Pedido {pedido_id} REJEITADO. Motivos: {'; '.join(erros_validacao)}"
        )
    else:
        novo_detail_type = "OrderValidated"
        status_validacao = "VALIDADO_COM_SUCESSO"
        logger.info(
            f"[VALIDADOR_PEDIDOS] Pedido {pedido_id} VALIDADO com sucesso ({len(itens)} itens verificados)."
        )

    payload_evento = {
        "order_id": pedido_id,
        "customer": cliente,
        "items": itens,
        "total_amount": valor_total,
        "payment": pagamento,
        "validation_status": status_validacao,
        "validation_errors": erros_validacao,
        "validated_at": timestamp_iso,
    }

    # Publica o resultado da validação no barramento do Amazon EventBridge
    aws["events"].put_events(
        Entries=[
            {
                "Source": "com.techcommerce.orders",
                "DetailType": novo_detail_type,
                "Detail": json.dumps(payload_evento, ensure_ascii=False),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    return {
        "statusCode": 200,
        "order_id": pedido_id,
        "emitted_event": novo_detail_type,
        "validation_status": status_validacao,
    }


# ==============================================================================
# 2. FUNÇÃO LAMBDA: ATUALIZAÇÃO DE STATUS DAS TRANSAÇÕES (AMAZON RDS)
# Gatilho EventBridge: detail-type in ["OrderValidated", "PaymentApproved"]
# ==============================================================================
def atualizar_status_transacao(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Recebe eventos de validação ou confirmação de pagamento e atualiza o registro
    transacional no banco de dados relacional gerenciado (Amazon RDS Multi-AZ).
    Em seguida, publica 'OrderStatusUpdated' no EventBridge.
    """
    detail_type = event.get("detail-type", "")
    detail = event.get("detail", {})
    pedido_id = detail.get("order_id", "ORD-UNKNOWN")

    mapeamento_status = {
        "OrderValidated": "AGUARDANDO_SEPARACAO_LOGISTICA",
        "PaymentApproved": "PAGAMENTO_CONFIRMADO_EM_SEPARACAO",
    }
    novo_status = mapeamento_status.get(detail_type, "EM_PROCESSAMENTO")
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"[ATUALIZADOR_STATUS] Evento recebido: '{detail_type}' para o pedido {pedido_id}. "
        f"Atualizando status no Amazon RDS (Multi-AZ) para '{novo_status}'."
    )

    aws = _obter_clientes_aws(context)

    # Atualiza o status no banco transacional (Amazon RDS PostgreSQL Multi-AZ)
    if "rds" in aws:
        aws["rds"].atualizar_pedido(
            order_id=pedido_id,
            novo_status=novo_status,
            updated_at=timestamp_iso,
            total_amount=detail.get("total_amount", 0.0),
            customer_name=detail.get("customer", {}).get("name", "Cliente"),
        )

    payload_atualizacao = {
        "order_id": pedido_id,
        "previous_event": detail_type,
        "new_status": novo_status,
        "customer": detail.get("customer", {}),
        "items": detail.get("items", []),
        "total_amount": detail.get("total_amount", 0.0),
        "updated_at": timestamp_iso,
        "rds_multi_az_sync": True,
    }

    # Emite evento OrderStatusUpdated no Amazon EventBridge para desacoplar as notificações
    aws["events"].put_events(
        Entries=[
            {
                "Source": "com.techcommerce.orders",
                "DetailType": "OrderStatusUpdated",
                "Detail": json.dumps(payload_atualizacao, ensure_ascii=False),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    logger.info(
        f"[ATUALIZADOR_STATUS] Transação {pedido_id} persistida no Amazon RDS e evento "
        f"'OrderStatusUpdated' publicado no EventBridge."
    )

    return {
        "statusCode": 200,
        "order_id": pedido_id,
        "new_status": novo_status,
        "emitted_event": "OrderStatusUpdated",
    }


# ==============================================================================
# 3. FUNÇÃO LAMBDA: NOTIFICAÇÃO AUTOMÁTICA DE LOGÍSTICA E ATENDIMENTO (AMAZON SNS)
# Gatilho EventBridge: detail-type in ["OrderStatusUpdated", "OrderRejected"]
# ==============================================================================
def notificar_equipes(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Consome eventos 'OrderStatusUpdated' ou 'OrderRejected' do EventBridge e dispara
    notificações pub/sub via Amazon SNS para as equipes de Logística e Atendimento.
    """
    detail_type = event.get("detail-type", "")
    detail = event.get("detail", {})
    pedido_id = detail.get("order_id", "ORD-UNKNOWN")
    cliente = detail.get("customer", {})
    valor_total = float(detail.get("total_amount", 0.0))

    aws = _obter_clientes_aws(context)
    notificacoes_enviadas = []

    if detail_type == "OrderStatusUpdated":
        novo_status = detail.get("new_status", "ATUALIZADO")
        qtd_itens = sum(item.get("quantity", 1) for item in detail.get("items", []))

        # 1) Notificação para a equipe de Logística (separação e expedição)
        msg_logistica = (
            f"[LOGÍSTICA TECHCOMMERCE] Pedido {pedido_id} liberado para expedição | "
            f"Status: {novo_status} | Itens: {qtd_itens} | Destino: {cliente.get('city', 'SP')}/{cliente.get('state', 'SP')}"
        )
        aws["sns"].publish(
            TopicArn=SNS_TOPIC_LOGISTICA_ARN,
            Subject=f"[Expedição] Pedido {pedido_id} - {novo_status}",
            Message=msg_logistica,
        )
        notificacoes_enviadas.append("SNS_LOGISTICA")

        # 2) Notificação para a equipe de Atendimento / CRM
        msg_atendimento = (
            f"[ATENDIMENTO TECHCOMMERCE] Status do pedido {pedido_id} do cliente "
            f"{cliente.get('name')} ({cliente.get('email')}) atualizado para: {novo_status}."
        )
        aws["sns"].publish(
            TopicArn=SNS_TOPIC_ATENDIMENTO_ARN,
            Subject=f"[Atualização de Pedido] {pedido_id}",
            Message=msg_atendimento,
        )
        notificacoes_enviadas.append("SNS_ATENDIMENTO")

        logger.info(
            f"[NOTIFICADOR_EQUIPES] Alertas SNS enviados para Logística e Atendimento referente ao pedido {pedido_id}."
        )

    elif detail_type == "OrderRejected":
        motivos = ", ".join(detail.get("validation_errors", ["Inconsistência cadastral"]))
        msg_atendimento = (
            f"[ALERTA ATENDIMENTO] Pedido {pedido_id} (R$ {valor_total:.2f}) requer tratativa! "
            f"Cliente: {cliente.get('name')} ({cliente.get('email')}) | Motivo: {motivos}"
        )
        aws["sns"].publish(
            TopicArn=SNS_TOPIC_ATENDIMENTO_ARN,
            Subject=f"[Ação Necessária] Pedido Rejeitado {pedido_id}",
            Message=msg_atendimento,
        )
        notificacoes_enviadas.append("SNS_ATENDIMENTO_REJEICAO")
        logger.info(
            f"[NOTIFICADOR_EQUIPES] Alerta de pedido rejeitado ({pedido_id}) enviado ao Atendimento via Amazon SNS."
        )

    return {
        "statusCode": 200,
        "order_id": pedido_id,
        "sns_topics_notified": notificacoes_enviadas,
    }


# ==============================================================================
# 4. FUNÇÃO LAMBDA: GERAÇÃO AGENDADA DE RELATÓRIOS DE VENDAS (CRON -> RDS -> S3)
# Gatilho EventBridge Scheduler: cron(0 3 * * ? *) e rate(1 hour)
# ==============================================================================
def gerar_relatorio_vendas(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Executada automaticamente via agendamento (Cron/Rate) no Amazon EventBridge.
    Consulta as transações na Read Replica do Amazon RDS (Unidade 3) para não impactar
    o banco principal, consolida os indicadores de vendas e armazena o relatório
    no Amazon S3 (Unidade 2) com durabilidade de 99,999999999% (11 noves).
    """
    tipo_relatorio = event.get("tipo_relatorio", "FECHAMENTO_DIARIO")
    origem_disparo = event.get("origem_disparo", "EventBridge-Scheduler-Cron")
    agora = datetime.now(timezone.utc)
    data_ref = agora.strftime("%Y-%m-%d")

    logger.info(
        f"[GERADOR_RELATORIOS] Disparo automático via '{origem_disparo}' ({tipo_relatorio}). "
        f"Consultando Read Replica do Amazon RDS: {RDS_READ_REPLICA_ENDPOINT}"
    )

    aws = _obter_clientes_aws(context)
    pedidos_processados = aws["rds"].consultar_vendas_read_replica() if "rds" in aws else []

    pedidos_aprovados = [
        p for p in pedidos_processados if p["status"] != "REJEITADO_NA_VALIDACAO"
    ]
    pedidos_rejeitados = [
        p for p in pedidos_processados if p["status"] == "REJEITADO_NA_VALIDACAO"
    ]
    receita_total = sum(p["total_amount"] for p in pedidos_aprovados)
    ticket_medio = receita_total / len(pedidos_aprovados) if pedidos_aprovados else 0.0

    relatorio_json = {
        "empresa": "TechCommerce E-Commerce S.A.",
        "tipo_relatorio": tipo_relatorio,
        "data_referencia": data_ref,
        "gerado_em_utc": agora.isoformat(),
        "origem_automacao": origem_disparo,
        "fonte_dados_rds": RDS_READ_REPLICA_ENDPOINT,
        "metricas_consolidadas": {
            "total_pedidos_recebidos": len(pedidos_processados),
            "pedidos_validados_e_processados": len(pedidos_aprovados),
            "pedidos_rejeitados": len(pedidos_rejeitados),
            "receita_bruta_aprovada_brl": round(receita_total, 2),
            "ticket_medio_brl": round(ticket_medio, 2),
            "taxa_aprovacao_percentual": round(
                (len(pedidos_aprovados) / len(pedidos_processados) * 100)
                if pedidos_processados
                else 100.0,
                2,
            ),
        },
        "transacoes_detalhadas": pedidos_processados,
    }

    # Geração de arquivo CSV em memória para equipe financeira/executiva
    buffer_csv = io.StringIO()
    writer = csv.writer(buffer_csv)
    writer.writerow(["order_id", "customer_name", "status", "total_amount_brl", "updated_at"])
    for p in pedidos_processados:
        writer.writerow([
            p["order_id"],
            p["customer_name"],
            p["status"],
            f"{p['total_amount']:.2f}",
            p["updated_at"],
        ])

    chave_s3_json = f"relatorios/{agora.strftime('%Y/%m')}/relatorio_vendas_{data_ref}.json"
    chave_s3_csv = f"relatorios/{agora.strftime('%Y/%m')}/relatorio_vendas_{data_ref}.csv"

    # Gravação dos objetos no Amazon S3 com Metadados Ricos (Unidade 2 - Aula 1)
    aws["s3"].put_object(
        Bucket=REPORTS_BUCKET_NAME,
        Key=chave_s3_json,
        Body=json.dumps(relatorio_json, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
        Metadata={
            "report-type": tipo_relatorio,
            "generated-by": "aws-lambda-gerador-relatorios",
            "lifecycle-policy": "standard-to-glacier",
        },
    )

    aws["s3"].put_object(
        Bucket=REPORTS_BUCKET_NAME,
        Key=chave_s3_csv,
        Body=buffer_csv.getvalue().encode("utf-8"),
        ContentType="text/csv",
        Metadata={
            "report-type": tipo_relatorio,
            "generated-by": "aws-lambda-gerador-relatorios",
        },
    )

    logger.info(
        f"[GERADOR_RELATORIOS] Relatórios salvos com sucesso no Amazon S3: "
        f"s3://{REPORTS_BUCKET_NAME}/{chave_s3_json} | Receita Consolidada: R$ {receita_total:.2f}"
    )

    # Notifica fechamento do relatório via Amazon SNS
    aws["sns"].publish(
        TopicArn=SNS_TOPIC_LOGISTICA_ARN,
        Subject=f"[Relatório Diário S3] Fechamento de Vendas {data_ref}",
        Message=(
            f"[RELATÓRIO AUTOMÁTICO TECHCOMMERCE] Fechamento {tipo_relatorio} concluído sem intervenção manual. "
            f"Pedidos Aprovados: {len(pedidos_aprovados)} | Receita Total: R$ {receita_total:.2f} | "
            f"Disponível em: s3://{REPORTS_BUCKET_NAME}/{chave_s3_json}"
        ),
    )

    return {
        "statusCode": 200,
        "s3_bucket": REPORTS_BUCKET_NAME,
        "s3_keys": [chave_s3_json, chave_s3_csv],
        "summary": relatorio_json["metricas_consolidadas"],
    }
