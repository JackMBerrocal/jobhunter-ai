import os
import re
import json
import urllib.request
from typing import Dict, Any, Optional

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class ProposalGenerator:
    """
    Motor de Inteligencia Artificial y Razonamiento Cognitivo para Propuestas Freelance.
    Distingue con precisión la naturaleza del requerimiento:
    - Servicios humanos (Atención por WhatsApp, Soporte, Setter de Ventas, Asistencia Virtual)
    - Proyectos de desarrollo de software (Chatbots con IA, Web Scraping, Power BI, QA, SQL, Web)
    Aplica tarifas reales (por hora o por proyecto) y redacta propuestas persuasivas en español.
    """

    def __init__(self, llm_engine=None):
        self.llm = llm_engine
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")
        self.gemini_client = None

        if HAS_GENAI and self.gemini_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_key)
            except Exception as e:
                print(f"[ProposalGenerator] Warning Gemini client: {e}")

    def categorize_project(self, title: str, description: str = "", skills: list = None) -> str:
        """
        Analiza cognitivamente la intención y categoría del proyecto.
        Prioriza la distinción entre servicio humano vs desarrollo técnico vs bots.
        """
        text = f"{title} {description} {' '.join(skills or [])}".lower()
        t_low = title.lower()

        # 1. Trading Bot / Finanzas Automatizadas -> python_automation_scraping
        if any(w in text for w in ["trading", "cripto", "crypto", "binance", "metatrader", "swing trading"]):
            return "python_automation_scraping"

        # 2. Setter de Ventas & Agendamiento Comercial & Asesorías Fitness
        if any(w in text for w in [
            "setter", "asesoría fitness", "asesoria fitness", "llamadas de venta", "appointment setter",
            "agendar llamadas", "agendamiento de llamadas", "prospección", "prospeccion",
            "cold caller", "closer", "cerrador", "lead qualification"
        ]):
            return "sales_setter_crm"

        # 3. Sistemas / Chatbots con Inteligencia Artificial & Bots de Software (Desarrollo técnico)
        if any(w in text for w in [
            "bot faq", "asistente automático", "asistente automatico", "crear chatbot",
            "desarrollo de bot", "desarrollar chatbot", "bot con ia", "chatbot con inteligencia",
            "sistema automatizado con ia", "bot de whatsapp", "bot whatsapp", "flujo manychat",
            "agente con ia", "agente ia", "bot inteligente", "automatizar respuestas con ia",
            "chatbot gpt", "chatbot", "typebot", "voicebot", "el bot debe"
        ]) or (("bot " in text or " bot" in text) and "responder mensajes" not in t_low and "atención al cliente" not in t_low):
            return "ai_chatbot_system"

        # 4. Soporte & Atención Humana por Chat / WhatsApp
        if any(w in t_low for w in ["whatsapp", "responder mensajes", "atención al cliente", "atencion al cliente", "chat"]) or any(w in text for w in [
            "responder mensajes", "atención al cliente", "atencion al cliente",
            "customer service", "customer support", "soporte por chat", "chat support",
            "contestar mensajes", "atender mensajes", "chat de atención", "moderador de chat",
            "atención de consultas"
        ]):
            return "customer_support_whatsapp"

        # 5. Asistencia Virtual & Admin
        if any(w in text for w in [
            "asistente virtual", "virtual assistant", "asistente administrativo", "gestión de correos",
            "gestion de correos", "data entry", "transcripción", "transcripcion", "agenda"
        ]):
            return "virtual_assistant_admin"

        # 5. Power BI & Analítica de Datos
        if any(w in text for w in [
            "power bi", "powerbi", "dax", "dashboard", "power query", "kpi",
            "business intelligence", "analista de datos", "reporte en excel", "modelado de datos"
        ]):
            return "power_bi_data"

        # 6. Web Scraping & Extracción con Python (Solo cuando piden extracción o scripts)
        if any(w in text for w in [
            "scraping", "scraper", "crawling", "extraer datos", "extracción de datos",
            "extraccion de datos", "script python", "script en python", "playwright",
            "selenium", "beautifulsoup", "automatizar excel con python"
        ]):
            return "python_automation_scraping"

        # 7. QA Testing & Pruebas de Software
        if any(w in text for w in [
            "qa", "testing", "tester", "pruebas funcionales", "postman", "casos de prueba",
            "test cases", "reporte de bugs", "control de calidad", "smoke testing"
        ]):
            return "qa_testing"

        # 8. SQL & Bases de Datos
        if any(w in text for w in [
            "sql", "postgres", "postgresql", "mysql", "base de datos", "consultas sql",
            "queries", "procedimientos almacenados", "optimización de consultas", "stored procedure"
        ]):
            return "sql_database"

        # 9. Desarrollo Web & Frontend
        if any(w in text for w in [
            "web", "html", "css", "javascript", "react", "landing", "wordpress",
            "desarrollo web", "página web", "pagina web", "frontend", "sitio web"
        ]):
            return "web_dev"

        # 10. Soporte TI / Helpdesk
        if any(w in text for w in [
            "soporte ti", "soporte técnico", "soporte tecnico", "helpdesk", "active directory", "anydesk"
        ]):
            return "it_support"

        return "general_tech"

    def estimate_bid_and_time(self, budget_str: str, category: str, full_text: str = "") -> Dict[str, str]:
        """
        Calcula el presupuesto óptimo y el tiempo/disponibilidad.
        Detecta si es por hora (Hourly) o precio fijo (Fixed), respetando la moneda.
        """
        combined = f"{budget_str} {full_text}".lower()
        is_hourly = any(h in combined for h in ["hour", "hora", "hr", "/h", "hourly", "/ hora", "/ hour"])

        # Detectar moneda
        currency = "USD"
        curr_symbol = "$"
        if "eur" in combined or "€" in combined:
            currency = "EUR"
            curr_symbol = "€"
        elif "pen" in combined or "s/" in combined or "soles" in combined:
            currency = "PEN"
            curr_symbol = "S/"
        elif "cop" in combined:
            currency = "COP"
            curr_symbol = "COP $"
        elif "mxn" in combined:
            currency = "MXN"
            curr_symbol = "MXN $"

        # Extraer valores numéricos limpios
        raw_nums = re.findall(r'(?<!\w)(\d+(?:\.\d+)?)(?!\w)', budget_str or "")
        numbers = [float(n) for n in raw_nums if float(n) > 0]

        if is_hourly:
            if numbers:
                min_v = min(numbers)
                max_v = max(numbers)
                if min_v == max_v:
                    suggested_rate = int(min_v)
                else:
                    # Elegir punto medio-alto competitivo (e.g. de 15-25 -> 20)
                    suggested_rate = int(round(min_v + (max_v - min_v) * 0.6))
            else:
                defaults_hourly = {
                    "customer_support_whatsapp": 18,
                    "sales_setter_crm": 16,
                    "virtual_assistant_admin": 15,
                    "qa_testing": 20,
                    "power_bi_data": 25,
                    "python_automation_scraping": 30,
                    "web_dev": 25
                }
                suggested_rate = defaults_hourly.get(category, 18)

            suggested_bid = f"{curr_symbol}{suggested_rate} {currency} / hora"
            suggested_timeline = "Disponibilidad inmediata para turno asignado"
            return {
                "suggested_bid": suggested_bid,
                "suggested_timeline": suggested_timeline,
                "is_hourly": True
            }

        # Proyectos de precio fijo (Fixed Price)
        if numbers:
            min_v = min(numbers)
            max_v = max(numbers)

            # Proyectos de sistemas/chatbots de IA: nunca cotizar como script menor
            if category == "ai_chatbot_system":
                if max_v < 150:
                    suggested_bid = f"{curr_symbol}350 {currency}"
                    suggested_timeline = "4 a 6 días"
                else:
                    target = int(round(min_v + (max_v - min_v) * 0.5))
                    suggested_bid = f"{curr_symbol}{target} {currency}"
                    suggested_timeline = "1 a 2 semanas"
            elif max_v <= 60:
                # Proyectos pequeños puntuales
                target = int(max_v)
                suggested_bid = f"{curr_symbol}{target} {currency}"
                suggested_timeline = "24 a 48 horas"
            elif max_v <= 150:
                target = int(round(min_v + (max_v - min_v) * 0.55))
                suggested_bid = f"{curr_symbol}{target} {currency}"
                suggested_timeline = "48 horas"
            elif max_v <= 350:
                target = int(round(min_v + (max_v - min_v) * 0.5))
                suggested_bid = f"{curr_symbol}{target} {currency}"
                suggested_timeline = "3 a 4 días"
            else:
                target = int(round(min_v + (max_v - min_v) * 0.45))
                suggested_bid = f"{curr_symbol}{target} {currency}"
                suggested_timeline = "5 a 7 días"
        else:
            defaults_fixed = {
                "ai_chatbot_system": (f"{curr_symbol}650 {currency}", "1 a 2 semanas"),
                "python_automation_scraping": (f"{curr_symbol}90 {currency}", "48 horas"),
                "power_bi_data": (f"{curr_symbol}120 {currency}", "3 días"),
                "qa_testing": (f"{curr_symbol}85 {currency}", "48 horas"),
                "sql_database": (f"{curr_symbol}75 {currency}", "24 a 48 horas"),
                "web_dev": (f"{curr_symbol}140 {currency}", "3 a 4 días"),
                "customer_support_whatsapp": (f"{curr_symbol}300 {currency}", "Semanal / Mensual"),
                "sales_setter_crm": (f"{curr_symbol}350 {currency}", "Semanal / Mensual"),
                "virtual_assistant_admin": (f"{curr_symbol}280 {currency}", "Semanal / Mensual")
            }
            suggested_bid, suggested_timeline = defaults_fixed.get(category, (f"{curr_symbol}100 {currency}", "48 horas"))

        return {
            "suggested_bid": suggested_bid,
            "suggested_timeline": suggested_timeline,
            "is_hourly": False
        }

    def _call_external_llm(self, prompt: str) -> Optional[str]:
        """Intenta llamar a Gemini, Groq u OpenAI si hay clave configurada."""
        # 1. Intentar Gemini
        if self.gemini_client:
            try:
                resp = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                text = (resp.text or "").strip()
                if len(text) > 80:
                    return text
            except Exception as e:
                print(f"[ProposalGenerator] Gemini API error: {e}")

        # 2. Intentar Groq (Llama 3.3 70B gratuito y ultrarrápido)
        if self.groq_key:
            try:
                req_data = json.dumps({
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=req_data,
                    headers={
                        "Authorization": f"Bearer {self.groq_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "JobHunter-AI"
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_json = json.loads(response.read().decode())
                    text = res_json["choices"][0]["message"]["content"].strip()
                    if len(text) > 80:
                        return text
            except Exception as e:
                print(f"[ProposalGenerator] Groq API error: {e}")

        # 3. Intentar OpenAI
        if self.openai_key:
            try:
                req_data = json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=req_data,
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_json = json.loads(response.read().decode())
                    text = res_json["choices"][0]["message"]["content"].strip()
                    if len(text) > 80:
                        return text
            except Exception as e:
                print(f"[ProposalGenerator] OpenAI API error: {e}")

        return None

    def generate_proposal(self, title: str, description: str, client_name: str = "Estimado cliente", budget: str = "") -> Dict[str, Any]:
        """
        Genera una propuesta comercial persuasiva, profesional, con empatía y precisión técnica.
        Garantiza que la respuesta responda EXACTAMENTE a lo que el cliente solicita.
        """
        category = self.categorize_project(title, description)
        estimates = self.estimate_bid_and_time(budget, category, f"{title} {description}")
        suggested_bid = estimates["suggested_bid"]
        timeline = estimates["suggested_timeline"]
        is_hourly = estimates.get("is_hourly", False)
        github_url = "https://github.com/JackMBerrocal"

        # Detección de palabra clave obligatoria (ej: "escribe al inicio FIT")
        codeword_prefix = ""
        cw_match = re.search(r'(?:escribe|incluye|pon|palabra)\s+(?:al inicio|al principio|en tu propuesta|la palabra)?\s*[\“\"\'\‘]([a-zA-Z0-9_\-]+)[\”\"\'\’]', description, re.IGNORECASE)
        if cw_match:
            codeword_prefix = f"[{cw_match.group(1).upper()}]\n\n"

        # Prompt maestro para LLM si existe API key
        prompt = f"""
Eres un estratega de propuestas freelance senior asesorando a Jack Michael Berrocal.
Perfil del profesional:
- Egresado en Ingeniería de Sistemas (UTEL 2025).
- Especialización en Ciencia de Datos e Ingeniería de Software (Oracle Next Education - ONE / Alura Latam).
- Habilidades técnicas y operativas: Atención al cliente profesional por chat/WhatsApp (redacción impecable, trato formal de "usted", velocidad < 2 min), Power BI (DAX, dashboards), Python (Pandas, Playwright, APIs), QA Testing (Postman, test cases, bugs en Jira), SQL (PostgreSQL, MySQL).
- Idioma: Español nativo, ortografía y redacción impecable.
- Portafolio en GitHub: {github_url}

Datos de la oferta publicada por el cliente:
- Título: "{title}"
- Requerimiento completo: "{description}"
- Presupuesto cliente: "{budget}"
- Cotización sugerida calculada: "{suggested_bid}" (Es por hora: {is_hourly})
- Tiempo de entrega / Disponibilidad sugerida: "{timeline}"
- Categoría detectada: "{category}"

INSTRUCCIONES CRÍTICAS DE REDACCIÓN:
1. DISTINCIÓN FUNDAMENTAL DE LA NECESIDAD:
   - Si el cliente busca una PERSONA para ATENDER MENSAJES (WhatsApp, soporte, chat, ventas, asistencia):
     NUNCA ofrezcas desarrollar un script de Python, web scraper ni BeautifulSoup. 
     En su lugar, demuestra empatía, compromiso con su turno, tiempo de respuesta rápido (< 2 min), uso formal de "usted", manejo de WhatsApp Web / atajos de teclado / etiquetas, y entrega de reportes diarios de incidencias y chats.
   - Si el cliente busca CONSTRUIR UN CHATBOT CON IA O SISTEMA AUTOMATIZADO:
     Propón una arquitectura seria de software (NLP/LLM, flujos conversacionales, API de WhatsApp/Meta, base de conocimiento RAG, control de errores) con presupuesto profesional acorde a software empresarial.
   - Si busca POWER BI / DATOS:
     Enfócate en Power Query, modelo relacional en estrella, DAX y visualización de negocio.
   - Si busca WEB SCRAPING / EXTRACCIÓN:
     Enfócate en Playwright/Requests, Pandas y Excel/BD.
   - Si busca QA TESTING:
     Enfócate en matriz de casos de prueba, Postman y reporte de bugs en Jira.

2. ESTRUCTURA DE LA PROPUESTA (100% en español, concisa, sin relleno):
   - Saludo cordial y confirmación inmediata en 2 líneas de que leíste y entendiste su requerimiento exacto.
   - Plan de trabajo concreto en 3 puntos claros respondiendo a lo que pidió.
   - Tarifa propuesta: Mención clara de la cotización ({suggested_bid}) y tiempo/disponibilidad ({timeline}).
   - Llamado a la acción invitando a conversar por chat para coordinar los detalles.

Responde ÚNICAMENTE con el texto final de la propuesta listo para enviar al cliente.
"""

        # Intentar con modelo de IA en línea
        llm_text = self._call_external_llm(prompt)
        if llm_text:
            return {
                "category": category,
                "suggested_bid": suggested_bid,
                "suggested_timeline": timeline,
                "is_hourly": is_hourly,
                "proposal_text": codeword_prefix + llm_text
            }

        # --- MOTOR DE RAZONAMIENTO COGNITIVO SIN CONEXIÓN A LLM ---
        # Si no hay API key configurada, el motor genera propuestas expertas contextuales:

        # 1. ATENCIÓN AL CLIENTE POR WHATSAPP / CHAT SUPPORT
        if category == "customer_support_whatsapp":
            proposal_text = f"""Hola, leí con atención tu requerimiento para la atención de clientes vía WhatsApp.

Cuento con disponibilidad inmediata para cubrir tu turno cumpliendo estrictamente con el tiempo de respuesta menor a dos minutos, tratamiento formal de "usted" y una ortografía y redacción impecable en español nativo:

1. 💬 Atención Ágil y Empática: Aplicación rigurosa de tus guías y políticas de empresa para responder dudas frecuentes y seguimiento de pedidos, utilizando WhatsApp Web con atajos de teclado, etiquetas y respuestas rápidas para máxima fluidez.
2. 📊 Registro y Control Diario: Al finalizar cada jornada, te entregaré la bitácora consolidada de chats atendidos y el informe de incidencias clasificadas para escalamiento oportuno a ventas o soporte técnico.
3. 🛡️ Compromiso y Confiabilidad: Como profesional en Ingeniería de Sistemas, aporto alta organización, método y seriedad en el manejo de la información y la comunicación con tus clientes.

Cuento con una tarifa competitiva de {suggested_bid} acorde a tu rango presupuestario y puedo realizar una prueba breve para que evalúes mi velocidad y tono de atención.

¿Podemos coordinar por el chat los horarios de turno y comenzar hoy mismo?"""

        # 2. SETTER DE VENTAS / PROSPECCIÓN COMERCIAL / FITNESS
        elif category == "sales_setter_crm":
            proposal_text = f"""Hola, revisé tu publicación para el rol de Setter de Ventas para Asesoría Fitness.

Cuento con excelente comunicación asertiva, disciplina y enfoque a resultados para convertir prospectos interesados en llamadas agendadas de alto valor:

1. 🎯 Contacto Rápido & Cualificación: Respuesta inmediata a los leads entrantes, aplicando preguntas estratégicas para identificar sus metas de entrenamiento/nutrición, nivel de compromiso y capacidad de inversión.
2. 💬 Manejo de Objeciones & Agendamiento: Tratamiento persuasivo y empático de dudas comunes para asegurar la cita en el calendario del equipo de ventas, manteniendo un tono profesional y cercano.
3. 📈 Seguimiento Riguroso & CRM: Registro minucioso de cada interacción, estatus del prospecto y métricas de conversión diarias para no dejar escapar ninguna oportunidad.

Mi tarifa propuesta es de {suggested_bid}, abierta a esquemas con incentivos por llamada agendada o venta concretada. Cuento con disponibilidad inmediata para familiarizarme con tu protocolo de ventas.

¿Conversamos por chat para revisar tu flujo de captación e iniciar?"""

        # 3. ASISTENCIA VIRTUAL Y GESTIÓN ADMINISTRATIVA
        elif category == "virtual_assistant_admin":
            proposal_text = f"""Hola, revisé los detalles de tu solicitud para asistencia virtual y soporte operativo.

Como profesional en Ingeniería de Sistemas, ofrezco un perfil organizado, metódico y confiable para gestionar tus tareas diarias con total autonomía:

1. 📋 Organización y Gestión: Administración rigurosa de correos, agenda, seguimiento de pendientes y comunicación formal con clientes o proveedores en español neutro e impecable.
2. 🗄️ Documentación y Datos: Manejo avanzado de herramientas en la nube (Google Workspace, Excel/Sheets, Notion), asegurando datos actualizados y libres de errores.
3. ⚡ Reportes Diarios: Comunicación constante del avance de actividades y entregables al cierre de cada jornada.

Mi tarifa sugerida es de {suggested_bid} con {timeline}. Cuento con alta confidencialidad y disposición para adaptarme a tus procesos internos.

¿Podemos coordinar por chat las primeras prioridades de trabajo?"""

        # 4. DESARROLLO DE CHATBOT CON IA / SISTEMA AUTOMATIZADO
        elif category == "ai_chatbot_system":
            proposal_text = f"""Hola, leí con atención tu proyecto para la implementación de un sistema de Chatbot con Inteligencia Artificial.

Como Ingeniero de Sistemas especializado en Ciencia de Datos y Software (Oracle Next Education), puedo diseñar una arquitectura conversacional robusta, inteligente y escalable:

1. 🧠 Inteligencia & Flujos Conversacionales: Configuración de modelos LLM con prompts de sistema estructurados y base de conocimiento (RAG con tus FAQs, productos y políticas) para respuestas precisas y naturales sin alucinaciones.
2. 🔗 Integración de Canales & APIs: Conexión segura mediante webhooks con la API oficial de WhatsApp (Meta Cloud API / Twilio), Telegram o tu web, integrando tu CRM o base de datos.
3. 🔀 Escalado a Agente Humano & Auditoría: Detección inteligente de intenciones complejas para transferir el chat a un asesor humano, con panel de registro y telemetría de conversaciones.

Cuento con proyectos de automatización y consumo de modelos de lenguaje publicados en mi GitHub ({github_url}).
Para este alcance, propongo una cotización de {suggested_bid} con un tiempo de entrega de {timeline} que incluye pruebas exhaustivas y garantía de funcionamiento.

¿Podemos coordinar una llamada o chat técnico para definir los casos de uso principales?"""

        # 5. POWER BI & ANALÍTICA DE DATOS
        elif category == "power_bi_data":
            proposal_text = f"""Hola, revisé tu proyecto sobre "{title}".

Como Ingeniero de Sistemas especializado en Data Science por Oracle Next Education (ONE / Alura), puedo estructurar este dashboard ejecutivo, interactivo y orientado a la toma de decisiones:

1. 🔄 Modelado & ETL: Extracción, limpieza y normalización de tus fuentes de datos mediante Power Query, eliminando redundancias y garantizando integridad.
2. 📊 Métricas & Fórmulas DAX: Creación de modelo relacional en estrella con medidas DAX avanzadas para monitorear tus KPIs clave (rendimiento, ventas, márgenes o tendencias).
3. 🎨 Visualización Ejecutiva: Diseño de interfaz intuitiva con segmentadores dinámicos, filtros temporales y diseño responsivo para gerencia.

Cuento con proyectos prácticos de analítica y bases de datos en mi repositorio ({github_url}).
Puedo entregarte el archivo .PBIX completo y funcional en {timeline} por {suggested_bid}.

Quedo a tu disposición por el chat para revisar la estructura de tus datos y empezar hoy mismo."""

        # 6. WEB SCRAPING & AUTOMATIZACIÓN PYTHON (SOLO CUANDO PIDEN SCRAPING)
        elif category == "python_automation_scraping":
            proposal_text = f"""Hola, leí con atención tu requerimiento sobre "{title}".

Puedo desarrollar el script de extracción y automatización de forma rápida, robusta y con código limpio:

1. ⚙️ Extracción Confiable: Desarrollo del script en Python (Playwright / Requests / BeautifulSoup) diseñado con control de errores, reintentos y respeto de estructuras web.
2. 🗄️ Limpieza & Formato: Procesamiento y normalización de los datos con Pandas para entregártelos exactamente en el formato requerido (Excel estructurado, CSV o base de datos relacional).
3. 📦 Entregable Listo para Usar: Código fuente documentado y un ejecutable o manual sencillo de 1 paso para que puedas volver a correr la extracción cuando lo desees.

Cuento con proyectos similares de automatización de datos publicados en mi GitHub ({github_url}).
Puedo entregarte la solución validada en {timeline} por una tarifa de {suggested_bid}.

¿Coordinamos los detalles específicos de los campos a extraer por el chat?"""

        # 7. QA TESTING & PRUEBAS DE SOFTWARE
        elif category == "qa_testing":
            proposal_text = f"""Hola, leí con detenimiento tu solicitud para "{title}".

Puedo realizar el aseguramiento de calidad y pruebas exhaustivas para garantizar la estabilidad y experiencia de usuario de tu software:

1. 🧪 Diseño de Casos de Prueba: Elaboración de matriz de cobertura con escenarios funcionales positivos, negativos y casos borde (edge cases).
2. 🚀 Pruebas Funcionales & APIs: Validación de flujos de usuario completos y verificación de endpoints con Postman (status codes, payloads JSON y tiempos de respuesta).
3. 📋 Reporte Detallado de Bugs: Documentación estructurada de cada incidencia detectada (pasos exactos de reproducción, evidencias/capturas, severidad y comportamiento esperado).

Cuento con formación especializada en QA y testing de software con proyectos comprobables en GitHub ({github_url}).
Puedo completar la ronda de pruebas y entregarte el informe consolidado en {timeline} por {suggested_bid}.

¿Me compartes el acceso o enlace para comenzar la evaluación preliminar?"""

        # 8. SQL & BASES DE DATOS
        elif category == "sql_database":
            proposal_text = f"""Hola, revisé tu requerimiento sobre "{title}".

Puedo ayudarte a estructurar, optimizar o consultar tu base de datos con máxima eficiencia:

1. 🔍 Diagnóstico & Modelado: Análisis de tablas, claves foráneas y normalización relacional (PostgreSQL, MySQL o SQLite).
2. ⚡ Consultas Optimizadas: Redacción de consultas SQL con JOINs, agrupaciones, subconsultas e índices para tiempos de respuesta mínimos.
3. 📄 Entregable Documentado: Scripts SQL probados y listos para integrarse en tu sistema o reportes.

Cuento con experiencia en administración relacional en GitHub ({github_url}).
Puedo tener tu solución lista en {timeline} por {suggested_bid}.

¿Coordinamos por chat las tablas y consultas que necesitas?"""

        # 9. DESARROLLO WEB / LANDING PAGES
        elif category == "web_dev":
            proposal_text = f"""Hola, revisé los requerimientos de tu proyecto web para "{title}".

Puedo ayudarte a implementar esta solución con código limpio, diseño moderno y excelente rendimiento:

1. 🎨 Maquetación & Responsividad: Interfaz atractiva y fluida, optimizada para dispositivos móviles y escritorio.
2. ⚡ Lógica & Integraciones: Desarrollo modular de funcionalidades con JavaScript/React y consumo de APIs según tus especificaciones.
3. 🚀 Despliegue & Entrega: Código fuente ordenado, documentado y listo para producción.

Cuento con proyectos web publicados en mi perfil de GitHub ({github_url}).
Puedo entregarte el proyecto terminado en {timeline} por {suggested_bid}.

Conversemos por el chat para revisar especificaciones y comenzar de inmediato."""

        # 10. GENERAL / SOPORTE TI
        else:
            proposal_text = f"""Hola, revisé con atención tu proyecto para "{title}".

Como Ingeniero de Sistemas, pongo a tu disposición mi formación técnica, seriedad y rapidez para resolver tu requerimiento:

1. 🛠️ Análisis & Diagnóstico: Entendimiento minucioso de la necesidad técnica para aplicar la solución más directa y eficiente.
2. ⚙️ Ejecución Metódica: Aplicación de buenas prácticas profesionales garantizando calidad y cumplimiento de tiempos.
3. 📋 Entrega & Soporte: Entrega documentada y acompañamiento para asegurar que todo funcione a tu entera satisfacción.

Tarifa propuesta: {suggested_bid} con {timeline}.
Cuento con proyectos comprobables en mi repositorio de GitHub ({github_url}).

Quedo atento en el chat para revisar los detalles e iniciar de inmediato."""

        return {
            "category": category,
            "suggested_bid": suggested_bid,
            "suggested_timeline": timeline,
            "is_hourly": is_hourly,
            "proposal_text": codeword_prefix + proposal_text
        }
