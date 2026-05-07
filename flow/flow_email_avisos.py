import sys
import os
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

import mysql.connector

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG
from config.gmail_config import GMAIL_CONFIG, TEST_EMAIL

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'template_email_3dias.html')

PLANES = {
    's-13go-A003': 'Mensual',
    's-13go-A004': 'Mensual',
    's-13go-B001': 'Mensual',
    's-13go-B004': 'Mensual',
    's-13go-A002': 'Anual',
    's-13go-B002': 'Anual',
}

def traducir_plan(plan_id):
    return PLANES.get(plan_id, plan_id or 'N/A')

MENSAJES = {
    14: """<p style="margin:0 0 24px;font-size:15px;color:#374151;line-height:1.6;">
                Tu suscripción a <strong style="color:#ea580c;">13go</strong> vence en
                <strong>14 días</strong>. Queremos avisarte con anticipación para que
                puedas decidir si deseas renovarla y seguir disfrutando de todo el contenido.
              </p>""",
    3:  """<p style="margin:0 0 24px;font-size:15px;color:#374151;line-height:1.6;">
                Tu suscripción a <strong style="color:#ea580c;">13go</strong> vence en
                <strong style="color:#ea580c;">solo 3 días</strong>. ¡Es tu última oportunidad
                para renovarla y no perder el acceso a tu contenido favorito!
              </p>""",
}

ASUNTOS = {
    14: 'Tu suscripción 13go vence en 14 días',
    3:  '⚠️ Tu suscripción 13go vence en 3 días',
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def get_pendientes(conn, dias):
    """Registros cuyo subscription_end es exactamente hoy + {dias} días.
    - 14 días: solo mail_enviado = 0 (primer contacto)
    - 3 días:  mail_enviado IN (0, 14) — reciben ambos correos
    """
    fecha_exacta = datetime.now().date() + timedelta(days=dias)

    if dias == 14:
        filtro_enviado = "mail_enviado = 0"
        valores = (fecha_exacta,)
    else:  # dias == 3
        filtro_enviado = "mail_enviado IN (0, 14)"
        valores = (fecha_exacta,)

    sql = f"""
        SELECT user_id, email, plan, inicio_plan, fin_plan, subscription_end, dias_hasta_fin
        FROM flow_cancelados
        WHERE {filtro_enviado}
          AND subscription_end IS NOT NULL
          AND DATE(subscription_end) = %s
    """
    with conn.cursor(dictionary=True) as cur:
        cur.execute(sql, valores)
        return cur.fetchall()


def marcar_enviado(conn, user_ids, dias):
    if not user_ids:
        return
    placeholders = ','.join(['%s'] * len(user_ids))
    sql = f"UPDATE flow_cancelados SET mail_enviado = %s WHERE user_id IN ({placeholders})"
    with conn.cursor() as cur:
        cur.execute(sql, [dias] + user_ids)
    conn.commit()


def build_email(row, dias):
    """Construye el HTML del correo reemplazando placeholders."""
    with open(TEMPLATE_PATH, encoding='utf-8') as f:
        html = f.read()

    def fmt_fecha(val):
        if not val:
            return 'N/A'
        if isinstance(val, (datetime,)):
            return val.strftime('%d/%m/%Y')
        return str(val)[:10]

    dias_restantes = row.get('dias_hasta_fin') or dias

    html = html.replace('{{MENSAJE_INTRO}}', MENSAJES[dias])
    html = html.replace('{{PLAN}}',          traducir_plan(row.get('plan')))
    html = html.replace('{{INICIO_PLAN}}',   fmt_fecha(row.get('inicio_plan')))
    html = html.replace('{{FIN_PLAN}}',      fmt_fecha(row.get('fin_plan')))
    html = html.replace('{{DIAS_RESTANTES}}', str(dias_restantes))
    return html


def send_email(to_email, subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f"{GMAIL_CONFIG['sender_name']} <{GMAIL_CONFIG['sender_email']}>"
    msg['To']      = to_email
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP(GMAIL_CONFIG['smtp_host'], GMAIL_CONFIG['smtp_port']) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_CONFIG['sender_email'], GMAIL_CONFIG['app_password'])
        server.sendmail(GMAIL_CONFIG['sender_email'], to_email, msg.as_string())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Envía avisos de vencimiento de suscripción por Gmail.'
    )
    parser.add_argument(
        '--dias', type=int, choices=[3, 14], required=True,
        help='Días de anticipación: 3 o 14'
    )
    parser.add_argument(
        '--test', action='store_true',
        help=f'Modo prueba: envía solo a {TEST_EMAIL}, sin actualizar mail_enviado'
    )
    args = parser.parse_args()

    conn = get_connection()
    pendientes = get_pendientes(conn, args.dias)

    print(f"Modo: {'PRUEBA' if args.test else 'PRODUCCIÓN'} | Días: {args.dias}")
    print(f"Registros encontrados: {len(pendientes)}\n")

    if not pendientes:
        print("No hay registros para enviar.")
        conn.close()
        sys.exit(0)

    subject = ASUNTOS[args.dias]
    enviados = []
    errores  = 0

    if args.test:
        # Prueba: envía el primer registro a tobarcid@gmail.com
        row = pendientes[0]
        html = build_email(row, args.dias)
        print(f"[PRUEBA] Enviando correo de ejemplo a {TEST_EMAIL}...")
        print(f"  user_id: {row['user_id']}")
        print(f"  plan:    {row.get('plan')}")
        print(f"  sub_end: {row.get('subscription_end')}")
        try:
            send_email(TEST_EMAIL, f"[PRUEBA] {subject}", html)
            print(f"  -> Enviado a {TEST_EMAIL}")
        except Exception as e:
            print(f"  -> Error: {e}")
        print("\nModo prueba: mail_enviado NO actualizado.")
    else:
        for row in pendientes:
            to = row.get('email')
            if not to:
                print(f"  Sin email: {row['user_id']} — omitido")
                continue
            html = build_email(row, args.dias)
            try:
                send_email(to, subject, html)
                enviados.append(row['user_id'])
                print(f"  OK  {to}")
            except Exception as e:
                print(f"  ERR {to}: {e}")
                errores += 1

        if enviados:
            marcar_enviado(conn, enviados, args.dias)

        print(f"\nEnviados: {len(enviados)} | Errores: {errores}")
        print(f"mail_enviado actualizado a {args.dias} para {len(enviados)} registros.")

    conn.close()
