import re
import urllib.parse
import urllib.request
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from playwright.async_api import Page
from adapters.base import BaseJobPlatform


class LaborumAdapter(BaseJobPlatform):
    """
    Adaptador para Laborum Perú (laborum.pe), uno de los portales líderes
    en Perú con alta densidad de vacantes junior, practicantes y sistemas/TI.
    """

    def __init__(self, browser_manager, llm_engine):
        super().__init__(browser_manager, llm_engine)
        self.platform_name = "laborum"
        self.base_url = "https://www.laborum.pe"

    async def is_authenticated(self, page: Page) -> bool:
        """Verifica si hay sesión activa en Laborum."""
        try:
            await page.goto(f"{self.base_url}/login", wait_until="domcontentloaded", timeout=15000)
            await self.browser_manager.random_delay(1.0, 2.0)
            if "login" not in page.url.lower():
                return True
            return False
        except Exception:
            return False

    async def search_jobs(self, query: str = "sistemas", remote_only: bool = True, max_results: int = 15) -> List[Dict[str, Any]]:
        """Busca ofertas en Laborum Perú."""
        jobs_found = []
        try:
            # En Laborum, consultas simples de una o dos palabras clave tienen mayor efectividad
            raw_q = query.lower().replace("teletrabajo", "").strip()
            # Mapeo de términos clave para Laborum Perú
            if any(k in raw_q for k in ["dato", "data", "analytics"]):
                keyword = "datos"
            elif any(k in raw_q for k in ["qa", "tester", "calidad"]):
                keyword = "qa"
            elif any(k in raw_q for k in ["practicante", "trainee", "pasante"]):
                keyword = "practicas sistemas"
            elif any(k in raw_q for k in ["programador", "developer", "software", "desarrollo"]):
                keyword = "desarrollador"
            else:
                keyword = "sistemas"

            if remote_only and "remoto" in raw_q:
                keyword = "remoto"

            encoded_query = urllib.parse.quote_plus(keyword)
            search_url = f"{self.base_url}/search-jobs?q={encoded_query}"
            
            print(f"[Laborum] Explorando: {search_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("a", href=re.compile(r"/job/"))
            print(f"[Laborum] Avisos detectados: {len(cards)}")

            for card in cards[:max_results]:
                try:
                    href = card.get("href", "")
                    if not href:
                        continue
                    full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                    
                    # Extraer ID externo del slug
                    ext_id = href.split("/")[-1].split("?")[0]
                    if not ext_id:
                        ext_id = str(abs(hash(href)) % 10000000)
                    
                    # Título de la vacante (aria-label suele ser "Vacantes Nombre del Cargo")
                    aria = card.get("aria-label", "").strip()
                    if aria:
                        title = re.sub(r"^vacantes\s+", "", aria, flags=re.IGNORECASE).strip()
                    else:
                        title_el = card.find(["h2", "h3", "h4", "p"])
                        title = title_el.text.strip() if title_el else "Oportunidad de Sistemas"

                    # Empresa
                    img_company = card.find("img", alt=True)
                    company = img_company.get("alt", "").strip() if img_company else "Empresa Destacada"

                    # Ubicación / snippet
                    card_text = card.get_text(" ", strip=True)
                    loc = "Remoto (Perú)" if "remoto" in card_text.lower() else "Lima, Perú"

                    fit = self.llm.analyze_requirements_fit(
                        title=title,
                        description=f"{title} en {company}. {card_text[:300]}",
                        company=company,
                        location=loc
                    )

                    if fit.get("is_recommended", True) and fit.get("score", 0) >= 0.58:
                        jobs_found.append({
                            "platform": self.platform_name,
                            "external_id": f"laborum_{ext_id}",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "modality": "remote" if "remoto" in loc.lower() else "hybrid",
                            "url": full_url,
                            "salary_snippet": "S/ 2,000 - S/ 3,500 PEN",
                            "description": card_text[:450],
                            "match_score": fit["score"],
                            "match_reason": fit["reason"],
                            "requirements": fit,
                            "is_recommended": True
                        })
                except Exception as card_err:
                    continue

        except Exception as e:
            print(f"[Laborum] Error durante búsqueda: {e}")

        return jobs_found

    async def apply(self, job_data: Dict[str, Any], auto_submit: bool = False) -> Dict[str, Any]:
        """Aplica a vacante de Laborum utilizando el flujo externo o navegador."""
        url = job_data.get("url")
        if not url:
            return {"status": "failed", "reason": "Sin URL de postulación"}

        from adapters.external_flow import ExternalFlowAdapter
        ext_adapter = ExternalFlowAdapter(self.browser_manager, self.llm)
        return await ext_adapter.handle_external_application(url, auto_submit=auto_submit, job_data=job_data)
