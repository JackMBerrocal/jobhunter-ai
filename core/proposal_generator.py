import os
import re
import json
import urllib.request
from typing import Dict, Any, Optional, List

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class BriefDetailExtractor:
    """
    Extractor cognitivo de entidades y especificaciones dentro del requerimiento del cliente.
    Detecta CMS, páginas, activos ya entregados (dominio, guía de estilo, textos, fotos, PDF),
    exclusiones explícitas (sin tienda, sin entradas dinámicas) y requerimientos normativos/técnicos.
    """

    @staticmethod
    def extract(title: str, description: str) -> Dict[str, Any]:
        text = f"{title} {description}".lower()

        # 1. CMS & Plataformas
        has_hostinger = "hostinger" in text
        has_wordpress = bool(re.search(r'\b(?:wordpress|wp)\b|/wordpress', text))
        has_shopify = "shopify" in text
        has_woocommerce = "woocommerce" in text
        has_elementor = "elementor" in text
        has_gutenberg = "gutenberg" in text
        has_divi = "divi" in text
        has_react = bool(re.search(r'\breact\b|react\.js', text))
        has_php = bool(re.search(r'\bphp\b', text))
        has_mysql = bool(re.search(r'\bmysql\b', text))
        has_python = "python" in text
        has_powerbi = bool(re.search(r'\b(?:power\s*bi|powerbi|dax|pbix)\b', text))

        # 2. Alcance numérico
        pages_match = re.search(r'(\d+)\s*(?:páginas|paginas|pages|secciones|pantallas)', text)
        pages_count = pages_match.group(1) if pages_match else None

        products_match = re.search(r'(\d+)\s*(?:productos|artículos|articulos|items|skus)', text)
        products_count = products_match.group(1) if products_match else None

        reels_match = re.search(r'(\d+)\s*(?:reels|tiktoks|videos|posts|publicaciones)', text)
        reels_count = reels_match.group(1) if reels_match else None

        hours_match = re.search(r'(\d+)\s*(?:horas diarias|hrs diarias|horas al día|horas por día|horas/semana)', text)
        hours_count = hours_match.group(1) if hours_match else None

        # 3. Materiales ya listos en poder del cliente (¡NUNCA PREGUNTAR POR ESTOS!)
        domain_linked = any(w in text for w in [
            "vinculado al dominio", "dominio vinculado", "ya está vinculado", "ya esta vinculado",
            "tengo dominio", "dominio comprado", "dominio configurado", "dominio listo", "ya cuenta con dominio"
        ])
        hosting_ready = any(w in text for w in [
            "hostinger", "hosting contratado", "ya tengo hosting", "servidor listo", "ya está en el hosting", "cuenta con hosting"
        ])
        brand_guide_ready = any(w in text for w in [
            "guía de estilo", "guia de estilo", "diseñador gráfico", "diseñador grafico",
            "diseño definido", "marca definida", "manual de marca", "identidad visual", "paleta de colores definida"
        ])
        texts_ready = any(w in text for w in [
            "textos redactados", "textos listos", "copy listo", "textos preparados", "contenido redactado", "información redactada"
        ])
        photos_ready = any(w in text for w in [
            "fotografías", "fotografias", "fotos listas", "imágenes listas", "imagenes listas", "fotos preparadas"
        ])
        pdf_provided = any(w in text for w in [
            "en el pdf", "adjunto pdf", "pdf explico", "pdf con", "especificaciones en pdf", "documento en pdf", "revisar pdf", "ver pdf"
        ])
        structure_defined = any(w in text for w in [
            "estructura ya definida", "estructura definida", "tengo claro qué quiero", "tengo claro que quiero", "flujo definido", "mapa del sitio"
        ])

        # 4. Exclusiones explícitas del cliente (¡RESPETAR ESTRICTAMENTE!)
        no_shop = any(w in text for w in [
            "no hay tienda", "sin tienda", "ni tienda", "no ecommerce", "no e-commerce", "no pasarela", "ni pasarela de pago", "sin pasarela", "no ventas online"
        ])
        no_dynamic = any(w in text for w in [
            "no hay entradas dinámicas", "no entradas dinamicas", "ni entradas dinámicas", "sin blog", "sin entradas", "web estática", "sitio informativo", "condensar la información", "condensar informacion"
        ])

        # 5. Funcionalidades específicas solicitadas
        has_cookie_banner = any(w in text for w in [
            "banner para cookies", "banner de cookies", "aviso de cookies", "cookies", "rgpd", "gdpr", "consentimiento"
        ])
        has_contact_form = any(w in text for w in [
            "formulario", "formularios", "contacto", "recoger información", "captar clientes", "consultas"
        ])
        has_ads_publicity = any(w in text for w in [
            "publicidad", "hacer publicidad", "anuncios", "meta ads", "google ads", "campañas"
        ])

        return {
            "has_hostinger": has_hostinger,
            "has_wordpress": has_wordpress,
            "has_shopify": has_shopify,
            "has_woocommerce": has_woocommerce,
            "has_elementor": has_elementor,
            "has_gutenberg": has_gutenberg,
            "has_divi": has_divi,
            "has_react": has_react,
            "has_php": has_php,
            "has_mysql": has_mysql,
            "has_python": has_python,
            "has_powerbi": has_powerbi,
            "pages_count": pages_count,
            "products_count": products_count,
            "reels_count": reels_count,
            "hours_count": hours_count,
            "domain_linked": domain_linked,
            "hosting_ready": hosting_ready,
            "brand_guide_ready": brand_guide_ready,
            "texts_ready": texts_ready,
            "photos_ready": photos_ready,
            "pdf_provided": pdf_provided,
            "structure_defined": structure_defined,
            "no_shop": no_shop,
            "no_dynamic": no_dynamic,
            "has_cookie_banner": has_cookie_banner,
            "has_contact_form": has_contact_form,
            "has_ads_publicity": has_ads_publicity
        }


class ProposalGenerator:
    """
    Motor de Inteligencia Artificial y Razonamiento Cognitivo para Propuestas Freelance.
    Distingue con precisión quirúrgica:
    - Servicios por Horas / Turnos (Atención WhatsApp, Soporte, Community Manager, Setter, Asistencia Virtual)
    - Proyectos por Trabajo Realizado / Precio Fijo (Web en WordPress/Hostinger, Chatbots IA, Power BI, QA, Scraping, etc.)
    Aplica tarifas reales dentro del rango del cliente, lee detalle a detalle el brief,
    formula preguntas estratégicas pertinentes (sin preguntar lo que el cliente ya aclaró)
    y garantiza el cierre 100% en el chat de la plataforma (CERO llamadas externas ni WhatsApp).
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
        Clasifica con precisión la categoría técnica del proyecto evitando colisiones por substrings.
        """
        text = f"{title} {description} {' '.join(skills or [])}".lower()
        t_low = title.lower()

        # 1. Web Scraping & Extracción con Python (Prioridad sobre 'web' genérico)
        if any(w in t_low for w in ["extraer lista", "scraping", "scraper", "crawling", "extraer datos", "scrapear"]) or any(w in text for w in [
            "scraping", "scraper", "crawling", "extraer datos", "extracción de datos", "extraccion de datos",
            "extraer lista", "extraer contactos", "extraer correos", "script python", "script en python",
            "playwright", "selenium", "beautifulsoup", "scrapear"
        ]):
            return "python_automation_scraping"

        # 2. Desarrollo Web & Frontend (PHP, MySQL, WordPress, Landing pages, React)
        if any(w in t_low for w in [
            "landing page", "wordpress", "hostinger", "sitio web", "pagina web", "página web", "desarrollo web",
            "react", "frontend", "maquetación web", "maquetacion web", "php y mysql"
        ]) or any(w in text for w in [
            "wordpress", "hostinger", "landing page", "elementor", "gutenberg",
            "desarrollo web", "página web", "pagina web", "frontend", "sitio web"
        ]):
            return "web_dev"

        # 3. Asistencia Virtual, Gestión de Agenda & Operaciones
        if any(w in t_low for w in ["asistente virtual", "virtual assistant", "asistente administrativo", "secretaria", "recepcionista virtual"]) or any(w in text for w in [
            "asistente virtual", "virtual assistant", "asistente administrativo", "gestión de agenda", "gestion de agenda",
            "agendar citas", "gestión de citas", "gestion de citas", "gestion de correos", "data entry", "transcripción", "agenda digital"
        ]):
            return "virtual_assistant_admin"

        # 4. Diseño Gráfico, Logotipos, Photoshop, Illustrator & Branding
        if any(w in t_low for w in [
            "diseño gráfico", "diseno grafico", "photoshop", "illustrator", "logotipo", "logo",
            "banner", "banners", "flyer", "flyers", "branding", "identidad visual", "vector", "vectorizar",
            "graphic design", "logo design", "tarjeta de presentación"
        ]) or any(w in text for w in [
            "diseño gráfico", "diseno grafico", "photoshop", "illustrator", "logotipo", "logo design",
            "banner", "banners", "flyer", "flyers", "branding", "identidad visual", "vector", "vectorizar",
            "retoque fotográfico", "retoque fotografico", "edición de fotos", "edicion de fotos", "folleto",
            "mockup", "diseño de logo", "diseno de logo", "tarjeta de presentación", "tarjetas de presentacion",
            "piezas gráficas", "piezas graficas", "arte digital", "diseño creativo", "graphic design"
        ]):
            return "graphic_design_creative"

        # 5. Redes Sociales, Instagram, TikTok, Reels & Marketing Digital
        if any(w in t_low for w in ["instagram", "tiktok", "reels", "redes sociales", "community manager", "crecimiento ig", "crecimiento tiktok"]) or any(w in text for w in [
            "tiktok", "instagram", "reels", "community manager", "redes sociales", "crecimiento ig", "crecimiento tiktok",
            "parrilla de contenido", "estrategia de contenido", "seguidores reales", "engagement", "creador de contenido",
            "videos de tiktok", "posts para instagram", "growth marketing", "social media", "crecer en instagram"
        ]):
            return "social_media_growth"

        # 6. E-Commerce & Tiendas Virtuales (Shopify, WooCommerce, Catálogo)
        if any(w in text for w in [
            "shopify", "woocommerce", "tienda online", "tienda virtual", "subir productos", "catalogo de productos",
            "mercado libre", "amazon fba", "dropshipping", "e-commerce", "ecommerce", "tiendanube"
        ]):
            return "ecommerce_stores"

        # 7. Setter de Ventas & Agendamiento Comercial
        if any(w in text for w in [
            "setter", "asesoría fitness", "asesoria fitness", "llamadas de venta", "appointment setter",
            "agendar llamadas", "agendamiento de llamadas", "prospección", "prospeccion",
            "cold caller", "closer", "cerrador", "lead qualification", "cerrar ventas"
        ]):
            return "sales_setter_crm"

        # 8. Chatbots con Inteligencia Artificial & Sistemas de Software
        if any(w in text for w in [
            "bot faq", "asistente automático", "asistente automatico", "crear chatbot",
            "desarrollo de bot", "desarrollar chatbot", "bot con ia", "chatbot con inteligencia",
            "sistema automatizado con ia", "bot de whatsapp", "bot whatsapp", "flujo manychat",
            "agente con ia", "agente ia", "bot inteligente", "automatizar respuestas con ia",
            "chatbot gpt", "chatbot", "typebot", "voicebot"
        ]):
            return "ai_chatbot_system"

        # 9. Soporte & Atención Humana por Chat / WhatsApp
        if any(w in t_low for w in ["whatsapp", "responder mensajes", "atención al cliente", "atencion al cliente", "chat"]) or any(w in text for w in [
            "responder mensajes", "atención al cliente", "atencion al cliente",
            "customer service", "customer support", "soporte por chat", "chat support",
            "contestar mensajes", "atender mensajes", "chat de atención", "moderador de chat",
            "atención de consultas"
        ]):
            return "customer_support_whatsapp"

        # 10. Power BI & Analítica de Datos (Con delimitadores exactos para evitar colisiones)
        if bool(re.search(r'\b(?:power\s*bi|powerbi|dax|power\s*query|pbix|business\s*intelligence)\b', text)):
            return "power_bi_data"

        # 11. QA Testing & Pruebas de Software
        if any(w in text for w in [
            "qa", "testing", "tester", "pruebas funcionales", "postman", "casos de prueba",
            "test cases", "reporte de bugs", "control de calidad", "smoke testing", "pruebas de regresion"
        ]):
            return "qa_testing"

        # 12. SQL & Bases de Datos
        if any(w in text for w in [
            "sql", "postgres", "postgresql", "mysql", "queries sql",
            "procedimientos almacenados", "optimización de consultas", "stored procedure", "consultas sql"
        ]):
            return "sql_database"

        # 13. Soporte TI / Helpdesk
        if any(w in text for w in [
            "soporte ti", "soporte técnico", "soporte tecnico", "helpdesk", "active directory", "anydesk"
        ]):
            return "it_support"

        return "general_tech"

    def estimate_bid_and_time(self, budget_str: str, category: str, full_text: str = "") -> Dict[str, Any]:
        """
        Calcula el presupuesto óptimo y el tiempo/disponibilidad.
        Detecta estrictamente si es por hora (Hourly) o precio fijo (Fixed).
        NUNCA confunde un rango de precio fijo (ej: EUR 50 - 250) con una tarifa por hora.
        """
        b_low = (budget_str or "").lower()
        t_low = (full_text or "").lower()

        # Detección de moneda
        currency = "USD"
        curr_symbol = "$"
        if "eur" in b_low or "€" in b_low or "eur" in t_low or "€" in t_low:
            currency = "EUR"
            curr_symbol = "€"
        elif "pen" in b_low or "s/" in b_low or "soles" in b_low:
            currency = "PEN"
            curr_symbol = "S/"
        elif "cop" in b_low:
            currency = "COP"
            curr_symbol = "COP $"
        elif "mxn" in b_low:
            currency = "MXN"
            curr_symbol = "MXN $"

        # Verificación estricta de Por Hora en el presupuesto (soporta '/ hora', '/hora', '/ hr', etc.)
        has_hourly_in_budget = bool(re.search(r'(?:/\s*(?:hr|hora|hour|h)\b|\b(?:por hora|por horas|hourly|x hora|x hr)\b)', b_low))
        has_fixed_range = bool(re.search(r'(?<!\w)\d+\s*-\s*\d+(?!\w)', b_low))

        if has_hourly_in_budget:
            is_hourly = True
        elif has_fixed_range:
            # Un rango numérico como "EUR 50 - 250" sin mención horaria es 100% PRECIO FIJO
            is_hourly = False
        else:
            # Si el presupuesto no tiene rango fijo ("A convenir" o vacío), verificar descripción con regex estricto
            is_hourly = bool(re.search(r'\b(?:pago por hora|tarifa por hora|contrato por hora|precio por hora|cobro por hora|por hora trabajada|hourly rate)\b', t_low))

        raw_nums = re.findall(r'(?<!\w)(\d+(?:\.\d+)?)(?!\w)', budget_str or "")
        numbers = [float(n) for n in raw_nums if float(n) > 0]

        # ---------------- CASO 1: CONTRATO POR HORA ----------------
        if is_hourly:
            if numbers:
                min_v = min(numbers)
                max_v = max(numbers)
                if min_v == max_v:
                    suggested_rate = int(min_v)
                else:
                    suggested_rate = int(round(min_v + (max_v - min_v) * 0.55))
            else:
                defaults_hourly = {
                    "customer_support_whatsapp": 16,
                    "sales_setter_crm": 18,
                    "social_media_growth": 18,
                    "virtual_assistant_admin": 15,
                    "qa_testing": 20,
                    "power_bi_data": 25,
                    "python_automation_scraping": 25,
                    "web_dev": 22,
                    "ecommerce_stores": 18,
                    "graphic_design_creative": 20
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

        # ---------------- CASO 2: PRECIO FIJO / POR TRABAJO REALIZADO ----------------
        if numbers:
            min_v = min(numbers)
            max_v = max(numbers)
            if min_v == max_v:
                target = int(min_v)
            else:
                # Cotización competitiva llave en mano dentro del rango del cliente
                if max_v <= 80:
                    target = int(max_v)
                elif max_v <= 250:
                    # Para presupuestos de 50 - 250 -> 50 + 200 * 0.45 = 140
                    target = int(round(min_v + (max_v - min_v) * 0.45))
                elif max_v <= 600:
                    target = int(round(min_v + (max_v - min_v) * 0.45))
                else:
                    target = int(round(min_v + (max_v - min_v) * 0.40))

            # Plazo de entrega según envergadura
            if max_v <= 80:
                timeline = "24 a 48 horas"
            elif max_v <= 250:
                timeline = "3 a 4 días hábiles"
            elif max_v <= 600:
                timeline = "4 a 6 días hábiles"
            else:
                timeline = "1 a 2 semanas"

            suggested_bid = f"{curr_symbol}{target} {currency}"
            suggested_timeline = timeline
        else:
            defaults_fixed = {
                "web_dev": (f"{curr_symbol}140 {currency}", "3 a 4 días hábiles"),
                "ecommerce_stores": (f"{curr_symbol}160 {currency}", "3 a 5 días hábiles"),
                "social_media_growth": (f"{curr_symbol}140 {currency}", "Entregables semanales"),
                "python_automation_scraping": (f"{curr_symbol}95 {currency}", "48 horas"),
                "power_bi_data": (f"{curr_symbol}130 {currency}", "3 días hábiles"),
                "qa_testing": (f"{curr_symbol}90 {currency}", "48 horas"),
                "sql_database": (f"{curr_symbol}80 {currency}", "48 horas"),
                "ai_chatbot_system": (f"{curr_symbol}280 {currency}", "5 a 7 días"),
                "sales_setter_crm": (f"{curr_symbol}180 {currency}", "Por ciclo de prospección"),
                "customer_support_whatsapp": (f"{curr_symbol}180 {currency}", "Por turno acordado"),
                "virtual_assistant_admin": (f"{curr_symbol}160 {currency}", "Por paquete de tareas"),
                "graphic_design_creative": (f"{curr_symbol}85 {currency}", "24 a 48 horas")
            }
            suggested_bid, suggested_timeline = defaults_fixed.get(category, (f"{curr_symbol}120 {currency}", "3 a 4 días"))

        return {
            "suggested_bid": suggested_bid,
            "suggested_timeline": suggested_timeline,
            "is_hourly": False,
            "currency": currency
        }

    def _call_external_llm(self, prompt: str) -> Optional[str]:
        """Intenta invocar Gemini o Groq si están configurados en el entorno."""
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
        Genera una propuesta comercial personalizada, detallada y de alto impacto.
        Cumple estrictamente las Reglas de Oro de Agencia:
        1. Lee el brief detalle a detalle reconociendo lo que el cliente ya entregó y lo que descartó.
        2. Plantea 2 a 3 preguntas estratégicas pertinentes para provocar respuesta en el chat.
        3. Nunca deriva a llamadas o contactos externos: cierre 100% dentro del chat de la plataforma.
        4. Cotización coherente con el tipo de contrato (Horas vs Precio Fijo).
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

        # Si hay LLM externo disponible, se ejecuta con prompt maestro ultra-específico
        modality_instruction = (
            "MODALIDAD: POR HORAS (HOURLY). Especifica disponibilidad de horas diarias, compromiso de turnos y reporte diario de actividades."
            if is_hourly else
            "MODALIDAD: POR TRABAJO REALIZADO (PRECIO FIJO). Especifica entregables cerrados, cronograma y ronda de ajustes incluida."
        )

        prompt = f"""
Eres un estratega senior de propuestas freelance redactando en nombre de Jack Michael Berrocal.
Perfil profesional de Jack:
- Egresado de Ingeniería de Sistemas (UTEL 2025). Especializado en Software, IA y Ciencia de Datos (Oracle Next Education - ONE / Alura).
- Habilidades: Desarrollo Web (WordPress, Hostinger, Elementor, Gutenberg, React, PHP), Gestión de Redes Sociales (IG/TikTok), Atención al Cliente WhatsApp/Chat (velocidad < 2 min, trato formal de "usted"), Chatbots con IA, Power BI, Python (Scraping, Playwright), QA Testing, SQL.
- Portafolio comprobable: {github_url}

Datos del proyecto del cliente:
- Título: "{title}"
- Descripción completa: "{description}"
- Presupuesto cliente: "{budget}"
- Cotización sugerida: "{suggested_bid}" ({modality_instruction})
- Tiempo estimado / Disponibilidad: "{timeline}"
- Categoría detectada: "{category}"

REGLAS DE ORO DE REDACCIÓN (¡ESTRICTAS!):
1. LEE DETALLE A DETALLE: Responde específicamente a los puntos y materiales mencionados. Si el cliente dice que ya tiene dominio, hosting o diseño en PDF, RECONÓCELO explícitamente y NUNCA le preguntes si ya tiene hosting o si necesita diseño.
2. PREGUNTAS ESTRATÉGICAS (OBLIGATORIAS): Incluye exactamente 2 a 3 preguntas técnicas y de negocio inteligentes que no hayan sido respondidas en el brief, para demostrar dominio y provocar respuesta en el chat.
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
            budget=budget,
            github_url=github_url
        )

        return {
            "category": category,
            "suggested_bid": suggested_bid,
            "suggested_timeline": timeline,
            "is_hourly": is_hourly,
            "proposal_text": codeword_prefix + proposal_text
        }

    def _generate_cognitive_proposal(
        self,
        title: str,
        description: str,
        category: str,
        suggested_bid: str,
        timeline: str,
        is_hourly: bool,
        budget: str = "",
        github_url: str = "https://github.com/JackMBerrocal"
    ) -> str:
        """
        Generador cognitivo de propuestas que analiza el requerimiento detalle a detalle,
        extrae activos y restricciones del cliente, formula preguntas inteligentes y diferencia
        con precisión milimétrica la modalidad comercial.
        """
        details = BriefDetailExtractor.extract(title, description)

        # Formato de bloque comercial según modalidad
        if is_hourly:
            commercial_block = f"""💼 Modalidad de Trabajo & Tarifa:
• Tarifa Propuesta: {suggested_bid}.
• Disponibilidad: {timeline}.
• Control & Transparencia: Registro transparente de actividades, bitácora diaria de tareas cumplidas y total adaptación a tu franja horaria."""
        else:
            budget_mention = f" (dentro de tu presupuesto de {budget})" if budget else ""
            commercial_block = f"""📦 Cotización Cerrada & Plazo Llave en Mano:
• Presupuesto Cerrado: {suggested_bid}{budget_mention}.
• Plazo de Entrega: {timeline} con puesta en producción.
• Garantía de Calidad: Incluye entrega de accesos, archivos fuente y una ronda de ajustes finales para certificar que cada sección quede exactamente como deseas."""

        closing_block = "Quedo disponible en este momento por el chat de la plataforma para resolver cualquier consulta y arrancar de inmediato. Coordinamos el 100% del proyecto por este chat, sin necesidad de llamadas externas ni pérdidas de tiempo. 🚀"

        # -------------------------------------------------------------
        # 1. DESARROLLO WEB & WORDPRESS / HOSTINGER / LANDING PAGES
        # -------------------------------------------------------------
        if category == "web_dev":
            pages_desc = f"de {details['pages_count']} páginas" if details['pages_count'] else "de servicios profesionales"
            platform_desc = "WordPress alojado en tu servidor Hostinger" if (details['has_hostinger'] and details['has_wordpress']) else ("WordPress" if details['has_wordpress'] else "web responsiva")

            # Pilar 1: Maquetación y estilo
            pages_count_str = f"{details['pages_count']} páginas" if details['pages_count'] else "páginas requeridas"
            if details['brand_guide_ready'] or details['structure_defined']:
                p1 = f"""1. 🎨 Maquetación Fiel a tu Guía de Estilo & Adaptabilidad Total:
Implementación de las {pages_count_str} respetando al 100% la guía de estilo del diseñador, la estructura establecida, los textos redactados y las fotografías preparadas. Interfaz moderna y fluida optimizada para celulares, tablets y computadoras de escritorio cumpliendo con los estándares de tu marca."""
            else:
                p1 = """1. 🎨 Maquetación Responsiva & Estética Moderna:
Diseño visual moderno optimizado para celulares, tablets y computadoras de escritorio cumpliendo estándares UI/UX, logrando una presentación clara y profesional de tus servicios."""

            # Pilar 2: Funcionalidad técnica y normativas
            p2_points = []
            if details['has_cookie_banner']:
                p2_points.append("Instalación y configuración del banner de cookies para estricto cumplimiento legal de privacidad y publicidad")
            if details['has_contact_form']:
                p2_points.append("Integración de formularios de contacto directos para captar las consultas de los clientes")
            if details['no_shop'] or details['no_dynamic']:
                p2_points.append("Arquitectura estática ultra ligera sin sobrecarga de plugins de tienda ni bases de datos dinámicas innecesarias")
            else:
                p2_points.append("Formularios de contacto operativos y optimización básica on-page")

            p2 = f"""2. ⚡ Funcionalidad & Cumplimiento Normativo:
{chr(10).join(['• ' + pt for pt in p2_points])}."""

            # Pilar 3: Despliegue en hosting
            if details['has_hostinger'] and details['domain_linked']:
                p3 = """3. 🚀 Despliegue en Hostinger & Alta Velocidad de Carga:
Configuración en tu hosting Hostinger sobre el dominio que ya tienes vinculado, certificado SSL activo, compresión de imágenes a formato WebP y optimización de caché para una velocidad de carga instantánea (PageSpeed 90+)."""
            else:
                p3 = """3. 🚀 Despliegue en Servidor & Verificación Técnica:
Puesta en marcha sobre tu servidor con certificado SSL activo, código ordenado y revisión completa de enlaces y formularios previo a la entrega."""

            # Preguntas estratégicas (NUNCA preguntar lo que el cliente ya dio)
            questions = []
            if details['has_wordpress']:
                if not details['has_elementor'] and not details['has_gutenberg']:
                    questions.append("¿Prefieres que la maquetación se desarrolle con Elementor o con Gutenberg (bloques nativos de WordPress para máxima velocidad en Hostinger)?")

            if details['pdf_provided']:
                questions.append("¿Podrías compartirme el PDF por el chat de la plataforma para validar la estructura exacta de las páginas y arrancar con el mapa claro?")
            elif not details['structure_defined']:
                questions.append("¿Tienes ya definido el esquema o boceto de las secciones que llevará cada página?")

            if details['has_cookie_banner'] and details['has_ads_publicity']:
                questions.append("¿Deseas que el banner de cookies sea compatible con Google Consent Mode v2 para medir tus campañas de publicidad sin bloqueos?")
            elif details['has_contact_form']:
                questions.append("¿Los formularios de contacto enviarán las consultas a un correo corporativo específico?")

            if len(questions) < 2:
                questions.append("¿Cuentas con los accesos al panel de Hostinger/WordPress listos para comenzar la maquetación hoy mismo?")

            q_block = "\n".join([f"• {q}" for q in questions[:3]])

            return f"""Hola, revisé minuciosamente los requerimientos para "{title}".

Comprendo con total claridad lo que necesitas: maquetar un sitio web profesional {pages_desc} en {platform_desc}, convirtiendo fielmente los materiales ya preparados en una web funcional, rápida y orientada a presentar tus servicios:

{p1}

{p2}

{p3}

Portafolio web con proyectos reales desplegados disponible en mi GitHub ({github_url}).

💡 Preguntas clave para afinar los detalles de inmediato:
{q_block}

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 2. CRECIMIENTO DE REDES SOCIALES (TIKTOK, REELS, INSTAGRAM)
        # -------------------------------------------------------------
        elif category == "social_media_growth":
            reels_str = f"de {details['reels_count']} contenidos" if details['reels_count'] else "con publicaciones y reels estratégicos"

            return f"""Hola, revisé los detalles de tu proyecto para "{title}".

Entiendo que el objetivo prioritario es impulsar el alcance, engagement y flujo de prospectos de forma coordinada en Instagram y TikTok {reels_str}, trabajando con métricas de conversión comprobables:

1. 🔍 Diagnóstico & Posicionamiento: Análisis del perfil actual, benchmarks de competidores en tu nicho y definición de ganchos (hooks) para retener la atención en los primeros 3 segundos.
2. 📱 Creación & Adaptación de Contenidos: Edición dinámica de reels y posts adaptados a las tendencias y algoritmos actuales de TikTok e Instagram, con portadas atractivas y llamados a la acción (CTA) claros.
3. 📈 Optimización Semanal de Resultados: Monitoreo periódico de retención y reproducciones para iterar sobre los formatos que generen mayor interacción y tráfico.

Portafolio de edición y proyectos visuales disponible en mi perfil de GitHub ({github_url}).

💡 Preguntas clave para iniciar con precisión:
• ¿Cuentan actualmente con material grabado para edición y adaptación, o partiremos de guiones conceptualizados desde cero?
• ¿Cuál es el producto, servicio o llamado a la acción central hacia donde queremos dirigir a los seguidores?
• ¿La estrategia inicial se basará en crecimiento 100% orgánico o se complementará con campañas de Meta Ads / TikTok Ads?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 3. E-COMMERCE & TIENDAS VIRTUALES (SHOPIFY / WOOCOMMERCE)
        # -------------------------------------------------------------
        elif category == "ecommerce_stores":
            items_str = f"de los {details['products_count']} productos" if details['products_count'] else "del catálogo completo de productos"

            return f"""Hola, leí con atención los requerimientos de tu proyecto para "{title}".

Puedo encargarme de la configuración integral, carga de productos y optimización de tu tienda virtual para asegurar un flujo de compra rápido, confiable y con alta conversión móvil:

1. 🛍️ Carga de Catálogo & Arquitectura de Productos: Subida detallada {items_str} con variantes (tallas, colores), títulos optimizados para búsqueda, descripciones atractivas y control de inventario.
2. 💳 Pasarelas de Pago & Configuración de Envíos: Integración segura de métodos de cobro locales e internacionales y cálculo automático de costos de despacho según zonas geográficas.
3. 📱 Optimización Móvil & Checkout sin Fricción: Verificación rigurosa de que el proceso de compra funcione con fluidez desde cualquier celular.

💡 Preguntas clave sobre tu tienda:
• ¿En qué plataforma está construida la tienda (Shopify, WooCommerce, Tiendanube u otra)?
• ¿Tienes ya la lista de productos organizada con imágenes y precios, o requieres apoyo para estructurar la base de datos de productos?
• ¿Qué pasarelas de pago principales necesitas tener habilitadas para el cobro a clientes?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 4. SOPORTE & ATENCIÓN AL CLIENTE POR WHATSAPP / CHAT
        # -------------------------------------------------------------
        elif category == "customer_support_whatsapp":
            return f"""Hola, leí con detenimiento tu solicitud para la atención y soporte de clientes vía WhatsApp.

Cuento con disponibilidad inmediata para cubrir tu servicio cumpliendo rigurosamente con una velocidad de respuesta menor a 2 minutos, tratamiento formal de "usted" y una redacción impecable en español nativo:

1. 💬 Atención Empática & Rigurosa: Aplicación estricta de tus protocolos y políticas de empresa para resolver dudas frecuentes, guiar compras y atender consultas con amabilidad y precisión.
2. ⌨️ Eficiencia con WhatsApp Web: Uso intensivo de atajos de teclado, etiquetas organizativas y respuestas rápidas para gestionar múltiples conversaciones en paralelo sin descuidar el detalle.
3. 📊 Bitácora Diaria de Incidencias: Registro consolidado de chats atendidos, motivos principales de consulta y escalamiento inmediato de casos especiales al cierre de cada jornada.

💡 Preguntas clave para coordinar la atención:
• ¿Cuál es el volumen promedio aproximado de conversaciones o consultas que se reciben por turno?
• ¿Cuentas con un documento de preguntas frecuentes (FAQs), catálogo o guía de respuestas para iniciar la inducción de inmediato?
• ¿El servicio se gestiona directamente sobre WhatsApp Business / Web o a través de una plataforma multiagente (como Kommo, ManyChat o Zendesk)?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 5. SETTER DE VENTAS & PROSPECCIÓN CRM
        # -------------------------------------------------------------
        elif category == "sales_setter_crm":
            return f"""Hola, revisé tu publicación para el rol de Setter de Ventas y Prospección Comercial.

Cuento con comunicación asertiva, disciplina metódica y enfoque orientado a resultados para transformar prospectos interesados en reuniones agendadas de alto valor en tu calendario:

1. 🎯 Cualificación Rápida de Leads: Respuesta inmediata a prospectos aplicando preguntas estratégicas para validar interés, necesidad real y capacidad de decisión.
2. 💬 Tratamiento de Objeciones & Agendamiento: Manejo empático de dudas habituales para asegurar la cita en el horario del cerrador, manteniendo un trato formal y profesional.
3. 📈 Seguimiento Riguroso en CRM: Registro diario del estatus de cada contacto en tu CRM o herramienta de control para evitar pérdida de oportunidades comerciales.

💡 Preguntas clave para el flujo comercial:
• ¿De qué canales provienen los prospectos principales (Meta Ads, inbound en redes sociales o prospección en frío)?
• ¿Qué herramienta utilizan para el agendamiento y control de citas (Calendly, HubSpot, Google Calendar)?
• ¿Cuentan con un guión o estructura de cualificación predefinida para iniciar de inmediato?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 6. ASISTENCIA VIRTUAL & GESTIÓN ADMINISTRATIVA
        # -------------------------------------------------------------
        elif category == "virtual_assistant_admin":
            return f"""Hola, revisé los detalles de tu solicitud para asistencia virtual y soporte administrativo.

Como profesional en Ingeniería de Sistemas, ofrezco un perfil organizado, metódico y confiable para gestionar tus operaciones diarias con autonomía y confidencialidad:

1. 📋 Gestión Operativa Diaria: Administración de correos, agenda de reuniones, seguimiento de pendientes y comunicación formal con clientes o proveedores en español neutro impecable.
2. 🗄️ Control de Documentación y Datos: Manejo avanzado de Google Workspace, Excel/Sheets y Notion, manteniendo reportes limpios, actualizados y ordenados.
3. ⚡ Reportes de Cierre de Jornada: Entrega diaria del estatus de actividades cumplidas y asuntos pendientes para tu completa tranquilidad.

💡 Preguntas clave para organizar las labores:
• ¿Cuáles serán las tareas prioritarias en las que necesitas apoyo durante los primeros días?
• ¿La posición requiere disponibilidad en un horario continuo específico o se maneja por objetivos diarios?
• ¿Qué herramientas principales utiliza el equipo para la comunicación interna y asignación de tareas?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 7. CHATBOTS CON INTELIGENCIA ARTIFICIAL & AUTOMATIZACIONES
        # -------------------------------------------------------------
        elif category == "ai_chatbot_system":
            return f"""Hola, leí con atención tu proyecto para la implementación de un sistema de Chatbot con Inteligencia Artificial.

Como Ingeniero de Sistemas especializado en Software y Ciencia de Datos (Oracle Next Education), puedo diseñar una arquitectura conversacional robusta, confiable y libre de alucinaciones:

1. 🧠 Base de Conocimientos & RAG: Integración de modelos LLM con tus catálogos, PDFs y políticas para que el bot responda con precisión matemática y lenguaje natural a las dudas de tus usuarios.
2. 🔗 Conexión de Canales Oficiales: Integración mediante webhooks seguros con la API oficial de WhatsApp (Meta Cloud API / Twilio), Telegram o Chat Web, sincronizando datos con tu base de datos o CRM.
3. 🔀 Derivación Inteligente & Auditoría: Detección automática de intenciones complejas para transferir el chat a un asesor humano cuando sea necesario, guardando telemetría de cada mensaje.

Portafolio de proyectos de automatización e IA disponible en mi GitHub ({github_url}).

💡 Preguntas clave sobre la arquitectura:
• ¿El bot se integrará con la API oficial de WhatsApp Cloud o sobre un chat web integrado en tu plataforma?
• ¿Cuentan con un archivo de preguntas frecuentes, catálogo o manual estructurado para entrenar la base de conocimiento?
• ¿Qué acciones automáticas debe ejecutar el bot además de responder dudas (ej: agendar citas, registrar leads o consultar stock)?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 8. POWER BI & ANALÍTICA DE DATOS
        # -------------------------------------------------------------
        elif category == "power_bi_data":
            return f"""Hola, revisé tu proyecto sobre "{title}".

Como Ingeniero de Sistemas especializado en Ciencia de Datos por Oracle Next Education (ONE / Alura), puedo diseñar un dashboard ejecutivo, interactivo y orientado a la toma de decisiones:

1. 🔄 Modelado & ETL con Power Query: Extracción, limpieza y normalización de tus fuentes de datos, garantizando integridad y eliminando redundancias.
2. 📊 Métricas & Fórmulas DAX: Creación de modelo relacional en estrella con medidas DAX para monitorear indicadores clave de rendimiento (ventas, márgenes, cohortes o tendencias).
3. 🎨 Visualización Ejecutiva de Alto Impacto: Diseño de interfaz intuitiva con segmentadores dinámicos, filtros temporales y layout limpio para la dirección.

Cuento con proyectos prácticos de analítica y bases de datos en mi repositorio ({github_url}).

💡 Preguntas clave sobre tus datos:
• ¿En qué formato se encuentran las fuentes de datos originales (Excel, Google Sheets, base de datos SQL o ERP)?
• ¿Cuáles son los 3 indicadores o KPIs más críticos que la dirección necesita visualizar en este reporte?
• ¿El reporte requiere actualización programada automática o carga periódica manual de archivos?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 9. WEB SCRAPING & AUTOMATIZACIÓN PYTHON
        # -------------------------------------------------------------
        elif category == "python_automation_scraping":
            return f"""Hola, leí con atención tu requerimiento técnico para "{title}".

Puedo desarrollar el script de extracción y automatización en Python de forma rápida, robusta y con código limpio:

1. ⚙️ Extracción Confiable & Evasión: Desarrollo modular con Playwright / Requests / BeautifulSoup, diseñado con reintentos automáticos, manejo de errores y respeto de estructuras web.
2. 🗄️ Procesamiento & Limpieza con Pandas: Normalización rigurosa de los campos extraídos para entregártelos exactamente en el formato requerido (Excel estructurado, CSV o base de datos relacional).
3. 📦 Entregable Documentado y Reutilizable: Código fuente ordenado con manual de 1 paso o script ejecutable para que puedas volver a correr la extracción cuando lo desees.

Proyectos similares de scraping y automatización disponibles en mi GitHub ({github_url}).

💡 Preguntas clave para el scraper:
• ¿El sitio web objetivo requiere inicio de sesión (login) o cuenta con algún sistema de protección Captcha/Cloudflare?
• ¿En qué formato específico necesitas la entrega final de los datos extraídos (Excel, CSV o base de datos)?
• ¿La extracción se ejecutará una única vez o requieres que el script quede automatizado para ejecuciones periódicas?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 10. QA TESTING & ASEGURAMIENTO DE CALIDAD
        # -------------------------------------------------------------
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
• ¿En qué herramienta prefieres que se registren los reportes de bugs (Jira, Trello, Notion o GitHub Issues)?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 11. SQL & BASES DE DATOS
        # -------------------------------------------------------------
        elif category == "sql_database":
            return f"""Hola, revisé tu requerimiento sobre "{title}".

Puedo ayudarte a estructurar, depurar o consultar tu base de datos con máxima eficiencia y rendimiento:

1. 🔍 Diagnóstico & Modelado Relacional: Análisis de esquemas, claves foráneas, tipos de datos y normalización (PostgreSQL, MySQL o SQLite).
2. ⚡ Consultas SQL Optimizadas: Redacción de consultas complejas con JOINs eficientes, agregaciones, subconsultas e índices para tiempos de respuesta mínimos.
3. 📄 Scripts Probados y Documentados: Entrega de código SQL limpio, comentado y validado para su integración directa.

Repositorio técnico con proyectos de bases de datos disponible en GitHub ({github_url}).

💡 Preguntas clave sobre tu base de datos:
• ¿Qué motor de base de datos están utilizando actualmente (PostgreSQL, MySQL, SQL Server u otro)?
• ¿El objetivo principal es crear un nuevo esquema relacional o depurar y acelerar consultas de un sistema en producción?
• ¿Cuentan con un diagrama entidad-relación o descripción de las tablas involucradas?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 12. DISEÑO GRÁFICO, PHOTOSHOP, ILUSTRACIÓN & BRANDING
        # -------------------------------------------------------------
        elif category == "graphic_design_creative":
            return f"""Hola, revisé detalladamente los requerimientos visuales para "{title}".

Comprendo con exactitud el impacto estético y la calidad que buscas transmitir. Como equipo de diseño gráfico y creativo con dominio avanzado de Adobe Photoshop y Adobe Illustrator, ofrecemos entregas ágiles y acabados de nivel agencia:

1. 🎨 Propuestas Originales & Concepto Visual: Creación de conceptos gráficos desde cero (logotipos, banners publicitarios, piezas para redes sociales, retoque fotográfico avanzado o vectorización en Illustrator), 100% alineados con tu identidad de marca.
2. 📦 Entrega Multiformato de Alta Resolución: Entrega de los archivos fuente editables (.AI y .PSD organizados en capas y vectores), versiones listas para imprenta (PDF CMYK 300 DPI) y formatos digitales optimizados para web y redes (.PNG con fondo transparente, .JPG alta definición y .SVG escalable).
3. ✨ Revisiones Ágiles hasta tu Plena Conformidad: Ajustes en composición, paleta cromática y tipografía sin costos adicionales hasta que el entregable quede exactamente como lo imaginas.

💡 Preguntas clave para iniciar con el diseño:
• ¿Cuentas con una paleta de colores corporativa o referencias visuales (marcas, estilos o bocetos) que te gusten especialmente?
• ¿Cuáles son las medidas o formatos finales requeridos (dimensiones para redes sociales, web o material impreso)?
• ¿Requieres que el primer borrador esté listo dentro de las próximas 24 a 48 horas?

{commercial_block}

{closing_block}"""

        # -------------------------------------------------------------
        # 13. GENERAL / SOPORTE TI
        # -------------------------------------------------------------
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
