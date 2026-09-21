import asyncio
import datetime
import random
from typing import Optional, Dict, Any
from core.database import SessionLocal, Job, EmailMessage
from core.llm_engine import LLMEngine
from adapters.browser_manager import BrowserManager
from adapters.linkedin import LinkedInAdapter
from adapters.computrabajo import ComputrabajoAdapter
from adapters.bumeran import BumeranAdapter
from adapters.getonbrd import GetOnBoardAdapter
from adapters.remote_tech import RemoteTechAdapter
from adapters.laborum import LaborumAdapter
from email_agent.scanner import EmailScanner
from email_agent.responder import EmailAgent


class AutonomousHunterDaemon:
    """
    Motor de Búsqueda y Postulación Continua 24/7.
    Ejecuta ciclos periódicos e ininterrumpidos en segundo plano:
    1. Revisa respuestas y ofertas en Gmail.
    2. Rastrea vacantes 100% remotas en 5 plataformas simultáneas.
    3. Descarta empleos presenciales o con sueldos inferiores a S/ 2,000 / $800 USD.
    4. Encola y postula automáticamente a los puestos afines.
    5. No se detiene hasta que se alcance una aceptación formal o el usuario lo pause.
    """

    def __init__(self, llm_engine: LLMEngine, job_queue, log_callback=None, interval_minutes: int = 30):
        self.llm = llm_engine
        self.job_queue = job_queue
        self.log_callback = log_callback or (lambda msg: print(msg))
        self.interval_minutes = interval_minutes
        
        self.is_running = False
        self.cycle_count = 0
        self.last_run_time: Optional[datetime.datetime] = None
        self.next_run_time: Optional[datetime.datetime] = None
        self.accepted_offer_detected = False
        self.auto_apply_enabled = True
        
        self._loop_task: Optional[asyncio.Task] = None

    def log(self, message: str):
        self.log_callback(f"[AutonomousHunter 24/7] {message}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "cycle_count": self.cycle_count,
            "last_run": self.last_run_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_run_time else None,
            "next_run": self.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if self.next_run_time else None,
            "interval_minutes": self.interval_minutes,
            "auto_apply": self.auto_apply_enabled,
            "accepted_offer_detected": self.accepted_offer_detected,
            "strict_remote": True,
            "min_salary_pen": 2000,
            "min_salary_usd": 800
        }

    def start(self, interval_minutes: Optional[int] = None):
        """Inicia el demonio de búsqueda continua."""
        if self.is_running:
            self.log("⚠️ El motor continuo ya se encuentra en ejecución.")
            return

        if interval_minutes:
            self.interval_minutes = max(interval_minutes, 10)

        self.accepted_offer_detected = False
        self.is_running = True
        self._loop_task = asyncio.create_task(self._continuous_loop())
        self.log(f"🚀 Motor de Búsqueda Continua 24/7 ACTIVADO. Ciclos cada {self.interval_minutes} minutos.")

    def stop(self):
        """Pausa el demonio de búsqueda continua."""
        self.is_running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        self.next_run_time = None
        self.log("🛑 Motor de Búsqueda Continua 24/7 PAUSADO.")

    async def _continuous_loop(self):
        """Bucle infinito que opera hasta ser detenido o hasta detectar aceptación de trabajo."""
        while self.is_running:
            self.cycle_count += 1
            start_time = datetime.datetime.now()
            self.last_run_time = start_time
            self.log(f"\n=======================================================")
            self.log(f"🔄 INICIANDO CICLO #{self.cycle_count} (100% Remoto | > S/ 2,000 | > $800 USD)")
            self.log(f"=======================================================")

            try:
                # 1. Monitoreo de Correo (Verificar si ya nos respondieron o contrataron)
                await self._step_email_check()

                if self.accepted_offer_detected:
                    self.log("🎉 ¡ALERTA MÁXIMA! Se ha detectado una oferta o aceptación formal en tu correo. Felicitaciones.")
                    self.is_running = False
                    break

                # 2. Rastreo Multi-Plataforma Remoto
                new_jobs_count = await self._step_multi_platform_search()

                # 3. Auto-Encolado y Postulación
                if self.auto_apply_enabled:
                    await self._step_auto_enqueue_and_apply()

            except asyncio.CancelledError:
                self.log("ℹ️ Ciclo continuo cancelado por el usuario.")
                break
            except Exception as loop_err:
                self.log(f"❌ Excepción en ciclo #{self.cycle_count}: {loop_err}")

            # 4. Programar siguiente ciclo con jitter natural
            if self.is_running:
                jitter = random.randint(-60, 120)
                sleep_seconds = max((self.interval_minutes * 60) + jitter, 180)
                self.next_run_time = datetime.datetime.now() + datetime.timedelta(seconds=sleep_seconds)
                mins = round(sleep_seconds / 60, 1)
                self.log(f"⏳ Ciclo #{self.cycle_count} finalizado. Próxima exploración automática en {mins} minutos.")

                # Espera en pequeños intervalos para permitir cancelación inmediata
                step_interval = 2
                elapsed = 0
                while elapsed < sleep_seconds and self.is_running:
                    await asyncio.sleep(step_interval)
                    elapsed += step_interval

    async def _step_email_check(self):
        """Escanea la bandeja de Gmail para detectar propuestas y avances."""
        self.log("📬 [Paso 1/3] Verificando bandeja de correo en busca de respuestas y ofertas...")
        bm = BrowserManager(headless=True)
        db = SessionLocal()
        try:
            scanner = EmailScanner(bm)
            agent = EmailAgent(scanner, self.llm)
            records = await agent.process_inbox(db)
            if records:
                for r in records:
                    subj = r.get("subject", "").lower()
                    is_newsletter = any(nl in subj for nl in ["ofertas de empleo", "alertas de empleo", "nuevas ofertas", "boletín", "aviso de empleo", "vacantes recomendadas"])
                    if not is_newsletter:
                        if any(k in subj for k in ["carta de oferta", "propuesta económica", "propuesta economica", "propuesta formal", "bienvenido al equipo", "felicitaciones por tu ingreso", "contrato de trabajo"]):
                            self.accepted_offer_detected = True
                            self.log(f"🌟 CONTRATACIÓN O PROPUESTA FORMAL DETECTADA: '{r.get('subject')}' de {r.get('sender')}")
                        elif any(k in subj for k in ["entrevista", "interview", "prueba técnica", "prueba tecnica", "agendar", "coordinar reunión"]):
                            self.log(f"📅 INVITACIÓN A ENTREVISTA DETECTADA: '{r.get('subject')}' de {r.get('sender')}")
            else:
                self.log("ℹ️ Sin novedades críticas en la bandeja de entrada.")
        except Exception as e:
            self.log(f"⚠️ Nota en verificación de correo: {e}")
        finally:
            await bm.close()
            db.close()

    async def _step_multi_platform_search(self) -> int:
        """Busca vacantes 100% remotas en todas las plataformas soportadas."""
        self.log("🔎 [Paso 2/3] Explorando ofertas en Torre.co, Get on Board, RemoteTech (WWR/Himalayas), Laborum, Computrabajo, Bumeran y LinkedIn...")
        bm = BrowserManager(headless=True)
        db = SessionLocal()
        total_new = 0

        try:
            from adapters.torre import TorreAdapter
            adapters = [
                TorreAdapter(bm, self.llm),
                GetOnBoardAdapter(bm, self.llm),
                RemoteTechAdapter(bm, self.llm),
                LaborumAdapter(bm, self.llm),
                BumeranAdapter(bm, self.llm),
                ComputrabajoAdapter(bm, self.llm),
                LinkedInAdapter(bm, self.llm)
            ]

            # Consultas adaptadas dinámicamente a los roles autorizados por el usuario
            active_queries = self.llm.get_active_search_queries()
            if not active_queries:
                self.log("⚠️ No hay puestos laborales activos en tus preferencias. Usando consultas de Sistemas base.")
                active_queries = ["junior sistemas", "trainee sistemas", "qa junior"]

            for adapter in adapters:
                if not self.is_running:
                    break
                p_name = adapter.platform_name.upper()
                q_selected = random.choice(active_queries)
                self.log(f"🌐 Escaneando {p_name} con filtro 100% Remoto ('{q_selected}')...")

                try:
                    found_jobs = await adapter.search_jobs(query=q_selected, remote_only=True, max_results=6)
                    for j in found_jobs:
                        # Verificar duplicados
                        exists = db.query(Job).filter(
                            Job.platform == j["platform"],
                            Job.external_id == j["external_id"]
                        ).first()

                        if not exists:
                            req_fit = j.get("requirements")
                            if not req_fit:
                                req_fit = self.llm.analyze_requirements_fit(
                                    title=j["title"],
                                    description=j.get("description", ""),
                                    company=j["company"],
                                    location=j.get("location", "")
                                )

                            # Descartar estrictamente si no es remota o no recomendada
                            if not req_fit.get("is_recommended", True) or req_fit.get("score", 0) < 0.60:
                                continue

                            import json
                            new_job = Job(
                                platform=j["platform"],
                                external_id=j["external_id"],
                                title=j["title"],
                                company=j["company"],
                                location=j["location"],
                                modality="remote",
                                url=j["url"],
                                salary_snippet=j.get("salary_snippet", ""),
                                description=j.get("description", ""),
                                match_score=req_fit.get("score", 0.8),
                                match_reason=req_fit.get("reason", ""),
                                requirements_json=json.dumps(req_fit, ensure_ascii=False),
                                requirements_fulfilled=json.dumps(req_fit.get("cumplimos", []), ensure_ascii=False),
                                requirements_missing=json.dumps(req_fit.get("no_cumplimos", []), ensure_ascii=False),
                                strategy_notes=req_fit.get("estrategia", ""),
                                is_recommended=True,
                                status="discovered"
                            )
                            db.add(new_job)
                            db.commit()
                            total_new += 1
                            self.log(f"✨ Nueva oportunidad remota ({int(new_job.match_score*100)}%): '{new_job.title}' en {new_job.company} [{p_name}]")

                except Exception as p_err:
                    self.log(f"⚠️ Error explorando {p_name}: {p_err}")

        finally:
            await bm.close()
            db.close()

        self.log(f"🎯 Total de nuevas vacantes 100% remotas registradas en este ciclo: {total_new}")
        return total_new

    async def _step_auto_enqueue_and_apply(self):
        """Encola vacantes de alta afinidad (>= 85%) para postulación automática."""
        self.log("⚡ [Paso 3/3] Evaluando vacantes para postulación automática en cola...")
        db = SessionLocal()
        try:
            # Buscar hasta 3 vacantes descubiertas con match_score >= 0.80
            candidates = db.query(Job).filter(
                Job.status == "discovered",
                Job.is_recommended == True,
                Job.match_score >= 0.80
            ).order_by(Job.match_score.desc(), Job.created_at.desc()).limit(3).all()

            # Filtrar candidatos que pertenezcan a roles autorizados por el usuario
            valid_candidates = []
            for c in candidates:
                role_match = self.llm.match_job_to_role(c.title, c.description or "")
                if role_match.get("is_allowed", True):
                    valid_candidates.append(c)
                else:
                    self.log(f"⏸️ Omitiendo vacante '{c.title}': Puesto '{role_match.get('role_name')}' pausado en preferencias.")

            if not valid_candidates:
                self.log("ℹ️ No hay vacantes pendientes para tus puestos de trabajo activos en este momento.")
                return

            self.log(f"🚀 Encolando {len(valid_candidates)} vacantes remotas de puestos autorizados para postulación...")
            for c in valid_candidates:
                await self.job_queue.enqueue(c.id)
                await asyncio.sleep(1)

        except Exception as e:
            self.log(f"⚠️ Error encolando postulaciones automáticas: {e}")
        finally:
            db.close()
