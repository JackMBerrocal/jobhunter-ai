import os
import time
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright

BROWSER_PROFILE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "browser_profile")
)


class BrowserBidder:
    """
    Operador Autónomo de Navegador para Freelancer.com y Portales Laborales.
    Utiliza Playwright con un perfil persistente para:
    1. Mantener la sesión iniciada de Jack sin pedir contraseñas recurrentes.
    2. Rellenar de forma humana y estructurada propuestas, montos y plazos.
    3. Confirmar y postular a proyectos reales en la plataforma.
    """

    def __init__(self, profile_dir: str = BROWSER_PROFILE_DIR):
        self.profile_dir = profile_dir
        os.makedirs(self.profile_dir, exist_ok=True)

    def launch_login_session(self):
        """
        Abre una ventana visible de Chromium para que Jack inicie sesión
        una sola vez en Freelancer.com. La sesión quedará guardada permanentemente.
        """
        print(f"🚀 Iniciando sesión de navegador en: {self.profile_dir}")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=False,
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.new_page()
            page.goto("https://www.freelancer.com/login", timeout=60000)
            print("🟢 Ventana de inicio de sesión lista. Inicia sesión en Freelancer.com.")
            print("👉 Cuando termines de iniciar sesión, puedes cerrar la ventana del navegador.")
            
            # Mantener abierto mientras el usuario interactúa
            try:
                page.wait_for_timeout(180000)  # 3 minutos
            except Exception:
                pass
            context.close()

    def check_login_status(self) -> bool:
        """Verifica si el perfil persistente cuenta con sesión activa en Freelancer.com."""
        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.new_page()
                page.goto("https://www.freelancer.com/dashboard", timeout=20000)
                url = page.url.lower()
                is_logged = ("login" not in url) and ("signup" not in url)
                context.close()
                return is_logged
            except Exception as e:
                print(f"[BrowserBidder] Error verificando sesión: {e}")
                return False

    def fill_and_place_bid(
        self,
        project_url: str,
        bid_amount: float,
        proposal_text: str,
        period_days: int = 3,
        auto_submit: bool = False
    ) -> Dict[str, Any]:
        """
        Navega al proyecto en Freelancer.com, localiza los campos de oferta,
        ingresa el monto, el plazo y el texto persuasivo, y opcionalmente envía la oferta.
        """
        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=not auto_submit,  # Si es interactivo, mostrar ventana
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.new_page()
                print(f"🌐 Navegando a: {project_url}")
                page.goto(project_url, timeout=30000)
                page.wait_for_timeout(3000)

                # Verificar si pide login
                if "login" in page.url.lower():
                    context.close()
                    return {
                        "success": False,
                        "error": "El navegador requiere inicio de sesión previo en Freelancer.com."
                    }

                # Localizar inputs de monto y propuesta
                # 1. Campo de monto (precio o tarifa horaria)
                amount_inputs = page.locator('input[type="number"], input[name*="amount"], input[name*="bid"], input[id*="amount"]')
                if amount_inputs.count() > 0:
                    amount_inputs.first.fill(str(int(bid_amount)))
                    print(f"💰 Monto completado: {bid_amount}")

                # 2. Campo de días de entrega (si aplica)
                period_inputs = page.locator('input[name*="period"], input[id*="period"]')
                if period_inputs.count() > 0:
                    period_inputs.first.fill(str(period_days))

                # 3. Textarea de la propuesta
                textareas = page.locator('textarea')
                if textareas.count() > 0:
                    textareas.first.fill(proposal_text)
                    print("📝 Propuesta redactada y pegada con éxito.")

                # 4. Enviar si auto_submit es True
                if auto_submit:
                    submit_btn = page.locator('button:has-text("Colocar Oferta"), button:has-text("Place Bid"), button[type="submit"]')
                    if submit_btn.count() > 0:
                        submit_btn.first.click()
                        page.wait_for_timeout(4000)
                        context.close()
                        return {
                            "success": True,
                            "message": f"Oferta de ${bid_amount} enviada exitosamente en Freelancer.com."
                        }

                context.close()
                return {
                    "success": True,
                    "message": f"Formulario preparado en Freelancer.com con propuesta y monto de ${bid_amount}."
                }
            except Exception as e:
                print(f"[BrowserBidder] Error al postular: {e}")
                return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import sys
    bidder = BrowserBidder()
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        bidder.launch_login_session()
    else:
        print("Uso: python -m core.browser_bidder login")
