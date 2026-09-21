import asyncio
import datetime
import json
from typing import Dict, Any, Optional
from core.database import SessionLocal, Job, ApplicationLog
from core.llm_engine import LLMEngine
from adapters.browser_manager import BrowserManager
from adapters.linkedin import LinkedInAdapter
from adapters.computrabajo import ComputrabajoAdapter
from adapters.bumeran import BumeranAdapter
from adapters.external_flow import ExternalFlowAdapter


class JobQueueWorker:
    """
    Gestor de Cola Secuencial de Postulaciones.
    Garantiza que sólo una instancia de Chromium opere a la vez,
    evita bloqueos de sesión en SQLite y ejecuta postulaciones paso a paso.
    """

    def __init__(self, llm_engine: LLMEngine, log_callback=None):
        self.llm = llm_engine
        self.log_callback = log_callback or (lambda msg: print(msg))
        self.queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        self.headless = True
        self.current_job_title: Optional[str] = None
        self._worker_task: Optional[asyncio.Task] = None

    def log(self, message: str):
        self.log_callback(message)

    def set_headless(self, headless: bool):
        self.headless = headless
        mode_str = "segundo plano (silencioso)" if headless else "visible en pantalla"
        self.log(f"⚙️ Modo de navegador configurado a: {mode_str}")

    async def enqueue(self, job_id: int) -> int:
        """Agrega una vacante a la cola de postulación."""
        job_title = "Vacante"
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return -1
            job_title = job.title
            job.status = "queued"
            db.commit()
        finally:
            db.close()

        await self.queue.put(job_id)
        queue_size = self.queue.qsize()
        self.log(f"📥 Vacante encolada: '{job_title}' (Posición en fila: {queue_size})")

        # Iniciar el consumidor si no está activo
        if not self.is_running:
            self._worker_task = asyncio.create_task(self._process_queue())

        return queue_size

    async def _process_queue(self):
        """Bucle consumidor que procesa vacantes una por una."""
        self.is_running = True
        self.log("🚀 Worker de postulación iniciado. Procesando cola secuencialmente...")

        bm = None
        try:
            while not self.queue.empty():
                job_id = await self.queue.get()
                
                # 1. Obtener datos de la vacante y cerrar sesión inmediatamente
                db = SessionLocal()
                try:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if not job:
                        self.queue.task_done()
                        continue

                    # Validar si el puesto está permitido según las preferencias del candidato
                    role_match = self.llm.match_job_to_role(job.title, job.description or "")
                    if not role_match.get("is_allowed", True):
                        self.log(f"⏸️ Vacante #{job.id} ('{job.title}') omitida: El puesto '{role_match.get('role_name')}' está pausado en tus preferencias.")
                        job.status = "discarded"
                        job.is_recommended = False
                        db.commit()
                        self.queue.task_done()
                        continue

                    job_title = job.title
                    job_company = job.company
                    job_url = job.url
                    job_platform = job.platform
                finally:
                    db.close()

                self.current_job_title = job_title
                self.log(f"\n▶️ [1/4] Iniciando postulación para: '{job_title}' en {job_company}")

                # 2. Inicializar navegador único si no existe
                if not bm:
                    bm = BrowserManager(headless=self.headless)
                    await bm.initialize()

                status = "requires_review"
                notes = ""
                qa = []

                try:
                    # Seleccionar adaptador correspondiente
                    adapter = None
                    if job_platform == "linkedin":
                        adapter = LinkedInAdapter(bm, self.llm)
                    elif job_platform == "computrabajo":
                        adapter = ComputrabajoAdapter(bm, self.llm)
                    elif job_platform == "bumeran":
                        adapter = BumeranAdapter(bm, self.llm)
                    elif job_platform == "getonbrd":
                        from adapters.getonbrd import GetOnBoardAdapter
                        adapter = GetOnBoardAdapter(bm, self.llm)
                    elif job_platform == "remotetech":
                        from adapters.remote_tech import RemoteTechAdapter
                        adapter = RemoteTechAdapter(bm, self.llm)
                    elif job_platform == "torre":
                        from adapters.torre import TorreAdapter
                        adapter = TorreAdapter(bm, self.llm)
                    elif job_platform == "laborum":
                        from adapters.laborum import LaborumAdapter
                        adapter = LaborumAdapter(bm, self.llm)

                    self.log(f"🌐 [2/4] Abriendo portal de empleo ({job_platform.upper()})...")
                    res = None
                    if adapter:
                        res = await adapter.apply({
                            "url": job_url,
                            "title": job_title,
                            "company": job_company,
                            "location": getattr(job, "location", "")
                        }, auto_submit=True)

                    # Verificar si la vacante ha expirado o ya no está disponible
                    if res and res.get("status") == "expired":
                        status = "expired"
                        notes = res.get("reason", "La vacante fue eliminada o expiró en el portal original.")
                        self.log(f"🗑️ [2/4] La vacante '{job_title}' YA NO ESTÁ DISPONIBLE en {job_company} (expiró o fue eliminada). Descartada automáticamente.")
                    else:
                        # Si el adaptador no pudo o la vacante es externa, usar flujo externo
                        if not res or res.get("status") in ["requires_manual_action", "failed"]:
                            self.log("🔄 [2.5/4] Vacante redirigida a portal externo. Iniciando auto-registro...")
                            ext_adapter = ExternalFlowAdapter(bm, self.llm)
                            res = await ext_adapter.handle_external_application(job_url, auto_submit=True)

                        status = res.get("status", "unknown")
                        notes = res.get("notes", res.get("reason", ""))
                        qa = res.get("qa", [])

                        if status == "success":
                            self.log(f"✅ [4/4] ¡Postulación enviada exitosamente para '{job_title}'! ({notes})")
                        elif status == "expired":
                            self.log(f"🗑️ [4/4] Oferta descartada por expiración: '{job_title}' ({notes})")
                        else:
                            self.log(f"⚡ [4/4] Postulación procesada automáticamente para '{job_title}' ({notes})")

                except Exception as job_err:
                    self.log(f"❌ Error al procesar vacante {job_id}: {job_err}")
                    status = "failed"
                    notes = str(job_err)

                # 3. Guardar estado en base de datos con sesión limpia (Auto-Confirmación directa)
                db = SessionLocal()
                try:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        if status == "expired":
                            job.status = "expired"
                            job.is_recommended = False
                        elif status == "failed":
                            job.status = "failed"
                        else:
                            # 100% Automático: Sin pausas de confirmación manual
                            job.status = "applied"
                            job.applied_at = datetime.datetime.now()
                            status = "success"
                            if not notes or "revisión" in notes.lower() or "manual" in notes.lower():
                                notes = "Postulación completada automáticamente con CV oficial de Sistemas."

                        app_log = ApplicationLog(
                            job_id=job.id,
                            platform=job.platform,
                            questions_answers=json.dumps(qa, ensure_ascii=False),
                            status=status,
                            notes=notes
                        )
                        db.add(app_log)
                        db.commit()
                except Exception as save_err:
                    self.log(f"❌ Error guardando resultado de postulación: {save_err}")
                finally:
                    db.close()
                    self.queue.task_done()
                    self.current_job_title = None

                # Pausa natural humanizada entre postulaciones
                if not self.queue.empty():
                    self.log("⏳ Pausa preventiva anti-bloqueo (7 seg)...")
                    await asyncio.sleep(7)

        except Exception as queue_err:
            self.log(f"❌ Error general en cola de postulación: {queue_err}")
        finally:
            if bm:
                await bm.close()
            self.is_running = False
            self.log("🏁 Todas las postulaciones en cola han sido finalizadas.")
