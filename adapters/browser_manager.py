import os
import random
import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page
from playwright_stealth import Stealth


class BrowserManager:
    """
    Administra la instancia de Chromium con perfil persistente de usuario.
    Permite mantener sesiones abiertas en LinkedIn, Computrabajo, Bumeran y Gmail
    sin necesidad de almacenar contraseñas en texto plano.
    """

    def __init__(self, user_data_dir: str = "data/browser_profile", headless: bool = False):
        self.user_data_dir = str(Path(user_data_dir).resolve())
        self.headless = headless
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> BrowserContext:
        """Inicia el navegador persistente con evasiones de detección de bots."""
        if self.context:
            return self.context

        self.playwright = await async_playwright().start()

        # Limpiar posibles archivos de bloqueo residuales de Chromium
        for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            lock_file = Path(self.user_data_dir) / lock_name
            if lock_file.exists() or lock_file.is_symlink():
                try:
                    lock_file.unlink(missing_ok=True)
                except Exception:
                    pass

        # Argumentos optimizados para apariencia de usuario real y mínimo consumo de RAM (< 120MB)
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--mute-audio",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--no-first-run",
            "--js-flags=--max-old-space-size=128",
            "--lang=es-419,es,en-US,en"
        ]

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            channel="chromium",
            args=args,
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-419",
            timezone_id="America/Lima"
        )

        # Sincronizar automáticamente sesiones activas desde LibreWolf (Upwork, Workana, Fiverr, etc.)
        await self._sync_librewolf_cookies()

        return self.context

    async def _sync_librewolf_cookies(self):
        """Sincroniza cookies de sesión desde LibreWolf (Flatpak) para Upwork, Workana, Fiverr, etc."""
        librewolf_db = Path('/home/jack/.var/app/io.gitlab.librewolf-community/config/librewolf/librewolf/6um5vgeg.default-default/cookies.sqlite')
        if not librewolf_db.exists():
            return
        try:
            import sqlite3
            con = sqlite3.connect(f'file:{librewolf_db}?immutable=1', uri=True)
            cur = con.cursor()
            cur.execute('SELECT name, value, host, path, expiry, isHttpOnly, isSecure, sameSite FROM moz_cookies;')
            rows = cur.fetchall()
            con.close()

            for r in rows:
                name, value, host, path, expiry, is_http_only, is_secure, same_site = r
                if expiry and expiry > 10000000000:
                    exp_sec = expiry // 1000
                elif expiry and expiry > 0:
                    exp_sec = expiry
                else:
                    exp_sec = -1

                ss_map = {0: 'None', 1: 'Lax', 2: 'Strict'}
                ss = ss_map.get(same_site, 'Lax')
                try:
                    await self.context.add_cookies([{
                        'name': name,
                        'value': value,
                        'domain': host,
                        'path': path or '/',
                        'expires': exp_sec,
                        'httpOnly': bool(is_http_only),
                        'secure': bool(is_secure),
                        'sameSite': ss
                    }])
                except Exception:
                    pass
        except Exception as e:
            print(f"[BrowserManager] Nota en sync de cookies: {e}")

    async def new_page_with_stealth(self) -> Page:
        """Crea una nueva pestaña aplicando evasiones stealth contra antibots."""
        if not self.context:
            await self.initialize()

        page = await self.context.new_page()
        try:
            await Stealth().apply_stealth_async(page)
        except Exception as e:
            print(f"[BrowserManager] Advertencia en stealth: {e}")
        return page

    async def human_type(self, page: Page, selector: str, text: str, min_delay: int = 40, max_delay: int = 120):
        """Escribe texto simulando velocidad y pausas de un humano."""
        element = await page.wait_for_selector(selector, state="visible", timeout=10000)
        await element.click()
        for char in text:
            await page.keyboard.press(char)
            await asyncio.sleep(random.uniform(min_delay / 1000.0, max_delay / 1000.0))

    async def human_click(self, page: Page, selector: str):
        """Hace clic en un elemento con un pequeño retardo natural."""
        element = await page.wait_for_selector(selector, state="visible", timeout=10000)
        box = await element.bounding_box()
        if box:
            # Mover ratón ligeramente dentro de las coordenadas del botón
            x = box["x"] + box["width"] * random.uniform(0.2, 0.8)
            y = box["y"] + box["height"] * random.uniform(0.2, 0.8)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        await element.click()

    async def random_delay(self, min_sec: float = 1.5, max_sec: float = 4.0):
        """Pausa aleatoria para evitar patrones rígidos de bot."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def close(self):
        """Cierra el contexto del navegador y limpia recursos."""
        if self.context:
            await self.context.close()
            self.context = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
