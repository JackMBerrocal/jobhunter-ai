import os
import re
import glob
import shlex
import shutil
import subprocess
import configparser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class DesktopAssistantTools:
    """
    Motor Universal de Habilidades de Escritorio y Sistema para Scrapy AI:
    1. Lanzador Inteligente de Aplicaciones (Flatpak, nativos, webapps, scripts).
    2. Motor de Búsqueda Rápida de Archivos en el Sistema de Jack (/home/jack).
    3. Control de Ventanas y Procesos (wmctrl).
    4. Capturas de Pantalla Instantáneas (import / scrot).
    5. Control de Audio y Hardware (pactl, nvidia-smi).
    """

    APP_DIRS = [
        "/usr/share/applications",
        "/home/jack/.local/share/applications",
        "/var/lib/flatpak/exports/share/applications",
        "/home/jack/.local/share/flatpak/exports/share/applications"
    ]

    _app_cache: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def get_desktop_env(cls) -> Dict[str, str]:
        """Obtiene las variables de entorno para ejecutar comandos con interfaz gráfica en DISPLAY=:0."""
        env = dict(os.environ)
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"
        if "XAUTHORITY" not in env and os.path.exists("/home/jack/.Xauthority"):
            env["XAUTHORITY"] = "/home/jack/.Xauthority"
        return env

    @classmethod
    def index_installed_apps(cls, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """Indexa todos los programas y aplicaciones instaladas en Linux Mint y Flatpaks."""
        if cls._app_cache is not None and not force_refresh:
            return cls._app_cache

        apps = {}
        for app_dir in cls.APP_DIRS:
            if not os.path.exists(app_dir):
                continue
            for fpath in glob.glob(f"{app_dir}/**/*.desktop", recursive=True):
                cp = configparser.ConfigParser(interpolation=None)
                try:
                    cp.read(fpath, encoding="utf-8")
                    if "Desktop Entry" in cp:
                        name = cp.get("Desktop Entry", "Name", fallback="").strip()
                        exec_cmd = cp.get("Desktop Entry", "Exec", fallback="").strip()
                        no_disp = cp.getboolean("Desktop Entry", "NoDisplay", fallback=False)
                        comment = cp.get("Desktop Entry", "Comment", fallback="").strip()
                        categories = cp.get("Desktop Entry", "Categories", fallback="").strip()

                        if name and exec_cmd and not no_disp:
                            # Limpiar modificadores de archivo como %u, %F, @@u
                            clean_cmd = re.sub(r'@@\S*', '', exec_cmd)
                            clean_cmd = re.sub(r'%[a-zA-Z]', '', clean_cmd).strip()

                            app_id = Path(fpath).stem.lower()
                            app_name_low = name.lower()

                            entry = {
                                "name": name,
                                "exec": clean_cmd,
                                "desktop_file": fpath,
                                "comment": comment,
                                "categories": categories
                            }

                            apps[app_id] = entry
                            apps[app_name_low] = entry
                except Exception:
                    pass

        # Agregar alias comunes para facilitar el lenguaje natural de Jack
        aliases = {
            "discord": ["com.discordapp.discord", "discord"],
            "whatsapp": ["webapp-whatsapp4369", "whatsapp"],
            "calculadora": ["calculator", "gnome-calculator"],
            "terminal": ["terminal", "x-terminal-emulator", "gnome-terminal"],
            "consola": ["terminal", "x-terminal-emulator"],
            "archivos": ["nemo", "files"],
            "explorador": ["nemo", "files"],
            "carpetas": ["nemo", "files"],
            "codigo": ["code", "visual-studio-code"],
            "visual studio": ["code"],
            "vscode": ["code"],
            "navegador": ["google-chrome", "librewolf"],
            "chrome": ["google-chrome"],
            "librewolf": ["librewolf"],
            "monitor": ["gnome-system-monitor"],
            "administrador de tareas": ["gnome-system-monitor"],
            "reproductor": ["celluloid", "vlc"],
            "musica": ["celluloid"],
            "video": ["celluloid"],
            "fotos": ["pix", "xviewer"],
            "imagenes": ["pix", "xviewer"],
            "lector pdf": ["xreader"],
            "pdf": ["xreader"],
            "overwatch": ["overwatch"],
            "warframe": ["warframe"],
            "steam": ["steam"],
            "bluetooth": ["blueman-manager"],
            "configuracion": ["cinnamon-settings"]
        }

        for alias, targets in aliases.items():
            for t in targets:
                if t in apps and alias not in apps:
                    apps[alias] = apps[t]
                    break

        cls._app_cache = apps
        return apps

    @classmethod
    def launch_application(cls, app_query: str) -> Tuple[bool, str, str]:
        """
        Busca y ejecuta cualquier aplicación instalada por su nombre o palabra clave.
        Retorna: (éxito, nombre_mostrado, comando_ejecutado)
        """
        env = cls.get_desktop_env()
        query = (app_query or "").strip().lower()

        # Quitar palabras accesorias como "abre", "abrir", "inicia", "ejecuta", "por favor"
        clean_q = re.sub(r'^(abre|abrir|lanzar|ejecuta|ejecutar|inicia|iniciar|pon|poner|arranca|arrancar)\s+(el|la|los|las)?\s*', '', query).strip()
        clean_q = re.sub(r'\b(por favor|de una vez|en mi pc|en el escritorio)\b', '', clean_q).strip()

        if not clean_q:
            return False, "", ""

        apps = cls.index_installed_apps()

        # 1. Búsqueda exacta en el mapa de apps
        target_entry = apps.get(clean_q)

        # 2. Búsqueda por subcadena
        if not target_entry:
            for k, entry in apps.items():
                if clean_q == k or clean_q in k or clean_q in entry["name"].lower():
                    target_entry = entry
                    break

        # 3. Casos especiales directos si no está en desktop entries
        if not target_entry:
            if clean_q in ["librewolf", "navegador libre"]:
                if os.path.exists("/home/jack/.local/bin/librewolf"):
                    target_entry = {"name": "LibreWolf", "exec": "/home/jack/.local/bin/librewolf"}
            elif clean_q in ["code", "vscode", "visual studio code", "codigo"]:
                target_entry = {"name": "Visual Studio Code", "exec": "code /home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai"}
            elif clean_q in ["nemo", "archivos", "mis archivos"]:
                target_entry = {"name": "Archivos (Nemo)", "exec": "nemo /home/jack"}
            elif clean_q in ["terminal", "consola"]:
                target_entry = {"name": "Terminal", "exec": "x-terminal-emulator"}

        # 4. Si aún no se encuentra, verificar si es un ejecutable en el PATH
        if not target_entry:
            which_path = shutil.which(clean_q)
            if which_path:
                target_entry = {"name": clean_q.capitalize(), "exec": which_path}

        if not target_entry:
            return False, clean_q, ""

        exec_str = target_entry["exec"]
        cmd_parts = shlex.split(exec_str)

        try:
            subprocess.Popen(cmd_parts, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, target_entry["name"], exec_str
        except Exception as e:
            print(f"[DesktopAppManager Error]: {e}")
            return False, target_entry["name"], str(e)

    # --------------------------------------------------------------------------
    # 🔍 BÚSQUEDA RÁPIDA DE ARCHIVOS LOCALES (/home/jack)
    # --------------------------------------------------------------------------
    @classmethod
    def search_local_files(cls, query: str, search_dir: str = "/home/jack", max_results: int = 8) -> List[Dict[str, Any]]:
        """
        Busca archivos reales dentro de la computadora de Jack (/home/jack).
        Filtra carpetas pesadas (.git, node_modules, cache, venv) para máxima velocidad.
        """
        clean_q = (query or "").strip()
        clean_q = re.sub(r'^(busca|buscar|encuentra|encontrar|donde esta|dónde está|ubica|ubicar)\s+(el\s+archivo|archivo|los\s+archivos)?\s*', '', clean_q, flags=re.IGNORECASE).strip()
        clean_q = re.sub(r'[¿?¡!]', '', clean_q).strip()

        if not clean_q or len(clean_q) < 2:
            return []

        # Determinar directorio base si el usuario menciona descargas, documentos, etc.
        target_dir = search_dir
        low_q = clean_q.lower()
        if "descarga" in low_q:
            target_dir = "/home/jack/Descargas"
            clean_q = re.sub(r'\b(en\s+descargas|descargas)\b', '', clean_q, flags=re.IGNORECASE).strip()
        elif "documento" in low_q:
            target_dir = "/home/jack/Documentos"
            clean_q = re.sub(r'\b(en\s+documentos|documentos)\b', '', clean_q, flags=re.IGNORECASE).strip()
        elif "imagen" in low_q or "foto" in low_q:
            target_dir = "/home/jack/Imágenes"
            clean_q = re.sub(r'\b(en\s+imagenes|en\s+imágenes|en\s+fotos)\b', '', clean_q, flags=re.IGNORECASE).strip()
        elif "proyecto" in low_q or "jobhunter" in low_q:
            target_dir = "/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai"
            clean_q = re.sub(r'\b(en\s+el\s+proyecto|proyecto|jobhunter)\b', '', clean_q, flags=re.IGNORECASE).strip()

        if not os.path.exists(target_dir):
            target_dir = "/home/jack"

        # Construir comando find optimizado con prune
        cmd = [
            "find", target_dir,
            "-maxdepth", "6",
            "(",
            "-name", ".git", "-o",
            "-name", "node_modules", "-o",
            "-name", ".cache", "-o",
            "-name", "venv", "-o",
            "-name", "__pycache__", "-o",
            "-name", ".local",
            ")", "-prune",
            "-o",
            "-iname", f"*{clean_q}*",
            "-print"
        ]

        results = []
        try:
            raw_out = subprocess.check_output(cmd, text=True, timeout=5)
            lines = [l.strip() for l in raw_out.splitlines() if l.strip()]

            for p in lines:
                if any(skip in p for skip in [".git", "node_modules", ".cache", "venv", "__pycache__"]):
                    continue
                try:
                    st = os.stat(p)
                    size_kb = st.st_size / 1024
                    size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
                    mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
                    results.append({
                        "name": os.path.basename(p),
                        "path": p,
                        "is_dir": os.path.isdir(p),
                        "size": size_str,
                        "modified": mtime,
                        "folder": os.path.dirname(p)
                    })
                except Exception:
                    pass

                if len(results) >= max_results:
                    break
        except Exception as e:
            print(f"[FileSearch Error]: {e}")

        return results

    @classmethod
    def open_path_in_desktop(cls, target_path: str) -> bool:
        """Abre un archivo con su programa predeterminado o una carpeta con Nemo."""
        env = cls.get_desktop_env()
        try:
            if os.path.isdir(target_path):
                subprocess.Popen(["nemo", target_path], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open", target_path], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    # --------------------------------------------------------------------------
    # 📸 CAPTURAS DE PANTALLA & CONTROL DE VENTANAS
    # --------------------------------------------------------------------------
    @classmethod
    def take_screenshot(cls) -> Optional[str]:
        """Toma una captura de pantalla completa del escritorio de Jack."""
        env = cls.get_desktop_env()
        dest_dir = Path("/home/jack/Imágenes")
        dest_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_file = dest_dir / f"captura_scrapy_{ts}.png"

        try:
            # Usar 'import' de ImageMagick (instalado y verificado en el sistema)
            subprocess.check_call(["import", "-window", "root", str(dest_file)], env=env, timeout=4)
            if dest_file.exists():
                return str(dest_file)
        except Exception as e:
            print(f"[Screenshot Error]: {e}")

        return None

    @classmethod
    def get_open_windows(cls) -> List[Dict[str, str]]:
        """Devuelve la lista de ventanas y programas activos en el escritorio de Jack."""
        env = cls.get_desktop_env()
        windows = []
        try:
            out = subprocess.check_output(["wmctrl", "-l"], env=env, text=True)
            for line in out.splitlines():
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    win_id = parts[0]
                    desktop_num = parts[1]
                    title = parts[3].strip()
                    if title and title != "Escritorio" and title != "plank":
                        windows.append({
                            "id": win_id,
                            "desktop": desktop_num,
                            "title": title
                        })
        except Exception:
            pass
        return windows

    PROTECTED_WINDOW_TERMS = [
        "antigravity", "antigravity ide", "antigravity-ide", "gemini",
        "cursor", "vscode", "code - oss", "vscodium", "visual studio code", "code"
    ]

    @classmethod
    def is_window_protected(cls, title: str, wm_class: str = "") -> bool:
        """Determina si una ventana es el IDE o entorno crítico de desarrollo y debe ser protegida contra cierres o minimizaciones."""
        t_low = (title or "").lower()
        c_low = (wm_class or "").lower()
        return any(term in t_low or term in c_low for term in cls.PROTECTED_WINDOW_TERMS)

    @classmethod
    def get_xdotool_bin(cls) -> Optional[str]:
        """Localiza el binario xdotool funcional en el sistema de Jack."""
        xdo = shutil.which("xdotool") or "/home/jack/.local/bin/xdotool"
        return xdo if os.path.exists(xdo) else None

    @classmethod
    def get_active_window_info(cls) -> Tuple[Optional[str], str]:
        """Obtiene el ID y el título de la ventana activa en X11."""
        env = cls.get_desktop_env()
        xdo = cls.get_xdotool_bin()
        if xdo:
            try:
                wid = subprocess.check_output([xdo, "getactivewindow"], env=env, text=True, timeout=1).strip()
                title = subprocess.check_output([xdo, "getwindowname", wid], env=env, text=True, timeout=1).strip()
                return wid, title
            except Exception:
                pass
        try:
            out = subprocess.check_output(["xprop", "-root", "_NET_ACTIVE_WINDOW"], env=env, text=True, timeout=1)
            m = re.search(r'0x[0-9a-fA-F]+', out)
            if m:
                hex_id = m.group(0)
                int_id = str(int(hex_id, 16))
                title = ""
                if xdo:
                    try:
                        title = subprocess.check_output([xdo, "getwindowname", int_id], env=env, text=True, timeout=1).strip()
                    except Exception:
                        pass
                return int_id, title
        except Exception:
            pass
        return None, ""

    @classmethod
    def close_window(cls, window_query: str) -> bool:
        """Cierra una ventana específica por su título o nombre de programa, protegiendo siempre Antigravity IDE."""
        env = cls.get_desktop_env()
        clean_q = window_query.strip().lower()
        if cls.is_window_protected(clean_q):
            print(f"🛡️ [Shield Active]: Rechazado cierre de ventana protegida '{clean_q}' (Antigravity IDE).")
            return False

        windows = cls.get_open_windows()
        for w in windows:
            if cls.is_window_protected(w.get("title", "")):
                continue
            if clean_q in w["title"].lower():
                try:
                    subprocess.check_call(["wmctrl", "-c", w["title"]], env=env)
                    return True
                except Exception:
                    pass
        return False

    @classmethod
    def focus_window(cls, window_query: str) -> bool:
        """Enfoca y trae al frente una ventana activa en pantalla."""
        env = cls.get_desktop_env()
        clean_q = (window_query or "").strip().lower()
        if not clean_q:
            return False

        # 1. Intentar con wmctrl -a
        try:
            res = subprocess.run(["wmctrl", "-a", clean_q], env=env, timeout=2, capture_output=True)
            if res.returncode == 0:
                return True
        except Exception:
            pass

        # 2. Búsqueda por coincidencia en lista de ventanas
        win_info = cls.find_window_by_keyword(clean_q)
        if win_info and win_info.get("id"):
            try:
                subprocess.run(["wmctrl", "-i", "-a", win_info["id"]], env=env, timeout=2)
                return True
            except Exception:
                pass

        # 3. Fallback con xdotool
        xdo = cls.get_xdotool_bin()
        if xdo:
            try:
                win_out = subprocess.check_output([xdo, "search", "--name", clean_q], env=env, text=True, stderr=subprocess.DEVNULL).strip()
                win_ids = [w.strip() for w in win_out.splitlines() if w.strip()]
                if win_ids:
                    subprocess.run([xdo, "windowactivate", "--sync", win_ids[0]], env=env, timeout=2)
                    return True
            except Exception:
                pass
        return False

    @classmethod
    def find_window_by_keyword(cls, keyword: str) -> Optional[Dict[str, Any]]:
        """Busca una ventana abierta cuyo título o clase contenga la palabra clave."""
        env = cls.get_desktop_env()
        clean_k = keyword.strip().lower()
        try:
            res = subprocess.run(["wmctrl", "-l", "-p", "-x"], env=env, capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if clean_k in line.lower():
                        parts = line.split(None, 4)
                        if len(parts) >= 5:
                            return {
                                "id": parts[0],
                                "desktop": parts[1],
                                "pid": parts[2],
                                "wm_class": parts[3],
                                "title": parts[4]
                            }
                        elif len(parts) >= 2:
                            return {"id": parts[0], "title": line}
        except Exception:
            pass
        return None

    @classmethod
    def navigate_existing_window_to_url(cls, win_id: str, url: str) -> bool:
        """
        Navega una ventana de navegador YA ABIERTA hacia una nueva URL
        sin abrir ventanas adicionales ni duplicar instancias.
        """
        env = cls.get_desktop_env()
        xdo = cls.get_xdotool_bin()

        # 1. Traer la ventana al frente absoluto
        try:
            subprocess.run(["wmctrl", "-i", "-a", win_id], env=env, timeout=2)
        except Exception:
            pass

        if not xdo:
            return False

        try:
            import time
            time.sleep(0.12)
            # 2. Enfocar barra de direcciones (Ctrl+L)
            subprocess.run([xdo, "key", "--clearmodifiers", "ctrl+l"], env=env, timeout=2)
            time.sleep(0.08)
            # 3. Escribir la URL
            subprocess.run([xdo, "type", "--delay", "2", url], env=env, timeout=4)
            time.sleep(0.05)
            # 4. Presionar Enter para cargar
            subprocess.run([xdo, "key", "--clearmodifiers", "Return"], env=env, timeout=2)
            return True
        except Exception as e:
            print(f"[Navigate Window Error]: {e}")
            return False

    @classmethod
    def smart_youtube_handler(cls, search_query: Optional[str] = None, target_url: Optional[str] = None, browser_pref: str = "librewolf") -> Dict[str, Any]:
        """
        Manejo Inteligente de YouTube (Regla Alexa de Jack):
        Si la ventana de YouTube YA está abierta en LibreWolf o Chrome:
        1. La reconoce de inmediato.
        2. La trae al frente.
        3. Navega hacia la búsqueda en esa MISMA ventana sin abrir otra.
        Si NO está abierta: la lanza en LibreWolf.
        """
        import urllib.parse
        if not target_url:
            if search_query:
                encoded = urllib.parse.quote_plus(search_query.strip())
                target_url = f"https://www.youtube.com/results?search_query={encoded}"
            else:
                target_url = "https://www.youtube.com"

        # Verificar si hay una ventana de YouTube abierta
        yt_win = cls.find_window_by_keyword("youtube")

        if yt_win and yt_win.get("id"):
            # ¡Ventana existente detectada! Reutilizarla sin abrir otra ventana
            env = cls.get_desktop_env()
            xdo = cls.get_xdotool_bin()
            import time
            try:
                subprocess.run(["wmctrl", "-i", "-a", yt_win["id"]], env=env, timeout=2)
                time.sleep(0.18)
            except Exception:
                pass

            if search_query and xdo:
                try:
                    # En YouTube, la tecla '/' enfoca el cuadro de búsqueda nativo
                    subprocess.run([xdo, "key", "--clearmodifiers", "slash"], env=env, timeout=2)
                    time.sleep(0.12)
                    subprocess.run([xdo, "type", "--delay", "6", search_query.strip()], env=env, timeout=3)
                    time.sleep(0.08)
                    subprocess.run([xdo, "key", "--clearmodifiers", "Return"], env=env, timeout=2)
                except Exception:
                    cls.navigate_existing_window_to_url(yt_win["id"], target_url)
            elif target_url and target_url != "https://www.youtube.com":
                cls.navigate_existing_window_to_url(yt_win["id"], target_url)

            return {
                "reused": True,
                "window_id": yt_win["id"],
                "window_title": yt_win.get("title", "YouTube"),
                "url": target_url
            }

        # Si no había ventana de YouTube abierta, abrirla en LibreWolf
        cls.open_in_browser(target_url, browser_pref=browser_pref)
        return {
            "reused": False,
            "url": target_url
        }

    @classmethod
    def smart_app_switcher(cls, app_name: str) -> Dict[str, Any]:
        """
        Si la aplicación ya está abierta en el escritorio, la enfoca de inmediato sin duplicarla.
        Si no está abierta, la inicia.
        """
        clean_name = app_name.strip().lower()
        win = cls.find_window_by_keyword(clean_name)
        if win and win.get("id"):
            cls.focus_window(clean_name)
            return {
                "reused": True,
                "window_title": win.get("title", app_name),
                "message": f"Ventana de {app_name} traída al frente."
            }

        success, title, cmd = cls.launch_application(app_name)
        return {
            "reused": False,
            "window_title": title or app_name,
            "message": f"Iniciando {title or app_name}..."
        }

    @classmethod
    def window_action(cls, action: str, target: Optional[str] = None) -> bool:
        """
        Ejecuta acciones de control de ventanas (minimizar, maximizar, cerrar, mostrar escritorio).
        """
        env = cls.get_desktop_env()
        xdo = cls.get_xdotool_bin()
        action_low = action.lower()

        try:
            if action_low in ["show_desktop", "escritorio"]:
                if xdo:
                    subprocess.run([xdo, "key", "--clearmodifiers", "super+d"], env=env, timeout=2)
                    return True
            elif action_low in ["minimize", "minimizar"]:
                if target:
                    if cls.is_window_protected(target):
                        print(f"🛡️ [Shield Active]: Rechazada minimización de ventana protegida '{target}'.")
                        return False
                    win = cls.find_window_by_keyword(target)
                    if win and win.get("id") and xdo:
                        subprocess.run([xdo, "windowminimize", win["id"]], env=env, timeout=2)
                        return True
                if xdo:
                    wid, act_title = cls.get_active_window_info()
                    if cls.is_window_protected(act_title):
                        print(f"🛡️ [Shield Active]: Rechazada minimización de ventana activa protegida '{act_title}'.")
                        return False
                    act_win = subprocess.check_output([xdo, "getactivewindow"], env=env, text=True).strip()
                    subprocess.run([xdo, "windowminimize", act_win], env=env, timeout=2)
                    return True
            elif action_low in ["maximize", "maximizar"]:
                subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "toggle,maximized_vert,maximized_horz"], env=env, timeout=2)
                return True
            elif action_low in ["close", "cerrar"]:
                if target:
                    if cls.is_window_protected(target):
                        print(f"🛡️ [Shield Active]: Rechazado cierre de ventana protegida '{target}' (Antigravity IDE).")
                        return False
                    return cls.close_window(target)
                # Si no hay target, verificar que la ventana activa no sea el IDE
                wid, act_title = cls.get_active_window_info()
                if cls.is_window_protected(act_title):
                    print(f"🛡️ [Shield Active]: Bloqueado cierre de ventana activa protegida '{act_title}' (Antigravity IDE).")
                    return False
                subprocess.run(["wmctrl", "-c", ":ACTIVE:"], env=env, timeout=2)
                return True
        except Exception as e:
            print(f"[Window Action Error]: {e}")
        return False

    @classmethod
    def take_screenshot(cls, filename: Optional[str] = None) -> Optional[str]:
        """Toma una captura de pantalla completa de la PC de Jack y la guarda en Pictures."""
        env = cls.get_desktop_env()
        pics_dir = Path("/home/jack/Pictures")
        pics_dir.mkdir(parents=True, exist_ok=True)
        if not filename:
            filename = f"captura_scrapy_{int(datetime.now().timestamp())}.png"
        out_path = pics_dir / filename

        try:
            if shutil.which("gnome-screenshot"):
                subprocess.run(["gnome-screenshot", "-f", str(out_path)], env=env, timeout=3)
                if out_path.exists():
                    return str(out_path)
            elif shutil.which("import"):
                subprocess.run(["import", "-window", "root", str(out_path)], env=env, timeout=3)
                if out_path.exists():
                    return str(out_path)
        except Exception:
            pass
        return None

    @classmethod
    def open_in_browser(cls, url: str, browser_pref: Optional[str] = None) -> bool:
        """
        Abre una URL en el navegador indicado o en el navegador principal de Jack (LibreWolf).
        Trae automáticamente la ventana al frente de la pantalla.
        """
        env = cls.get_desktop_env()
        pref_low = (browser_pref or "").lower()

        # Detección inteligente si no se especificó preferencia
        if not pref_low:
            open_wins = cls.get_open_windows()
            has_yt_chrome = any("youtube" in w['title'].lower() and "chrome" in w['title'].lower() for w in open_wins)
            has_yt_librewolf = any("youtube" in w['title'].lower() and "librewolf" in w['title'].lower() for w in open_wins)
            if has_yt_chrome and not has_yt_librewolf:
                pref_low = "chrome"
            else:
                pref_low = "librewolf"

        # Si Jack pide explícitamente Chrome o está viendo YouTube en Chrome
        if "chrome" in pref_low or "google" in pref_low:
            try:
                subprocess.Popen(["google-chrome", url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                cls.focus_window("Google Chrome")
                return True
            except Exception:
                pass

        # LibreWolf (Navegador preferido de Jack y por defecto)
        librewolf_bin = "/home/jack/.local/bin/librewolf"
        if os.path.exists(librewolf_bin):
            try:
                subprocess.Popen([librewolf_bin, url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                cls.focus_window("LibreWolf")
                return True
            except Exception:
                pass

        # Fallback a Chrome si LibreWolf fallara
        if shutil.which("google-chrome"):
            try:
                subprocess.Popen(["google-chrome", url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                cls.focus_window("Google Chrome")
                return True
            except Exception:
                pass

        # Fallback universal xdg-open
        try:
            subprocess.Popen(["xdg-open", url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    @classmethod
    def volume_up(cls, delta: int = 10) -> bool:
        """Sube el volumen del sistema mediante pactl."""
        env = cls.get_desktop_env()
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{delta}%"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    @classmethod
    def volume_down(cls, delta: int = 10) -> bool:
        """Baja el volumen del sistema mediante pactl."""
        env = cls.get_desktop_env()
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{delta}%"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    @classmethod
    def mute_audio(cls, mute: bool = True) -> bool:
        """Silencia o desilencia el audio del sistema."""
        env = cls.get_desktop_env()
        try:
            val = "1" if mute else "0"
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", val], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    @classmethod
    def set_volume(cls, percentage: int) -> bool:
        """Fija el volumen a un porcentaje específico."""
        env = cls.get_desktop_env()
        try:
            pct = max(0, min(100, int(percentage)))
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    @classmethod
    def get_youtube_video_details(cls, query: str, max_count: int = 5) -> List[Dict[str, str]]:
        """
        Obtiene lista de videos con id, título y url directa para reproducción instantánea.
        """
        import urllib.request
        import urllib.parse
        encoded = urllib.parse.quote_plus(query.strip())
        url = f"https://www.youtube.com/results?search_query={encoded}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'})
            html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8', errors='ignore')
            matches = re.findall(r'\"videoRenderer\":\{\"videoId\":\"([^\"]+)\".*?\"title\":\{\"runs\":\[\{\"text\":\"([^\"]+)\"\}', html)
            results = []
            seen_ids = set()
            for vid, title in matches:
                if vid not in seen_ids:
                    seen_ids.add(vid)
                    results.append({
                        "id": vid,
                        "title": title,
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    })
                if len(results) >= max_count:
                    break
            
            # Fallback a regex simple si el parser estructurado no capturó
            if not results:
                video_ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                for vid in video_ids:
                    if vid not in seen_ids:
                        seen_ids.add(vid)
                        results.append({
                            "id": vid,
                            "title": query,
                            "url": f"https://www.youtube.com/watch?v={vid}"
                        })
                    if len(results) >= max_count:
                        break
            return results
        except Exception as e:
            print(f"[YouTube Search Error]: {e}")
            return []

    @classmethod
    def get_youtube_video_urls(cls, query: str, max_count: int = 5) -> List[str]:
        """
        Obtiene los enlaces directos a los videos de YouTube para una búsqueda dada.
        """
        details = cls.get_youtube_video_details(query, max_count)
        return [item["url"] for item in details]

    @classmethod
    def control_youtube_playback(cls, action: str) -> bool:
        """
        Controla la reproducción activa de YouTube (play/pausa, pantalla completa, siguiente, etc.)
        utilizando eventos nativos X11 hacia la ventana activa del navegador.
        """
        env = cls.get_desktop_env()
        key_map = {
            'play': 'k',
            'pause': 'k',
            'toggle': 'k',
            'space': 'space',
            'fullscreen': 'f',
            'next': 'shift+n',
            'mute': 'm',
            'forward': 'l',
            'rewind': 'j'
        }
        key = key_map.get(action.lower(), 'k')

        xdo = cls.get_xdotool_bin()
        if xdo:
            for pattern in ["YouTube", "LibreWolf", "Chrome"]:
                try:
                    win_out = subprocess.check_output([xdo, "search", "--name", pattern], env=env, text=True, stderr=subprocess.DEVNULL).strip()
                    win_ids = [w.strip() for w in win_out.splitlines() if w.strip()]
                    if win_ids:
                        subprocess.run([xdo, "windowactivate", "--sync", win_ids[0]], env=env, timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        subprocess.run([xdo, "key", "--window", win_ids[0], key], env=env, timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return True
                except Exception:
                    continue
        return False

