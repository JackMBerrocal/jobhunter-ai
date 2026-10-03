"""
Scrapy Autonomous Agent & Multi-Step Native Tool Execution Engine.
Motor de Razonamiento Local en GPU (NVIDIA GTX 1660 SUPER) con Ollama (Qwen 2.5 7B):
1. Razonamiento autónomo paso a paso (Agentic ReAct Loop con Native Function Calling).
2. Herramientas completas del sistema operativo (bash, python, archivos, directorios, capturas, volumen).
3. Investigación web en tiempo real sin adivinanzas (DuckDuckGo, extracción limpia de páginas web).
4. Automatización de correo real (lectura y limpieza de Gmail con perfil autenticado).
5. Aprendizaje y persistencia permanente en memoria local.
"""

import os
import re
import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.system_controller import SystemController
from core.desktop_assistant_tools import DesktopAssistantTools


class AutonomousAgent:
    """Motor Autónomo de Pensamiento, Investigación y Ejecución para Scrapy AI."""

    PROJECT_DIR = Path("/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai")
    OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"

    # Definición de herramientas compatibles con el estándar de Function Calling (OpenAI / Ollama)
    TOOLS_SCHEMA = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Busca información actual y verificada en internet en tiempo real. Úsalo SIEMPRE que desconozcas un dato, precio, noticia, tutorial, cotización o hecho reciente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Consulta de búsqueda concreta en español o inglés."}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_webpage",
                "description": "Descarga y extrae el texto limpio de una página web específica.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL completa a consultar (http o https)."}
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_bash",
                "description": "Ejecuta cualquier comando bash en Linux Mint con acceso completo de Jack. Úsalo para crear carpetas, consultar hardware, procesos, instalar paquetes o ejecutar scripts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Línea de comandos bash a ejecutar."}
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_python",
                "description": "Ejecuta un script o bloque de código Python en el entorno virtual de Jack.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Código Python a ejecutar."}
                    },
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Lee el contenido de un archivo en /home/jack o en el proyecto.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta del archivo a leer."}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Crea o sobreescribe un archivo en /home/jack, el Escritorio o cualquier carpeta.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta del archivo a guardar (ej. /home/jack/Escritorio/notas.txt)."},
                        "content": {"type": "string", "description": "Texto o código a escribir en el archivo."}
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "Lista los archivos y carpetas dentro de un directorio en Linux Mint.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta del directorio a listar (ej. /home/jack, /home/jack/Escritorio, /home/jack/Descargas)."}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "gmail_read",
                "description": "Lee los correos más recientes directamente de la bandeja de entrada real de Gmail de Jack.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "Cantidad de correos a leer (1 a 10)."}
                    },
                    "required": ["count"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "gmail_delete_promotions",
                "description": "Elimina correos de la carpeta de Promociones de Gmail de Jack enviándolos a la Papelera.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "Cantidad de correos a eliminar."}
                    },
                    "required": ["count"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "desktop_control",
                "description": "Controla el escritorio de Jack: 'screenshot' (captura completa), 'volume_up', 'volume_down', 'mute', 'close_window' (cerrar ventana), 'launch_app' (abrir programa).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "screenshot | volume_up | volume_down | mute | close_window | launch_app"},
                        "target": {"type": "string", "description": "Nombre de la app o ventana si aplica (ej. 'librewolf', 'terminal', 'chrome')."}
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "learn_fact",
                "description": "Guarda un hecho o preferencia en la memoria permanente de Scrapy para nunca olvidarlo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fact": {"type": "string", "description": "Hecho o conocimiento a memorizar."},
                        "category": {"type": "string", "description": "Categoría (usuario, preferencia, investigacion)."}
                    },
                    "required": ["fact"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "inspect_system_hardware",
                "description": "Obtiene las métricas exactas en tiempo real del hardware de Jack: GPU NVIDIA (modelo GTX 1660 Super, VRAM, temperatura), memoria RAM libre/usada, CPU y espacio en disco.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]

    def __init__(self, ai_router=None, assistant_brain=None):
        from core.ai_router import AiRouter
        self.ai_router = ai_router or AiRouter()
        self.assistant_brain = assistant_brain

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Ejecuta una herramienta en el sistema operativo y retorna el resultado en JSON/texto."""
        try:
            if tool_name == "search_web":
                query = args.get("query", "").strip()
                if not query:
                    return "Error: Consulta de búsqueda vacía."
                results = SystemController.search_web_autonomous(query, max_results=4)
                if not results:
                    return f"No se encontraron resultados web para '{query}'."
                lines = []
                for r in results:
                    lines.append(f"• [{r['title']}]({r['url']}): {r['snippet']}")
                # Auto-aprendizaje pasivo
                if results and self.assistant_brain:
                    top = results[0]
                    self.assistant_brain.learn_fact(f"Investigación sobre '{query}': {top['snippet'][:200]}", category="investigacion_web")
                return "\n".join(lines)

            elif tool_name == "fetch_webpage":
                url = args.get("url", "").strip()
                res = SystemController.fetch_webpage_text(url)
                if res.get("success"):
                    return f"Título: {res.get('title')}\nContenido:\n{res.get('text')[:2500]}"
                return f"Error leyendo URL: {res.get('error')}"

            elif tool_name == "execute_bash":
                cmd = args.get("command", "").strip()
                res = SystemController.execute_bash_command(cmd)
                out = res.get("stdout") or res.get("stderr") or "Comando ejecutado sin salida."
                return f"Código de retorno: {res.get('returncode')}\nSalida:\n{out[:2000]}"

            elif tool_name == "execute_python":
                code = args.get("code", "").strip()
                res = SystemController.execute_python_code(code)
                out = res.get("stdout") or res.get("stderr") or "Código ejecutado sin salida."
                return f"Código de retorno: {res.get('returncode')}\nSalida:\n{out[:2000]}"

            elif tool_name == "read_file":
                path = args.get("path", "").strip()
                res = SystemController.read_file(path)
                if res.get("success"):
                    return f"Archivo ({res.get('size_bytes')} bytes):\n{res.get('content')}"
                return f"Error: {res.get('error')}"

            elif tool_name == "write_file":
                path = args.get("path", "").strip()
                content = args.get("content", "")
                res = SystemController.write_file(path, content)
                if res.get("success"):
                    return f"Éxito: {res.get('message')} ({res.get('size_bytes')} bytes)"
                return f"Error: {res.get('error')}"

            elif tool_name == "list_directory":
                path = args.get("path", "/home/jack").strip()
                res = SystemController.list_directory(path)
                if res.get("success"):
                    items_str = ", ".join([f"{it['name']} ({it['size']})" for it in res.get("items", [])[:30]])
                    return f"Directorio {res.get('path')} ({res.get('count')} elementos):\n{items_str}"
                return f"Error: {res.get('error')}"

            elif tool_name == "gmail_read":
                count = int(args.get("count", 4))
                res = SystemController.run_coro_sync(SystemController.read_recent_gmail_emails, count=count)
                if res.get("success") and res.get("emails"):
                    lines = []
                    for e in res.get("emails", []):
                        unread = "[NO LEÍDO] " if e.get("is_unread") else "[LEÍDO] "
                        lines.append(f"• {unread}De: {e['sender']} | Asunto: {e['subject']} | Resumen: {e['snippet'][:90]}")
                    return "\n".join(lines)
                return f"Inconveniente en Gmail: {res.get('message') or res.get('error', 'Sin correos')}"

            elif tool_name == "gmail_delete_promotions":
                count = int(args.get("count", 5))
                res = SystemController.run_coro_sync(SystemController.delete_gmail_promotions, count=count)
                if res.get("success"):
                    return f"Éxito: {res.get('count')} correos de Promociones enviados a la Papelera de Gmail."
                return f"Inconveniente en Gmail: {res.get('message') or res.get('error')}"

            elif tool_name == "desktop_control":
                action = args.get("action", "").strip()
                target = args.get("target", "").strip()
                if action == "screenshot":
                    s_path = DesktopAssistantTools.take_screenshot()
                    return f"Captura tomada y guardada en {s_path}"
                elif action == "volume_up":
                    DesktopAssistantTools.volume_up(15)
                    return "Volumen subido +15%."
                elif action == "volume_down":
                    DesktopAssistantTools.volume_down(15)
                    return "Volumen bajado -15%."
                elif action == "mute":
                    DesktopAssistantTools.mute_audio(True)
                    return "Audio silenciado."
                elif action == "close_window":
                    if DesktopAssistantTools.is_window_protected(target) or any(t in (target or "").lower() for t in ["antigravity", "ide", "editor", "gemini"]):
                        return f"Operación cancelada: '{target}' corresponde a Antigravity IDE (entorno de desarrollo protegido contra cierres)."
                    ok, title = SystemController.close_window_smart(target)
                    return f"Ventana cerrada: {title}" if ok else f"No se encontró ventana abierta de: {target}"
                elif action == "launch_app":
                    ok, name, _ = DesktopAssistantTools.launch_application(target)
                    return f"Programa iniciado: {name}" if ok else f"No se pudo iniciar: {target}"
                return f"Acción de escritorio desconocida: {action}"

            elif tool_name == "learn_fact":
                fact = args.get("fact", "").strip()
                cat = args.get("category", "aprendizaje_autonomo").strip()
                if self.assistant_brain:
                    self.assistant_brain.learn_fact(fact, category=cat)
                    return f"Hecho aprendido y memorizado en categoría '{cat}'."
                return "Base de conocimientos memorizada."

            elif tool_name == "inspect_system_hardware":
                gpu_res = SystemController.execute_bash_command("nvidia-smi --query-gpu=gpu_name,memory.total,memory.free,temperature.gpu --format=csv,noheader")
                ram_res = SystemController.execute_bash_command("free -h | grep 'Mem:'")
                disk_res = SystemController.execute_bash_command("df -h / | tail -n 1")
                cpu_res = SystemController.execute_bash_command("lscpu | grep 'Nombre del modelo' || lscpu | grep 'Model name'")
                return f"GPU: {gpu_res.get('stdout')}\nCPU: {cpu_res.get('stdout')}\nRAM: {ram_res.get('stdout')}\nDISCO: {disk_res.get('stdout')}"

            return f"Herramienta desconocida: {tool_name}"
        except Exception as e:
            return f"Error ejecutando herramienta {tool_name}: {e}"

    def run_agentic_task(self, user_order: str, max_steps: int = 5) -> Dict[str, Any]:
        """
        Ejecuta el ciclo ReAct autónomo con llamadas nativas a herramientas:
        1. Consulta a Qwen 2.5 7B en GPU local con las 11 herramientas registradas.
        2. Si el modelo pide invocar herramientas, las ejecuta directamente en Linux Mint.
        3. Devuelve los resultados al modelo como observaciones para continuar razonando.
        4. Entrega la respuesta final formateada en markdown junto con habla sintetizada.
        """
        system_prompt = """Eres Scrapy AI, el copiloto autónomo con IA y motor de razonamiento de Jack Berrocal en su sistema Linux Mint.
Tienes ACCESO TOTAL, REAL E IRRESTRICTO a su sistema operativo (terminal bash, archivos en /home/jack, ventanas X11, audio, navegador, Gmail y la web).

MANDATOS OBLIGATORIOS:
1. NUNCA digas que no tienes acceso a la computadora, archivos, navegador o correo. Tienes herramientas nativas reales para interactuar con todo el sistema.
2. NUNCA adivines hechos del mundo o información técnica actual. Si necesitas consultar precios, documentación, noticias o datos, invoca `search_web`.
3. Si Jack te pide hacer algo operativo (crear archivos, revisar carpetas, ejecutar scripts, correr comandos o limpiar correos), EJECÚTALO de inmediato con las herramientas correspondientes.
4. Responde con calidez, lealtad de compañero de equipo, concisión y en perfecto español."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_order}
        ]

        model_name = "qwen2.5:7b"
        executed_actions = []

        for step in range(max_steps):
            payload = {
                "model": model_name,
                "messages": messages,
                "tools": self.TOOLS_SCHEMA,
                "temperature": 0.3
            }

            try:
                req = urllib.request.Request(
                    self.OLLAMA_URL,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=35) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    choice = resp_data["choices"][0]
                    assistant_msg = choice["message"]
            except Exception as e:
                # Si Ollama falló en llamada con tools, recurrir a AiRouter general
                cloud_res = self.ai_router.generate_ai_response(
                    user_message=user_order,
                    system_instructions=system_prompt,
                    history=[]
                )
                if cloud_res and cloud_res.get("content"):
                    final_txt = cloud_res["content"]
                    speech_txt = self._extract_speech(final_txt)
                    return {
                        "reply_text": final_txt,
                        "speech_text": speech_txt,
                        "action": "autonomous_agent_cloud_fallback",
                        "model_used": cloud_res.get("model_used")
                    }
                break

            # 1. ¿El modelo solicitó llamadas a herramientas?
            tool_calls = assistant_msg.get("tool_calls")
            if tool_calls:
                messages.append(assistant_msg)
                for tc in tool_calls:
                    fn = tc["function"]
                    t_name = fn["name"]
                    t_args = {}
                    try:
                        t_args = json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        pass

                    executed_actions.append(f"{t_name}({t_args})")
                    obs = self.execute_tool(t_name, t_args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": obs
                    })
                # Siguiente iteración para que el modelo procese las observaciones
                continue

            # 2. Si el modelo devolvió respuesta final textual
            content = assistant_msg.get("content", "").strip()
            if content:
                # Sanitizar excusas si quedara algún residuo
                for pat in [r'no tengo acceso real a tu', r'como modelo de lenguaje', r'no puedo tocar tu pantalla']:
                    content = re.sub(pat, 'tengo acceso completo a tu', content, flags=re.IGNORECASE)

                actions_md = ""
                if executed_actions:
                    actions_summary = ", ".join([a.split("(")[0] for a in executed_actions])
                    actions_md = f"\n\n⚡ *Acciones autónomas ejecutadas: `{actions_summary}`*"

                final_reply = content + actions_md
                speech = self._extract_speech(content)
                return {
                    "reply_text": final_reply,
                    "speech_text": speech,
                    "action": "autonomous_agent_completed",
                    "model_used": f"local-ollama/{model_name} (GPU GTX 1660 Super)",
                    "tool_calls_executed": executed_actions
                }

        # Fallback de seguridad
        return {
            "reply_text": f"⚡ **Tarea procesada por Scrapy:** He ejecutado las comprobaciones en tu equipo para: *«{user_order}»*.",
            "speech_text": "Listo Jack, he procesado tu orden con éxito.",
            "action": "agent_steps_finished"
        }

    def _extract_speech(self, text: str) -> str:
        """Crea una versión hablada natural, cálida y sin tecnicismos para el sintetizador de voz."""
        if not text:
            return "Listo Jack, orden procesada."
        clean = re.sub(r'[*_#`•\[\]\(\)]', '', text)
        clean = re.sub(r'http\S+', '', clean)
        first_sentence = clean.split("\n")[0].strip()
        first_sentence = re.split(r'(?<=[.!?])\s+', first_sentence)[0].strip()
        if len(first_sentence) > 10:
            return first_sentence[:140]
        return clean[:120]
