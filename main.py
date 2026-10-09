import sys
import argparse
import asyncio
import uvicorn
from core.database import init_db
from login_setup import run_login_session
from web_ui.app import app, execute_job_hunting_cycle, execute_email_scan_cycle


async def run_daemon():
    print("=" * 60)
    print("🤖 JOBHUNTER AI - MODO GUARDIÁN AUTÓNOMO (DAEMON)")
    print("=" * 60)
    print("El agente se ejecutará en segundo plano:")
    print(" - Monitoreo de correos cada 30 minutos.")
    print(" - Exploración y postulación de vacantes remotas 3 veces al día.")
    print("Presiona Ctrl + C para detener.")
    print("=" * 60)

    # Ciclo continuo
    minute_counter = 0
    while True:
        try:
            # Cada 30 minutos: Escanear emails
            if minute_counter % 30 == 0:
                print("\n[Daemon] Ejecutando revisión periódica de correos...")
                await execute_email_scan_cycle()

            # Cada 180 minutos (3 horas): Búsqueda de empleo
            if minute_counter % 180 == 0:
                print("\n[Daemon] Ejecutando ronda de búsqueda y postulación...")
                await execute_job_hunting_cycle()

            await asyncio.sleep(60)
            minute_counter += 1
        except asyncio.CancelledError:
            print("[Daemon] Tarea cancelada por el usuario.")
            break
        except Exception as e:
            print(f"[Daemon] Error en loop: {e}")
            await asyncio.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="JobHunter AI - Agente de Búsqueda Laboral")
    parser.add_argument("--login", action="store_true", help="Abrir navegador persistente para iniciar sesión en los portales")
    parser.add_argument("--run-now", action="store_true", help="Ejecutar de inmediato una ronda de búsqueda y postulación")
    parser.add_argument("--scan-emails", action="store_true", help="Escanear bandeja de entrada inmediatamente")
    parser.add_argument("--daemon", action="store_true", help="Iniciar agente autónomo continuo en segundo plano")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del Dashboard Web (por defecto 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host del servidor Web")

    args = parser.parse_args()

    # Inicializar tablas de base de datos
    init_db()

    if args.login:
        asyncio.run(run_login_session())
    elif args.run_now:
        asyncio.run(execute_job_hunting_cycle())
    elif args.scan_emails:
        asyncio.run(execute_email_scan_cycle())
    elif args.daemon:
        asyncio.run(run_daemon())
    else:
        port = int(os.environ.get("PORT", args.port))
        print(f"🚀 Iniciando Dashboard de JobHunter AI en http://{args.host}:{port}")
        uvicorn.run("web_ui.app:app", host=args.host, port=port, reload=False)


if __name__ == "__main__":
    main()
