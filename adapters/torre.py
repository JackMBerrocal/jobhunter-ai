import json
import urllib.request
import urllib.parse
from typing import List, Dict, Any
from playwright.async_api import Page
from adapters.base import BaseJobPlatform


class TorreAdapter(BaseJobPlatform):
    """
    Adaptador para Torre.co / Torre.ai,
    la red de empleo tecnológico de Latinoamérica con soporte nativo
    para vacantes Junior, Trainee y 100% remotas.
    """

    def __init__(self, browser_manager, llm_engine):
        super().__init__(browser_manager, llm_engine)
        self.platform_name = "torre"
        self.base_url = "https://torre.ai"
        self.api_url = "https://search.torre.co/opportunities/_search/"

    async def is_authenticated(self, page: Page) -> bool:
        return True

    async def search_jobs(self, query: str = "junior", remote_only: bool = True, max_results: int = 15) -> List[Dict[str, Any]]:
        """Busca ofertas 100% remotas en Torre.co."""
        jobs_found = []
        try:
            payload = {
                "skill/role": {
                    "text": query,
                    "experience": "potential-to-develop"
                }
            }

            req_url = f"{self.api_url}?size={max_results * 2}"
            print(f"[Torre] Consultando API con query '{query}': {req_url}")
            
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(req_url, data=data_bytes, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Content-Type": "application/json"
            })

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            results = data.get("results", [])
            print(f"[Torre] Oportunidades encontradas: {len(results)}")

            for r in results[:max_results]:
                try:
                    ext_id = r.get("id")
                    title = r.get("objective", "").strip()
                    if not title:
                        continue

                    # Verificar si es remoto
                    is_remote = r.get("remote", False)
                    if remote_only and not is_remote:
                        continue

                    # Empresa
                    orgs = r.get("organizations", [])
                    company = orgs[0].get("name", "Empresa Tecnológica") if orgs else "Empresa Tecnológica"

                    # Ubicación
                    locations = r.get("locations", [])
                    loc_str = "100% Remoto (LatAm / Global)"
                    if locations:
                        loc_str = f"Remoto ({', '.join(locations[:2])})"

                    # Salario
                    comp_data = r.get("compensation", {})
                    salary_str = ""
                    min_sal = None
                    if comp_data and comp_data.get("data"):
                        cd = comp_data.get("data", {})
                        min_sal = cd.get("minAmount")
                        max_sal = cd.get("maxAmount")
                        curr = cd.get("currency", "USD")
                        period = cd.get("periodicity", "monthly")
                        if min_sal or max_sal:
                            salary_str = f"{min_sal or 0} - {max_sal or 0} {curr} ({period})"

                    job_url = f"https://torre.ai/post/{ext_id}"

                    # Evaluar adecuación
                    fit_analysis = self.llm.analyze_requirements_fit(
                        title=title,
                        description=f"{title} - Oportunidad en {company}. Modalidad 100% Remota. {salary_str}",
                        company=company,
                        location=loc_str
                    )

                    # Si es presencial o salario bajo
                    if not fit_analysis.get("is_recommended", True) or fit_analysis.get("score", 0) < 0.60:
                        continue

                    jobs_found.append({
                        "platform": self.platform_name,
                        "external_id": str(ext_id),
                        "title": title,
                        "company": company,
                        "location": loc_str,
                        "modality": "remote",
                        "url": job_url,
                        "salary_snippet": salary_str,
                        "description": f"Oportunidad remota en Torre.co para {title} en {company}.",
                        "match_score": fit_analysis["score"],
                        "match_reason": fit_analysis["reason"],
                        "requirements": fit_analysis,
                        "is_recommended": True
                    })
                except Exception as item_err:
                    print(f"[Torre] Error procesando vacante: {item_err}")
                    continue

        except Exception as e:
            print(f"[Torre] Error en búsqueda de vacantes: {e}")

        return jobs_found

    async def apply(self, job_data: Dict[str, Any], auto_submit: bool = False) -> Dict[str, Any]:
        """Aplica a vacante de Torre enlazando por navegador o flujo externo con Gmail."""
        url = job_data.get("url")
        if not url:
            return {"status": "failed", "reason": "Sin URL"}

        from adapters.external_flow import ExternalFlowAdapter
        ext_adapter = ExternalFlowAdapter(self.browser_manager, self.llm)
        return await ext_adapter.handle_external_application(url, auto_submit=auto_submit, job_data=job_data)
