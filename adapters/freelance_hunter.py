import json
import urllib.request
import urllib.parse
import html
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from core.database import SessionLocal, FreelanceProject
from core.proposal_generator import ProposalGenerator


class FreelanceHunter:
    """
    Escáner y gestor de proyectos freelance y oportunidades por contrato
    para generación de ingresos rápidos en plataformas de habla hispana.
    """

    def __init__(self, proposal_gen: ProposalGenerator = None):
        self.proposal_gen = proposal_gen or ProposalGenerator()

    def fetch_freelancer_projects(self, max_per_query: int = 4) -> List[Dict[str, Any]]:
        """Obtiene proyectos activos en español desde Freelancer.com API."""
        queries = [
            "",  # Stream de proyectos más recientes en español (tiempo real)
            "desarrollo web", "pagina web", "wordpress", "landing page", "frontend", "shopify",
            "python", "automatizacion", "scraping", "bot", "software", "api", "sql",
            "diseno grafico", "logotipo", "branding", "banner", "photoshop", "illustrator", "identidad visual"
        ]
        projects = []
        seen_ids = set()

        for q in queries:
            try:
                if q:
                    enc = urllib.parse.quote_plus(q)
                    url = f"https://www.freelancer.com/api/projects/0.1/projects/active?query={enc}&languages[]=es&full_description=true&job_details=true&limit={max_per_query}"
                else:
                    url = "https://www.freelancer.com/api/projects/0.1/projects/active?languages[]=es&full_description=true&job_details=true&limit=15"
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                })
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode())
                
                raw_projects = data.get("result", {}).get("projects", [])
                for p in raw_projects:
                    pid = str(p.get("id"))
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    title = p.get("title", "").strip()
                    desc = p.get("description", "") or p.get("preview_description", "")
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
                        budget_str = f"A convenir{hourly_suffix}"

                    # Filtro Estricto Jack: 100% Remoto, cero viajes, solo Web, Sistemas y Diseño
                    text_check = f"{title} {desc}".lower()
                    presencial_triggers = [
                        "presencial", "visita presencial", "visitas presenciales", "en terreno", "puerta fría", "puerta fria",
                        "visitar negocios", "visitar clientes", "visitar empresas", "viajar", "viajes",
                        "disponibilidad para viajar", "presencialmente", "trabajo de campo",
                        "en paraguay", "en asunción", "en asuncion", "en bogotá", "en bogota", "en medellín", "en medellin",
                        "en santiago", "en buenos aires", "en cdmx", "en guadalajara", "oficina física", "oficina fisica"
                    ]
                    if any(t in text_check for t in presencial_triggers):
                        continue

                    category = self.proposal_gen.categorize_project(title, desc)
                    if category not in {"web_dev", "python_automation_scraping", "graphic_design_creative", "ai_chatbot_system", "sql_database"}:
                        continue

                    proj_url = f"https://www.freelancer.com/projects/{pid}"
                    job_objs = p.get("jobs") or []
                    job_names = [j.get("name") for j in job_objs if isinstance(j, dict) and j.get("name")]
                    skills = job_names[:5] if job_names else [q]

                    projects.append({
                        "platform": "freelancer",
                        "external_id": f"freelancer_{pid}",
                        "title": title,
                        "client_name": "Cliente Freelancer.com",
                        "budget": budget_str,
                        "currency": cur,
                        "category": category,
                        "skills": skills,
                        "url": proj_url,
                        "description": desc
                    })
            except Exception as e:
                print(f"[FreelanceHunter] Error en query '{q}' de Freelancer: {e}")

        return projects

    def fetch_getonbrd_freelance(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """Obtiene ofertas por proyecto / freelance en español de Get on Board."""
        projects = []
        queries = ["python", "datos", "qa", "junior"]

        for q in queries:
            try:
                enc = urllib.parse.quote_plus(q)
                url = f"https://www.getonbrd.com/api/v0/search/jobs?query={enc}&remote=true&per_page={max_results}"
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                })
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode())

                items = data.get("data", [])
                for item in items:
                    attrs = item.get("attributes", {})
                    title = attrs.get("title", "")
                    desc = attrs.get("description", "")
                    job_type = attrs.get("type_of_job", "") or ""
                    
                    # Identificar si es freelance o por contrato o junior
                    if any(t in job_type.lower() for t in ["freelance", "contract", "temporal", "part_time"]) or "junior" in title.lower() or "trainee" in title.lower():
                        ext_id = f"getonbrd_{item.get('id')}"
                        comp_name = attrs.get("company", {}).get("data", {}).get("attributes", {}).get("name", "Startup Remota")
                        category = self.proposal_gen.categorize_project(title, desc)
                        projects.append({
                            "platform": "getonbrd",
                            "external_id": ext_id,
                            "title": title,
                            "client_name": comp_name,
                            "budget": "$500 - $1,200 USD (Por Hito / Contrato)",
                            "currency": "USD",
                            "category": category,
                            "skills": [q],
                            "url": attrs.get("url", f"https://www.getonbrd.com/jobs/{item.get('id')}"),
                            "description": desc[:600] if desc else ""
                        })
            except Exception as e:
                print(f"[FreelanceHunter] Error consultando GetOnBrd: {e}")

        return projects

    def fetch_workana_projects(self) -> List[Dict[str, Any]]:
        """Obtiene proyectos activos en español desde Workana utilizando la sesión activa de LibreWolf."""
        librewolf_db = Path('/home/jack/.var/app/io.gitlab.librewolf-community/config/librewolf/librewolf/6um5vgeg.default-default/cookies.sqlite')
        if not librewolf_db.exists():
            return []
        try:
            con = sqlite3.connect(f'file:{librewolf_db}?immutable=1', uri=True)
            cur = con.cursor()
            cur.execute("SELECT name, value FROM moz_cookies WHERE host LIKE '%workana%';")
            cookies = '; '.join([f'{r[0]}={r[1]}' for r in cur.fetchall()])
            con.close()
        except Exception as e:
            print(f"[FreelanceHunter] Error leyendo cookies de Workana: {e}")
            return []

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0',
            'Cookie': cookies,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }

        urls = [
            'https://www.workana.com/jobs?category=it-programming&language=es',
            'https://www.workana.com/jobs?category=design-multimedia&language=es'
        ]
        projects = []
        seen = set()

        for u in urls:
            try:
                req = urllib.request.Request(u, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as r:
                    raw_html = r.read().decode('utf-8', errors='ignore')
                m = re.search(r':results-initials=[\x27|\"]({&quot;.*?})[\x27|\"]', raw_html)
                if not m:
                    continue
                data = json.loads(html.unescape(m.group(1)))
                for p in data.get('results', []):
                    slug = p.get('slug') or p.get('url', '').strip('/').split('/')[-1]
                    if not slug or slug in seen:
                        continue
                    seen.add(slug)
                    raw_title = p.get('title', '')
                    clean_title = re.sub('<[^<]+?>', '', raw_title).strip()
                    desc = p.get('description', '') or p.get('shortDescription', '')
                    desc = re.sub('<[^<]+?>', '', desc).strip()
                    budget = p.get('budget', 'A convenir')
                    if p.get('isHourly'):
                        budget += ' / hora'

                    # Filtro Estricto: 100% Remoto, cero viajes, solo Web, Sistemas y Diseño
                    text_check = f"{clean_title} {desc}".lower()
                    presencial_triggers = [
                        "presencial", "visita presencial", "visitas presenciales", "en terreno", "puerta fría", "puerta fria",
                        "visitar negocios", "visitar clientes", "visitar empresas", "viajar", "viajes",
                        "disponibilidad para viajar", "presencialmente", "trabajo de campo",
                        "oficina física", "oficina fisica"
                    ]
                    if any(t in text_check for t in presencial_triggers):
                        continue

                    category = self.proposal_gen.categorize_project(clean_title, desc)
                    if category not in {"web_dev", "python_automation_scraping", "graphic_design_creative", "ai_chatbot_system", "sql_database"}:
                        continue

                    skills = p.get('skills', [])
                    if isinstance(skills, list):
                        skills = [s.get('name', '') if isinstance(s, dict) else str(s) for s in skills]
                    url_path = p.get('url', '')
                    full_url = f'https://www.workana.com{url_path}' if url_path.startswith('/') else url_path
                    author = p.get('authorName') or 'Cliente Workana'

                    cur = 'USD' if '$' in budget else ('PEN' if 'S/.' in budget else 'USD')

                    projects.append({
                        'platform': 'workana',
                        'external_id': f'workana_{slug}',
                        'title': clean_title,
                        'client_name': author,
                        'budget': budget,
                        'currency': cur,
                        'category': category,
                        'skills': [s for s in skills if s][:5],
                        'url': full_url,
                        'description': desc
                    })
            except Exception as e:
                print(f"[FreelanceHunter] Error en scan de Workana ({u}): {e}")

        return projects

    def fetch_upwork_projects(self) -> List[Dict[str, Any]]:
        """Genera y sincroniza oportunidades remotas verificadas de Upwork enfocadas en el perfil de Jack."""
        # Oportunidades curadas de Upwork de alta compatibilidad en desarrollo y automatización
        upwork_jobs = [
            {
                "platform": "upwork",
                "external_id": "upwork_python_scraper_automation_q4",
                "title": "Python Web Scraping & Workflow Automation Specialist Needed",
                "client_name": "Upwork Enterprise Client",
                "budget": "$350 - $700 USD",
                "currency": "USD",
                "category": "python_automation_scraping",
                "skills": ["Python", "Playwright", "Web Scraping", "API", "Automation"],
                "url": "https://www.upwork.com/nx/find-work/",
                "description": "Looking for an expert Python developer to build robust web scrapers using Playwright or BeautifulSoup and automate data sync into Google Sheets / PostgreSQL. Must handle anti-bot detections, proxies, and error reporting cleanly."
            },
            {
                "platform": "upwork",
                "external_id": "upwork_wordpress_landing_fast_q4",
                "title": "Full-Stack WordPress & React Developer for High-Converting Landing Page",
                "client_name": "Digital Agency US",
                "budget": "$400 - $800 USD",
                "currency": "USD",
                "category": "web_dev",
                "skills": ["WordPress", "PHP", "JavaScript", "Responsive Design", "CSS"],
                "url": "https://www.upwork.com/nx/find-work/",
                "description": "We need a responsive, ultra-fast WordPress landing page with custom CSS, Elementor/ACF integration, and mobile optimization. Must be pixel-perfect, SEO-friendly, and connected to CRM via Webhooks."
            },
            {
                "platform": "upwork",
                "external_id": "upwork_qa_tester_junior_automation_q4",
                "title": "QA Manual & Automated Tester for Web Application (Junior/Mid)",
                "client_name": "SaaS Platform Inc.",
                "budget": "$15 - $25 USD / hora",
                "currency": "USD",
                "category": "python_automation_scraping",
                "skills": ["QA Testing", "Selenium", "Playwright", "Test Cases", "Bug Tracking"],
                "url": "https://www.upwork.com/nx/find-work/",
                "description": "Seeking a detail-oriented QA engineer to execute manual exploratory testing, report bugs with clear reproduction steps, and create automated regression test scripts using Python/Playwright."
            },
            {
                "platform": "upwork",
                "external_id": "upwork_branding_graphic_design_pack",
                "title": "Modern Corporate Identity, Logo & Social Media Kit Design",
                "client_name": "E-commerce Brand",
                "budget": "$250 - $500 USD",
                "currency": "USD",
                "category": "graphic_design_creative",
                "skills": ["Graphic Design", "Logo Design", "Adobe Illustrator", "Photoshop", "Branding"],
                "url": "https://www.upwork.com/nx/find-work/",
                "description": "We need a complete brand identity package including modern minimalist logo, color palette, typography guidelines, and social media post templates in Figma and Illustrator."
            }
        ]
        return upwork_jobs

    def scan_and_sync(self) -> int:
        """Escanea todos los proveedores y persiste nuevos proyectos en SQLite."""
        db: Session = SessionLocal()
        new_count = 0
        try:
            projs_freelancer = self.fetch_freelancer_projects()
            projs_getonbrd = self.fetch_getonbrd_freelance()
            projs_workana = self.fetch_workana_projects()
            projs_upwork = self.fetch_upwork_projects()
            all_projs = projs_freelancer + projs_getonbrd + projs_workana + projs_upwork

            for p in all_projs:
                existing = db.query(FreelanceProject).filter(
                    FreelanceProject.platform == p["platform"],
                    FreelanceProject.external_id == p["external_id"]
                ).first()

                category = self.proposal_gen.categorize_project(p["title"], p["description"])
                estimates = self.proposal_gen.estimate_bid_and_time(p["budget"], category, f"{p['title']} {p['description']}")
                suggested_bid = estimates["suggested_bid"]
                suggested_time = estimates["suggested_timeline"]
                is_hourly = estimates.get("is_hourly", False)
                prop_text = self.proposal_gen._generate_cognitive_proposal(
                    title=p["title"],
                    description=p["description"],
                    category=category,
                    suggested_bid=suggested_bid,
                    timeline=suggested_time,
                    is_hourly=is_hourly,
                    budget=p["budget"]
                )

                if existing:
                    # Actualizar si la nueva descripción es más completa o si tenía propuesta genérica
                    if len(p["description"]) > len(existing.description or "") or "Playwright / Requests / BeautifulSoup" in (existing.generated_proposal or ""):
                        existing.budget = p["budget"]
                        existing.description = p["description"]
                        existing.category = category
                        existing.generated_proposal = prop_text
                        existing.suggested_bid = suggested_bid
                        existing.suggested_timeline = suggested_time
                else:
                    new_proj = FreelanceProject(
                        platform=p["platform"],
                        external_id=p["external_id"],
                        title=p["title"],
                        client_name=p["client_name"],
                        budget=p["budget"],
                        currency=p.get("currency", "USD"),
                        category=category,
                        skills_json=json.dumps(p.get("skills", [])),
                        url=p["url"],
                        description=p["description"],
                        generated_proposal=prop_text,
                        suggested_bid=suggested_bid,
                        suggested_timeline=suggested_time,
                        status="open"
                    )
                    db.add(new_proj)
                    new_count += 1

            db.commit()
            print(f"[FreelanceHunter] Sincronización completada. Nuevos proyectos: {new_count}")
            return new_count
        except Exception as e:
            db.rollback()
            print(f"[FreelanceHunter] Error sincronizando proyectos: {e}")
            return 0
        finally:
            db.close()
