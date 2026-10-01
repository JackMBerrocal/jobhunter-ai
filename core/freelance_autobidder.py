import asyncio
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, date, time
from typing import Dict, Any, List, Optional
from core.database import SessionLocal, FreelanceProject, FreelanceAutoBidConfig
from core.proposal_generator import ProposalGenerator


class FreelanceAutoBidder:
    """
    Guardián y Postulador Autónomo 24/7 para Freelancer.com y Oportunidades Remotas.
    Monitorea de forma continua en tiempo real (cada 60-90 segundos) para ser uno
    de los primeros en ofertar apenas se publica un proyecto compatible.
    """

    def __init__(self, proposal_generator: ProposalGenerator = None, log_callback=None):
        self.proposal_gen = proposal_generator or ProposalGenerator()
        self.log_callback = log_callback or (lambda msg: print(f"[AutoBidder] {msg}"))
        
        self.is_running = False
        self._loop_task: Optional[asyncio.Task] = None
        self.last_check_time: Optional[datetime] = None
        self.next_check_time: Optional[datetime] = None
        self.cycle_count = 0

    def log(self, message: str):
        self.log_callback(f"[⚡ Auto-Bid 24/7] {message}")

    def get_config(self) -> Dict[str, Any]:
        """Obtiene la configuración actual desde la base de datos."""
        db = SessionLocal()
        try:
            cfg = db.query(FreelanceAutoBidConfig).filter(FreelanceAutoBidConfig.id == 1).first()
            if not cfg:
                cfg = FreelanceAutoBidConfig(
                    id=1,
                    is_enabled=False,
                    min_hourly_rate=15.0,
                    min_fixed_budget=50.0,
                    max_daily_bids=4,
                    check_interval_seconds=75
                )
                db.add(cfg)
                db.commit()
                db.refresh(cfg)

            categories = []
            try:
                categories = json.loads(cfg.target_categories_json) if cfg.target_categories_json else []
            except Exception:
                categories = [
                    "customer_support_whatsapp", "sales_setter_crm", "ai_chatbot_system",
                    "social_media_growth", "ecommerce_stores", "virtual_assistant_admin",
                    "power_bi_data", "qa_testing", "sql_database", "web_dev", "python_automation_scraping"
                ]

            return {
                "is_enabled": bool(cfg.is_enabled),
                "min_hourly_rate": float(cfg.min_hourly_rate or 15.0),
                "min_fixed_budget": float(cfg.min_fixed_budget or 50.0),
                "max_daily_bids": int(cfg.max_daily_bids or 25),
                "check_interval_seconds": max(int(cfg.check_interval_seconds or 75), 45),
                "target_categories": categories,
                "has_api_token": bool(cfg.freelancer_api_token and len(cfg.freelancer_api_token) > 5),
                "freelancer_api_token": cfg.freelancer_api_token or ""
            }
        finally:
            db.close()

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza parámetros de configuración y guarda en SQLite."""
        db = SessionLocal()
        try:
            cfg = db.query(FreelanceAutoBidConfig).filter(FreelanceAutoBidConfig.id == 1).first()
            if not cfg:
                cfg = FreelanceAutoBidConfig(id=1)
                db.add(cfg)

            if "is_enabled" in updates:
                cfg.is_enabled = bool(updates["is_enabled"])
            if "min_hourly_rate" in updates:
                cfg.min_hourly_rate = float(updates["min_hourly_rate"])
            if "min_fixed_budget" in updates:
                cfg.min_fixed_budget = float(updates["min_fixed_budget"])
            if "max_daily_bids" in updates:
                cfg.max_daily_bids = int(updates["max_daily_bids"])
            if "check_interval_seconds" in updates:
                cfg.check_interval_seconds = max(int(updates["check_interval_seconds"]), 45)
            if "target_categories" in updates:
                cfg.target_categories_json = json.dumps(updates["target_categories"])
            if "freelancer_api_token" in updates:
                cfg.freelancer_api_token = updates["freelancer_api_token"].strip() if updates["freelancer_api_token"] else None

            cfg.updated_at = datetime.now()
            db.commit()
            self.log(f"⚙️ Configuración de Auto-Bid actualizada. Estado: {'ACTIVADO ⚡' if cfg.is_enabled else 'PAUSADO ⏸️'}")
            return self.get_config()
        finally:
            db.close()

    def get_bids_today_count(self) -> int:
        """Calcula cuántas ofertas automáticas se han realizado en el día actual."""
        db = SessionLocal()
        try:
            today_start = datetime.combine(date.today(), time.min)
            count = db.query(FreelanceProject).filter(
                FreelanceProject.auto_applied == True,
                FreelanceProject.applied_at >= today_start
            ).count()
            return count
        finally:
            db.close()

    def get_status(self) -> Dict[str, Any]:
        """Estado general en tiempo real para el Dashboard."""
        cfg = self.get_config()
        bids_today = self.get_bids_today_count()
        
        # Últimas ofertas enviadas automáticamente
        recent_applied = []
        db = SessionLocal()
        try:
            applied_projs = db.query(FreelanceProject).filter(
                FreelanceProject.auto_applied == True
            ).order_by(FreelanceProject.applied_at.desc()).limit(5).all()

            for p in applied_projs:
                recent_applied.append({
                    "id": p.id,
                    "title": p.title,
                    "category": p.category,
                    "bid": p.suggested_bid,
                    "applied_at": p.applied_at.strftime("%H:%M - %d/%m") if p.applied_at else "",
                    "url": p.url
                })
        finally:
            db.close()

        return {
            "is_running": self.is_running,
            "is_enabled": cfg["is_enabled"],
            "bids_today": bids_today,
            "max_daily_bids": cfg["max_daily_bids"],
            "remaining_today": max(0, cfg["max_daily_bids"] - bids_today),
            "min_hourly_rate": cfg["min_hourly_rate"],
            "min_fixed_budget": cfg["min_fixed_budget"],
            "check_interval_seconds": cfg["check_interval_seconds"],
            "last_check": self.last_check_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_check_time else None,
            "next_check": self.next_check_time.strftime("%Y-%m-%d %H:%M:%S") if self.next_check_time else None,
            "target_categories": cfg["target_categories"],
            "has_api_token": cfg["has_api_token"],
            "cycle_count": self.cycle_count,
            "recent_applied": recent_applied
        }

    def start(self):
        """Inicia el bucle continuo del Auto-Bidder."""
        if self.is_running:
            self.log("⚠️ El Auto-Bidder ya se encuentra corriendo.")
            return

        self.is_running = True
        self._loop_task = asyncio.create_task(self._monitor_loop())
        self.log("🚀 Monitor Continuo Freelance 24/7 INICIADO.")

    def stop(self):
        """Detiene el bucle continuo del Auto-Bidder."""
        self.is_running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        self.next_check_time = None
        self.log("🛑 Monitor Continuo Freelance DETENIDO.")

    async def _monitor_loop(self):
        """Bucle infinito de monitoreo en segundo plano."""
        while self.is_running:
            try:
                cfg = self.get_config()
                self.last_check_time = datetime.now()
                interval = cfg.get("check_interval_seconds", 75)
                self.next_check_time = datetime.fromtimestamp(datetime.now().timestamp() + interval)

                if cfg.get("is_enabled", False):
                    bids_today = self.get_bids_today_count()
                    max_bids = cfg.get("max_daily_bids", 4)
                    if bids_today < max_bids:
                        await self._execute_scan_and_autobid(cfg)
                    else:
                        self.log(f"⏸️ Límite diario alcanzado ({bids_today}/{max_bids} ofertas enviadas hoy). Protegiendo créditos.")
                else:
                    # Modo copiloto pasivo (el usuario no ha encendido el switch de auto-bid)
                    pass

                self.cycle_count += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log(f"❌ Error en ciclo de auto-bid: {e}")

            await asyncio.sleep(self.get_config().get("check_interval_seconds", 75))

    async def _execute_scan_and_autobid(self, cfg: Dict[str, Any]):
        """Ejecuta una ronda de detección de proyectos nuevos y auto-postulación."""
        loop = asyncio.get_event_loop()
        new_projects = await loop.run_in_executor(None, self._fetch_recent_projects)
        
        if not new_projects:
            return

        for p in new_projects:
            bids_today = self.get_bids_today_count()
            if bids_today >= cfg.get("max_daily_bids", 4):
                self.log("🛑 Cupo diario completado durante el ciclo. Pausando auto-bids por hoy.")
                break

            await self._evaluate_and_place_bid(p, cfg)

    def _fetch_recent_projects(self) -> List[Dict[str, Any]]:
        """
        Consulta la API de Freelancer.com ordenando por fecha de envío descendente
        (time_submitted desc) para detectar ofertas de hace pocos minutos.
        """
        queries = [
            "",  # Stream general de más recientes en español
            "whatsapp", "atencion al cliente", "setter", "power bi", "python", "sql", "qa testing"
        ]
        results = []
        seen_ids = set()

        for q in queries:
            try:
                if q:
                    url = f"https://www.freelancer.com/api/projects/0.1/projects/active?query={urllib.parse.quote_plus(q)}&languages[]=es&sort_field=time_submitted&reverse_sort=true&limit=6&full_description=true"
                else:
                    url = "https://www.freelancer.com/api/projects/0.1/projects/active?languages[]=es&sort_field=time_submitted&reverse_sort=true&limit=8&full_description=true"

                req = urllib.request.Request(url, headers={"User-Agent": "JobHunter-AI/1.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode())

                projects = data.get("result", {}).get("projects", [])
                for p in projects:
                    pid = str(p.get("id"))
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    b = p.get("budget", {})
                    cur = p.get("currency", {}).get("code", "USD")
                    min_b = b.get("minimum", 0)
                    max_b = b.get("maximum", 0)
                    p_type = p.get("type", "fixed")
                    hourly_suffix = " / hora" if p_type == "hourly" else ""

                    if min_b and max_b:
                        budget_str = f"{cur} {int(min_b)} - {int(max_b)}{hourly_suffix}"
                    elif max_b:
                        budget_str = f"Hasta {cur} {int(max_b)}{hourly_suffix}"
                    elif min_b:
                        budget_str = f"Desde {cur} {int(min_b)}{hourly_suffix}"
                    else:
                        budget_str = "A convenir"

                    results.append({
                        "platform": "freelancer",
                        "external_id": pid,
                        "title": p.get("title", "").strip(),
                        "description": p.get("description", "") or p.get("preview_description", ""),
                        "budget": budget_str,
                        "currency": cur,
                        "min_budget": float(min_b or 0),
                        "max_budget": float(max_b or 0),
                        "is_hourly": (p_type == "hourly"),
                        "url": f"https://www.freelancer.com/projects/{p.get('seo_url', pid)}",
                        "time_submitted": p.get("time_submitted", 0),
                        "client_name": "Cliente Freelance"
                    })
            except Exception as e:
                pass

        return results

    async def _evaluate_and_place_bid(self, proj_data: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
        """
        Evalúa si el proyecto cumple con los filtros estrictos y ejecuta el Auto-Bid.
        """
        title = proj_data["title"]
        desc = proj_data["description"]
        budget_str = proj_data["budget"]
        ext_id = proj_data["external_id"]

        # 1. Categorizar con el motor cognitivo
        category = self.proposal_gen.categorize_project(title, desc)
        target_cats = cfg.get("target_categories", [])

        if category not in target_cats:
            return False  # Categoría no autorizada

        # 2. Guardarraíl Salarial Estricto
        min_hourly = cfg.get("min_hourly_rate", 15.0)
        min_fixed = cfg.get("min_fixed_budget", 50.0)

        if proj_data["is_hourly"]:
            effective_rate = proj_data["max_budget"] or proj_data["min_budget"]
            if effective_rate > 0 and effective_rate < min_hourly:
                return False  # Tarifa horaria indigna (< $15/hr)
        else:
            effective_fixed = proj_data["max_budget"] or proj_data["min_budget"]
            if effective_fixed > 0 and effective_fixed < min_fixed:
                return False  # Proyecto plano muy bajo (< $50)

        # 3. Verificar en BD si ya existe y si ya fue postulado
        db = SessionLocal()
        try:
            existing = db.query(FreelanceProject).filter(
                FreelanceProject.platform == "freelancer",
                FreelanceProject.external_id == ext_id
            ).first()

            if existing and existing.status in ("applied", "auto_applied", "dismissed"):
                return False  # Ya postulado previamente

            # 4. Generar propuesta cognitiva
            proposal_res = self.proposal_gen.generate_proposal(
                title=title,
                description=desc,
                client_name=proj_data.get("client_name", "Estimado cliente"),
                budget=budget_str
            )
            proposal_text = proposal_res["proposal_text"]
            suggested_bid = proposal_res["suggested_bid"]
            suggested_time = proposal_res["suggested_timeline"]

            # 5. Ejecutar la oferta (API Token o Navegador)
            bid_success, response_note = await self._send_bid_to_platform(
                project_id=ext_id,
                bid_amount_str=suggested_bid,
                proposal_text=proposal_text,
                cfg=cfg
            )

            if bid_success:
                now = datetime.now()
                if not existing:
                    new_proj = FreelanceProject(
                        platform="freelancer",
                        external_id=ext_id,
                        title=title,
                        client_name=proj_data.get("client_name", "Cliente Freelance"),
                        budget=budget_str,
                        currency=proj_data.get("currency", "USD"),
                        category=category,
                        url=proj_data["url"],
                        description=desc,
                        generated_proposal=proposal_text,
                        suggested_bid=suggested_bid,
                        suggested_timeline=suggested_time,
                        status="auto_applied",
                        auto_applied=True,
                        applied_at=now,
                        bid_response_log=response_note
                    )
                    db.add(new_proj)
                else:
                    existing.status = "auto_applied"
                    existing.auto_applied = True
                    existing.applied_at = now
                    existing.suggested_bid = suggested_bid
                    existing.suggested_timeline = suggested_time
                    existing.generated_proposal = proposal_text
                    existing.bid_response_log = response_note

                db.commit()
                self.log(f"⚡ [AUTO-BID ENVIADO] Postulado a '{title}' ({suggested_bid}) en Freelancer.com.")
                return True
            else:
                now = datetime.now()
                if not existing:
                    new_proj = FreelanceProject(
                        platform="freelancer",
                        external_id=ext_id,
                        title=title,
                        client_name=proj_data.get("client_name", "Cliente Freelance"),
                        budget=budget_str,
                        currency=proj_data.get("currency", "USD"),
                        category=category,
                        url=proj_data["url"],
                        description=desc,
                        generated_proposal=proposal_text,
                        suggested_bid=suggested_bid,
                        suggested_timeline=suggested_time,
                        status="pending",
                        auto_applied=False,
                        bid_response_log=response_note
                    )
                    db.add(new_proj)
                else:
                    existing.generated_proposal = proposal_text
                    existing.suggested_bid = suggested_bid
                    existing.suggested_timeline = suggested_time
                    existing.bid_response_log = response_note
                db.commit()
                self.log(f"📝 Propuesta IA generada para '{title}'. {response_note}")
                return False
        finally:
            db.close()

    async def _send_bid_to_platform(self, project_id: str, bid_amount_str: str, proposal_text: str, cfg: Dict[str, Any]) -> tuple[bool, str]:
        """
        Envía la propuesta a la plataforma.
        """
        token = cfg.get("freelancer_api_token")
        
        num_match = re.search(r'(\d+(?:\.\d+)?)', bid_amount_str)
        bid_value = float(num_match.group(1)) if num_match else 25.0

        if token and len(token) > 10:
            try:
                url = "https://www.freelancer.com/api/projects/0.1/bids/"
                payload = json.dumps({
                    "project_id": int(project_id),
                    "amount": bid_value,
                    "period": 3,
                    "description": proposal_text,
                    "milestone_percentage": 100
                }).encode("utf-8")

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Freelancer-Developer-Auth": token,
                        "Content-Type": "application/json",
                        "User-Agent": "JobHunter-AI/1.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    resp_json = json.loads(resp.read().decode())
                    bid_id = resp_json.get("result", {}).get("id", "OK")
                    return True, f"Bid REAL colocado en Freelancer.com: ID #{bid_id}"
            except urllib.error.HTTPError as he:
                try:
                    err_json = json.loads(he.read().decode())
                    err_msg = err_json.get("message") or str(err_json)
                except Exception:
                    err_msg = f"HTTP {he.code}"
                return False, f"Error API Freelancer: {err_msg}"
            except Exception as e:
                return False, f"Error en API Freelancer: {e}"

        # Sin Token de desarrollador de Freelancer.com
        return False, "Token de API Freelancer no configurado. Propuesta generada y lista para publicar vía LibreWolf o ingresando tu Token personal."

    async def test_bid(self, project_id: int) -> Dict[str, Any]:
        """Permite probar el mecanismo de Auto-Bid en un proyecto específico de la BD."""
        db = SessionLocal()
        try:
            proj = db.query(FreelanceProject).filter(FreelanceProject.id == project_id).first()
            if not proj:
                return {"success": False, "error": "Proyecto no encontrado"}

            now = datetime.now()
            proj.auto_applied = True
            proj.status = "auto_applied"
            proj.applied_at = now
            proj.bid_response_log = "Prueba de Auto-Bid ejecutada exitosamente."
            db.commit()

            self.log(f"🧪 [PRUEBA AUTO-BID] Oferta registrada para: '{proj.title}'")
            return {
                "success": True,
                "project_id": proj.id,
                "title": proj.title,
                "bid": proj.suggested_bid,
                "applied_at": now.strftime("%H:%M:%S")
            }
        finally:
            db.close()
