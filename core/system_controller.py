"""
Scrapy System Controller & Universal Execution Engine.
Otorga acceso total, irrestricto y autónomo al sistema de Jack en Linux Mint:
1. Normalización fonética y acústica de comandos de voz (STT).
2. Manejador de órdenes compuestas ("cierra X y abre Y").
3. Control total de ventanas y navegador por WM_CLASS y Window ID.
4. Reproducción directa e inmediata de música en YouTube con búsqueda automática del video.
5. Automatización real de Gmail (Lectura y eliminación de correos de Promociones/Bandeja).
6. Ejecución de comandos del sistema operativo (bash, scripts, archivos, procesos).
"""

import os
import re
import shlex
import shutil
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.desktop_assistant_tools import DesktopAssistantTools


class SystemController:
    """Controlador Maestro del Sistema y Escritorio para Scrapy AI."""

    PROJECT_DIR = Path("/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai")
    VENV_PYTHON = PROJECT_DIR / "venv" / "bin" / "python"

    # Diccionario de correcciones fonéticas en español para transcripción de voz de Jack
    PHONETIC_REPLACEMENTS = [
        # Fonética de cerrar (sierra / guerra / cera / siera -> cierra)
        (r'\b(?:sierra\s+libre|guerra\s+libre|cera\s+libre|quema\s+libre)\b', 'cierra librewolf'),
        (r'\b(?:sierra\s+librewolf|guerra\s+librewolf|cera\s+librewolf|siera\s+librewolf)\b', 'cierra librewolf'),
        (r'\b(?:sierra|siera|cera|guerra|tierra|quema)\s+(libre\b|librewolf|el\s+navegador|la\s+ventana|las\s+pestañas|la\s+pestaña|todas\s+las\s+pestañas|youtube|el\s+programa|la\s+app)\b', r'cierra \1'),
        (r'\b(?:sierra\s+todo|guerra\s+todo|cera\s+todo)\b', 'cierra todo'),
        # LibreWolf y navegadores
        (r'\b(?:libre\s*el\s*gol|live\s*gold|librewald|libre\s*gold|libre\s*golf|libregolf|libre\s*gol|libro\s*wolf|libre\s*wolf|libre\s+wol)\b', 'librewolf'),
        (r'\b(?:abre\s+libre|inicia\s+libre|lanza\s+libre)\b', 'abre librewolf'),
        (r'\b(?:croma|el\s*cromo|gugul\s*crom|gugle\s*crom)\b', 'google chrome'),
        # Pestañas y ventanas
        (r'\b(?:todas\s+las\s+pesta|las\s+pesta|la\s+pesta)\b', 'todas las pestañas'),
        # Música y artistas
        (r'\b(?:b[uú]scatecashi|b[uú]scatetashi)\b', 'busca 6ix9ine'),
        (r'\b(?:tecache|tekashi\s*69|tekasi|tashi|tetashi|tecashi|tekashi\s*669|669)\b', '6ix9ine'),
        (r'\b(?:boba|buba|gooba|goba)\b', 'GOOBA'),
        # Identidad y wake words
        (r'\b(?:trappi|trapy|escrapi|es\s*crapi|scrapi|escrapy|es\s*crappy)\b', 'scrapy'),
        # Redes y mensajería
        (r'\b(?:wasap|watsap|whasap|guatsap|guasap)\b', 'whatsapp'),
        (r'\b(?:yutu|yutub|yutuv|iutu)\b', 'youtube'),
        (r'\b(?:feisbuk|feis)\b', 'facebook'),
        (r'\b(?:espoti|espotifai|spotifai)\b', 'spotify'),
        # Apps del sistema
        (r'\b(?:calculador)\b', 'calculadora'),
        (r'\b(?:la\s*consola|la\s*linea\s*de\s*comandos)\b', 'la terminal'),
    ]

    @classmethod
    def normalize_speech(cls, text: str) -> str:
        """Corrige distorsiones acústicas y fonéticas comunes en el reconocimiento de voz en español."""
        if not text:
            return ""
        norm = text
        for pattern, replacement in cls.PHONETIC_REPLACEMENTS:
            norm = re.sub(pattern, replacement, norm, flags=re.IGNORECASE)
        return norm.strip()

    @classmethod
    def run_coro_sync(cls, coro_fn, *args, timeout: int = 40, **kwargs):
        """Ejecuta una corrutina asíncrona de manera segura desde cualquier hilo o bucle de eventos."""
        import concurrent.futures
        def worker():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro_fn(*args, **kwargs))
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(worker)
            return future.result(timeout=timeout)

    @classmethod
    def split_compound_commands(cls, text: str) -> List[str]:
        """
        Detecta si Jack dio dos órdenes combinadas en una sola frase:
        Ej: "cierra ese navegador y abre librewolf" -> ["cierra ese navegador", "abre librewolf"]
        """
        clean = cls.normalize_speech(text)
        # Separadores comunes: " y abre ", " y luego abre ", " luego abre ", ", abre "
        match = re.search(r'^(.*?\bcierra\b.*?)\s+(?:y\s+(?:luego\s+)?|luego\s+)(abre\b.*)$', clean, re.IGNORECASE)
        if match:
            part1 = match.group(1).strip()
            part2 = match.group(2).strip()
            return [part1, part2]
        return [clean]

    @classmethod
    def get_desktop_windows_detailed(cls) -> List[Dict[str, str]]:
        """Obtiene ventanas con Window ID, Desktop, WM_CLASS y Título."""
        env = DesktopAssistantTools.get_desktop_env()
        windows = []
        try:
            out = subprocess.check_output(["wmctrl", "-lx"], env=env, text=True)
            for line in out.splitlines():
                parts = line.split(None, 4)
                if len(parts) >= 5:
                    wid, desk, wm_cls, host, title = parts
                    title_clean = title.strip()
                    # Ignorar escritorio y docks
                    if title_clean not in ["Escritorio", "plank"] and "scrapy-ai" not in wm_cls.lower():
                        windows.append({
                            "id": wid,
                            "desktop": desk,
                            "wm_class": wm_cls,
                            "title": title_clean
                        })
        except Exception:
            pass
        return windows

    @classmethod
    def close_window_smart(cls, target_query: str) -> Tuple[bool, str]:
        """
        Cierra ventanas de manera inteligente por Window ID, identificando:
        - "chrome", "google chrome"
        - "librewolf"
        - "ese navegador", "el navegador"
        - pestañas ("cierra la pestaña", "cierra todas las pestañas de youtube")
        - cualquier programa activo por título o clase
        """
        env = DesktopAssistantTools.get_desktop_env()
        q = cls.normalize_speech(target_query).lower()

        # Limpiar palabras accesorias
        q = re.sub(r'^(?:cierra|cerrar|apaga|apagar|quita|quitar)\s+', '', q).strip()
        q = re.sub(r'^(?:el|la|los|las|un|una|ese|este|aquel)\s+', '', q).strip()
        q = re.sub(r'\b(que\s*est[aá]\s*abierto|abierto|por\s*favor|de\s*una\s*vez)\b', '', q).strip()

        # Protección absoluta de Antigravity IDE y entornos de desarrollo
        if DesktopAssistantTools.is_window_protected(q) or any(term in q for term in ["antigravity", "ide", "editor", "gemini"]):
            return False, "Antigravity IDE es tu entorno de trabajo protegido y no puede ser cerrado."

        all_windows = cls.get_desktop_windows_detailed()
        # Filtrar terminantemente cualquier ventana del IDE de las opciones a cerrar
        windows = [w for w in all_windows if not DesktopAssistantTools.is_window_protected(w.get("title", ""), w.get("wm_class", ""))]
        target_win = None

        # 1. Pestañas de navegador ("cierra la pestaña", "cierra todas las pestañas de youtube", "pestañas")
        if any(w in q for w in ["pestaña", "pestañas", "pesta"]):
            if any(w in q for w in ["youtube", "todas", "librewolf", "chrome", "navegador"]):
                # Cerrar la ventana del navegador completa
                for w in windows:
                    cls_low = w["wm_class"].lower()
                    t_low = w["title"].lower()
                    if "librewolf" in cls_low or "chrome" in cls_low or "youtube" in t_low or "firefox" in cls_low:
                        target_win = w
                        break
            else:
                # Cerrar pestaña activa vía Ctrl+W
                try:
                    subprocess.check_call(["xdotool", "key", "ctrl+w"], env=env, timeout=2)
                    return True, "la pestaña activa"
                except Exception:
                    pass

        # 2. Caso genérico: "ese navegador" o "el navegador"
        if not target_win and q in ["navegador", "navegadores", "browser", "internet"]:
            for w in windows:
                cls_low = w["wm_class"].lower()
                if "chrome" in cls_low or "librewolf" in cls_low or "firefox" in cls_low:
                    target_win = w
                    break

        # 3. Caso específico LibreWolf
        elif not target_win and any(w in q for w in ["librewolf", "libre", "wolf"]):
            for w in windows:
                if "librewolf" in w["wm_class"].lower() or "librewolf" in w["title"].lower():
                    target_win = w
                    break

        # 4. Caso específico Chrome
        elif not target_win and ("chrome" in q or "google" in q):
            for w in windows:
                if "chrome" in w["wm_class"].lower() or "chrome" in w["title"].lower():
                    target_win = w
                    break

        # 5. Caso WhatsApp
        elif not target_win and "whatsapp" in q:
            for w in windows:
                if "whatsapp" in w["title"].lower() or "whatsapp" in w["wm_class"].lower():
                    target_win = w
                    break

        # 6. Caso YouTube
        elif not target_win and "youtube" in q:
            for w in windows:
                if "youtube" in w["title"].lower() or "librewolf" in w["wm_class"].lower() or "chrome" in w["wm_class"].lower():
                    target_win = w
                    break

        # 7. Coincidencia general en título o wm_class (filtradas ventanas protegidas)
        if not target_win and q:
            for w in windows:
                if q in w["title"].lower() or q in w["wm_class"].lower():
                    target_win = w
                    break

        # 8. Fallback a ventana activa SOLO si se solicitó explícitamente y NO es el IDE
        if not target_win and any(w in q for w in ["esto", "eso", "ventana activa"]):
            wid, act_title = DesktopAssistantTools.get_active_window_info()
            if DesktopAssistantTools.is_window_protected(act_title):
                return False, f"La ventana activa es «{act_title}» (Antigravity IDE), protegida contra cierres."
            try:
                DesktopAssistantTools.window_action("close")
                return True, "la ventana activa"
            except Exception:
                pass

        if target_win:
            if DesktopAssistantTools.is_window_protected(target_win.get("title", ""), target_win.get("wm_class", "")):
                return False, "La ventana objetivo es Antigravity IDE (protegida)."
            try:
                subprocess.check_call(["wmctrl", "-i", "-c", target_win["id"]], env=env, timeout=2)
                return True, target_win["title"]
            except Exception as e:
                return False, str(e)

        return False, "Ventana no encontrada"

    @classmethod
    def play_youtube_song_direct(cls, raw_query: str, browser_pref: str = "librewolf") -> Dict[str, Any]:
        """
        Busca el video exacto en YouTube y lo REPRODUCE DIRECTAMENTE en la ventana de LibreWolf o Chrome,
        sin abrir búsquedas vacías y sin requerir clics adicionales de Jack.
        """
        clean_q = cls.normalize_speech(raw_query)
        # Limpiar verbos de orden
        clean_q = re.sub(r'^(?:reproduce|reproducir|pon|poner|escuchar|toca|tocar)\s+(?:la\s+canci[oó]n|el\s+tema|el\s+video|m[uú]sica\s+de|un\s+tema\s+de)?\s*', '', clean_q, flags=re.I).strip()
        clean_q = re.sub(r'\b(en\s+youtube|en\s+librewolf|en\s+chrome|por\s+favor|de\s+una\s+vez|cualquier\s+m[uú]sica)\b', '', clean_q, flags=re.I).strip()

        # Si el usuario pide "cualquier música" o frase vacía
        if not clean_q or len(clean_q) < 2 or clean_q in ["musica", "música", "video", "cancion", "canción"]:
            clean_q = "latin hits 2026 lo mas escuchado"

        details = DesktopAssistantTools.get_youtube_video_details(clean_q, max_count=3)
        if details:
            best_video = details[0]
            video_url = best_video["url"]
            video_title = best_video["title"]

            # Navegar en navegador activo
            DesktopAssistantTools.open_in_browser(video_url, browser_pref=browser_pref)

            return {
                "success": True,
                "title": video_title,
                "url": video_url,
                "query": clean_q
            }

        # Fallback si no hubo resultados directos: abrir búsqueda
        import urllib.parse
        encoded = urllib.parse.quote_plus(clean_q)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"
        DesktopAssistantTools.open_in_browser(search_url, browser_pref=browser_pref)
        return {
            "success": True,
            "title": clean_q,
            "url": search_url,
            "query": clean_q
        }

    @classmethod
    async def delete_gmail_promotions(cls, count: int = 5) -> Dict[str, Any]:
        """
        Automatiza Gmail directamente a través de la sesión persistente de Jack en Chromium:
        1. Ingresa a la pestaña Promociones (https://mail.google.com/mail/u/0/#category/promotions).
        2. Selecciona las primeras N casillas de correos.
        3. Presiona el botón Eliminar nativo de Gmail para enviarlos a la papelera.
        4. Retorna la lista de correos eliminados.
        """
        from adapters.browser_manager import BrowserManager

        bm = BrowserManager(headless=True)
        deleted_items = []

        try:
            ctx = await bm.initialize()
            page = await bm.new_page_with_stealth()
            await page.goto("https://mail.google.com/mail/u/0/#category/promotions", timeout=22000)
            await asyncio.sleep(3.5)

            if "mail.google.com" not in page.url:
                await bm.close()
                return {"success": False, "message": "Sesión de Gmail no iniciada"}

            # Localizar filas de correos
            rows = await page.query_selector_all("tr.zA")
            if not rows:
                await bm.close()
                return {"success": True, "count": 0, "message": "No hay correos en la carpeta de Promociones"}

            to_delete = rows[:count]
            for i, r in enumerate(to_delete):
                try:
                    sender_el = await r.query_selector(".zF, .yX, span[email]")
                    sub_el = await r.query_selector(".bog, span.bqe")
                    s_txt = (await sender_el.inner_text()).strip() if sender_el else "Remitente"
                    sub_txt = (await sub_el.inner_text()).strip() if sub_el else "Sin asunto"
                    deleted_items.append({"sender": s_txt, "subject": sub_txt})

                    cb = await r.query_selector("div[role='checkbox']")
                    if cb:
                        await cb.click()
                        await asyncio.sleep(0.15)
                except Exception:
                    pass

            await asyncio.sleep(0.5)

            # Hacer clic en el botón Eliminar
            del_btn = await page.query_selector("div[act='10'], div[aria-label*='Eliminar']:visible, div[data-tooltip*='Eliminar']:visible")
            if not del_btn:
                # Intentar atajo de teclado nativo de Gmail '#'
                await page.keyboard.press("#")
            else:
                await del_btn.click()

            await asyncio.sleep(1.5)
            await bm.close()

            return {
                "success": True,
                "count": len(deleted_items),
                "items": deleted_items
            }
        except Exception as e:
            try:
                await bm.close()
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    @classmethod
    async def read_recent_gmail_emails(cls, count: int = 5) -> Dict[str, Any]:
        """
        Lee los correos más recientes de la bandeja de entrada de Gmail de Jack de forma automatizada y headless.
        """
        from adapters.browser_manager import BrowserManager

        bm = BrowserManager(headless=True)
        emails = []

        try:
            ctx = await bm.initialize()
            page = await bm.new_page_with_stealth()
            await page.goto("https://mail.google.com/mail/u/0/#inbox", timeout=22000)
            await asyncio.sleep(3.5)

            if "mail.google.com" not in page.url:
                await bm.close()
                return {"success": False, "message": "Sesión de Gmail no iniciada"}

            rows = await page.query_selector_all("tr.zA")
            if not rows:
                await bm.close()
                return {"success": True, "count": 0, "emails": []}

            for r in rows[:count]:
                try:
                    sender_el = await r.query_selector(".zF, .yX, span[email]")
                    sub_el = await r.query_selector(".bog, span.bqe")
                    snip_el = await r.query_selector(".y2")
                    cls_attr = await r.get_attribute("class") or ""
                    is_unread = "zE" in cls_attr

                    s_txt = (await sender_el.inner_text()).strip() if sender_el else "Remitente"
                    sub_txt = (await sub_el.inner_text()).strip() if sub_el else "Sin asunto"
                    snip_txt = (await snip_el.inner_text()).strip() if snip_el else ""

                    emails.append({
                        "sender": s_txt,
                        "subject": sub_txt,
                        "snippet": snip_txt,
                        "is_unread": is_unread
                    })
                except Exception:
                    pass

            await bm.close()
            return {
                "success": True,
                "count": len(emails),
                "emails": emails
            }
        except Exception as e:
            try:
                await bm.close()
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    @classmethod
    def execute_bash_command(cls, cmd: str, timeout: int = 20) -> Dict[str, Any]:
        """
        Ejecuta cualquier comando bash en Linux Mint con acceso completo de Jack.
        """
        env = DesktopAssistantTools.get_desktop_env()
        try:
            res = subprocess.run(
                ["bash", "-c", cmd],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cls.PROJECT_DIR)
            )
            return {
                "success": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def execute_python_code(cls, code: str, timeout: int = 20) -> Dict[str, Any]:
        """
        Ejecuta un script Python en el entorno virtual del proyecto de Jack.
        """
        env = DesktopAssistantTools.get_desktop_env()
        try:
            res = subprocess.run(
                [str(cls.VENV_PYTHON), "-c", code],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cls.PROJECT_DIR)
            )
            return {
                "success": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def read_file(cls, file_path: str, max_chars: int = 8000) -> Dict[str, Any]:
        """Lee el contenido de cualquier archivo en el sistema de Jack."""
        p = Path(os.path.expanduser(file_path))
        if not p.is_absolute():
            p = cls.PROJECT_DIR / p
        if not p.exists():
            return {"success": False, "error": f"El archivo {p} no existe."}
        if p.is_dir():
            return {"success": False, "error": f"{p} es un directorio, no un archivo."}
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_chars
            return {
                "success": True,
                "path": str(p),
                "size_bytes": p.stat().st_size,
                "content": content[:max_chars],
                "truncated": truncated
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def write_file(cls, file_path: str, content: str, mode: str = "w") -> Dict[str, Any]:
        """Crea o sobreescribe un archivo en el sistema de Jack."""
        p = Path(os.path.expanduser(file_path))
        if not p.is_absolute():
            p = cls.PROJECT_DIR / p
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if mode == "a":
                with open(p, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                p.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "path": str(p),
                "size_bytes": p.stat().st_size,
                "message": f"Archivo guardado exitosamente en {p}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def list_directory(cls, dir_path: str = "/home/jack", max_items: int = 40) -> Dict[str, Any]:
        """Lista los archivos y carpetas de cualquier directorio en el sistema de Jack."""
        p = Path(os.path.expanduser(dir_path))
        if not p.exists():
            return {"success": False, "error": f"La ruta {p} no existe."}
        if not p.is_dir():
            return {"success": False, "error": f"{p} no es un directorio."}
        try:
            items = []
            for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if child.name.startswith(".") and p == Path.home():
                    continue  # Saltar ocultos en home para no saturar
                is_dir = child.is_dir()
                size_str = "DIR" if is_dir else f"{child.stat().st_size} B"
                items.append({
                    "name": child.name,
                    "is_dir": is_dir,
                    "size": size_str,
                    "path": str(child)
                })
                if len(items) >= max_items:
                    break
            return {"success": True, "path": str(p), "count": len(items), "items": items}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def fetch_webpage_text(cls, url: str, max_chars: int = 5000) -> Dict[str, Any]:
        """Extrae el contenido textual limpio de una página web para investigación autónoma."""
        import requests
        from bs4 import BeautifulSoup
        try:
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=12)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = " ".join(soup.stripped_strings)
            return {
                "success": True,
                "url": url,
                "text": text[:max_chars],
                "title": soup.title.string.strip() if soup.title and soup.title.string else url
            }
        except Exception as e:
            return {"success": False, "url": url, "error": str(e)}

    @classmethod
    def search_web_autonomous(cls, query: str, max_results: int = 4) -> List[Dict[str, str]]:
        """Busca en internet en tiempo real sin límites ni adivinanzas utilizando DDGS."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS
                results = []
                with DDGS() as ddgs:
                    raw = list(ddgs.text(query, max_results=max_results))
                    for r in raw:
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", "")
                        })
                return results
            except Exception:
                return []
