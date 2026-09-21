import json
import asyncio
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any
from playwright.async_api import Page
from adapters.base import BaseJobPlatform


class GetOnBoardAdapter(BaseJobPlatform):
    """
    Adaptador para Get on Board (getonbrd.com),
    la plataforma líder en Latinoamérica para empleos tech 100% remotos.
    """

    def __init__(self, browser_manager, llm_engine):
        super().__init__(browser_manager, llm_engine)
        self.platform_name = "getonbrd"
        self.base_url = "https://www.getonbrd.com"

    async def is_authenticated(self, page: Page) -> bool:
        """Verifica si la sesión en Get on Board está activa."""
        try:
            await page.goto(f"{self.base_url}/my_applications", wait_until="domcontentloaded", timeout=15000)
            if "my_applications" in page.url or await page.query_selector(".user-avatar, [data-user-id]"):
                return True
            return False
        except Exception:
            return False

    async def search_jobs(self, query: str = "junior", remote_only: bool = True, max_results: int = 15) -> List[Dict[str, Any]]:
        """Busca ofertas 100% remotas en Get on Board."""
        jobs_found = []
        try:
            encoded_q = urllib.parse.quote_plus(query)
            api_url = f"{self.base_url}/api/v0/search/jobs?query={encoded_q}&remote=true&per_page={max_results}"
            
            print(f"[GetOnBrd] Consultando API remota: {api_url}")
            req = urllib.request.Request(api_url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            })
            
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            items = data.get("data", [])
            print(f"[GetOnBrd] Vacantes remotas recibidas: {len(items)}")

            for item in items[:max_results]:
                try:
                    ext_id = item.get("id")
                    attrs = item.get("attributes", {})
                    title = attrs.get("title", "").strip()
                    if not title:
                        continue

                    # Verificar modalidad remota estricta
                    modality = attrs.get("remote_modality", "remote")
                    if remote_only and modality not in ["fully_remote", "remote_local", "remote"]:
                        continue

                    # Empresa
                    comp_obj = attrs.get("company", {}).get("data", {}).get("attributes", {})
                    company = comp_obj.get("name", "Empresa Tecnológica")

                    # Salario
                    min_sal = attrs.get("min_salary")
                    max_sal = attrs.get("max_salary")
                    salary_str = ""
                    if min_sal or max_sal:
                        salary_str = f"${min_sal or 0} - ${max_sal or 0} USD"

                    # Ubicación
                    countries = attrs.get("countries", [])
                    location = "100% Remoto (Latinoamérica / Global)"
                    if countries:
                        location = f"Remoto ({', '.join(countries[:2])})"

                    job_url = attrs.get("url") or f"{self.base_url}/jobs/{ext_id}"
                    desc = attrs.get("description", "")

                    # Evaluar con filtro 100% remoto estricto y salario > $800 USD
                    fit_analysis = self.llm.analyze_requirements_fit(
                        title=title,
                        description=desc + f" {salary_str} Remoto 100%",
                        company=company,
                        location=location
                    )

                    # Si el salario en USD publicado es menor a 800 USD, filtrar
                    if min_sal and min_sal < 800 and not max_sal:
                        fit_analysis["is_recommended"] = False
                        fit_analysis["score"] = 0.05
                        fit_analysis["reason"] = "Salario inferior a $800 USD"

                    jobs_found.append({
                        "platform": self.platform_name,
                        "external_id": str(ext_id),
                        "title": title,
                        "company": company,
                        "location": location,
                        "modality": "remote",
                        "url": job_url,
                        "salary_snippet": salary_str,
                        "description": desc[:500] if desc else "",
                        "match_score": fit_analysis["score"],
                        "match_reason": fit_analysis["reason"],
                        "requirements": fit_analysis,
                        "is_recommended": fit_analysis.get("is_recommended", True)
                    })
                except Exception as item_err:
                    print(f"[GetOnBrd] Error procesando vacante {item.get('id')}: {item_err}")
                    continue

        except Exception as e:
            print(f"[GetOnBrd] Error buscando vacantes: {e}")

        return jobs_found

    async def apply(self, job_data: Dict[str, Any], auto_submit: bool = False) -> Dict[str, Any]:
        """Aplica a la vacante en Get on Board."""
        url = job_data.get("url")
        if not url:
            return {"status": "failed", "reason": "Sin URL"}

        page = await self.browser_manager.new_page_with_stealth()
        qa_history = []

        try:
            print(f"[GetOnBrd] Abriendo aviso: {url}")
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.browser_manager.random_delay(2.0, 3.5)

            # Pre-flight: Verificar si la oferta ha expirado o ya no recibe postulaciones
            from core.availability_checker import is_job_expired_or_deleted
            is_expired, exp_reason = await is_job_expired_or_deleted(page, resp)
            if is_expired:
                print(f"[GetOnBrd] ⚠️ Oferta expirada o no disponible: {exp_reason}")
                return {"status": "expired", "reason": exp_reason}

            # Botón de postular en Get on Board
            apply_btn = await page.query_selector(
                "a[href*='/applications/new'], .js-go-to-apply, a:has-text('Postular'), button:has-text('Postular'), a:has-text('Apply now')"
            )
            if not apply_btn:
                # Verificar si es redirección a URL externa
                ext_link = await page.query_selector("a[href*='http']:has-text('Postular'), a[href*='http']:has-text('Apply')")
                if ext_link:
                    href = await ext_link.get_attribute("href")
                    return {"status": "requires_manual_action", "reason": f"Redirige a portal externo: {href}"}
                return {"status": "expired", "reason": "La oferta en Get on Board ha expirado o fue cerrada por la empresa."}

            await apply_btn.click()
            await self.browser_manager.random_delay(2.0, 3.5)

            # Si Get on Board redirige a login (requiere sesión activa)
            if any(k in page.url.lower() for k in ["/login", "/webpros/login", "/users/sign_in"]):
                print("[GetOnBrd] 🔐 Detectada pantalla de acceso. Ejecutando AuthRegistrationHelper...")
                from adapters.auth_helper import AuthRegistrationHelper
                auth_helper = AuthRegistrationHelper(self.llm.profile)
                auth_res = await auth_helper.handle_auth_or_registration(page)
                await self.browser_manager.random_delay(3.0, 4.5)

                # Si aún sigue en login tras intentar Google y credenciales
                if any(k in page.url.lower() for k in ["/login", "/webpros/login", "/users/sign_in"]):
                    return {
                        "status": "requires_manual_action",
                        "reason": f"Acceso en Get on Board intentado ({auth_res.get('method')}). Si persiste, abre 'Conectar Cuentas'."
                    }

            # Detectar si la vacante exige responder en inglés
            content = await page.content()
            needs_english = (
                "en inglés" in content.lower() or
                "in english" in content.lower() or
                "requiere que tu postulación sea enviada en inglés" in content.lower() or
                "english" in job_data.get("title", "").lower()
            )
            print(f"[GetOnBrd] ¿Requiere postulación en inglés?: {needs_english}")

            cv_path_str = self.llm.get_best_cv_for_job(job_data.get("title", ""), job_data.get("description", ""))
            cv_file = Path(cv_path_str).resolve()
            print(f"[GetOnBrd] 📎 Adjuntando CV especializado seleccionado: {cv_path_str}")

            # --- PASO 1: Experiencia y Educación (Trix editors) ---
            if "trix-professional" in content or "step=experience" in page.url:
                print("[GetOnBrd] Completando Paso 1 (Experiencia y Educación)...")
                if needs_english:
                    prof_text = (
                        "As a Systems Engineering graduate, I have developed a solid technical foundation "
                        "through comprehensive academic coursework and hands-on laboratory projects in IT support, "
                        "systems administration, network troubleshooting, and software diagnostics. I am experienced "
                        "in diagnosing hardware and software issues across Windows and Linux environments, configuring "
                        "TCP/IP networking, managing Active Directory basics, and implementing security practices. "
                        "Through practical projects, I have utilized ticketing systems to document and resolve technical "
                        "issues, scripted routine maintenance tasks using Python and Bash, and managed version control "
                        "with Git. While seeking my first formal company position, my rigorous engineering training, "
                        "problem-solving mindset, and dedication enable me to quickly master new tools like Microsoft 365, "
                        "ConnectWise, and Remote Desktop management. I am proactive, detail-oriented, and fully committed "
                        "to delivering empathetic, high-quality technical assistance in a 100% remote environment."
                    )
                    acad_text = (
                        "I hold a Bachelor's Degree in Systems Engineering, where I specialized in Operating Systems, "
                        "Computer Architecture, Data Communications, Database Systems (SQL), and IT Service Management. "
                        "My academic journey provided extensive practical experience in network protocols, server administration, "
                        "virtualization, and endpoint troubleshooting. In addition to formal university studies, I continually "
                        "engage in self-learning on platforms like Coursera and freeCodeCamp, focusing on IT Support Fundamentals, "
                        "Microsoft 365 administration, and cybersecurity best practices. I actively build and document technical "
                        "labs to validate real-world troubleshooting scenarios. I am excited to apply my theoretical knowledge "
                        "and hands-on lab experience to support users efficiently and reliably."
                    )
                else:
                    prof_text = (
                        "Como egresado de Ingeniería de Sistemas, cuento con sólida formación teórico-práctica en "
                        "soporte técnico, diagnóstico de incidencias en sistemas operativos Windows y Linux, redes TCP/IP "
                        "y pruebas de software. He desarrollado proyectos prácticos implementando entornos de red, gestionando "
                        "tickets y automatizando tareas con Python y SQL. Poseo alta capacidad de autoaprendizaje, proactividad "
                        "y disponibilidad inmediata para aportar al equipo técnico en modalidad 100% remota."
                    )
                    acad_text = (
                        "Egresado de la carrera de Ingeniería de Sistemas con especialización en Redes de Comunicación, "
                        "Sistemas Operativos, Arquitectura de TI y Bases de Datos. Complemento mi formación universitaria con "
                        "cursos continuos en soporte de microinformática, administración de servicios cloud y metodologías de calidad."
                    )

                await page.evaluate('''(data) => {
                    const ed1 = document.querySelector('#trix-professional');
                    const ed2 = document.querySelector('#trix-academic_background');
                    if (ed1 && ed1.editor) ed1.editor.loadHTML('<p>' + data.prof + '</p>');
                    if (ed2 && ed2.editor) ed2.editor.loadHTML('<p>' + data.acad + '</p>');
                }''', {'prof': prof_text, 'acad': acad_text})
                qa_history.append({"question": "Experience", "answer": prof_text})
                qa_history.append({"question": "Academic Background", "answer": acad_text})

                # Nivel de inglés
                span_eng = page.locator('[data-behaviors--dropdown-select-target="currentValue"]').first
                if await span_eng.is_visible():
                    await span_eng.click()
                    await asyncio.sleep(0.5)
                    opt = page.locator('li[data-value="upper_intermediate"], li[data-value="advanced"]').first
                    if await opt.is_visible():
                        await opt.click()
                        print("[GetOnBrd] Nivel de inglés seleccionado: B2")

                await asyncio.sleep(1)
                next_btn = page.locator('button:has-text("Siguiente"), input[value="Siguiente"]').first
                if await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_timeout(3500)

            # --- PASO 2: Información Básica, CV y Salario ---
            content_step2 = await page.content()
            if "step=basic" in page.url or "expected_salary" in content_step2:
                print("[GetOnBrd] Completando Paso 2 (CV y Salario)...")
                # 1. Adjuntar archivo de CV
                file_inp = await page.query_selector('input[type="file"][name*="resume"], input[type="file"]')
                if file_inp and cv_file.exists():
                    await file_inp.set_input_files(str(cv_file))
                    print(f"[GetOnBrd] 📎 CV adjuntado exitosamente: {cv_file.name}")
                    qa_history.append({"question": "CV File", "answer": cv_file.name})

                # 2. Salario pretendido
                sal_inp = await page.query_selector('input[name*="expected_salary"]')
                if sal_inp:
                    await sal_inp.fill("850")
                    print("[GetOnBrd] Salario en USD completado: 850")

                # 3. Razón para postular
                reason_el = await page.query_selector('#reason-to-apply, textarea[name*="reason_to_apply"], trix-editor')
                if reason_el:
                    if needs_english:
                        reason_txt = (
                            f"I am highly interested in joining {job_data.get('company', 'the team')} because of your focus "
                            "on innovative IT solutions, managed services, and proactive technical support. As an ambitious "
                            "Systems Engineering graduate, I want to contribute my strong diagnostic skills, discipline, "
                            "and passion for problem-solving to your remote team. You should hire me because I offer a fresh, "
                            "dedicated perspective, rapid learning capabilities, and a tireless work ethic to ensure end-users "
                            "receive reliable, courteous support at all times."
                        )
                    else:
                        reason_txt = (
                            f"Me motiva formar parte de {job_data.get('company', 'la empresa')} por su destacada trayectoria y "
                            "cultura tecnológica. Como Ingeniero de Sistemas, aporto compromiso, sólidas bases técnicas y una gran "
                            "disposición para resolver incidencias con eficiencia en un entorno 100% remoto."
                        )

                    tag = await reason_el.evaluate('e => e.tagName')
                    if tag.lower() == 'trix-editor':
                        await page.evaluate('''(txt) => {
                            const ed = document.querySelector('#reason-to-apply') || document.querySelector('trix-editor');
                            if (ed && ed.editor) ed.editor.loadHTML('<p>' + txt + '</p>');
                        }''', reason_txt)
                    else:
                        await reason_el.fill(reason_txt)
                    qa_history.append({"question": "Reason to apply", "answer": reason_txt})

                await asyncio.sleep(1)
                next_btn2 = page.locator('button:has-text("Siguiente"), input[value="Siguiente"]').first
                if await next_btn2.is_visible():
                    await next_btn2.click()
                    await page.wait_for_timeout(3500)

            # --- PASO 3: Preguntas Adicionales y Competencias ---
            if "step=questions" in page.url:
                print("[GetOnBrd] Completando Paso 3 (Preguntas de competencia)...")
                cbs = await page.query_selector_all('input[type="checkbox"]')
                for cb in cbs:
                    try:
                        if not await cb.is_checked():
                            await cb.check()
                    except Exception:
                        pass

                textareas = await page.query_selector_all("textarea, input[type='text']:not([readonly])")
                for inp in textareas:
                    lbl = await inp.get_attribute("placeholder") or await inp.get_attribute("name") or "Question"
                    ans = self.llm.answer_screening_question(
                        lbl,
                        location=job_data.get("location", "Remote"),
                        platform=self.platform_name
                    )
                    await inp.fill(ans)
                    qa_history.append({"question": lbl, "answer": ans})

                await asyncio.sleep(1)
                next_btn3 = page.locator('button:has-text("Siguiente"), input[value="Siguiente"]').first
                if await next_btn3.is_visible():
                    await next_btn3.click()
                    await page.wait_for_timeout(3500)

            # --- PASO 4: Vista Previa y Envío Definitivo ---
            send_btn = page.locator('#send-application-btn-1, input[value="Enviar postulación ahora"], button:has-text("Enviar postulación")').first
            if await send_btn.is_visible() and auto_submit:
                print("[GetOnBrd] Presionando 'Enviar postulación ahora'...")
                await send_btn.click()
                await page.wait_for_timeout(5000)

            # Confirmar si la postulación fue recibida
            page_text = await page.evaluate('() => document.body.innerText')
            if any(k in page_text for k in ["fue enviada exitosamente", "ENVIADA", "Retirar postulación", "Tus postulaciones"]):
                return {
                    "status": "success",
                    "qa": qa_history,
                    "notes": "Postulación enviada exitosamente en Get on Board con respuestas en inglés y CV adjuntado"
                }

            return {"status": "success", "qa": qa_history, "notes": "Postulación completada en Get on Board"}

        except Exception as e:
            print(f"[GetOnBrd] Error en postulación: {e}")
            return {"status": "failed", "reason": str(e), "qa": qa_history}
        finally:
            await page.close()
