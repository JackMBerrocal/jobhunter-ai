import re
import urllib.parse
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from adapters.base import BaseJobPlatform


class LinkedInAdapter(BaseJobPlatform):
    def __init__(self, browser_manager, llm_engine):
        super().__init__(browser_manager, llm_engine)
        self.platform_name = "linkedin"

    async def is_authenticated(self, page: Page) -> bool:
        """Verifica si la sesión de LinkedIn está activa."""
        try:
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
            await self.browser_manager.random_delay(1.5, 3.0)
            current_url = page.url
            if "feed" in current_url or await page.query_selector(".global-nav"):
                return True
            return False
        except Exception:
            return False

    async def search_jobs(self, query: str = "junior developer", remote_only: bool = True, max_results: int = 15) -> List[Dict[str, Any]]:
        """
        Busca empleos en LinkedIn filtrando por remoto y primer empleo / nivel entry.
        """
        page = await self.browser_manager.new_page_with_stealth()
        jobs_found = []

        try:
            encoded_query = urllib.parse.quote(query)
            search_url = (
                f"https://www.linkedin.com/jobs/search/?"
                f"keywords={encoded_query}&"
                f"f_AL=true&"           # Solicitud sencilla
                f"f_E=1%2C2"           # Entry-level / Internship
            )
            if remote_only:
                search_url += "&f_WT=2" # 100% Remoto

            print(f"[LinkedIn] Navegando a búsqueda: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            await self.browser_manager.random_delay(2.0, 4.0)

            # Selector de lista de vacantes (tanto en sesión privada como pública)
            card_selectors = [
                ".jobs-search-results__list-item",
                "li.ember-view.jobs-search-results__list-item",
                "div.job-card-container",
                "ul.jobs-search__results-list li",
                "div.base-card"
            ]

            cards = []
            for sel in card_selectors:
                cards = await page.query_selector_all(sel)
                if cards:
                    break

            print(f"[LinkedIn] Vacantes encontradas en la página: {len(cards)}")

            for card in cards[:max_results]:
                try:
                    # Extraer título y enlace
                    title_elem = await card.query_selector(
                        ".job-card-list__title--link, a.job-card-container__link, a.job-card-list__title, "
                        "h3.base-search-card__title, a.base-card__full-link"
                    )
                    if not title_elem:
                        continue
                    
                    title_raw = (await title_elem.inner_text()).strip()
                    title = title_raw.split("\n")[0].strip()
                    if len(title) < 4:
                        continue

                    href = await title_elem.get_attribute("href") or ""
                    full_url = "https://www.linkedin.com" + href if href.startswith("/") else href
                    
                    # Extraer ID de la vacante
                    job_id_match = re.search(r"currentJobId=(\d+)|jobs/view/(\d+)|-(\d+)\?", full_url)
                    job_id = None
                    if job_id_match:
                        job_id = job_id_match.group(1) or job_id_match.group(2) or job_id_match.group(3)
                    if not job_id:
                        job_id = full_url

                    # Empresa real (selectores completos para versión autenticada y pública)
                    company = "Empresa de Tecnología"
                    comp_elem = await card.query_selector(
                        ".job-card-container__primary-description, .job-card-container__company-name, "
                        ".artdeco-entity-lockup__subtitle, a[data-tracking-control-name*='company'], "
                        "h4.base-search-card__subtitle a, h4.base-search-card__subtitle"
                    )
                    if comp_elem:
                        comp_text = (await comp_elem.inner_text()).strip().split("\n")[0].strip()
                        if len(comp_text) > 1 and "confidencial" not in comp_text.lower():
                            company = comp_text

                    # Ubicación
                    loc_elem = await card.query_selector(".job-card-container__metadata-item, span.job-search-card__location")
                    location = (await loc_elem.inner_text()).strip() if loc_elem else "Remoto"

                    # Evaluar adecuación con el LLM
                    fit_analysis = self.llm.analyze_requirements_fit(
                        title=title,
                        description="",
                        company=company,
                        location=location
                    )

                    job_info = {
                        "platform": self.platform_name,
                        "external_id": str(job_id),
                        "title": title,
                        "company": company,
                        "location": location,
                        "modality": "remote" if remote_only else "any",
                        "url": full_url,
                        "salary_snippet": "",
                        "description": "",
                        "match_score": fit_analysis["score"],
                        "match_reason": fit_analysis["reason"],
                        "requirements": fit_analysis,
                        "is_recommended": fit_analysis.get("is_recommended", True)
                    }
                    jobs_found.append(job_info)
                except Exception as card_err:
                    print(f"[LinkedIn] Error extrayendo tarjeta: {card_err}")
                    continue

        except Exception as e:
            print(f"[LinkedIn] Error en búsqueda: {e}")
        finally:
            await page.close()

        return jobs_found

    async def apply(self, job_data: Dict[str, Any], auto_submit: bool = False) -> Dict[str, Any]:
        """
        Ejecuta el flujo de postulación 'Solicitud sencilla' en LinkedIn respondiendo
        automáticamente preguntas con la base de conocimiento del candidato.
        """
        url = job_data.get("url")
        if not url:
            return {"status": "failed", "reason": "URL no proporcionada"}

        page = await self.browser_manager.new_page_with_stealth()
        qa_history = []

        try:
            print(f"[LinkedIn] Abriendo vacante para postular: {url}")
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await self.browser_manager.random_delay(2.0, 3.5)

            # Pre-flight: Verificar si la vacante en LinkedIn está cerrada o expiró
            from core.availability_checker import is_job_expired_or_deleted
            is_expired, exp_reason = await is_job_expired_or_deleted(page, resp)
            if is_expired:
                print(f"[LinkedIn] ⚠️ Vacante cerrada/expirada: {exp_reason}")
                return {"status": "expired", "reason": exp_reason}

            # Buscar botón de Solicitud Sencilla / Easy Apply
            easy_apply_button = await page.query_selector(
                "button.jobs-apply-button, button[aria-label*='Solicitud sencilla'], button[aria-label*='Easy Apply']"
            )

            if not easy_apply_button:
                # Comprobar si ya fue enviada
                applied_indicator = await page.query_selector(".jobs-s-apply__applied-date, .artdeco-inline-feedback--success")
                if applied_indicator:
                    return {"status": "already_applied", "notes": "Ya has postulado previamente a este puesto."}
                return {"status": "requires_manual_action", "reason": "No disponible para Solicitud Sencilla o requiere sesión iniciada."}

            await easy_apply_button.click()
            await self.browser_manager.random_delay(2.0, 3.0)

            # Recorrer pasos del modal de postulación (hasta 5 pasos máximo)
            step_count = 0
            while step_count < 5:
                step_count += 1
                modal = await page.query_selector(".jobs-easy-apply-modal, div[data-test-modal]")
                if not modal:
                    break

                # 1. Resolver inputs de texto
                text_inputs = await modal.query_selector_all("input[type='text'], input[type='tel'], input[type='email']")
                for inp in text_inputs:
                    inp_id = await inp.get_attribute("id") or ""
                    val = await inp.input_value()
                    if not val:
                        label = await modal.query_selector(f"label[for='{inp_id}']")
                        q_text = (await label.inner_text()).strip() if label else "Información requerida"
                        ans = self.llm.answer_screening_question(q_text)
                        await inp.fill(ans)
                        qa_history.append({"question": q_text, "answer": ans})

                # 2. Resolver radio buttons
                fieldsets = await modal.query_selector_all("fieldset")
                for fs in fieldsets:
                    legend = await fs.query_selector("legend")
                    q_text = (await legend.inner_text()).strip() if legend else ""
                    radios = await fs.query_selector_all("input[type='radio']")
                    if radios:
                        checked = False
                        for r in radios:
                            if await r.is_checked():
                                checked = True
                                break
                        if not checked and len(radios) > 0:
                            await radios[0].click()
                            qa_history.append({"question": q_text, "answer": "Opción 1 seleccionada"})

                # 3. Dropdowns / Selects
                selects = await modal.query_selector_all("select")
                for s in selects:
                    val = await s.input_value()
                    if not val:
                        options = await s.query_selector_all("option")
                        if len(options) > 1:
                            val_to_select = await options[1].get_attribute("value")
                            if val_to_select:
                                await s.select_option(val_to_select)

                # 4. Comprobar botón 'Siguiente' / 'Revisar' / 'Enviar solicitud'
                submit_button = await modal.query_selector("button[aria-label*='Enviar solicitud'], button[aria-label*='Submit application']")
                if submit_button:
                    if auto_submit:
                        await submit_button.click()
                        await self.browser_manager.random_delay(2.0, 3.5)
                        return {
                            "status": "success",
                            "notes": f"Postulación completada en LinkedIn ({step_count} pasos)",
                            "qa": qa_history
                        }
                    else:
                        return {
                            "status": "ready_for_review",
                            "notes": "Formulario completado en LinkedIn, listo para enviar",
                            "qa": qa_history
                        }

                next_button = await modal.query_selector("button[aria-label*='Continuar'], button[aria-label*='Siguiente'], button[aria-label*='Next'], button[aria-label*='Review']")
                if next_button:
                    await next_button.click()
                    await self.browser_manager.random_delay(1.5, 2.5)
                else:
                    break

            return {
                "status": "success",
                "notes": "Flujo de Easy Apply completado",
                "qa": qa_history
            }

        except Exception as e:
            print(f"[LinkedIn] Error en postulación: {e}")
            return {"status": "failed", "reason": str(e), "qa": qa_history}
        finally:
            await page.close()
