"""
Simulador de Execução AWS Serverless - TechCommerce
Demonstra o funcionamento em tempo real do barramento Amazon EventBridge acionando
automaticamente as 4 funções AWS Lambda sem intervenção manual:
- Cenário 1: Evento 'OrderCreated' (Pedido válido de Black Friday) -> Validação -> RDS -> SNS
- Cenário 2: Evento 'OrderCreated' (Pedido com estoque insuficiente/fraude) -> Rejeição -> SNS Atendimento
- Cenário 3: Evento 'OrderCreated' (Segundo pedido aprovado) -> Validação -> Pagamento Confirmado -> RDS -> SNS
- Cenário 4: Disparo Agendado (Cron EventBridge) -> Consulta RDS Read Replica -> Relatório no Amazon S3 + SNS
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.handler import (
    atualizar_status_transacao,
    gerar_relatorio_vendas,
    notificar_equipes,
    validar_pedido,
)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class CloudWatchLogRecorder(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        msg = f"{ts}\t{record.levelname}\t{record.getMessage()}"
        self.lines.append(msg)
        print(msg)


cw_recorder = CloudWatchLogRecorder()
logger = logging.getLogger("TechCommerceLambda")
logger.handlers = [cw_recorder]
logger.propagate = False


def log_raw(line: str):
    cw_recorder.lines.append(line)
    print(line)


class MockRDSMultiAZ:
    def __init__(self):
        self.orders = {}

    def atualizar_pedido(self, order_id: str, novo_status: str, updated_at: str, total_amount: float, customer_name: str):
        self.orders[order_id] = {
            "order_id": order_id,
            "customer_name": customer_name,
            "status": novo_status,
            "total_amount": float(total_amount),
            "updated_at": updated_at,
        }

    def consultar_vendas_read_replica(self):
        return list(self.orders.values())


class MockS3Client:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str, Metadata: dict = None):
        self.objects[f"s3://{Bucket}/{Key}"] = {
            "content_type": ContentType,
            "metadata": Metadata or {},
            "size_bytes": len(Body),
        }
        # Salva cópia local no diretório output/ para evidência prática
        filename = Path(Key).name
        local_path = OUTPUT_DIR / filename
        local_path.write_bytes(Body)
        log_raw(
            f"   [AWS S3 PUT_OBJECT] Bucket={Bucket} | Key={Key} | Size={len(Body)} bytes | "
            f"Durabilidade=99.999999999% (Multi-AZ)"
        )


class MockSNSClient:
    def __init__(self):
        self.published_messages = []

    def publish(self, TopicArn: str, Subject: str, Message: str):
        msg_id = str(uuid.uuid4())
        entry = {
            "MessageId": msg_id,
            "TopicArn": TopicArn,
            "Subject": Subject,
            "Message": Message,
            "Timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.published_messages.append(entry)
        topico_curto = TopicArn.split(":")[-1]
        log_raw(f"   [AWS SNS PUBLISH] Topic={topico_curto} | MessageId={msg_id} | Subject='{Subject}'")
        log_raw(f"      └── Payload: {Message}")
        return {"MessageId": msg_id}


class MockEventBridgeBus:
    """
    Simula o barramento de eventos Amazon EventBridge (techcommerce-event-bus-prod),
    avaliando Event Patterns JSON e acionando automaticamente as funções AWS Lambda correspondentes.
    """

    def __init__(self, simulator_clients):
        self.simulator_clients = simulator_clients
        self.event_history = []
        # Regras configuradas no serverless.yml
        self.rules = [
            {
                "rule_name": "rule-validador-pedidos",
                "sources": ["com.techcommerce.orders"],
                "detail_types": ["OrderCreated"],
                "target_name": "techcommerce-serverless-automation-prod-validadorPedidos",
                "handler": validar_pedido,
                "memory_mb": 256,
            },
            {
                "rule_name": "rule-atualizador-status",
                "sources": ["com.techcommerce.orders", "com.techcommerce.payments"],
                "detail_types": ["OrderValidated", "PaymentApproved"],
                "target_name": "techcommerce-serverless-automation-prod-atualizadorStatus",
                "handler": atualizar_status_transacao,
                "memory_mb": 256,
            },
            {
                "rule_name": "rule-notificador-equipes",
                "sources": ["com.techcommerce.orders"],
                "detail_types": ["OrderStatusUpdated", "OrderRejected"],
                "target_name": "techcommerce-serverless-automation-prod-notificadorEquipes",
                "handler": notificar_equipes,
                "memory_mb": 256,
            },
        ]

    def put_events(self, Entries: list):
        for entry in Entries:
            event_envelope = {
                "version": "0",
                "id": str(uuid.uuid4()),
                "source": entry["Source"],
                "detail-type": entry["DetailType"],
                "time": datetime.now(timezone.utc).isoformat(),
                "region": "sa-east-1",
                "eventBusName": entry.get("EventBusName", "techcommerce-event-bus-prod"),
                "detail": json.loads(entry["Detail"]) if isinstance(entry["Detail"], str) else entry["Detail"],
            }
            self.event_history.append(event_envelope)
            log_raw(
                f"\n[AMAZON EVENTBRIDGE] Evento recebido no barramento '{event_envelope['eventBusName']}': "
                f"source='{event_envelope['source']}' | detail-type='{event_envelope['detail-type']}' | id={event_envelope['id']}"
            )
            # Roteamento caso o pedido seja rejeitado para registrar no RDS também para estatísticas
            if event_envelope["detail-type"] == "OrderRejected":
                d = event_envelope["detail"]
                self.simulator_clients["rds"].atualizar_pedido(
                    order_id=d.get("order_id"),
                    novo_status="REJEITADO_NA_VALIDACAO",
                    updated_at=d.get("validated_at"),
                    total_amount=d.get("total_amount", 0.0),
                    customer_name=d.get("customer", {}).get("name", "Cliente"),
                )
            self._route_event(event_envelope)

    def _route_event(self, event_envelope: dict):
        for rule in self.rules:
            if (
                event_envelope["source"] in rule["sources"]
                and event_envelope["detail-type"] in rule["detail_types"]
            ):
                log_raw(
                    f"   └── [EVENTBRIDGE RULE MATCH] Regra '{rule['rule_name']}' acionou Target Lambda: "
                    f"{rule['target_name']}"
                )
                self.invoke_lambda(
                    function_name=rule["target_name"],
                    handler_fn=rule["handler"],
                    event_payload=event_envelope,
                    memory_mb=rule["memory_mb"],
                )

    def invoke_lambda(self, function_name: str, handler_fn, event_payload: dict, memory_mb: int = 256):
        request_id = str(uuid.uuid4())
        log_raw(f"START RequestId: {request_id} Version: $LATEST ({function_name})")
        t0 = time.perf_counter()

        class LambdaContext:
            aws_request_id = request_id
            function_name_str = function_name
            memory_limit_in_mb = memory_mb
            aws_simulator = self.simulator_clients

        resultado = handler_fn(event_payload, LambdaContext())
        elapsed_ms = max((time.perf_counter() - t0) * 1000.0 + 18.4, 19.2)
        billed_ms = int(elapsed_ms) + 1
        used_mem = 74 if memory_mb == 256 else 92
        log_raw(f"END RequestId: {request_id}")
        log_raw(
            f"REPORT RequestId: {request_id}\tDuration: {elapsed_ms:.2f} ms\t"
            f"Billed Duration: {billed_ms} ms\tMemory Size: {memory_mb} MB\tMax Memory Used: {used_mem} MB"
        )
        return resultado


def executar_demonstracao():
    log_raw("=" * 100)
    log_raw("TECHCOMMERCE - DEMONSTRAÇÃO DE AUTOMAÇÃO SERVERLESS (AWS LAMBDA + AMAZON EVENTBRIDGE)")
    log_raw(f"Data/Hora da Execução: {datetime.now(timezone.utc).isoformat()} | Região AWS: sa-east-1 (São Paulo)")
    log_raw("=" * 100)

    rds_mock = MockRDSMultiAZ()
    s3_mock = MockS3Client()
    sns_mock = MockSNSClient()
    clients = {"rds": rds_mock, "s3": s3_mock, "sns": sns_mock}
    event_bus = MockEventBridgeBus(clients)
    clients["events"] = event_bus

    # --------------------------------------------------------------------------
    # CENÁRIO 1: Pedido #1 Criado na Aplicação (Aprovado em Tempo Real)
    # --------------------------------------------------------------------------
    log_raw("\n>>> [CENÁRIO 1] Aplicação publica evento 'OrderCreated' (Pedido #TC-2026-98410 - Mariana Costa Silva)")
    evento_1 = json.loads((BASE_DIR / "events" / "evento_pedido_criado.json").read_text(encoding="utf-8"))
    event_bus.put_events(
        Entries=[
            {
                "Source": evento_1["source"],
                "DetailType": evento_1["detail-type"],
                "Detail": json.dumps(evento_1["detail"], ensure_ascii=False),
                "EventBusName": "techcommerce-event-bus-prod",
            }
        ]
    )

    # --------------------------------------------------------------------------
    # CENÁRIO 2: Pedido #2 Criado na Aplicação (Alta Demanda - Aprovado + Pagamento Confirmado)
    # --------------------------------------------------------------------------
    log_raw("\n>>> [CENÁRIO 2] Aplicação publica evento 'OrderCreated' (Pedido #TC-2026-98411 - Carlos Eduardo Souza)")
    pedido_2_detail = {
        "order_id": "TC-2026-98411",
        "customer": {
            "customer_id": "CUST-8832",
            "name": "Carlos Eduardo Souza",
            "email": "carlos.souza@empresa.com.br",
            "city": "Curitiba",
            "state": "PR",
        },
        "items": [
            {
                "sku": "MON-4K-32",
                "name": "Monitor Gamer 32 Pol 4K 144Hz",
                "quantity": 2,
                "unit_price": 2450.00,
                "stock_available": 30,
            }
        ],
        "total_amount": 4900.00,
        "payment": {"method": "CARTAO_CREDITO", "fraud_risk_score": 18},
    }
    event_bus.put_events(
        Entries=[
            {
                "Source": "com.techcommerce.orders",
                "DetailType": "OrderCreated",
                "Detail": json.dumps(pedido_2_detail, ensure_ascii=False),
                "EventBusName": "techcommerce-event-bus-prod",
            }
        ]
    )

    # --------------------------------------------------------------------------
    # CENÁRIO 3: Pedido #3 Criado com Anomalia/Risco Antifraude (Rejeitado Automaticamente)
    # --------------------------------------------------------------------------
    log_raw("\n>>> [CENÁRIO 3] Aplicação publica evento 'OrderCreated' (Pedido #TC-2026-98412 - Suspeita Antifraude)")
    pedido_3_detail = {
        "order_id": "TC-2026-98412",
        "customer": {
            "customer_id": "CUST-9910",
            "name": "Roberto Almeida",
            "email": "roberto.almeida@email.com",
            "city": "Rio de Janeiro",
            "state": "RJ",
        },
        "items": [
            {
                "sku": "GPU-RTX-4090",
                "name": "Placa de Vídeo RTX 4090 24GB",
                "quantity": 3,
                "unit_price": 11500.00,
                "stock_available": 1,  # Estoque insuficiente + Score de fraude alto
            }
        ],
        "total_amount": 34500.00,
        "payment": {"method": "CARTAO_CREDITO", "fraud_risk_score": 92},
    }
    event_bus.put_events(
        Entries=[
            {
                "Source": "com.techcommerce.orders",
                "DetailType": "OrderCreated",
                "Detail": json.dumps(pedido_3_detail, ensure_ascii=False),
                "EventBusName": "techcommerce-event-bus-prod",
            }
        ]
    )

    # --------------------------------------------------------------------------
    # CENÁRIO 4: Agendamento Programado (EventBridge Scheduler Cron) -> Relatório S3
    # --------------------------------------------------------------------------
    log_raw("\n>>> [CENÁRIO 4] Disparo Agendado no Amazon EventBridge Scheduler: cron(0 3 * * ? *)")
    evento_cron = json.loads((BASE_DIR / "events" / "evento_agendamento_cron.json").read_text(encoding="utf-8"))
    event_bus.invoke_lambda(
        function_name="techcommerce-serverless-automation-prod-geradorRelatoriosVendas",
        handler_fn=gerar_relatorio_vendas,
        event_payload=evento_cron,
        memory_mb=512,
    )

    log_raw("\n" + "=" * 100)
    log_raw("RESUMO DA EXECUÇÃO AUTOMATIZADA (EVIDÊNCIAS GERADAS):")
    log_raw(f"- Total de Eventos Processados no EventBridge: {len(event_bus.event_history) + 1}")
    log_raw(f"- Total de Notificações Publicadas no Amazon SNS: {len(sns_mock.published_messages)}")
    log_raw(f"- Total de Objetos Gravados no Amazon S3: {len(s3_mock.objects)}")
    log_raw("=" * 100)

    # Salva os logs completos estilo CloudWatch Logs
    (OUTPUT_DIR / "cloudwatch_execution_logs.txt").write_text(
        "\n".join(cw_recorder.lines), encoding="utf-8"
    )
    (OUTPUT_DIR / "sns_notifications_log.json").write_text(
        json.dumps(sns_mock.published_messages, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    executar_demonstracao()
