import sqlite3
import os
import re
from core.company_resolver import resolve_clean_company_name

DB_PATH = "data/jobhunter.db"

def run_migration():
    print(f"=== INICIANDO MIGRACIÓN PROFESIONAL DE DATOS ===")
    if not os.path.exists(DB_PATH):
        print(f"Base de datos {DB_PATH} no encontrada.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Asegurar columnas en email_messages
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(email_messages)").fetchall()]
    print("Columnas actuales en email_messages:", cols)
    
    if "job_id" not in cols:
        print("Añadiendo columna job_id a email_messages...")
        cursor.execute("ALTER TABLE email_messages ADD COLUMN job_id INTEGER REFERENCES jobs(id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_email_messages_job_id ON email_messages(job_id);")

    if "action_url" not in cols:
        print("Añadiendo columna action_url a email_messages...")
        cursor.execute("ALTER TABLE email_messages ADD COLUMN action_url TEXT;")

    conn.commit()

    # 2. Normalizar empresas en la tabla jobs
    print("\n--- Actualizando nombres reales de empresas en jobs ---")
    jobs = cursor.execute("SELECT id, platform, title, company, url, description FROM jobs").fetchall()
    updated_jobs = 0

    for jid, plat, title, comp, url, desc in jobs:
        clean_name = resolve_clean_company_name(comp, url, title, desc)
        if clean_name != comp:
            cursor.execute("UPDATE jobs SET company = ? WHERE id = ?", (clean_name, jid))
            updated_jobs += 1

    conn.commit()
    print(f"✅ Se normalizaron {updated_jobs} vacantes con sus empresas reales (ej: SOLGAS S.A., Monnet, Valtx).")

    # 3. Limpiar IDs DOM efímeros en email_messages
    print("\n--- Saneando tabla email_messages ---")
    stale_emails = cursor.execute("SELECT id, message_id, sender, subject FROM email_messages WHERE message_id LIKE ':%'").fetchall()
    print(f"Detectados {len(stale_emails)} correos con IDs DOM efímeros (:58, :6o, etc.)")
    if stale_emails:
        cursor.execute("DELETE FROM email_messages WHERE message_id LIKE ':%'")
        conn.commit()
        print(f"✅ Se eliminaron {len(stale_emails)} registros efímeros bloqueantes para permitir re-sincronización limpia.")

    conn.close()
    print("=== MIGRACIÓN COMPLETADA EXITOSAMENTE ===")

if __name__ == "__main__":
    run_migration()
