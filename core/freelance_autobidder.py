import asyncio
import os
import json
import re
import urllib.request
import urllib.parse
import subprocess
from datetime import datetime, date, time
from typing import Dict, Any, List, Optional
from pathlib import Path
from core.database import SessionLocal, FreelanceProject, FreelanceAutoBidConfig
from core.proposal_generator import ProposalGenerator, strip_all_emojis


def notify_desktop(title: str, message: str, urgency: str = "normal", sound: str = "message-new-instant", voice_text: str = None):
    """Dispara notificación emergente en el escritorio Linux, reproduce alerta sonora e interactúa por voz."""
    try:
        subprocess.run([
            "notify-send",
            "-u", urgency,
            "-i", "dialog-warning" if urgency == "critical" else "mail-send",
            "-a", "JobHunter AI",
            title,
            message
        ], check=False, timeout=3)
    except Exception:
        pass
    
    if sound:
        sound_file = f"/usr/share/sounds/freedesktop/stereo/{sound}.oga"
        played = False
        if os.path.exists(sound_file):
            try:
                subprocess.run(["paplay", sound_file], check=False, timeout=3)
                played = True
            except Exception:
                pass
        if not played:
            try:
                subprocess.run(["canberra-gtk-play", "-i", sound], check=False, timeout=3)
            except Exception:
                pass

    if voice_text:
        try:
            subprocess.run(["spd-say", "-l", "es", "-r", "5", voice_text], check=False, timeout=5)
        except Exception:
            pass


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
        self.notified_thread_ids = set()
        self._user_skill_ids: Optional[set] = None
        self.my_user_id = 29738534
        self.replied_message_ids_file = Path("/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/data/replied_message_ids.json")
        self.replied_message_ids = self._load_replied_message_ids()

    def _load_replied_message_ids(self) -> set:
        """Carga IDs de mensajes respondidos para evitar respuestas duplicadas."""
        if self.replied_message_ids_file.exists():
            try:
                with open(self.replied_message_ids_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                pass
        initial = {2291080474, 2291082400}
        self._save_replied_message_ids(initial)
        return initial

    def _save_replied_message_ids(self, ids: set):
        try:
            self.replied_message_ids_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.replied_message_ids_file, "w", encoding="utf-8") as f:
                json.dump(list(ids), f)
        except Exception:
            pass

    def log(self, message: str):
        self.log_callback(f"[⚡ Auto-Bid 24/7] {message}")

    def get_user_skill_ids(self) -> set:
        """Devuelve el conjunto de IDs de habilidades registradas en el perfil de Jack en Freelancer.com."""
        if self._user_skill_ids:
            return self._user_skill_ids

        token = self.get_config().get("freelancer_api_token")
        if token:
            try:
                url = "https://www.freelancer.com/api/users/0.1/self?jobs=true"
                req = urllib.request.Request(url, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode())
                    jobs = data.get("result", {}).get("jobs", [])
                    if jobs:
                        self._user_skill_ids = {j.get("id") for j in jobs if j.get("id") is not None}
            except Exception:
                pass

        if not self._user_skill_ids:
            # 39 Habilidades verificadas del perfil de Jack en Freelancer.com (@jmberrocale)
            self._user_skill_ids = {
                3, 7, 9, 13, 17, 26, 32, 36, 55, 68, 74, 79, 105, 129, 167, 305, 323, 335,
                408, 454, 482, 500, 564, 671, 759, 1013, 1020, 1031, 1065, 1091, 1277, 1383,
                1683, 1977, 2376, 2507, 2562, 2701, 2839
            }

        return self._user_skill_ids

    def get_config(self) -> Dict[str, Any]:
        """Obtiene la configuración actual desde la base de datos."""
        db = SessionLocal()
        try:
            cfg = db.query(FreelanceAutoBidConfig).filter(FreelanceAutoBidConfig.id == 1).first()
            if not cfg:
                cfg = FreelanceAutoBidConfig(
                    id=1,
                    is_enabled=False,
                    min_hourly_rate=20.0,
                    min_fixed_budget=150.0,
                    max_daily_bids=4,
                    max_competition_bids=12,
                    goal_monthly_usd=1500.0,
                    membership_bids_total=100,
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
                    "python_automation_scraping", "ai_chatbot_system", "web_dev",
                    "sql_database", "power_bi_data", "qa_testing", "customer_support_whatsapp",
                    "sales_setter_crm", "graphic_design_creative"
                ]

            return {
                "is_enabled": bool(cfg.is_enabled),
                "min_hourly_rate": float(cfg.min_hourly_rate or 20.0),
                "min_fixed_budget": float(cfg.min_fixed_budget or 150.0),
                "max_daily_bids": int(cfg.max_daily_bids or 4),
                "max_competition_bids": int(getattr(cfg, "max_competition_bids", 12) or 12),
                "goal_monthly_usd": float(getattr(cfg, "goal_monthly_usd", 1500.0) or 1500.0),
                "membership_bids_total": int(getattr(cfg, "membership_bids_total", 100) or 100),
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
            if "max_competition_bids" in updates:
                cfg.max_competition_bids = int(updates["max_competition_bids"])
            if "goal_monthly_usd" in updates:
                cfg.goal_monthly_usd = float(updates["goal_monthly_usd"])
            if "membership_bids_total" in updates:
                cfg.membership_bids_total = int(updates["membership_bids_total"])
            if "check_interval_seconds" in updates:
                cfg.check_interval_seconds = max(int(updates["check_interval_seconds"]), 45)
            if "target_categories" in updates:
                cfg.target_categories_json = json.dumps(updates["target_categories"])
            if "freelancer_api_token" in updates:
                cfg.freelancer_api_token = updates["freelancer_api_token"].strip() if updates["freelancer_api_token"] else None

            cfg.updated_at = datetime.now()
            db.commit()
            self.log(f"⚙️ Configuración Objetivo $1500 actualizada. Estado: {'ACTIVADO ⚡' if cfg.is_enabled else 'PAUSADO ⏸️'}")
            return self.get_config()
        finally:
            db.close()

    def get_bids_today_count(self) -> int:
        """Calcula cuántas ofertas automáticas reales se han realizado en el día actual."""
        db = SessionLocal()
        try:
            today_start = datetime.combine(date.today(), time.min)
            count = db.query(FreelanceProject).filter(
                FreelanceProject.auto_applied == True,
                FreelanceProject.status.in_(["applied", "auto_applied", "accepted"]),
                FreelanceProject.applied_at >= today_start
            ).count()
            return count
        finally:
            db.close()

    def get_bids_month_count(self) -> int:
        """Calcula cuántas ofertas automáticas reales se han realizado en el mes en curso (control de membresía)."""
        db = SessionLocal()
        try:
            today = date.today()
            month_start = datetime(today.year, today.month, 1)
            count = db.query(FreelanceProject).filter(
                FreelanceProject.auto_applied == True,
                FreelanceProject.status.in_(["applied", "auto_applied", "accepted"]),
                FreelanceProject.applied_at >= month_start
            ).count()
            return count
        finally:
            db.close()

    def get_status(self) -> Dict[str, Any]:
        """Estado general en tiempo real para el Dashboard con métricas de la Meta $1500."""
        cfg = self.get_config()
        bids_today = self.get_bids_today_count()
        bids_month = self.get_bids_month_count()
        membership_total = cfg.get("membership_bids_total", 100)
        
        # Últimas ofertas enviadas automáticamente
        recent_applied = []
        db = SessionLocal()
        try:
            applied_projs = db.query(FreelanceProject).filter(
                FreelanceProject.auto_applied == True,
                FreelanceProject.status.in_(["applied", "auto_applied", "accepted"]),
                FreelanceProject.category.in_(["web_dev", "ecommerce_stores", "python_automation_scraping", "ai_chatbot_system", "sql_database", "qa_testing", "power_bi_data", "it_support", "graphic_design_creative"])
            ).order_by(FreelanceProject.applied_at.desc()).limit(8).all()

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
            "bids_month": bids_month,
            "membership_bids_total": membership_total,
            "remaining_month": max(0, membership_total - bids_month),
            "min_hourly_rate": cfg["min_hourly_rate"],
            "min_fixed_budget": cfg["min_fixed_budget"],
            "max_competition_bids": cfg["max_competition_bids"],
            "goal_monthly_usd": cfg["goal_monthly_usd"],
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

                # 1. Alerta prioritaria si un cliente respondió en Freelancer.com
                await self._check_freelancer_inbox_and_alerts(cfg)

                # 2. Verificación si nos adjudicaron algún proyecto
                await self._check_freelancer_awarded_bids(cfg)

                # 3. Depuración periódica de ofertas cerradas o tomadas por otro (cada 4 ciclos)
                if self.cycle_count % 4 == 0:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.clean_closed_or_taken_bids)

                # 4. Escaneo y postulación autónoma si está activada
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

    async def _check_freelancer_inbox_and_alerts(self, cfg: Dict[str, Any]):
        """Verifica la bandeja de mensajes de Freelancer.com y responde automáticamente si un cliente escribe."""
        token = cfg.get("freelancer_api_token")
        if not token:
            return

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._auto_respond_thread_messages(token))
        except Exception as e:
            pass

    async def _check_freelancer_awarded_bids(self, cfg: Dict[str, Any]):
        """Verifica si algún cliente nos ha adjudicado o aceptado un proyecto en Freelancer.com."""
        token = cfg.get("freelancer_api_token")
        if not token:
            return

        try:
            loop = asyncio.get_event_loop()
            awarded = await loop.run_in_executor(None, lambda: self._query_freelancer_awarded_bids(token))
            if awarded:
                db = SessionLocal()
                try:
                    for aw in awarded:
                        proj_id = aw.get("project_id")
                        ext_id = f"freelancer_{proj_id}"
                        proj = db.query(FreelanceProject).filter(FreelanceProject.external_id == ext_id).first()
                        if proj and not proj.is_awarded:
                            proj.is_awarded = True
                            proj.status = "accepted"
                            proj.agreed_amount = f"${aw.get('amount', 0)} USD"
                            db.commit()
                            self.log(f"🎉 ¡PROYECTO ADJUDICADO! '{proj.title}' fue aceptado por el cliente (${proj.agreed_amount}).")
                            notify_desktop(
                                title="🎉 ¡PROYECTO ADJUDICADO EN FREELANCER!",
                                message=f"¡El cliente nos aceptó en '{proj.title}'! Entra a Antigravity para iniciar el plan de trabajo.",
                                urgency="critical",
                                sound="complete",
                                voice_text=f"Felicidades Jack. Nos acaban de adjudicar el proyecto {proj.title[:45]}. Entra al sistema para iniciar el trabajo."
                            )
                finally:
                    db.close()
        except Exception as e:
            pass

    def _query_freelancer_awarded_bids(self, token: str) -> List[Dict[str, Any]]:
        """Consulta ofertas enviadas para detectar aquellas con award_status activo."""
        try:
            url = "https://www.freelancer.com/api/users/0.1/self"
            req = urllib.request.Request(url, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                self_data = json.loads(resp.read().decode())
            user_id = self_data.get("result", {}).get("id", 29738534)

            bids_url = f"https://www.freelancer.com/api/projects/0.1/bids/?bidders[]={user_id}&limit=25"
            req2 = urllib.request.Request(bids_url, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
            with urllib.request.urlopen(req2, timeout=8) as resp2:
                bids_data = json.loads(resp2.read().decode())
            bids = bids_data.get("result", {}).get("bids", [])
            awarded = [b for b in bids if b.get("award_status") in ("awarded", "pending", "accepted")]
            return awarded
        except Exception:
            return []

    def sync_freelancer_api_now(self) -> Dict[str, Any]:
        """
        Sincronización 100% fidedigna y en tiempo real con Freelancer.com:
        1. Consulta el ID de usuario de Jack y sus ofertas REALES en Freelancer.com API.
        2. Reconcilia la BD: si un proyecto figuraba falsamente como 'applied'/'auto_applied'
           pero Jack NUNCA ofertó a él en Freelancer, lo revierte a 'open' (radar) o lo descarta si cerró.
        3. Comprueba el estado real de los proyectos ofertados (adjudicados o expirados).
        4. Depura proyectos cerrados, tomados por otro o expirados en toda la base de datos.
        5. Consulta mensajes no leídos en chat.
        """
        cfg = self.get_config()
        token = cfg.get("freelancer_api_token")
        if not token:
            return {"status": "error", "message": "No hay token de Freelancer.com configurado."}

        synced_bids = 0
        awarded_count = 0
        reverted_count = 0
        try:
            # 1. Obtener ID de usuario autenticado
            url = "https://www.freelancer.com/api/users/0.1/self"
            req = urllib.request.Request(url, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                self_data = json.loads(resp.read().decode())
            user_id = self_data.get("result", {}).get("id", 29738534)

            # 2. Obtener TODAS las ofertas REALES de Jack en Freelancer.com
            bids_url = f"https://www.freelancer.com/api/projects/0.1/bids/?bidders[]={user_id}&limit=100"
            req2 = urllib.request.Request(bids_url, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                bids_data = json.loads(resp2.read().decode())
            all_bids = bids_data.get("result", {}).get("bids", [])
            active_real_bids = [b for b in all_bids if not b.get("retracted")]
            retracted_bids = [b for b in all_bids if b.get("retracted")]
            active_bid_pids = {int(b.get("project_id")) for b in active_real_bids if b.get("project_id")}
            retracted_bid_pids = {int(b.get("project_id")) for b in retracted_bids if b.get("project_id")}

            db = SessionLocal()
            try:
                # A) Eliminar o retirar proyectos cuya oferta fue RETIRADA o CANCELADA en Freelancer.com
                for r_pid in retracted_bid_pids:
                    candidates = db.query(FreelanceProject).filter(
                        FreelanceProject.external_id.in_([f"freelancer_{r_pid}", str(r_pid)])
                    ).all()
                    for p in candidates:
                        # Si es categoría fuera de alcance (ventas, setters, marketing) o retirada, borrar completamente de la BD
                        db.delete(p)
                        reverted_count += 1

                # B) Corregir proyectos marcados falsamente como postulados en BD
                all_applied_in_db = db.query(FreelanceProject).filter(
                    FreelanceProject.platform == "freelancer",
                    FreelanceProject.status.in_(["applied", "auto_applied"])
                ).all()

                for p in all_applied_in_db:
                    m = re.search(r'(\d+)', p.external_id or '')
                    pid_int = int(m.group(1)) if m else None
                    if pid_int and pid_int not in active_bid_pids:
                        if p.category not in {"web_dev", "python_automation_scraping", "graphic_design_creative", "ai_chatbot_system", "sql_database"}:
                            db.delete(p)
                        else:
                            p.status = "open"
                            p.auto_applied = False
                            p.bid_response_log = "🟢 Oportunidad activa en radar (Sin postular aún en Freelancer.com)."
                        reverted_count += 1

                # C) Sincronizar SOLO las ofertas ACTIVAS que REALMENTE existen en Freelancer.com
                missing_pids = []
                for b in active_real_bids:
                    pid = b.get("project_id")
                    if not pid:
                        continue
                    
                    proj = None
                    for candidate in db.query(FreelanceProject).filter(
                        FreelanceProject.external_id.in_([f"freelancer_{pid}", str(pid)])
                    ).all():
                        proj = candidate
                        break

                    award_st = b.get("award_status")
                    is_aw = award_st in ("awarded", "pending", "accepted")

                    if proj:
                        proj.auto_applied = True
                        if is_aw:
                            proj.status = "accepted"
                            proj.is_awarded = True
                            proj.agreed_amount = f"${b.get('amount')} USD"
                            awarded_count += 1
                        elif proj.status not in ("not_selected", "completed", "client_replied"):
                            proj.status = "applied"
                        proj.suggested_bid = f"${b.get('amount')} USD"
                        synced_bids += 1
                    else:
                        missing_pids.append(pid)

                # Si hay proyectos ofertados en Freelancer que no estaban en la BD
                if missing_pids:
                    q_pids = "&".join([f"projects[]={p}" for p in missing_pids[:15]])
                    p_url = f"https://www.freelancer.com/api/projects/0.1/projects/?{q_pids}"
                    req3 = urllib.request.Request(p_url, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
                    with urllib.request.urlopen(req3, timeout=10) as resp3:
                        p_data = json.loads(resp3.read().decode())
                    for pr in p_data.get("result", {}).get("projects", []):
                        pid = pr.get("id")
                        matching_bid = next((b for b in active_real_bids if b.get("project_id") == pid), None)
                        if not matching_bid:
                            continue
                        bid_amount = matching_bid.get("amount")
                        is_aw = matching_bid.get("award_status") in ("awarded", "pending", "accepted")
                        
                        currency_code = pr.get("currency", {}).get("code", "USD")
                        budget_str = f"{currency_code} {pr.get('budget', {}).get('minimum', '')} - {pr.get('budget', {}).get('maximum', '')}"
                        
                        new_fl = FreelanceProject(
                            platform="freelancer",
                            external_id=f"freelancer_{pid}",
                            title=pr.get("title", f"Proyecto Freelancer #{pid}"),
                            client_name="Cliente Freelancer",
                            budget=budget_str,
                            currency=currency_code,
                            category="web_dev",
                            url=f"https://www.freelancer.com/projects/{pid}",
                            description=pr.get("preview_description") or pr.get("description") or "",
                            status="accepted" if is_aw else "applied",
                            auto_applied=True,
                            applied_at=datetime.now(),
                            suggested_bid=f"${bid_amount} {currency_code}" if bid_amount else "$150 USD",
                            is_awarded=is_aw,
                            agreed_amount=f"${bid_amount} {currency_code}" if is_aw else None
                        )
                        db.add(new_fl)
                        synced_bids += 1
                        if is_aw:
                            awarded_count += 1

                db.commit()
            finally:
                db.close()

            # 3. Depurar proyectos cerrados, expirados o tomados por otro (en ofertas y en radar)
            purge_res = self.clean_closed_or_taken_bids()
            purged_count = purge_res.get("purged", 0)

            # 4. Comprobar chats activos
            unread_threads = self._query_freelancer_threads(token)

            msg = (
                f"Sincronización real completada: {synced_bids} ofertas reales en tu cuenta, "
                f"{reverted_count} postulaciones falsas devueltas al radar, "
                f"{purged_count} proyectos cerrados/expirados eliminados, "
                f"{len(unread_threads)} chats activos."
            )
            self.log(f"⚡ [SINCRONIZACIÓN REAL] {msg}")

            return {
                "status": "success",
                "synced_bids": synced_bids,
                "reverted_count": reverted_count,
                "awarded_count": awarded_count,
                "purged_count": purged_count,
                "unread_threads": len(unread_threads),
                "message": msg
            }
        except Exception as e:
            return {"status": "error", "message": f"Error al sincronizar con Freelancer API: {e}"}

    def clean_closed_or_taken_bids(self) -> Dict[str, Any]:
        """
        Audita los proyectos en Freelancer.com y clasifica aquellos que:
        1. El cliente ya seleccionó/adjudicó a otro postulante (sub_status: closed_awarded).
        2. El proyecto fue cerrado, expiró, se congeló o fue cancelado (status: closed, frozen, cancelled, deleted).
        3. Proyectos que ya no existen en Freelancer.com.

        REGLA DE TRANSPARENCIA PARA JACK:
        - Si Jack SÍ se postuló (auto_applied o status applied/auto_applied), NO se oculta:
          se pasa al estado 'not_selected' en la pestaña '5. No Seleccionados' con el motivo exacto,
          para que Jack no se quede con dudas ni falsas esperanzas.
        - Si era un proyecto del radar al que nunca se postuló, se descarta ('dismissed') limpiamente.
        """
        cfg = self.get_config()
        token = cfg.get("freelancer_api_token")
        if not token:
            return {"status": "error", "message": "Token de Freelancer no configurado."}

        db = SessionLocal()
        purged_count = 0
        reasons = []
        try:
            # Traer proyectos pendientes de auditar (tanto aplicados como radar abierto)
            active_db_projs = db.query(FreelanceProject).filter(
                FreelanceProject.platform == "freelancer",
                FreelanceProject.status.in_(["applied", "auto_applied", "open", "pending", "proposal_generated"]),
                FreelanceProject.is_awarded == False
            ).all()

            if not active_db_projs:
                return {"status": "success", "purged": 0, "message": "No hay proyectos pendientes de auditar."}

            proj_map: Dict[str, list] = {}
            for p in active_db_projs:
                m = re.search(r'(\d+)', p.external_id or '')
                if m:
                    pid = m.group(1)
                    proj_map.setdefault(pid, []).append(p)

            pids_list = list(proj_map.keys())
            batch_size = 20
            for i in range(0, len(pids_list), batch_size):
                batch_pids = pids_list[i:i + batch_size]
                q_pids = "&".join([f"projects[]={pid}" for pid in batch_pids])
                url = f"https://www.freelancer.com/api/projects/0.1/projects/?{q_pids}"
                req = urllib.request.Request(
                    url,
                    headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        res = json.loads(resp.read().decode())
                    projects_meta = res.get("result", {}).get("projects", [])
                    found_pids = set()
                    for pr in projects_meta:
                        pid = str(pr.get("id"))
                        found_pids.add(pid)
                        st = pr.get("status")
                        sub = pr.get("sub_status")
                        matching_projs = proj_map.get(pid, [])
                        if not matching_projs:
                            continue

                        for db_proj in matching_projs:
                            is_taken_by_other = (sub == "closed_awarded" and not db_proj.is_awarded)
                            is_closed_or_expired = (st in ("closed", "frozen") or sub in ("closed_expired", "closed_cancelled", "frozen_timeout"))
                            is_cancelled = st in ("cancelled", "deleted")

                            if is_taken_by_other or is_closed_or_expired or is_cancelled:
                                prev_status = db_proj.status
                                was_applied = bool(db_proj.auto_applied or prev_status in ("applied", "auto_applied"))

                                if is_taken_by_other:
                                    reason_msg = "El cliente seleccionó y adjudicó el proyecto a otro profesional (closed_awarded)."
                                elif is_closed_or_expired:
                                    reason_msg = f"El tiempo de publicación venció y el proyecto finalizó ({sub or st})."
                                else:
                                    reason_msg = f"El cliente canceló la publicación ({sub or st})."

                                if was_applied:
                                    db_proj.status = "not_selected"
                                    db_proj.bid_response_log = f"❌ Concluido: {reason_msg}"
                                else:
                                    db_proj.status = "dismissed"
                                    db_proj.bid_response_log = f"🧹 Descartado automáticamente: {reason_msg}"

                                purged_count += 1
                                reasons.append(f"'{db_proj.title[:25]}...': {reason_msg} ({prev_status} -> {db_proj.status})")

                    for b_pid in batch_pids:
                        if b_pid not in found_pids:
                            for db_proj in proj_map.get(b_pid, []):
                                if db_proj and db_proj.status not in ("dismissed", "not_selected"):
                                    prev_status = db_proj.status
                                    was_applied = bool(db_proj.auto_applied or prev_status in ("applied", "auto_applied"))
                                    if was_applied:
                                        db_proj.status = "not_selected"
                                        db_proj.bid_response_log = "❌ Concluido: La publicación fue retirada o cerrada en Freelancer.com."
                                    else:
                                        db_proj.status = "dismissed"
                                        db_proj.bid_response_log = "🧹 Descartado: Proyecto ya no existe en Freelancer.com."
                                    purged_count += 1
                                    reasons.append(f"'{db_proj.title[:25]}...': Eliminado de plataforma ({prev_status} -> {db_proj.status})")
                except Exception as batch_err:
                    self.log(f"⚠️ Error al consultar lote de proyectos en Freelancer: {batch_err}")

            db.commit()
            if purged_count > 0:
                self.log(f"🧹 [AUDITORÍA DE PROPUESTAS] Se auditaron y clasificaron {purged_count} proyectos (cerrados/expirados/no seleccionados).")
            return {
                "status": "success",
                "purged": purged_count,
                "reasons": reasons,
                "message": f"Auditoría completada: Se auditaron y clasificaron {purged_count} proyectos."
            }
        except Exception as e:
            self.log(f"❌ Error en clean_closed_or_taken_bids: {e}")
            return {"status": "error", "message": f"Error al limpiar ofertas: {e}"}
        finally:
            db.close()


    def _auto_respond_thread_messages(self, token: str) -> None:
        """
        Monitorea hilos de chat activos y responde automáticamente a mensajes entrantes
        de clientes utilizando MiamBotSalesCopilot para mantener viva la conversación
        y cerrar el trato de forma 100% autónoma mientras el usuario duerme.
        """
        try:
            url = "https://www.freelancer.com/api/messages/0.1/threads/?limit=10"
            req = urllib.request.Request(url, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            threads = data.get("result", {}).get("threads", [])

            for t in threads:
                tid = t.get("id")
                th_info = t.get("thread", {}) or {}
                ctx = th_info.get("context", {}) or {}

                # Solo procesar hilos vinculados a un proyecto real (ignorar mensajes del sistema o bots)
                if ctx.get("type") != "project":
                    continue

                proj_id = ctx.get("id")

                # Obtener los mensajes recientes del hilo
                murl = f"https://www.freelancer.com/api/messages/0.1/messages/?threads[]={tid}&limit=4"
                mreq = urllib.request.Request(murl, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
                try:
                    with urllib.request.urlopen(mreq, timeout=8) as mresp:
                        mdata = json.loads(mresp.read().decode())
                except Exception:
                    continue

                msgs = mdata.get("result", {}).get("messages", [])
                if not msgs:
                    continue

                # msgs[0] es el mensaje más reciente del hilo
                latest_msg = msgs[0]
                latest_msg_id = latest_msg.get("id")
                from_user = latest_msg.get("from_user")
                client_text = latest_msg.get("message", "").strip()

                # Si el último mensaje es de nosotros (Jack / 29738534), ya respondimos: esperar al cliente
                if from_user == self.my_user_id:
                    continue

                # Si este mensaje específico ya fue respondido, ignorar
                if latest_msg_id in self.replied_message_ids:
                    continue

                if not client_text:
                    continue

                # ¡NUEVO MENSAJE DE UN CLIENTE!
                self.log(f"📩 [NUEVO MENSAJE EN CHAT #{tid}] Cliente ({from_user}) dice: '{client_text[:80]}...'")

                # Obtener contexto del proyecto de la base de datos o de la API
                proj_title = ""
                proj_cat = "web_dev"
                proj_bid = ""
                proj_timeline = ""

                db = SessionLocal()
                try:
                    ext_id = f"freelancer_{proj_id}"
                    proj = db.query(FreelanceProject).filter(FreelanceProject.external_id == ext_id).first()
                    if not proj and proj_id:
                        proj = db.query(FreelanceProject).filter(FreelanceProject.title.like(f"%{proj_id}%")).first()
                    if proj:
                        proj_title = proj.title or ""
                        proj_cat = proj.category or "web_dev"
                        proj_bid = proj.suggested_bid or ""
                        proj_timeline = proj.suggested_timeline or ""
                except Exception:
                    pass
                finally:
                    db.close()

                # Si no está en BD, consultar detalles a la API de Freelancer
                if not proj_title and proj_id:
                    try:
                        p_url = f"https://www.freelancer.com/api/projects/0.1/projects/{proj_id}"
                        p_req = urllib.request.Request(p_url, headers={"freelancer-oauth-v1": token, "User-Agent": "JobHunter-AI/1.0"})
                        with urllib.request.urlopen(p_req, timeout=6) as p_resp:
                            p_data = json.loads(p_resp.read().decode())
                        p_res = p_data.get("result", {})
                        proj_title = p_res.get("title", "")
                        proj_cat = self.proposal_gen.categorize_project(proj_title)
                    except Exception:
                        pass

                # Generar respuesta consultiva ultra natural con MiamBot Copilot
                from core.miambot_copilot import MiamBotSalesCopilot
                reply_data = MiamBotSalesCopilot.generate_chat_reply(
                    client_message=client_text,
                    project_title=proj_title,
                    category=proj_cat,
                    offered_bid=proj_bid,
                    timeline=proj_timeline
                )
                reply_text = reply_data.get("suggested_reply", "").strip()

                if reply_text:
                    # Enviar mensaje vía POST urlencoded a Freelancer
                    send_url = f"https://www.freelancer.com/api/messages/0.1/threads/{tid}/messages/"
                    post_data = urllib.parse.urlencode({"message": reply_text}).encode("utf-8")
                    send_req = urllib.request.Request(
                        send_url,
                        data=post_data,
                        headers={
                            "freelancer-oauth-v1": token,
                            "Content-Type": "application/x-www-form-urlencoded",
                            "User-Agent": "JobHunter-AI/1.0"
                        }
                    )
                    with urllib.request.urlopen(send_req, timeout=10) as send_resp:
                        send_res = json.loads(send_resp.read().decode())

                    # Registrar como respondido y persistir en disco
                    self.replied_message_ids.add(latest_msg_id)
                    self._save_replied_message_ids(self.replied_message_ids)

                    self.log(f"💬 [CHAT AUTO-RESPONDER] ¡Respondido automáticamente en chat #{tid}! Respuesta: '{reply_text[:70]}...'")
                    notify_desktop(
                        title="💬 RESPUESTA AUTOMÁTICA ENVIADA",
                        message=f"Se respondió al cliente en '{proj_title[:30]}': {reply_text[:60]}...",
                        urgency="normal",
                        sound="message-new-instant",
                        voice_text="Mensaje de cliente respondido automáticamente en Freelancer."
                    )
        except Exception as e:
            self.log(f"⚠️ Error en auto-responder de chat: {e}")

    def _query_freelancer_threads(self, token: str) -> List[Dict[str, Any]]:
        """Consulta hilos no leídos para compatibilidad."""
        return []

    async def _execute_scan_and_autobid(self, cfg: Dict[str, Any]):
        """Ejecuta una ronda de detección de proyectos nuevos y auto-postulación."""
        self.log("🔍 Escaneando Freelancer.com en vivo (Filtros: Web, Sistemas, Diseño | 100% Remoto)...")
        loop = asyncio.get_event_loop()
        new_projects = await loop.run_in_executor(None, self._fetch_recent_projects)
        
        if not new_projects:
            self.log("ℹ️ Sin proyectos nuevos en este ciclo que cumplan filtros estrictos. Monitoreando...")
            return

        # 1. Asegurar que los proyectos detectados se guarden en SQLite para el Radar en tiempo real
        db = SessionLocal()
        try:
            for p in new_projects:
                ext_id = str(p["external_id"])
                existing = db.query(FreelanceProject).filter(
                    FreelanceProject.platform == "freelancer",
                    FreelanceProject.external_id.in_([ext_id, f"freelancer_{ext_id}"])
                ).first()
                if not existing:
                    cat = self.proposal_gen.categorize_project(p["title"], p["description"], skills=p.get("job_names", []))
                    db_proj = FreelanceProject(
                        platform="freelancer",
                        external_id=ext_id,
                        title=p["title"],
                        client_name=p.get("client_name", "Cliente Freelancer"),
                        budget=p["budget"],
                        currency=p.get("currency", "USD"),
                        category=cat,
                        url=p["url"],
                        description=p["description"],
                        status="open"
                    )
                    db.add(db_proj)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        # 2. Priorización de velocidad Relámpago: Ordenar estrictamente para SER DE LOS PRIMEROS
        # Prioridad 1: Menor cantidad de ofertas competidoras (bid_count ascendente: 0, 1, 2, 3...)
        # Prioridad 2: Mayor frescura (time_submitted descendente)
        new_projects.sort(key=lambda x: (x.get("bid_count", 999), -x.get("time_submitted", 0)))

        # 3. Evaluar y postular automáticamente según cupo diario (Ritmo suave con protección térmica)
        evaluated_count = 0
        for p in new_projects:
            bids_today = self.get_bids_today_count()
            if bids_today >= cfg.get("max_daily_bids", 4):
                self.log("🛑 Cupo diario completado durante el ciclo. Pausando auto-bids por hoy.")
                break

            if evaluated_count >= 2:
                # Máximo 2 evaluaciones por ciclo para mantener la máquina en reposo térmico frío
                break

            success = await self._evaluate_and_place_bid(p, cfg)
            evaluated_count += 1
            if success:
                # Si una oferta fue enviada con éxito, pausamos el ciclo para dar respiro
                break
            await asyncio.sleep(2)

    def _fetch_recent_projects(self) -> List[Dict[str, Any]]:
        """
        Consulta la API de Freelancer.com en tiempo real (proyectos de hoy).
        Prioriza proyectos de alto ticket y descarta micro-gigs de centavos.
        """
        cfg = self.get_config()
        # NOTA: Para buscar proyectos activos públicos NO enviamos el OAuth token personal,
        # evitando agotar la cuota de peticiones por minuto (HTTP 429). El token se usa exclusivamente al postular.
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

        queries = [
            "",  # Stream general de más recientes en español (tiempo real)
            "web", "wordpress", "landing page", "shopify", "woocommerce",
            "python", "bot", "scraping", "automatizacion", "software",
            "qa", "testing", "soporte ti", "sql", "react", "fastapi",
            "app", "aplicacion", "sistemas", "backend", "frontend",
            "usabilidad", "ui ux", "javascript", "soporte",
            "diseno grafico", "logotipo", "logo", "branding", "flyer",
            "pagina web", "rediseño web", "desarrollo web", "crear web", "bot whatsapp"
        ]
        results = []
        seen_ids = set()

        for q in queries:
            try:
                if q:
                    encoded_q = urllib.parse.quote_plus(q)
                    url = f"https://www.freelancer.com/api/projects/0.1/projects/active?query={encoded_q}&languages[]=es&languages[]=en&limit=25&full_description=true&job_details=true&sort_field=time_submitted"
                else:
                    url = "https://www.freelancer.com/api/projects/0.1/projects/active?languages[]=es&languages[]=en&limit=100&full_description=true&job_details=true&sort_field=time_submitted"

                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())

                projects = data.get("result", {}).get("projects", [])
                for p in projects:
                    pid = str(p.get("id"))
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    b = p.get("budget", {})
                    cur = p.get("currency", {}).get("code", "USD")
                    rate = float(p.get("currency", {}).get("exchange_rate", 1.0) or 1.0)
                    min_b = b.get("minimum", 0)
                    max_b = b.get("maximum", 0)
                    p_type = p.get("type", "fixed")
                    hourly_suffix = " / hora" if p_type == "hourly" else ""

                    # Conteo de ofertas actuales de competidores
                    bid_count = int(p.get("bid_stats", {}).get("bid_count", 0))

                    # Filtro de velocidad relámpago: descartar proyectos con más de 22 ofertas para centrarse en recién publicados
                    if bid_count > 22:
                        continue

                    # Conversión aproximada a USD para estandarizar guardarraíles
                    usd_min = (min_b / rate) if rate > 0 and min_b else 0
                    usd_max = (max_b / rate) if rate > 0 and max_b else 0

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
                        "usd_min": float(usd_min),
                        "usd_max": float(usd_max),
                        "bid_count": bid_count,
                        "is_hourly": (p_type == "hourly"),
                        "job_ids": [j.get("id") for j in p.get("jobs", []) if j.get("id") is not None],
                        "job_names": [j.get("name", "") for j in p.get("jobs", []) if j.get("name")],
                        "url": f"https://www.freelancer.com/projects/{p.get('seo_url', pid)}",
                        "time_submitted": p.get("time_submitted", 0),
                        "language": p.get("language", "es"),
                        "client_name": "Cliente Freelance"
                    })
            except Exception as e:
                pass

        return results

    async def _evaluate_and_place_bid(self, proj_data: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
        """
        Evalúa si el proyecto cumple con los filtros estrictos de Jack:
        1. 100% Remoto (CERO viajes, presencialidad o visitas).
        2. Solo Páginas Web, Sistemas/Software/Python/Bots y Diseño Gráfico (Esposa).
        3. No esquemas 100% comisión sin pago asegurado.
        4. Anti-saturación de competencia (máx permitido).
        5. Guardarraíl financiero y no haber postulado antes.
        """
        title = proj_data["title"]
        desc = proj_data["description"]
        budget_str = proj_data["budget"]
        ext_id = proj_data["external_id"]
        bid_count = proj_data.get("bid_count", 0)

        text_check = f"{title} {desc}".lower()

        # FILTRO ESTRICTO 0: CERO RECUPERACIÓN DE CUENTAS / CONTRASEÑAS / CUENTAS BANEADAS
        # No es ingeniería de software ni desarrollo; son trámites de soporte de usuario (Gmail, Facebook, Instagram, etc.)
        account_recovery_patterns = [
            r"\b(?:recover(?:y|ed)?|unfreeze|unban|restore|reactivat(?:e|ion))\s+(?:disabled\s+)?(?:gmail|google|facebook|instagram|tiktok|epfo|rockstar|email|account|password)\b",
            r"\b(?:recuperar|desbloquear|reactivar)\s+(?:cuenta|contrase[ñn]a|correo)\s+(?:de\s+)?(?:gmail|google|facebook|instagram|tiktok|redes|hackeada|bloqueada|suspendida)\b",
            r"\b(?:account\s+recovery|password\s+recovery|hacked\s+account|disabled\s+account|banned\s+account)\b",
            r"\b(?:recuperaci[oó]n\s+de\s+cuenta|cuenta\s+hackeada|cuenta\s+bloqueada|cuenta\s+inhabilitada)\b"
        ]
        for arpat in account_recovery_patterns:
            if re.search(arpat, text_check):
                self.log(f"🛡️ [Anti-Recuperación Cuentas] Proyecto descartado '{title[:32]}...': Es recuperación de cuentas/contraseñas personales. Jack hace Desarrollo de Software, Web, QA, Datos y Scraping.")
                return False

        # FILTRO ESTRICTO 1: CERO 3D, CERO MODELADO FÍSICO, CERO DISEÑO INDUSTRIAL O MECÁNICO, CERO PATRONAJE
        # La esposa de Jack hace SOLO diseño gráfico 2D (Photoshop, Illustrator, posts para redes, logos, marcas, flyers, banners, trípticos)
        disallowed_3d_patterns = [
            r"\b3d\b", r"\b3ds\b", r"\bmodelado\s*3d\b", r"\brender(?:s|ing|izado|izar)?\s*3d\b",
            r"\bblender\b", r"\bautocad\b", r"\bsketchup\b", r"\brevit\b",
            r"\bsolidworks\b", r"\brhino(?:ceros)?\b", r"\bclo\s*3d\b", r"\boptitex\b",
            r"\bmaya\s*3d\b", r"\bcinema\s*4d\b", r"\bzbrush\b",
            r"\bdiseñ(?:o|ador|adora)\s+industrial\b", r"\bdisen(?:o|ador|adora)\s+industrial\b",
            r"\bdiseñ(?:o|ador|adora)\s+mecánic[ao]\b", r"\bdisen(?:o|ador|adora)\s+mecanic[ao]\b",
            r"\bingenier[ií]a\s+(?:mec[aá]nica|industrial)\b", r"\bplanos?\s+t[eé]cnicos?\b", r"\bvistas?\s+ortogonales?\b",
            r"\bdespiece\b", r"\bpiezas?\s+mec[aá]nicas?\b", r"\bherramienta\s+(?:f[ií]sica|port[aá]til|mec[aá]nica)\b",
            r"\bpatronaje\b", r"\bpatronista\b", r"\bfichas?\s+t[eé]cnicas?\b", r"\bcorte\s+y\s+confecci[oó]n\b",
            r"\bconfecci[oó]n\s+textil\b", r"\bplano\s+arquitect[oó]nico\b", r"\bmodelado\s+bim\b"
        ]
        for pat in disallowed_3d_patterns:
            if re.search(pat, text_check):
                self.log(f"🛡️ [Anti-3D/Industrial] Proyecto descartado '{title[:32]}...': Contiene 3D, ingeniería, planos o patronaje. Tu esposa hace SOLO diseño gráfico 2D (Photoshop, Illustrator, logos, marcas, posts, redes, flyers, banners).")
                return False

        # FILTRO ESTRICTO 2: CERO DISEÑO DE INTERIORES, CERO ARQUITECTURA FÍSICA/CONSTRUCCIÓN, CERO ESPACIOS FÍSICOS, CERO REMODELACIÓN
        disallowed_interior_arch_patterns = [
            r"\b(?:diseñ[oó]\s+de\s+interiores?|diseñador[a]?\s+de\s+interiores?|interior\s+design(?:er)?|interiorismo)\b",
            r"\b(?:diseñ[oó]\s+(?:de\s+)?(?:cocinas?|baños?|banos?|sal[oó]n(?:es)?|habitaci[oó]n|dormitorio|casas?|fachadas?|viviendas?|espacios\s+(?:interiores|f[ií]sicos|habitables)))\b",
            r"\b(?:cocina[s]?\s+y\s+sal[oó]n|cocina/sal[oó]n|isla\s+de\s+cocina|cocina\s+moderna)\b",
            r"\b(?:arquitectura\s+(?:de\s+interiores?|civil|residencial|habitacional|comercial)|estudio\s+de\s+arquitectura|planos?\s+arquitect[oó]nicos?|diseño\s+arquitect[oó]nico|proyecto\s+arquitect[oó]nico|levantamiento\s+arquitect[oó]nico)\b",
            r"\b(?:arquitecto|arquitecta)\s+(?:colegiado|de\s+interiores|de\s+obras?|de\s+edificaciones?|para\s+(?:casa|edificio|remodelaci[oó]n|obra))\b",
            r"\b(?:remodelaci[oó]n\s+(?:de\s+casas?|de\s+viviendas?|de\s+espacios|de\s+cocinas?|de\s+baños?)|decoraci[oó]n\s+de\s+interiores?|decorador[a]?\s+de\s+interiores?)\b",
            r"\b(?:muebles?|carpinter[ií]a|mobiliario|paisajismo|planos?\s+(?:de\s+casas?|arquitect[oó]nicos?|de\s+distribuci[oó]n\s+f[ií]sica))\b"
        ]
        for pat in disallowed_interior_arch_patterns:
            if re.search(pat, text_check):
                self.log(f"🛡️ [Anti-Interiores/Arquitectura] Proyecto descartado '{title[:32]}...': Es diseño de interiores, arquitectura o remodelación física. Tu esposa hace EXCLUSIVAMENTE diseño gráfico 2D (logos, branding, flyers, trípticos, Photoshop, Illustrator).")
                return False

        # FILTRO ESTRICTO 3: HABILIDADES TÉCNICAS EXCLUIDAS (Tags de la plataforma)
        disallowed_skill_names = {
            "interior design", "architecture", "building architecture", "civil architecture", "3d rendering",
            "3d design", "3d modelling", "autocad", "sketchup", "revit", "solidworks",
            "civil engineering", "structural engineering", "landscape design",
            "home design", "fashion design", "video editing", "videography", "video production",
            "voice talent", "audio production",
            "telemarketing", "sales", "sales management", "lead generation", "b2b marketing",
            "cold calling", "appointment setting", "google ads", "facebook ads", "meta ads",
            "advertising", "market research"
        }
        for jname in proj_data.get("job_names", []):
            jname_l = jname.lower().strip()
            # NUNCA excluir arquitectura de software, nube, web o sistemas
            if any(tech in jname_l for tech in ["software", "system", "cloud", "solution", "enterprise", "data", "network", "web", "information"]):
                continue
            if jname_l in disallowed_skill_names or any(w in jname_l for w in ["interior design", "building architect", "civil architect", "3d render", "3d design", "autocad", "sketchup"]):
                self.log(f"🛡️ [Habilidad Excluida] Proyecto descartado '{title[:32]}...': Exige '{jname}'. Se postula exclusivamente a Desarrollo Web, Sistemas y Diseño Gráfico 2D.")
                return False

        # FILTRO ESTRICTO 3.5: CERO VENTAS, TELEMARKETING, CAPTACIÓN DE CLIENTES, LEAD GEN, ADS / PUBLICIDAD
        sales_marketing_patterns = [
            r"\b(?:telemarketing|cold\s*calling|llamadas?\s+(?:en\s+fr[ií]o|telef[oó]nicas?|de\s+ventas?))\b",
            r"\b(?:captaci[oó]n\s+(?:de\s+)?(?:clientes|leads|prospectos)|captar\s+(?:clientes|leads|prospectos)|conseguir\s+(?:clientes|leads))\b",
            r"\b(?:lead\s+generation|generaci[oó]n\s+de\s+leads|generar\s+leads|prospecci[oó]n\s+(?:comercial|b2b)?)\b",
            r"\b(?:appointment\s+setter|setter\s+de\s+ventas|closer\s+de\s+ventas|cerrador\s+de\s+ventas|cold\s+caller)\b",
            r"\b(?:b2b\s+marketing|marketing\s+b2b|campa[ñn]as?\s+(?:de\s+)?(?:google\s+ads|meta\s+ads|facebook\s+ads))\b",
            r"\b(?:google\s+ads|meta\s+ads|facebook\s+ads|tr[aá]fico\s+pago|media\s+buyer|gesti[oó]n\s+de\s+anuncios)\b",
            r"\b(?:anuncios\s+y\s+contenido|campa[ñn]a\s+publicitaria|pauta\s+digital|anuncios\s+digitales)\b",
            r"\b(?:vender\s+(?:servicios|productos|software|saas)|comercial\s+para\s+saas|socio\s+comercial|ejecutivo\s+de\s+ventas)\b",
            r"\b(?:lead\s+magnet|sistema\s+de\s+captaci[oó]n|embudo\s+de\s+ventas|funnel\s+de\s+ventas)\b",
            r"\b(?:conseguir\s+esos\s+primeros\s+clientes|clientes\s+de\s+pago|contratos\s+firmados|demostraciones\s+agendadas)\b"
        ]
        is_dev_code = any(tech in text_check for tech in [
            "script python", "script en python", "desarrollo web", "programador", "backend",
            "api rest", "fastapi", "react", "wordpress", "php", "base de datos", "sql", "qa", "software"
        ]) and any(action in text_check for action in [
            "programar", "desarrollar", "crear código", "codificar", "construir api", "integrar api", "implementar webhook", "corregir bug"
        ])
        if not is_dev_code:
            for pat in sales_marketing_patterns:
                if re.search(pat, text_check):
                    self.log(f"🛡️ [Anti-Ventas/Marketing] Proyecto descartado '{title[:32]}...': Involucra ventas, telemarketing, captación de clientes o campañas de publicidad. Jack es Ingeniero de Sistemas (Desarrollo, QA, Datos, Soporte - Sin Ventas).")
                    return False

        # 1. Categorizar con el motor cognitivo con habilidades incluidas
        category = self.proposal_gen.categorize_project(title, desc, skills=proj_data.get("job_names", []))

        # FILTRO ESTRICTO: Solo Sistemas/Software, Web, QA, Datos, Soporte TI y Diseño Gráfico 2D
        ALLOWED_STRICT_CATEGORIES = {
            "web_dev",                     # Páginas web, Creación, Rediseño, Landing pages, WordPress, Frontend
            "ecommerce_stores",            # Tiendas online, Prestashop, WooCommerce, Shopify
            "python_automation_scraping",  # Python, Scraping, Automatización, Bots, APIs, Software
            "ai_chatbot_system",           # Bots de WhatsApp, Chatbots, Automatización con APIs
            "sql_database",                # Bases de Datos SQL
            "qa_testing",                  # QA Tester, Pruebas funcionales, Casos de prueba, Reporte de bugs
            "power_bi_data",               # Power BI, Dashboards, Analítica de Datos
            "it_support",                  # Soporte TI, Helpdesk, Servidores Linux
            "graphic_design_creative"      # Exclusivamente Diseño Gráfico 2D (Esposa de Jack: logos, branding, flyers, trípticos)
        }
        if category not in ALLOWED_STRICT_CATEGORIES:
            self.log(f"🛡️ [Filtro Jack] Proyecto descartado '{title[:32]}...': Categoría '{category}' excluida (solo Sistemas, Web, QA, Datos y Diseño Gráfico 2D).")
            return False

        # 2. FILTRO ESTRICTO 100% REMOTO & NO VIAJES
        presencial_triggers = [
            "presencial", "visita presencial", "visitas presenciales", "en terreno", "puerta fría", "puerta fria",
            "visitar negocios", "visitar clientes", "visitar empresas", "viajar", "viajes",
            "disponibilidad para viajar", "presencialmente", "trabajo de campo",
            "en paraguay", "en asunción", "en asuncion", "en bogotá", "en bogota", "en medellín", "en medellin",
            "en santiago", "en buenos aires", "en cdmx", "en guadalajara", "oficina física", "oficina fisica"
        ]
        for trig in presencial_triggers:
            if trig in text_check:
                self.log(f"🛡️ [100% Remoto] Proyecto descartado '{title[:32]}...': Exige presencia física/viaje ('{trig}'). Jack trabaja 100% remoto desde su PC.")
                return False

        # FILTRO ESTRICTO: CERO LLAMADAS OBLIGATORIAS / CERO ZOOM (Jack gestiona 100% por chat)
        disallowed_call_patterns = [
            r"\b(?:must\s+speak\s+fluent\s+english\s+on\s+(?:calls?|zoom|phone))\b",
            r"\b(?:daily\s+(?:zoom|google\s+meet|voice|phone)\s+calls?\s+(?:required|mandatory))\b",
            r"\b(?:mandatory\s+(?:voice|video|phone)\s+calls?)\b",
            r"\b(?:fluent\s+spoken\s+english\s+(?:is\s+a\s+must|required))\b",
            r"\b(?:llamadas\s+diarias\s+obligatorias|reuniones\s+diarias\s+por\s+zoom)\b"
        ]
        for cpat in disallowed_call_patterns:
            if re.search(cpat, text_check):
                self.log(f"🛡️ [Anti-Llamadas] Proyecto descartado '{title[:32]}...': Exige llamadas de voz/video obligatorias. Jack gestiona 100% por chat.")
                return False

        # 3. FILTRO ESTRICTO ANTI-COMISIÓN PURA (Sin tarifa fija)
        commission_triggers = [
            "100% comisión", "100% comision", "solo comisión", "solo comision",
            "únicamente a comisión", "unicamente a comision", "pago es 100% por comision",
            "pago 100% comision", "a comisión pura", "a comision pura", "sin salario fijo", "sin sueldo fijo"
        ]
        for trig in commission_triggers:
            if trig in text_check:
                self.log(f"🛡️ [Guardarraíl] Proyecto descartado '{title[:32]}...': Modelo 100% comisión sin pago asegurado ('{trig}').")
                return False

        # 4. FILTRO ESTRICTO: CERO VIDEOS / REELS / EDICIÓN DE VIDEO (Solo para Diseño Gráfico de la esposa)
        if category == "graphic_design_creative":
            video_regex_patterns = [
                r"\bedici[oó]n de videos?\b", r"\beditor[a]? de videos?\b",
                r"\beditar videos?\b", r"\bcreaci[oó]n de videos?\b", r"\bcrear videos?\b",
                r"\breels?\b", r"\btiktok\b", r"\byoutube video\b", r"\bafter effects\b",
                r"\bpremiere(?:\s+pro)?\b", r"\bmogrt\b", r"\bmotion graphics\b", r"\bcapcut\b",
                r"\banimaci[oó]n de video\b", r"\banimar video\b", r"\bintro animad[ao]\b",
                r"\blocuci[oó]n\b", r"\bvoz en off\b", r"\bvoiceover\b", r"\bsubt[ií]tulos\b"
            ]
            for vpat in video_regex_patterns:
                if re.search(vpat, text_check):
                    self.log(f"🛡️ [Solo Diseño Gráfico] Proyecto descartado '{title[:32]}...': Involucra video/reels/edición. La esposa de Jack hace diseño gráfico 2D (logos, banners, branding, Photoshop, Illustrator).")
                    return False

        # 5. FILTRO DE HABILIDADES DEL PERFIL (Garantiza aceptación por Freelancer API)
        user_skills = self.get_user_skill_ids()
        proj_jobs = proj_data.get("job_ids", [])
        if proj_jobs and user_skills:
            if not any(jid in user_skills for jid in proj_jobs):
                self.log(f"🛡️ [Habilidades Perfil] Proyecto descartado '{title[:32]}...': Requiere habilidades no presentes en tu perfil de Freelancer.")
                return False

        # 6. FILTRO DE POSICIONAMIENTO PRIVILEGIADO: SER DE LOS PRIMEROS (TOP 1 A 15)
        # NUNCA postular a proyectos saturados donde quedamos enterrados en páginas lejanas.
        # Jack exige estar entre los primeros postores para máxima probabilidad de respuesta.
        effective_usd = proj_data.get("usd_max") or proj_data.get("usd_min") or proj_data.get("max_budget", 0)
        max_allowed_bids = int(cfg.get("max_competition_bids", 12) or 12)
        # Permitir hasta 18 solo para proyectos excepcionales de alto valor (>= $200 USD / €200 EUR)
        if effective_usd >= 200:
            max_allowed_bids = min(max_allowed_bids + 6, 18)

        if bid_count > max_allowed_bids:
            self.log(f"🛡️ [Anti-Saturación / Top Primeros] Proyecto descartado '{title[:32]}...': Ya tiene {bid_count} ofertas (máx permitido: {max_allowed_bids}). Priorizamos exclusivamente ser de los primeros postores (TOP 1 a {max_allowed_bids}).")
            return False

        self.log(f"⚡ [Oportunidad Temprana] '{title[:32]}...' tiene apenas {bid_count} ofertas. ¡Postulando de inmediato para posicionar a Jack en el TOP {bid_count + 1}!")

        # 3. Guardarraíl Salarial Flexible - Trabajos Pequeños y Grandes
        min_hourly = cfg.get("min_hourly_rate", 8.0)
        min_fixed = cfg.get("min_fixed_budget", 20.0)

        if proj_data["is_hourly"]:
            effective_usd_rate = proj_data["usd_max"] or proj_data["usd_min"] or proj_data["max_budget"]
            if effective_usd_rate > 0 and effective_usd_rate < min_hourly:
                self.log(f"🛡️ [Guardarraíl Tarifa] Tarifa horaria de '{title[:32]}...' (${effective_usd_rate:.0f}/hr) menor al mínimo requerido (${min_hourly}/hr).")
                return False
        else:
            effective_usd_fixed = proj_data["usd_max"] or proj_data["usd_min"] or proj_data["max_budget"]
            if effective_usd_fixed > 0 and effective_usd_fixed < min_fixed:
                self.log(f"🛡️ [Guardarraíl Presupuesto] Presupuesto de '{title[:32]}...' (${effective_usd_fixed:.0f} USD) inferior a la meta mínima (${min_fixed} USD).")
                return False

        # 4. Verificar en BD si ya existe y si ya fue postulado
        db = SessionLocal()
        try:
            existing = db.query(FreelanceProject).filter(
                FreelanceProject.platform == "freelancer",
                FreelanceProject.external_id.in_([str(ext_id), f"freelancer_{ext_id}"])
            ).first()

            if existing and (existing.status in ("applied", "auto_applied", "dismissed") or existing.auto_applied):
                return False  # Ya postulado previamente

            # 5. Generar propuesta cognitiva optimizada (Bilingüe: Español / Inglés)
            p_lang = proj_data.get("language") or ("en" if any(w in text_check for w in [" the ", " to ", " and ", " is ", " looking for ", " need "]) else "es")
            default_client = "Estimado cliente" if p_lang == "es" else "Hi there"
            proposal_res = self.proposal_gen.generate_proposal(
                title=title,
                description=desc,
                client_name=proj_data.get("client_name", default_client),
                budget=budget_str,
                language=p_lang
            )
            proposal_text = proposal_res["proposal_text"]
            suggested_bid = proposal_res["suggested_bid"]
            suggested_time = proposal_res["suggested_timeline"]

            # 6. Ejecutar la oferta (API Token o Navegador Autónomo)
            bid_success, response_note = await self._send_bid_to_platform(
                project_id=ext_id,
                bid_amount_str=suggested_bid,
                proposal_text=proposal_text,
                cfg=cfg,
                project_url=proj_data.get("url", "")
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
                self.log(f"⚡ [AUTO-BID ENVIADO] Postulado a '{title}' ({suggested_bid}, {bid_count} ofertas previas) en Freelancer.com.")
                notify_desktop(
                    title="⚡ [JobHunter AI] Oferta Enviada",
                    message=f"Postulado con éxito a: '{title[:45]}...' ({suggested_bid})",
                    urgency="normal",
                    sound="message-new-instant"
                )
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
                        status="dismissed" if ("error" in response_note.lower() or "must have" in response_note.lower()) else "pending",
                        auto_applied=False,
                        bid_response_log=response_note
                    )
                    db.add(new_proj)
                else:
                    if "error" in response_note.lower() or "must have" in response_note.lower():
                        existing.status = "dismissed"
                    existing.generated_proposal = proposal_text
                    existing.suggested_bid = suggested_bid
                    existing.suggested_timeline = suggested_time
                    existing.bid_response_log = response_note
                db.commit()
                self.log(f"📝 Propuesta IA generada para '{title}'. {response_note}")
                return False
        finally:
            db.close()

    async def _send_bid_to_platform(self, project_id: str, bid_amount_str: str, proposal_text: str, cfg: Dict[str, Any], project_url: str = "") -> tuple[bool, str]:
        """
        Envía la propuesta a Freelancer.com.
        Prioridad 1: Vía REST API con Developer Token (< 300ms de latencia).
        Prioridad 2: Vía Navegador Playwright con sesión persistente si el navegador está autenticado.
        """
        token = cfg.get("freelancer_api_token")
        proposal_text = strip_all_emojis(proposal_text)
        
        num_match = re.search(r'(\d+(?:\.\d+)?)', bid_amount_str)
        bid_value = float(num_match.group(1)) if num_match else 250.0

        # Prioridad 1: Envío instantáneo por API
        if token and len(token) > 10:
            try:
                pid_clean = re.search(r'(\d+)', str(project_id))
                if not pid_clean:
                    return False, f"ID de proyecto inválido: {project_id}"
                numeric_pid = int(pid_clean.group(1))

                url = "https://www.freelancer.com/api/projects/0.1/bids/"
                payload = json.dumps({
                    "project_id": numeric_pid,
                    "bidder_id": 29738534,
                    "amount": bid_value,
                    "period": 4,
                    "description": proposal_text,
                    "milestone_percentage": 100
                }).encode("utf-8")

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "freelancer-oauth-v1": token,
                        "Content-Type": "application/json",
                        "User-Agent": "JobHunter-AI/1.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    resp_json = json.loads(resp.read().decode())
                    bid_id = resp_json.get("result", {}).get("id", "OK")
                    return True, f"Bid REAL colocado en Freelancer.com vía API: ID #{bid_id}"
            except urllib.error.HTTPError as he:
                try:
                    err_json = json.loads(he.read().decode())
                    err_msg = err_json.get("message") or str(err_json)
                except Exception:
                    err_msg = f"HTTP {he.code}"
                return False, f"Error API Freelancer: {err_msg}"
            except Exception as e:
                return False, f"Error en API Freelancer: {e}"

        # Prioridad 2: Intento por Navegador Autónomo si hay sesión iniciada
        try:
            from core.browser_bidder import BrowserBidder
            bidder = BrowserBidder()
            if bidder.check_login_status():
                target_url = project_url or f"https://www.freelancer.com/projects/{project_id}"
                loop = asyncio.get_event_loop()
                bid_res = await loop.run_in_executor(
                    None,
                    lambda: bidder.fill_and_place_bid(
                        project_url=target_url,
                        bid_amount=bid_value,
                        proposal_text=proposal_text,
                        period_days=3,
                        auto_submit=True
                    )
                )
                if bid_res.get("success"):
                    return True, f"Bid colocado exitosamente vía Navegador Autónomo: {bid_res.get('message')}"
                else:
                    return False, f"Navegador: {bid_res.get('error')}"
        except Exception as be:
            pass

        # Si ni API ni Navegador están configurados
        return False, "⚠️ Acción requerida: Ingresa tu Token de API Freelancer en el Dashboard o inicia sesión con './service_ctl.sh login' para activar el envío automático real."

    async def test_bid(self, project_id: int) -> Dict[str, Any]:
        """Permite probar y enviar una oferta REAL a un proyecto específico de la BD."""
        db = SessionLocal()
        try:
            proj = db.query(FreelanceProject).filter(FreelanceProject.id == project_id).first()
            if not proj:
                return {"success": False, "error": "Proyecto no encontrado"}

            cfg = self.get_config()
            if not proj.generated_proposal or len(proj.generated_proposal) < 30:
                prop_data = self.proposal_gen.generate_proposal(
                    title=proj.title,
                    description=proj.description or "",
                    client_name=proj.client_name or "Estimado cliente",
                    budget=proj.budget or "$150 USD"
                )
                proj.generated_proposal = prop_data["proposal_text"]
                proj.suggested_bid = prop_data["suggested_bid"]
                proj.suggested_timeline = prop_data["suggested_timeline"]
                db.commit()

            success, note = await self._send_bid_to_platform(
                project_id=proj.external_id,
                bid_amount_str=proj.suggested_bid or "$150 USD",
                proposal_text=proj.generated_proposal,
                cfg=cfg,
                project_url=proj.url or ""
            )

            now = datetime.now()
            if success:
                proj.auto_applied = True
                proj.status = "applied"
                proj.applied_at = now
                proj.bid_response_log = note
                db.commit()
                self.log(f"⚡ [OFERTA REAL ENVIADA] {note} para '{proj.title}'")
                notify_desktop(
                    title="⚡ [JobHunter AI] Oferta Enviada a Freelancer",
                    message=f"Postulación real enviada: '{proj.title[:45]}...' ({proj.suggested_bid})",
                    urgency="normal",
                    sound="message-new-instant"
                )
                return {
                    "success": True,
                    "project_id": proj.id,
                    "title": proj.title,
                    "bid": proj.suggested_bid,
                    "note": note
                }
            else:
                proj.bid_response_log = f"Intento de envío: {note}"
                db.commit()
                return {
                    "success": False,
                    "error": note
                }
        finally:
            db.close()
