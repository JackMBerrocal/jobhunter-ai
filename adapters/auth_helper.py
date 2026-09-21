import re
import asyncio
from typing import Dict, Any, List, Optional
from playwright.async_api import Page, ElementHandle


class AuthRegistrationHelper:
    """
    Módulo inteligente para automatizar el inicio de sesión y registro de cuentas
    en cualquier portal de empleo, ATS o página web corporativa.
    
    Regla de Prioridad Obligatoria:
    1. Intentar inicio de sesión / registro con Google SSO (jmberrocale@gmail.com).
    2. Si Google no está disponible o no funciona, proceder al Auto-Registro con:
       - Correo: jmberrocale@gmail.com
       - Contraseña: Michael23@* (aplicada en contraseña y confirmación de contraseña)
       - Nombre Completo: Jack Michael Berrocal
       - Teléfono: +51 963979996
       - Aceptación automática de términos y políticas.
    3. Si la página es únicamente de Login, ingresar con jmberrocale@gmail.com y Michael23@*.
    """

    def __init__(self, profile: Optional[Dict[str, Any]] = None):
        self.profile = profile or {}
        auth = self.profile.get("auth_credentials", {})
        personal = self.profile.get("personal_info", {})
        
        self.email = auth.get("email") or personal.get("email", "jmberrocale@gmail.com")
        self.password = auth.get("password") or personal.get("password", "Michael23@*")
        self.full_name = auth.get("full_name") or personal.get("full_name", "Jack Michael Berrocal")
        self.first_name = auth.get("first_name") or personal.get("first_name", "Jack Michael")
        self.last_name = auth.get("last_name") or personal.get("last_name", "Berrocal")
        self.phone = auth.get("phone") or personal.get("phone", "+51 963979996")
        self.country = auth.get("country") or personal.get("country", "Perú")
        self.city = auth.get("city") or personal.get("city", "Lima")
        self.use_google_first = auth.get("use_google_first", True)

    async def is_auth_barrier(self, page: Page) -> bool:
        """Determina si la página actual o modal exige autenticación o registro."""
        curr_url = page.url.lower()
        if any(k in curr_url for k in ["/login", "/signin", "/sign-in", "/auth", "/register", "/signup", "/sign-up", "/crear-cuenta", "/postulantes", "accounts.google"]):
            return True
        
        # Verificar si hay modal de login o formulario de contraseña visible
        pw_input = await page.query_selector("input[type='password']")
        if pw_input and await pw_input.is_visible():
            return True
            
        login_modal = await page.query_selector("div[id*='login' i], div[class*='login-modal' i], div[role='dialog']:has(input)")
        if login_modal and await login_modal.is_visible():
            return True
            
        return False

    async def attempt_google_auth(self, page: Page) -> Dict[str, Any]:
        """
        Intenta iniciar sesión o registrarse usando el botón de Google SSO.
        """
        print("[AuthHelper] 🔍 Buscando botón de inicio/registro rápido con Google...")
        google_selectors = [
            "button:has-text('Continuar con Google')",
            "button:has-text('Iniciar sesión con Google')",
            "button:has-text('Sign in with Google')",
            "button:has-text('Sign up with Google')",
            "button:has-text('Google')",
            "a:has-text('Continuar con Google')",
            "a:has-text('Iniciar con Google')",
            "a:has-text('Google')",
            "[data-provider='google']",
            "[aria-label*='Google' i]",
            "a[href*='accounts.google.com']",
            "a[href*='oauth'][href*='google']",
            "button[id*='google' i]",
            "div[id*='google' i][role='button']",
            ".btn-google",
            "#google-signin-btn"
        ]

        google_btn = None
        for sel in google_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    google_btn = elem
                    print(f"[AuthHelper] 🟢 Botón de Google detectado con selector: {sel}")
                    break
            except Exception:
                continue

        if not google_btn:
            print("[AuthHelper] ℹ️ No se detectó botón de Google SSO en la página actual.")
            return {"status": "not_available", "reason": "No Google button found"}

        try:
            # Escuchar posible popup de OAuth
            popup_page = None
            try:
                async with page.expect_popup(timeout=4000) as popup_info:
                    await google_btn.click()
                popup_page = await popup_info.value
            except Exception:
                # Si no abre popup sino que redirige en la misma pestaña
                pass

            target_tab = popup_page or page
            await target_tab.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(2.5)

            # Si estamos en accounts.google.com, seleccionar la cuenta de Jack
            current_target_url = target_tab.url.lower()
            if "accounts.google.com" in current_target_url:
                print("[AuthHelper] Detectada pantalla de selección de cuenta de Google...")
                jack_acc = await target_tab.query_selector(
                    f"div:has-text('{self.email}'), "
                    f"div[data-identifier='{self.email}'], "
                    f"li:has-text('{self.email}'), "
                    f"div:has-text('Jack Michael')"
                )
                if jack_acc:
                    print(f"[AuthHelper] Seleccionando cuenta de Google de Jack ({self.email})...")
                    await jack_acc.click()
                    await asyncio.sleep(2.5)

                # Si pide confirmar permisos / continuar
                confirm_btn = await target_tab.query_selector("button:has-text('Continuar'), button:has-text('Confirmar'), button:has-text('Next')")
                if confirm_btn and await confirm_btn.is_visible():
                    await confirm_btn.click()
                    await asyncio.sleep(2.5)

            # Si se usó popup, esperar a que se cierre
            if popup_page:
                try:
                    await popup_page.wait_for_event("close", timeout=6000)
                except Exception:
                    pass

            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(2.0)

            # Comprobar si ya no estamos en login/auth
            if not await self.is_auth_barrier(page):
                print("[AuthHelper] ✅ ¡Autenticado exitosamente con Cuenta de Google!")
                return {"status": "success", "method": "google_sso", "email": self.email}

        except Exception as e:
            print(f"[AuthHelper] ⚠️ Intento de Google SSO no concluyó: {e}")

        return {"status": "failed", "reason": "Google SSO could not complete"}

    async def attempt_manual_registration(self, page: Page) -> Dict[str, Any]:
        """
        Completa el formulario de registro con correo jmberrocale@gmail.com y clave Michael23@*.
        Rellena ambos campos de contraseña (contraseña y confirmación) y acepta términos.
        """
        print(f"[AuthHelper] 📝 Iniciando Auto-Registro con correo '{self.email}' y clave fijada...")

        # 1. Si la página está en modo "Iniciar Sesión" y NO hay campos de registro visibles
        has_reg_form = await page.query_selector("input[name*='confirm' i], input[placeholder*='repet' i], form[action*='register' i], form[action*='signup' i]")
        if not has_reg_form:
            signup_switch_selectors = [
                "a:has-text('Crear cuenta')",
                "a:has-text('Registrarse')",
                "a:has-text('Sign up')",
                "a:has-text('Regístrate')",
                "button:not([type='submit']):has-text('Crear cuenta')",
                "button:not([type='submit']):has-text('Registrarse')",
                "button:not([type='submit']):has-text('Sign up')",
                "a[href*='register']",
                "a[href*='signup']",
                "a[href*='registro']"
            ]
            for sel in signup_switch_selectors:
                try:
                    switch_btn = await page.query_selector(sel)
                    if switch_btn and await switch_btn.is_visible():
                        print(f"[AuthHelper] Cambiando a pestaña de registro: {sel}")
                        await switch_btn.click()
                        await asyncio.sleep(2.0)
                        break
                except Exception:
                    continue

        # 2. Localizar y rellenar campos de formulario
        inputs = await page.query_selector_all("input:not([type='hidden']), textarea")
        filled_fields = []
        password_count = 0

        for inp in inputs:
            try:
                if not await inp.is_visible():
                    continue

                inp_type = (await inp.get_attribute("type") or "text").lower()
                inp_name = (await inp.get_attribute("name") or "").lower()
                inp_id = (await inp.get_attribute("id") or "").lower()
                placeholder = (await inp.get_attribute("placeholder") or "").lower()
                aria_label = (await inp.get_attribute("aria-label") or "").lower()
                field_sig = f"{inp_name} {inp_id} {placeholder} {aria_label}"

                # Ignorar checkboxes y radios por ahora
                if inp_type in ["checkbox", "radio", "file", "submit", "button"]:
                    continue

                # Campo de Contraseña (Contraseña o Confirmación de Contraseña)
                if inp_type == "password" or any(k in field_sig for k in ["password", "contraseña", "clave", "pass", "repetir", "confirm"]):
                    await inp.fill(self.password)
                    password_count += 1
                    filled_fields.append(f"Contraseña #{password_count} (Michael23@*)")
                    print(f"[AuthHelper] 🔑 Contraseña asignada en campo: {inp_name or inp_id or inp_type}")
                    continue

                # Campo de Correo Electrónico
                if inp_type == "email" or any(k in field_sig for k in ["email", "correo", "e-mail", "usuario", "user"]):
                    await inp.fill(self.email)
                    filled_fields.append("Correo (jmberrocale@gmail.com)")
                    print(f"[AuthHelper] 📧 Correo asignado: {self.email}")
                    continue

                # Nombres
                if any(k in field_sig for k in ["first_name", "firstname", "first name", "nombre"]) and not any(k in field_sig for k in ["completo", "full"]):
                    await inp.fill(self.first_name)
                    filled_fields.append("Nombre (Jack Michael)")
                    continue

                # Apellidos
                if any(k in field_sig for k in ["last_name", "lastname", "last name", "apellido"]):
                    await inp.fill(self.last_name)
                    filled_fields.append("Apellido (Berrocal)")
                    continue

                # Nombre Completo
                if any(k in field_sig for k in ["full_name", "fullname", "nombre completo", "name"]):
                    await inp.fill(self.full_name)
                    filled_fields.append("Nombre Completo (Jack Michael Berrocal)")
                    continue

                # Teléfono
                if inp_type == "tel" or any(k in field_sig for k in ["phone", "teléfono", "telefono", "celular", "mobile"]):
                    phone_val = self.phone if "+51" in self.phone else f"+51{self.phone}"
                    await inp.fill(phone_val)
                    filled_fields.append("Teléfono")
                    continue

                # Ciudad o País
                if any(k in field_sig for k in ["city", "ciudad"]):
                    await inp.fill(self.city)
                    continue
                if any(k in field_sig for k in ["country", "país", "pais"]):
                    await inp.fill(self.country)
                    continue

            except Exception as inp_err:
                print(f"[AuthHelper] Campo omitido: {inp_err}")

        # 3. Aceptar casillas obligatorias de Términos y Condiciones / Privacidad
        checkboxes = await page.query_selector_all("input[type='checkbox']")
        for cb in checkboxes:
            try:
                if await cb.is_visible() and not await cb.is_checked():
                    cb_id = (await cb.get_attribute("id") or "").lower()
                    cb_name = (await cb.get_attribute("name") or "").lower()
                    # Aceptar términos y condiciones
                    if any(k in f"{cb_id} {cb_name}" for k in ["term", "privac", "condit", "agree", "accept", "legal", "politica"]):
                        await cb.click()
                        print(f"[AuthHelper] Casilla de términos marcada: {cb_id or cb_name}")
                    else:
                        # Si solo hay 1 o 2 checkboxes en el registro, marcarlos
                        if len(checkboxes) <= 2:
                            await cb.click()
            except Exception:
                pass

        await asyncio.sleep(1.0)

        # 4. Enviar formulario de registro
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Registrarse')",
            "button:has-text('Crear cuenta')",
            "button:has-text('Sign up')",
            "button:has-text('Regístrate')",
            "button:has-text('Continuar')",
            "button:has-text('Registrarme')",
            "button:has-text('Create account')",
            "button:has-text('Join')"
        ]

        submitted = False
        for s_sel in submit_selectors:
            try:
                s_btn = await page.query_selector(s_sel)
                if s_btn and await s_btn.is_visible():
                    print(f"[AuthHelper] 🚀 Haciendo clic en botón de envío: {s_sel}")
                    await s_btn.click()
                    submitted = True
                    await asyncio.sleep(3.0)
                    break
            except Exception:
                continue

        if submitted:
            print("[AuthHelper] ✅ Formulario de Auto-Registro enviado exitosamente.")
            return {
                "status": "success",
                "method": "manual_registration",
                "email": self.email,
                "fields_filled": filled_fields
            }
        else:
            return {
                "status": "partial",
                "method": "manual_registration",
                "fields_filled": filled_fields,
                "notes": "Campos rellenados, botón de envío final no detectado con selectores estándar."
            }

    async def attempt_manual_login(self, page: Page) -> Dict[str, Any]:
        """
        Ingresa con jmberrocale@gmail.com y Michael23@* si la página es estrictamente de login.
        """
        print(f"[AuthHelper] 🔑 Intentando inicio de sesión directo con '{self.email}'...")
        try:
            email_input = await page.query_selector(
                "input[type='email'], input[name*='email' i], input[id*='email' i], input[placeholder*='correo' i], input[placeholder*='email' i], input[name*='user' i]"
            )
            pw_input = await page.query_selector(
                "input[type='password'], input[name*='password' i], input[id*='password' i], input[name*='clave' i]"
            )

            if email_input and pw_input:
                await email_input.fill(self.email)
                await pw_input.fill(self.password)
                await asyncio.sleep(0.5)

                login_btn = await page.query_selector(
                    "button[type='submit'], input[type='submit'], button:has-text('Iniciar sesión'), button:has-text('Ingresar'), button:has-text('Log in'), button:has-text('Sign in'), button:has-text('Entrar')"
                )
                if login_btn:
                    await login_btn.click()
                    await asyncio.sleep(3.0)
                    print("[AuthHelper] ✅ Formulario de login enviado con éxito.")
                    return {"status": "success", "method": "manual_login", "email": self.email}

        except Exception as e:
            print(f"[AuthHelper] Error en login manual: {e}")

        return {"status": "failed", "reason": "No se pudo completar el login manual"}

    async def handle_auth_or_registration(self, page: Page, mode: str = "auto") -> Dict[str, Any]:
        """
        Orquesta el flujo integral de autenticación / registro:
        1. Intenta Google SSO primero si está habilitado.
        2. Si no es posible o falla, procede al registro manual con Michael23@*.
        3. Si la página es solo de login, ejecuta inicio de sesión con Michael23@*.
        """
        # Comprobar si realmente hay una barrera de autenticación
        if not await self.is_auth_barrier(page):
            return {"status": "already_authenticated", "notes": "No se detectó barrera de autenticación"}

        # 1. Prioridad: Cuenta de Google
        if self.use_google_first:
            g_res = await self.attempt_google_auth(page)
            if g_res.get("status") == "success":
                return g_res

        # 2. Si Google no está o falló: Auto-registro con Michael23@*
        reg_res = await self.attempt_manual_registration(page)
        if reg_res.get("status") == "success":
            return reg_res

        # 3. Fallback a Login directo con Michael23@*
        log_res = await self.attempt_manual_login(page)
        return log_res
