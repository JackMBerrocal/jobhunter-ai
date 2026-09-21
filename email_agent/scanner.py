import imaplib
import email
from email.header import decode_header
import datetime
from typing import List, Dict, Any, Optional
from adapters.browser_manager import BrowserManager


class EmailScanner:
    """
    Escanea la bandeja de entrada para detectar correos de reclutadores,
    invitaciones a entrevistas o pruebas técnicas.
    Admite dos modos:
    1. Modo Navegador: Lee Gmail directamente a través de la sesión activa en Chromium.
    2. Modo IMAP: Conexión segura con Contraseña de Aplicación.
    """

    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser_manager = browser_manager

    async def scan_gmail_via_browser(self) -> List[Dict[str, Any]]:
        """
        Escanea Gmail utilizando la sesión persistente del navegador,
        sin necesidad de almacenar contraseñas ni configurar credenciales IMAP.
        """
        if not self.browser_manager:
            return []

        import hashlib
        import urllib.parse
        page = await self.browser_manager.new_page_with_stealth()
        detected_emails = []

        try:
            print("[EmailScanner] Abriendo Gmail en la sesión persistente...")
            # Búsqueda ampliada con ATS, evaluaciones (evaluar, buk, aira) y procesos de selección
            search_terms = 'entrevista OR "postulación" OR postulacion OR "prueba técnica" OR evaluaciones OR evaluacion OR evaluar OR buk OR aira OR reclutamiento OR "proceso de selección" OR seleccion OR vacante'
            encoded_query = urllib.parse.quote(search_terms)
            gmail_search_url = f"https://mail.google.com/mail/u/0/#search/{encoded_query}"

            await page.goto(gmail_search_url, wait_until="domcontentloaded", timeout=25000)
            await self.browser_manager.random_delay(3.0, 4.5)

            # Verificar si cargó Gmail
            if "mail.google.com" not in page.url:
                print("[EmailScanner] Sesión de Gmail no activa. Ejecuta login_setup.py primero.")
                return []

            # Filas de correos en Gmail: tr.zA
            email_rows = await page.query_selector_all("tr.zA")
            print(f"[EmailScanner] Correos relevantes encontrados en Gmail: {len(email_rows)}")

            for row in email_rows[:35]:
                try:
                    # Remitente
                    sender_elem = await row.query_selector(".zF, .yX, span[email]")
                    sender = (await sender_elem.inner_text()).strip() if sender_elem else "Desconocido"

                    # Asunto y snippet
                    subject_elem = await row.query_selector(".bog, span.bqe")
                    subject = (await subject_elem.inner_text()).strip() if subject_elem else "Sin asunto"

                    snippet_elem = await row.query_selector("span.y2")
                    snippet = (await snippet_elem.inner_text()).strip() if snippet_elem else ""

                    # Fecha aproximada visible
                    date_elem = await row.query_selector("td.xW span, span.xW")
                    date_str = (await date_elem.inner_text()).strip() if date_elem else ""

                    # ID único y persistente: intentar ID nativo de Google o hash criptográfico (evitando IDs DOM como :58)
                    legacy_id = await row.get_attribute("data-legacy-thread-id") or await row.get_attribute("data-thread-id")
                    if legacy_id and not legacy_id.startswith(":"):
                        msg_id = f"gmail_{legacy_id}"
                    else:
                        clean_sig = f"{sender.lower().strip()}|{subject.lower().strip()}|{snippet[:50].lower().strip()}"
                        msg_id = f"hash_{hashlib.sha256(clean_sig.encode('utf-8')).hexdigest()[:16]}"

                    detected_emails.append({
                        "message_id": str(msg_id),
                        "sender": sender,
                        "subject": subject,
                        "snippet": snippet,
                        "date_str": date_str,
                        "body": f"{subject}\n\n{snippet}",
                        "received_at": datetime.datetime.now()
                    })
                except Exception as row_err:
                    print(f"[EmailScanner] Error al leer fila de correo: {row_err}")
                    continue

        except Exception as e:
            print(f"[EmailScanner] Error escaneando Gmail: {e}")
        finally:
            await page.close()

        return detected_emails

    def scan_via_imap(self, host: str, user: str, app_password: str) -> List[Dict[str, Any]]:
        """Escanea la bandeja mediante IMAP seguro."""
        detected = []
        try:
            mail = imaplib.IMAP4_SSL(host)
            mail.login(user, app_password)
            mail.select("INBOX")

            # Buscar correos recientes con palabras clave de empleo
            search_query = '(OR (SUBJECT "entrevista") (OR (SUBJECT "seleccion") (SUBJECT "tecnica")))'
            status, messages = mail.search(None, search_query)
            if status != "OK" or not messages[0]:
                mail.logout()
                return []

            msg_ids = messages[0].split()
            # Tomar los últimos 10 correos
            for mid in msg_ids[-10:]:
                res, data = mail.fetch(mid, "(RFC822)")
                for response_part in data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                        sender = msg.get("From", "Desconocido")
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode(errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode(errors="ignore")

                        detected.append({
                            "message_id": f"imap_{mid.decode()}",
                            "sender": sender,
                            "subject": subject,
                            "snippet": body[:200],
                            "body": body,
                            "received_at": datetime.datetime.now()
                        })
            mail.logout()
        except Exception as e:
            print(f"[EmailScanner] Error en conexión IMAP: {e}")

        return detected
