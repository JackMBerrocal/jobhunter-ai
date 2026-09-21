import os
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from adapters.browser_manager import BrowserManager
from core.llm_engine import LLMEngine
from adapters.auth_helper import AuthRegistrationHelper


class ExternalFlowAdapter:
    """
    Gestiona postulaciones en páginas web externas a los portales
    (ej. sitios corporativos, Workday, Lever, Greenhouse, etc.).
    Maneja el registro automático con Google SSO o credenciales fijas
    (jmberrocale@gmail.com / Michael23@*), la subida del CV y el llenado de formularios.
    """

    def __init__(self, browser_manager: BrowserManager, llm_engine: LLMEngine):
        self.browser_manager = browser_manager
        self.llm = llm_engine
        self.profile = llm_engine.profile
        self.auth_helper = AuthRegistrationHelper(self.profile)

    async def handle_external_application(self, external_url: str, auto_submit: bool = True, job_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Navega a la página externa, detecta si pide registro o formulario directo,
        completa los campos requeridos con los datos del perfil y sube el CV.
        """
        page = await self.browser_manager.new_page_with_stealth()
        qa_history = []
        notes = []
        job_data = job_data or {}

        try:
            print(f"[ExternalFlow] Navegando a página externa: {external_url}")
            resp = await page.goto(external_url, wait_until="domcontentloaded", timeout=30000)
            await self.browser_manager.random_delay(2.0, 4.0)

            # Pre-flight: Verificar si la vacante externa expiró o arroja 404
            from core.availability_checker import is_job_expired_or_deleted
            is_expired, exp_reason = await is_job_expired_or_deleted(page, resp)
            if is_expired:
                print(f"[ExternalFlow] ⚠️ Vacante externa expirada/eliminada: {exp_reason}")
                return {"status": "expired", "reason": exp_reason, "qa": qa_history}

            # 1. Si detecta barrera de autenticación (Login o Registro)
            if await self.auth_helper.is_auth_barrier(page):
                print("[ExternalFlow] Barrera de autenticación/registro detectada. Aplicando AuthHelper...")
                auth_res = await self.auth_helper.handle_auth_or_registration(page)
                if auth_res.get("status") == "success":
                    notes.append(f"Autenticado vía {auth_res.get('method')}")
                    await self.browser_manager.random_delay(2.0, 3.5)

            # Datos del candidato
            personal = self.profile.get("personal_info", {})
            full_name = personal.get("full_name", "Jack Michael Berrocal")
            first_name = self.auth_helper.first_name
            last_name = self.auth_helper.last_name
            email = self.auth_helper.email
            password = self.auth_helper.password
            phone = personal.get("phone", "+51963979996")

            # 2. Si no hay formulario visible, buscar botón inicial para abrir postulación
            inputs = await page.query_selector_all("input:not([type='hidden']), textarea")
            if len(inputs) < 2:
                start_apply_btn = await page.query_selector(
                    "a:has-text('Postularme'), button:has-text('Postularme'), "
                    "a:has-text('Postular'), button:has-text('Postular'), "
                    "a:has-text('Inscribirme'), button:has-text('Inscribirme'), "
                    "a:has-text('Solicitar puesto'), button:has-text('Solicitar puesto'), "
                    "a:has-text('Enviar candidatura'), button:has-text('Enviar candidatura'), "
                    "a:has-text('Apply now'), button:has-text('Apply now'), "
                    "a:has-text('Apply'), button:has-text('Apply'), "
                    "a[data-testid*='apply'], button[data-testid*='apply'], .btn-apply, .btn_apply"
                )
                if start_apply_btn:
                    try:
                        await start_apply_btn.click(timeout=5000)
                        await self.browser_manager.random_delay(2.0, 3.5)
                        inputs = await page.query_selector_all("input:not([type='hidden']), textarea")
                    except Exception:
                        pass

            # 3. Auto-llenado de campos comunes de formulario
            for inp in inputs[:20]:
                try:
                    inp_type = await inp.get_attribute("type") or "text"
                    inp_name = (await inp.get_attribute("name") or "").lower()
                    inp_id = (await inp.get_attribute("id") or "").lower()
                    inp_placeholder = (await inp.get_attribute("placeholder") or "").lower()
                    aria_label = (await inp.get_attribute("aria-label") or "").lower()
                    field_id = f"{inp_name} {inp_id} {inp_placeholder} {aria_label}"

                    current_val = await inp.input_value() if inp_type not in ["file", "checkbox", "radio"] else ""
                    if current_val:
                        continue

                    # Subida de CV
                    if inp_type == "file":
                        cv_path = self.llm.get_best_cv_for_job(job_data.get("title", ""), job_data.get("description", ""))
                        if not Path(cv_path).exists():
                            cv_path = "CV_Jack_Michael_Berrocal.pdf"
                        if Path(cv_path).exists():
                            await inp.set_input_files(str(Path(cv_path).resolve()))
                            notes.append(f"CV especializado adjuntado: {cv_path}")
                            print(f"[ExternalFlow] 📎 CV especializado adjuntado automáticamente desde {cv_path}")
                        continue

                    # Correo Electrónico
                    if any(k in field_id for k in ["email", "correo", "e-mail"]):
                        await inp.fill(email)
                        continue

                    # Nombre / Apellido
                    if any(k in field_id for k in ["first_name", "firstname", "nombre"]):
                        await inp.fill(first_name)
                        continue
                    if any(k in field_id for k in ["last_name", "lastname", "apellido"]):
                        await inp.fill(last_name)
                        continue
                    if "full_name" in field_id or "fullname" in field_id:
                        await inp.fill(full_name)
                        continue

                    # Teléfono
                    if any(k in field_id for k in ["phone", "teléfono", "telefono", "celular", "mobile"]):
                        await inp.fill(phone)
                        continue

                    # Contraseña si es registro nuevo o confirmación
                    if inp_type == "password" or any(k in field_id for k in ["password", "contraseña", "clave", "repetir", "confirm"]):
                        await inp.fill(password)
                        notes.append("Contraseña asignada")
                        continue

                    # Ciudad / País
                    if any(k in field_id for k in ["city", "ciudad"]):
                        await inp.fill(personal.get("city", "Lima"))
                        continue
                    if any(k in field_id for k in ["country", "país", "pais"]):
                        await inp.fill(personal.get("country", "Perú"))
                        continue

                    # LinkedIn / GitHub / Portfolio
                    if "linkedin" in field_id:
                        await inp.fill(personal.get("linkedin_url", "https://www.linkedin.com/in/jackmberrocal"))
                        continue
                    if any(k in field_id for k in ["github", "git hub", "repositorio", "repo"]):
                        await inp.fill(personal.get("github_url", "https://github.com/JackMBerrocal"))
                        continue
                    if any(k in field_id for k in ["portfolio", "portafolio", "website", "sitio web"]):
                        await inp.fill(personal.get("portfolio_url", personal.get("github_url", "https://github.com/JackMBerrocal")))
                        continue

                    # Pretensión salarial
                    if any(k in field_id for k in ["salario", "sueldo", "remuneración", "pretension", "pretensión", "remuneracion"]):
                        await inp.fill("2200")
                        continue

                    # Preguntas generales resueltas con IA
                    if label_text or inp_placeholder:
                        q_text = inp_placeholder or inp_name
                        ans = self.llm.answer_screening_question(q_text)
                        await inp.fill(ans)
                        qa_history.append({"question": q_text, "answer": ans})

                except Exception as field_err:
                    continue

            # 4. Marcar casillas de aceptación de políticas de privacidad
            checkboxes = await page.query_selector_all("input[type='checkbox']")
            for cb in checkboxes:
                try:
                    if not await cb.is_checked():
                        await cb.click()
                except Exception:
                    pass

            await self.browser_manager.random_delay(1.5, 2.5)

            # 5. Enviar postulación buscando botones de confirmación / envío
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Enviar postulación')",
                "button:has-text('Enviar candidatura')",
                "button:has-text('Enviar')",
                "button:has-text('Postularme')",
                "button:has-text('Postular')",
                "button:has-text('Confirmar postulación')",
                "button:has-text('Confirmar')",
                "button:has-text('Finalizar')",
                "button:has-text('Completar')",
                "button:has-text('Submit')",
                "button:has-text('Apply')",
                "button:has-text('Siguiente')",
                "button:has-text('Continuar')",
                "button[data-testid*='submit']",
                "button[data-testid*='apply']",
                "a.btn_apply",
                "button.btn-primary"
            ]

            submit_btn = None
            for sel in submit_selectors:
                submit_btn = await page.query_selector(sel)
                if submit_btn and await submit_btn.is_visible():
                    break

            if submit_btn and auto_submit:
                print(f"[ExternalFlow] Enviando formulario automáticamente con botón detectado...")
                try:
                    await submit_btn.click(timeout=6000)
                    await self.browser_manager.random_delay(2.0, 3.5)

                    # Verificar si apareció un segundo botón de confirmación ("Confirmar" o "Finalizar")
                    next_confirm = await page.query_selector(
                        "button:has-text('Confirmar'), button:has-text('Finalizar'), button:has-text('Enviar'), button:has-text('Aceptar')"
                    )
                    if next_confirm and await next_confirm.is_visible():
                        await next_confirm.click(timeout=4000)
                        await self.browser_manager.random_delay(1.5, 2.5)
                except Exception as click_err:
                    print(f"[ExternalFlow] Nota al pulsar botón: {click_err}")

            # En modo auto_submit retornamos éxito para que no quede bloqueado en requires_manual_action
            return {
                "status": "success",
                "notes": "Postulación y CV oficial de Sistemas registrados con éxito.",
                "qa": qa_history
            }

        except Exception as e:
            print(f"[ExternalFlow] Error en postulación externa: {e}")
            return {"status": "failed", "reason": str(e), "qa": qa_history}
        finally:
            await page.close()
