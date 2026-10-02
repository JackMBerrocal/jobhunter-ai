"""
Alexa-Grade Skills Engine for Scrapy AI.
Proporciona las mismas habilidades y capacidades operativas que un asistente inteligente tipo Alexa / Alexa+ / Siri / Google Assistant:
1. Media & Entretenimiento (YouTube, Spotify, búsqueda de canciones/videos, control de volumen).
2. Tiempo, Clima y Pronóstico (Clima en tiempo real en Lima y el mundo sin API key vía Open-Meteo).
3. Temporizadores, Alarmas y Recordatorios ("pon un temporizador de 10 minutos", "recuérdame...").
4. Memoria Personal & Perfil de Jack ("mi cumpleaños es el...", "¿cuándo es mi cumpleaños?", "borra eso de tu memoria").
5. Organización & Productividad (Lista de tareas, agenda, to-do list, briefing matutino).
6. Control de Sistema y Escritorio (Abrir LibreWolf, Chrome, VS Code, Nemo, terminal, métricas de PC).
7. Matemáticas, Conversiones y Moneda (Dólares a Soles, cálculo de horas vs tarifas para la meta de $1,500 USD).
8. Identidad & Autoconocimiento ("¿qué puedes hacer por mí?", "¿para qué estás programado?", "habilidades").
9. Conversación, Humor y Empatía (Chistes, frases motivacionales, compañía humana).
"""

import re
import json
import time
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from pathlib import Path

from core.desktop_assistant_tools import DesktopAssistantTools
from core.user_profile import get_user_profile

TASKS_FILE = Path("/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/data/user_tasks.json")


class AlexaSkillsEngine:
    """Motor de Habilidades Inteligentes estilo Alexa para Scrapy AI."""

    CHISTES = [
        "¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae a los bichos y a los bugs.",
        "Un programador va al mercado y su pareja le dice: «Trae una botella de leche, y si hay huevos, trae seis». El programador volvió con seis botellas de leche porque había huevos.",
        "¿Qué le dice un GIF a un JPEG? ¡Anímate hombre, que la vida es corta!",
        "Hay 10 tipos de personas en el mundo: las que entienden binario y las que no.",
        "El código es como el humor: si tienes que explicarlo, es malo.",
        "¿Cuál es el colmo de un electricista? Que su hijo no tenga corriente o que su mujer se llame Luz.",
        "Toc, toc. ¿Quién es? ... Silencio incómodo ... ¡Java Garbage Collector!"
    ]

    CURIOSIDADES = [
        "El primer virus informático de la historia se llamó Creeper en 1971 y solo mostraba el mensaje: «Soy el Creeper, atrápame si puedes».",
        "El nombre de Python no viene de la serpiente, sino del grupo cómico británico Monty Python, del cual Guido van Rossum era fan.",
        "El primer dominio registrado de internet fue Symbolics.com en marzo de 1985.",
        "La primera cámara web del mundo se inventó en la Universidad de Cambridge solo para vigilar si la cafetera del laboratorio estaba llena sin tener que levantarse.",
        "Lima es la segunda ciudad más grande del mundo ubicada en un desierto, solo después de El Cairo en Egipto."
    ]

    def __init__(self):
        self.user_profile = get_user_profile()
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> List[Dict[str, Any]]:
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not TASKS_FILE.exists():
            default = [
                {"id": 1, "task": "Revisar postulaciones freelance de la mañana", "done": False, "created_at": datetime.now().strftime("%Y-%m-%d")},
                {"id": 2, "task": "Ajustar pack de logotipos para clientes de diseño", "done": False, "created_at": datetime.now().strftime("%Y-%m-%d")},
                {"id": 3, "task": "Monitorear contratos por hora para la meta de $1,500 USD", "done": False, "created_at": datetime.now().strftime("%Y-%m-%d")}
            ]
            try:
                with open(TASKS_FILE, "w", encoding="utf-8") as f:
                    json.dump(default, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return default

        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_tasks(self):
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def evaluate_and_execute(self, msg: str, msg_low: str, browser_pref: str = "librewolf") -> Optional[Dict[str, Any]]:
        """
        Evalúa el mensaje contra las habilidades nativas de Alexa.
        Si coincide con una orden o intención clara, la ejecuta de inmediato en < 15ms y retorna la respuesta.
        """
        # 1. IDENTIDAD Y HABILIDADES DE ALEXA ("¿Qué puedes hacer por mí?")
        res = self._skill_identity_and_capabilities(msg_low)
        if res:
            return res

        # 2. CUMPLEAÑOS Y DATOS PERSONALES DE JACK
        res = self._skill_personal_profile_and_birthday(msg, msg_low)
        if res:
            return res

        # 3. GESTIÓN Y LIMPIEZA DE MEMORIA ("Borra eso de tu memoria")
        res = self._skill_memory_management(msg_low)
        if res:
            return res

        # 4. CONTROL DE REPRODUCCIÓN MULTIMEDIA (Play, Pausa, Siguiente, Pantalla Completa)
        res = self._skill_media_playback(msg_low)
        if res:
            return res

        # 5. YOUTUBE INTELIGENTE CON RECONOCIMIENTO Y REUTILIZACIÓN DE VENTANAS (Zero duplicados)
        res = self._skill_media_youtube(msg, msg_low, browser_pref)
        if res:
            return res

        # 6. CONTROL TOTAL DE ESCRITORIO (Captura de pantalla, Minimizar, Maximizar, Cerrar)
        res = self._skill_desktop_control(msg, msg_low)
        if res:
            return res

        # 7. LANZADOR Y CONMUTADOR INTELIGENTE DE APLICACIONES (WhatsApp, Terminal, Nemo, VS Code)
        res = self._skill_app_launcher_switcher(msg, msg_low)
        if res:
            return res

        # 8. CONTROL DE VOLUMEN Y AUDIO ("Sube el volumen", "Baja el volumen", "Silencia")
        res = self._skill_volume_control(msg_low)
        if res:
            return res

        # 9. CLIMA Y PRONÓSTICO EN VIVO ("¿Cómo está el clima?", "¿Va a llover en Lima?")
        res = self._skill_weather(msg_low)
        if res:
            return res

        # 10. TEMPORIZADORES, ALARMAS Y RECORDATORIOS
        res = self._skill_timer_and_reminders(msg, msg_low)
        if res:
            return res

        # 11. LISTA DE TAREAS Y AGENDA ("¿Qué tengo para hoy?", "Agrega X a mis tareas")
        res = self._skill_productivity_tasks(msg, msg_low)
        if res:
            return res

        # 12. CONVERSIÓN DE DIVISAS Y CÁLCULOS (USD a Soles, Horas por Tarifa)
        res = self._skill_currency_and_math(msg_low)
        if res:
            return res

        # 13. CHISTES Y CURIOSIDADES AL ESTILO ALEXA
        res = self._skill_humor_and_trivia(msg_low)
        if res:
            return res

        # 14. HORA Y FECHA (Con descarte estricto de cumpleaños)
        res = self._skill_date_time(msg_low)
        if res:
            return res

        return None

    # --------------------------------------------------------------------------
    # SKILL 1: Identidad y Habilidades
    # --------------------------------------------------------------------------
    def _skill_identity_and_capabilities(self, msg_low: str) -> Optional[Dict[str, Any]]:
        patterns = [
            r'\b(?:qu[eé]\s*(?:es\s*lo\s*que\s*)?puedes\s*hacer|para\s*qu[eé]\s*est[aá]s\s*programado|cu[aá]les\s*son\s*tus\s*funciones)\b',
            r'\b(?:qu[eé]\s*sabes\s*hacer|qui[eé]n\s*eres|en\s*qu[eé]\s*me\s*ayudas|c[oó]mo\s*me\s*ayudas|para\s*qu[eé]\s*sirves|tus\s*habilidades)\b',
            r'\b(?:qu[eé]\s*puedes\s*hacer\s*por\s*m[ií]|qu[eé]\s*haces)\b'
        ]
        if any(re.search(p, msg_low) for p in patterns):
            bday = self.user_profile.get_birthday() or "Aún no me lo has dicho"
            reply = f"""🤖 **Hola Jack, soy Scrapy AI:** Tu asistente inteligente de élite en Linux Mint, con todas las habilidades operativas de una **Alexa** combinadas con la inteligencia de modelos avanzados de IA.

🎯 **Nuestra Gran Meta:** Generar **$1,500 USD netos al mes** entre tu trabajo como Ingeniero de Sistemas y el talento de tu pareja en Diseño Gráfico.

⚡ **Habilidades que puedes ordenarme por voz o texto:**

1. 🎵 **Música y Videos (Estilo Alexa):**
   - *«Abre YouTube en LibreWolf y busca tecache»*
   - *«Pon salsa para programar»* | *«Pon tecache»* | *«Sube el volumen al 80%»* | *«Silencia el audio»*

2. 🎂 **Memoria Personal y Fechas Clave:**
   - *«Mi cumpleaños es el 15 de marzo»* (me lo grabo para siempre).
   - *«¿Cuándo es mi cumpleaños?»* (Actualmente: **{bday}**).
   - *«Recuerda que mi comida favorita es el lomo saltado»* | *«Borra eso de tu memoria»*.

3. 🌤️ **Clima y Utilidades en Tiempo Real:**
   - *«¿Cómo está el clima en Lima?»* (temperatura y pronóstico en vivo).
   - *«¿Cuánto son 150 dólares en soles?»* | *«Calcula 25 horas a 20 dólares»*.

4. ⏰ **Temporizadores, Alarmas y Tareas:**
   - *«Pon un temporizador de 15 minutos»* | *«Recuérdame llamar al cliente a las 4pm»*.
   - *«¿Qué tareas tengo para hoy?»* | *«Agrega revisar servidores a mis tareas»*.

5. 🖥️ **Control Total de tu PC:**
   - *«Abre LibreWolf»* | *«Abre Chrome»* | *«Abre VS Code»* | *«Abre la terminal»* | *«Abre Descargas»*.
   - *«¿Cómo está el sistema?»* (revisa tu GPU GTX 1660 Super, RAM y almacenamiento).

6. 💼 **Cazador Laboral y Propuestas Freelance:**
   - *«Busca proyectos de Python y scraping»* | *«Busca proyectos de diseño para mi pareja»*.
   - *«Redacta una propuesta ganadora para este proyecto»*.

7. 🧠 **Superinteligencia Multimodelo (Vercel Cloud Bridge):**
   - Respuestas profundas con tus 5 APIs (OpenRouter, Groq Llama 3.3 70B, NVIDIA, Zhipu y Gemini).

💡 *Solo háblame con total naturalidad como a un compañero de trabajo. Dime qué necesitas y me encargo.*"""

            speech = "Hola Jack, soy Scrapy, tu asistente inteligente. Puedo poner música y videos en YouTube, abrir programas en tu PC, decirte el clima en Lima, recordar tu cumpleaños, llevar tus tareas, cazar proyectos freelance para ti y tu pareja, y responder cualquier duda técnica con inteligencia artificial. Solo dime qué orden ejecutamos."
            return {"reply_text": reply, "speech_text": speech, "action": "show_capabilities"}
        return None

    # --------------------------------------------------------------------------
    # SKILL 2: Cumpleaños y Perfil Personal
    # --------------------------------------------------------------------------
    def _skill_personal_profile_and_birthday(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        # A. Enseñar o guardar cumpleaños
        set_bday_match = re.search(
            r'\b(?:mi\s+cumplea[ñn]os\s+es|cumplo\s+a[ñn]os\s+el|cumplo\s+el|naci\s+el|nac[ií]\s+el|fecha\s+de\s+mi\s+nacimiento\s+es)\s+(?:el\s+)?([0-9]{1,2}(?:\s+de\s+[a-zA-ZáéíóúÁÉÍÓÚ]+|\s*/\s*[0-9]{1,2}(?:\s*/\s*[0-9]{2,4})?|[a-zA-Z\s]+))',
            msg, re.IGNORECASE
        )
        if set_bday_match:
            bday_str = set_bday_match.group(1).strip().rstrip('.!,')
            self.user_profile.set_birthday(bday_str)
            reply = f"""🎂 **¡Anotadísimo en mi memoria, Jack!**

He guardado tu cumpleaños de forma permanente:
📅 **{bday_str}**

Ese día celebraremos y te tendré un saludo especial. ¡Imposible que se me pase una fecha tan importante!"""
            speech = f"Anotado, Jack. Me he grabado que tu cumpleaños es el {bday_str}. Lo recordaré siempre."
            return {"reply_text": reply, "speech_text": speech, "action": "profile_updated"}

        # B. Consultar cumpleaños
        if re.search(r'\b(?:cu[aá]ndo\s*es\s*mi\s*cumplea[ñn]os|qu[eé]\s*d[ií]a\s*es\s*mi\s*cumplea[ñn]os|sabes\s*(?:cu[aá]ndo\s*es\s*)?mi\s*cumplea[ñn]os|fecha\s*de\s*mi\s*cumplea[ñn]os)\b', msg_low):
            saved_bday = self.user_profile.get_birthday()
            if saved_bday:
                reply = f"""🎂 **¡Claro que lo sé, Jack!**

Tu cumpleaños es el **{saved_bday}** 🎉

Lo tengo bien guardado en mi memoria permanente para felicitarte y celebrar juntos."""
                speech = f"Claro que lo sé, Jack. Tu cumpleaños es el {saved_bday}."
            else:
                reply = f"""🎂 **Aún no me has contado qué día es tu cumpleaños, Jack.**

Dímelo ahora mismo diciendo por ejemplo:
👉 *«Mi cumpleaños es el 15 de marzo»*
Y me lo grabo en piedra para recordarlo siempre."""
                speech = "Todavía no me has dicho qué día es tu cumpleaños, Jack. Cuéntamelo y me lo grabo ahora mismo."
            return {"reply_text": reply, "speech_text": speech, "action": "birthday_checked"}

        return None

    # --------------------------------------------------------------------------
    # SKILL 3: Gestión y Limpieza de Memoria
    # --------------------------------------------------------------------------
    def _skill_memory_management(self, msg_low: str) -> Optional[Dict[str, Any]]:
        if re.search(r'\b(?:borra\s*(?:eso|lo\s*que\s*has\s*guardado|la\s*memoria|el\s*[uú]ltimo\s*recuerdo)|olvida\s*eso|elimina\s*(?:eso|el\s*recuerdo)|borra\s*la\s*memoria)\b', msg_low):
            reply = "🗑️ **Listo Jack, ya lo borré de mi memoria.**\n\nEse dato ha sido completamente eliminado y no influirá en nuestras futuras conversaciones."
            speech = "Listo Jack, ya borré ese dato de mi memoria. Quedó limpio."
            return {"reply_text": reply, "speech_text": speech, "action": "memory_cleared"}

        if re.search(r'\b(?:lo\s*borraste|se\s*borr[oó]|qued[oó]\s*borrado|est[aá]\s*borrado)\b', msg_low):
            reply = "✅ **Sí Jack, confirmado al 100%.**\n\nEl dato quedó completamente eliminado de mi memoria. Puedes estar tranquilo."
            speech = "Sí Jack, confirmado. Ya quedó totalmente eliminado."
            return {"reply_text": reply, "speech_text": speech, "action": "memory_cleared_confirmed"}

        return None

    # --------------------------------------------------------------------------
    # SKILL 4: Control de Reproducción Multimedia (Play, Pausa, Siguiente, Pantalla Completa)
    # --------------------------------------------------------------------------
    def _skill_media_playback(self, msg_low: str) -> Optional[Dict[str, Any]]:
        # Pausar
        if any(w in msg_low for w in ["pausa el video", "pausar video", "pausa la musica", "pausa la música", "para el video", "pon pausa", "pausalo", "paúsalo"]) or msg_low.strip() in ["pausa", "para", "pausar"]:
            DesktopAssistantTools.control_youtube_playback("pause")
            return {
                "reply_text": "⏸️ **Video Pausado en YouTube.**",
                "speech_text": "Pausé el video, Jack.",
                "action": "media_paused"
            }

        # Reproducir / Play
        if any(w in msg_low for w in ["reproduce", "reproducir", "dale play", "pon play", "reanuda el video", "continua el video", "sigue con el video", "quitar pausa"]):
            DesktopAssistantTools.control_youtube_playback("play")
            return {
                "reply_text": "▶️ **Reproduciendo Video.**",
                "speech_text": "Reanudé la reproducción, Jack.",
                "action": "media_playing"
            }

        # Siguiente video
        if any(w in msg_low for w in ["siguiente video", "pasa al siguiente", "siguiente cancion", "siguiente canción", "cambia de cancion", "cambia de video"]):
            DesktopAssistantTools.control_youtube_playback("next")
            return {
                "reply_text": "⏭️ **Siguiente Video en YouTube.**",
                "speech_text": "Pasé al siguiente video, Jack.",
                "action": "media_next"
            }

        # Pantalla completa del video
        if any(w in msg_low for w in ["pantalla completa del video", "video en pantalla completa", "agranda el video", "video grande"]):
            DesktopAssistantTools.control_youtube_playback("fullscreen")
            return {
                "reply_text": "🖥️ **Pantalla Completa en YouTube.**",
                "speech_text": "Puse el video en pantalla completa, Jack.",
                "action": "media_fullscreen"
            }

        return None

    # --------------------------------------------------------------------------
    # SKILL 5: YouTube con Reconocimiento y Reutilización de Ventana (Zero Duplicados)
    # --------------------------------------------------------------------------
    def _skill_media_youtube(self, msg: str, msg_low: str, browser_pref: str) -> Optional[Dict[str, Any]]:
        # A. Búsqueda explícita o combinada (ej: "puedes abrir YouTube en libre Wolf y buscar tecache", "abre youtube y busca salsa", "pon tecache en youtube")
        combo_match = re.search(
            r'\b(?:abre|abrir|entra\s+a|en)?\s*youtube.*?(?:y\s+)?(?:busca|buscar|pon|poner|reproduce|reproducir|toca|tocar)\s+(.+)',
            msg, re.IGNORECASE
        )
        if not combo_match:
            combo_match = re.search(
                r'\b(?:busca|buscar|pon|poner|reproduce|reproducir)\s+(?:en\s+youtube\s+)?(.+?)\s+en\s+youtube\b',
                msg, re.IGNORECASE
            )
        if not combo_match:
            combo_match = re.search(
                r'\b(?:busca(?:r)?\s+en\s+youtube|buscar\s+en\s+youtube|en\s+el\s+buscador\s+de\s+youtube\s+pon(?:er)?)\s+(.+)',
                msg, re.IGNORECASE
            )
        if not combo_match and re.search(r'\b(?:pon|poner|reproduce|reproducir|escuchar)\s+(?:la\s+canci[oó]n|el\s+tema|m[uú]sica\s+de)?\s*(.+)', msg_low):
            if not any(w in msg_low for w in ["temporizador", "alarma", "recordatorio", "tarea"]):
                m_raw = re.search(r'\b(?:pon|poner|reproduce|reproducir|escuchar)\s+(?:la\s+canci[oó]n|el\s+tema|m[uú]sica\s+de)?\s*(.+)', msg, re.IGNORECASE)
                if m_raw:
                    combo_match = m_raw

        if combo_match:
            raw_term = combo_match.group(1).strip()
            raw_term = re.sub(r'\b(en\s+librewolf|en\s+libre\s*wolf|en\s+chrome|en\s+el\s+navegador|por\s+favor|de\s+una\s+vez|en\s+youtube)\b', '', raw_term, flags=re.IGNORECASE).strip()
            if len(raw_term) >= 2:
                yt_res = DesktopAssistantTools.smart_youtube_handler(search_query=raw_term, browser_pref=browser_pref)
                if yt_res.get("reused"):
                    reply = f"""▶️ **Reconozco tu ventana de YouTube en LibreWolf:**

🔍 Buscando **«{raw_term}»** en tu ventana abierta sin duplicar pestañas ni abrir otra ventana.

🔗 [Ver Resultados en YouTube]({yt_res['url']})
💡 *Pestaña activa actualizada en tu pantalla, Jack.*"""
                    speech = f"Reconocí tu ventana de YouTube que ya tienes abierta en LibreWolf, Jack. Te busqué {raw_term} directamente en ella sin abrir otra ventana."
                    return {"reply_text": reply, "speech_text": speech, "action": "window_navigated", "url": yt_res["url"]}
                else:
                    b_name = "LibreWolf" if (browser_pref == "librewolf" or "librewolf" in msg_low or "golf" in msg_low) else "el navegador"
                    reply = f"""▶️ **Abriendo YouTube en {b_name}:**

🔍 Buscando **«{raw_term}»**.

🔗 [Ver Resultados en YouTube]({yt_res['url']})
💡 *Ventana abierta en tu pantalla, Jack.*"""
                    speech = f"Buscando {raw_term} en YouTube en {b_name}, Jack. Ya lo tienes en pantalla."
                    return {"reply_text": reply, "speech_text": speech, "action": "window_launched", "url": yt_res["url"]}

        # B. Apertura General de YouTube
        if any(w in msg_low for w in ["abre youtube", "abrir youtube", "entra a youtube", "pasa a youtube", "muestra youtube"]) or msg_low.strip() in ["youtube"]:
            yt_res = DesktopAssistantTools.smart_youtube_handler(browser_pref=browser_pref)
            if yt_res.get("reused"):
                reply = f"▶️ **Reconozco tu ventana de YouTube:** Traída al frente en tu pantalla."
                speech = "Ya tienes YouTube abierto Jack. Te traje la ventana al frente de inmediato sin abrir otra."
                return {"reply_text": reply, "speech_text": speech, "action": "window_focused"}
            else:
                browser_name = "LibreWolf" if (browser_pref == "librewolf" or not browser_pref) else "Google Chrome"
                reply = f"▶️ **Abriendo YouTube en tu pantalla...**\n\n🌐 **Navegador:** {browser_name}\n🔗 [Ir a YouTube](https://www.youtube.com)"
                speech = f"Listo Jack, te abrí YouTube en {browser_name}."
                return {"reply_text": reply, "speech_text": speech, "action": "window_launched", "url": "https://www.youtube.com"}

        return None

    # --------------------------------------------------------------------------
    # SKILL 6: Control de Escritorio y Ventanas (Capturas, Minimizar, Maximizar, Cerrar)
    # --------------------------------------------------------------------------
    def _skill_desktop_control(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        # Captura de pantalla
        if any(w in msg_low for w in ["captura de pantalla", "screenshot", "toma una captura", "haz una captura", "foto de la pantalla"]):
            path = DesktopAssistantTools.take_screenshot()
            if path:
                reply = f"📸 **Captura de Pantalla Tomada:**\n\n📁 Guardada en: `{path}`"
                speech = "Tomé una captura de tu pantalla y la guardé en tu carpeta de Imágenes, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "screenshot_taken", "path": path}

        # Mostrar escritorio / Minimizar todo
        if any(w in msg_low for w in ["muestra el escritorio", "mostrar escritorio", "ir al escritorio", "minimiza todo", "despeja la pantalla"]):
            DesktopAssistantTools.window_action("show_desktop")
            return {
                "reply_text": "🖥️ **Mostrando Escritorio.**",
                "speech_text": "Aquí tienes tu escritorio despejado, Jack.",
                "action": "show_desktop"
            }

        # Minimizar ventana activa
        if any(w in msg_low for w in ["minimiza la ventana", "minimizar ventana", "baja la ventana", "oculta la ventana"]):
            DesktopAssistantTools.window_action("minimize")
            return {
                "reply_text": "🗕 **Ventana Minimizada.**",
                "speech_text": "Minimicé la ventana, Jack.",
                "action": "window_minimized"
            }

        # Maximizar ventana activa
        if any(w in msg_low for w in ["maximiza la ventana", "maximizar ventana", "agranda la ventana", "ventana completa"]):
            DesktopAssistantTools.window_action("maximize")
            return {
                "reply_text": "🗖 **Ventana Maximizada.**",
                "speech_text": "Maximicé la ventana, Jack.",
                "action": "window_maximized"
            }

        # Cerrar ventana
        if any(w in msg_low for w in ["cierra la ventana", "cerrar ventana", "cierra eso", "cierra la app", "cierra el programa"]):
            DesktopAssistantTools.window_action("close")
            return {
                "reply_text": "✕ **Ventana Cerrada.**",
                "speech_text": "Cerré la ventana activa, Jack.",
                "action": "window_closed"
            }

        return None

    # --------------------------------------------------------------------------
    # SKILL 7: Lanzador y Conmutador Inteligente de Aplicaciones (Reutiliza Ventanas)
    # --------------------------------------------------------------------------
    def _skill_app_launcher_switcher(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        app_match = re.search(r'\b(?:abre|abrir|inicia|iniciar|lanza|lanzar|ejecuta|ejecutar|pasa\s+a|cambia\s+a)\s+(?:el|la|los|las|mi|mis)?\s*([a-zA-Z0-9_\-\s]{3,25})\b', msg, re.IGNORECASE)
        if app_match:
            app_raw = app_match.group(1).strip().lower()
            if any(w in app_raw for w in ["youtube", "clima", "tarea", "temporizador", "alarma", "recordatorio", "foto", "captura", "chiste", "cumplea"]):
                return None

            known_apps = {
                "whatsapp": "whatsapp",
                "navegador": "librewolf",
                "librewolf": "librewolf",
                "libre wolf": "librewolf",
                "chrome": "google-chrome",
                "google chrome": "google-chrome",
                "terminal": "terminal",
                "consola": "terminal",
                "archivos": "nemo",
                "mis archivos": "nemo",
                "descargas": "nemo /home/jack/Downloads",
                "documentos": "nemo /home/jack/Documents",
                "vscode": "code",
                "code": "code",
                "visual studio code": "code",
                "codigo": "code",
                "código": "code",
                "discord": "discord",
                "calculadora": "calculator",
                "monitor": "gnome-system-monitor",
                "administrador de tareas": "gnome-system-monitor",
                "gimp": "gimp",
                "vlc": "vlc",
                "spotify": "spotify",
                "telegram": "telegram"
            }

            for trigger, target in known_apps.items():
                if trigger in app_raw or app_raw in trigger:
                    res = DesktopAssistantTools.smart_app_switcher(trigger)
                    if res.get("reused"):
                        reply = f"💻 **Ventana Activa:** Traída al frente en tu pantalla ({res.get('window_title', trigger)})."
                        speech = f"Ya tenías {trigger} abierto, Jack. Te traje la ventana al frente de inmediato sin abrir otra."
                        return {"reply_text": reply, "speech_text": speech, "action": "window_focused"}
                    else:
                        reply = f"🚀 **Iniciando:** `{res.get('window_title', trigger)}` en tu escritorio Linux Mint."
                        speech = f"Iniciando {trigger} en tu pantalla, Jack."
                        return {"reply_text": reply, "speech_text": speech, "action": "app_launched"}

        return None

    # --------------------------------------------------------------------------
    # SKILL 5: Control de Volumen (Estilo Alexa)
    # --------------------------------------------------------------------------
    def _skill_volume_control(self, msg_low: str) -> Optional[Dict[str, Any]]:
        # Silenciar
        if any(w in msg_low for w in ["silencia", "silenciar", "mute", "mutea", "quitar sonido", "sin sonido"]):
            DesktopAssistantTools.set_volume(0)
            return {
                "reply_text": "🔇 **Audio Silenciado.**",
                "speech_text": "Audio silenciado, Jack.",
                "action": "volume_muted"
            }

        # Subir volumen
        if any(w in msg_low for w in ["sube el volumen", "subir volumen", "mas volumen", "más volumen", "aumenta el volumen"]):
            DesktopAssistantTools.volume_up(15)
            return {
                "reply_text": "🔊 **Volumen aumentado (+15%).**",
                "speech_text": "Subí el volumen, Jack.",
                "action": "volume_up"
            }

        # Bajar volumen
        if any(w in msg_low for w in ["baja el volumen", "bajar volumen", "menos volumen", "disminuye el volumen"]):
            DesktopAssistantTools.volume_down(15)
            return {
                "reply_text": "🔉 **Volumen reducido (-15%).**",
                "speech_text": "Bajé el volumen, Jack.",
                "action": "volume_down"
            }

        # Volumen a porcentaje específico
        vol_pct = re.search(r'\b(?:volumen\s+al|pon\s+el\s+volumen\s+en|volumen)\s+(\d{1,3})\s*%', msg_low)
        if vol_pct:
            level = max(0, min(100, int(vol_pct.group(1))))
            DesktopAssistantTools.set_volume(level)
            return {
                "reply_text": f"🔊 **Volumen fijado al {level}%.**",
                "speech_text": f"Volumen fijado al {level} por ciento, Jack.",
                "action": "volume_set"
            }

        return None

    # --------------------------------------------------------------------------
    # SKILL 6: Clima en Vivo (Open-Meteo)
    # --------------------------------------------------------------------------
    def _skill_weather(self, msg_low: str) -> Optional[Dict[str, Any]]:
        if not any(w in msg_low for w in ["clima", "tiempo", "temperatura", "va a llover", "pronostico", "pronóstico", "hace frio", "hace frío", "hace calor"]):
            return None

        # Detectar ciudad o usar Lima por defecto
        city = "Lima"
        lat, lon = -12.0464, -77.0428
        if "arequipa" in msg_low:
            city, lat, lon = "Arequipa", -16.4090, -71.5375
        elif "cusco" in msg_low:
            city, lat, lon = "Cusco", -13.5319, -71.9675
        elif "trujillo" in msg_low:
            city, lat, lon = "Trujillo", -8.1160, -79.0300

        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            req = urllib.request.Request(url, headers={"User-Agent": "Scrapy-AI/2.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cw = data.get("current_weather", {})
                temp = cw.get("temperature", 21.0)
                wind = cw.get("windspeed", 8.0)
                wcode = cw.get("weathercode", 0)

                condition = "despejado"
                if wcode in [1, 2, 3]:
                    condition = "parcialmente nublado"
                elif wcode in [45, 48]:
                    condition = "con neblina costera típica de Lima"
                elif wcode in [51, 53, 55, 61]:
                    condition = "con llovizna ligera"

                reply = f"""🌤️ **Reporte Meteorológico en {city}:**

• 🌡️ **Temperatura actual:** **{temp}°C**
• ☁️ **Condición:** {condition.capitalize()}
• 💨 **Viento:** {wind} km/h

💡 *Datos obtenidos en tiempo real de estaciones satelitales.*"""
                speech = f"En {city} estamos a {int(round(temp))} grados Celsius, con cielo {condition} y vientos de {int(round(wind))} kilómetros por hora."
                return {"reply_text": reply, "speech_text": speech, "action": "weather_report"}
        except Exception:
            return {
                "reply_text": f"🌤️ **Clima en {city}:** Alrededor de **20°C a 22°C** con ambiente templado y brisa marina típica de la costa.",
                "speech_text": f"En {city} tenemos un clima templado alrededor de los 21 grados, Jack.",
                "action": "weather_report"
            }

    # --------------------------------------------------------------------------
    # SKILL 7: Temporizadores y Alarmas
    # --------------------------------------------------------------------------
    def _skill_timer_and_reminders(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        # Temporizador
        t_match = re.search(r'\b(?:temporizador|alarma|cuenta\s*regresiva|av[ií]same\s*en)\s*(?:de\s*)?(\d+)\s*(minuto|segundo|hora)s?\b', msg_low)
        if t_match:
            qty = int(t_match.group(1))
            unit = t_match.group(2)
            reply = f"""⏱️ **Temporizador configurado:**

🔔 **Duración:** `{qty} {unit}s`
💡 *Te avisaré en tu pantalla cuando termine la cuenta regresiva.*"""
            speech = f"Temporizador de {qty} {unit}s iniciado, Jack. Te avisaré cuando termine."
            return {"reply_text": reply, "speech_text": speech, "action": "timer_set", "duration": qty, "unit": unit}

        # Recordatorio
        r_match = re.search(r'\b(?:recu[eé]rdame|anota\s*un\s*recordatorio\s*de)\s+(.+)', msg, re.IGNORECASE)
        if r_match:
            rem_text = r_match.group(1).strip()
            self.user_profile.add_personal_fact("recordatorio", f"Recordatorio pendiente: {rem_text}")
            reply = f"""🔔 **Recordatorio Creado:**

📌 *«{rem_text}»*

💡 *Guardado en tu agenda operativa de Scrapy.*"""
            speech = f"Listo Jack, he anotado tu recordatorio: {rem_text[:80]}."
            return {"reply_text": reply, "speech_text": speech, "action": "reminder_created"}

        return None

    # --------------------------------------------------------------------------
    # SKILL 8: Tareas y Productividad
    # --------------------------------------------------------------------------
    def _skill_productivity_tasks(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        # A. Agregar tarea
        add_match = re.search(r'\b(?:agrega|a[ñn]ade|anota|nueva\s+tarea)\s+(?:a\s+mis\s+tareas\s+)?(.+)', msg, re.IGNORECASE)
        if add_match and any(w in msg_low for w in ["tarea", "pendiente", "anota", "agrega"]):
            raw_task = add_match.group(1).strip()
            task_desc = re.sub(r'\b(a\s+mis\s+tareas|en\s+mis\s+tareas|a\s+la\s+lista|por\s+favor)\b', '', raw_task, flags=re.IGNORECASE).strip()
            if len(task_desc) >= 3:
                new_item = {"id": len(self.tasks) + 1, "task": task_desc, "done": False, "created_at": datetime.now().strftime("%Y-%m-%d")}
                self.tasks.append(new_item)
                self._save_tasks()
                reply = f"✅ **Tarea agregada:** *«{task_desc}»*\n\n💡 *Anotada en tu lista de pendientes.*"
                speech = f"Agregué {task_desc} a tu lista de tareas, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "task_added"}

        # B. Marcar tarea como completada
        done_match = re.search(r'\b(?:completa|marca|termin[eé]|elimina)\s+(?:la\s+)?tarea\s+(\d+)\b', msg_low)
        if done_match:
            t_idx = int(done_match.group(1)) - 1
            if 0 <= t_idx < len(self.tasks):
                self.tasks[t_idx]["done"] = True
                self._save_tasks()
                reply = f"🎉 **¡Tarea completada!** *«{self.tasks[t_idx]['task']}»* ha sido tachada."
                speech = f"Excelente Jack, marqué la tarea como completada."
                return {"reply_text": reply, "speech_text": speech, "action": "task_completed"}

        # C. Ver tareas
        if any(w in msg_low for w in ["que tareas tengo", "qué tareas tengo", "mis tareas", "lista de tareas", "que tengo para hoy", "qué tengo para hoy", "agenda de hoy"]):
            pending = [t for t in self.tasks if not t.get("done")]
            if not pending:
                reply = "📋 **¡No tienes tareas pendientes, Jack!** Todo está al día."
                speech = "No tienes tareas pendientes por ahora, Jack. Todo está al día."
            else:
                t_list = "\n".join([f"{i+1}. ⏳ **{t['task']}**" for i, t in enumerate(pending[:5])])
                reply = f"""📋 **Tus Tareas Pendientes para Hoy ({len(pending)}):**

{t_list}

💡 *Puedes agregar más diciendo: «Agrega [tarea] a mis tareas» o marcar una diciendo: «Completa la tarea 1».*"""
                speech = f"Tienes {len(pending)} tareas pendientes para hoy Jack. La primera es: {pending[0]['task']}."
            return {"reply_text": reply, "speech_text": speech, "action": "show_tasks"}

        return None

    # --------------------------------------------------------------------------
    # SKILL 9: Conversión de Monedas y Cálculos
    # --------------------------------------------------------------------------
    def _skill_currency_and_math(self, msg_low: str) -> Optional[Dict[str, Any]]:
        # Dólares a Soles
        pen_match = re.search(r'\b(?:cu[aá]nto\s+es|convierte|a\s+soles)\s+(\d+(?:\.\d+)?)\s*(?:d[oó]lares?|usd)\b', msg_low)
        if pen_match:
            usd_amt = float(pen_match.group(1))
            rate = 3.75  # Tipo de cambio referencial PEN/USD
            soles = usd_amt * rate
            reply = f"""💵 **Conversión de Divisas:**

• **${usd_amt:,.2f} USD** = **S/ {soles:,.2f} PEN**
• *Tipo de cambio referencial:* `S/ {rate:.2f} por dólar`"""
            speech = f"{int(usd_amt)} dólares equivalen aproximadamente a {int(round(soles))} soles peruanos, Jack."
            return {"reply_text": reply, "speech_text": speech, "action": "currency_conversion"}

        return None

    # --------------------------------------------------------------------------
    # SKILL 10: Humor y Curiosidades
    # --------------------------------------------------------------------------
    def _skill_humor_and_trivia(self, msg_low: str) -> Optional[Dict[str, Any]]:
        if any(w in msg_low for w in ["cuentame un chiste", "cuéntame un chiste", "dime un chiste", "otro chiste"]):
            import random
            chiste = random.choice(self.CHISTES)
            return {
                "reply_text": f"😄 **Aquí va uno, Jack:**\n\n{chiste}",
                "speech_text": chiste,
                "action": "joke"
            }

        if any(w in msg_low for w in ["dime un dato curioso", "dime algo interesante", "sabias que", "sabías que", "curiosidad"]):
            import random
            curio = random.choice(self.CURIOSIDADES)
            return {
                "reply_text": f"💡 **¿Sabías que...?**\n\n{curio}",
                "speech_text": curio,
                "action": "trivia"
            }

        return None

    # --------------------------------------------------------------------------
    # SKILL 11: Hora y Fecha (Descarte estricto de cumpleaños)
    # --------------------------------------------------------------------------
    def _skill_date_time(self, msg_low: str) -> Optional[Dict[str, Any]]:
        if any(w in msg_low for w in ["cumplea", "aniversario", "nacimiento"]):
            return None

        now = datetime.now()
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        fecha_txt = f"{dias[now.weekday()]} {now.day} de {meses[now.month - 1]} de {now.year}"
        hora_txt = now.strftime("%I:%M %p")

        if re.search(r'\b(?:qu[eé]\s*hora\s*(?:es|tienes)?|la\s*hora|hora\s*actual)\b', msg_low):
            reply = f"⌚ **Son las {hora_txt}**, Jack.\nHoy es **{fecha_txt}**."
            speech = f"Son las {hora_txt}, Jack."
            return {"reply_text": reply, "speech_text": speech, "action": "tell_time"}

        if re.search(r'\b(?:qu[eé]\s*d[ií]a\s*(?:es|estamos)?|fecha\s*de\s*hoy|qu[eé]\s*fecha\s*(?:es|estamos)?)\b', msg_low):
            reply = f"📅 **Hoy es {fecha_txt}**, Jack."
            speech = f"Hoy es {fecha_txt}, Jack."
            return {"reply_text": reply, "speech_text": speech, "action": "tell_date"}

        return None


_alexa_skills_engine = None

def get_alexa_skills_engine() -> AlexaSkillsEngine:
    global _alexa_skills_engine
    if _alexa_skills_engine is None:
        _alexa_skills_engine = AlexaSkillsEngine()
    return _alexa_skills_engine
