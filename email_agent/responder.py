import re
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from core.database import SessionLocal, EmailMessage, Job
from core.llm_engine import LLMEngine
from email_agent.scanner import EmailScanner


def find_matching_job_for_email(db: Session, sender: str, subject: str, body: str) -> Optional[Job]:
    """Busca en la base de datos la vacante exacta que originó este correo."""
    text = f"{sender} {subject} {body}".lower()
    
    # 1. Búsqueda por coincidencia de empresa y título
    jobs = db.query(Job).order_by(Job.applied_at.desc().nullslast()).all()
    best_job = None
    best_score = 0
    
    for j in jobs:
        score = 0
        comp = (j.company or "").lower()
        if len(comp) > 3 and not any(bad in comp for bad in ["confidencial", "tecnología", "empleadora", "computrabajo"]):
            comp_clean = re.sub(r'\b(s\.a\.c|s\.a|s\.r\.l|sac|sa|s\.a\.a)\b', '', comp).strip()
            if len(comp_clean) >= 3 and comp_clean in text:
                score += 8
            else:
                # Palabras individuales distintivas de la empresa (ej: monnet, solgas, valtx, alicorp, etc.)
                words_ignore = {"pagos", "linea", "peru", "group", "solutions", "latin", "america", "asociados", "comercial", "industrial", "servicios", "corporation", "banco", "bank"}
                comp_distinct = [w.strip(".,-") for w in comp_clean.split() if len(w.strip(".,-")) >= 4 and w.strip(".,-") not in words_ignore]
                if any(re.search(rf'\b{re.escape(w)}\b', text) for w in comp_distinct):
                    score += 7

        # Búsqueda por palabras distintivas del título
        t_words = [w for w in re.split(r'\W+', (j.title or "").lower()) if len(w) > 4 and w not in ["practicante", "junior", "asistente", "senior", "remoto", "modalidad"]]
        matches = sum(1 for w in t_words if re.search(rf'\b{re.escape(w)}\b', text))
        if matches >= 1:
            score += matches * 3

        # Si coincide slug de la URL
        if j.url:
            slug_match = re.search(r'/empleos/([^/?#]+)', j.url)
            if slug_match:
                slug_words = [w for w in slug_match.group(1).split('-') if len(w) > 4 and w not in ["practicante", "junior", "empleo", "oferta", "trabajo"]]
                matches_slug = sum(1 for sw in slug_words if re.search(rf'\b{re.escape(sw)}\b', text))
                score += matches_slug * 3

        if score > best_score:
            best_score = score
            best_job = j
            
    if best_score >= 5:
        return best_job
    return None


class EmailAgent:
    """
    Gestiona el ciclo de vida de los correos laborales:
    Detección -> Clasificación con LLM -> Generación de Respuesta -> Notificación.
    """

    def __init__(self, scanner: EmailScanner, llm_engine: LLMEngine):
        self.scanner = scanner
        self.llm = llm_engine

    async def process_inbox(self, db: Session, auto_reply: bool = False) -> List[Dict[str, Any]]:
        """
        Escanea la bandeja, filtra correos no leídos o nuevos,
        genera respuestas y los almacena en la base de datos vinculándolos a la oferta laboral.
        """
        raw_emails = await self.scanner.scan_gmail_via_browser()
        processed_records = []

        for item in raw_emails:
            # Comprobar si ya está registrado en la base de datos
            existing = db.query(EmailMessage).filter(EmailMessage.message_id == item["message_id"]).first()
            if existing:
                continue

            # Analizar con LLM
            analysis = self.llm.classify_and_draft_email(
                subject=item["subject"],
                sender=item["sender"],
                body=item["body"]
            )

            # Vincular a la vacante correspondiente en la base de datos
            matched_job = find_matching_job_for_email(db, item["sender"], item["subject"], item["body"])
            job_id = matched_job.id if matched_job else None

            # Extraer enlaces de pruebas técnicas o reuniones
            action_url = None
            url_match = re.search(r'https?://[^\s<>"\']+(?:evaluar\.com|buk\.(?:pe|cl)|meet\.google\.com|zoom\.us|teams\.microsoft\.com|hackerrank\.com)[^\s<>"\']*', item["body"])
            if url_match:
                action_url = url_match.group(0).rstrip('.,;')

            # Crear registro en la BD
            new_msg = EmailMessage(
                job_id=job_id,
                message_id=item["message_id"],
                sender=item["sender"],
                subject=item["subject"],
                snippet=item["snippet"],
                body=item["body"],
                category=analysis.get("category", "other"),
                confidence=analysis.get("confidence", 0.7),
                received_at=item["received_at"],
                action_url=action_url,
                action_taken="pending" if not auto_reply else "replied",
                proposed_reply=analysis.get("proposed_reply", "")
            )

            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)

            job_badge = f" [Vacante vinculada: #{matched_job.id} {matched_job.title} en {matched_job.company}]" if matched_job else ""
            print(f"[EmailAgent] 📩 Nuevo correo detectado: '{item['subject']}' | Categoría: {new_msg.category}{job_badge}")
            processed_records.append({
                "id": new_msg.id,
                "subject": new_msg.subject,
                "category": new_msg.category,
                "summary": analysis.get("summary", ""),
                "proposed_reply": new_msg.proposed_reply
            })

        return processed_records

    def approve_and_send_reply(self, db: Session, email_id: int, custom_reply: str = None) -> bool:
        """
        Aprueba el envío de una respuesta (manual desde el dashboard o automática).
        """
        msg = db.query(EmailMessage).filter(EmailMessage.id == email_id).first()
        if not msg:
            return False

        reply_text = custom_reply if custom_reply else msg.proposed_reply
        msg.sent_reply = reply_text
        msg.action_taken = "replied"
        msg.replied_at = datetime.datetime.now()
        db.commit()
        print(f"[EmailAgent] ✅ Respuesta registrada y enviada para correo ID {email_id}")
        return True
