import asyncio
from pathlib import Path
from adapters.auth_helper import AuthRegistrationHelper
from core.llm_engine import LLMEngine
from adapters.browser_manager import BrowserManager


async def test_auth_helper_unit():
    print("--- [TEST 1] Verificando Inicialización de Credenciales ---")
    llm = LLMEngine()
    auth_helper = AuthRegistrationHelper(llm.profile)
    
    assert auth_helper.email == "jmberrocale@gmail.com", f"Email esperado 'jmberrocale@gmail.com', obtenido: {auth_helper.email}"
    assert auth_helper.password == "Michael23@*", f"Password esperado 'Michael23@*', obtenido: {auth_helper.password}"
    assert auth_helper.full_name == "Jack Michael Berrocal", f"Nombre esperado 'Jack Michael Berrocal', obtenido: {auth_helper.full_name}"
    assert auth_helper.first_name == "Jack Michael"
    assert auth_helper.last_name == "Berrocal"
    assert auth_helper.use_google_first is True
    print(f"✅ Credenciales verificadas con éxito: Email={auth_helper.email}, Password={auth_helper.password}")

    print("\n--- [TEST 2] Verificando Llenado de Formulario con Doble Clave y Términos ---")
    # Crear una página HTML simulada con formulario de registro
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Página de Registro de Empleo</title></head>
    <body>
        <h1>Crea tu cuenta profesional</h1>
        <button id="google-signin-btn">Continuar con Google</button>
        <form id="signup-form" action="#" onsubmit="return false;">
            <input type="text" name="first_name" placeholder="Tu Nombre">
            <input type="text" name="last_name" placeholder="Tu Apellido">
            <input type="email" name="email" placeholder="Correo electrónico">
            <input type="password" name="password" placeholder="Contraseña">
            <input type="password" name="confirm_password" placeholder="Repite tu contraseña">
            <input type="tel" name="phone" placeholder="Celular">
            <label><input type="checkbox" name="terms" id="chk_terms"> Acepto términos y condiciones</label>
            <button type="submit" id="btn_submit_reg">Registrarse Ahora</button>
        </form>
    </body>
    </html>
    """
    temp_html = Path("tests/temp_signup.html")
    temp_html.write_text(html_content, encoding="utf-8")

    bm = BrowserManager(headless=True)
    await bm.initialize()
    page = await bm.new_page_with_stealth()

    try:
        await page.goto(f"file://{temp_html.resolve()}")
        await asyncio.sleep(1)

        # 1. Verificar detección de botón Google
        g_btn = await page.query_selector("button:has-text('Continuar con Google')")
        assert g_btn is not None
        print("✅ Botón de Continuar con Google detectado correctamente.")

        # 2. Ejecutar auto-registro manual
        res = await auth_helper.attempt_manual_registration(page)
        print(f"Resultado de auto-registro: {res}")
        assert res.get("status") == "success"
        assert res.get("email") == "jmberrocale@gmail.com"

        # 3. Comprobar que ambos campos de contraseña tienen 'Michael23@*'
        pw1_val = await page.input_value("input[name='password']")
        pw2_val = await page.input_value("input[name='confirm_password']")
        email_val = await page.input_value("input[name='email']")
        name_val = await page.input_value("input[name='first_name']")
        terms_checked = await page.is_checked("input[name='terms']")

        assert pw1_val == "Michael23@*", f"Password 1 no coincide: {pw1_val}"
        assert pw2_val == "Michael23@*", f"Password 2 (confirmación) no coincide: {pw2_val}"
        assert email_val == "jmberrocale@gmail.com", f"Email no coincide: {email_val}"
        assert terms_checked is True, "Checkbox de términos no fue marcado"

        print("✅ Validación de campos completada:")
        print(f"   - Email en formulario: {email_val}")
        print(f"   - Clave en formulario: {pw1_val}")
        print(f"   - Clave confirmación: {pw2_val}")
        print(f"   - Términos aceptados: {terms_checked}")

    finally:
        await bm.close()
        if temp_html.exists():
            temp_html.unlink()

    print("\n🎉 ¡TODOS LOS TESTS DE AUTH Y REGISTRO PASARON SATISFACTORIAMENTE!")


if __name__ == "__main__":
    asyncio.run(test_auth_helper_unit())
