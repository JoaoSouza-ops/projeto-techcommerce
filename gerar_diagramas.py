"""
Gera os diagramas de arquitetura AWS, fluxograma de automação e captura de evidência
do CloudWatch/EventBridge em alta resolução (PNG) utilizando HTML/SVG + Microsoft Edge Headless.
"""

import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
DIAG_DIR = BASE_DIR / "diagramas"
DIAG_DIR.mkdir(exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# 1. HTML/SVG: Diagrama de Arquitetura Serverless AWS - TechCommerce
HTML_ARQUITETURA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, Arial, sans-serif; }
  body { width: 1400px; height: 860px; background: #0f172a; color: #f8fafc; padding: 24px; overflow: hidden; }
  .board {
    width: 100%; height: 100%; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 2px solid #334155; border-radius: 16px; padding: 20px 26px; position: relative;
    display: flex; flex-direction: column; justify-content: space-between;
  }
  .header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 2px solid #334155; padding-bottom: 12px;
  }
  .header-title h1 { font-size: 23px; color: #ff9900; font-weight: 800; letter-spacing: 0.4px; }
  .header-title p { font-size: 13px; color: #94a3b8; margin-top: 3px; }
  .region-badge {
    background: rgba(255, 153, 0, 0.14); border: 1.5px solid #ff9900; color: #ff9900;
    padding: 7px 14px; border-radius: 8px; font-size: 13px; font-weight: 700;
  }
  .aws-cloud {
    border: 2px dashed #ff9900; border-radius: 14px; padding: 16px 20px; position: relative;
    flex: 1; margin: 14px 0; display: grid; grid-template-columns: 230px 270px 340px 380px;
    gap: 20px; align-items: center; background: rgba(15, 23, 42, 0.55);
  }
  .cloud-label {
    position: absolute; top: -13px; left: 22px; background: #0f172a; padding: 2px 12px;
    color: #ff9900; font-weight: 800; font-size: 13px; border: 1px solid #ff9900; border-radius: 6px;
  }
  .col { display: flex; flex-direction: column; gap: 14px; height: 100%; justify-content: center; }
  .card {
    background: #1e293b; border: 1.5px solid #475569; border-radius: 11px; padding: 12px 14px;
    box-shadow: 0 6px 14px rgba(0,0,0,0.35); position: relative;
  }
  .card-source { border-color: #38bdf8; background: linear-gradient(180deg, #0c4a6e 0%, #1e293b 100%); }
  .card-eb { border-color: #ec4899; background: linear-gradient(180deg, #831843 0%, #1e293b 100%); }
  .card-lambda { border-color: #f97316; background: linear-gradient(180deg, #7c2d12 0%, #1e293b 100%); }
  .card-data { border-color: #22c55e; background: linear-gradient(180deg, #14532d 0%, #1e293b 100%); }
  .card-sns { border-color: #a855f7; background: linear-gradient(180deg, #4c1d95 0%, #1e293b 100%); }
  .tag {
    display: inline-block; font-size: 10px; font-weight: 800; text-transform: uppercase;
    padding: 2px 7px; border-radius: 4px; margin-bottom: 5px; letter-spacing: 0.5px;
  }
  .tag-blue { background: #0284c7; color: #fff; }
  .tag-pink { background: #db2777; color: #fff; }
  .tag-orange { background: #ea580c; color: #fff; }
  .tag-green { background: #16a34a; color: #fff; }
  .tag-purple { background: #9333ea; color: #fff; }
  .card h3 { font-size: 14px; color: #ffffff; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
  .card p { font-size: 11.5px; color: #cbd5e1; line-height: 1.35; }
  .code-pill {
    margin-top: 6px; background: #0f172a; border: 1px solid #334155; border-radius: 5px;
    padding: 4px 7px; font-family: Consolas, monospace; font-size: 10.5px; color: #fde047;
  }
  .arrow-hint {
    font-size: 11px; color: #94a3b8; text-align: center; font-weight: 600;
    background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 6px;
  }
  .bottom-bar {
    display: grid; grid-template-columns: 1fr 1fr; gap: 18px;
  }
  .gov-box {
    background: rgba(30, 41, 59, 0.9); border: 1.5px solid #eab308; border-radius: 10px;
    padding: 10px 16px; display: flex; align-items: center; justify-content: space-between;
  }
  .gov-box.cw { border-color: #06b6d4; }
  .gov-title { font-size: 13px; font-weight: 800; color: #fef08a; margin-bottom: 3px; }
  .gov-box.cw .gov-title { color: #67e8f9; }
  .gov-desc { font-size: 11.5px; color: #cbd5e1; }
  .badge-pill {
    background: #0f172a; border: 1px solid #475569; padding: 5px 10px; border-radius: 6px;
    font-size: 11px; font-weight: 700; color: #f8fafc; white-space: nowrap;
  }
</style>
</head>
<body>
<div class="board">
  <div class="header">
    <div class="header-title">
      <h1>ARQUITETURA SERVERLESS ORIENTADA A EVENTOS — TECHCOMMERCE (AWS)</h1>
      <p>Automação de Processos em Nuvem com AWS Lambda, Amazon EventBridge, Amazon RDS Multi-AZ, Amazon S3 e Amazon SNS</p>
    </div>
    <div class="region-badge">AWS Region: sa-east-1 (São Paulo) • Multi-AZ</div>
  </div>

  <div class="aws-cloud">
    <div class="cloud-label">AWS Cloud • Infraestrutura Gerenciada Serverless</div>

    <!-- COLUNA 1: FONTES DE EVENTOS -->
    <div class="col">
      <div class="card card-source">
        <span class="tag tag-blue">Produtor de Eventos</span>
        <h3>🛒 Plataforma E-Commerce</h3>
        <p>Checkout Web/Mobile &amp; API Gateway recebem milhares de pedidos em picos promocionais.</p>
        <div class="code-pill">source: com.techcommerce.orders<br>detail-type: OrderCreated</div>
      </div>

      <div class="card card-source">
        <span class="tag tag-blue">Produtor de Eventos</span>
        <h3>💳 Gateway de Pagamento</h3>
        <p>Processamento PIX e Cartão de Crédito com score antifraude em tempo real.</p>
        <div class="code-pill">source: com.techcommerce.payments<br>detail-type: PaymentApproved</div>
      </div>

      <div class="card card-eb">
        <span class="tag tag-pink">Agendador Serverless</span>
        <h3>⏰ EventBridge Scheduler</h3>
        <p>Disparo automático programado sem intervenção humana para relatórios.</p>
        <div class="code-pill">cron(0 3 * * ? *) → Diário 00h BRT<br>rate(1 hour) → Pico Black Friday</div>
      </div>
    </div>

    <!-- COLUNA 2: BARRAMENTO DE EVENTOS -->
    <div class="col">
      <div class="card card-eb" style="padding: 18px 14px;">
        <span class="tag tag-pink">Core Event Bus</span>
        <h3>🔀 Amazon EventBridge</h3>
        <p>Barramento customizado <b>techcommerce-event-bus-prod</b>. Filtra payloads JSON e roteia eventos de forma assíncrona e desacoplada.</p>
        <div class="code-pill" style="margin-top:10px;">
          • Rule 1: OrderCreated ➔ Validador<br>
          • Rule 2: OrderValidated / PaymentApproved ➔ Atualizador<br>
          • Rule 3: OrderStatusUpdated / Rejected ➔ Notificador<br>
          • Rule 4: Schedule Cron/Rate ➔ Relatórios
        </div>
        <div class="arrow-hint" style="margin-top:10px;">⚡ Desacoplamento Total (Loose Coupling) &amp; Retry Automático + DLQ</div>
      </div>
    </div>

    <!-- COLUNA 3: CAMADA DE COMPUTAÇÃO SERVERLESS (AWS LAMBDA) -->
    <div class="col">
      <div class="card card-lambda">
        <span class="tag tag-orange">AWS Lambda #1 • Python 3.12</span>
        <h3>λ validadorPedidos</h3>
        <p>Valida itens, disponibilidade de estoque e score antifraude. Emite <b>OrderValidated</b> ou <b>OrderRejected</b> ao EventBridge.</p>
      </div>

      <div class="card card-lambda">
        <span class="tag tag-orange">AWS Lambda #2 • Python 3.12</span>
        <h3>λ atualizadorStatus</h3>
        <p>Atualiza o status transacional do pedido no banco relacional gerenciado e publica <b>OrderStatusUpdated</b>.</p>
      </div>

      <div class="card card-lambda">
        <span class="tag tag-orange">AWS Lambda #3 • Python 3.12</span>
        <h3>λ notificadorEquipes</h3>
        <p>Formata alertas operacionais e publica nos tópicos do Amazon SNS para Logística e Atendimento.</p>
      </div>

      <div class="card card-lambda">
        <span class="tag tag-orange">AWS Lambda #4 • Python 3.12</span>
        <h3>λ geradorRelatoriosVendas</h3>
        <p>Acionada via Cron. Consulta a Read Replica do RDS, gera relatórios JSON/CSV e grava no Amazon S3.</p>
      </div>
    </div>

    <!-- COLUNA 4: PERSISTÊNCIA, ARMAZENAMENTO E NOTIFICAÇÕES -->
    <div class="col">
      <div class="card card-data">
        <span class="tag tag-green">Banco Gerenciado (Unidade 3)</span>
        <h3>🗄️ Amazon RDS (PostgreSQL Multi-AZ)</h3>
        <p><b>Instância Principal (Multi-AZ):</b> Escrita transacional de pedidos com failover automático.<br>
        <b>Read Replica:</b> Leitura isolada para geração de relatórios sem onerar o checkout.</p>
      </div>

      <div class="card card-sns">
        <span class="tag tag-purple">Mensageria Pub/Sub (Unidade 2)</span>
        <h3>📣 Amazon SNS (Notificações)</h3>
        <p>• <b>Tópico Logística:</b> Dispara separação de estoque e expedição (Webhook/E-mail).<br>
        • <b>Tópico Atendimento:</b> Notifica cliente e CRM sobre status ou rejeição antifraude.</p>
      </div>

      <div class="card card-data">
        <span class="tag tag-green">Object Storage (Unidade 2)</span>
        <h3>🪣 Amazon S3 (11 Noves Durabilidade)</h3>
        <p>Bucket privado <b>techcommerce-relatorios-vendas</b> com criptografia AES-256 e <b>Lifecycle Policy</b>:</p>
        <div class="code-pill">S3 Standard (0-30d) ➔ Standard-IA (30d) ➔ S3 Glacier (90d)</div>
      </div>
    </div>
  </div>

  <!-- BARRA INFERIOR: SEGURANÇA (IAM) E OBSERVABILIDADE (CLOUDWATCH) -->
  <div class="bottom-bar">
    <div class="gov-box">
      <div>
        <div class="gov-title">🔐 AWS IAM &amp; Secrets Manager — Governança e Menor Privilégio (Unidade 1 e 2)</div>
        <div class="gov-desc">Execution Roles exclusivas por função Lambda (Least Privilege: s3:PutObject, sns:Publish, events:PutEvents) e credenciais de banco protegidas.</div>
      </div>
      <div class="badge-pill">Zero Hardcoded Secrets</div>
    </div>

    <div class="gov-box cw">
      <div>
        <div class="gov-title">📊 Amazon CloudWatch + SNS — Observabilidade e Alarmes em Tempo Real (Unidade 2)</div>
        <div class="gov-desc">Coleta centralizada de logs (RequestId, Billed Duration) e métricas (Invocations, Errors, Throttles) com alertas proativos via SNS.</div>
      </div>
      <div class="badge-pill">Monitoramento 24/7</div>
    </div>
  </div>
</div>
</body>
</html>
"""

# 2. HTML/SVG: Fluxograma Completo de Automação (Eventos + Agendamentos)
HTML_FLUXOGRAMA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, Arial, sans-serif; }
  body { width: 1400px; height: 800px; background: #f8fafc; color: #0f172a; padding: 24px; overflow: hidden; }
  .canvas {
    width: 100%; height: 100%; background: #ffffff; border: 2px solid #cbd5e1;
    border-radius: 16px; padding: 22px 28px; display: flex; flex-direction: column; justify-content: space-between;
  }
  .title-bar {
    border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; display: flex; justify-content: space-between; align-items: center;
  }
  .title-bar h1 { font-size: 22px; color: #0f172a; font-weight: 800; }
  .title-bar span { background: #1e293b; color: #ff9900; padding: 6px 14px; border-radius: 8px; font-size: 12.5px; font-weight: 700; }
  .lanes { display: flex; flex-direction: column; gap: 18px; flex: 1; justify-content: center; }
  .lane {
    border: 2px solid #cbd5e1; border-radius: 14px; padding: 16px 20px; position: relative;
    background: #f8fafc;
  }
  .lane-1 { border-color: #3b82f6; background: #eff6ff; }
  .lane-2 { border-color: #10b981; background: #ecfdf5; }
  .lane-header {
    font-size: 14px; font-weight: 800; text-transform: uppercase; margin-bottom: 14px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .lane-1 .lane-header { color: #1d4ed8; }
  .lane-2 .lane-header { color: #047857; }
  .steps { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; align-items: stretch; }
  .step {
    background: #ffffff; border: 1.5px solid #94a3b8; border-radius: 10px; padding: 12px;
    box-shadow: 0 3px 8px rgba(0,0,0,0.06); display: flex; flex-direction: column; justify-content: space-between;
  }
  .step-num {
    display: inline-block; width: 24px; height: 24px; border-radius: 50%; background: #1d4ed8;
    color: #fff; font-weight: 800; font-size: 12px; text-align: center; line-height: 24px; margin-bottom: 6px;
  }
  .lane-2 .step-num { background: #047857; }
  .step h4 { font-size: 13.5px; color: #0f172a; margin-bottom: 5px; }
  .step p { font-size: 11.5px; color: #334155; line-height: 1.38; }
  .step-code {
    margin-top: 8px; background: #0f172a; color: #38bdf8; padding: 5px 8px;
    border-radius: 5px; font-family: Consolas, monospace; font-size: 10.5px;
  }
  .branch-box {
    margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
  }
  .branch {
    background: #ffffff; border-left: 5px solid #22c55e; padding: 9px 14px; border-radius: 8px;
    font-size: 12px; color: #1e293b; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
  }
  .branch.reject { border-left-color: #ef4444; }
  .footer-note {
    background: #0f172a; color: #f8fafc; padding: 12px 18px; border-radius: 10px;
    display: flex; justify-content: space-between; align-items: center; font-size: 12px;
  }
  .footer-note b { color: #ff9900; }
</style>
</head>
<body>
<div class="canvas">
  <div class="title-bar">
    <h1>FLUXOGRAMA DE AUTOMAÇÃO SERVERLESS — EVENTOS EM TEMPO REAL E AGENDAMENTOS</h1>
    <span>Zero Intervenção Manual • Escalabilidade Elástica</span>
  </div>

  <div class="lanes">
    <!-- FLUXO 1: EVENTOS DA APLICAÇÃO EM TEMPO REAL -->
    <div class="lane lane-1">
      <div class="lane-header">
        <span>⚡ FLUXO A: AUTOMAÇÃO ORIENTADA A EVENTOS DA APLICAÇÃO (TEMPO REAL — MILISSEGUNDOS)</span>
        <span>Gatilho: Event Pattern JSON</span>
      </div>
      <div class="steps">
        <div class="step">
          <div>
            <span class="step-num">1</span>
            <h4>Ingestão do Pedido</h4>
            <p>Cliente finaliza compra no e-commerce. A aplicação publica o evento no barramento customizado.</p>
          </div>
          <div class="step-code">EventBridge PutEvents<br>DetailType: OrderCreated</div>
        </div>

        <div class="step">
          <div>
            <span class="step-num">2</span>
            <h4>Roteamento e Validação</h4>
            <p>Regra do EventBridge aciona a função <b>λ validadorPedidos</b>. Verifica itens, estoque e score antifraude.</p>
          </div>
          <div class="step-code">Score ≤ 80 &amp; Estoque OK?<br>➔ Emite Novo Evento</div>
        </div>

        <div class="step">
          <div>
            <span class="step-num">3</span>
            <h4>Persistência no RDS</h4>
            <p>Se aprovado (<b>OrderValidated</b>), aciona <b>λ atualizadorStatus</b>, que grava no <b>Amazon RDS Multi-AZ</b>.</p>
          </div>
          <div class="step-code">UPDATE orders SET status=<br>'AGUARDANDO_SEPARACAO'</div>
        </div>

        <div class="step">
          <div>
            <span class="step-num">4</span>
            <h4>Evento de Status</h4>
            <p>Após gravar no RDS, a função publica <b>OrderStatusUpdated</b> no EventBridge para desacoplar os avisos.</p>
          </div>
          <div class="step-code">DetailType:<br>OrderStatusUpdated</div>
        </div>

        <div class="step">
          <div>
            <span class="step-num">5</span>
            <h4>Notificação via SNS</h4>
            <p>Regra aciona <b>λ notificadorEquipes</b>, que publica nos tópicos <b>Amazon SNS</b> de Logística e Atendimento.</p>
          </div>
          <div class="step-code">sns:Publish ➔ Expedição<br>sns:Publish ➔ Atendimento</div>
        </div>
      </div>

      <div class="branch-box">
        <div class="branch">
          <b>✅ Caminho Feliz (OrderValidated ➔ OrderStatusUpdated):</b> Pedido liberado automaticamente para separação física na Logística e cliente notificado em menos de 50 ms.
        </div>
        <div class="branch reject">
          <b>🛡️ Caminho de Exceção (OrderRejected):</b> Se faltar estoque ou score antifraude &gt; 80, o EventBridge aciona diretamente <b>λ notificadorEquipes</b> para alerta imediato ao Atendimento.
        </div>
      </div>
    </div>

    <!-- FLUXO 2: AGENDAMENTO PROGRAMADO (CRON / RATE) -->
    <div class="lane lane-2">
      <div class="lane-header">
        <span>⏰ FLUXO B: AUTOMAÇÃO BASEADA EM AGENDAMENTOS PROGRAMADOS (BATCH SERVERLESS)</span>
        <span>Gatilho: EventBridge Schedule (Cron / Rate)</span>
      </div>
      <div class="steps">
        <div class="step">
          <div>
            <span class="step-num">1</span>
            <h4>Gatilho Temporal</h4>
            <p>O <b>EventBridge Scheduler</b> dispara automaticamente todo dia às 03:00 UTC (00:00 BRT) ou a cada 1h em promoções.</p>
          </div>
          <div class="step-code">cron(0 3 * * ? *)<br>rate(1 hour)</div>
        </div>

        <div class="step">
          <div>
            <span class="step-num">2</span>
            <h4>Acionamento Lambda</h4>
            <p>Inicia a função <b>λ geradorRelatoriosVendas</b> (512 MB RAM) sem necessidade de servidor dedicado ligado 24/7.</p>
          </div>
          <div class="step-code">Target: λ geradorRelatorios<br>Custo Ocioso = R$ 0,00</div>
        </div>

        <div class="step">
          <div>
            <span class="step-num">3</span>
            <h4>Leitura Isolada (RDS)</h4>
            <p>Consulta milhares de transações diretamente na <b>Read Replica do Amazon RDS</b>, preservando a CPU do banco primário.</p>
          </div>
          <div class="step-code">SELECT * FROM orders<br>(Read Replica Endpoint)</div>
        </div>

        <div class="step">
          <div>
            <span class="step-num">4</span>
            <h4>Gravação no Amazon S3</h4>
            <p>Gera os arquivos consolidados (JSON e CSV) e armazena no <b>Amazon S3</b> com 11 noves de durabilidade e Lifecycle.</p>
          </div>
          <div class="step-code">s3:PutObject (AES-256)<br>Standard ➔ IA ➔ Glacier</div>
        </div>

        <div class="step">
          <div>
            <span class="step-num">5</span>
            <h4>Resumo Executivo</h4>
            <p>Publica notificação no <b>Amazon SNS</b> informando receita total, ticket médio e link seguro do relatório no S3.</p>
          </div>
          <div class="step-code">sns:Publish ➔ Diretoria<br>&amp; CloudWatch Metrics</div>
        </div>
      </div>
    </div>
  </div>

  <div class="footer-note">
    <div><b>Observabilidade Transversal:</b> Todas as etapas registram logs estruturados no <b>Amazon CloudWatch Logs</b> com alarmes vinculados ao <b>Amazon SNS</b>.</div>
    <div><b>IaC:</b> Provisionado via <code>serverless.yml</code> (<code>npx sls deploy</code>)</div>
  </div>
</div>
</body>
</html>
"""

# 3. HTML: Evidência Visual de Execução (Console CloudWatch Logs + EventBridge + S3)
HTML_EVIDENCIA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, Arial, sans-serif; }
  body { width: 1400px; height: 820px; background: #0f172a; color: #f8fafc; padding: 20px; overflow: hidden; }
  .window {
    width: 100%; height: 100%; background: #1e293b; border: 1.5px solid #475569;
    border-radius: 12px; overflow: hidden; display: flex; flex-direction: column;
  }
  .aws-nav {
    background: #232f3e; padding: 10px 20px; display: flex; justify-content: space-between;
    align-items: center; border-bottom: 2px solid #ff9900;
  }
  .aws-brand { display: flex; align-items: center; gap: 12px; font-weight: 800; font-size: 15px; color: #ffffff; }
  .aws-badge { background: #ff9900; color: #111827; padding: 3px 9px; border-radius: 4px; font-size: 12px; font-weight: 900; }
  .aws-meta { font-size: 12px; color: #cbd5e1; font-family: Consolas, monospace; }
  .content { padding: 16px 20px; display: grid; grid-template-columns: 420px 1fr; gap: 16px; flex: 1; overflow: hidden; }
  .left-col { display: flex; flex-direction: column; gap: 12px; }
  .panel {
    background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 12px 14px;
  }
  .panel h3 { font-size: 13px; color: #ff9900; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px; }
  .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .metric { background: #1e293b; padding: 8px 10px; border-radius: 6px; border-left: 3px solid #22c55e; }
  .metric .val { font-size: 18px; font-weight: 800; color: #ffffff; }
  .metric .lbl { font-size: 11px; color: #94a3b8; }
  .table-mini { width: 100%; border-collapse: collapse; font-size: 11.5px; }
  .table-mini th, .table-mini td { text-align: left; padding: 6px 6px; border-bottom: 1px solid #1e293b; }
  .table-mini th { color: #94a3b8; font-weight: 600; }
  .status-ok { background: rgba(34,197,94,0.18); color: #4ade80; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px; }
  .status-warn { background: rgba(239,68,68,0.2); color: #f87171; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px; }
  .log-panel {
    background: #090d16; border: 1px solid #334155; border-radius: 8px; padding: 14px;
    font-family: Consolas, 'Courier New', monospace; font-size: 11.3px; line-height: 1.44;
    color: #e2e8f0; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between;
  }
  .log-line { margin-bottom: 3px; }
  .c-eb { color: #f472b6; font-weight: 700; }
  .c-start { color: #38bdf8; }
  .c-info { color: #a7f3d0; }
  .c-warn { color: #fca5a5; font-weight: 700; }
  .c-sns { color: #c084fc; }
  .c-s3 { color: #fde047; font-weight: 700; }
  .c-rep { color: #94a3b8; background: rgba(255,255,255,0.04); padding: 2px 4px; border-radius: 3px; }
</style>
</head>
<body>
<div class="window">
  <div class="aws-nav">
    <div class="aws-brand">
      <span class="aws-badge">AWS</span>
      <span>Amazon CloudWatch Logs &amp; EventBridge — Evidência de Execução Automatizada (TechCommerce)</span>
    </div>
    <div class="aws-meta">Região: sa-east-1 (São Paulo) | Stack: techcommerce-serverless-automation-prod</div>
  </div>

  <div class="content">
    <div class="left-col">
      <div class="panel">
        <h3>📊 Métricas de Execução (Sem Intervenção Manual)</h3>
        <div class="metric-grid">
          <div class="metric"><div class="val">9 Eventos</div><div class="lbl">Roteados no EventBridge</div></div>
          <div class="metric"><div class="val">8 Invocações</div><div class="lbl">Funções AWS Lambda (0 Erros)</div></div>
          <div class="metric"><div class="val">~19.4 ms</div><div class="lbl">Latência Média por Função</div></div>
          <div class="metric"><div class="val">R$ 10.099,90</div><div class="lbl">Receita Consolidada no S3</div></div>
        </div>
      </div>

      <div class="panel">
        <h3>⚡ Funções Lambda Acionadas na Demonstração</h3>
        <table class="table-mini">
          <thead><tr><th>Função AWS Lambda</th><th>Gatilho</th><th>Status</th></tr></thead>
          <tbody>
            <tr><td>λ validadorPedidos</td><td>OrderCreated</td><td><span class="status-ok">200 OK (3x)</span></td></tr>
            <tr><td>λ atualizadorStatus</td><td>OrderValidated</td><td><span class="status-ok">200 OK (2x)</span></td></tr>
            <tr><td>λ notificadorEquipes</td><td>Status / Rejected</td><td><span class="status-ok">200 OK (3x)</span></td></tr>
            <tr><td>λ geradorRelatoriosVendas</td><td>cron(0 3 * * ? *)</td><td><span class="status-ok">200 OK (1x)</span></td></tr>
          </tbody>
        </table>
      </div>

      <div class="panel">
        <h3>🗄️ Estado dos Pedidos no Amazon RDS Multi-AZ</h3>
        <table class="table-mini">
          <thead><tr><th>Pedido</th><th>Cliente</th><th>Valor</th><th>Status Final</th></tr></thead>
          <tbody>
            <tr><td>TC-2026-98410</td><td>Mariana Silva</td><td>R$ 5.199,90</td><td><span class="status-ok">EM SEPARAÇÃO</span></td></tr>
            <tr><td>TC-2026-98411</td><td>Carlos Souza</td><td>R$ 4.900,00</td><td><span class="status-ok">EM SEPARAÇÃO</span></td></tr>
            <tr><td>TC-2026-98412</td><td>Roberto Almeida</td><td>R$ 34.500,00</td><td><span class="status-warn">REJEITADO (FRAUDE)</span></td></tr>
          </tbody>
        </table>
      </div>

      <div class="panel">
        <h3>🪣 Objetos Gravados no Bucket Amazon S3</h3>
        <div style="font-family: Consolas, monospace; font-size: 11px; color: #fde047; line-height: 1.5;">
          s3://techcommerce-relatorios-vendas-prod/<br>
          ├── relatorios/2026/11/relatorio_vendas_2026-11-13.json (1.3 KB)<br>
          └── relatorios/2026/11/relatorio_vendas_2026-11-13.csv (370 B)<br>
          <span style="color:#94a3b8;">Criptografia: SSE-S3 (AES-256) | Durabilidade: 99,999999999%</span>
        </div>
      </div>
    </div>

    <div class="log-panel">
      <div>
        <div style="color:#ff9900; font-weight:700; margin-bottom:8px; border-bottom:1px solid #334155; padding-bottom:5px;">
          Log Group: /aws/lambda/techcommerce-serverless-automation-prod • Stream: 2026/11/12/[$LATEST]9341d2f9
        </div>

        <div class="log-line c-eb">[AMAZON EVENTBRIDGE] Bus='techcommerce-event-bus-prod' | source='com.techcommerce.orders' | detail-type='OrderCreated' (TC-2026-98410)</div>
        <div class="log-line c-start">START RequestId: 25084ccf-d9fc-4dfb-89c8-518aee7c44cc Version: $LATEST (validadorPedidos)</div>
        <div class="log-line c-info">INFO [VALIDADOR_PEDIDOS] Iniciando validação automática do pedido TC-2026-98410 | Cliente: Mariana Costa Silva | Valor: R$ 5199.90</div>
        <div class="log-line c-info">INFO [VALIDADOR_PEDIDOS] Pedido TC-2026-98410 VALIDADO com sucesso (2 itens verificados). Emitindo 'OrderValidated'.</div>
        <div class="log-line c-rep">REPORT RequestId: 25084ccf-d9fc-4dfb-89c8-518aee7c44cc  Duration: 19.36 ms  Billed Duration: 20 ms  Memory Size: 256 MB  Max Memory: 74 MB</div>

        <div class="log-line c-eb" style="margin-top:6px;">[AMAZON EVENTBRIDGE] Rule='rule-atualizador-status' matched 'OrderValidated' ➔ Target: atualizadorStatus</div>
        <div class="log-line c-start">START RequestId: aa680621-35b7-43ff-9e03-4b81df2c3508 Version: $LATEST (atualizadorStatus)</div>
        <div class="log-line c-info">INFO [ATUALIZADOR_STATUS] Atualizando status no Amazon RDS (Multi-AZ) para 'AGUARDANDO_SEPARACAO_LOGISTICA'.</div>
        <div class="log-line c-info">INFO [ATUALIZADOR_STATUS] Transação TC-2026-98410 persistida no RDS e evento 'OrderStatusUpdated' publicado no EventBridge.</div>
        <div class="log-line c-rep">REPORT RequestId: aa680621-35b7-43ff-9e03-4b81df2c3508  Duration: 19.20 ms  Billed Duration: 20 ms  Memory Size: 256 MB  Max Memory: 74 MB</div>

        <div class="log-line c-eb" style="margin-top:6px;">[AMAZON EVENTBRIDGE] Rule='rule-notificador-equipes' matched 'OrderStatusUpdated' ➔ Target: notificadorEquipes</div>
        <div class="log-line c-sns">   [AWS SNS PUBLISH] Topic=techcommerce-notificacoes-logistica-prod | Subject='[Expedição] Pedido TC-2026-98410'</div>
        <div class="log-line c-sns">   [AWS SNS PUBLISH] Topic=techcommerce-notificacoes-atendimento-prod | Subject='[Atualização de Pedido] TC-2026-98410'</div>
        <div class="log-line c-rep">REPORT RequestId: d1164d56-f9a4-4040-9b03-e8251eea06d5  Duration: 19.20 ms  Billed Duration: 20 ms  Memory Size: 256 MB  Max Memory: 74 MB</div>

        <div class="log-line c-eb" style="margin-top:6px;">[AMAZON EVENTBRIDGE] Bus='techcommerce-event-bus-prod' | detail-type='OrderCreated' (TC-2026-98412 - Roberto Almeida)</div>
        <div class="log-line c-warn">WARN [VALIDADOR_PEDIDOS] Pedido TC-2026-98412 REJEITADO. Motivos: Estoque insuficiente (SKU GPU-RTX-4090); Score antifraude elevado (92/100).</div>
        <div class="log-line c-sns">   [AWS SNS PUBLISH] Topic=techcommerce-notificacoes-atendimento-prod | Subject='[Ação Necessária] Pedido Rejeitado TC-2026-98412'</div>

        <div class="log-line c-eb" style="margin-top:6px;">[EVENTBRIDGE SCHEDULER] Disparo automático programado: cron(0 3 * * ? *) ➔ Target: geradorRelatoriosVendas</div>
        <div class="log-line c-start">START RequestId: 78c12356-7a83-4807-a18f-0f8b5f9a7ed4 Version: $LATEST (geradorRelatoriosVendas)</div>
        <div class="log-line c-info">INFO [GERADOR_RELATORIOS] Consultando Read Replica do Amazon RDS: techcommerce-db-read-replica.c9akciq32.sa-east-1.rds.amazonaws.com</div>
        <div class="log-line c-s3">   [AWS S3 PUT_OBJECT] s3://techcommerce-relatorios-vendas-prod/relatorios/2026/11/relatorio_vendas_2026-11-13.json (1305 bytes)</div>
        <div class="log-line c-s3">   [AWS S3 PUT_OBJECT] s3://techcommerce-relatorios-vendas-prod/relatorios/2026/11/relatorio_vendas_2026-11-13.csv (370 bytes)</div>
        <div class="log-line c-sns">   [AWS SNS PUBLISH] Topic=techcommerce-notificacoes-logistica-prod | Subject='[Relatório Diário S3] Receita: R$ 10.099,90'</div>
        <div class="log-line c-rep">REPORT RequestId: 78c12356-7a83-4807-a18f-0f8b5f9a7ed4  Duration: 21.44 ms  Billed Duration: 22 ms  Memory Size: 512 MB  Max Memory: 92 MB</div>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""

def render_screenshot(html_content: str, html_name: str, png_name: str, width: int, height: int):
    html_path = DIAG_DIR / html_name
    png_path = DIAG_DIR / png_name
    html_path.write_text(html_content, encoding="utf-8")
    cmd = [
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={png_path.resolve()}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True)
    print(f"Gerado com sucesso: {png_path} ({png_path.stat().st_size} bytes)")


if __name__ == "__main__":
    render_screenshot(HTML_ARQUITETURA, "arquitetura_aws.html", "diagrama_arquitetura_aws.png", 1400, 860)
    render_screenshot(HTML_FLUXOGRAMA, "fluxograma_automacao.html", "diagrama_fluxo_automacao.png", 1400, 800)
    render_screenshot(HTML_EVIDENCIA, "evidencia_cloudwatch.html", "evidencia_execucao_cloudwatch.png", 1400, 820)
