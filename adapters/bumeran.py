import re
import urllib.parse
from typing import List, Dict, Any
from playwright.async_api import Page
from adapters.base import BaseJobPlatform


from core.company_resolver import resolve_clean_company_name


class BumeranAdapter(BaseJobPlatform):
    def __init__(self, browser_manager, llm_engine, country_domain: str = "com.pe"):
        super().__init__(browser_manager, llm_engine)
        self.platform_name = "bumeran"
        self.base_url = f"https://www.bumeran.{country_domain}"

    async def is_authenticated(self, page: Page) -> bool:
        """Verifica si la sesión de Bumeran está activa."""
        try:
            await page.goto(f"{self.base_url}/postulantes", wait_until="domcontentloaded", timeout=15000)
            await self.browser_manager.random_delay(1.0, 2.0)
            if "postulantes" in page.url or await page.query_selector("[data-testid='user-avatar'], .header-user"):
                return True
            return False
        except Exception:
            return False

    async def search_jobs(self, query: str = "Ingeniero de Sistemas Junior", remote_only: bool = True, max_results: int = 15) -> List[Dict[str, Any]]:
        """Busca ofertas remotas en Bumeran."""
        page = await self.browser_manager.new_page_with_stealth()
        jobs_found = []

        try:
            # Query ajustada para teletrabajo
            slug_query = query.lower().replace(" ", "-")
            search_url = f"{self.base_url}/empleos-busqueda-{slug_query}"
            if remote_only:
                search_url += "-teletrabajo"
            search_url += ".html"

            print(f"[Bumeran] Buscando en: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            await self.browser_manager.random_delay(2.0, 3.5)

            # Tarjetas de vacantes en Bumeran
            cards = await page.query_selector_all("div[data-id], a[href*='/empleos/'], div[class*='AvisosLista']")
            print(f"[Bumeran] Avisos encontrados: {len(cards)}")

            for card in cards[:max_results]:
                try:
                    # Enlace específico de la vacante
                    link_elem = await card.query_selector("a[href*='/empleos/']")
                    if not link_elem:
                        # Si la propia tarjeta es el enlace
                        tag_name = await (await card.get_property("tagName")).json_value()
                        if tag_name.lower() == "a":
                            link_elem = card

                    if not link_elem:
                        continue

                    href = await link_elem.get_attribute("href") or ""
                    if not href or "/empleos/" not in href:
                        continue

                    # Buscar título dentro del enlace o tarjeta (h2, h1 o texto del link)
                    title_elem = await link_elem.query_selector("h2, h1") or await card.query_selector("h2, h1")
                    if title_elem:
                        title = (await title_elem.inner_text()).strip()
                    else:
                        title = (await link_elem.inner_text()).strip()

                    # Limpiar saltos de línea y ruido
                    title = title.split("\n")[0].strip()

                    # Filtro anti-basura: descartar fechas y textos inválidos
                    title_lower = title.lower()
                    if len(title) < 5 or any(bad in title_lower for bad in ["publicado", "actualizado", "hace ", "días", "ayer", "guardar", "destacado"]):
                        continue

                    full_url = self.base_url + href if href.startswith("/") else href
                    ext_id_match = re.search(r"-(\d+)\.html", full_url)
                    ext_id = ext_id_match.group(1) if ext_id_match else full_url

                    # Empresa real (excluyendo fechas y deduciendo de URL slug si el DOM falla)
                    comp_elem = await card.query_selector("p[class*='Empresa'], span[class*='Empresa'], [data-qa='job-company']")
                    raw_company = (await comp_elem.inner_text()).strip() if comp_elem else ""
                    if any(bad in raw_company.lower() for bad in ["publicado", "actualizado", "hace ", "días", "ayer"]):
                        raw_company = ""
                    company = resolve_clean_company_name(raw_company, full_url, title)

                    # Ubicación
                    loc_elem = await card.query_selector("p[class*='Ubicacion'], span[class*='Ubicacion']")
                    location = (await loc_elem.inner_text()).strip() if loc_elem else "Teletrabajo / Remoto"

                    fit_analysis = self.llm.analyze_requirements_fit(
                        title=title,
                        description="",
                        company=company,
                        location=location
                    )

                    jobs_found.append({
                        "platform": self.platform_name,
                        "external_id": str(ext_id),
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
                    })
                except Exception as card_err:
                    print(f"[Bumeran] Error extrayendo aviso: {card_err}")
                    continue

        except Exception as e:
            print(f"[Bumeran] Error en búsqueda: {e}")
        finally:
            await page.close()

        return jobs_found

    async def apply(self, job_data: Dict[str, Any], auto_submit: bool = False) -> Dict[str, Any]:
        """
        Aplica a la vacante en Bumeran y responde proactivamente todas las preguntas
        de filtro de los reclutadores (incluyendo el banner 'Tienes preguntas sin responder').
        """
        url = job_data.get("url")
        if not url:
            return {"status": "failed", "reason": "Sin URL"}

        page = await self.browser_manager.new_page_with_stealth()
        qa_history = []

        try:
            print(f"[Bumeran] Abriendo aviso: {url}")
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.browser_manager.random_delay(2.5, 3.5)

            # Pre-flight: Verificar si el aviso de Bumeran finalizó o fue eliminado
            from core.availability_checker import is_job_expired_or_deleted
            is_expired, exp_reason = await is_job_expired_or_deleted(page, resp)
            if is_expired:
                print(f"[Bumeran] ⚠️ Aviso finalizado o eliminado: {exp_reason}")
                return {"status": "expired", "reason": exp_reason}

            # 1. Verificar si ya se ha postulado anteriormente
            already_applied = await page.query_selector('text="Postulado el", div:has-text("Postulado el")')
            if already_applied:
                print("[Bumeran] Estado detectado: Ya postulado previamente. Revisando preguntas pendientes...")

            # 2. Si no se ha postulado aún, presionar el botón de postulación
            if not already_applied:
                postular_btn = await page.query_selector("button#postularme, button[data-testid='btn-apply'], button[class*='Postularme'], div[id='section-postular-bar'] button")
                if postular_btn:
                    print("[Bumeran] Botón de postularme encontrado. Haciendo clic...")
                    await postular_btn.click()
                    await self.browser_manager.random_delay(2.5, 3.5)

                    # Verificar si se desplegó un modal de inicio de sesión o registro
                    from adapters.auth_helper import AuthRegistrationHelper
                    auth_helper = AuthRegistrationHelper(self.llm.profile)
                    if await auth_helper.is_auth_barrier(page):
                        print("[Bumeran] 🔐 Modal de autenticación/registro detectado en Bumeran. Ejecutando AuthHelper...")
                        await auth_helper.handle_auth_or_registration(page)
                        await self.browser_manager.random_delay(2.5, 4.0)
                else:
                    # Si no hay botón ni texto de postulado
                    return {"status": "expired", "reason": "El aviso ha finalizado o ya no admite postulaciones en Bumeran."}

            # 3. Detectar si existe el banner de preguntas pendientes
            # Ej: "Tienes preguntas sin responder - Contesta las preguntas para aumentar tus chances"
            banner_preguntas = await page.query_selector(
                'div[role="button"]:has-text("Tienes preguntas sin responder"), '
                'p:has-text("Tienes preguntas sin responder"), '
                'div[id="section-postular-bar"] div[role="button"]'
            )
            if banner_preguntas:
                print("[Bumeran] ⚠️ Banner 'Tienes preguntas sin responder' detectado. Abriendo cuestionario...")
                await banner_preguntas.click()
                await self.browser_manager.random_delay(2.0, 3.0)

            # 4. Procesar campos de preguntas (Textareas con name="name-pregunta-...")
            textareas = await page.query_selector_all('textarea[name^="name-pregunta-"], textarea[id^="id-pregunta-"]')
            if not textareas:
                # Si usan otra clase o contenedor
                textareas = await page.query_selector_all("div[class*='Pregunta'] textarea, div[class*='Question'] textarea")

            if textareas:
                print(f"[Bumeran] Se encontraron {len(textareas)} preguntas abiertas para responder.")
                for ta in textareas:
                    # Extraer texto de la pregunta (del atributo label, id o contenedor padre)
                    q_text = await ta.get_attribute("label") or ""
                    if not q_text:
                        ta_id = await ta.get_attribute("id") or ""
                        if ta_id:
                            label_elem = await page.query_selector(f"div[for='{ta_id}'], label[for='{ta_id}']")
                            if label_elem:
                                q_text = (await label_elem.inner_text()).strip()
                    if not q_text:
                        q_text = await ta.get_attribute("placeholder") or "Pregunta de postulación"

                    ans = self.llm.answer_screening_question(
                        q_text,
                        location=job_data.get("location", "Lima, Perú"),
                        platform=self.platform_name
                    )
                    print(f"[Bumeran] Pregunta: '{q_text[:70]}...' -> Respuesta generada.")
                    await ta.fill(ans)
                    qa_history.append({"question": q_text, "answer": ans})
                    await self.browser_manager.random_delay(0.5, 1.2)

            # 5. Procesar preguntas de selección (Radio buttons o Selects)
            radio_groups = await page.query_selector_all("div[class*='Pregunta']:has(input[type='radio'])")
            for rg in radio_groups:
                try:
                    label_elem = await rg.query_selector("label, p, span")
                    q_text = (await label_elem.inner_text()).strip() if label_elem else "Pregunta de opciones"
                    radio_inputs = await rg.query_selector_all("input[type='radio']")
                    options = []
                    for r in radio_inputs:
                        r_lbl = await rg.query_selector(f"label[for='{await r.get_attribute('id')}']")
                        if r_lbl:
                            options.append((await r_lbl.inner_text()).strip())
                    
                    ans = self.llm.answer_screening_question(
                        q_text,
                        options=options,
                        location=job_data.get("location", "Lima, Perú"),
                        platform=self.platform_name
                    )
                    # Marcar la opción seleccionada
                    for idx, opt in enumerate(options):
                        if opt.lower() == ans.lower() or ans.lower() in opt.lower():
                            await radio_inputs[idx].check()
                            break
                    qa_history.append({"question": q_text, "answer": ans})
                except Exception as r_err:
                    print(f"[Bumeran] Error procesando radios: {r_err}")

            # 6. Guardar/Enviar respuestas
            responder_btn = await page.query_selector(
                'button:has-text("Responder"), '
                'button[type="submit"]:has-text("Responder"), '
                'button:has-text("Guardar"), '
                'button[type="submit"]:has-text("Guardar")'
            )
            if responder_btn:
                print("[Bumeran] Botón 'Responder' encontrado. Enviando respuestas...")
                await responder_btn.click()
                await self.browser_manager.random_delay(3.0, 4.5)
                print("[Bumeran] Respuestas enviadas exitosamente al reclutador.")

            return {
                "status": "success",
                "qa": qa_history,
                "notes": f"Postulación procesada en Bumeran. {len(qa_history)} preguntas respondidas." if qa_history else "Postulación registrada en Bumeran."
            }

        except Exception as e:
            print(f"[Bumeran] Error en postulación: {e}")
            return {"status": "failed", "reason": str(e), "qa": qa_history}
        finally:
            await page.close()

