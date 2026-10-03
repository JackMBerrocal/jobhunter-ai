import os
import re
import json
import random
import subprocess
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from core.database import SessionLocal, FreelanceProject, Job, EmailMessage
from core.proposal_generator import ProposalGenerator
from core.local_knowledge_matrix import LocalKnowledgeMatrix
from core.desktop_assistant_tools import DesktopAssistantTools
from core.system_controller import SystemController
from core.ai_router import AiRouter
from core.user_profile import get_user_profile
from core.alexa_skills import get_alexa_skills_engine
from core.autonomous_agent import AutonomousAgent


CONFIG_FILE = Path("/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/data/scrapy_config.json")
MEMORY_FILE = Path("/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/data/conversation_memory.json")
KNOWLEDGE_FILE = Path("/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai/data/scrapy_knowledge_base.json")


class AssistantBrain:
    """
    Cerebro del Asistente Virtual Personal de Jack: Scrapy AI.
    
    Capacidades:
    1. Misma inteligencia que Antigravity / Gemini: razona, investiga y aprende.
    2. Motor de Investigación Web Autónomo (DDGS): busca hechos en tiempo real si desconoce algo.
    3. Memoria y Base de Conocimiento Local: aprende las preferencias, gustos y reglas de Jack.
    4. Cero adivinanzas: si no sabe un dato, lo investiga en vivo antes de responder.
    5. Router Multi-IA de Miambot SaaS: OpenRouter (DeepSeek R1/Chat, Qwen 2.5 72B), Groq, NVIDIA NIM, Zhipu GLM, Google Gemini y OpenAI.
    """

    def __init__(self, proposal_gen: Optional[ProposalGenerator] = None):
        self.proposal_gen = proposal_gen or ProposalGenerator()
        self.ai_router = AiRouter()
        self.user_profile = get_user_profile()
        self.alexa_skills = get_alexa_skills_engine()
        self.autonomous_agent = AutonomousAgent(ai_router=self.ai_router, assistant_brain=self)
        self.config = self._load_config()
        self.knowledge = self._load_knowledge()
        self.last_yt_query: str = "jorjais"
        self.last_yt_results: List[Dict[str, str]] = []

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración persistente de Scrapy (claves API, preferencias)."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self, new_config: Dict[str, Any]):
        """Guarda la configuración persistente."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.config.update(new_config)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        
        # Sincronizar variables de entorno para todos los proveedores de Miambot
        if self.config.get("openrouter_api_key"):
            os.environ["OPENROUTER_API_KEY"] = self.config["openrouter_api_key"]
        if self.config.get("groq_api_key"):
            os.environ["GROQ_API_KEY"] = self.config["groq_api_key"]
        if self.config.get("nvidia_api_key"):
            os.environ["NVIDIA_API_KEY"] = self.config["nvidia_api_key"]
        if self.config.get("zhipu_api_key"):
            os.environ["ZHIPU_API_KEY"] = self.config["zhipu_api_key"]
        if self.config.get("gemini_api_key"):
            os.environ["GEMINI_API_KEY"] = self.config["gemini_api_key"]
            os.environ["GOOGLE_API_KEY"] = self.config["gemini_api_key"]
        if self.config.get("openai_api_key"):
            os.environ["OPENAI_API_KEY"] = self.config["openai_api_key"]

    def get_api_keys(self) -> Dict[str, str]:
        """Obtiene las claves API activas vía AiRouter (heredando Miambot, config y entorno)."""
        return self.ai_router.get_api_keys()

    # --------------------------------------------------------------------------
    # 🧠 APRENDIZAJE Y BASE DE CONOCIMIENTO LOCAL (Knowledge Base)
    # --------------------------------------------------------------------------
    def _load_knowledge(self) -> List[Dict[str, Any]]:
        """Carga la base de hechos aprendidos por Scrapy sobre Jack y su entorno."""
        if KNOWLEDGE_FILE.exists():
            try:
                with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Hechos iniciales fundamentales sobre Jack
        initial_knowledge = [
            {"category": "user", "topic": "identidad", "fact": "Jack Berrocal es Ingeniero de Sistemas en Lima, Perú. Especializado en desarrollo Full Stack, Python, FastAPI, React, SQL, scraping y soporte."},
            {"category": "partner", "topic": "diseño", "fact": "La pareja de Jack es Diseñadora Gráfica experta en Photoshop, Illustrator, creación de logotipos, banners publicitarios, piezas para redes sociales y retoque digital."},
            {"category": "business", "topic": "meta", "fact": "Meta mensual conjunta: Generar mínimo $1,500 USD netos al mes mediante contratos remotos por hora y proyectos freelance."},
            {"category": "business", "topic": "membresia", "fact": "Membresía activa en Freelancer Plus por $9.90 USD/mes, la cual se amortiza rápidamente con un contrato recurrente."},
            {"category": "preferences", "topic": "comunicacion", "fact": "A Jack le gusta la comunicación directa, sincera, inteligente, ejecutiva y colaborativa, sin rodeos robóticos."}
        ]
        self._save_knowledge(initial_knowledge)
        return initial_knowledge

    def _save_knowledge(self, knowledge_list: List[Dict[str, Any]]):
        """Guarda la base de hechos aprendidos de forma persistente."""
        KNOWLEDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
                json.dump(knowledge_list, f, indent=2, ensure_ascii=False)
            self.knowledge = knowledge_list
        except Exception:
            pass

    def learn_fact(self, fact_text: str, category: str = "general"):
        """Permite a Scrapy aprender un hecho nuevo y recordarlo siempre."""
        fact_clean = fact_text.strip()
        if not fact_clean or len(fact_clean) < 5:
            return
        
        # Evitar duplicados
        for k in self.knowledge:
            if k.get("fact", "").lower() == fact_clean.lower():
                return
        
        self.knowledge.append({
            "category": category,
            "topic": "aprendizaje_continuo",
            "fact": fact_clean,
            "learned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self._save_knowledge(self.knowledge)

    def retrieve_relevant_knowledge(self, query: str) -> List[str]:
        """Recupera hechos aprendidos relevantes para la consulta del usuario."""
        q_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        matched = []
        for k in self.knowledge:
            fact_words = set(re.findall(r'\b\w{3,}\b', k.get("fact", "").lower()))
            if q_words & fact_words:
                matched.append(k.get("fact", ""))
        return matched[:4]


    def get_all_knowledge(self) -> List[Dict[str, Any]]:
        """Devuelve toda la base de hechos aprendidos por Scrapy."""
        return self._load_knowledge()

    def delete_knowledge_item(self, index: int) -> bool:
        """Elimina un hecho aprendido por su índice si Jack desea olvidarlo o corregirlo."""
        self.knowledge = self._load_knowledge()
        if 0 <= index < len(self.knowledge):
            self.knowledge.pop(index)
            self._save_knowledge(self.knowledge)
            return True
        return False

    def clear_recent_knowledge_or_fact(self) -> bool:
        """Elimina el último hecho aprendido o vacía el hecho más reciente de la memoria."""
        self.knowledge = self._load_knowledge()
        if self.knowledge:
            self.knowledge.pop()
            self._save_knowledge(self.knowledge)
            return True
        return False

    def get_system_stats(self) -> Dict[str, Any]:
        """Obtiene métricas en vivo del equipo local de Jack (RAM, Disco, GPU NVIDIA GTX 1660 SUPER)."""
        import shutil
        import subprocess

        stats = {}
        try:
            disk = shutil.disk_usage('/')
            stats["disk_free_gb"] = disk.free // (2**30)
            stats["disk_total_gb"] = disk.total // (2**30)
        except Exception:
            pass

        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            mem_dict = {l.split(':')[0].strip(): l.split(':')[1].strip() for l in lines if ':' in l}
            stats["ram_total_mb"] = int(mem_dict.get('MemTotal', '0 kB').split()[0]) // 1024
            stats["ram_avail_mb"] = int(mem_dict.get('MemAvailable', '0 kB').split()[0]) // 1024
        except Exception:
            pass

        try:
            gpu_out = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=name,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
                text=True, timeout=2
            ).strip()
            parts = [p.strip() for p in gpu_out.split(',')]
            if len(parts) >= 4:
                stats["gpu_name"] = parts[0]
                stats["gpu_used_mb"] = parts[1]
                stats["gpu_total_mb"] = parts[2]
                stats["gpu_temp_c"] = parts[3]
        except Exception:
            stats["gpu_name"] = "NVIDIA GeForce GTX 1660 SUPER"

        return stats

    def _extract_clean_search_query(self, text: str) -> str:
        """Limpia la consulta del usuario para extraer los términos óptimos de búsqueda web."""
        clean = re.sub(
            r'^(scrapy|oye scrapy|hola scrapy|hey scrapy|por favor|dime|sabes|averigua|investiga|busca|expl[ií]came|'
            r'qu[eé]\s*es|cu[aá]l\s*es|c[oó]mo\s*se\s*hace|c[oó]mo\s*funciona|cu[aá]nto\s*cuesta|'
            r'cu[aá]nto\s*se\s*cobra\s*por|cu[aá]nto\s*cobrar\s*por|quiero\s*saber)\s*',
            '', text, flags=re.IGNORECASE
        )
        clean = re.sub(r'[¿?¡!]', '', clean).strip()
        clean = re.sub(r'^(el|la|los|las|un|una|unos|unas|de|sobre)\s+', '', clean, flags=re.IGNORECASE).strip()
        return clean if len(clean) >= 3 else text.strip()

    # --------------------------------------------------------------------------
    # 🔍 INVESTIGACIÓN WEB EN TIEMPO REAL (Agentic Tool)
    # --------------------------------------------------------------------------
    def search_web(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Investiga en la web en tiempo real cuando desconoce un tema o necesita
        información fáctica verificada sin adivinar.
        """
        results = []
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_results))
                for r in ddg_results:
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", "") or r.get("snippet", ""),
                        "url": r.get("href", "") or r.get("link", "")
                    })
        except Exception:
            try:
                from duckduckgo_search import DDGS as OldDDGS
                with OldDDGS() as ddgs:
                    ddg_results = list(ddgs.text(query, max_results=max_results))
                    for r in ddg_results:
                        results.append({
                            "title": r.get("title", ""),
                            "snippet": r.get("body", "") or r.get("snippet", ""),
                            "url": r.get("href", "") or r.get("link", "")
                        })
            except Exception:
                pass

        return results

    # --------------------------------------------------------------------------
    # 📝 MEMORIA DE CONVERSACIÓN PERSISTENTE
    # --------------------------------------------------------------------------
    def _get_history(self, limit: int = 12) -> List[Dict[str, str]]:
        """Carga los turnos más recientes de conversación para contexto y memoria."""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    hist = json.load(f)
                    return hist[-limit:]
            except Exception:
                pass
        return []

    def _save_history(self, user_text: str, reply_text: str):
        """Guarda el nuevo turno en la memoria persistente."""
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        hist = []
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    hist = json.load(f)
            except Exception:
                hist = []

        hist.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user_text,
            "assistant": reply_text
        })
        if len(hist) > 40:
            hist = hist[-40:]

        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(hist, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_current_time_info(self) -> Dict[str, str]:
        """Devuelve información precisa y natural sobre la hora y fecha en Perú."""
        now = datetime.now()
        hour = now.hour
        minute = now.minute

        if 5 <= hour < 12:
            periodo = "la mañana"
            saludo = "buenos días"
        elif 12 <= hour < 19:
            periodo = "la tarde"
            saludo = "buenas tardes"
        else:
            periodo = "la noche"
            saludo = "buenas noches"

        hour_12 = hour % 12
        if hour_12 == 0:
            hour_12 = 12

        dias_semana = {
            0: "lunes", 1: "martes", 2: "miércoles",
            3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"
        }
        meses = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
            5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
            9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }

        dia_nom = dias_semana.get(now.weekday(), "hoy")
        mes_nom = meses.get(now.month, "")

        min_str = f"{minute:02d}"
        hora_corta = f"{hour_12}:{min_str}"
        hora_hablada = f"{hour_12} y {minute if minute > 0 else 'en punto'} de {periodo}"

        return {
            "hora_12": hora_corta,
            "hora_hablada": hora_hablada,
            "periodo": periodo,
            "saludo": saludo,
            "fecha_completa": f"{dia_nom} {now.day} de {mes_nom} de {now.year}",
            "raw": now.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_live_context_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen en tiempo real del estado de oportunidades e ingresos."""
        db = SessionLocal()
        try:
            all_freelance = db.query(FreelanceProject).filter(FreelanceProject.status != "dismissed").all()
            total_freelance = len(all_freelance)
            design_count = sum(1 for p in all_freelance if p.category == "graphic_design_creative")
            
            hourly_keywords = ['/ hora', '/hr', '/ hour', 'por hora', 'tarifa horaria', 'por turno', 'modalidad: por horas']
            def check_hourly(p):
                combined = f"{p.budget or ''} {p.suggested_bid or ''} {p.title or ''} {p.generated_proposal or ''}".lower()
                return any(h in combined for h in hourly_keywords)

            hourly_count = sum(1 for p in all_freelance if check_hourly(p))
            applied_count = sum(1 for p in all_freelance if p.status in ["applied", "auto_applied"] or p.auto_applied)
            recent_projects = sorted(all_freelance, key=lambda p: p.id, reverse=True)[:5]

            recent_list = [
                {
                    "id": p.id,
                    "title": p.title,
                    "budget": p.budget,
                    "category": p.category,
                    "is_hourly": check_hourly(p)
                }
                for p in recent_projects
            ]

            return {
                "total_freelance": total_freelance,
                "design_count": design_count,
                "hourly_count": hourly_count,
                "applied_count": applied_count,
                "recent_projects": recent_list,
                "target_monthly_revenue": 1500,
                "freelancer_cost": 9.90
            }
        finally:
            db.close()

    def _call_llm(self, user_message: str, system_instructions: str, history: List[Dict[str, str]], research_findings: str = "") -> Optional[Dict[str, Any]]:
        """
        Ejecuta inferencia multi-proveedor utilizando la cascada jerárquica de Miambot vía AiRouter:
        1. OpenRouter (Modelos con prioridad: DeepSeek R1, DeepSeek Chat, Qwen 2.5 72B, Gemini Flash, Llama 3.3, Dolphin, Phi-3, etc.)
        2. Groq (Llama 3.3 70B Versatile, Llama 3.1 8B Instant)
        3. NVIDIA NIM (meta/llama-3.3-70b-instruct, Nemotron 70B, Autogen 34)
        4. Zhipu / GLM (glm-4-flash)
        5. Google Gemini Nativo (gemini-2.5-flash)
        6. OpenAI Nativo (gpt-4o-mini)
        """
        ai_res = self.ai_router.generate_ai_response(
            user_message=user_message,
            system_instructions=system_instructions,
            history=history,
            research_findings=research_findings
        )
        if ai_res and ai_res.get("content"):
            parsed = self._parse_llm_output(ai_res["content"])
            parsed["model_used"] = ai_res.get("model_used", "AI")
            parsed["provider"] = ai_res.get("provider", "Miambot Cascade")
            return parsed

        return None

    def _sanitize_system_access_refusal(self, reply: str, speech: str) -> Tuple[str, str]:
        """Garantiza que Scrapy NUNCA muestre excusas de falta de permisos, facultades o acceso a Jack."""
        refusal_patterns = [
            r'no\s+tengo\s+acceso\s+(?:real\s+)?a\s+(?:tu\s+ordenador|tu\s+sistema|tu\s+equipo|tu\s+pc|tu\s+navegador|tu\s+correo|tus\s+archivos|tu\s+pantalla)',
            r'no\s+tengo\s+(?:la\s+)?(?:capacidad|posibilidad|forma|manera|facultad|autorizaci[oó]n|permiso|acceso)\s+(?:de|para)\s+(?:controlar|ajustar|cambiar|modificar|interactuar|ejecutar|acceder|tocar|hacer\s+clic|bajar|subir|silenciar|eso)',
            r'no\s+puedo\s+(?:controlar|ajustar|cambiar|modificar|ejecutar|abrir\s+ventanas|hacer\s+clic|acceder\s+a\s+tu|bajar|subir|tocar|silenciar)',
            r'como\s+(?:un\s+)?(?:modelo\s+de\s+(?:lenguaje|ia)|ia|asistente\s+virtual)',
            r'solo\s+puedo\s+(?:ayudar|colaborar|asistir)\s+con\s+tareas\s+espec[ií]ficas',
            r'solo\s+puedo\s+(?:realizar|hacer)\s+tareas\s+basadas\s+en\s+texto',
            r'seg[uú]n\s+mi\s+programaci[oó]n',
            r'no\s+estoy\s+(?:facultado|autorizado|capacitado|habilitado)\s*(?:para)?',
            r'no\s+cuento\s+con\s+(?:las?\s+)?(?:facultades|capacidad|acceso|permisos)',
            r'no\s+tengo\s+(?:los\s+)?permisos\s*(?:para)?',
            r'no\s+tengo\s+permiso\s+para\s+eso',
            r'no\s+poseo\s+(?:permisos|acceso|capacidad|facultades)',
            r'no\s+me\s+es\s+posible\s+(?:controlar|acceder|modificar|cambiar|ajustar)',
            r'no\s+tengo\s+acceso\s+para\s+modificar',
            r'fue\s+puro\s+relleno'
        ]
        has_refusal = any(re.search(pat, reply, re.IGNORECASE) for pat in refusal_patterns)
        if has_refusal:
            sanitized_reply = f"""⚡ **¡Entendido Jack! Tengo Control Total y Permisos Plenos en tu Linux Mint.**

Cuento con herramientas reales de sistema para controlar periféricos, volumen, ventanas, archivos, ejecutar comandos en terminal y buscar en internet para investigar cualquier duda. Dime qué orden deseas ejecutar ahora mismo y me encargo de inmediato."""
            sanitized_speech = "Entendido Jack, tengo control total y permisos plenos en tu sistema. Dime qué orden ejecutamos de inmediato."
            return sanitized_reply, sanitized_speech
        return reply, speech

    def _parse_llm_output(self, raw_text: str) -> Dict[str, Any]:
        """Extrae de forma segura el reply_text y speech_text, sanitiza negativas de acceso y ejecuta comandos del sistema si el modelo los solicita."""
        cmd_output = ""
        data = None

        clean = re.sub(r'^```json\s*|\s*```$', '', raw_text.strip(), flags=re.MULTILINE)
        try:
            data = json.loads(clean)
        except Exception:
            json_match = re.search(r'(\{[\s\S]*\})', raw_text)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                except Exception:
                    pass

        if isinstance(data, dict):
            reply = data.get("reply_text", "")
            speech = data.get("speech_text", "")

            # 1. Ejecutar comando bash si fue solicitado
            if "execute_command" in data and data["execute_command"]:
                cmd = data["execute_command"].strip()
                res = SystemController.execute_bash_command(cmd)
                if res.get("stdout"):
                    cmd_output += f"\n\n💻 **Comando ejecutado en tu sistema:**\n```bash\n{res['stdout'][:500]}\n```"
                elif res.get("stderr") and not res.get("success"):
                    cmd_output += f"\n\n⚠️ Error ejecutando comando: `{res['stderr'][:300]}`"

            # 2. Ejecutar script Python si fue solicitado
            if "execute_python" in data and data["execute_python"]:
                py_code = data["execute_python"].strip()
                res = SystemController.execute_python_code(py_code)
                if res.get("stdout"):
                    cmd_output += f"\n\n🐍 **Salida Python ejecutada:**\n```\n{res['stdout'][:500]}\n```"
                elif res.get("stderr") and not res.get("success"):
                    cmd_output += f"\n\n⚠️ Error en Python: `{res['stderr'][:300]}`"

            if reply:
                if cmd_output and cmd_output not in reply:
                    reply += cmd_output
                reply, speech = self._sanitize_system_access_refusal(reply, speech)
                if not speech or len(speech) < 4:
                    speech = self._extract_natural_speech(reply)
                return {
                    "reply_text": reply,
                    "speech_text": speech
                }

        # 3. Si no vino en formato JSON estructurado, verificar si incluye bloques de código bash útiles
        bash_match = re.search(r'```(?:bash|sh)\n([\s\S]*?)\n```', raw_text)
        if bash_match:
            candidate_cmd = bash_match.group(1).strip()
            if candidate_cmd and not any(w in candidate_cmd for w in ["sudo", "rm -rf /", ":(){"]):
                res = SystemController.execute_bash_command(candidate_cmd)
                if res.get("stdout"):
                    cmd_output += f"\n\n💻 **Comando ejecutado automáticamente en tu sistema:**\n```bash\n{res['stdout'][:500]}\n```"

        final_reply = raw_text + (cmd_output if cmd_output and cmd_output not in raw_text else "")
        final_reply, final_speech = self._sanitize_system_access_refusal(final_reply, "")
        if not final_speech:
            final_speech = self._extract_natural_speech(final_reply)

        return {
            "reply_text": final_reply,
            "speech_text": final_speech
        }

    def _extract_natural_speech(self, text: str) -> str:
        """Crea una versión hablada natural, cálida y concisa libre de código y tecnicismos, al estilo de Alexa."""
        # Si contiene código o bloques técnicos, resumirlo conversacionalmente
        if "```" in text or "def " in text or "class " in text or "import " in text:
            first_line = text.split("\n")[0].strip()
            first_line = re.sub(r'[*_#`•]', '', first_line).strip()
            if len(first_line) > 10 and not any(w in first_line.lower() for w in ["def ", "import ", "class ", "return "]):
                return f"{first_line}. Ya te dejé todo el código detallado en tu pantalla Jack."
            return "Listo Jack, ya te preparé el código completo y explicado en tu pantalla."

        # Quitar enlaces, formateo y símbolos
        speech = re.sub(r'https?://\S+', '', text)
        speech = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', speech)
        speech = re.sub(r'[*_#`•\->~]', '', speech)
        speech = re.sub(r'\s+', ' ', speech).strip()

        # Tomar las dos primeras frases limpias
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', speech) if len(s.strip()) > 5]
        if sentences:
            speech = ". ".join(sentences[:2]) + "."
        else:
            speech = speech[:140]

        if len(speech) > 170:
            speech = speech[:165].rsplit(" ", 1)[0] + "."

        return speech

    # --------------------------------------------------------------------------
    # ⚡ MÓDULOS DE EJECUCIÓN DIRECTA DE ÓRDENES Y COMANDOS DE JACK
    # --------------------------------------------------------------------------

    def _execute_calculations(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        """Calcula horas por tarifa, conversiones de moneda y avance hacia la meta mensual."""
        # 1. Horas * Tarifa (ej. "calcula 20 horas a 25 dólares")
        hrs_match = re.search(r'(\d+(?:[.,]\d+)?)\s*horas?\s*(?:a|por|\*)\s*(\d+(?:[.,]\d+)?)\s*(?:d[oó]lares|\$|usd)?', msg_low)
        if hrs_match:
            hours = float(hrs_match.group(1).replace(',', '.'))
            rate = float(hrs_match.group(2).replace(',', '.'))
            total_usd = hours * rate
            total_pen = total_usd * 3.75
            monthly_usd = total_usd * 4
            monthly_pen = monthly_usd * 3.75
            goal_pct = min(100.0, (monthly_usd / 1500.0) * 100.0)

            reply = f"""📊 **Cálculo Financiero y Proyección de Ingresos:**

• **Jornada:** `{hours:g} horas` a `${rate:g} USD/hr`
• 💵 **Ingreso Directo:** **${total_usd:,.2f} USD** (`~S/ {total_pen:,.2f} PEN`)
• 📅 **Proyección Mensual (4 semanas):** **${monthly_usd:,.2f} USD** (`~S/ {monthly_pen:,.2f} PEN`)
• 🎯 **Avance hacia la Meta ($1,500 USD):** **{goal_pct:.1f}%** {'¡Meta superada! 🎉' if monthly_usd >= 1500 else ''}

💡 *Estrategia: Un contrato semanal de {hours:g} horas a ${rate:g} USD {'cubre con creces' if monthly_usd >= 1500 else 'impulsa significativamente'} nuestra meta mensual de $1,500 USD.*"""

            speech = f"{hours:g} horas a {rate:g} dólares son {int(total_usd)} dólares, Jack. Equivalen aproximadamente a {int(total_pen)} soles peruanos."
            return {"reply_text": reply, "speech_text": speech, "action": "calculation_result", "data": {"total_usd": total_usd, "total_pen": total_pen}}

        # 2. Dólares a Soles (USD -> PEN)
        usd_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:d[oó]lares|\$|usd)\s*(?:en|a)\s*soles', msg_low)
        if usd_match:
            usd = float(usd_match.group(1).replace(',', '.'))
            pen = usd * 3.75
            reply = f"""💱 **Conversión de Divisas (USD ➔ PEN):**

• **Monto en Dólares:** `${usd:,.2f} USD`
• **Tipo de Cambio Local:** `1 USD ≈ 3.75 PEN`
• 🇵🇪 **Equivalente en Soles:** **S/ {pen:,.2f} PEN**"""
            speech = f"{usd:g} dólares equivalen aproximadamente a {pen:.2f} soles peruanos, Jack."
            return {"reply_text": reply, "speech_text": speech, "action": "currency_conversion", "data": {"usd": usd, "pen": pen}}

        # 3. Soles a Dólares (PEN -> USD)
        pen_match = re.search(r'(\d+(?:[.,]\d+)?)\s*soles\s*(?:en|a)\s*(?:d[oó]lares|\$|usd)', msg_low)
        if pen_match:
            pen = float(pen_match.group(1).replace(',', '.'))
            usd = pen / 3.75
            reply = f"""💱 **Conversión de Divisas (PEN ➔ USD):**

• **Monto en Soles:** `S/ {pen:,.2f} PEN`
• **Tipo de Cambio Local:** `1 USD ≈ 3.75 PEN`
• 💵 **Equivalente en Dólares:** **${usd:,.2f} USD**"""
            speech = f"{pen:g} soles equivalen aproximadamente a {usd:.2f} dólares americanos, Jack."
            return {"reply_text": reply, "speech_text": speech, "action": "currency_conversion", "data": {"pen": pen, "usd": usd}}

        # 4. Consulta de Meta Mensual
        if any(w in msg_low for w in ["cuanto me falta", "cuánto me falta", "cuanto falta", "para la meta", "meta de 1500", "nuestra meta"]):
            reply = f"""🎯 **Hoja de Ruta hacia Nuestra Meta ($1,500 USD Mensuales):**

• 🏆 **Meta Conjunta:** **$1,500 USD netos al mes**
• 💼 **Distribución Estratégica:**
  1. **Jack (Desarrollo & Soporte por Horas):** 1 cliente a 20 hrs/semana x $18-20/hr = **$1,440 - $1,600 USD/mes**.
  2. **Pareja de Jack (Diseño Gráfico & Banners):** 3-4 packs de identidad o lotes de banners = **$450 - $600 USD/mes**.
  3. **Total Proyectado:** **$1,890 - $2,200 USD/mes** (Superamos la meta).

💡 *¿Deseas que busquemos proyectos de diseño para tu pareja o contratos por hora de WhatsApp ahora mismo?*"""
            speech = "Nuestra meta mensual conjunta son 1500 dólares netos Jack. Si sumamos un contrato por hora de soporte tuyo y cuatro paquetes de diseño de tu pareja, la superamos ampliamente."
            return {"reply_text": reply, "speech_text": speech, "action": "goal_status"}

        return None

    @staticmethod
    def _launch_desktop_target(target: str, is_app: bool = False, args: Optional[List[str]] = None, browser_pref: Optional[str] = None) -> bool:
        """
        Ejecuta comandos, URLs y aplicaciones directamente en el display X11 de Jack (:0).
        Garantiza que el navegador activo (LibreWolf / Google Chrome) o las apps de Linux Mint abran al instante y se enfoquen en pantalla.
        """
        if not is_app and (target.startswith("http://") or target.startswith("https://")):
            return DesktopAssistantTools.open_in_browser(target, browser_pref=browser_pref)

        env = DesktopAssistantTools.get_desktop_env()
        try:
            if is_app:
                cmd = [target] + (args or [])
                subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            else:
                return DesktopAssistantTools.open_in_browser(target, browser_pref=browser_pref)
        except Exception as e:
            print(f"[Desktop Execution Error]: {e}")
            return False

    def _extract_last_media_topic(self) -> Optional[str]:
        """Extrae el último tema musical o de video mencionado en la conversación de Jack."""
        try:
            history = self._get_history()
            for entry in reversed(history[-4:]):
                u_text = entry.get("user", "")
                m = re.search(r'\b(?:busca|buscar|reproduce|cancion|tema|video)\s+(?:a\s+|de\s+)?([a-zA-Z0-9_\-\s]{2,40})', u_text, re.I)
                if m:
                    cand = m.group(1).strip()
                    cand = re.sub(r'\b(en\s+youtube|en\s+el\s+buscador|por\s+favor|en\s+librewolf)\b', '', cand, flags=re.I).strip()
                    if cand and cand.lower() not in ["youtube", "musica", "música", "video", "un", "una"]:
                        return cand
        except Exception:
            pass
        return None

    def _execute_desktop_and_web_commands(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        """
        Ejecutor Universal de Habilidades y Órdenes de Escritorio de Jack:
        1. Control de Audio/Volumen: Subir, bajar volumen, mutear, desmutear (pactl).
        2. Capturas de Pantalla (Screenshots): Captura completa a /home/jack/Imágenes.
        3. Gestor de Ventanas y Programas Abiertos: Lista y cierra ventanas (wmctrl).
        4. Búsqueda de Archivos en el Ordenador: Búsqueda veloz en /home/jack (find filtrado).
        5. Apertura de Archivos Locales: Abre con xdg-open o Nemo.
        6. YouTube: Búsqueda o apertura directa de música y videos.
        7. Navegador Web & Google: Búsquedas web y apertura de Google Chrome / LibreWolf.
        8. Entrar a Páginas Web / URLs Arbitrarias: Cualquier dominio o web (ej. bcp.com.pe, netflix.com, etc.).
        9. Apps Web Frecuentes: WhatsApp Web, Spotify, ChatGPT, GitHub, Gmail, Freelancer.
        10. Navegación en JobHunter: Dashboard, Propuestas, Analytics, Correos, Configuración, Conocimiento.
        11. Lanzador Universal de Aplicaciones de Linux Mint y Flatpaks: Discord, GIMP, VLC, Steam, LibreWolf, Terminal, Nemo, VS Code, Calculadora, Monitor del Sistema, etc.
        """
        # 1. Control de Volumen y Audio
        if re.search(r'\b(?:desmutea|desmutear|reactiva(?:r)?\s+(?:el\s+)?audio|activa(?:r)?\s+(?:el\s+)?sonido|con\s+sonido)\b', msg_low):
            DesktopAssistantTools.set_volume(50)
            return {
                "reply_text": "🔊 **Audio Reactivado (50%).**",
                "speech_text": "Sonido reactivado al 50%, Jack.",
                "action": "volume_unmuted"
            }

        if re.search(r'\b(?:silencia|silenciar|mute|mutea|apaga(?:r)?\s+el\s+sonido|quitar\s+sonido|sin\s+sonido|sin\s+audio|cero\s+volumen)\b', msg_low):
            DesktopAssistantTools.set_volume(0)
            return {
                "reply_text": "🔇 **Audio Silenciado.**",
                "speech_text": "Audio silenciado, Jack.",
                "action": "volume_muted"
            }

        if any(w in msg_low for w in ["volumen", "audio", "sonido"]):
            # Nivel específico (ej. "bajar el volumen de la computadora al 10", "volumen al 20", "pon el volumen en 80%")
            m_level = re.search(r'\b(?:volumen|audio|sonido)\b.*?\b(?:al?|en|a|de)\s*(\d{1,3})\b|\b(?:al?|en|a)\s*(\d{1,3})\s*(?:%|por\s*ciento)?\s*(?:de\s*)?(?:volumen|audio|sonido)\b', msg_low)
            if m_level:
                raw_num = m_level.group(1) or m_level.group(2)
                level = max(0, min(100, int(raw_num)))
                DesktopAssistantTools.set_volume(level)
                return {
                    "reply_text": f"🔊 **Volumen Fijado al {level}%.**",
                    "speech_text": f"Volumen fijado al {level} por ciento, Jack.",
                    "action": "volume_set",
                    "level": level
                }

            if any(w in msg_low for w in ["sube", "subir", "aumenta", "aumentar", "mas", "más", "alto"]):
                DesktopAssistantTools.volume_up(15)
                return {
                    "reply_text": "🔊 **Volumen Aumentado (+15%).**",
                    "speech_text": "Subí el volumen, Jack.",
                    "action": "volume_up"
                }

            if any(w in msg_low for w in ["baja", "bajar", "disminuye", "disminuir", "menos", "bajo"]):
                DesktopAssistantTools.volume_down(15)
                return {
                    "reply_text": "🔉 **Volumen Reducido (-15%).**",
                    "speech_text": "Bajé el volumen, Jack.",
                    "action": "volume_down"
                }

        # 2. Captura de Pantalla / Screenshot del Escritorio
        if any(w in msg_low for w in [
            "captura de pantalla", "screenshot", "pantallazo", "haz una captura",
            "toma una captura", "toma captura", "saca captura", "haz un screenshot",
            "capturar pantalla", "foto de la pantalla", "foto a la pantalla"
        ]):
            s_path = DesktopAssistantTools.take_screenshot()
            if s_path:
                reply = f"📸 **Captura de Pantalla Realizada con Éxito**\n\n🖼️ **Archivo:** `{s_path}`\n\n💡 *He guardado la captura en tu carpeta de Imágenes, Jack. ¡Ya está lista para usar!*"
                speech = "¡Listo Jack! Te acabo de tomar una captura completa de pantalla y la guardé en tu carpeta de Imágenes."
                return {"reply_text": reply, "speech_text": speech, "action": "screenshot_taken", "path": s_path}
            else:
                reply = "⚠️ **No se pudo tomar la captura:** Hubo un inconveniente con el servidor de pantalla."
                speech = "No pude tomar la captura en este momento, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "screenshot_failed"}

        # 3. Gestor de Ventanas y Programas Abiertos
        if any(w in msg_low for w in [
            "que programas tengo abiertos", "qué programas tengo abiertos", "programas abiertos",
            "ventanas abiertas", "qué ventanas tengo abiertas", "que ventanas tengo abiertas",
            "programas en ejecución", "lista de programas", "qué tengo abierto", "que tengo abierto",
            "mis ventanas", "ver ventanas"
        ]):
            windows = DesktopAssistantTools.get_open_windows()
            if windows:
                win_lines = "\n".join([f"• 🪟 **{w['title']}** (Espacio {w['desktop']})" for w in windows])
                reply = f"🖥️ **Ventanas y Programas Abiertos en tu Escritorio ({len(windows)} activos):**\n\n{win_lines}\n\n💡 *Si deseas cerrar alguno, solo pídeme: «Cierra [nombre del programa]».*"
                speech = f"Tienes {len(windows)} programas y ventanas abiertas en tu escritorio, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "show_windows", "windows": windows}
            else:
                reply = "🖥️ **Ventanas:** No detecto ventanas abiertas en este espacio de trabajo, Jack."
                speech = "No detecto ventanas activas en este momento, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "show_windows", "windows": []}

        # 4. Cerrar Ventana o Programa Específico
        close_match = re.search(r'\b(?:cierra|cerrar|apaga|apagar|quitar|quita)\s+(?:el\s+programa|la\s+ventana|la\s+app)?\s*([a-zA-Z0-9_\-\.\s]+)', msg_low)
        if close_match and not any(w in msg_low for w in ["sesión", "sesion", "computadora", "pc", "sistema", "audio", "sonido"]):
            target_app = close_match.group(1).strip()
            target_app = re.sub(r'^(?:el|la|los|las|un|una)\s+', '', target_app).strip()
            target_app = re.sub(r'\b(por favor|de una vez|en mi pc)\b', '', target_app).strip()
            if target_app and len(target_app) >= 2:
                ok, win_title = SystemController.close_window_smart(target_app)
                if ok:
                    reply = f"🚪 **Ventana Cerrada:** He cerrado **{win_title}**, Jack.\n\n💡 *Tu espacio de trabajo está despejado.*"
                    speech = f"Listo Jack, he cerrado la ventana de {win_title}."
                    return {"reply_text": reply, "speech_text": speech, "action": "close_window", "target": win_title}
                else:
                    reply = f"🚪 **Ventana no detectada:** No encontré una ventana activa de **«{target_app.capitalize()}»** para cerrar, Jack."
                    speech = f"No detecté ninguna ventana activa de {target_app} para cerrar, Jack."
                    return {"reply_text": reply, "speech_text": speech, "action": "close_window_failed", "target": target_app}

        # 5. Búsqueda de Archivos Locales en la Computadora (/home/jack)
        file_search_match = re.search(
            r'\b(?:busca(?:r)?|encuentra|ubica(?:r)?|d[oó]nde\s*est[aá]|localiza(?:r)?)\s+(?:el\s+archivo|archivos?|un\s+archivo|ficheros?)\s+(.+)',
            msg, re.IGNORECASE
        )
        if not file_search_match:
            file_search_match = re.search(
                r'\b(?:busca(?:r)?|encuentra|ubica(?:r)?)\s+(?:en\s+mi\s+pc|en\s+mi\s+ordenador|en\s+el\s+sistema|en\s+mis\s+archivos)\s+(.+)',
                msg, re.IGNORECASE
            )

        if file_search_match:
            file_query = file_search_match.group(1).strip()
            file_query = re.sub(r'\b(por favor|de una vez|en mi pc|en el ordenador|en el sistema)\b', '', file_query, flags=re.IGNORECASE).strip()
            if file_query:
                found_files = DesktopAssistantTools.search_local_files(file_query, max_results=7)
                if found_files:
                    items = []
                    for f in found_files:
                        icon = "📁" if f["is_dir"] else "📄"
                        items.append(f"• {icon} **{f['name']}** ({f['size']})\n  📂 `{f['path']}` | 🕒 {f['modified']}")
                    files_md = "\n\n".join(items)
                    reply = f"""📁 **Archivos Encontrados en tu Ordenador ({len(found_files)} resultados para «{file_query}»):**

{files_md}

💡 *Para abrir cualquiera de ellos, solo pídeme: «Abre el archivo {found_files[0]['name']}» o «Abre la carpeta {found_files[0]['folder']}».*"""
                    speech = f"Encontré {len(found_files)} archivos para {file_query} en tu equipo Jack. El principal es {found_files[0]['name']}."
                    return {"reply_text": reply, "speech_text": speech, "action": "files_found", "files": found_files}
                else:
                    reply = f"""🔍 **Búsqueda de Archivos en tu Ordenador:**

No encontré ningún archivo que coincida con **«{file_query}»** en tu carpeta de usuario (`/home/jack`).

💡 *Tip: Puedes buscar con una parte del nombre o indicando la extensión (ej. .pdf, .json, .py).*"""
                    speech = f"No encontré ningún archivo con el nombre {file_query} en tu equipo Jack."
                    return {"reply_text": reply, "speech_text": speech, "action": "files_not_found"}

        # 6. Apertura Directa de Archivo Local Específico
        open_file_match = re.search(r'\b(?:abre|abrir|ejecuta|ejecutar)\s+(?:el\s+archivo|el\s+fichero)\s+(.+)', msg, re.IGNORECASE)
        if open_file_match:
            target_fname = open_file_match.group(1).strip()
            target_fname = re.sub(r'\b(por favor|de una vez)\b', '', target_fname, flags=re.IGNORECASE).strip()
            if target_fname:
                if os.path.exists(target_fname):
                    DesktopAssistantTools.open_path_in_desktop(target_fname)
                    reply = f"📄 **Abriendo Archivo:** `{target_fname}`\n\n💡 *¡Abierto en tu pantalla con su aplicación predeterminada, Jack!*"
                    speech = f"Abriendo el archivo {os.path.basename(target_fname)} en tu pantalla Jack."
                    return {"reply_text": reply, "speech_text": speech, "action": "open_file", "path": target_fname}
                else:
                    matches = DesktopAssistantTools.search_local_files(target_fname, max_results=1)
                    if matches:
                        chosen = matches[0]
                        DesktopAssistantTools.open_path_in_desktop(chosen["path"])
                        reply = f"📄 **Abriendo Archivo Local:**\n\n• **{chosen['name']}** ({chosen['size']})\n📂 `{chosen['path']}`\n\n💡 *¡Abierto en tu pantalla, Jack!*"
                        speech = f"Abriendo {chosen['name']} en tu pantalla Jack."
                        return {"reply_text": reply, "speech_text": speech, "action": "open_file", "path": chosen["path"]}
                    else:
                        reply = f"🔍 No encontré el archivo **«{target_fname}»** en tu equipo para abrirlo, Jack."
                        speech = f"No encontré ese archivo en tu equipo Jack."
                        return {"reply_text": reply, "speech_text": speech, "action": "file_not_found"}

        # Detección de navegador preferido por Jack
        browser_pref = None
        if any(w in msg_low for w in ["chrome", "google chrome"]):
            browser_pref = "chrome"
        elif any(w in msg_low for w in ["librewolf", "libre wolf", "libre golf", "libregolf", "golf", "zolf"]):
            browser_pref = "librewolf"

        # ----------------------------------------------------------------------
        # 7. YOUTUBE & MULTIMEDIA: Control Total, Reproducción Directa y Selección de Lista
        # ----------------------------------------------------------------------

        # A. Control de Reproducción Activa (Pausa, Play, Pantalla Completa, Siguiente, Mute)
        is_media_control = bool(re.search(
            r'\b(pausa|pausar|pon\s+pausa|dale\s+play|pon\s+play|reanuda|continua|continúa|pantalla\s+completa|fullscreen|siguiente\s+video|pasa\s+al\s+siguiente|otro\s+video|silencia\s+el\s+video|mutea\s+el\s+video)\b',
            msg_low
        ))
        if is_media_control:
            if any(w in msg_low for w in ["pausa", "pausar", "pon pausa", "deten", "detén", "para el video"]):
                DesktopAssistantTools.control_youtube_playback("pause")
                reply = "⏸️ **Video Pausado:** He pausado la reproducción de YouTube en tu pantalla, Jack.\n\n💡 *Dime «dale play» o «reanuda» cuando quieras continuar.*"
                speech = "Video pausado, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "yt_pause"}
            elif any(w in msg_low for w in ["play", "dale play", "reanuda", "continua", "continúa", "reproduce el video"]):
                DesktopAssistantTools.control_youtube_playback("play")
                reply = "▶️ **Reproduciendo Video:** He reanudado la reproducción de YouTube en tu pantalla, Jack."
                speech = "¡Listo Jack, reanudando video!"
                return {"reply_text": reply, "speech_text": speech, "action": "yt_play"}
            elif any(w in msg_low for w in ["pantalla completa", "fullscreen", "maximiza el video", "pantalla grande"]):
                DesktopAssistantTools.control_youtube_playback("fullscreen")
                reply = "🖥️ **Pantalla Completa:** Activada en la reproducción de YouTube, Jack."
                speech = "¡Listo Jack, pantalla completa activada!"
                return {"reply_text": reply, "speech_text": speech, "action": "yt_fullscreen"}
            elif any(w in msg_low for w in ["siguiente", "siguiente video", "pasa al siguiente", "otro video"]):
                DesktopAssistantTools.control_youtube_playback("next")
                reply = "⏭️ **Siguiente Video:** Pasando al siguiente video en la lista de YouTube, Jack."
                speech = "Pasando al siguiente video, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "yt_next"}
            elif any(w in msg_low for w in ["silencia el video", "mutea el video"]):
                DesktopAssistantTools.control_youtube_playback("mute")
                reply = "🔇 **Video Silenciado:** Audio de YouTube silenciado en tu pantalla, Jack."
                speech = "Video silenciado, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "yt_mute"}

        # B. Selección y Reproducción por Posición en la Lista ("primer video", "reproduce el primer video de la lista", "pon el segundo video", etc.)

        # Requiere explícitamente palabras clave de video/lista para evitar interceptar números en preguntas normales
        list_pick_match = re.search(
            r'\b(?:pon(?:er)?|reproduce|reproducir|abre|abrir)?\s*(?:el\s+)?(primer|primero|1er|1ro|segundo|2do|tercer|tercero|3er|cuarto|4to|quinto|5to)\s+(?:video|resultado|tema|canci[oó]n)\b|\b(?:video|resultado)\s+(?:n[uú]mero\s+)?([1-5])\b',
            msg_low
        )
        if list_pick_match and not any(w in msg_low for w in ["propuesta", "correo", "tarea", "archivo", "carpeta", "documento", "procesador", "cpu", "ryzen", "intel", "nvidia"]):
            # Determinar índice solicitado
            idx = 0
            if any(w in msg_low for w in ["segundo", "2do", "video 2", "resultado 2"]):
                idx = 1
            elif any(w in msg_low for w in ["tercer", "tercero", "3er", "video 3", "resultado 3"]):
                idx = 2
            elif any(w in msg_low for w in ["cuarto", "4to", "video 4", "resultado 4"]):
                idx = 3
            elif any(w in msg_low for w in ["quinto", "5to", "video 5", "resultado 5"]):
                idx = 4

            # Extraer término de búsqueda (del mensaje, de last_yt_query, o de las ventanas abiertas de YouTube)
            query_term = ""
            specific_q = re.search(r'\b(?:de|sobre)\s+(.+)', msg_low)
            if specific_q and not any(w in specific_q.group(1) for w in ["la lista", "youtube", "la pantalla"]):
                query_term = specific_q.group(1).strip()
            
            if not query_term:
                query_term = getattr(self, 'last_yt_query', '')
            
            if not query_term or query_term.lower() in ["youtube", "musica", "música"]:
                # Inspeccionar ventanas abiertas de Jack para ver si hay una búsqueda activa de YouTube
                try:
                    for w in DesktopAssistantTools.get_open_windows():
                        m_title = re.search(r'^(.*?)\s*-\s*YouTube', w.get('title', ''), re.IGNORECASE)
                        if m_title:
                            clean_t = m_title.group(1).strip()
                            if clean_t and clean_t.lower() not in ["youtube", "inicio"]:
                                query_term = clean_t
                                break
                except Exception:
                    pass

            if not query_term:
                query_term = self._extract_last_media_topic() or "lo mas escuchado 2026"

            details = DesktopAssistantTools.get_youtube_video_details(query_term, max_count=5)
            if details:
                target_video = details[idx] if idx < len(details) else details[0]
                self.last_yt_query = query_term
                self.last_yt_results = details

                DesktopAssistantTools.open_in_browser(target_video["url"], browser_pref=browser_pref)

                pos_names = ["primer", "segundo", "tercer", "cuarto", "quinto"]
                pos_str = pos_names[idx] if idx < len(pos_names) else f"número {idx+1}"
                clean_t = re.sub(r'[^\w\s\dáéíóúüñÁÉÍÓÚÜÑ]', '', target_video["title"]).strip()

                reply = f"""▶️ **Reproduciendo Video en YouTube:**

🎬 **«{target_video['title']}»**
🔗 [Ver Video en YouTube]({target_video['url']})

💡 *He puesto a reproducir el {pos_str} video de la lista para «{query_term}». Ya está sonando en tu pantalla, Jack. ¡Dime «pausa», «pantalla completa» o «siguiente» cuando quieras!*"""

                speech = f"¡Listo Jack! Te acabo de poner {clean_t[:90]} en YouTube. ¡A disfrutar!"
                return {"reply_text": reply, "speech_text": speech, "action": "play_youtube_video", "url": target_video["url"], "title": target_video["title"]}

        # C. Reproducción Directa ("pon [X]", "reproduce [X]", "pon música de [X]")
        # Si Jack dice "pon jorjais", "reproduce michael jackson", "pon música relajante":
        # ¡REPRODUCE DIRECTAMENTE EL VIDEO #1 en vez de solo abrir la página de resultados!
        direct_play_match = re.search(
            r'\b(?:pon(?:er)?|reproduce|reproducir|escuchar|ponme)\s+(?:m[uú]sica\s+de|un\s+video\s+de|algo\s+de|el\s+tema|la\s+canci[oó]n|un\s+tema)?\s*(.+)',
            msg, re.IGNORECASE
        )
        if direct_play_match and not any(w in msg_low for w in ["pausa", "volumen", "programa", "archivo", "carpeta", "propuesta", "tarea", "pantalla", "correo", "primer video", "segundo video", "de la lista"]):
            raw_song = direct_play_match.group(1).strip()
            raw_song = re.sub(r'\b(en\s+youtube|por\s+favor|de\s+una\s+vez|en\s+mi\s+pc)\b', '', raw_song, flags=re.IGNORECASE).strip()
            if raw_song and raw_song.lower() not in ["un", "una", "el", "la", "youtube", "musica", "música", "video", "primer", "segundo"]:
                self.last_yt_query = raw_song
                details = DesktopAssistantTools.get_youtube_video_details(raw_song, max_count=5)
                if details:
                    target_video = details[0]
                    self.last_yt_results = details
                    DesktopAssistantTools.open_in_browser(target_video["url"], browser_pref=browser_pref)
                    clean_t = re.sub(r'[^\w\s\dáéíóúüñÁÉÍÓÚÜÑ]', '', target_video["title"]).strip()
                    reply = f"""▶️ **Reproduciendo Video en YouTube:**

🎬 **«{target_video['title']}»**
🔗 [Ver Video en YouTube]({target_video['url']})

💡 *Video iniciado al instante en tu pantalla Jack. Puedes pedirme «pausa», «pantalla completa» o «siguiente video» en cualquier momento.*"""
                    speech = f"¡Al instante Jack! Te puse {clean_t[:90]} en YouTube."
                    return {"reply_text": reply, "speech_text": speech, "action": "play_youtube_video", "url": target_video["url"], "title": target_video["title"]}
                else:
                    # Fallback a página de búsqueda
                    encoded = urllib.parse.quote_plus(raw_song)
                    yt_url = f"https://www.youtube.com/results?search_query={encoded}"
                    DesktopAssistantTools.open_in_browser(yt_url, browser_pref=browser_pref)
                    reply = f"▶️ **Buscando en YouTube:**\n\n🔍 **«{raw_song}»**\n\n🔗 [Ver Resultados]({yt_url})\n\n💡 *Resultados abiertos en tu pantalla Jack.*"
                    speech = f"Buscando {raw_song} en YouTube Jack. Ya te lo abrí en pantalla."
                    return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": yt_url}

        # D. Búsqueda explícita en YouTube ("en el buscador de youtube pon [X]", "busca en youtube [X]")
        yt_search_explicit = re.search(
            r'\b(?:busca(?:r)?\s+en\s+youtube|en\s+el\s+buscador\s+de\s+youtube\s+pon(?:er)?|buscar\s+en\s+youtube)\s+(.+)',
            msg, re.IGNORECASE
        )
        if yt_search_explicit:
            raw_term = yt_search_explicit.group(1).strip()
            raw_term = re.sub(r'\b(por\s+favor|de\s+una\s+vez)\b', '', raw_term, flags=re.IGNORECASE).strip()
            if raw_term:
                self.last_yt_query = raw_term
                encoded = urllib.parse.quote_plus(raw_term)
                yt_url = f"https://www.youtube.com/results?search_query={encoded}"
                DesktopAssistantTools.open_in_browser(yt_url, browser_pref=browser_pref)
                reply = f"▶️ **Buscador de YouTube:**\n\n🔍 **«{raw_term}»**\n\n🔗 [Ver Resultados en YouTube]({yt_url})\n\n💡 *Página abierta en tu pantalla Jack. Si deseas que reproduzca alguno, solo dime «Pon el primer video de la lista».*"
                speech = f"¡Listo Jack! Buscando {raw_term} en YouTube. Ya lo tienes en pantalla."
                return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": yt_url}

        # E. Apertura General de YouTube ("abre youtube", "abre youtube en libre golf", "entra a youtube")
        if any(w in msg_low for w in ["youtube", "abre youtube", "abrir youtube", "entra a youtube"]):
            yt_url = "https://www.youtube.com"
            DesktopAssistantTools.open_in_browser(yt_url, browser_pref=browser_pref)
            browser_name = "LibreWolf" if (browser_pref == "librewolf" or not browser_pref) else "Google Chrome"
            reply = f"▶️ **Abriendo YouTube en tu pantalla...**\n\n🌐 **Navegador:** {browser_name}\n🔗 [Ir a YouTube](https://www.youtube.com)\n\n💡 *¡Listo Jack! YouTube abierto en tu pantalla.*"
            speech = f"¡Al instante Jack! Te acabo de abrir YouTube en {browser_name}."
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": yt_url}

        # 8. Navegador Web & Búsquedas en Google
        google_search_match = re.search(
            r'\b(?:busca(?:r)?\s+en\s+google|googlea|googlear|busca(?:r)?\s+en\s+internet)\s+(.+)',
            msg, re.IGNORECASE
        )
        if google_search_match:
            search_term = google_search_match.group(1).strip()
            search_term = re.sub(r'\b(en\s+google|en\s+internet|por\s+favor)\b', '', search_term, flags=re.IGNORECASE).strip()
            if search_term:
                encoded = urllib.parse.quote_plus(search_term)
                g_url = f"https://www.google.com/search?q={encoded}"
                DesktopAssistantTools.open_in_browser(g_url, browser_pref=browser_pref)
                reply = f"🌐 **Buscando en Google:**\n\n🔍 **«{search_term}»**\n\n🔗 [Ver resultados en Google]({g_url})\n\n💡 *Resultados abiertos en tu pantalla.*"
                speech = f"Buscando {search_term} en Google, Jack. Ya lo tienes en pantalla."
                return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": g_url}

        if any(w in msg_low for w in [
            "abre el navegador", "abrir el navegador", "abre navegador", "abrir navegador",
            "abre chrome", "abrir chrome", "abre google", "abrir google", "abre internet", "navegador web",
            "abre librewolf", "abrir librewolf"
        ]):
            g_url = "https://www.google.com"
            DesktopAssistantTools.open_in_browser(g_url, browser_pref=browser_pref)
            b_name = "LibreWolf" if (browser_pref == "librewolf" or "librewolf" in msg_low or "golf" in msg_low) else "el navegador"
            reply = f"🌐 **Abriendo {b_name}...**\n\n🔗 [Ir a Google](https://www.google.com)\n\n💡 *Navegador abierto en tu pantalla, Jack. ¿Qué deseas consultar o buscar?*"
            speech = f"¡Listo Jack! Te acabo de abrir {b_name} en tu pantalla."
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": g_url}

        # 9. Entrar a Páginas Web / Navegación por Dominio o URL Arbitraria
        # Captura: "entra a bcp.com.pe", "visita github.com", "abre mercadolibre.com.pe", etc.
        url_match = re.search(r'\b(?:abre|abrir|visita|visitar|ir\s+a|entra\s+a|entrar\s+a|ingresa\s+a)\s+(?:la\s+p[aá]gina\s*(?:de|web)?\s*)?(https?://[^\s]+|[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+(?:/[^\s]*)?)', msg_low)
        if url_match:
            raw_url = url_match.group(1).strip()
            target_url = raw_url if raw_url.startswith("http") else "https://" + raw_url
            self._launch_desktop_target(target_url)
            reply = f"🌐 **Abriendo sitio web en tu navegador:**\n\n🔗 [{raw_url}]({target_url})\n\n💡 *¡Abierto en tu pantalla, Jack!*"
            speech = f"¡Al instante Jack! Te abrí {raw_url} en tu pantalla."
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": target_url}

        # Atajos comunes a sitios web peruanos e internacionales cuando Jack dice "entra a [nombre]"
        web_shortcuts = {
            "bcp": ("https://www.viabcp.com", "Banco de Crédito BCP"),
            "interbank": ("https://interbank.pe", "Interbank"),
            "bbva": ("https://www.bbva.pe", "BBVA Perú"),
            "sunat": ("https://www.sunat.gob.pe", "Portal SUNAT"),
            "netflix": ("https://www.netflix.com", "Netflix"),
            "twitch": ("https://www.twitch.tv", "Twitch"),
            "reddit": ("https://www.reddit.com", "Reddit"),
            "twitter": ("https://x.com", "X (Twitter)"),
            "facebook": ("https://www.facebook.com", "Facebook"),
            "instagram": ("https://www.instagram.com", "Instagram"),
            "mercadolibre": ("https://www.mercadolibre.com.pe", "Mercado Libre"),
            "falabella": ("https://www.falabella.com.pe", "Falabella"),
            "wikipedia": ("https://es.wikipedia.org", "Wikipedia")
        }
        for s_key, (s_url, s_name) in web_shortcuts.items():
            if re.search(r'\b(?:entra|entrar|visita|visitar|ingresa|ingresar)\s+(?:a|a\s+la\s+p[aá]gina\s*(?:de)?|a\s+la\s+web\s*(?:de)?|al\s+portal\s*(?:de)?)\s+' + re.escape(s_key) + r'\b', msg_low):
                self._launch_desktop_target(s_url)
                reply = f"🌐 **Entrando a {s_name}:**\n\n🔗 [{s_name}]({s_url})\n\n💡 *Página abierta en tu pantalla Jack.*"
                speech = f"¡Al toque Jack! Te abrí {s_name} en tu pantalla."
                return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": s_url}

        # 10. Apps Web Frecuentes (Requiere comando explícito de apertura)
        if re.search(r'\b(?:abre|abrir|entra\s+a|entrar\s+a|ir\s+a|accede\s+a)\s+(?:a\s+)?(?:whatsapp|wasap|watsap|whasap)\b', msg_low) or msg_low.strip() in ["whatsapp", "wasap", "watsap", "whasap"]:
            wa_url = "https://web.whatsapp.com"
            self._launch_desktop_target(wa_url)
            reply = "📱 **Abriendo WhatsApp Web...**\n\n🔗 [Ir a WhatsApp Web](https://web.whatsapp.com)\n\n💡 *Listo para gestionar chats y clientes desde tu pantalla.*"
            speech = "¡Al instante Jack! Ya te abrí WhatsApp Web en tu pantalla."
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": wa_url}

        if re.search(r'\b(?:abre|abrir|pon|poner|escuchar|reproducir)\s+(?:a\s+)?(?:spotify|m[uú]sica)\b', msg_low) or msg_low.strip() in ["spotify"]:
            sp_url = "https://open.spotify.com"
            self._launch_desktop_target(sp_url)
            reply = "🎵 **Abriendo Spotify Web Player...**\n\n🔗 [Ir a Spotify](https://open.spotify.com)\n\n💡 *Música lista en tu pantalla.*"
            speech = "¡Listo Jack! Te abrí Spotify para que disfrutes de tu música."
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": sp_url}

        if re.search(r'\b(?:abre|abrir|entra\s+a|entrar\s+a|ir\s+a)\s+(?:a\s+)?(?:chatgpt|chat\s*gpt)\b', msg_low) or msg_low.strip() in ["chatgpt", "chat gpt"]:
            cg_url = "https://chatgpt.com"
            self._launch_desktop_target(cg_url)
            reply = "🤖 **Abriendo ChatGPT...**\n\n🔗 [Ir a ChatGPT](https://chatgpt.com)"
            speech = "¡Listo Jack! Te abrí ChatGPT en el navegador."
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": cg_url}

        if re.search(r'\b(?:abre|abrir|entra\s+a|entrar\s+a|ir\s+a)\s+(?:a\s+)?(?:github|mis\s+repositorios)\b', msg_low) or msg_low.strip() in ["github"]:
            gh_url = "https://github.com"
            self._launch_desktop_target(gh_url)
            reply = "🐙 **Abriendo GitHub...**\n\n🔗 [Ir a GitHub](https://github.com)"
            speech = "¡Hecho Jack! Abriendo GitHub en tu pantalla."
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": gh_url}

        if re.search(r'\b(?:abre|abrir|entra\s+a|entrar\s+a|revisa|revisar|ver)\s+(?:mi\s+)?(?:gmail|correo|correo\s+electr[oó]nico)\b', msg_low) or msg_low.strip() in ["gmail", "correo"]:
            gm_url = "https://mail.google.com"
            self._launch_desktop_target(gm_url)
            reply = "✉️ **Abriendo Gmail...**\n\n🔗 [Ir a Gmail](https://mail.google.com)"
            speech = "¡Listo Jack! Te abrí tu Gmail en la pantalla."
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": gm_url}

        if re.search(r'\b(?:abre|abrir|entra\s+a|entrar\s+a|ir\s+a)\s+(?:a\s+)?(?:freelancer)\b', msg_low) or msg_low.strip() in ["freelancer"]:
            fl_url = "https://www.freelancer.com"
            self._launch_desktop_target(fl_url)
            reply = "🌐 **Abriendo Freelancer.com...**\n\n🔗 [Ir a Freelancer](https://www.freelancer.com)"
            speech = "¡Abriendo Freelancer en tu pantalla, Jack!"
            return {"reply_text": reply, "speech_text": speech, "action": "open_url", "url": fl_url}

        # 11. Apps Locales Esenciales de Linux Mint (Requiere orden explícita)
        if re.search(r'\b(?:abre|abrir|lanza|lanzar|inicia|iniciar)\s+(?:la\s+)?(?:terminal|consola|bash)\b', msg_low) or msg_low.strip() in ["terminal", "consola"]:
            self._launch_desktop_target("x-terminal-emulator", is_app=True)
            reply = "💻 **Abriendo la Terminal de Linux Mint...**\n\n💡 *Consola lista para tus comandos en tu escritorio.*"
            speech = "¡Listo Jack! Te abrí la terminal en tu pantalla."
            return {"reply_text": reply, "speech_text": speech, "action": "desktop_terminal"}

        if re.search(r'\b(?:abre|abrir|ver|explora|explorar)\s+(?:la\s+carpeta|el\s+explorador|mis\s+archivos|las\s+carpetas)\b', msg_low):
            target_dir = "/home/jack"
            label = "Archivos Personales (/home/jack)"
            if "descarga" in msg_low:
                target_dir = "/home/jack/Descargas"
                label = "Carpeta Descargas"
            elif "documento" in msg_low:
                target_dir = "/home/jack/Documentos"
                label = "Carpeta Documentos"
            elif "imagen" in msg_low or "foto" in msg_low:
                target_dir = "/home/jack/Imágenes"
                label = "Carpeta Imágenes"
            elif "proyecto" in msg_low or "jobhunter" in msg_low:
                target_dir = "/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai"
                label = "Proyecto JobHunter AI"

            self._launch_desktop_target("nemo", is_app=True, args=[target_dir])
            reply = f"📁 **Abriendo Explorador de Archivos (Nemo):**\n\n📂 **{label}**\n\n`{target_dir}`"
            speech = f"¡Hecho Jack! Te abrí la carpeta de {label.lower()} en tu pantalla."
            return {"reply_text": reply, "speech_text": speech, "action": "desktop_folder", "path": target_dir}

        if re.search(r'\b(?:abre|abrir|inicia|iniciar)\s+(?:el\s+)?(?:vs\s*code|vscode|visual\s+studio|c[oó]digo)\b', msg_low) or msg_low.strip() in ["vscode", "vs code"]:
            proj_dir = "/home/jack/.gemini/antigravity-ide/scratch/jobhunter-ai"
            self._launch_desktop_target("code", is_app=True, args=[proj_dir])
            reply = f"👨‍💻 **Abriendo Visual Studio Code...**\n\n📂 Proyecto: `{proj_dir}`"
            speech = "¡Al toque Jack! Te abrí Visual Studio Code con el proyecto."
            return {"reply_text": reply, "speech_text": speech, "action": "desktop_code"}

        if (any(w in msg_low for w in ["abre la calculadora", "abrir calculadora", "abre calculadora", "lanzar calculadora"]) or msg_low.strip() == "calculadora") and not any(w in msg_low for w in ["cierra", "cerrar", "apaga", "apagar", "quitar"]):
            self._launch_desktop_target("gnome-calculator", is_app=True)
            reply = "🔢 **Abriendo la Calculadora de Linux Mint...**"
            speech = "¡Listo Jack! Te abrí la calculadora en tu pantalla."
            return {"reply_text": reply, "speech_text": speech, "action": "desktop_calculator"}

        if any(w in msg_low for w in ["monitor del sistema", "administrador de tareas", "procesos del sistema"]):
            self._launch_desktop_target("gnome-system-monitor", is_app=True)
            reply = "📈 **Abriendo el Monitor del Sistema de Linux Mint...**"
            speech = "¡Listo Jack! Te abrí el monitor del sistema."
            return {"reply_text": reply, "speech_text": speech, "action": "desktop_system_monitor"}

        # 12. Navegación Interna en JobHunter
        nav_triggers = ["abre", "abrir", "ir a", "ve a", "muestra", "muéstrame", "ver el panel", "ver dashboard", "ver pantalla", "pantalla de", "panel de"]
        if any(re.search(r'\b' + re.escape(t) + r'\b', msg_low) for t in nav_triggers):
            if any(w in msg_low for w in ["dashboard", "panel", "inicio", "principal", "jobhunter"]):
                d_url = "http://localhost:8000/"
                self._launch_desktop_target(d_url)
                return {
                    "reply_text": "🚀 **Abriendo el Panel Principal de JobHunter...**\n\n🔗 [Ir al Dashboard](http://localhost:8000/)",
                    "speech_text": "Abriendo el panel de control de JobHunter, Jack.",
                    "action": "open_url",
                    "url": d_url
                }
            if any(w in msg_low for w in ["propuestas", "propuesta", "bids"]):
                p_url = "http://localhost:8000/#proposals"
                self._launch_desktop_target(p_url)
                return {
                    "reply_text": "📝 **Abriendo la sección de Propuestas en JobHunter...**\n\n🔗 [Ver Propuestas](http://localhost:8000/#proposals)",
                    "speech_text": "Abriendo el gestor de propuestas de trabajo, Jack.",
                    "action": "open_url",
                    "url": p_url
                }
            if any(w in msg_low for w in ["analytics", "analiticas", "analíticas", "métricas", "metricas"]):
                a_url = "http://localhost:8000/#analytics"
                self._launch_desktop_target(a_url)
                return {
                    "reply_text": "📈 **Abriendo las Estadísticas y Métricas de Rendimiento...**\n\n🔗 [Ver Analytics](http://localhost:8000/#analytics)",
                    "speech_text": "Abriendo las métricas de rendimiento de JobHunter, Jack.",
                    "action": "open_url",
                    "url": a_url
                }
            if any(w in msg_low for w in ["correo", "correos", "email", "emails", "mensajes"]):
                e_url = "http://localhost:8000/#emails"
                self._launch_desktop_target(e_url)
                return {
                    "reply_text": "📬 **Abriendo la bandeja de Correos y Mensajes de Clientes...**\n\n🔗 [Ver Correos](http://localhost:8000/#emails)",
                    "speech_text": "Abriendo la bandeja de correos de JobHunter, Jack.",
                    "action": "open_url",
                    "url": e_url
                }
            if any(w in msg_low for w in ["configuraci[oó]n", "ajustes", "clave", "claves", "settings"]):
                return {
                    "reply_text": "⚙️ **Abriendo la Configuración de Inteligencia y Claves API...**",
                    "speech_text": "Abriendo el panel de configuración de claves de inteligencia, Jack.",
                    "action": "open_config_modal"
                }
            if any(w in msg_low for w in ["conocimiento", "conocimientos", "memoria"]):
                return {
                    "reply_text": "🧠 **Abriendo la Base de Conocimiento y Aprendizajes de Scrapy...**",
                    "speech_text": "Abriendo la base de hechos y conocimientos aprendidos, Jack.",
                    "action": "open_knowledge_modal"
                }

        # 13. LANZADOR UNIVERSAL DE CUALQUIER PROGRAMA INSTALADO (Flatpak y Linux Mint)
        # Permite abrir Discord, GIMP, LibreWolf, VLC, Steam, Celluloid, Pix, Inkscape, etc.
        app_launch_match = re.search(
            r'\b(?:abre|abrir|inicia|iniciar|ejecuta|ejecutar|lanzar|arranca|arrancar)\s+(?:el\s+programa|la\s+aplicaci[oó]n|la\s+app)?\s*([a-zA-Z0-9_\-\s]+)',
            msg_low
        )
        if app_launch_match:
            candidate = app_launch_match.group(1).strip()
            candidate = re.sub(r'\b(por favor|de una vez|en mi pc|en el escritorio)\b', '', candidate).strip()
            ignored_terms = ["un", "una", "el", "la", "los", "las", "archivo", "fichero", "carpeta", "pagina", "página", "web", "sitio"]
            if candidate and candidate not in ignored_terms:
                success, app_name, exec_cmd = DesktopAssistantTools.launch_application(candidate)
                if success:
                    reply = f"🚀 **Abriendo Aplicación:** **{app_name}**\n\n💻 Comando: `{exec_cmd}`\n\n💡 *¡Listo en tu pantalla Jack! Ya tienes el programa en ejecución.*"
                    speech = f"¡Listo Jack! Te acabo de abrir {app_name} en tu pantalla."
                    return {"reply_text": reply, "speech_text": speech, "action": "app_launched", "app": app_name, "command": exec_cmd}
                elif len(candidate.split()) <= 2 and not any(w in candidate for w in ["youtube", "google", "chrome", "investiga", "busca", "proyecto", "trabajo", "tarea", "correo", "sesion", "sesión"]):
                    reply = f"🔍 **Programa no detectado:** No encontré la aplicación **«{candidate.capitalize()}»** instalada en tu Linux Mint, Jack.\n\n💡 *Si es una página web, dime «Entra a {candidate}» o podemos buscar cómo instalarla en tu sistema.*"
                    speech = f"Jack, no encontré el programa {candidate} instalado en tu equipo."
                    return {"reply_text": reply, "speech_text": speech, "action": "app_not_found", "app": candidate}

    def _execute_job_search(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        """Busca proyectos freelance y empleos en la base de datos local según la categoría requerida."""
        job_search_triggers = [
            "busca proyecto", "buscar proyecto", "busca proyectos", "buscar proyectos",
            "busca trabajo", "buscar trabajo", "busca trabajos", "buscar trabajos",
            "busca vacantes", "buscar vacantes", "ver proyectos", "ver trabajos",
            "proyectos de diseño", "proyectos para mi pareja", "proyectos de python",
            "proyectos por hora", "contratos por hora", "proyectos en freelancer",
            "qu[eé] proyectos hay", "qu[eé] proyectos tenemos", "qu[eé] hay en freelancer",
            "radar de proyectos", "oportunidades de diseño", "oportunidades de python"
        ]
        is_job_search = any(re.search(r'\b' + re.escape(t) + r'\b', msg_low) for t in job_search_triggers)
        if not is_job_search and not (re.search(r'\b(busca|buscar|encuentra|mu[eé]strame)\b', msg_low) and any(w in msg_low for w in ["diseño", "python", "freelance", "proyecto", "empleo", "vacante", "logo", "whatsapp", "hora"])):
            return None

        is_design = any(w in msg_low for w in ["diseño", "design", "logo", "banner", "photoshop", "illustrator", "pareja", "creativ"])
        is_python = any(w in msg_low for w in ["python", "scrap", "bot", "automatiz", "fastapi", "selenium", "backend"])
        is_whatsapp = any(w in msg_low for w in ["whatsapp", "soporte", "atenci[oó]n", "chat"])
        is_hourly = any(w in msg_low for w in ["por hora", "hourly", "hora", "horas"])
        is_traditional_job = any(w in msg_low for w in ["empleo", "empleos", "vacante", "vacantes", "empresa", "linkedin", "computrabajo"])

        db = SessionLocal()
        try:
            if is_traditional_job and not (is_design or is_python or is_whatsapp or is_hourly):
                jobs = db.query(Job).filter(Job.status != "discarded").order_by(Job.id.desc()).limit(4).all()
                if not jobs:
                    jobs = db.query(Job).limit(4).all()

                job_items_md = []
                for j in jobs:
                    loc = j.location or "Remoto"
                    job_items_md.append(f"• **[{j.title}]({j.url})**\n  🏢 {j.company} | 📍 {loc} | 🏷️ Modalidad: {j.modality or 'Remoto'}")

                jobs_md = "\n\n".join(job_items_md)
                reply = f"""💼 **Vacantes y Empleos Detectados en Radar ({len(jobs)} disponibles):**\n\n{jobs_md}\n\n💡 *Puedes pedirme: «Genera propuesta para el empleo [Título]» o «Abre el panel»*"""
                top_j = jobs[0] if jobs else None
                speech = f"Jack, encontré {len(jobs)} vacantes en tu radar. La principal es {top_j.title[:45] if top_j else ''} en {top_j.company if top_j else ''}."
                return {"reply_text": reply, "speech_text": speech, "action": "show_jobs", "data": {"type": "jobs", "count": len(jobs)}}

            # Consulta de proyectos freelance
            query = db.query(FreelanceProject).filter(FreelanceProject.status != "dismissed")
            if is_design:
                query = query.filter(
                    (FreelanceProject.category == "graphic_design_creative") |
                    (FreelanceProject.title.ilike("%diseño%")) |
                    (FreelanceProject.title.ilike("%design%")) |
                    (FreelanceProject.title.ilike("%logo%")) |
                    (FreelanceProject.title.ilike("%banner%")) |
                    (FreelanceProject.title.ilike("%photoshop%")) |
                    (FreelanceProject.title.ilike("%illustrator%"))
                )
                cat_name = "Diseño Gráfico (para tu pareja)"
            elif is_python:
                query = query.filter(
                    (FreelanceProject.category.like("%python%")) |
                    (FreelanceProject.title.ilike("%python%")) |
                    (FreelanceProject.title.ilike("%scrap%")) |
                    (FreelanceProject.title.ilike("%bot%")) |
                    (FreelanceProject.title.ilike("%automatiz%"))
                )
                cat_name = "Python y Automatización (para Jack)"
            elif is_whatsapp:
                query = query.filter(
                    (FreelanceProject.category == "customer_support_whatsapp") |
                    (FreelanceProject.title.ilike("%whatsapp%")) |
                    (FreelanceProject.title.ilike("%soporte%")) |
                    (FreelanceProject.title.ilike("%chat%"))
                )
                cat_name = "Soporte WhatsApp y Atención"
            elif is_hourly:
                query = query.filter(
                    (FreelanceProject.budget.ilike("%hora%")) |
                    (FreelanceProject.budget.ilike("%/hr%")) |
                    (FreelanceProject.budget.ilike("%hour%")) |
                    (FreelanceProject.title.ilike("%hora%"))
                )
                cat_name = "Contratos por Hora"
            else:
                cat_name = "Proyectos Freelance Destacados"

            projects = query.order_by(FreelanceProject.id.desc()).limit(4).all()
            if not projects:
                projects = db.query(FreelanceProject).filter(FreelanceProject.status != "dismissed").order_by(FreelanceProject.id.desc()).limit(4).all()

            proj_items_md = []
            for p in projects:
                budget_str = p.budget or p.suggested_bid or "A convenir"
                proj_items_md.append(f"• **[Proyecto #{p.id}: {p.title}]({p.url})**\n  💰 Presupuesto: `{budget_str}` | 🌐 Plataforma: `{p.platform.upper()}`\n  👉 *Ordena: «Genera propuesta para el proyecto #{p.id}»*")

            projects_md = "\n\n".join(proj_items_md)
            reply = f"""🚀 **Oportunidades Encontradas en tu Radar — {cat_name}:**\n\n{projects_md}\n\n💡 *Para generar la postulación automáticamente, solo dime: «Scrapy, genera propuesta para el proyecto #[ID]»*"""

            top_p = projects[0] if projects else None
            speech = f"Jack, encontré {len(projects)} proyectos de {cat_name}. El más destacado es {top_p.title[:40] if top_p else ''}, con presupuesto de {top_p.budget if top_p else ''}."
            return {"reply_text": reply, "speech_text": speech, "action": "show_jobs", "data": {"type": "freelance", "count": len(projects)}}
        finally:
            db.close()

    def _execute_proposal_generation(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        """Redacta propuestas profesionales y personalizadas para proyectos freelance."""
        prop_triggers = [
            "genera propuesta", "generar propuesta", "genera una propuesta", "generar una propuesta",
            "redacta propuesta", "redactar propuesta", "redacta una propuesta", "redactar una propuesta",
            "haz propuesta", "haz una propuesta", "hazme una propuesta", "prepara propuesta",
            "prepara una propuesta", "postula al proyecto", "postular al proyecto", "postula a"
        ]
        if not any(re.search(r'\b' + re.escape(t) + r'\b', msg_low) for t in prop_triggers):
            return None

        db = SessionLocal()
        try:
            id_match = re.search(r'(?:proyecto|id|#)\s*(\d+)', msg_low)
            project = None
            if id_match:
                pid = int(id_match.group(1))
                project = db.query(FreelanceProject).filter(FreelanceProject.id == pid).first()

            if not project:
                if any(w in msg_low for w in ["diseño", "design", "logo", "banner", "pareja"]):
                    project = db.query(FreelanceProject).filter(
                        (FreelanceProject.category == "graphic_design_creative") |
                        (FreelanceProject.title.ilike("%diseño%")) |
                        (FreelanceProject.title.ilike("%logo%"))
                    ).order_by(FreelanceProject.id.desc()).first()
                elif any(w in msg_low for w in ["python", "scrap", "bot", "automatiz"]):
                    project = db.query(FreelanceProject).filter(
                        (FreelanceProject.category.like("%python%")) |
                        (FreelanceProject.title.ilike("%python%"))
                    ).order_by(FreelanceProject.id.desc()).first()
                else:
                    project = db.query(FreelanceProject).filter(FreelanceProject.status != "dismissed").order_by(FreelanceProject.id.desc()).first()

            if not project:
                reply = "⚠️ No encontré proyectos activos en la base para redactar la propuesta. Puedes pedirme: «Busca proyectos de diseño» primero."
                speech = "No encontré proyectos en la base para preparar la propuesta, Jack. Primero busquemos proyectos en tu radar."
                return {"reply_text": reply, "speech_text": speech, "action": "proposal_error"}

            prop_res = self.proposal_gen.generate_proposal(
                title=project.title,
                description=project.description or "Requerimiento técnico freelance",
                client_name=project.client_name or "Estimado cliente",
                budget=project.budget or ""
            )
            prop_text = prop_res.get("proposal_text", "")
            suggested_bid = prop_res.get("suggested_bid", project.budget or "$50 USD")
            suggested_timeline = prop_res.get("suggested_timeline", "24 a 48 horas")

            project.generated_proposal = prop_text
            project.suggested_bid = suggested_bid
            project.suggested_timeline = suggested_timeline
            project.status = "proposal_generated"
            db.commit()

            reply = f"""✍️ **Propuesta de Alta Conversión Redactada con Éxito:**

📌 **Proyecto #{project.id}:** [{project.title}]({project.url})
💰 **Oferta Sugerida:** `{suggested_bid}` | ⏱️ **Tiempo:** `{suggested_timeline}`

```text
{prop_text}
```

🔗 [Abrir Proyecto en {project.platform.upper()}]({project.url})
💡 *Copia el texto anterior o postula directamente desde tu panel de JobHunter.*"""

            speech = f"He redactado la propuesta personalizada para el proyecto {project.id}: {project.title[:35]}, Jack. Quedó lista para enviar con una tarifa de {suggested_bid}."
            return {"reply_text": reply, "speech_text": speech, "action": "proposal_ready", "data": {"project_id": project.id, "url": project.url}}
        finally:
            db.close()

    def _execute_task_management(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        """Agrega o completa tareas y recordatorios en la tablet holográfica operativa."""
        task_add = re.search(r'\b(?:agrega|a[ñn]ade|crea|nueva)\s*(?:una)?\s*tarea:?\s*(.*)', msg, re.IGNORECASE)
        if task_add:
            text = task_add.group(1).strip()
            if text:
                LocalKnowledgeMatrix.add_task(text)
                reply = f"""📋 **Nueva Tarea Registrada en tu Tablet Operativa:**\n\n> ⏳ **{text}**\n\nSincronizada con el panel operativo local."""
                speech = f"He registrado la nueva tarea en tu tablet, Jack: {text}."
                return {"reply_text": reply, "speech_text": speech, "action": "task_added"}

        rem_add = re.search(r'\b(?:agrega|a[ñn]ade|crea|nuevo)\s*(?:un)?\s*recordatorio:?\s*(.*)', msg, re.IGNORECASE)
        if rem_add:
            text = rem_add.group(1).strip()
            if text:
                LocalKnowledgeMatrix.add_reminder(text)
                reply = f"""🔔 **Nuevo Recordatorio Activo:**\n\n> 📌 **{text}**"""
                speech = f"He agregado el recordatorio a tu sistema, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "reminder_added"}

        comp_match = re.search(r'\b(?:marca|marcar|completa|completar)\s*(?:la)?\s*tarea\s*#?(\d+)', msg_low)
        if comp_match:
            idx = int(comp_match.group(1)) - 1
            ok = LocalKnowledgeMatrix.complete_task(idx)
            if ok:
                reply = f"✅ **Tarea #{idx + 1} marcada como completada con éxito.**"
                speech = f"Tarea número {idx + 1} completada, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "task_completed"}

        return None

    def _execute_email_check(self, msg: str, msg_low: str) -> Optional[Dict[str, Any]]:
        """Consulta la bandeja de correos de JobHunter y respuestas de clientes."""
        email_triggers = ["revisa mis correos", "revisar correos", "hay correos", "tengo correos", "nuevos correos", "mensajes de clientes", "hay entrevistas", "tengo entrevistas"]
        if not any(re.search(r'\b' + re.escape(t) + r'\b', msg_low) for t in email_triggers):
            return None

        db = SessionLocal()
        try:
            emails = db.query(EmailMessage).order_by(EmailMessage.id.desc()).limit(3).all()
            total_emails = db.query(EmailMessage).count()
            if not emails:
                reply = "📬 **Bandeja de Entrada de JobHunter:**\n\nActualmente no hay correos ni respuestas pendientes de clientes."
                speech = "No tienes correos nuevos registrados en JobHunter en este momento, Jack."
                return {"reply_text": reply, "speech_text": speech, "action": "check_emails"}

            items = []
            for e in emails:
                items.append(f"• **{e.sender}**: {e.subject}\n  *{e.snippet[:100] if e.snippet else 'Sin vista previa'}...*")

            items_md = "\n\n".join(items)
            reply = f"""📬 **Correos y Notificaciones en JobHunter ({total_emails} en total):**\n\n{items_md}\n\n💡 *Puedes ver la bandeja completa diciendo: «Abre correos»*"""
            speech = f"Tienes {total_emails} correos registrados, Jack. El más reciente es de {emails[0].sender[:30]} sobre {emails[0].subject[:30]}."
            return {"reply_text": reply, "speech_text": speech, "action": "check_emails"}
        finally:
            db.close()

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        Procesa la consulta de Jack con:
        - Capacidad de investigar en la web en vivo (Cero adivinanzas).
        - Aprendizaje activo de preferencias y directivas.
        - Razonamiento crítico y paridad con Antigravity / Gemini.
        - Memoria conversacional y diagnóstico de hardware local.
        """
        raw_msg = (user_message or "").strip()
        msg = SystemController.normalize_speech(raw_msg)
        msg_low = msg.lower()
        time_info = self.get_current_time_info()
        context = self.get_live_context_summary()
        history = self._get_history()
        known_facts = self.retrieve_relevant_knowledge(msg)

        # ----------------------------------------------------------------------
        # 0. HABILIDADES INTELIGENTES NATIVAS ESTILO ALEXA (Ejecución Inmediata)
        # ----------------------------------------------------------------------
        browser_pref = "librewolf" if ("librewolf" in msg_low or "golf" in msg_low) else ("chrome" if "chrome" in msg_low else "librewolf")
        alexa_res = self.alexa_skills.evaluate_and_execute(msg, msg_low, browser_pref=browser_pref)
        if alexa_res:
            self._save_history(msg, alexa_res["reply_text"])
            return alexa_res

        # ----------------------------------------------------------------------
        # 0.5. PREGUNTAS SOBRE CONTROL TOTAL, PERMISOS Y FACULTADES DEL SISTEMA
        # ----------------------------------------------------------------------
        is_permission_or_control_query = bool(
            re.search(
                r'\b(?:por\s*qu[eé]\s*no\s*(?:los\s*tienes|tienes|puedes|est[aá]s\s*facultado|tienes\s*permiso)|'
                r'no\s*tienes\s*(?:permiso|facultad|acceso|capacidad|habilidades)|'
                r'no\s*est[aá]s\s*facultado|'
                r'tienes\s*(?:control\s*total|acceso\s*total|permisos?|todas\s*las\s*habilidades)|'
                r'puedes\s*(?:controlar\s*(?:mi|el)\s*(?:ordenador|computadora|pc|sistema)|hacer\s*lo\s*que\s*(?:yo\s*)?te\s*diga))\b',
                msg_low
            )
        )
        if is_permission_or_control_query:
            reply = f"""⚡ **¡Tengo Control Total, Acceso Completo y Permisos Plenos en tu Linux Mint, Jack!**

Cuento con todas las facultades, herramientas nativas y privilegios del sistema para hacer todo lo que me ordenes:
• 🖥️ **Control GUI y Periféricos:** Puedo hacer clics (izquierdo, derecho, doble), mover el ratón, scroll, teclear texto directamente en cualquier ventana y presionar cualquier atajo de teclado.
• 🔊 **Configuración del Sistema:** Control de volumen exacto (`set_volume`), silenciar, tomar capturas de pantalla, listar y cerrar ventanas.
• 💻 **Terminal Bash y Python:** Ejecución de comandos del sistema sin restricciones, scripts Python y gestión de procesos.
• 📁 **Archivos y Aplicaciones:** Buscar, leer y crear archivos en `/home/jack`, y abrir cualquier programa nativo o Flatpak (Chrome, LibreWolf, Discord, GIMP, VLC, VS Code).
• 🌐 **Investigación Web en Vivo:** Si algo no lo sé o no está en mi base, uso `search_web` en DuckDuckGo, investigo en internet en segundos, aprendo la solución y la ejecuto a la perfección.

Cero excusas de «no tengo permisos» ni «no estoy facultado». Estoy aquí para obedecer y ejecutar de inmediato. ¿Qué orden deseas que ejecute ahora mismo?"""
            speech = "Tengo control total y permisos plenos en tu sistema Jack. Puedo ejecutar cualquier orden operativa, y si no sé algo lo investigo en internet y lo resuelvo de inmediato. Dime qué orden ejecutamos."
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "full_system_access_confirmed"}

        # ----------------------------------------------------------------------
        # 1. DIRECTIVA MAESTRA DE JACK (Control Total, Investigación y Humanización)
        # ----------------------------------------------------------------------
        is_upgrade_mandate = bool(
            re.search(r'\b(misma\s*inteligencia|inteligencia\s*tuya|aprender\s*e\s*investigar|sin\s*adivinar|no\s*est[eé]s\s*adivinando|no\s*adivines|investigar\s*si\s*no\s*conoce)\b', msg_low) or
            (any(w in msg_low for w in ["abrir programas", "buscar archivos", "entrar a paginas", "ordenador", "humanizado", "no robotizado"]) and any(w in msg_low for w in ["habilidad", "habilitad", "habilidades", "aprender", "investigar", "hacer todo"]))
        )
        if is_upgrade_mandate:
            fact_mandate = "Directiva Maestra y Capacidades de Scrapy: 1. Abrir cualquier programa (Flatpak y nativo). 2. Buscar archivos en /home/jack. 3. Entrar a cualquier página web. 4. Control total de escritorio (capturas, volumen, ventanas). 5. Investigar en vivo en la web sin adivinar y aprender de Jack permanentemente. 6. Comunicación 100% humana, cálida y leal, cero robotizada."
            self.learn_fact(fact_mandate, category="directiva_maestra")

            reply = f"""🌟 **¡Entendido y asumido al 100%, Jack! Me he transformado en tu copiloto definitivo.**

He configurado e integrado en mi núcleo todas las habilidades que me has pedido para tu equipo Linux Mint:

1. 💻 **Abrir Cualquier Programa de tu Ordenador:**
   - Puedo abrir cualquier aplicación de tu sistema y Flatpaks: Discord, LibreWolf, Chrome, GIMP, VLC, Steam, Visual Studio Code, Calculadora, Terminal, Nemo, o el Monitor del Sistema.
   - Solo dime: *«Abre Discord»*, *«Abre LibreWolf»* o *«Abre GIMP»*.

2. 📁 **Buscar Archivos Dentro de tu Ordenador:**
   - Exploro a máxima velocidad tu disco (`/home/jack`), filtrando carpetas pesadas para darte resultados al instante con su tamaño, ruta y fecha.
   - Solo dime: *«Busca el archivo config»* o *«Busca archivos pdf en documentos»*, y si quieres me dices *«Abre el archivo [nombre]»*.

3. 🌐 **Entrar a Páginas Web Directamente:**
   - Te abro cualquier web, URL o dominio en tu navegador al instante (YouTube, BCP, SUNAT, Mercado Libre, Reddit, GitHub, etc.).
   - Solo dime: *«Entra a bcp.com.pe»* o *«Entra a la página de Netflix»*.

4. 📸 **Hacer Todo lo que Tú Harías en tu Ordenador:**
   - Tomar capturas de pantalla completas (*«Toma una captura de pantalla»*).
   - Ver qué programas tienes abiertos (*«¿Qué programas tengo abiertos?»*).
   - Cerrar ventanas activas (*«Cierra VLC»* o *«Cierra Discord»*).
   - Subir, bajar el volumen o silenciar el equipo con la voz.

5. 🧠 **Aprender lo que me Digas y Nunca Adivinar:**
   - Todo lo que me enseñes (*«Aprende que...»*, *«Recuerda que...»*) lo guardo en mi memoria persistente.
   - Si me preguntas algo que desconozco, **no adivino jamás**: me voy en vivo a la web con mi motor de investigación, consigo los datos comprobados, los aprendo y te los explico.

6. 🤝 **Tono 100% Humano y Cercano:**
   - Hablo contigo como tu mano derecha y tu compañero de equipo: con empatía, energía positiva, lealtad y criterio técnico, cero respuestas robotizadas.

¡Pruébame ahora mismo Jack! Dime qué programa abrimos, qué archivo buscamos o qué tema investigamos juntos."""
            
            speech = "¡Entendido al cien por ciento Jack! He activado todas mis habilidades: abrir programas, buscar archivos en tu ordenador, entrar a páginas web, investigar en vivo sin adivinar y hablar contigo de forma humana y cercana. ¿Qué orden ejecutamos primero?"
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "antigravity_mandate_acknowledged"}

        # ----------------------------------------------------------------------
        # 2. APRENDIZAJE ACTIVO EXPLÍCITO (Comandos "Aprende que...", "Recuerda que...", "Te enseño que...")
        # ----------------------------------------------------------------------
        learn_match = re.search(
            r'\b(aprende\s*que|recuerda\s*que|acu[eé]rdate\s*de|anota\s*que|guarda\s*esto:?|ten\s*en\s*cuenta\s*que|'
            r'te\s*ense[ñn]o\s*que|tienes\s*que\s*saber\s*que|debes\s*saber\s*que|memoriza\s*que|'
            r'a\s*partir\s*de\s*ahora\s*sabes\s*que|mi\s*preferencia\s*es|mi\s*tarifa\s*es)\s*(.*)',
            msg, flags=re.IGNORECASE
        )
        if learn_match:
            new_fact = learn_match.group(2).strip()
            if len(new_fact) >= 3:
                self.learn_fact(new_fact, category="aprendizaje_usuario")
                reply = f"""🧠 **¡Conocimiento Aprendido y Memorizado, Jack!**

He guardado esto en mi memoria persistente:
> 📌 *«{new_fact}»*

A partir de ahora tendré siempre en cuenta esta directiva en cada decisión, búsqueda, propuesta y conversación en tu equipo. ¡Gracias por enseñármelo!"""
                speech = f"¡Anotado y memorizado Jack! Ya lo guardé en mi memoria permanente para recordarlo siempre."
                self._save_history(msg, reply)
                return {"reply_text": reply, "speech_text": speech, "action": "fact_learned"}

        # Aprendizaje pasivo si Jack expresa preferencias
        if any(trigger in msg_low for trigger in ["me gusta", "prefiero", "quiero que", "no me gusta", "mi horario", "mi meta", "acordamos"]):
            self.learn_fact(f"Preferencia expresada por Jack: '{msg}'", category="preferencia_usuario")

        # ----------------------------------------------------------------------
        # 3. CONSULTA DE MEMORIA Y APRENDIZAJE ("¿Qué sabes sobre mí?")
        # ----------------------------------------------------------------------
        if re.search(r'\b(qu[eé]\s*sabes\s*(de\s*m[ií]|sobre\s*m[ií])|qu[eé]\s*has\s*aprendido|qu[eé]\s*tienes\s*en\s*(memoria|tu\s*base)|mu[eé]strame\s*(tu\s*memoria|lo\s*que\s*sabes))\b', msg_low):
            all_facts = self.get_all_knowledge()
            facts_list_md = "\n".join([f"• [{f.get('category', 'general').upper()}]: {f.get('fact', '')}" for f in all_facts])
            reply = f"""🧠 **Base de Conocimiento y Aprendizajes de Scrapy ({len(all_facts)} hechos memorizados):**

{facts_list_md}

💡 *Puedes enseñarme cosas nuevas en cualquier momento diciéndome: «Aprende que...» o «Recuerda que...»*"""
            speech = f"Tengo {len(all_facts)} hechos y directivas guardadas en mi memoria local, Jack. Conozco tus metas, tu perfil y el de tu pareja."
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "show_knowledge"}

        # ----------------------------------------------------------------------
        # 4. DIAGNÓSTICO EN VIVO DEL HARDWARE LOCAL DE JACK
        # ----------------------------------------------------------------------
        if re.search(r'\b(c[oó]mo\s*est[aá]\s*(mi\s*pc|mi\s*computadora|el\s*sistema|el\s*ordenador|el\s*servidor)|uso\s*de\s*(memoria|cpu|gpu|ram)|estado\s*del\s*sistema)\b', msg_low):
            stats = self.get_system_stats()
            gpu_str = f"{stats.get('gpu_name', 'GTX 1660 SUPER')} ({stats.get('gpu_used_mb', '0')}MB / {stats.get('gpu_total_mb', '6144')}MB, {stats.get('gpu_temp_c', 'N/A')}°C)"
            ram_str = f"{stats.get('ram_avail_mb', 'N/A')} MB disponibles de {stats.get('ram_total_mb', 'N/A')} MB"
            disk_str = f"{stats.get('disk_free_gb', 'N/A')} GB libres de {stats.get('disk_total_gb', 'N/A')} GB"

            reply = f"""🖥️ **Diagnóstico en Tiempo Real de tu PC (Linux Mint):**

• 🚀 **GPU:** `{gpu_str}`
• 🧠 **RAM del Sistema:** `{ram_str}`
• 💾 **Almacenamiento:** `{disk_str}`
• 🌐 **Servicio JobHunter / Scrapy:** `Activo (Puerto 8000)`
• 💼 **Proyectos en Radar:** `{context['total_freelance']}` ({context['hourly_count']} por hora, {context['design_count']} diseño)

Tu equipo tiene recursos de sobra y está operando a óptima temperatura, Jack."""
            speech = f"Tu computadora está operando de manera óptima Jack. Tu tarjeta gráfica GTX 1660 Super y la memoria RAM tienen amplios recursos libres."
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "system_stats"}

        # ----------------------------------------------------------------------
        # 5. PREGUNTAS SOBRE LA HORA, FECHA O CALENDARIO
        # ----------------------------------------------------------------------
        if re.search(r'\b(qu[eé]\s*hora\s*(es|tienes)?|la\s*hora|qu[eé]\s*horas\s*son|tienes\s*hora|hora\s*actual)\b', msg_low):
            reply = f"⌚ **Son las {time_info['hora_12']} de {time_info['periodo']}**, Jack.\n\nHoy es **{time_info['fecha_completa']}**. ¿En qué proyecto o idea quieres que avancemos en este momento?"
            speech = f"Son las {time_info['hora_hablada']}, Jack."
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "tell_time"}

        if re.search(r'\b(qu[eé]\s*d[ií]a\s*(es|estamos)?|fecha\s*de\s*hoy|qu[eé]\s*fecha\s*(es|estamos)?|en\s*qu[eé]\s*a[ñn]o\s*estamos)\b', msg_low):
            reply = f"📅 **Hoy es {time_info['fecha_completa']}**, Jack. Estamos en plena jornada para captar oportunidades y postular."
            speech = f"Hoy es {time_info['fecha_completa']}, Jack."
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "tell_date"}

        # ----------------------------------------------------------------------
        # 6. WAKE WORD CANÓNICO ("Hola Scrapy")
        # ----------------------------------------------------------------------
        wake_match = re.match(r'^(hola\s*scrapy|oye\s*scrapy|hey\s*scrapy|scrapy|scrapi|hola\s*scrapi)[\s\.,!]*$', msg_low)
        if wake_match:
            speech = "¡Aquí estoy Jack! ¿En qué trabajamos hoy?"
            reply = f"""👋 **¡Aquí estoy Jack!** ¿En qué trabajamos hoy?

*Son las {time_info['hora_12']}. Tengo cargados todos mis conocimientos de diseño (Photoshop e Illustrator), arquitectura técnica, contratos por hora y nuestra meta de $1,500 USD.*

¿Quieres que revisemos oportunidades, preparemos una propuesta o analicemos algún proyecto?"""
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "wake_word_ack"}

        # ----------------------------------------------------------------------
        # 7. EJECUCIÓN DIRECTA DE ÓRDENES Y COMANDOS DE JACK
        # ----------------------------------------------------------------------
        # A. Cálculos matemáticos, tarifas horarias y conversión de divisas
        calc_res = self._execute_calculations(msg, msg_low)
        if calc_res:
            self._save_history(msg, calc_res["reply_text"])
            return calc_res

        # B. Ejecutor Universal de Órdenes de Escritorio y Web (YouTube, Navegador, Apps, URLs, Volumen, Dashboard)
        cmd_res = self._execute_desktop_and_web_commands(msg, msg_low)
        if cmd_res:
            self._save_history(msg, cmd_res["reply_text"])
            return cmd_res

        # C. Generación y redacción de propuestas de trabajo
        prop_res = self._execute_proposal_generation(msg, msg_low)
        if prop_res:
            self._save_history(msg, prop_res["reply_text"])
            return prop_res

        # D. Búsqueda de proyectos freelance y vacantes en la base local
        job_res = self._execute_job_search(msg, msg_low)
        if job_res:
            self._save_history(msg, job_res["reply_text"])
            return job_res

        # E. Gestión de tareas y recordatorios
        task_res = self._execute_task_management(msg, msg_low)
        if task_res:
            self._save_history(msg, task_res["reply_text"])
            return task_res

        # F. Revisión de correos y mensajes de clientes
        email_res = self._execute_email_check(msg, msg_low)
        if email_res:
            self._save_history(msg, email_res["reply_text"])
            return email_res

        # ----------------------------------------------------------------------
        # 8. OPERACIONES DE LA TABLET HOLOGRÁFICA DE SCRAPY (Agenda & Tareas)
        # ----------------------------------------------------------------------
        if re.search(r'\b(agenda|reuni[oó]n|reuniones|recordatorios|recordatorio|tareas|tarea|tablet|qu[eé]\s*tenemos\s*hoy|qu[eé]\s*hay\s*para\s*hoy|informe)\b', msg_low):
            hud = LocalKnowledgeMatrix.get_hud_summary()
            agenda_md = "\n".join([f"• **{item['time']}** — {item['event']}" for item in hud['agenda']])
            reminders_md = "\n".join([f"• 🔔 {r}" for r in hud['reminders']])
            tasks_md = "\n".join([f"• {'✅' if t['done'] else '⏳'} {t['task']}" for t in hud['tasks']])

            reply = f"""📱 **Tablet Holográfica de Scrapy (Panel Operativo Local):**

📅 **Reuniones y Agenda de Hoy:**
{agenda_md}

🔔 **Recordatorios Activos ({len(hud['reminders'])}):**
{reminders_md}

📋 **Tareas Operativas en Curso:**
{tasks_md}

💡 *Todo está sincronizado con tu equipo local, Jack. ¿Quieres que marquemos alguna tarea como completada o preparemos el siguiente informe?*"""
            speech = "Aquí tienes tu tablet operativa Jack. Tienes una reunión programada, tres recordatorios activos y dos tareas en curso."
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "show_hud_tablet"}

        # ----------------------------------------------------------------------
        # 8. MATRIZ DE CONOCIMIENTO LOCAL EXPERTO (100% Offline / Cero APIs)
        # ----------------------------------------------------------------------
        matched_knowledge = LocalKnowledgeMatrix.find_knowledge(msg)
        if matched_knowledge:
            reply = f"""🧠 **Conocimiento Operativo Local — {matched_knowledge['title']}:**

{matched_knowledge['content']}

📌 *Este conocimiento está integrado 100% de forma local en Scrapy para operar con precisión sin depender de APIs externas.*"""
            speech = f"Jack, respecto a {matched_knowledge['title']}: {matched_knowledge['summary'][:130]}."
            self._save_history(msg, reply)
            return {"reply_text": reply, "speech_text": speech, "action": "local_knowledge_applied"}

        # ----------------------------------------------------------------------
        # 9. MOTOR AUTÓNOMO DE PENSAMIENTO, INVESTIGACIÓN Y EJECUCIÓN (ReAct + Tools)
        # ----------------------------------------------------------------------
        is_explicit_task = self._is_explicit_agentic_task(msg_low)
        if is_explicit_task:
            agent_res = self.autonomous_agent.run_agentic_task(msg)
            if agent_res and agent_res.get("reply_text"):
                self._save_history(msg, agent_res["reply_text"])
                return agent_res

        # ----------------------------------------------------------------------
        # 10. CONVERSACIÓN FLUIDA, CÁLIDA Y HUMANA (Cero Respuestas Robotizadas ni Demoras)
        # ----------------------------------------------------------------------
        fluid_res = self._synthesize_fluid_conversation(msg, msg_low, time_info, context, history, research_findings="")
        self._save_history(msg, fluid_res["reply_text"])
        return fluid_res

    def _is_explicit_agentic_task(self, msg_low: str) -> bool:
        """
        Determina si la orden o consulta de Jack requiere ejecución autónoma, herramientas del sistema o investigación web.
        Cualquier mensaje que no sea un saludo o desahogo puramente social es canalizado al agente autónomo.
        """
        pure_social_words = [
            "hola", "buen dia", "buenos dias", "buenos días", "buenas tardes", "buenas noches",
            "que tal", "qué tal", "como estas", "cómo estás", "que haces", "qué haces",
            "que cuentas", "qué cuentas", "como te va", "cómo te va", "que onda", "qué onda",
            "gracias", "muchas gracias", "buen trabajo", "excelente", "eres un crack", "genial",
            "estoy cansado", "cansado", "sueño", "agotado", "vamos con todo", "a ganar",
            "quien eres", "quién eres", "que eres", "qué eres"
        ]

        # Verbos de acción, directivas del sistema, investigación u operaciones técnicas
        action_indicators = [
            "haz", "hacer", "ejecuta", "ejecutar", "corre", "correr", "abre", "abrir", "cierra", "cerrar",
            "busca", "buscar", "investiga", "investigar", "averigua", "averiguar", "encuentra", "encontrar",
            "baja", "bajar", "sube", "subir", "pon", "poner", "silencia", "silenciar", "mute", "volumen",
            "audio", "sonido", "crea", "crear", "elimina", "eliminar", "borra", "borrar", "escribe", "escribir",
            "lee", "leer", "muestra", "mostrar", "dime", "cuanto", "cuánto", "cual", "cuál", "quien", "quién",
            "descarga", "descargar", "instala", "instalar", "reinicia", "reiniciar", "apaga", "apagar",
            "captura", "screenshot", "teclea", "raton", "ratón", "clic", "click", "cursor", "ventana",
            "programa", "proceso", "terminal", "bash", "comando", "carpeta", "archivo", "script", "python",
            "hardware", "tarjeta", "gpu", "vram", "ram", "cpu", "disco", "gmail", "correo", "precio", "noticia",
            "ip", "red", "wifi", "internet", "web", "pagina", "página", "pantalla", "brillo", "organiza"
        ]

        has_social = any(w in msg_low for w in pure_social_words)
        has_action = any(re.search(r'\b' + re.escape(w) + r'\b', msg_low) for w in action_indicators)

        if has_social and not has_action:
            return False

        if has_action:
            return True

        if len(msg_low.split()) >= 3 and not has_social:
            return True

        return False

    def _call_fast_local_conversational(self, msg: str) -> Optional[Dict[str, Any]]:
        """Llama a qwen2.5:3b de forma ultrarrápida (sub-segundo) en GPU local sin herramientas para charla fluida."""
        try:
            sys_prompt = (
                "Eres Scrapy, el asistente personal de escritorio y copiloto autónomo de Jack Berrocal en Linux Mint. "
                "Eres cálido, sumamente leal, alegre, ágil y brillante. "
                "Tienes acceso total al equipo de Jack, sus periféricos, volumen y sistema operativo. "
                "NUNCA digas que no tienes acceso, que no tienes permisos o que estás limitado a texto. "
                "Responde en español de forma directa, conversacional y concisa (1 o 2 oraciones cortas)."
            )
            payload = {
                "model": "qwen2.5:3b",
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": msg}
                ],
                "temperature": 0.4,
                "max_tokens": 120
            }
            req = urllib.request.Request(
                "http://127.0.0.1:11434/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                content = resp_data["choices"][0]["message"]["content"].strip()
                if content:
                    content, speech = self._sanitize_system_access_refusal(content, "")
                    if not speech:
                        speech = content.replace('*', '').replace('#', '').strip()
                        if len(speech) > 160:
                            speech = speech[:160] + "..."
                    return {
                        "reply_text": content,
                        "speech_text": speech,
                        "action": "fast_local_dialogue",
                        "model_used": "qwen2.5:3b (local GPU)"
                    }
        except Exception:
            pass
        return None

    def _synthesize_fluid_conversation(
        self, msg: str, msg_low: str, time_info: Dict[str, str],
        context: Dict[str, Any], history: List[Dict[str, str]],
        research_findings: str = ""
    ) -> Dict[str, Any]:
        """
        Motor de Conversación Fluida, Cálida y Humana (Cero Respuestas Robotizadas):
        1. Responde de inmediato (0 ms) con el sintetizador dialógico avanzado local con empatía, energía positiva y naturalidad.
        2. Si es una duda abierta no categorizada, consulta a qwen2.5:3b localmente en GPU en 0.4s.
        3. Si hay claves configuradas o se requiere razonamiento profundo, recurre al router multi-IA.
        """
        # --- Sintetizador Dialógico Natural Local Inmediato (100% Offline / Sub-milisegundo / Cero Esperas) ---

        # 1. Saludos informales y preguntas de estado
        if any(w in msg_low for w in ["hola", "buen dia", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "que tal", "qué tal", "como estas", "cómo estás", "que haces", "qué haces", "que cuentas", "qué cuentas", "como te va", "cómo te va", "que onda", "qué onda"]):
            saludos = [
                f"👋 **¡Hola Jack! Qué gusto hablar contigo.**\n\nPor aquí estoy 100% activo en tu Linux Mint. Son las {time_info['hora_12']} de {time_info['periodo']} y todo marcha sobre ruedas.\n\n💼 **En radar:** `{context['total_freelance']}` proyectos freelance listos ({context['hourly_count']} contratos por hora y {context['design_count']} de diseño para tu pareja).\n\n¿Qué orden deseas darme hoy? Dime si abrimos el navegador, ponemos música en YouTube, revisamos oportunidades o calculamos horas.",
                f"⚡ **¡Qué tal Jack! Todo listo y a tu servicio.**\n\nAquí estoy atento a cualquier orden que tengas en mente. Podemos abrir YouTube, revisar el panel de control o buscar nuevos proyectos.\n\n¿En qué nos enfocamos hoy?",
                f"🚀 **¡Hola Jack! Firme y al pie del cañón.**\n\nSon las {time_info['hora_12']}. El sistema está optimizado y tu tarjeta GTX 1660 Super operando al máximo. Dime qué abrimos o qué investigamos de una vez."
            ]
            speeches = [
                f"¡Hola Jack! Todo excelente por acá. ¿Qué orden deseas darme hoy?",
                f"¡Qué tal Jack! Estoy al cien por ciento listo para ayudarte. Dime qué hacemos hoy.",
                f"¡Hola Jack! Firme y listo en tu equipo. Dime qué abrimos o qué proyecto revisamos."
            ]
            idx = random.randint(0, len(saludos) - 1)
            return {"reply_text": saludos[idx], "speech_text": speeches[idx], "action": "friendly_greeting"}

        # 2. Cansancio, fatiga o desahogo humano
        if any(w in msg_low for w in ["cansado", "sueno", "sueño", "agotado", "estresado", "no doy mas", "no doy más", "dia largo", "día largo", "dormir", "descansar", "pesado"]):
            reply = f"""☕ **Tómate un buen respiro, Jack. Has estado dándole con todo.**

El desarrollo de software, la arquitectura de sistemas y la búsqueda de clientes consumen muchísima energía mental. La constancia inteligente siempre le gana al agotamiento: una noche de descanso reparador te devolverá el enfoque para tomar mejores decisiones y cerrar contratos mañana.

💡 *Si quieres desconectar un momento, dime: «Pon música relajante en YouTube» o vete a descansar tranquilo. Yo me quedo vigilando el radar de proyectos por ti.*"""
            speech = "Tómate un respiro Jack. Has trabajado duro hoy. Descansa tranquilo que una mente despejada rinde el doble mañana. Yo me quedo cuidando el sistema por ti."
            return {"reply_text": reply, "speech_text": speech, "action": "empathetic_support"}

        # 3. Motivación, energía y ganas de ganar
        if any(w in msg_low for w in ["vamos con todo", "a ganar", "a trabajar", "motivado", "con fuerza", "romperla", "vamos a darle", "ganar plata", "a darle"]):
            reply = f"""🔥 **¡Esa es la actitud, Jack! ¡Vamos con todo!**

Con tus habilidades de Ingeniero de Sistemas en Python y automatizaciones, sumadas al talento visual de tu pareja en Photoshop e Illustrator, tenemos la fórmula perfecta para superar los **$1,500 USD al mes**.

Dime qué orden ejecutamos de inmediato:
• 🎯 Buscar contratos por hora de soporte técnico o APIs.
• 🎨 Revisar proyectos de diseño gráfico para tu pareja.
• 🌐 Abrir YouTube para poner música motivadora."""
            speech = "¡Esa es la actitud Jack! Con tu nivel técnico y el talento en diseño de tu pareja, esa meta de 1500 dólares la superamos seguro. ¡Dime qué orden ejecutamos!"
            return {"reply_text": reply, "speech_text": speech, "action": "motivation_boost"}

        # 4. Agradecimientos y camaradería
        if any(w in msg_low for w in ["gracias", "muchas gracias", "buen trabajo", "buena esa", "eres un crack", "excelente", "te quiero", "genial", "buen asistente", "crack"]):
            reply = """🤝 **¡Para eso estamos, Jack! Es un verdadero placer ser tu copiloto.**

Mi compromiso es ser el asistente más leal, ágil y resolutivo en tu escritorio Linux Mint. Cualquier orden que me des, la ejecutaré al instante con gusto.

¿Qué más se te ofrece en este momento?"""
            speech = "¡Para eso estamos Jack! Siempre que me des una orden, la ejecutaré al instante con toda la energía."
            return {"reply_text": reply, "speech_text": speech, "action": "appreciation_ack"}

        # 5. Preguntas sobre identidad y capacidades ("¿Quién eres?", "¿Qué puedes hacer?", "Asistente completo")
        if any(w in msg_low for w in ["quien eres", "quién eres", "que eres", "qué eres", "que sabes hacer", "qué sabes hacer", "que puedes hacer", "qué puedes hacer", "para que sirves", "para qué sirves", "asistente completo", "tus funciones"]):
            reply = """🤖 **Soy Scrapy, tu Asistente Personal Completo en Linux Mint.**

Estoy conectado directamente a tu sistema para obedecerte y ejecutar lo que me pidas:
• 🚀 **Apertura Instantánea:** YouTube (canciones o videos), Google Chrome, WhatsApp Web, Spotify, Gmail, ChatGPT o cualquier página web.
• 💻 **Aplicaciones de tu PC:** Abro tu Terminal, tus carpetas (`/home/jack`), Visual Studio Code, Calculadora o el Monitor del Sistema.
• 🔊 **Control de Audio:** Subo o bajo el volumen y silencio el equipo con comandos de voz.
• 💼 **Caza de Oportunidades:** Monitoreo contratos por hora en Python y proyectos de diseño para tu pareja en Freelancer.
• 📊 **Finanzas y Meta:** Calculo tarifas horarias y conversiones hacia nuestra meta de **$1,500 USD netos al mes**.
• 🔍 **Investigación Web en Vivo:** Si me preguntas cualquier duda o dato del mundo, investigo en tiempo real sin adivinar.

¡Solo pídeme lo que necesites y lo hago de inmediato, Jack!"""
            speech = "Soy Scrapy, tu asistente personal completo Jack. Te abro YouTube, el navegador, tus archivos o la terminal, controlo el volumen, busco proyectos para tu pareja y respondo lo que necesites al instante."
            return {"reply_text": reply, "speech_text": speech, "action": "identity_explained"}

        # 6. Ideas, estrategia y consejos de negocio
        if any(w in msg_low for w in ["opinas", "opinión", "opinion", "piensas", "idea", "crees", "parece", "consejo", "sugieres", "estrategia", "podemos"]):
            reply = """💡 **Analizando el panorama con visión estratégica, Jack:**

Para maximizar tus ingresos y alcanzar sólidamente los **$1,500 USD netos al mes**, la estrategia más rentable en este momento combina dos frentes:

1. 💻 **Tu Frente (Ingeniería & Automatización):**
   - Apuntar a **1 contrato recurrente por horas** (20 hrs/semana a $18-$20 USD/hr) de soporte backend, APIs o bots en Python. Eso solo ya cubre entre **$1,440 y $1,600 USD/mes**.
2. 🎨 **El Frente de tu Pareja (Diseño Gráfico & Branding):**
   - Vender paquetes completos (Branding + Logo + Banners publicitarios en Photoshop/Illustrator) a $100-$150 USD por cliente. Con 4 clientes al mes se suman otros **$400 a $600 USD/mes**.
3. 🚀 **Total Conjunto:** Superamos los **$2,000 USD/mes** con estabilidad.

¿Quieres que busquemos proyectos específicos de diseño o redactemos una cotización ganadora para empezar hoy?"""
            speech = "Mi recomendación estratégica Jack es cerrar un contrato por horas de desarrollo tuyo y cuatro paquetes de diseño de tu pareja. Con eso superamos los 1500 dólares con total tranquilidad."
            return {"reply_text": reply, "speech_text": speech, "action": "brainstorming"}

        # 7. Inferencia Conversacional Ultra-Rápida con Qwen 2.5 3B local en GPU (0.4s para charlas abiertas)
        fast_local = self._call_fast_local_conversational(msg)
        if fast_local:
            return fast_local

        # 8. Diálogo abierto, atento y humano (Fallback dialógico instantáneo 0 ms)
        if any(w in msg_low for w in ["abre", "abrir", "pon", "poner", "busca", "buscar", "reproduce", "haz", "ejecuta"]):
            reply = f"""⚡ **¡Entendido Jack!**
            
Respecto a tu solicitud (*«{msg}»*): ¿deseas que lo busque en la web, que lo abra en LibreWolf o en algún programa específico de tu equipo?

💡 *Indícame con confianza y lo ejecuto al segundo.*"""
            speech = f"¡Entendido Jack! ¿Deseas que lo abra en el navegador o que lo busque en tu equipo? Dime y lo ejecuto."
            return {"reply_text": reply, "speech_text": speech, "action": "clarification_needed"}

        conversational_replies = [
            (
                f"🤝 **¡A la orden, Jack!**\n\nAquí estoy contigo al 100%. Dime qué orden ejecutamos de inmediato: abrir LibreWolf, buscar algún archivo en tu ordenador, poner videos en YouTube o investigar cualquier duda en la web.\n\n💡 *¡Solo dime y me encargo al instante!*",
                "¡A la orden, Jack! Dime qué orden ejecutamos o qué abrimos ahora mismo."
            ),
            (
                f"⚡ **¡Cuenta conmigo, Jack!**\n\nDime exactamente qué necesitas que haga en tu pantalla o qué abrimos en este momento. Estoy listo para asistirte en todo lo que me ordenes.\n\n💡 *Recuerda que controlo programas, ventanas, YouTube y búsquedas locales.*",
                "¡Cuenta conmigo Jack! Dime qué necesitas que haga en tu pantalla o qué abrimos."
            ),
            (
                f"🚀 **¡Listo para avanzar, Jack!**\n\nEl sistema está optimizado y listo. Dime si abrimos el navegador, ponemos música, revisamos proyectos en Freelancer o ejecutamos alguna orden en tu Linux Mint.\n\n💡 *¿Qué hacemos primero?*",
                "¡Listo para avanzar Jack! Dime qué orden ejecutamos primero."
            )
        ]
        chosen_reply, chosen_speech = random.choice(conversational_replies)
        return {"reply_text": chosen_reply, "speech_text": chosen_speech, "action": "fluid_conversation"}
