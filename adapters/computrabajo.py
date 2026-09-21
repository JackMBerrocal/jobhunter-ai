import re
import urllib.parse
from typing import List, Dict, Any
from playwright.async_api import Page
from adapters.base import BaseJobPlatform
from core.company_resolver import resolve_clean_company_name


class ComputrabajoAdapter(BaseJobPlatform):
    def __init__(self, browser_manager, llm_engine, country_code: str = "pe"):
        super().__init__(browser_manager, llm_engine)
        self.platform_name = "computrabajo"
        self.base_url = f"https://{country_code}.computrabajo.com"

    async def is_authenticated(self, page: Page) -> bool:
        """Verifica si la sesión de Computrabajo está activa."""
        try:
            await page.goto(f"{self.base_url}/candidate/home", wait_until="domcontentloaded", timeout=15000)
            await self.browser_manager.random_delay(1.0, 2.0)
            if "candidate" in page.url or await page.query_selector(".box_user, .user_menu, .user_name"):
                return True
            return False
        except Exception:
            return False

    async def search_jobs(self, query: str = "sistemas", remote_only: bool = True, max_results: int = 15) -> List[Dict[str, Any]]:
        """Busca ofertas remotas en Computrabajo utilizando rutas canónicas y buscador."""
        page = await self.browser_manager.new_page_with_stealth()
        jobs_found = []

        try:
            clean_query = query.lower().strip()
            # Si se solicita remoto y la consulta no lo incluye, añadirlo
            if remote_only and "remoto" not in clean_query and "teletrabajo" not in clean_query:
                search_term = f"{clean_query} remoto"
            else:
                search_term = clean_query

            # 1. Intentar URL directa canónica (ej: /trabajo-de-desarrollador-junior-remoto)
            slug = re.sub(r"[^\w\s-]", "", search_term).strip().replace(" ", "-")
            direct_url = f"{self.base_url}/trabajo-de-{slug}"
            print(f"[Computrabajo] Intentando navegación directa: {direct_url}")
            
            await page.goto(direct_url, wait_until="domcontentloaded", timeout=25000)
            await self.browser_manager.random_delay(2.0, 3.5)

            # Si redirigió a la home o no hay ofertas, usar el buscador de la página principal
            offer_articles = await page.query_selector_all("article.box_offer, article[data-id]")
            if not offer_articles or page.url.rstrip("/") == self.base_url.rstrip("/"):
                print("[Computrabajo] Usando buscador interactivo en home...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=25000)
                await self.browser_manager.random_delay(1.5, 2.5)

                search_input = await page.query_selector("#prof-cat-search-input, input[name='prof-cat-search-input']")
                if search_input:
                    await search_input.fill(search_term)
                    await page.keyboard.press("Enter")
                    await page.wait_for_load_state("domcontentloaded")
                    await self.browser_manager.random_delay(2.0, 3.5)
                    offer_articles = await page.query_selector_all("article.box_offer, article[data-id]")

            print(f"[Computrabajo] Vacantes detectadas: {len(offer_articles)}")

            for article in offer_articles[:max_results]:
                try:
                    title_elem = await article.query_selector("h2 a, a.js-o-link, h2.title a")
                    if not title_elem:
                        continue

                    title_raw = (await title_elem.inner_text()).strip()
                    # Limpiar ruido típico de Computrabajo ("Vista", saltos de línea)
                    title = title_raw.split("\n")[0].replace("Vista", "").strip()
                    if len(title) < 4:
                        continue

                    rel_url = await title_elem.get_attribute("href") or ""
                    full_url = self.base_url + rel_url if rel_url.startswith("/") else rel_url

                    # ID único de la oferta
                    offer_id = await article.get_attribute("data-id")
                    if not offer_id:
                        id_match = re.search(r"-([A-F0-9]{32})", full_url, re.IGNORECASE)
                        offer_id = id_match.group(1) if id_match else full_url

                    # Empresa real (p.fs16 a, span.fc_base, .company-name)
                    raw_company = ""
                    comp_elem = await article.query_selector("p.fs16 a, span.fc_base, .company-name, p.fs16")
                    if comp_elem:
                        comp_raw = (await comp_elem.inner_text()).strip()
                        comp_clean = comp_raw.split("\n")[0].replace("Vista", "").strip()
                        if len(comp_clean) > 2 and comp_clean.lower() not in ["destacado", "urgente"]:
                            raw_company = comp_clean

                    # Ubicación / Remoto
                    loc_elem = await article.query_selector("span.fs13.fc_aux, p.fs14, span.location")
                    loc_text = (await loc_elem.inner_text()).strip() if loc_elem else "Remoto"

                    # Snippet de descripción y salario
                    desc_elem = await article.query_selector("p.fs13.fc_aux, p.fs14, p.description")
                    desc_text = (await desc_elem.inner_text()).strip() if desc_elem else ""

                    company = resolve_clean_company_name(raw_company, full_url, title, desc_text)

                    sal_elem = await article.query_selector("span.salary, p.salary, span.fs13")
                    salary = (await sal_elem.inner_text()).strip() if sal_elem else ""

                    # Análisis profundo de idoneidad con el perfil del candidato
                    fit_analysis = self.llm.analyze_requirements_fit(
                        title=title,
                        description=desc_text,
                        company=company,
                        location=loc_text
                    )

                    jobs_found.append({
                        "platform": self.platform_name,
                        "external_id": str(offer_id),
                        "title": title,
                        "company": company,
                        "location": loc_text,
                        "modality": "remote" if "remoto" in loc_text.lower() or remote_only else "any",
                        "url": full_url,
                        "salary_snippet": salary,
                        "description": desc_text,
                        "match_score": fit_analysis["score"],
                        "match_reason": fit_analysis["reason"],
                        "requirements": fit_analysis,
                        "is_recommended": fit_analysis.get("is_recommended", True)
                    })
                except Exception as card_err:
                    print(f"[Computrabajo] Error leyendo tarjeta: {card_err}")
                    continue

        except Exception as e:
            print(f"[Computrabajo] Error en búsqueda: {e}")
        finally:
            await page.close()

        return jobs_found

    async def apply(self, job_data: Dict[str, Any], auto_submit: bool = False) -> Dict[str, Any]:
        """Aplica a la oferta en Computrabajo y responde preguntas de la empresa."""
        url = job_data.get("url")
        if not url:
            return {"status": "failed", "reason": "Sin URL"}

        page = await self.browser_manager.new_page_with_stealth()
        qa_history = []

        try:
            print(f"[Computrabajo] Abriendo oferta: {url}")
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await self.browser_manager.random_delay(2.0, 3.5)

            # Pre-flight: Verificar si la oferta ha expirado o fue eliminada (404)
            from core.availability_checker import is_job_expired_or_deleted
            is_expired, exp_reason = await is_job_expired_or_deleted(page, resp)
            if is_expired:
                print(f"[Computrabajo] ⚠️ Oferta expirada o eliminada: {exp_reason}")
                return {"status": "expired", "reason": exp_reason}

            # Botón de postulación (a.b_primary o texto Postularme)
            apply_button = await page.query_selector(
                "a.b_primary, a:has-text('Postularme'), a:has-text('Postular'), button#btnPostular, .btn_apply"
            )
            if not apply_button:
                already = await page.query_selector(".box_applied, .applied_message, .applied")
                if already:
                    return {"status": "already_applied", "notes": "Ya habías postulado a esta vacante anteriormente."}
                return {"status": "expired", "reason": "La oferta finalizó o fue retirada por el empleador (sin botón de postulación activo)."}

            await apply_button.click()
            await self.browser_manager.random_delay(2.0, 3.5)

            # Comprobar si redirigió a la pantalla de login o registro
            curr_url = page.url.lower()
            if "login" in curr_url or "acceso" in curr_url or "secure." in curr_url or "register" in curr_url:
                print("[Computrabajo] 🔐 Detectada barrera de acceso. Ejecutando AuthRegistrationHelper...")
                from adapters.auth_helper import AuthRegistrationHelper
                auth_helper = AuthRegistrationHelper(self.llm.profile)
                auth_res = await auth_helper.handle_auth_or_registration(page)
                await self.browser_manager.random_delay(2.5, 4.0)
                
                if "login" in page.url.lower() or "secure." in page.url.lower():
                    return {
                        "status": "requires_manual_action",
                        "notes": f"Acceso intentado ({auth_res.get('method')}). Requiere verificar sesión en Computrabajo."
                    }

            # Modal de preguntas
            questions_box = await page.query_selector("#modalQuestions, .box_questions, form#formQuestions")
            if questions_box:
                print("[Computrabajo] Respondiendo cuestionario de la empresa con IA...")
                textareas = await questions_box.query_selector_all("textarea, input[type='text']")
                for ta in textareas:
                    label = await ta.query_selector("xpath=preceding-sibling::label | preceding-sibling::p")
                    q_text = (await label.inner_text()).strip() if label else "Experiencia y motivación"
                    answer = self.llm.answer_screening_question(
                        q_text,
                        location=job_data.get("location", "Perú"),
                        platform=self.platform_name
                    )
                    await ta.fill(answer)
                    qa_history.append({"question": q_text, "answer": answer})
                    await self.browser_manager.random_delay(0.5, 1.0)

                # Radio buttons
                radios = await questions_box.query_selector_all("input[type='radio']")
                if radios:
                    for r in radios:
                        await r.click()
                        break

                submit_q = await questions_box.query_selector("button[type='submit'], input[type='submit']")
                if submit_q:
                    if auto_submit:
                        await submit_q.click()
                        await self.browser_manager.random_delay(2.0, 3.0)
                        return {"status": "success", "qa": qa_history, "notes": "Postulación y cuestionario enviados exitosamente en Computrabajo"}
                    else:
                        return {"status": "ready_for_review", "qa": qa_history, "notes": "Cuestionario completado, listo para revisión"}

            return {"status": "success", "qa": qa_history, "notes": "Postulación completada con CV de Computrabajo"}

        except Exception as e:
            print(f"[Computrabajo] Error en postulación: {e}")
            return {"status": "failed", "reason": str(e), "qa": qa_history}
        finally:
            await page.close()
