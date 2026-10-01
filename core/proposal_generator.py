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
    - Servicios y Contratos por Horas (Atención WhatsApp, Soporte, Community Manager, Setter, Asistencia)
    - Proyectos por Trabajo Realizado / Precio Fijo (Chatbots con IA, Web, Power BI, QA, SQL, Scraping)
    Aplica tarifas reales, responde detalle a detalle al brief del cliente,
    formula preguntas estratégicas para ganar la asignación y NUNCA deriva a llamadas externas.
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
        Prioriza la detección exacta evitando colisiones de palabras clave genéricas.
        """
        text = f"{title} {description} {' '.join(skills or [])}".lower()
        t_low = title.lower()

        # 1. Asistencia Virtual, Gestión de Agenda & Operaciones
        if any(w in t_low for w in ["asistente virtual", "virtual assistant", "asistente administrativo", "secretaria", "recepcionista virtual"]) or any(w in text for w in [
            "asistente virtual", "virtual assistant", "asistente administrativo", "gestión de agenda", "gestion de agenda",
            "agendar citas", "gestión de citas", "gestion de citas", "gestion de correos", "data entry", "transcripción", "agenda digital"
        ]):
            return "virtual_assistant_admin"

        # 2. Crecimiento de Redes Sociales, Instagram, TikTok, Reels & Marketing Digital
        if any(w in t_low for w in ["instagram", "tiktok", "reels", "redes sociales", "community manager", "crecimiento ig", "crecimiento tiktok"]) or any(w in text for w in [
            "tiktok", "instagram", "reels", "community manager", "redes sociales", "crecimiento ig", "crecimiento tiktok",
            "parrilla de contenido", "estrategia de contenido", "seguidores reales", "engagement", "creador de contenido",
            "videos de tiktok", "posts para instagram", "growth marketing", "social media", "crecer en instagram"
        ]):
            return "social_media_growth"

        # 3. E-Commerce & Tiendas Virtuales (Shopify, WooCommerce, Catálogo)
        if any(w in text for w in [
            "shopify", "woocommerce", "tienda online", "tienda virtual", "subir productos", "catalogo de productos",
            "mercado libre", "amazon fba", "dropshipping", "e-commerce", "ecommerce", "tiendanube"
        ]):
            return "ecommerce_stores"

        # 4. Setter de Ventas & Agendamiento Comercial & Asesorías Fitness
        if any(w in text for w in [
            "setter", "asesoría fitness", "asesoria fitness", "llamadas de venta", "appointment setter",
            "agendar llamadas", "agendamiento de llamadas", "prospección", "prospeccion",
            "cold caller", "closer", "cerrador", "lead qualification", "cerrar ventas"
        ]):
            return "sales_setter_crm"

        # 5. Sistemas / Chatbots con Inteligencia Artificial & Bots de Software (Desarrollo técnico)
        if any(w in text for w in [
            "bot faq", "asistente automático", "asistente automatico", "crear chatbot",
            "desarrollo de bot", "desarrollar chatbot", "bot con ia", "chatbot con inteligencia",
            "sistema automatizado con ia", "bot de whatsapp", "bot whatsapp", "flujo manychat",
            "agente con ia", "agente ia", "bot inteligente", "automatizar respuestas con ia",
            "chatbot gpt", "chatbot", "typebot", "voicebot", "el bot debe"
        ]) or (("bot " in text or " bot" in text) and "responder mensajes" not in t_low and "atención al cliente" not in t_low):
            return "ai_chatbot_system"

        # 6. Soporte & Atención Humana por Chat / WhatsApp (Servicio Humano)
        if any(w in t_low for w in ["whatsapp", "responder mensajes", "atención al cliente", "atencion al cliente", "chat"]) or any(w in text for w in [
            "responder mensajes", "atención al cliente", "atencion al cliente",
            "customer service", "customer support", "soporte por chat", "chat support",
            "contestar mensajes", "atender mensajes", "chat de atención", "moderador de chat",
            "atención de consultas"
        ]):
            return "customer_support_whatsapp"

        # 7. Power BI & Analítica de Datos (Excluye menciones casuales de 'kpi' o 'datos' en marketing)
        if any(w in text for w in [
            "power bi", "powerbi", "dax", "power query", "business intelligence",
            "tablero en power bi", "reporte en power bi", "modelo relacional", "pbix", "analista de bi"
        ]) or ("dashboard" in text and any(w in text for w in ["dax", "bi", "etl", "power", "excel avanzado"])):
            return "power_bi_data"

        # 8. Web Scraping & Extracción con Python (Solo scripts y crawling)
        if any(w in text for w in [
            "scraping", "scraper", "crawling", "extraer datos", "extracción de datos",
            "extraccion de datos", "script python", "script en python", "playwright",
            "selenium", "beautifulsoup", "automatizar excel con python"
        ]):
            return "python_automation_scraping"

        # 9. QA Testing & Pruebas de Software
        if any(w in text for w in [
            "qa", "testing", "tester", "pruebas funcionales", "postman", "casos de prueba",
            "test cases", "reporte de bugs", "control de calidad", "smoke testing", "pruebas de regresion"
        ]):
            return "qa_testing"

        # 10. SQL & Bases de Datos
        if any(w in text for w in [
            "sql", "postgres", "postgresql", "mysql", "queries sql",
            "procedimientos almacenados", "optimización de consultas", "stored procedure", "consultas sql"
        ]):
            return "sql_database"

        # 11. Desarrollo Web & Frontend
        if any(w in text for w in [
            "wordpress", "landing page", "react", "html", "css", "javascript",
            "desarrollo web", "página web", "pagina web", "frontend", "sitio web", "web developer"
        ]):
            return "web_dev"

        # 12. Soporte TI / Helpdesk
        if any(w in text for w in [
            "soporte ti", "soporte técnico", "soporte tecnico", "helpdesk", "active directory", "anydesk"
        ]):
            return "it_support"

        return "general_tech"

    def estimate_bid_and_time(self, budget_str: str, category: str, full_text: str = "") -> Dict[str, Any]:
        """
        Calcula el presupuesto óptimo y el tiempo/disponibilidad.
        Detecta si es por hora (Hourly) o precio fijo (Fixed), respetando la moneda.
        """
        combined = f"{budget_str} {full_text}".lower()
        is_hourly = any(h in combined for h in ["hour", "hora", "hr", "/h", "hourly", "/ hora", "/ hour", "por hora", "por horas", "por turno"])

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
                    "sales_setter_crm": 18,
                    "social_media_growth": 20,
                    "virtual_assistant_admin": 15,
                    "qa_testing": 20,
                    "power_bi_data": 25,
                    "python_automation_scraping": 30,
                    "web_dev": 25,
                    "ecommerce_stores": 18
                }
                suggested_rate = defaults_hourly.get(category, 18)

            suggested_bid = f"{curr_symbol}{suggested_rate} {currency} / hora"
            suggested_timeline = "Disponibilidad inmediata: 4 a 6 horas diarias (o turno asignado)"
            return {
                "suggested_bid": suggested_bid,
                "suggested_timeline": suggested_timeline,
                "is_hourly": True,
                "currency": currency
            }

        # Proyectos de precio fijo (Fixed Price / Trabajo realizado)
        if numbers:
            min_v = min(numbers)
            max_v = max(numbers)

            if category == "ai_chatbot_system":
                if max_v < 150:
                    suggested_bid = f"{curr_symbol}350 {currency}"
                    suggested_timeline = "4 a 6 días"
                else:
                    target = int(round(min_v + (max_v - min_v) * 0.5))
                    suggested_bid = f"{curr_symbol}{target} {currency}"
                    suggested_timeline = "1 a 2 semanas"
            elif max_v <= 60:
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
                "social_media_growth": (f"{curr_symbol}160 {currency}", "Entregables semanales / mensual"),
                "ecommerce_stores": (f"{curr_symbol}180 {currency}", "3 a 5 días"),
                "python_automation_scraping": (f"{curr_symbol}90 {currency}", "48 horas"),
                "power_bi_data": (f"{curr_symbol}120 {currency}", "3 días"),
                "qa_testing": (f"{curr_symbol}85 {currency}", "48 horas"),
                "sql_database": (f"{curr_symbol}75 {currency}", "24 a 48 horas"),
                "web_dev": (f"{curr_symbol}140 {currency}", "3 a 4 días"),
                "customer_support_whatsapp": (f"{curr_symbol}280 {currency}", "Turno mensual"),
                "sales_setter_crm": (f"{curr_symbol}320 {currency}", "Semanal / Mensual"),
                "virtual_assistant_admin": (f"{curr_symbol}250 {currency}", "Semanal / Mensual")
            }
            suggested_bid, suggested_timeline = defaults_fixed.get(category, (f"{curr_symbol}100 {currency}", "48 horas"))

        return {
            "suggested_bid": suggested_bid,
            "suggested_timeline": suggested_timeline,
            "is_hourly": False,
            "currency": currency
        }

    def _call_external_llm(self, prompt: str) -> Optional[str]:
        """Intenta llamar a Gemini, Groq u OpenAI si hay clave configurada."""
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

        return None

    def generate_proposal(self, title: str, description: str, client_name: str = "Estimado cliente", budget: str = "") -> Dict[str, Any]:
        """
        Genera una propuesta comercial persuasiva, profesional, con empatía y precisión técnica.
        Garantiza que la respuesta responda EXACTAMENTE a lo que el cliente solicita:
        1. Reconocimiento específico del objetivo del cliente (sin clichés).
        2. Plan de trabajo técnico detalle a detalle respondiendo a cada requerimiento.
        3. 2 a 3 preguntas estratégicas clave que diferencian la propuesta y enganchan al cliente.
        4. Modalidad clara: Por Horas (Hourly) o Por Trabajo Realizado (Fixed).
        5. Cierre 100% por chat de la plataforma (CERO llamadas, CERO WhatsApp).
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
        modality_instruction = (
            "MODALIDAD: POR HORAS (HOURLY). Especifica disponibilidad de horas diarias, compromiso de turnos y reporte diario de actividades."
            if is_hourly else
            "MODALIDAD: POR TRABAJO REALIZADO (PRECIO FIJO). Especifica entregables cerrados, cronograma y ronda de ajustes incluida."
        )

        prompt = f"""
Eres un estratega senior de propuestas freelance redactando en nombre de Jack Michael Berrocal.
Perfil profesional de Jack:
- Egresado de Ingeniería de Sistemas (UTEL 2025). Especializado en Software, IA y Ciencia de Datos (Oracle Next Education - ONE / Alura).
- Habilidades: Gestión de Redes Sociales (IG/TikTok), Atención al Cliente WhatsApp/Chat (redacción impecable, trato formal de "usted", velocidad < 2 min), Chatbots de IA, Power BI (DAX, tableros), Python (Playwright, scraping, APIs), QA Testing (Postman, test cases, bugs), SQL (PostgreSQL, MySQL), Desarrollo Web (React, WordPress).
- Portafolio comprobable: {github_url}

Datos del proyecto del cliente:
- Título: "{title}"
- Descripción completa: "{description}"
- Presupuesto cliente: "{budget}"
- Cotización sugerida: "{suggested_bid}" ({modality_instruction})
- Tiempo estimado / Disponibilidad: "{timeline}"
- Categoría detectada: "{category}"

REGLAS DE ORO DE REDACCIÓN (¡ESTRICTAS!):
1. LEE DETALLE A DETALLE: Responde específicamente a los puntos, herramientas y metas que el cliente menciona en su descripción. PROHIBIDO dar respuestas genéricas o hablar de temas no solicitados (ej: NUNCA hables de PowerBI si pide Instagram/TikTok).
2. PREGUNTAS ESTRATÉGICAS (OBLIGATORIAS): Incluye exactamente 2 a 3 preguntas técnicas y de negocio inteligentes sobre su proyecto para demostrar dominio y provocar que responda en el chat.
3. MODALIDAD DIFERENCIADA: Si es por horas, resalta disponibilidad horaria y método de control; si es por proyecto, resalta entrega llave en mano y garantía de ajustes.
4. PROHIBIDO DERIVAR A LLAMADAS O CONTACTOS EXTERNOS: Está terminantemente prohibido sugerir "llamadas", "Zoom", "videollamadas" o "WhatsApp". Todo debe ofrecerse y resolverse DIRECTAMENTE por el chat de la plataforma.
5. LONGITUD ÓPTIMA: Entre 3 y 4 párrafos concisos y persuasivos con formato limpio y viñetas con emojis profesionales.

Responde ÚNICAMENTE con el texto de la propuesta listo para enviar.
"""

        llm_text = self._call_external_llm(prompt)
        if llm_text:
            return {
                "category": category,
                "suggested_bid": suggested_bid,
                "suggested_timeline": timeline,
                "is_hourly": is_hourly,
                "proposal_text": codeword_prefix + llm_text
            }

        # --- MOTOR COGNITIVO DETERMINÍSTICO AVANZADO ---
        proposal_text = self._generate_cognitive_proposal(
            title=title,
            description=description,
            category=category,
            suggested_bid=suggested_bid,
            timeline=timeline,
            is_hourly=is_hourly,
            github_url=github_url
        )

        return {
            "category": category,
            "suggested_bid": suggested_bid,
            "suggested_timeline": timeline,
            "is_hourly": is_hourly,
            "proposal_text": codeword_prefix + proposal_text
        }

    def _generate_cognitive_proposal(self, title: str, description: str, category: str, suggested_bid: str, timeline: str, is_hourly: bool, github_url: str) -> str:
        """
        Generador cognitivo de propuestas de nivel agencia que analiza el requerimiento
        detalle a detalle, formula preguntas inteligentes y diferencia por horas vs por proyecto.
        """
        # Formato de modalidad comercial
        if is_hourly:
            commercial_block = f"""💼 Modalidad de Trabajo & Tarifa:
Propongo una tarifa de {suggested_bid} con {timeline}. Cuento con registro transparente de actividades, bitácora diaria de tareas cumplidas y total adaptación a tu franja horaria."""
        else:
            commercial_block = f"""📦 Entregable Llave en Mano & Cotización:
El costo cerrado para este proyecto completo es de {suggested_bid} en un plazo de {timeline}, incluyendo la entrega de archivos fuente, puesta en marcha y una ronda de ajustes posteriores para garantizar que quede exactamente como necesitas."""

        closing_block = "Quedo disponible en este momento por el chat de la plataforma para resolver cualquier detalle sobre estos puntos y arrancar en cuanto me des luz verde. 🚀"

        # 1. CRECIMIENTO DE REDES SOCIALES, INSTAGRAM, TIKTOK & REELS
        if category == "social_media_growth":
            return f"""Hola, revisé minuciosamente tu proyecto para "{title}".

Entiendo perfectamente que el objetivo central es elevar el alcance, engagement y flujo de clientes potenciales de forma coordinada en Instagram y TikTok, evitando acciones improvisadas y centrándonos en métricas reales de conversión:

1. 🔍 Auditoría de Cuentas & Definición de KPIs: Análisis inicial de la situación actual de tus perfiles, competidores directos y establecimiento de metas claras de retención y tráfico hacia tus canales de venta.
2. 📱 Calendario de Contenidos Nativos (Reels & TikToks): Estructuración de parrilla con ganchos (hooks) potentes en los primeros 3 segundos, estructura de valor y llamados a la acción (CTA) orientados al público de cada plataforma.
3. 📈 Optimización Basada en Analítica Semanal: Monitoreo constante de métricas para iterar sobre los formatos que mejor convierten y entrega de informe periódico de resultados transparentes.

💡 Preguntas clave para iniciar con precisión:
• ¿Cuál es el nicho o producto principal de la marca y a qué perfil de cliente estamos apuntando?
• ¿Cuentan actualmente con material audiovisual grabado para edición y adaptación, o partiremos desde la conceptualización de guiones desde cero?
• ¿Tienen cuenta publicitaria configurada en Meta Ads para complementar con pauta, o la estrategia inicial será 100% de crecimiento orgánico?

{commercial_block}

{closing_block}"""

        # 2. E-COMMERCE & TIENDAS VIRTUALES (SHOPIFY / WOOCOMMERCE)
        elif category == "ecommerce_stores":
            return f"""Hola, leí con atención los requerimientos de tu proyecto para "{title}".

Puedo encargarme de la configuración, carga de productos y optimización de tu tienda virtual para que la experiencia de compra sea rápida, segura y orientada a la conversión:

1. 🛍️ Estructuración de Catálogo & Productos: Carga detallada de artículos con títulos optimizados para búsqueda, variantes (tallas, colores), descripciones atractivas y control de inventario.
2. 💳 Pasarelas de Pago & Envíos: Configuración de métodos de cobro locales e internacionales y cálculo automático de tarifas de envío según tus zonas de despacho.
3. 📱 Optimización Móvil & Velocidad: Verificación de que el flujo de checkout funcione sin fricciones desde dispositivos móviles.

💡 Preguntas clave para tu tienda:
• ¿En qué plataforma está construida tu tienda (Shopify, WooCommerce, Tiendanube u otra)?
• ¿Tienes ya la lista de productos organizada con imágenes y precios, o requieres apoyo para la preparación de los archivos base?

{commercial_block}

{closing_block}"""

        # 3. ATENCIÓN AL CLIENTE POR WHATSAPP / CHAT SUPPORT
        elif category == "customer_support_whatsapp":
            return f"""Hola, leí con atención tu requerimiento para la atención y soporte de clientes vía WhatsApp.

Cuento con disponibilidad inmediata para cubrir tu turno cumpliendo estrictamente con un tiempo de respuesta menor a dos minutos, tratamiento formal de "usted" y una ortografía y redacción impecable en español nativo:

1. 💬 Atención Ágil y Empática: Aplicación rigurosa de tus guías y políticas de empresa para resolver consultas frecuentes, seguimiento de pedidos y resolución de dudas con calidez y profesionalismo.
2. ⌨️ Eficiencia con WhatsApp Web: Uso intensivo de atajos de teclado, etiquetas de organización y respuestas rápidas para gestionar múltiples conversaciones simultáneas sin descuidar el detalle.
3. 📊 Bitácora Diaria de Incidencias: Registro consolidado de chats atendidos y reporte de casos críticos al cierre de cada jornada para escalamiento oportuno.

💡 Preguntas clave para coordinar tu atención:
• ¿Cuál es el volumen promedio aproximado de conversaciones que se reciben por turno?
• ¿Cuentas con un documento de preguntas frecuentes (FAQs), catálogo o guía de respuestas para comenzar la inducción de inmediato?

{commercial_block}

{closing_block}"""

        # 4. CHATBOTS CON INTELIGENCIA ARTIFICIAL & AUTOMATIZACIONES
        elif category == "ai_chatbot_system":
            return f"""Hola, leí con detenimiento tu proyecto para la implementación de un sistema de Chatbot con Inteligencia Artificial.

Como Ingeniero de Sistemas especializado en Software y Ciencia de Datos (Oracle Next Education), puedo diseñar una arquitectura conversacional robusta, confiable y libre de alucinaciones:

1. 🧠 Base de Conocimientos & RAG: Integración de modelos LLM con tus catálogos, PDFs y políticas para que el bot responda con precisión matemática y lenguaje natural a las dudas de tus clientes.
2. 🔗 Conexión de Canales Oficiales: Integración mediante webhooks seguros con la API oficial de WhatsApp (Meta Cloud API / Twilio), Telegram o Chat Web, sincronizando datos con tu base de datos o CRM.
3. 🔀 Derivación Inteligente & Auditoría: Detección automática de intenciones complejas para transferir el chat a un asesor humano cuando sea necesario, guardando telemetría de cada mensaje.

Portafolio de proyectos de automatización e IA disponible en mi GitHub ({github_url}).

💡 Preguntas clave sobre la arquitectura:
• ¿El bot se integrará con la API oficial de WhatsApp Cloud o sobre un chat web integrado en tu sistema?
• ¿Cuentan con un archivo de preguntas frecuentes o catálogo estructurado para entrenar la base de conocimiento?

{commercial_block}

{closing_block}"""

        # 5. SETTER DE VENTAS & PROSPECCIÓN COMERCIAL
        elif category == "sales_setter_crm":
            return f"""Hola, revisé tu publicación para el rol de Setter de Ventas y Prospección Comercial.

Cuento con comunicación asertiva, disciplina metódica y enfoque orientado a resultados para convertir prospectos interesados en reuniones agendadas de alto valor:

1. 🎯 Contacto Rápido & Cualificación: Respuesta inmediata a prospectos entrantes aplicando preguntas estratégicas para validar interés, necesidad y capacidad de decisión.
2. 💬 Tratamiento de Objeciones & Agendamiento: Manejo empático de dudas habituales para asegurar la cita en el calendario del equipo de ventas, manteniendo siempre un tono profesional.
3. 📈 Control Riguroso en CRM: Registro diario del estatus de cada contacto en tu CRM o herramienta de seguimiento para garantizar cero pérdidas de oportunidades.

💡 Preguntas clave para el flujo de ventas:
• ¿De qué canales provienen los prospectos principales (Meta Ads, orgánico en redes sociales o prospección en frío)?
• ¿Qué plataforma utilizan actualmente para agendar citas (Calendly, HubSpot, Google Calendar)?

{commercial_block}

{closing_block}"""

        # 6. ASISTENCIA VIRTUAL & GESTIÓN ADMINISTRATIVA
        elif category == "virtual_assistant_admin":
            return f"""Hola, revisé los detalles de tu solicitud para asistencia virtual y soporte administrativo.

Como profesional en Ingeniería de Sistemas, ofrezco un perfil organizado, metódico y confiable para gestionar tus tareas operativas con total autonomía:

1. 📋 Organización y Gestión Diaria: Administración de correos, agenda, seguimiento de pendientes y comunicación formal con clientes o proveedores en español neutro impecable.
2. 🗄️ Control de Documentación y Datos: Manejo avanzado de Google Workspace, Excel/Sheets y Notion, manteniendo reportes limpios, actualizados y estructurados.
3. ⚡ Reportes de Cierre de Jornada: Entrega diaria del estado de tareas completadas y asuntos pendientes para tu completa tranquilidad.

💡 Preguntas clave para estructurar el trabajo:
• ¿Cuáles serán las tareas y herramientas de mayor prioridad en los primeros días de trabajo?
• ¿La posición requiere atención en horarios fijos continuos o entrega por objetivos diarios?

{commercial_block}

{closing_block}"""

        # 7. POWER BI & ANALÍTICA DE DATOS
        elif category == "power_bi_data":
            return f"""Hola, revisé tu proyecto sobre "{title}".

Como Ingeniero de Sistemas especializado en Ciencia de Datos por Oracle Next Education (ONE / Alura), puedo diseñar un dashboard ejecutivo, interactivo y orientado a la toma de decisiones:

1. 🔄 Modelado & ETL: Extracción, limpieza y normalización de tus fuentes de datos mediante Power Query, garantizando integridad y eliminando redundancias.
2. 📊 Métricas & Fórmulas DAX: Creación de modelo relacional en estrella con medidas DAX avanzadas para monitorear tus indicadores clave de rendimiento (ventas, márgenes, cohortes o tendencias).
3. 🎨 Visualización Ejecutiva de Alto Impacto: Diseño de interfaz intuitiva con segmentadores dinámicos, filtros temporales y layout responsivo para la gerencia.

Cuento con proyectos prácticos de analítica y bases de datos en mi repositorio ({github_url}).

💡 Preguntas clave sobre tus datos:
• ¿En qué formato se encuentran las fuentes de datos originales (Excel, Google Sheets, base de datos SQL o ERP)?
• ¿Cuáles son los 3 indicadores o KPIs más críticos que la dirección necesita visualizar en este reporte?

{commercial_block}

{closing_block}"""

        # 8. WEB SCRAPING & AUTOMATIZACIÓN PYTHON
        elif category == "python_automation_scraping":
            return f"""Hola, leí con atención tu requerimiento técnico para "{title}".

Puedo desarrollar el script de extracción y automatización en Python de forma rápida, robusta y con código limpio:

1. ⚙️ Extracción Confiable & Evasión: Desarrollo modular con Playwright / Requests / BeautifulSoup, diseñado con reintentos automáticos, manejo de errores y respeto de estructuras web.
2. 🗄️ Procesamiento & Limpieza con Pandas: Normalización rigurosa de los campos extraídos para entregártelos exactamente en el formato requerido (Excel estructurado, CSV o base de datos relacional).
3. 📦 Entregable Documentado y Reutilizable: Código fuente ordenado con manual de 1 paso o script ejecutable para que puedas volver a correr la extracción cuando lo desees.

Proyectos similares de scraping y automatización disponibles en mi GitHub ({github_url}).

💡 Preguntas clave para el scraper:
• ¿El sitio web objetivo requiere inicio de sesión (login) o cuenta con algún sistema de protección Captcha/Cloudflare?
• ¿En qué formato específico necesitas la entrega final de los datos extraídos?

{commercial_block}

{closing_block}"""

        # 9. QA TESTING & ASEGURAMIENTO DE CALIDAD
        elif category == "qa_testing":
            return f"""Hola, leí con detenimiento tu solicitud de QA Testing para "{title}".

Puedo realizar las pruebas funcionales exhaustivas para certificar la estabilidad, seguridad y experiencia de usuario de tu software:

1. 🧪 Matriz de Casos de Prueba: Elaboración de cobertura completa con escenarios funcionales positivos, negativos y casos borde (edge cases).
2. 🚀 Pruebas Funcionales & Verificación de APIs: Validación de flujos end-to-end de usuario y verificación de endpoints con Postman (códigos de respuesta HTTP, validación de schemas JSON y tiempos de carga).
3. 📋 Reporte Detallado de Bugs en Jira/Trello: Documentación estructurada de cada incidencia con pasos exactos de reproducción, evidencias en video/capturas, severidad y comportamiento esperado.

Formación especializada en aseguramiento de calidad con proyectos comprobables en GitHub ({github_url}).

💡 Preguntas clave para la fase de testing:
• ¿La aplicación a evaluar es un entorno web, aplicación móvil (Android/iOS) o endpoints de API backend?
• ¿Cuentan con historias de usuario o especificaciones funcionales previas, o estructuramos los casos desde los flujos principales?

{commercial_block}

{closing_block}"""

        # 10. SQL & BASES DE DATOS
        elif category == "sql_database":
            return f"""Hola, revisé tu requerimiento sobre "{title}".

Puedo ayudarte a estructurar, depurar o consultar tu base de datos con máxima eficiencia y rendimiento:

1. 🔍 Diagnóstico & Modelado Relacional: Análisis de esquemas, claves foráneas, tipos de datos y normalización (PostgreSQL, MySQL o SQLite).
2. ⚡ Consultas SQL Optimizadas: Redacción de consultas complejas con JOINs eficientes, agregaciones, subconsultas e índices para tiempos de respuesta mínimos.
3. 📄 Scripts Probados y Documentados: Entrega de código SQL limpio, comentado y validado para su integración directa.

Repositorio técnico con proyectos de bases de datos disponible en GitHub ({github_url}).

💡 Preguntas clave sobre tu base de datos:
• ¿Qué motor de base de datos están utilizando actualmente (PostgreSQL, MySQL, SQL Server u otro)?
• ¿El objetivo es crear un nuevo esquema o depurar y acelerar consultas de un sistema en producción?

{commercial_block}

{closing_block}"""

        # 11. DESARROLLO WEB & WORDPRESS / LANDING PAGES
        elif category == "web_dev":
            return f"""Hola, revisé los requerimientos de tu proyecto web para "{title}".

Puedo ayudarte a desarrollar esta solución con código limpio, diseño visual moderno, alta velocidad de carga y total adaptabilidad móvil:

1. 🎨 Maquetación Responsiva & Estética: Interfaz fluida optimizada para celulares, tablets y computadoras de escritorio cumpliendo estándares UI/UX.
2. ⚡ Lógica, Formularios & APIs: Integración de formularios de contacto con envío directo a correo o WhatsApp, y consumo de APIs según tus especificaciones.
3. 🚀 Despliegue & Garantía de Funcionamiento: Configuración en tu servidor/hosting con certificado SSL activo y código ordenado listo para producción.

Portafolio web con proyectos reales desplegados disponible en mi perfil de GitHub ({github_url}).

💡 Preguntas clave sobre el sitio:
• ¿Ya cuentan con dominio y hosting contratados o requieren orientación para la configuración inicial?
• ¿Tienen un sitio de referencia cuyo estilo visual o estructura de navegación les gustaría tomar como modelo?

{commercial_block}

{closing_block}"""

        # 12. GENERAL / SOPORTE TI
        else:
            return f"""Hola, revisé con atención tu proyecto para "{title}".

Como Ingeniero de Sistemas, pongo a tu disposición mi formación técnica, disciplina y capacidad de resolución para abordar tu requerimiento con rapidez y precisión:

1. 🛠️ Diagnóstico Técnico: Análisis detallado de la necesidad para plantear la solución más limpia y duradera.
2. ⚙️ Ejecución Metódica: Aplicación de buenas prácticas profesionales con comunicación constante y cumplimiento de plazos.
3. 📋 Entrega Llave en Mano: Entrega documentada y acompañamiento post-entrega para verificar que todo funcione a tu entera satisfacción.

Portafolio técnico y proyectos prácticos disponibles en mi GitHub ({github_url}).

💡 Preguntas clave para comenzar:
• ¿Cuáles son los entregables más urgentes que necesitas tener listos en los primeros días?
• ¿Cuentas con accesos o documentación previa que pueda revisar de inmediato?

{commercial_block}

{closing_block}"""
