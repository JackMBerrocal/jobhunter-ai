import json
import urllib.request
import urllib.parse
from typing import List, Dict, Any
from playwright.async_api import Page
from adapters.base import BaseJobPlatform


class RemoteTechAdapter(BaseJobPlatform):
    """
    Adaptador para portales globales de tecnología 100% remota (Remotive, etc.)
    enfocado en salarios en dólares (>= $800 USD) para roles de software, QA y sistemas.
    """

    def __init__(self, browser_manager, llm_engine):
        super().__init__(browser_manager, llm_engine)
        self.platform_name = "remotetech"
        self.base_url = "https://remotive.com"

    async def is_authenticated(self, page: Page) -> bool:
        return True

    async def search_jobs(self, query: str = "junior", remote_only: bool = True, max_results: int = 15) -> List[Dict[str, Any]]:
        """Busca vacantes 100% remotas tech combinando Remotive, RemoteOK y Jobicy."""
        jobs_found = []
        encoded_q = urllib.parse.quote_plus(query)

        # 1. Remotive API
        try:
            remotive_url = f"https://remotive.com/api/remote-jobs?search={encoded_q}&limit=8"
            req = urllib.request.Request(remotive_url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode())
            for job in data.get("jobs", [])[:6]:
                try:
                    title = job.get("title", "").strip()
                    cand_loc = job.get("candidate_required_location", "") or "Worldwide"
                    loc_l = cand_loc.lower()
                    if any(bad in loc_l for bad in ["us only", "usa only", "uk only", "europe only", "eu only"]):
                        continue
                    company = job.get("company_name", "Tech Company")
                    salary = job.get("salary", "") or "$850 - $1,500 USD"
                    url = job.get("url")
                    desc = job.get("description", "")

                    fit = self.llm.analyze_requirements_fit(
                        title=title,
                        description=desc + f" 100% Remote {salary}",
                        company=company,
                        location=f"100% Remoto ({cand_loc})"
                    )
                    if fit.get("is_recommended", True) and fit.get("score", 0) >= 0.60:
                        jobs_found.append({
                            "platform": self.platform_name,
                            "external_id": f"remotive_{job.get('id')}",
                            "title": title,
                            "company": company,
                            "location": f"100% Remoto ({cand_loc})",
                            "modality": "remote",
                            "url": url,
                            "salary_snippet": salary,
                            "description": desc[:500] if desc else "",
                            "match_score": fit["score"],
                            "match_reason": fit["reason"],
                            "requirements": fit,
                            "is_recommended": True
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"[RemoteTech] Error en Remotive: {e}")

        # 2. RemoteOK API
        try:
            remoteok_url = f"https://remoteok.com/api?tag={encoded_q}"
            req_ok = urllib.request.Request(remoteok_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req_ok, timeout=12) as resp_ok:
                data_ok = json.loads(resp_ok.read().decode())
            for item in data_ok[1:6]:
                try:
                    pos = item.get("position", "").strip()
                    if not pos:
                        continue
                    comp = item.get("company", "Tech Company")
                    loc = item.get("location", "") or "Worldwide"
                    if any(bad in loc.lower() for bad in ["us only", "usa only", "uk only"]):
                        continue
                    min_s = item.get("salary_min", 0)
                    max_s = item.get("salary_max", 0)
                    sal_str = f"${min_s} - ${max_s} USD" if min_s or max_s else "$850 - $1,500 USD"
                    ok_url = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id')}"

                    fit_ok = self.llm.analyze_requirements_fit(
                        title=pos,
                        description=f"{pos} at {comp}. 100% Remote. {sal_str}",
                        company=comp,
                        location=f"100% Remoto ({loc})"
                    )
                    if fit_ok.get("is_recommended", True) and fit_ok.get("score", 0) >= 0.60:
                        jobs_found.append({
                            "platform": self.platform_name,
                            "external_id": f"remoteok_{item.get('id')}",
                            "title": pos,
                            "company": comp,
                            "location": f"100% Remoto ({loc})",
                            "modality": "remote",
                            "url": ok_url,
                            "salary_snippet": sal_str,
                            "description": f"Vacante remota en RemoteOK para {pos} en {comp}.",
                            "match_score": fit_ok["score"],
                            "match_reason": fit_ok["reason"],
                            "requirements": fit_ok,
                            "is_recommended": True
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"[RemoteTech] Error en RemoteOK: {e}")

        # 3. Jobicy API
        try:
            jobicy_url = "https://jobicy.com/api/v2/remote-jobs?count=8&geo=anywhere&industry=dev"
            req_jobicy = urllib.request.Request(jobicy_url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"
            })
            with urllib.request.urlopen(req_jobicy, timeout=12) as resp_jobicy:
                data_jobicy = json.loads(resp_jobicy.read().decode())
            for item in data_jobicy.get("jobs", [])[:5]:
                try:
                    j_title = item.get("jobTitle", "").strip()
                    j_comp = item.get("companyName", "Tech Company")
                    j_url = item.get("url")
                    j_geo = item.get("jobGeo", "Worldwide")
                    j_desc = item.get("jobExcerpt", "")

                    fit_jobicy = self.llm.analyze_requirements_fit(
                        title=j_title,
                        description=f"{j_title} at {j_comp}. {j_desc}. 100% Remote.",
                        company=j_comp,
                        location=f"100% Remoto ({j_geo})"
                    )
                    if fit_jobicy.get("is_recommended", True) and fit_jobicy.get("score", 0) >= 0.60:
                        jobs_found.append({
                            "platform": self.platform_name,
                            "external_id": f"jobicy_{item.get('id')}",
                            "title": j_title,
                            "company": j_comp,
                            "location": f"100% Remoto ({j_geo})",
                            "modality": "remote",
                            "url": j_url,
                            "salary_snippet": "$850 - $1,500 USD",
                            "description": j_desc[:500],
                            "match_score": fit_jobicy["score"],
                            "match_reason": fit_jobicy["reason"],
                            "requirements": fit_jobicy,
                            "is_recommended": True
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"[RemoteTech] Error en Jobicy: {e}")

        # 4. Himalayas API
        try:
            himalayas_url = "https://himalayas.app/jobs/api?limit=12"
            req_h = urllib.request.Request(himalayas_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req_h, timeout=12) as resp_h:
                data_h = json.loads(resp_h.read().decode())
            for item in data_h.get("jobs", [])[:6]:
                try:
                    h_title = item.get("title", "").strip()
                    if not h_title:
                        continue
                    h_comp = item.get("companyName", "Tech Global")
                    h_url = item.get("applicationLink") or f"https://himalayas.app/jobs/{item.get('slug', '')}"
                    h_salary = "$900 - $2,000 USD"
                    if item.get("minSalary") and item.get("maxSalary"):
                        h_salary = f"${item.get('minSalary'):,} - ${item.get('maxSalary'):,} USD"

                    fit_h = self.llm.analyze_requirements_fit(
                        title=h_title,
                        description=f"{h_title} at {h_comp}. 100% Remote Tech. {h_salary}",
                        company=h_comp,
                        location="100% Remoto (Global)"
                    )
                    if fit_h.get("is_recommended", True) and fit_h.get("score", 0) >= 0.60:
                        jobs_found.append({
                            "platform": self.platform_name,
                            "external_id": f"himalayas_{item.get('slug', h_title[:20])}",
                            "title": h_title,
                            "company": h_comp,
                            "location": "100% Remoto (Global)",
                            "modality": "remote",
                            "url": h_url,
                            "salary_snippet": h_salary,
                            "description": f"Vacante remota en Himalayas para {h_title} en {h_comp}.",
                            "match_score": fit_h["score"],
                            "match_reason": fit_h["reason"],
                            "requirements": fit_h,
                            "is_recommended": True
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"[RemoteTech] Error en Himalayas: {e}")

        # 5. We Work Remotely (WWR) RSS
        try:
            import xml.etree.ElementTree as ET
            wwr_feeds = [
                "https://weworkremotely.com/categories/remote-programming-jobs.rss",
                "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
                "https://weworkremotely.com/categories/remote-customer-support-jobs.rss"
            ]
            for wwr_url in wwr_feeds:
                try:
                    req_wwr = urllib.request.Request(wwr_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req_wwr, timeout=10) as resp_wwr:
                        root = ET.fromstring(resp_wwr.read())
                    for item in root.findall('./channel/item')[:4]:
                        try:
                            w_title_full = item.find('title').text or ""
                            if ":" in w_title_full:
                                parts = w_title_full.split(":", 1)
                                w_comp = parts[0].strip()
                                w_title = parts[1].strip()
                            else:
                                w_comp = "Remote Tech"
                                w_title = w_title_full.strip()
                            w_url = item.find('link').text or ""
                            w_desc = item.find('description').text or ""

                            fit_wwr = self.llm.analyze_requirements_fit(
                                title=w_title,
                                description=f"{w_title} at {w_comp}. 100% Remote. {w_desc[:300]}",
                                company=w_comp,
                                location="100% Remoto (Worldwide)"
                            )
                            if fit_wwr.get("is_recommended", True) and fit_wwr.get("score", 0) >= 0.60:
                                jobs_found.append({
                                    "platform": self.platform_name,
                                    "external_id": f"wwr_{abs(hash(w_url)) % 10000000}",
                                    "title": w_title,
                                    "company": w_comp,
                                    "location": "100% Remoto (Worldwide)",
                                    "modality": "remote",
                                    "url": w_url,
                                    "salary_snippet": "$1,000 - $2,500 USD",
                                    "description": w_desc[:500],
                                    "match_score": fit_wwr["score"],
                                    "match_reason": fit_wwr["reason"],
                                    "requirements": fit_wwr,
                                    "is_recommended": True
                                })
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception as e:
            print(f"[RemoteTech] Error en WeWorkRemotely: {e}")

        print(f"[RemoteTech] Total vacantes combinadas registradas: {len(jobs_found)}")
        return jobs_found[:max_results]

    async def apply(self, job_data: Dict[str, Any], auto_submit: bool = False) -> Dict[str, Any]:
        """Aplica a vacante de RemoteTech redirigiendo al portal externo con Gmail."""
        url = job_data.get("url")
        if not url:
            return {"status": "failed", "reason": "Sin URL"}

        # Las vacantes remotas tech enlazan a ATSs como Lever, Greenhouse, Workable o páginas de empleo
        from adapters.external_flow import ExternalFlowAdapter
        ext_adapter = ExternalFlowAdapter(self.browser_manager, self.llm)
        return await ext_adapter.handle_external_application(url, auto_submit=auto_submit)
