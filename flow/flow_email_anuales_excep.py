"""
Envío excepcional a suscriptores ANUALES con vencimiento en menos de 30 días.
No modifica la lógica de flow_email_avisos.py (3 y 14 días).
Marca mail_enviado = 30 tras el envío.
"""
import sys
import os
import argparse
from datetime import datetime, timedelta

import mysql.connector

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG
from config.gmail_config import TEST_EMAIL
from flow_email_avisos import build_email, send_email, ASUNTOS


ASUNTO_EXCEP = 'Tu suscripción anual 13go vence pronto'


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def get_anuales_proximos(conn):
    """Anuales con subscription_end entre hoy y hoy+30, aún no notificados (mail_enviado = 0)."""
    hoy   = datetime.now().date()
    hasta = hoy + timedelta(days=30)
    sql = """
        SELECT user_id, email, plan, inicio_plan, fin_plan, subscription_end, dias_hasta_fin
        FROM flow_cancelados
        WHERE plan IN ('s-13go-A002', 's-13go-B002')
          AND subscription_end IS NOT NULL
          AND DATE(subscription_end) BETWEEN %s AND %s
          AND mail_enviado = 0
    """
    with conn.cursor(dictionary=True) as cur:
        cur.execute(sql, (hoy, hasta))
        return cur.fetchall()


def dias_reales(row):
    """Días reales desde hoy hasta subscription_end."""
    sub_end = row.get('subscription_end')
    if isinstance(sub_end, datetime):
        sub_end = sub_end.date()
    elif isinstance(sub_end, str):
        sub_end = datetime.strptime(sub_end[:10], '%Y-%m-%d').date()
    return (sub_end - datetime.now().date()).days


def marcar_enviado(conn, user_ids):
    if not user_ids:
        return
    placeholders = ','.join(['%s'] * len(user_ids))
    sql = f"UPDATE flow_cancelados SET mail_enviado = 30 WHERE user_id IN ({placeholders})"
    with conn.cursor() as cur:
        cur.execute(sql, user_ids)
    conn.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Envío excepcional a suscriptores anuales con vencimiento en menos de 30 días.'
    )
    parser.add_argument('--test', action='store_true',
                        help=f'Modo prueba: envía solo a {TEST_EMAIL}, sin actualizar mail_enviado')
    args = parser.parse_args()

    conn = get_connection()
    pendientes = get_anuales_proximos(conn)

    print(f"Modo: {'PRUEBA' if args.test else 'PRODUCCIÓN'}")
    print(f"Anuales con vencimiento en menos de 30 días: {len(pendientes)}\n")

    if not pendientes:
        print("No hay registros para enviar.")
        conn.close()
        sys.exit(0)

    enviados = []
    errores  = 0

    if args.test:
        row  = pendientes[0]
        dias = dias_reales(row)
        html = build_email(row, dias)
        print(f"[PRUEBA] Enviando a {TEST_EMAIL}")
        print(f"  user_id: {row['user_id']}")
        print(f"  email:   {row['email']}")
        print(f"  plan:    {row['plan']}")
        print(f"  sub_end: {row['subscription_end']} ({dias} días)")
        try:
            send_email(TEST_EMAIL, f'[PRUEBA] {ASUNTO_EXCEP}', html)
            print(f"  -> Enviado a {TEST_EMAIL}")
        except Exception as e:
            print(f"  -> Error: {e}")
        print("\nModo prueba: mail_enviado NO actualizado.")
    else:
        for row in pendientes:
            to   = row.get('email')
            dias = dias_reales(row)
            if not to:
                print(f"  Sin email: {row['user_id']} — omitido")
                continue
            html = build_email(row, dias)
            try:
                send_email(to, ASUNTO_EXCEP, html)
                enviados.append(row['user_id'])
                print(f"  OK  {to}  ({dias} días)")
            except Exception as e:
                print(f"  ERR {to}: {e}")
                errores += 1

        if enviados:
            marcar_enviado(conn, enviados)

        print(f"\nEnviados: {len(enviados)} | Errores: {errores}")
        print(f"mail_enviado actualizado a 30 para {len(enviados)} registros.")

    conn.close()
