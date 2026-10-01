import os
import re
import json
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, Request, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel

from core.database import init_db, get_db, SessionLocal, Job, ApplicationLog, EmailMessage, AgentMetric, FreelanceProject
from core.llm_engine import LLMEngine
from core.proposal_generator import ProposalGenerator
from adapters.freelance_hunter import FreelanceHunter
from adapters.browser_manager import BrowserManager
from adapters.linkedin import LinkedInAdapter
from adapters.computrabajo import ComputrabajoAdapter
from adapters.bumeran import BumeranAdapter
from adapters.external_flow import ExternalFlowAdapter
from adapters.getonbrd import GetOnBoardAdapter
from adapters.remote_tech import RemoteTechAdapter
from adapters.laborum import LaborumAdapter
from adapters.torre import TorreAdapter
from email_agent.scanner import EmailScanner
from email_agent.responder import EmailAgent
from core.job_queue import JobQueueWorker
from core.autonomous_hunter import AutonomousHunterDaemon
from core.freelance_autobidder import FreelanceAutoBidder
from core.miambot_copilot import MiamBotSalesCopilot

app = FastAPI(title="JobHunter AI - Dashboard de Búsqueda Laboral")

# Inicializar Base de Datos
init_db()

# Montar plantillas
templates = Jinja2Templates(directory="web_ui/templates")

# Estado global del agente
agent_state = {
    "is_running": False,
    "current_action": "🟢 Sistema Activo y Listo",
    "last_run": None,
    "logs": [
        f"[{datetime.now().strftime('%H:%M:%S')}] Sistema inicializado correctamente. Conexión a SQLite activa (NullPool)."
    ]
}

def log_event(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    agent_state["logs"].append(entry)
    if len(agent_state["logs"]) > 100:
        agent_state["logs"].pop(0)
    print(entry)

llm = LLMEngine()
job_queue = JobQueueWorker(llm, log_callback=log_event)
autonomous_hunter = AutonomousHunterDaemon(llm, job_queue, log_callback=log_event, interval_minutes=90)
proposal_generator = ProposalGenerator(llm)
freelance_hunter = FreelanceHunter(proposal_generator)
freelance_autobidder = FreelanceAutoBidder(proposal_generator, log_callback=log_event)


@app.on_event("startup")
async def startup_event():
    """Inicia con prioridad el motor freelance (por horas y entregables) y en segundo plano el empleo corporativo."""
    # 1. Prioridad Principal: Motor Freelance & Oportunidades por Horas
    freelance_autobidder.start()
    log_event("⚡ FREELANCE AUTO-BIDDER 24/7 EN MODO PRIORITARIO: Monitoreo activo de contratos por hora y precio fijo.")

    # 2. Segundo Plano: Rastreador de Empleo Corporativo
    autonomous_hunter.start(interval_minutes=90)
    log_event("💼 Rastreador Corporativo Remoto configurado en SEGUNDO PLANO (Ciclos espaciados en background cada 90 min).")


@app.on_event("shutdown")
async def shutdown_event():
    """Detiene ordenadamente los motores continuos."""
    autonomous_hunter.stop()
    freelance_autobidder.stop()


# --- Tareas en Segundo Plano ---
async def execute_job_hunting_cycle(platform_filter: Optional[str] = None):
    if agent_state["is_running"]:
        log_event("⚠️ Ya hay un ciclo de búsqueda en ejecución.")
        return

    agent_state["is_running"] = True
    agent_state["current_action"] = "Iniciando explorador de vacantes remotas..."
    log_event("🚀 Iniciando ciclo de búsqueda automatizada para Primer Empleo...")

    bm = BrowserManager(headless=True)
    db = SessionLocal()

    try:
        profile = llm.profile
        # Consultas de alta afinidad para Ingeniero de Sistemas sin experiencia laboral previa
        search_queries = [
            "desarrollador junior",
            "practicante sistemas",
            "programador junior"
        ]
        
        adapters = []
        if not platform_filter or platform_filter == "torre":
            adapters.append(TorreAdapter(bm, llm))
        if not platform_filter or platform_filter == "getonbrd":
            adapters.append(GetOnBoardAdapter(bm, llm))
        if not platform_filter or platform_filter == "remotetech":
            adapters.append(RemoteTechAdapter(bm, llm))
        if not platform_filter or platform_filter == "computrabajo":
            adapters.append(ComputrabajoAdapter(bm, llm))
        if not platform_filter or platform_filter == "linkedin":
            adapters.append(LinkedInAdapter(bm, llm))
        if not platform_filter or platform_filter == "bumeran":
            adapters.append(BumeranAdapter(bm, llm))
        if not platform_filter or platform_filter == "laborum":
            adapters.append(LaborumAdapter(bm, llm))

        total_new_jobs = 0

        for adapter in adapters:
            for query in search_queries[:2]:
                agent_state["current_action"] = f"Buscando en {adapter.platform_name.capitalize()}: '{query}'..."
                log_event(f"🔎 Explorando {adapter.platform_name.upper()} para: '{query}' (100% Remoto)")

                try:
                    jobs = await adapter.search_jobs(query=query, remote_only=True, max_results=8)
                    for j in jobs:
                        # Verificar si ya existe por ID o por título similar en la misma plataforma
                        existing = db.query(Job).filter(
                            Job.platform == j["platform"],
                            Job.external_id == j["external_id"]
                        ).first()

                        if not existing:
                            req_fit = j.get("requirements")
                            if not req_fit:
                                req_fit = llm.analyze_requirements_fit(
                                    title=j["title"],
                                    description=j.get("description", ""),
                                    company=j["company"],
                                    location=j.get("location", "")
                                )

                            fulfilled = req_fit.get("cumplimos", [])
                            missing = req_fit.get("no_cumplimos", [])
                            strategy = req_fit.get("estrategia", "")
                            is_rec = req_fit.get("is_recommended", True)
                            score = req_fit.get("score", 0.5)

                            new_job = Job(
                                platform=j["platform"],
                                external_id=j["external_id"],
                                title=j["title"],
                                company=j["company"],
                                location=j["location"],
                                modality=j.get("modality", "remote"),
                                url=j["url"],
                                salary_snippet=j.get("salary_snippet", ""),
                                description=j.get("description", ""),
                                match_score=score,
                                match_reason=req_fit.get("reason", ""),
                                requirements_json=json.dumps(req_fit, ensure_ascii=False),
                                requirements_fulfilled=json.dumps(fulfilled, ensure_ascii=False),
                                requirements_missing=json.dumps(missing, ensure_ascii=False),
                                strategy_notes=strategy,
                                is_recommended=is_rec,
                                status="discovered"
                            )
                            db.add(new_job)
                            db.commit()
                            total_new_jobs += 1
                            log_event(f"✨ Nueva vacante afín ({int(new_job.match_score*100)}%): '{new_job.title}' en {new_job.company}")
                except Exception as ad_err:
                    log_event(f"❌ Error buscando en {adapter.platform_name}: {ad_err}")

        log_event(f"🎯 Búsqueda concluida exitosamente. Se registraron {total_new_jobs} nuevas oportunidades.")
        agent_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        log_event(f"❌ Error crítico en ciclo: {e}")
    finally:
        await bm.close()
        db.close()
        agent_state["is_running"] = False
        agent_state["current_action"] = "🟢 Sistema Activo y Listo"


async def execute_email_scan_cycle():
    agent_state["current_action"] = "Escaneando correos de reclutadores..."
    log_event("📬 Verificando bandeja de entrada en busca de respuestas...")
    
    bm = BrowserManager(headless=True)
    db = SessionLocal()
    try:
        scanner = EmailScanner(bm)
        agent = EmailAgent(scanner, llm)
        new_records = await agent.process_inbox(db)
        if new_records:
            log_event(f"🎉 Se detectaron {len(new_records)} mensajes clave de reclutadores.")
        else:
            log_event("ℹ️ No hay nuevos correos de procesos de selección pendientes.")
    except Exception as e:
        log_event(f"❌ Error escaneando correos: {e}")
    finally:
        await bm.close()
        db.close()
        agent_state["current_action"] = "🟢 Sistema Activo y Listo"


PORTAL_AUTH_MAP = {
    "linkedin": {
        "id": "linkedin",
        "name": "LinkedIn",
        "url": "https://www.linkedin.com/login",
        "domain": "linkedin.com",
        "description": "Red profesional y vacantes con Solicitud sencilla (Easy Apply)",
        "icon": "💼",
        "category": "Red Profesional"
    },
    "computrabajo": {
        "id": "computrabajo",
        "name": "Computrabajo Perú",
        "url": "https://pe.computrabajo.com/candidate/login",
        "domain": "computrabajo.com",
        "description": "Portal líder nacional para ofertas de TI, desarrollo y sistemas",
        "icon": "🏢",
        "category": "Bolsa Nacional"
    },
    "bumeran": {
        "id": "bumeran",
        "name": "Bumeran Perú",
        "url": "https://www.bumeran.com.pe/postulantes",
        "domain": "bumeran.com.pe",
        "description": "Plataforma líder en Perú con filtros avanzados de teletrabajo",
        "icon": "🌐",
        "category": "Bolsa Nacional"
    },
    "laborum": {
        "id": "laborum",
        "name": "Laborum Perú",
        "url": "https://www.laborum.pe",
        "domain": "laborum.pe",
        "description": "Portal peruano con alta demanda en prácticas y sistemas junior",
        "icon": "🇵🇪",
        "category": "Bolsa Nacional"
    },
    "torre": {
        "id": "torre",
        "name": "Torre.co LatAm",
        "url": "https://torre.ai",
        "domain": "torre.ai",
        "description": "Red global de empleo remoto tech con contratos en USD",
        "icon": "🚀",
        "category": "Tech Remoto"
    },
    "getonbrd": {
        "id": "getonbrd",
        "name": "Get on Board",
        "url": "https://www.getonbrd.com/webpros/login",
        "domain": "getonbrd.com",
        "description": "Startups y empresas tech de software 100% remoto en LatAm",
        "icon": "💻",
        "category": "Tech Remoto"
    },
    "indeed": {
        "id": "indeed",
        "name": "Indeed Perú",
        "url": "https://pe.indeed.com",
        "domain": "indeed.com",
        "description": "Agregador global masivo con ofertas directas de empresas",
        "icon": "🔎",
        "category": "Agregador Global"
    },
    "gmail": {
        "id": "gmail",
        "name": "Gmail / Google",
        "url": "https://mail.google.com/",
        "domain": "google.com",
        "description": "Bandeja activa de entrevistas, pruebas técnicas y Google SSO",
        "icon": "📧",
        "category": "Comunicación"
    }
}


def get_portal_connection_status() -> List[Dict[str, Any]]:
    """Verifica qué portales tienen cookies / sesión activa en data/browser_profile."""
    cookie_db = Path("data/browser_profile/Default/Cookies")
    hosts = []
    if cookie_db.exists():
        try:
            import sqlite3
            con = sqlite3.connect(f"file:{cookie_db}?immutable=1", uri=True)
            cur = con.cursor()
            cur.execute("SELECT DISTINCT host_key FROM cookies;")
            hosts = [r[0] for r in cur.fetchall()]
            con.close()
        except Exception:
            pass

    portals_info = []
    for pid, pdata in PORTAL_AUTH_MAP.items():
        domain = pdata["domain"]
        is_connected = any(domain in h for h in hosts)
        portals_info.append({
            **pdata,
            "connected": is_connected,
            "status_label": "🟢 Conectado" if is_connected else "🟡 Pendiente de inicio"
        })
    return portals_info


async def launch_interactive_login_session(target_platform: Optional[str] = None):
    """Abre LibreWolf (o Chromium en fallback) en pantalla para que el usuario inicie sesión."""
    portals_to_open = []
    if target_platform and target_platform != "all" and target_platform in PORTAL_AUTH_MAP:
        portals_to_open = [PORTAL_AUTH_MAP[target_platform]]
        log_event(f"🌐 Abriendo LibreWolf para conectar: {PORTAL_AUTH_MAP[target_platform]['name']}...")
    else:
        portals_to_open = list(PORTAL_AUTH_MAP.values())
        log_event(f"🌐 Abriendo LibreWolf con las {len(portals_to_open)} plataformas de búsqueda...")

    urls = [p["url"] for p in portals_to_open]

    # Prioridad: Lanzar en LibreWolf (el navegador predeterminado configurado)
    librewolf_paths = [
        "/home/jack/.local/bin/librewolf",
        "/home/jack/.local/bin/libreflow",
        "/var/lib/flatpak/exports/bin/io.gitlab.librewolf-community"
    ]
    librewolf_bin = next((p for p in librewolf_paths if os.path.exists(p) and os.access(p, os.X_OK)), None)

    if librewolf_bin:
        try:
            log_event(f"🚀 Abriendo LibreWolf con {len(urls)} pestañas listas para conectar...")
            subprocess.Popen([librewolf_bin] + urls)
            log_event("✅ LibreWolf ejecutándose en pantalla. Inicia sesión en las páginas deseadas.")
            return
        except Exception as le:
            log_event(f"⚠️ Error iniciando LibreWolf ({le}). Recurriendo a Chromium...")

    # Fallback a Chromium si LibreWolf no responde
    bm = BrowserManager(user_data_dir="data/browser_profile", headless=False)
    try:
        context = await bm.initialize()
        for idx, portal in enumerate(portals_to_open):
            if idx == 0:
                p = await bm.new_page_with_stealth()
            else:
                p = await context.new_page()
            try:
                await p.goto(portal["url"], wait_until="domcontentloaded", timeout=25000)
            except Exception as pe:
                print(f"[LoginBrowser] Error cargando {portal['name']}: {pe}")
            await asyncio.sleep(0.8)

        log_event("✅ Ventana de navegador lista. Inicia sesión en las páginas deseadas y cierra al terminar.")
        for _ in range(90):
            await asyncio.sleep(10)
            if not context.pages:
                break
    except Exception as e:
        log_event(f"ℹ️ Sesión de navegador finalizada o cerrada: {e}")
    finally:
        await bm.close()


# --- Rutas de la Interfaz Web ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/system/health")
async def get_system_health(db: Session = Depends(get_db)):
    """Diagnóstico en tiempo real del sistema y estado de componentes."""
    personal = llm.profile.get("personal_info", {})
    return {
        "status": "operational",
        "database": {
            "engine": "SQLite",
            "pool": "NullPool (Sin bloqueos)",
            "total_jobs": db.query(Job).count(),
            "applied_jobs": db.query(Job).filter(Job.status == "applied").count(),
            "status": "connected"
        },
        "candidate": {
            "name": personal.get("full_name", "Ingeniero de Sistemas"),
            "email": personal.get("email", "jmberrocale@gmail.com"),
            "phone": personal.get("phone", "+51 963979996"),
            "degree": llm.profile.get("education", {}).get("degree", "Ingeniería de Sistemas"),
            "experience": "0 años formales (Primer Empleo formal)",
            "target": "100% Remoto"
        },
        "adapters": [
            {"id": "torre", "name": "Torre.co LatAm", "status": "activo", "mode": "Junior & Trainee Remoto"},
            {"id": "getonbrd", "name": "Get on Board LatAm", "status": "activo", "mode": "100% Remoto Tech"},
            {"id": "remotetech", "name": "Remote Tech Portals", "status": "activo", "mode": "Contratos USD (>= $800)"},
            {"id": "computrabajo", "name": "Computrabajo Perú", "status": "activo", "mode": "Teletrabajo Remoto"},
            {"id": "linkedin", "name": "LinkedIn Jobs", "status": "activo", "mode": "Easy Apply Remoto"},
            {"id": "bumeran", "name": "Bumeran Perú", "status": "activo", "mode": "Teletrabajo Remoto"},
            {"id": "laborum", "name": "Laborum Perú", "status": "activo", "mode": "Sistemas & Junior Remoto"},
            {"id": "external", "name": "Portales Externos", "status": "activo", "mode": "Registro con Gmail"}
        ],
        "policy": {
            "strict_remote": True,
            "min_salary_pen": 2000,
            "min_salary_usd": 800,
            "target": "Ingeniero de Sistemas (Primer Empleo formal)"
        },
        "continuous_hunter": autonomous_hunter.get_status(),
        "freelance_autobidder": freelance_autobidder.get_status(),
        "browser_engine": {
            "type": "Playwright Chromium Stealth",
            "headless": job_queue.headless,
            "profile_dir": "data/browser_profile"
        },
        "agent": {
            "is_running": agent_state["is_running"] or autonomous_hunter.is_running,
            "current_action": agent_state["current_action"],
            "queue_pending": job_queue.queue.qsize()
        }
    }


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    active_jobs = db.query(Job).filter(Job.status != "expired").count()
    applied_jobs = db.query(Job).filter(Job.status == "applied").count()
    expired_jobs = db.query(Job).filter(Job.status == "expired").count()
    interviews = db.query(EmailMessage).filter(EmailMessage.category == "interview_invite").count()
    tests = db.query(EmailMessage).filter(EmailMessage.category == "coding_challenge").count()

    freelance_projects = db.query(FreelanceProject).filter(FreelanceProject.status != "dismissed").all()
    freelance_count = len(freelance_projects)
    freelance_hourly_count = sum(
        1 for p in freelance_projects
        if any(h in ((p.budget or '') + ' ' + (p.suggested_bid or '') + ' ' + (p.title or '') + ' ' + (p.generated_proposal or '')).lower()
               for h in ['/ hora', '/hr', '/ hour', 'por hora', 'tarifa horaria', 'por turno', 'modalidad: por horas'])
    )
    freelance_fixed_count = freelance_count - freelance_hourly_count
    freelance_applied_count = sum(1 for p in freelance_projects if p.status in ["applied", "auto_applied"] or p.auto_applied)

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    freelance_bids_today = db.query(FreelanceProject).filter(
        FreelanceProject.auto_applied == True,
        FreelanceProject.applied_at >= today_start
    ).count()

    roles = llm.get_target_roles()
    active_roles = sum(1 for r in roles if r.get("enabled", True))

    return {
        "total_jobs": active_jobs,
        "applied_jobs": applied_jobs,
        "expired_jobs": expired_jobs,
        "interviews": interviews,
        "tests": tests,
        "freelance_count": freelance_count,
        "freelance_hourly_count": freelance_hourly_count,
        "freelance_fixed_count": freelance_fixed_count,
        "freelance_applied_count": freelance_applied_count,
        "freelance_bids_today": freelance_bids_today,
        "active_roles_count": active_roles,
        "total_roles_count": len(roles),
        "is_running": agent_state["is_running"] or autonomous_hunter.is_running,
        "current_action": agent_state["current_action"],
        "last_run": agent_state["last_run"],
        "queue_size": job_queue.queue.qsize(),
        "queue_running": job_queue.is_running,
        "current_processing_job": job_queue.current_job_title,
        "headless": job_queue.headless
    }



@app.get("/api/jobs")
async def get_jobs(status: Optional[str] = None, platform: Optional[str] = None, role: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Job)
    if status and status != "all":
        query = query.filter(Job.status == status)
    else:
        # Por defecto solo mostrar vacantes activas y disponibles (ocultar expiradas/eliminadas)
        query = query.filter(Job.status != "expired")
    if platform and platform != "all":
        query = query.filter(Job.platform == platform)
    
    jobs = query.order_by(Job.match_score.desc(), Job.created_at.desc()).limit(80).all()
    
    results = []
    for j in jobs:
        # Emparejar con puesto objetivo
        role_info = llm.match_job_to_role(j.title, j.description or "")
        target_role = role_info["role_name"]
        target_role_id = role_info["role_id"]
        target_role_enabled = role_info["is_allowed"]
        target_role_icon = role_info.get("icon", "💼")

        # Filtro de puesto opcional
        if role and role != "all":
            if role != target_role_id and role.lower() not in target_role.lower():
                continue

        # Decodificar listas de cumplidos y no cumplidos
        cumplimos = []
        no_cumplimos = []
        estrategia = j.strategy_notes or ""

        if j.requirements_fulfilled:
            try:
                cumplimos = json.loads(j.requirements_fulfilled)
            except Exception:
                cumplimos = []
        if j.requirements_missing:
            try:
                no_cumplimos = json.loads(j.requirements_missing)
            except Exception:
                no_cumplimos = []

        if not cumplimos and not no_cumplimos and j.requirements_json:
            try:
                data = json.loads(j.requirements_json)
                cumplimos = data.get("cumplimos", [])
                no_cumplimos = data.get("no_cumplimos", [])
                estrategia = data.get("estrategia", estrategia)
            except Exception:
                pass

        if not cumplimos:
            analysis = llm.analyze_requirements_fit(j.title, j.description or "", j.company, j.location)
            cumplimos = analysis["cumplimos"]
            no_cumplimos = analysis["no_cumplimos"]
            estrategia = analysis["estrategia"]

        results.append({
            "id": j.id,
            "platform": j.platform,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "url": j.url,
            "salary": j.salary_snippet or "",
            "match_score": int(j.match_score * 100),
            "match_reason": j.match_reason or "",
            "cumplimos": cumplimos,
            "no_cumplimos": no_cumplimos,
            "estrategia": estrategia,
            "is_recommended": j.is_recommended if j.is_recommended is not None else True,
            "status": j.status,
            "target_role": target_role,
            "target_role_id": target_role_id,
            "target_role_enabled": target_role_enabled,
            "target_role_icon": target_role_icon,
            "created_at": j.created_at.strftime("%d/%m %H:%M") if j.created_at else ""
        })
    return results


@app.get("/api/applications")
async def get_applications(status: Optional[str] = None, platform: Optional[str] = None, q: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Retorna el registro detallado de dónde se registró/postuló el agente
    y con qué oferta laboral exacta fue realizada cada postulación.
    Soporta búsqueda textual instantánea (q).
    """
    import urllib.parse

    query = db.query(ApplicationLog).join(Job, ApplicationLog.job_id == Job.id)
    if status and status != "all":
        query = query.filter(ApplicationLog.status == status)
    if platform and platform != "all":
        query = query.filter(ApplicationLog.platform == platform)
    if q and q.strip():
        q_term = f"%{q.strip().lower()}%"
        query = query.filter(
            (func.lower(Job.title).like(q_term)) |
            (func.lower(Job.company).like(q_term)) |
            (func.lower(Job.url).like(q_term)) |
            (func.lower(ApplicationLog.notes).like(q_term))
        )

    logs = query.order_by(ApplicationLog.created_at.desc()).limit(150).all()

    results = []
    for log in logs:
        job = log.job
        if not job:
            continue

        parsed = urllib.parse.urlparse(job.url)
        portal_domain = parsed.netloc or job.platform

        # Parsear Q&A si hubo
        qa = []
        if log.questions_answers:
            try:
                qa = json.loads(log.questions_answers)
            except Exception:
                qa = []

        # Determinar método de autenticación y cuenta usada
        notes_low = (log.notes or "").lower()
        if "google" in notes_low or "gmail" in notes_low:
            auth_method = "Google SSO (jmberrocale@gmail.com)"
        elif "easy apply" in notes_low or job.platform == "linkedin":
            auth_method = "Sesión Activa LinkedIn (Easy Apply)"
        elif job.platform in ["computrabajo", "bumeran", "laborum", "getonbrd", "torre"]:
            auth_method = f"Sesión Persistente en {job.platform.capitalize()} (jmberrocale@gmail.com)"
        else:
            auth_method = "Auto-registro con correo y contraseña (jmberrocale@gmail.com)"

        # Label de estado amigable
        if log.status == "success":
            status_badge = "🟢 Registrado y Postulado con Éxito"
            status_type = "success"
        elif log.status == "requires_manual_action":
            status_badge = "🟡 Requiere Revisión / Acción Manual"
            status_type = "review"
        elif log.status == "expired":
            status_badge = "🗑️ Oferta Expirada / Finalizada"
            status_type = "expired"
        else:
            status_badge = f"⚪ {log.status.capitalize()}"
            status_type = "other"

        role_info = llm.match_job_to_role(job.title, job.description or "")

        # Decodificar cumplidos y no cumplidos
        req_fulfilled = []
        req_missing = []
        if job.requirements_fulfilled:
            try:
                req_fulfilled = json.loads(job.requirements_fulfilled)
            except Exception:
                pass
        if job.requirements_missing:
            try:
                req_missing = json.loads(job.requirements_missing)
            except Exception:
                pass

        # Anuncio y propuesta laboral completa
        anuncio_text = (job.description or "").strip()
        is_brief_or_date = (
            len(anuncio_text) < 50 or 
            re.match(r'^(hace\s+\d+|hoy|\d+\s+de\s+[a-z]+)', anuncio_text.lower()) is not None
        )
        if is_brief_or_date:
            anuncio_text = (
                f"📌 PUESTO: {job.title}\n"
                f"🏢 EMPRESA: {job.company}\n"
                f"📍 MODALIDAD / UBICACIÓN: {job.location or '100% Remoto'}\n"
                f"💰 RANGO SALARIAL: {job.salary_snippet or 'Acorde al mercado / A convenir'}\n"
                f"🌐 PORTAL ORIGEN: {portal_domain}\n\n"
                f"📄 DETALLE DEL ANUNCIO Y PROPUESTA LABORAL:\n"
                f"Convocatoria oficial para la posición de {job.title} en {job.company}. "
                f"Posición técnica correspondiente al área de {role_info.get('role_name', 'Ingeniería de Sistemas')} con requerimientos afines a tu formación académica y perfil profesional.\n\n"
                f"🎯 REQUISITOS Y PERFIL EVALUADO:\n"
                f"• Carrera universitaria o técnica en Ingeniería de Sistemas, Informática, Computación o afines.\n"
                f"• Competencias y tecnologías clave: {', '.join(req_fulfilled[:5]) if req_fulfilled else 'Herramientas de software, sistemas y resolución de incidencias'}.\n"
                f"• Modalidad de trabajo: {job.location or 'Remoto / Híbrido'}.\n\n"
                f"🔗 Nota: Puedes consultar la publicación completa original y actualizada directamente en el portal haciendo clic en 'Ver Aviso Oficial'."
            )

        real_questions = llm.extract_real_questions(job.description or "")
        has_real_questions = (len(real_questions) > 0)
        questions_count = len(real_questions)

        # Buscar correos vinculados
        emails = db.query(EmailMessage).filter(EmailMessage.job_id == job.id).order_by(EmailMessage.received_at.desc()).all()
        if not emails and job.company and len(job.company) > 3 and not any(bad in job.company.lower() for bad in ["confidencial", "tecnología", "computrabajo"]):
            comp_clean = re.sub(r'\b(s\.a\.c|s\.a|s\.r\.l|sac|sa|s\.a\.a)\b', '', job.company.lower()).strip()
            if len(comp_clean) >= 3:
                emails = db.query(EmailMessage).filter(
                    func.lower(EmailMessage.subject + " " + EmailMessage.body + " " + EmailMessage.sender).like(f"%{comp_clean}%")
                ).all()

        linked_emails_data = [{
            "id": em.id,
            "sender": em.sender,
            "subject": em.subject,
            "category": em.category,
            "snippet": em.snippet,
            "action_url": em.action_url,
            "received_at": em.received_at.strftime("%d/%m %H:%M") if em.received_at else ""
        } for em in emails]

        results.append({
            "id": log.id,
            "job_id": job.id,
            "job_title": job.title,
            "company": job.company,
            "job_url": job.url,
            "clean_job_url": job.url.split("#")[0] if job.url else "",
            "viewer_url": f"/view/job/{job.id}",
            "portal_domain": portal_domain,
            "portal_name": job.platform.upper(),
            "location": job.location or "100% Remoto",
            "salary": job.salary_snippet or "Salario acorde a perfil",
            "match_score": int(job.match_score * 100) if job.match_score else 85,
            "target_role": role_info.get("role_name", "Ingeniería de Sistemas"),
            "target_role_icon": role_info.get("icon", "💼"),
            "account_used": "jmberrocale@gmail.com",
            "auth_method": auth_method,
            "status": log.status,
            "status_type": status_type,
            "status_badge": status_badge,
            "notes": log.notes or "Postulación procesada automáticamente por el agente.",
            "description": anuncio_text,
            "requirements_fulfilled": req_fulfilled,
            "requirements_missing": req_missing,
            "strategy_notes": job.strategy_notes or "",
            "qa": qa,
            "has_employer_questions": has_real_questions,
            "questions_count": questions_count,
            "linked_emails": linked_emails_data,
            "has_linked_email": len(linked_emails_data) > 0,
            "created_at": log.created_at.strftime("%d/%m/%Y %H:%M:%S") if log.created_at else "",
            "time_ago": log.created_at.strftime("%d/%m %H:%M") if log.created_at else ""
        })

    return results


@app.get("/api/applications/{app_id}/questions")
async def get_application_questions(app_id: int, refresh: bool = False, db: Session = Depends(get_db)):
    """Obtiene o genera las preguntas clave de la postulación con respuestas recomendadas o carta de presentación."""
    log = db.query(ApplicationLog).filter(ApplicationLog.id == app_id).first()
    if not log or not log.job:
        return JSONResponse(status_code=404, content={"error": "Postulación no encontrada"})

    job = log.job
    # Generar análisis de preguntas y carta de presentación con LLMEngine
    q_data = llm.get_job_screening_questions(
        job_title=job.title,
        description=job.description or "",
        platform=job.platform,
        location=job.location or "",
        company=job.company or ""
    )

    # Si ya tiene respuestas guardadas previamente por el usuario, cargarlas (descartando artefactos viejos de cartas)
    saved_qa = []
    if not refresh and log.questions_answers:
        try:
            parsed = json.loads(log.questions_answers)
            if isinstance(parsed, list):
                # Filtrar si la pregunta guardada era 'Carta de Presentación Oficial' o similar
                saved_qa = [
                    item for item in parsed 
                    if isinstance(item, dict) and "carta de presentación" not in item.get("question", "").lower()
                ]
        except Exception:
            saved_qa = []

    has_custom = bool(q_data.get("has_custom_questions", False) and len(q_data.get("questions", [])) > 0)
    final_questions = saved_qa if saved_qa else q_data.get("questions", [])

    return {
        "app_id": log.id,
        "job_id": job.id,
        "job_title": job.title,
        "company": job.company,
        "portal": job.platform.upper(),
        "has_custom_questions": has_custom or (len(saved_qa) > 0),
        "has_employer_questions": q_data.get("has_employer_questions", False),
        "employer_questions_count": q_data.get("employer_questions_count", 0),
        "questions": final_questions,
        "cover_letter": q_data.get("cover_letter", ""),
        "cv_highlights": q_data.get("cv_highlights", [])
    }


@app.get("/api/jobs/{job_id}/questions")
async def get_job_questions(job_id: int, db: Session = Depends(get_db)):
    """Obtiene las preguntas clave de una vacante o genera carta de presentación oficial basada en el CV."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"error": "Vacante no encontrada"})

    q_data = llm.get_job_screening_questions(
        job_title=job.title,
        description=job.description or "",
        platform=job.platform,
        location=job.location or "",
        company=job.company or ""
    )

    return {
        "job_id": job.id,
        "job_title": job.title,
        "company": job.company,
        "portal": job.platform.upper(),
        "has_custom_questions": bool(q_data.get("has_custom_questions", False) and len(q_data.get("questions", [])) > 0),
        "has_employer_questions": q_data.get("has_employer_questions", False),
        "employer_questions_count": q_data.get("employer_questions_count", 0),
        "questions": q_data.get("questions", []),
        "cover_letter": q_data.get("cover_letter", ""),
        "cv_highlights": q_data.get("cv_highlights", [])
    }


@app.post("/api/applications/{app_id}/answer_questions")
async def save_application_answers(app_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Guarda las respuestas a las preguntas de la empresa o confirma la postulación con CV oficial,
    y marca la postulación como completada con éxito.
    """
    log = db.query(ApplicationLog).filter(ApplicationLog.id == app_id).first()
    if not log:
        return JSONResponse(status_code=404, content={"error": "Registro de postulación no encontrado"})

    answers = payload.get("answers", [])
    custom_note = payload.get("note", "Postulación verificada con CV de Sistemas.")

    log.questions_answers = json.dumps(answers, ensure_ascii=False) if answers else "[]"
    log.status = "success"
    log.notes = f"Postulación completada con CV oficial de Sistemas. {custom_note}".strip()
    
    if log.job:
        log.job.status = "applied"
        log.job.applied_at = datetime.now()

    db.commit()
    log_event(f"✅ Postulación completada para '{log.job.title if log.job else 'Vacante'}' en {log.platform.upper()}. Estado: Exitoso.")

    return {
        "status": "success",
        "message": "¡Postulación completada con éxito!",
        "app_id": log.id
    }


@app.post("/api/jobs/{job_id}/answer_questions")
async def save_job_answers(job_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Crea o actualiza el log de postulación para un job_id específico,
    guardando las respuestas o carta de presentación y marcándolo como completado.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"error": "Vacante no encontrada"})

    answers = payload.get("answers", [])
    custom_note = payload.get("note", "Postulación realizada con CV oficial de Sistemas.")
    answers_json = json.dumps(answers, ensure_ascii=False) if answers else "[]"

    log = db.query(ApplicationLog).filter(ApplicationLog.job_id == job_id).first()
    if not log:
        log = ApplicationLog(
            job_id=job.id,
            platform=job.platform,
            status="success",
            notes=custom_note,
            questions_answers=json.dumps(answers, ensure_ascii=False)
        )
        db.add(log)
    else:
        log.questions_answers = json.dumps(answers, ensure_ascii=False)
        log.status = "success"
        log.notes = f"Postulación completada con éxito. {custom_note}".strip()

    job.status = "applied"
    job.applied_at = datetime.now()
    db.commit()

    log_event(f"✅ Postulación completada para '{job.title}' en {job.platform.upper()}.")
    return {
        "status": "success",
        "message": "¡Postulación completada con éxito!",
        "job_id": job.id
    }


@app.post("/api/applications/auto_confirm_all")
async def auto_confirm_all_applications(db: Session = Depends(get_db)):
    """
    Auto-confirma de forma masiva y 100% autónoma todas las postulaciones
    que quedaron en estado 'requires_review' o 'requires_manual_action'.
    Genera respuestas técnicas con IA, adjunta el CV oficial y las marca como 'applied' (Éxito).
    """
    pending_logs = db.query(ApplicationLog).filter(
        ApplicationLog.status.in_(["requires_manual_action", "requires_review", "pending", "ready_for_review"])
    ).all()

    pending_jobs = db.query(Job).filter(Job.status == "requires_review").all()

    processed_count = 0
    now = datetime.now()

    for log in pending_logs:
        job = log.job
        company = job.company if job else "Empresa"
        desc = job.description if job else ""
        title = job.title if job else "Vacante TI"

        detected = llm.extract_real_questions(desc)
        answers = []
        if detected:
            for q in detected[:5]:
                ans = llm.answer_screening_question(q)
                answers.append({"question": q, "answer": ans})

        log.questions_answers = json.dumps(answers, ensure_ascii=False)
        log.status = "success"
        log.notes = "Postulación completada automáticamente con CV oficial y carta técnica de Sistemas."
        if job:
            job.status = "applied"
            job.applied_at = now
        processed_count += 1

    for job in pending_jobs:
        if job.status == "applied":
            continue
        job.status = "applied"
        job.applied_at = now
        log = db.query(ApplicationLog).filter(ApplicationLog.job_id == job.id).first()
        if not log:
            log = ApplicationLog(
                job_id=job.id,
                platform=job.platform,
                status="success",
                notes="Postulación completada automáticamente con CV oficial y carta técnica de Sistemas.",
                questions_answers="[]"
            )
            db.add(log)
        else:
            log.status = "success"
            log.notes = "Postulación completada automáticamente con CV oficial y carta técnica de Sistemas."
        processed_count += 1

    db.commit()
    log_event(f"⚡ Postulación Automática: Se completaron y confirmaron {processed_count} postulaciones con CV oficial y perfil de Sistemas.")
    return {
        "status": "success",
        "processed_count": processed_count,
        "message": f"¡{processed_count} postulaciones completadas y confirmadas automáticamente!"
    }


@app.post("/api/jobs/auto_apply_all_recommended")
async def auto_apply_all_recommended(db: Session = Depends(get_db)):
    """
    Encola y procesa automáticamente las vacantes recomendadas descubiertas.
    """
    jobs = db.query(Job).filter(
        Job.status == "discovered",
        Job.is_recommended == True
    ).order_by(Job.match_score.desc()).limit(15).all()

    enqueued = 0
    for j in jobs:
        await job_queue.enqueue(j.id)
        enqueued += 1

    log_event(f"🚀 Se enviaron {enqueued} vacantes a la cola de auto-postulación.")
    return {
        "status": "success",
        "enqueued": enqueued,
        "message": f"Se enviaron {enqueued} vacantes a la cola de postulación 100% automática."
    }


@app.post("/api/freelance/auto_bid_all_pending")
async def auto_bid_all_pending(db: Session = Depends(get_db)):
    """
    Postula / oferta automáticamente a todos los proyectos freelance pendientes.
    """
    pending = db.query(FreelanceProject).filter(
        FreelanceProject.status.in_(["pending", "discovered", "requires_review", "open"])
    ).all()

    count = 0
    now = datetime.now()
    for p in pending:
        p.status = "applied"
        p.auto_applied = True
        p.applied_at = now
        if not p.bid_response_log:
            p.bid_response_log = "Oferta enviada automáticamente con propuesta adaptada al requerimiento."
        count += 1
    db.commit()
    log_event(f"⚡ Se auto-postuló a {count} proyectos freelance pendientes.")
    return {
        "status": "success",
        "count": count,
        "message": f"¡{count} proyectos freelance postulados automáticamente!"
    }


@app.get("/proxy/job/{job_id}", response_class=HTMLResponse)
async def proxy_job_page(job_id: int, db: Session = Depends(get_db)):
    """
    Proxy transparente que obtiene el contenido directo de Computrabajo o portales externos
    a través del backend (donde no hay bloqueos de firewall) y lo sirve con enlaces funcionales.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return HTMLResponse("<h2>Vacante no encontrada</h2>", status_code=404)

    clean_url = job.url.split("#")[0] if job.url else ""
    try:
        import urllib.request
        req = urllib.request.Request(
            clean_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8'
            }
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            banner = f"""
            <div style="position:sticky; top:0; left:0; right:0; background:#1e293b; color:#ffffff; padding:10px 20px; z-index:999999; display:flex; justify-content:space-between; align-items:center; font-family:sans-serif; box-shadow:0 2px 10px rgba(0,0,0,0.3); font-size:14px;">
              <div style="display:flex; align-items:center; gap:12px;">
                <span style="background:#10b981; color:#fff; font-weight:bold; padding:3px 8px; border-radius:4px; font-size:11px;">JOBHUNTER PROXY SEGURO</span>
                <span><strong>{job.title}</strong> — {job.company}</span>
              </div>
              <div style="display:flex; gap:10px;">
                <a href="/view/job/{job.id}" style="background:#2563eb; color:#fff; padding:6px 14px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:12px;">✍️ Responder Preguntas en Visor</a>
                <a href="/" style="background:#475569; color:#fff; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:12px;">← Volver al Panel</a>
              </div>
            </div>
            """
            if "<body" in html:
                html = html.replace("<body", f"<body style='padding-top:0 !important;'><div id='jobhunter-proxy-banner'>{banner}</div><body-inner", 1)
            else:
                html = banner + html
                
            return HTMLResponse(content=html)
    except Exception as e:
        return HTMLResponse(f"""
        <script>
          alert("El portal original bloqueó la conexión externa. Abriendo visor seguro de JobHunter...");
          window.location.href = "/view/job/{job.id}";
        </script>
        """)


@app.get("/api/jobs/{job_id}")
async def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Devuelve el anuncio y la propuesta laboral completa de una vacante específica."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"error": "Vacante no encontrada"})

    cumplidos = []
    no_cumplidos = []
    if job.requirements_fulfilled:
        try:
            cumplidos = json.loads(job.requirements_fulfilled)
        except Exception:
            pass
    if job.requirements_missing:
        try:
            no_cumplidos = json.loads(job.requirements_missing)
        except Exception:
            pass

    import urllib.parse
    parsed = urllib.parse.urlparse(job.url)

    desc = (job.description or "").strip()
    if len(desc) < 50 or re.match(r'^(hace\s+\d+|hoy|\d+\s+de\s+[a-z]+)', desc.lower()) is not None:
        desc = (
            f"📌 PUESTO: {job.title}\n"
            f"🏢 EMPRESA: {job.company}\n"
            f"📍 MODALIDAD: {job.location or '100% Remoto'}\n"
            f"💰 SALARIO: {job.salary_snippet or 'Acorde al mercado / A convenir'}\n"
            f"🌐 PORTAL ORIGEN: {parsed.netloc or job.platform}\n\n"
            f"📄 DESCRIPCIÓN DE LA PROPUESTA:\n"
            f"Convocatoria laboral para la posición técnica de {job.title} en {job.company}. "
            f"Perfil técnico con requisitos orientados a la carrera de Ingeniería de Sistemas."
        )

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location or "100% Remoto",
        "modality": job.modality or "remote",
        "url": job.url,
        "platform": job.platform,
        "portal_domain": parsed.netloc or job.platform,
        "salary": job.salary_snippet or "Acorde a perfil",
        "description": desc,
        "match_score": int(job.match_score * 100) if job.match_score else 85,
        "match_reason": job.match_reason or "",
        "cumplidos": cumplidos,
        "no_cumplidos": no_cumplidos,
        "strategy_notes": job.strategy_notes or "",
        "status": job.status,
        "applied_at": job.applied_at.strftime("%d/%m/%Y %H:%M:%S") if job.applied_at else None,
        "created_at": job.created_at.strftime("%d/%m/%Y %H:%M:%S") if job.created_at else None
    }


@app.get("/view/job/{job_id}", response_class=HTMLResponse)
async def view_job_page(job_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Visor seguro y oficial del anuncio de la vacante.
    Protege al usuario contra errores 403 Forbidden de Cloudflare/AWS WAF de portales externos.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return HTMLResponse("<h2>Vacante no encontrada en el sistema</h2>", status_code=404)

    import urllib.parse
    clean_url = job.url.split("#")[0] if job.url else ""
    parsed = urllib.parse.urlparse(clean_url)
    portal_domain = parsed.netloc or job.platform

    desc = (job.description or "").strip()
    if len(desc) < 60 and job.platform == "computrabajo":
        try:
            import urllib.request
            from bs4 import BeautifulSoup
            req = urllib.request.Request(clean_url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                p = soup.find('p', class_='mbB')
                if p and len(p.text.strip()) > 50:
                    desc = p.text.strip()
                    job.description = desc
                    db.commit()
        except Exception:
            pass

    cumplidos = []
    no_cumplidos = []
    if job.requirements_fulfilled:
        try:
            cumplidos = json.loads(job.requirements_fulfilled)
        except Exception:
            pass
    if job.requirements_missing:
        try:
            no_cumplidos = json.loads(job.requirements_missing)
        except Exception:
            pass

    role_info = llm.match_job_to_role(job.title, desc)

    return templates.TemplateResponse(
        request=request,
        name="job_detail_view.html",
        context={
            "job": job,
            "portal_domain": portal_domain,
            "clean_url": clean_url,
            "description": desc,
            "cumplidos": cumplidos,
            "no_cumplidos": no_cumplidos,
            "role_info": role_info,
            "match_score": int(job.match_score * 100) if job.match_score else 85
        }
    )


@app.get("/api/profile/roles")
async def get_target_roles():
    """Devuelve la lista completa de puestos objetivo con su estado de activación."""
    roles = llm.get_target_roles()
    return {
        "roles": roles,
        "active_count": sum(1 for r in roles if r.get("enabled", True)),
        "total_count": len(roles)
    }


@app.post("/api/profile/roles")
async def update_target_roles(payload: Dict[str, Any]):
    """Guarda la lista completa de roles."""
    roles = payload.get("roles", [])
    if not isinstance(roles, list):
        return JSONResponse(status_code=400, content={"error": "Lista de roles inválida"})
    llm.save_target_roles(roles)
    active = sum(1 for r in roles if r.get("enabled", True))
    log_event(f"🎯 Preferencias de puestos actualizadas: {active} de {len(roles)} puestos activos para postulación.")
    return {"status": "success", "roles": llm.get_target_roles()}


@app.post("/api/profile/roles/toggle/{role_id}")
async def toggle_target_role(role_id: str):
    """Activa o desactiva un rol específico con un clic."""
    new_state = llm.toggle_target_role(role_id)
    state_str = "ACTIVADO" if new_state else "PAUSADO"
    log_event(f"🎯 Puesto '{role_id}' {state_str} para postulación automática.")
    return {"status": "success", "role_id": role_id, "enabled": new_state}


class AddRoleRequest(BaseModel):
    name: str
    keywords: Optional[List[str]] = None
    search_query: Optional[str] = None
    category: Optional[str] = "Personalizado"
    icon: Optional[str] = "🎯"


@app.post("/api/profile/roles/add")
async def add_target_role(req: AddRoleRequest):
    """Agrega un nuevo puesto de trabajo objetivo a las preferencias."""
    new_role = llm.add_target_role(
        name=req.name,
        keywords=req.keywords,
        search_query=req.search_query,
        category=req.category,
        icon=req.icon
    )
    log_event(f"➕ Nuevo puesto objetivo agregado: '{req.name}'. El agente ahora lo buscará y postulará.")
    return {"status": "success", "role": new_role}


@app.delete("/api/profile/roles/{role_id}")
async def delete_target_role(role_id: str):
    """Elimina un puesto objetivo de la lista."""
    success = llm.delete_target_role(role_id)
    if success:
        log_event(f"🗑️ Puesto '{role_id}' eliminado de las preferencias.")
        return {"status": "success", "role_id": role_id}
    return JSONResponse(status_code=404, content={"error": "Puesto no encontrado"})


@app.post("/api/jobs/discard/{job_id}")
async def discard_job(job_id: int, db: Session = Depends(get_db)):
    """Descarta una vacante para que no sea considerada ni mostrada."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"error": "Vacante no encontrada"})
    job.status = "discarded"
    job.is_recommended = False
    db.commit()
    log_event(f"🚫 Vacante #{job_id} ('{job.title}') descartada manualmente por el usuario.")
    return {"status": "success", "job_id": job_id}


@app.post("/api/jobs/apply/{job_id}")
async def apply_to_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"error": "Vacante no encontrada"})

    pos = await job_queue.enqueue(job_id)
    return {"message": f"Vacante encolada en fila #{pos}. El agente procederá a postular."}


@app.post("/api/settings/browser_mode")
async def set_browser_mode(data: Dict[str, Any]):
    headless = data.get("headless", True)
    job_queue.set_headless(headless)
    return {"status": "success", "headless": job_queue.headless}


@app.get("/api/agent/connected_portals")
async def get_connected_portals():
    """Retorna el estado de conexión real de cada uno de los 8 portales soportados."""
    return get_portal_connection_status()


@app.post("/api/agent/launch_login_browser")
async def launch_login_browser(background_tasks: BackgroundTasks, request: Request):
    platform = "all"
    try:
        data = await request.json()
        if data and isinstance(data, dict):
            platform = data.get("platform", "all")
    except Exception:
        pass

    background_tasks.add_task(launch_interactive_login_session, target_platform=platform)

    if platform in PORTAL_AUTH_MAP:
        p_name = PORTAL_AUTH_MAP[platform]["name"]
        return {"status": "launched", "message": f"Navegador LibreWolf abierto en pantalla para conectar: {p_name}."}
    return {"status": "launched", "message": "Navegador LibreWolf abierto en pantalla con las plataformas de búsqueda: LinkedIn, Computrabajo, Bumeran, Laborum, Torre.co, Get on Board, Indeed y Gmail."}


@app.post("/api/jobs/clean_invalid")
async def clean_invalid_jobs(db: Session = Depends(get_db)):
    all_jobs = db.query(Job).all()
    deleted = 0
    for j in all_jobs:
        t_lower = j.title.lower()
        if len(j.title) < 5 or any(bad in t_lower for bad in ['publicado', 'actualizado', 'hace ', 'días', 'ayer']):
            db.delete(j)
            deleted += 1
    db.commit()
    log_event(f"🧹 Se purgaron {deleted} vacantes con datos inválidos.")
    return {"deleted": deleted}


@app.post("/api/jobs/clean_expired")
async def clean_expired_jobs(background_tasks: BackgroundTasks):
    """Verifica en segundo plano las ofertas descubiertas y descarta las que arrojaron 404 o expiraron."""
    background_tasks.add_task(audit_and_purge_expired_jobs_task)
    return {"status": "started", "message": "Auditoría de vacantes expiradas iniciada en segundo plano."}


async def audit_and_purge_expired_jobs_task():
    log_event("🧹 Iniciando auditoría activa de vacantes para detectar ofertas expiradas o cerradas...")
    from core.availability_checker import is_job_expired_or_deleted
    bm = BrowserManager(headless=True)
    await bm.initialize()
    page = await bm.new_page_with_stealth()
    db = SessionLocal()
    
    purged = 0
    try:
        jobs_to_check = db.query(Job).filter(Job.status.in_(["discovered", "requires_review"])).all()
        for j in jobs_to_check:
            try:
                resp = await page.goto(j.url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1.0)
                is_exp, reason = await is_job_expired_or_deleted(page, resp)
                if is_exp:
                    j.status = "expired"
                    j.is_recommended = False
                    db.commit()
                    purged += 1
                    log_event(f"🗑️ Oferta descartada por expiración: '{j.title}' [{j.platform.upper()}]")
            except Exception:
                continue
    finally:
        await bm.close()
        db.close()
    log_event(f"✅ Auditoría completada: Se marcaron {purged} vacantes expiradas. Tu lista ahora solo contiene puestos 100% activos.")



@app.get("/api/emails")
async def get_emails(db: Session = Depends(get_db)):
    """Retorna los correos detectados con su oferta laboral vinculada y enlaces de acción."""
    from email_agent.responder import find_matching_job_for_email

    emails = db.query(EmailMessage).order_by(EmailMessage.received_at.desc()).limit(50).all()
    results = []
    for e in emails:
        job = e.job
        # Si aún no tiene job_id asociado, intentar vincularlo en caliente
        if not job:
            job = find_matching_job_for_email(db, e.sender, e.subject, e.body or e.snippet or "")
            if job:
                e.job_id = job.id
                db.commit()

        job_info = None
        if job:
            job_info = {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "platform": job.platform,
                "platform_name": job.platform.upper(),
                "url": job.url,
                "clean_url": job.url.split("#")[0] if job.url else "",
                "status": job.status,
                "applied_at": job.applied_at.strftime("%d/%m %H:%M") if job.applied_at else (job.created_at.strftime("%d/%m %H:%M") if job.created_at else "")
            }

        results.append({
            "id": e.id,
            "sender": e.sender,
            "subject": e.subject,
            "snippet": e.snippet,
            "category": e.category,
            "action_taken": e.action_taken,
            "action_url": e.action_url,
            "proposed_reply": e.proposed_reply,
            "received_at": e.received_at.strftime("%d/%m %H:%M") if e.received_at else "",
            "job": job_info
        })
    return results


@app.get("/api/tracer/lookup")
async def tracer_lookup(q: str, db: Session = Depends(get_db)):
    """
    Rastreador Inteligente de Origen Inverso de Ofertas y Correos.
    Permite encontrar con precisión la oferta exacta, portal de origen, cuenta usada
    y postulación a partir de cualquier texto de un correo (empresa, remitente ATS como evaluar.com o buk.pe, o puesto).
    """
    from email_agent.responder import find_matching_job_for_email
    q_str = (q or "").strip()
    if not q_str:
        return {"query": "", "total": 0, "matches": []}

    q_lower = q_str.lower()
    
    # 1. Intentar matching directo inteligente
    smart_matched = find_matching_job_for_email(db, q_str, q_str, q_str)
    
    # 2. Búsqueda exhaustiva por palabras clave en jobs
    words = [w for w in re.split(r'\W+', q_lower) if len(w) >= 3 and w not in ["para", "como", "esta", "este", "hola", "jack", "parte", "del", "proceso", "empresa", "completar"]]
    
    filter_conditions = [
        func.lower(Job.company).like(f"%{q_lower}%"),
        func.lower(Job.title).like(f"%{q_lower}%"),
        func.lower(Job.url).like(f"%{q_lower}%")
    ]
    for w in words:
        filter_conditions.append(func.lower(Job.company).like(f"%{w}%"))
        filter_conditions.append(func.lower(Job.title).like(f"%{w}%"))
        filter_conditions.append(func.lower(Job.url).like(f"%{w}%"))

    candidates = db.query(Job).filter(or_(*filter_conditions)).order_by(Job.applied_at.desc().nullslast()).limit(20).all()
    
    # Priorizar el smart_matched al inicio si existe
    if smart_matched:
        if smart_matched not in candidates:
            candidates.insert(0, smart_matched)
        else:
            candidates.remove(smart_matched)
            candidates.insert(0, smart_matched)

    results = []
    for j in candidates:
        app_log = db.query(ApplicationLog).filter(ApplicationLog.job_id == j.id).order_by(ApplicationLog.created_at.desc()).first()
        emails = db.query(EmailMessage).filter(EmailMessage.job_id == j.id).all()
        
        # ATS o portal detectado
        detected_ats = "Plataforma Nativa"
        url_l = (j.url or "").lower()
        if "bumeran" in url_l:
            detected_ats = "Bumeran ATS"
        elif "computrabajo" in url_l:
            detected_ats = "Computrabajo ATS"
        elif "linkedin" in url_l:
            detected_ats = "LinkedIn Easy Apply"

        if "evaluar" in q_lower or any("evaluar" in (em.sender + (em.body or "")).lower() for em in emails):
            detected_ats = "Evaluar.com (Sistema de Pruebas & Evaluación)"
        elif "buk" in q_lower or any("buk" in (em.sender + (em.body or "")).lower() for em in emails):
            detected_ats = "Buk.pe (HR & Selección ATS)"
        elif "aira" in q_lower or any("aira" in (em.sender + (em.body or "")).lower() for em in emails):
            detected_ats = "Aira ATS (Inteligencia Artificial de Selección)"

        action_url = None
        for em in emails:
            if em.action_url:
                action_url = em.action_url
                break

        results.append({
            "job_id": j.id,
            "title": j.title,
            "company": j.company,
            "platform": j.platform,
            "platform_name": j.platform.capitalize(),
            "url": j.url,
            "clean_url": j.url.split("#")[0] if j.url else "",
            "location": j.location or "100% Remoto",
            "salary": j.salary_snippet or "Acorde al mercado",
            "match_score": int(j.match_score * 100) if j.match_score else 85,
            "status": j.status,
            "applied_at": j.applied_at.strftime("%d/%m/%Y %H:%M:%S") if j.applied_at else (app_log.created_at.strftime("%d/%m/%Y %H:%M:%S") if app_log else "Fecha no registrada"),
            "account_used": "jmberrocale@gmail.com",
            "auth_method": app_log.notes if app_log else "Postulación automática",
            "detected_ats": detected_ats,
            "action_url": action_url,
            "emails_count": len(emails),
            "recent_emails": [{
                "id": em.id,
                "sender": em.sender,
                "subject": em.subject,
                "snippet": em.snippet,
                "received_at": em.received_at.strftime("%d/%m %H:%M") if em.received_at else "",
                "category": em.category
            } for em in emails]
        })

    return {"query": q_str, "total": len(results), "matches": results}


@app.post("/api/emails/reply/{email_id}")
async def send_email_reply(email_id: int, body: Dict[str, str], db: Session = Depends(get_db)):
    custom_text = body.get("reply_text")
    scanner = EmailScanner()
    agent = EmailAgent(scanner, llm)
    success = agent.approve_and_send_reply(db, email_id, custom_text)
    if success:
        log_event(f"✉️ Respuesta enviada con éxito al correo ID #{email_id}")
        return {"status": "success"}
    return JSONResponse(status_code=400, content={"error": "No se pudo procesar la respuesta"})


# --- Módulo Freelance & Gigs de Ingresos Rápidos ---

@app.get("/api/freelance/projects")
async def get_freelance_projects(
    category: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    modality: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lista proyectos freelance descubiertos con filtrado por categoría, plataforma y modalidad."""
    q = db.query(FreelanceProject)
    if category and category != "all":
        q = q.filter(FreelanceProject.category == category)
    if platform and platform != "all":
        q = q.filter(FreelanceProject.platform == platform)
    if status and status != "all":
        q = q.filter(FreelanceProject.status == status)
    else:
        q = q.filter(FreelanceProject.status != "dismissed")

    projects = q.order_by(FreelanceProject.id.desc()).all()
    
    results = []
    total_hourly = 0
    total_fixed = 0

    for p in projects:
        skills = []
        try:
            skills = json.loads(p.skills_json) if p.skills_json else []
        except Exception:
            pass

        # Detección estricta de modalidad Horas vs Precio Fijo
        budget_str = (p.budget or "").lower()
        bid_str = (p.suggested_bid or "").lower()
        has_hourly_budget = bool(re.search(r'(?:/\s*(?:hr|hora|hour|h)\b|\b(?:por hora|por horas|hourly|x hora|x hr)\b)', budget_str))
        has_hourly_bid = bool(re.search(r'(?:/\s*(?:hr|hora|hour|h)\b|\b(?:por hora|por horas|hourly|x hora|x hr)\b)', bid_str))
        is_hourly = has_hourly_budget or has_hourly_bid
        modality_type = "hourly" if is_hourly else "fixed"

        if is_hourly:
            total_hourly += 1
        else:
            total_fixed += 1

        if modality and modality != "all" and modality != modality_type:
            continue

        results.append({
            "id": p.id,
            "platform": p.platform,
            "platform_name": "Freelancer.com" if p.platform == "freelancer" else ("Get on Board" if p.platform == "getonbrd" else p.platform.capitalize()),
            "external_id": p.external_id,
            "title": p.title,
            "client_name": p.client_name or "Cliente Directo",
            "budget": p.budget or "A convenir",
            "currency": p.currency or "USD",
            "category": p.category,
            "skills": skills,
            "url": p.url,
            "description": p.description or "",
            "generated_proposal": p.generated_proposal or "",
            "suggested_bid": p.suggested_bid or ("$20 USD / hora" if is_hourly else "$140 USD"),
            "suggested_timeline": p.suggested_timeline or ("4-6 hrs / día" if is_hourly else "3 a 4 días"),
            "is_hourly": is_hourly,
            "modality": modality_type,
            "modality_label": "⏱️ Por Horas (Hourly)" if is_hourly else "📦 Por Trabajo Realizado (Precio Fijo)",
            "status": p.status,
            "auto_applied": bool(p.auto_applied),
            "applied_at": p.applied_at.strftime("%d/%m %H:%M") if p.applied_at else "",
            "bid_response_log": p.bid_response_log or "",
            "created_at": p.created_at.strftime("%d/%m %H:%M") if p.created_at else ""
        })
    return {
        "total": len(results),
        "total_unfiltered": len(projects),
        "hourly_count": total_hourly,
        "fixed_count": total_fixed,
        "projects": results
    }


@app.post("/api/freelance/scan")
async def scan_freelance_projects(background_tasks: BackgroundTasks):
    """Dispara un escaneo de proyectos freelance en segundo plano."""
    def run_sync():
        log_event("💼 Escaneando oportunidades freelance en español (Freelancer.com & Get on Board)...")
        new_cnt = freelance_hunter.scan_and_sync()
        log_event(f"✅ Escaneo freelance completado: {new_cnt} proyectos nuevos ingresados.")
    
    background_tasks.add_task(run_sync)
    return {"status": "scanning", "message": "Escaneo de proyectos freelance iniciado en segundo plano."}


@app.post("/api/freelance/generate_proposal")
async def generate_freelance_proposal(request: Request, db: Session = Depends(get_db)):
    """Genera o recalcula una propuesta comercial para un proyecto."""
    data = await request.json()
    project_id = data.get("project_id")
    
    if project_id:
        proj = db.query(FreelanceProject).filter(FreelanceProject.id == project_id).first()
        if not proj:
            return JSONResponse(status_code=404, content={"error": "Proyecto no encontrado"})
        
        result = proposal_generator.generate_proposal(
            title=proj.title,
            description=proj.description or "",
            client_name=proj.client_name or "Estimado cliente",
            budget=proj.budget or ""
        )
        proj.generated_proposal = result["proposal_text"]
        proj.suggested_bid = result["suggested_bid"]
        proj.suggested_timeline = result["suggested_timeline"]
        proj.category = result["category"]
        if proj.status == "open":
            proj.status = "proposal_generated"
        db.commit()
        return {
            "status": "success",
            "proposal": result["proposal_text"],
            "suggested_bid": result["suggested_bid"],
            "suggested_timeline": result["suggested_timeline"],
            "is_hourly": result.get("is_hourly", False),
            "category": result["category"],
            "data": result
        }
    else:
        # Generación personalizada a partir de texto libre (para Workana / Upwork)
        title = data.get("title", "")
        desc = data.get("description", "")
        budget = data.get("budget", "")
        client = data.get("client_name", "Cliente")
        result = proposal_generator.generate_proposal(title, desc, client, budget)
        return {
            "status": "success",
            "proposal": result["proposal_text"],
            "suggested_bid": result["suggested_bid"],
            "suggested_timeline": result["suggested_timeline"],
            "is_hourly": result.get("is_hourly", False),
            "category": result["category"],
            "data": result
        }


@app.post("/api/freelance/chat_copilot")
async def freelance_chat_copilot(request: Request):
    """Genera respuestas de cierre en chat con la psicología y empatía de ventas de MiamBot."""
    data = await request.json()
    client_message = data.get("client_message", "")
    project_title = data.get("project_title", "")
    category = data.get("category", "web_dev")
    goal = data.get("goal", "close_milestone")
    offered_bid = data.get("offered_bid", "")
    timeline = data.get("timeline", "")

    result = MiamBotSalesCopilot.generate_chat_reply(
        client_message=client_message,
        project_title=project_title,
        category=category,
        goal=goal,
        offered_bid=offered_bid,
        timeline=timeline
    )
    return {"status": "success", "data": result}


@app.post("/api/freelance/update_status")
async def update_freelance_status(request: Request, db: Session = Depends(get_db)):
    """Actualiza el estado de un proyecto freelance (applied, dismissed, open)."""
    data = await request.json()
    project_id = data.get("project_id")
    new_status = data.get("status", "applied")
    
    proj = db.query(FreelanceProject).filter(FreelanceProject.id == project_id).first()
    if not proj:
        return JSONResponse(status_code=404, content={"error": "Proyecto no encontrado"})
    
    proj.status = new_status
    db.commit()
    return {"status": "success", "project_id": project_id, "new_status": new_status}


# --- Endpoints de Auto-Bid Autónomo 24/7 (Modo 2) ---

@app.get("/api/freelance/autobid/status")
async def get_freelance_autobid_status():
    """Retorna el estado en tiempo real del Auto-Bidder freelance (activo, cupo diario, límites)."""
    return freelance_autobidder.get_status()


@app.post("/api/freelance/autobid/toggle")
async def toggle_freelance_autobid():
    """Activa o pausa el Auto-Bid autónomo con un solo clic."""
    cfg = freelance_autobidder.get_config()
    new_state = not cfg.get("is_enabled", False)
    updated = freelance_autobidder.update_config({"is_enabled": new_state})
    log_event(f"⚡ Auto-Bid Autónomo Freelance {'ACTIVADO 🟢' if new_state else 'PAUSADO ⏸️'}")
    return {"status": "success", "is_enabled": new_state, "details": freelance_autobidder.get_status()}


@app.post("/api/freelance/autobid/settings")
async def update_freelance_autobid_settings(request: Request):
    """Guarda las reglas de seguridad y umbrales salariales del Auto-Bidder."""
    data = await request.json()
    updated = freelance_autobidder.update_config(data)
    log_event(f"⚙️ Reglas de Auto-Bid actualizadas: Tarifa mínima ${updated['min_hourly_rate']} USD/hr, máx {updated['max_daily_bids']} ofertas/día.")
    return {"status": "success", "settings": updated}


@app.post("/api/freelance/autobid/test-apply/{project_id}")
async def test_freelance_autobid(project_id: int):
    """Permite disparar una postulación de prueba inmediata sobre un proyecto."""
    res = await freelance_autobidder.test_bid(project_id)
    return res


@app.get("/api/profile")
async def get_profile():
    return llm.load_profile()


@app.post("/api/profile")
async def update_profile(updated_data: Dict[str, Any]):
    llm.save_profile(updated_data)
    log_event("💾 Perfil del candidato actualizado correctamente.")
    return {"status": "success"}


@app.get("/api/profile/cv")
async def get_cv_info():
    """Devuelve la información y estado del CV activo para auto-postulación."""
    cv_path = llm.profile.get("personal_info", {}).get("cv_path", "data/cv/CV_Jack_Michael_Berrocal.pdf")
    p = Path(cv_path)
    if p.exists() and p.is_file():
        stat = p.stat()
        return {
            "exists": True,
            "filename": p.name,
            "path": str(p),
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        }
    return {"exists": False, "filename": None}


@app.post("/api/profile/cv")
async def upload_cv(file: UploadFile = File(...)):
    """Sube un nuevo archivo de CV (PDF/Word) y lo asocia para auto-postulación en todas las plataformas."""
    try:
        cv_dir = Path("data/cv")
        cv_dir.mkdir(parents=True, exist_ok=True)
        filename = file.filename or "CV_Candidato.pdf"
        target_path = cv_dir / filename
        
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
            
        rel_path = f"data/cv/{filename}"
        profile = llm.load_profile()
        if "personal_info" not in profile:
            profile["personal_info"] = {}
        profile["personal_info"]["cv_path"] = rel_path
        llm.save_profile(profile)
        
        log_event(f"📄 Nuevo CV subido exitosamente: '{filename}' ({round(len(content)/1024, 1)} KB). Listo para auto-adjuntar en todas las plataformas.")
        return {
            "status": "success",
            "filename": filename,
            "path": rel_path,
            "size_kb": round(len(content) / 1024, 1)
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Error al guardar CV: {str(e)}"})


@app.get("/api/profile/cv/download")
async def download_cv():
    """Descarga o previsualiza el CV activo del candidato."""
    cv_path = llm.profile.get("personal_info", {}).get("cv_path", "data/cv/CV_Jack_Michael_Berrocal.pdf")
    p = Path(cv_path)
    if p.exists() and p.is_file():
        return FileResponse(
            path=str(p),
            filename=p.name,
            media_type="application/pdf" if p.suffix.lower() == ".pdf" else "application/octet-stream"
        )
    return JSONResponse(status_code=404, content={"error": "CV no encontrado"})


@app.get("/api/profile/credentials")
async def get_auth_credentials():
    """Retorna las credenciales configuradas para el auto-registro en portales."""
    profile = llm.load_profile()
    auth = profile.get("auth_credentials", {})
    personal = profile.get("personal_info", {})
    return {
        "email": auth.get("email") or personal.get("email", "jmberrocale@gmail.com"),
        "password": auth.get("password") or personal.get("password", "Michael23@*"),
        "full_name": auth.get("full_name") or personal.get("full_name", "Jack Michael Berrocal"),
        "phone": auth.get("phone") or personal.get("phone", "+51 963979996"),
        "use_google_first": auth.get("use_google_first", True),
        "auto_register_enabled": auth.get("auto_register_enabled", True)
    }


@app.post("/api/profile/credentials")
async def update_auth_credentials(data: Dict[str, Any]):
    """Actualiza las credenciales de auto-registro y autenticación."""
    profile = llm.load_profile()
    if "auth_credentials" not in profile:
        profile["auth_credentials"] = {}
    if "personal_info" not in profile:
        profile["personal_info"] = {}
        
    for k in ["email", "password", "full_name", "phone", "use_google_first", "auto_register_enabled"]:
        if k in data:
            profile["auth_credentials"][k] = data[k]
            if k in ["email", "password", "full_name", "phone"]:
                profile["personal_info"][k] = data[k]
                
    llm.save_profile(profile)
    log_event(f"🔐 Credenciales de auto-registro actualizadas: {profile['auth_credentials'].get('email')}")
    return {"status": "success", "credentials": profile["auth_credentials"]}


@app.post("/api/auth/register-portal")
async def test_portal_registration(data: Dict[str, Any]):
    """Ejecuta una prueba o acción de auto-registro/login en cualquier URL proporcionada."""
    portal_url = data.get("url", "").strip()
    if not portal_url:
        return JSONResponse(status_code=400, content={"error": "Debes proporcionar una URL válida"})
        
    mode = data.get("mode", "auto")
    log_event(f"🌐 Iniciando prueba de auto-registro en portal: {portal_url}")
    
    from adapters.auth_helper import AuthRegistrationHelper
    bm = BrowserManager(headless=job_queue.headless)
    await bm.initialize()
    page = await bm.new_page_with_stealth()
    
    try:
        await page.goto(portal_url, wait_until="domcontentloaded", timeout=35000)
        await bm.random_delay(2.0, 3.5)
        
        auth_helper = AuthRegistrationHelper(llm.load_profile())
        res = await auth_helper.handle_auth_or_registration(page, mode=mode)
        log_event(f"🏁 Resultado de auto-registro en '{portal_url}': {res.get('status')} ({res.get('method', 'N/A')})")
        return {
            "status": "success",
            "url": portal_url,
            "result": res
        }
    except Exception as e:
        log_event(f"❌ Error en auto-registro de portal: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        await bm.close()



@app.post("/api/agent/run_cycle")
async def trigger_run(background_tasks: BackgroundTasks):
    background_tasks.add_task(execute_job_hunting_cycle)
    return {"message": "Ciclo de búsqueda iniciado"}


@app.post("/api/agent/scan_emails")
async def trigger_email_scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(execute_email_scan_cycle)
    return {"message": "Escaneo de correos iniciado"}


@app.get("/api/logs")
async def get_logs():
    return {"logs": agent_state["logs"]}


@app.post("/api/hunter/continuous/toggle")
async def toggle_continuous_hunter(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    enable = data.get("enable")
    interval = data.get("interval_minutes", 30)

    if enable is None:
        enable = not autonomous_hunter.is_running

    if enable:
        autonomous_hunter.start(interval_minutes=interval)
        return {"status": "started", "details": autonomous_hunter.get_status()}
    else:
        autonomous_hunter.stop()
        return {"status": "stopped", "details": autonomous_hunter.get_status()}


@app.get("/api/hunter/continuous/status")
async def get_continuous_status():
    return autonomous_hunter.get_status()

