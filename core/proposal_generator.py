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

def strip_all_emojis(text: str) -> str:
    """
    Elimina de forma exhaustiva todos los emojis, asteriscos markdown (**), almohadillas (###),
    cliches de apertura de IA y simbolos incompatibles con el formulario de Freelancer.com.
    """
    if not text:
        return ""
    emoji_pattern = re.compile(
        r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b00-\u2bff\ufe00-\ufe0f\u200d\u20e3\u3030]+",
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub("", text)
    cliches = [
        r"^\s*gracias\s+por\s+tu\s+inter[eé]s\s+en\s+mi\s+perfil[^\n\.]*[\.\n]*",
        r"^\s*gracias\s+por\s+confiar\s+en\s+m[ií][^\n\.]*[\.\n]*",
        r"^\s*entiendo\s+completamente\s+tu\s+requerimiento[^\n\.]*[\.\n]*",
        r"^\s*me\s+complace\s+escuchar\s+sobre\s+tu\s+inter[eé]s[^\n\.]*[\.\n]*",
        r"^\s*me\s+complazco\s+en[^\n\.]*[\.\n]*",
        r"^\s*espero\s+que\s+te\s+encuentres\s+muy\s+bien[^\n\.]*[\.\n]*",
        r"^\s*espero\s+que\s+est[eé]s\s+bien[^\n\.]*[\.\n]*"
    ]
    for c in cliches:
        cleaned = re.sub(c, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"^\s*estimad[oa]\s+cliente[,:.]*\s*\n*", "Hola, qué tal.\n\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\*+", "", cleaned)
    cleaned = re.sub(r"^[ \t]*#+[ \t]*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^[ \t]*[-•][ \t]*", "- ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^(\d+\.)\s+", r"\1 ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


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
        
        # Cargar llaves seguras de la nube (Groq, Gemini, OpenRouter) para evitar computación pesada en CPU
        from pathlib import Path
        miambot_env = Path("/home/jack/.gemini/antigravity-ide/scratch/miambot_repo/.env.production")
        if miambot_env.exists():
            try:
                with open(miambot_env, "r", encoding="utf-8") as ef:
                    for line in ef:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'").strip('"')
                            if not os.environ.get(k):
                                os.environ[k] = v
            except Exception:
                pass

        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
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

        # 0. EXCLUSIÓN TOTAL: DISEÑO DE INTERIORES, ARQUITECTURA, CONSTRUCCIÓN, 3D, MODELADO, RENDER, INGENIERÍA, DISEÑO INDUSTRIAL O MECÁNICO, PATRONAJE
        # La esposa de Jack hace estrictamente DISEÑO GRÁFICO 2D (Photoshop, Illustrator, logos, marcas, banners, flyers, trípticos, identidad visual)
        # 0. EXCLUSIÓN TOTAL: DISEÑO DE INTERIORES, ARQUITECTURA FÍSICA/CONSTRUCCIÓN, 3D, MODELADO, RENDER, INGENIERÍA, DISEÑO INDUSTRIAL O MECÁNICO, PATRONAJE
        # La esposa de Jack hace estrictamente DISEÑO GRÁFICO 2D (Photoshop, Illustrator, logos, marcas, banners, flyers, trípticos, identidad visual)
        interior_arch_3d_patterns = [
            r"\b(?:diseñ[oó]\s+de\s+interiores?|diseñador[a]?\s+de\s+interiores?|interior\s+design(?:er)?|interiorismo)\b",
            r"\b(?:diseñ[oó]\s+(?:de\s+)?(?:cocinas?|baños?|banos?|sal[oó]n(?:es)?|habitaci[oó]n|dormitorio|casas?|fachadas?|viviendas?|espacios\s+(?:interiores|f[ií]sicos|habitables)))\b",
            r"\b(?:cocina[s]?\s+y\s+sal[oó]n|cocina/sal[oó]n|isla\s+de\s+cocina|cocina\s+moderna)\b",
            r"\b(?:arquitectura\s+(?:de\s+interiores?|civil|residencial|habitacional|comercial)|estudio\s+de\s+arquitectura|planos?\s+arquitect[oó]nicos?|diseño\s+arquitect[oó]nico|proyecto\s+arquitect[oó]nico|levantamiento\s+arquitect[oó]nico)\b",
            r"\b(?:arquitecto|arquitecta)\s+(?:colegiado|de\s+interiores|de\s+obras?|de\s+edificaciones?|para\s+(?:casa|edificio|remodelaci[oó]n|obra))\b",
            r"\b(?:remodelaci[oó]n\s+(?:de\s+casas?|de\s+viviendas?|de\s+espacios|de\s+cocinas?|de\s+baños?)|decoraci[oó]n\s+de\s+interiores?|decorador[a]?\s+de\s+interiores?)\b",
            r"\b(?:muebles?|carpinter[ií]a|mobiliario|paisajismo|planos?\s+(?:de\s+casas?|arquitect[oó]nicos?|de\s+distribuci[oó]n\s+f[ií]sica))\b",
            r"\b(?:3d|3ds|modelado(?:\s*3d)?|render(?:s|ing|izado|izar)?(?:\s*3d)?|blender|autocad|sketchup|clo\s*3d|optitex|solidworks|revit|3ds\s*max|maya\s*3d|cinema\s*4d|zbrush)\b",
            r"\b(?:diseñ(?:o|ador|adora)\s+industrial|disen(?:o|ador|adora)\s+industrial|diseñ(?:o|ador|adora)\s+mec[aá]nic[ao]|patronaje|planos?\s+t[eé]cnicos?|despiece)\b"
        ]
        for pat in interior_arch_3d_patterns:
            if re.search(pat, text):
                return "excluded_interior_or_3d"

        # EXCLUSIÓN TOTAL: RECUPERACIÓN DE CUENTAS / CONTRASEÑAS / CUENTAS BANEADAS
        account_recovery_patterns = [
            r"\b(?:recover(?:y|ed)?|unfreeze|unban|restore|reactivat(?:e|ion))\s+(?:disabled\s+)?(?:gmail|google|facebook|instagram|tiktok|epfo|rockstar|email|account|password)\b",
            r"\b(?:recuperar|desbloquear|reactivar)\s+(?:cuenta|contrase[ñn]a|correo)\s+(?:de\s+)?(?:gmail|google|facebook|instagram|tiktok|redes|hackeada|bloqueada|suspendida)\b",
            r"\b(?:account\s+recovery|password\s+recovery|hacked\s+account|disabled\s+account|banned\s+account)\b",
            r"\b(?:recuperaci[oó]n\s+de\s+cuenta|cuenta\s+hackeada|cuenta\s+bloqueada|cuenta\s+inhabilitada)\b"
        ]
        for arpat in account_recovery_patterns:
            if re.search(arpat, text):
                return "excluded_account_recovery"

        # Verificación estricta de tags o habilidades del proyecto
        if skills:
            excluded_skills_terms = {
                "interior design", "architecture", "building architecture", "civil architecture",
                "landscape design", "home design", "structural engineering", "civil engineering",
                "architectural rendering", "3d rendering", "3d design", "3d modelling",
                "autocad", "sketchup", "revit", "solidworks", "fashion design",
                "video editing", "videography", "video production", "voice talent", "audio production"
            }
            for s in skills:
                s_str = str(s).lower().strip()
                # NUNCA excluir arquitectura de software, nube, web o sistemas
                if any(tech in s_str for tech in ["software", "system", "cloud", "solution", "enterprise", "data", "network", "web", "information"]):
                    continue
                if s_str in excluded_skills_terms or any(term in s_str for term in ["interior design", "building architect", "civil architect", "3d render", "3d design", "autocad", "sketchup"]):
                    return "excluded_interior_or_3d"

        # 0.5. PRIORIDAD ABSOLUTA AL TÍTULO PARA DISEÑO GRÁFICO 2D (Esposa de Jack)
        # Asegura que un tríptico, folleto, logo o flyer que mencione "página web" dentro de su contenido
        # NUNCA sea clasificado erróneamente como desarrollo web.
        graphic_title_pattern = (
            r"\b(?:tr[ií]ptico[s]?|folleto[s]?|diseñ[oó]\s+gr[aá]fic[ao]|logotipo[s]?|logos?|"
            r"banners?|flyers?|branding|identidad\s+visual|vectorizar|logo\s+design|graphic\s+design|"
            r"tarjetas?\s+de\s+presentaci[oó]n|maquetaci[oó]n\s+editorial|invitaci[oó]n(?:es)?|"
            r"piezas?\s+gr[aá]ficas?|photoshop|illustrator|manual\s+de\s+(?:marca|identidad)|"
            r"diseñador[a]?\s+gr[aá]fic[ao])\b"
        )
        if re.search(graphic_title_pattern, t_low) and not any(w in t_low for w in ["sitio web", "pagina web", "página web", "desarrollo web", "programador", "wordpress", "landing page"]):
            return "graphic_design_creative"

        # 0.1. EXCLUSIÓN TOTAL: GESTIÓN DE PROPIEDADES, ALOJAMIENTOS, AIRBNB, HOSPITABLE, VRBO, BOOKING, LISTINGS
        property_rental_patterns = [
            r"\b(?:airbnb|hospitable|vrbo|booking\.com|superhost|alquiler\s+vacacional|propiedades\s+activas|listings?\s+(?:de\s+)?airbnb)\b",
            r"\b(?:gesti[oó]n\s+de\s+propiedades|sincronizaci[oó]n\s+de\s+calendario\s+e\s+inventario|anuncios?\s+(?:en|de)\s+airbnb)\b",
            r"\b(?:propiedades\s+en\s+airbnb|listings\s+airbnb|app\s+hospitable)\b"
        ]
        for pat in property_rental_patterns:
            if re.search(pat, text):
                return "excluded_property_management"

        # 0.2. EXCLUSIÓN TOTAL: ASISTENCIA VIRTUAL ADMINISTRATIVA, SECRETARIADO, DIGITACIÓN, AGENDA
        va_patterns = [
            r"\b(?:asistente\s+virtual|virtual\s+assistant|secretaria|secretario|data\s+entry|transcripci[oó]n|transcripcion|llenar\s+(?:excel|formularios))\b",
            r"\b(?:gesti[oó]n\s+de\s+agenda|gestion\s+de\s+agenda|agendar\s+citas|recepcionista|recepcionista\s+virtual)\b"
        ]
        for pat in va_patterns:
            if re.search(pat, text) and not any(w in t_low for w in ["sitio web", "pagina web", "software", "python", "scraping", "api"]):
                return "virtual_assistant_admin"

        # 0.3. EXCLUSIÓN TOTAL: VENTAS, TELEMARKETING, CAPTACIÓN DE CLIENTES, LEAD GEN, ADS / PUBLICIDAD, CLOSER, SETTER
        # Jack es Ingeniero de Sistemas (Desarrollo, QA, Datos, Soporte TI, Bots y Scraping) y su esposa Diseñadora Gráfica 2D.
        # NUNCA clasificar ni postular a proyectos de captación comercial, telemarketing, ventas o campañas de anuncios pagos.
        sales_marketing_exclusion_patterns = [
            r"\b(?:telemarketing|cold\s*calling|llamadas?\s+(?:en\s+fr[ií]o|telef[oó]nicas?|de\s+ventas?))\b",
            r"\b(?:captaci[oó]n\s+(?:de\s+)?(?:clientes|leads|prospectos)|captar\s+(?:clientes|leads|prospectos)|conseguir\s+(?:clientes|leads))\b",
            r"\b(?:lead\s+generation|generaci[oó]n\s+de\s+leads|generar\s+leads|prospecci[oó]n\s+(?:comercial|b2b)?)\b",
            r"\b(?:appointment\s+setter|setter\s+de\s+ventas|closer\s+de\s+ventas|cerrador\s+de\s+ventas|cold\s+caller)\b",
            r"\b(?:b2b\s+marketing|marketing\s+b2b|campa[ñn]as?\s+(?:de\s+)?(?:google\s+ads|meta\s+ads|facebook\s+ads))\b",
            r"\b(?:google\s+ads|meta\s+ads|facebook\s+ads|tr[aá]fico\s+pago|media\s+buyer|gesti[oó]n\s+de\s+anuncios)\b",
            r"\b(?:anuncios\s+y\s+contenido|campa[ñn]a\s+publicitaria|pauta\s+digital|anuncios\s+digitales)\b",
            r"\b(?:vender\s+(?:servicios|productos|software|saas)|comercial\s+para\s+saas|socio\s+comercial|ejecutivo\s+de\s+ventas)\b",
            r"\b(?:lead\s+magnet|sistema\s+de\s+captaci[oó]n|embudo\s+de\s+ventas|funnel\s+de\s+ventas)\b",
            r"\b(?:conseguir\s+esos\s+primeros\s+clientes|clientes\s+de\s+pago|contratos\s+firmados|demostraciones\s+agendadas)\b"
        ]
        is_dev_code = any(tech in text for tech in [
            "script python", "script en python", "desarrollo web", "programador", "backend",
            "api rest", "fastapi", "react", "wordpress", "php", "base de datos", "sql", "qa", "software"
        ]) and any(action in text for action in [
            "programar", "desarrollar", "crear código", "codificar", "construir api", "integrar api", "implementar webhook", "corregir bug"
        ])
        if not is_dev_code:
            for pat in sales_marketing_exclusion_patterns:
                if re.search(pat, text):
                    return "excluded_sales_and_marketing"

        if skills and not is_dev_code:
            excluded_sales_skills = {
                "telemarketing", "sales", "sales management", "lead generation", "b2b marketing",
                "cold calling", "appointment setting", "google ads", "facebook ads", "meta ads",
                "advertising", "market research", "email marketing", "social media marketing"
            }
            matching_sales_skills = [str(s).lower().strip() for s in skills if str(s).lower().strip() in excluded_sales_skills]
            if len(matching_sales_skills) >= 1 and not any(dev_s in [str(s).lower().strip() for s in skills] for dev_s in ["php", "python", "javascript", "react", "html", "css", "sql", "c#", "java"]):
                return "excluded_sales_and_marketing"

        # 1. Web Scraping & Extracción con Python (Prioridad sobre 'web' genérico)
        if any(w in t_low for w in ["extraer lista", "scraping", "scraper", "crawling", "extraer datos", "scrapear", "script python"]) or any(w in text for w in [
            "scraping", "scraper", "crawling", "extraer datos", "extracción de datos", "extraccion de datos",
            "extraer lista", "extraer contactos", "extraer correos", "script python", "script en python",
            "playwright", "selenium", "beautifulsoup", "scrapear", "automatización con python"
        ]):
            return "python_automation_scraping"

        # 2. Desarrollo Web & Frontend (PHP, MySQL, WordPress, Landing pages, React, Angular, Vue)
        # NUNCA clasificar proyectos de ventas comerciales, marketing o anuncios como desarrollo web
        sales_triggers_dev_check = [
            "ventas", "vendedor", "comercial", "closer", "setter", "prospección", "prospeccion",
            "telemarketing", "llamadas en frío", "llamadas en frio", "captación de clientes",
            "captacion de clientes", "lead generation", "google ads", "meta ads", "anuncios y contenido"
        ]
        if not any(sw in text for sw in sales_triggers_dev_check):
            if any(w in t_low for w in [
                "landing page", "wordpress", "hostinger", "sitio web", "pagina web", "página web", "desarrollo web",
                "react", "frontend", "front end", "angular", "vue", "maquetación web", "maquetacion web", "php y mysql",
                "plataforma web", "sistema web", "cotizador web", "desarrollo saas", "desarrollar saas", "plataforma saas",
                "rediseño web", "actualizacion web", "actualización web"
            ]) or any(w in text for w in [
                "wordpress", "hostinger", "landing page", "elementor", "gutenberg",
                "desarrollo web", "página web", "pagina web", "frontend", "front end", "sitio web",
                "angular", "react", "vue.js", "desarrollador web", "programador web", "creacion de pagina web",
                "creación de página web", "crear pagina web", "rediseño de pagina", "rediseno de pagina"
            ]):
                return "web_dev"

        # 2.5. Chatbots, Bots de WhatsApp & Sistemas de Automatización con APIs (Jack)
        # NUNCA clasificar trabajos de atención humana / operador de chat / call center como desarrollo de bots
        human_chat_triggers = [
            "atienda mis conversaciones", "atender conversaciones", "call center", "call centers",
            "operador de chat", "operadora de chat", "moderar chat", "atención de llamadas", "atencion de llamadas",
            "atender whatsapp web", "acceso a la línea de whatsapp web", "acceso a la linea de whatsapp web",
            "responder mensajes de uso personal", "mensajes de uso personal", "consultas de clientes y mensajes personales"
        ]
        if any(w in text for w in human_chat_triggers):
            return "customer_support_whatsapp"

        # Solo clasificar como ai_chatbot_system si hay contexto real de software, programación o APIs de bots
        chatbot_tech_terms = [
            "bot whatsapp", "chatbot", "bot de whatsapp", "bot de telegram", "bot telegram",
            "whatsapp cloud api", "whatsapp business api", "twilio", "flujo manychat", "manychat",
            "typebot", "voiceflow", "botpress", "crear bot", "desarrollo de bot", "desarrollar chatbot",
            "bot con ia", "chatbot con ia", "agente ia", "asistente con ia", "bot faq", "chatbot gpt"
        ]
        if any(w in t_low for w in chatbot_tech_terms) or any(w in text for w in chatbot_tech_terms):
            return "ai_chatbot_system"

        # 3. Asistencia Virtual, Gestión de Agenda & Operaciones (Manual / Humano)
        if not any(bw in text for bw in ["bot", "chatbot", "typebot", "manychat", "script", "api", "automatiz", "python"]):
            if any(w in t_low for w in ["asistente virtual", "virtual assistant", "asistente administrativo", "secretaria", "recepcionista virtual"]) or any(w in text for w in [
                "asistente virtual", "virtual assistant", "asistente administrativo", "gestión de agenda", "gestion de agenda",
                "agendar citas", "gestión de citas", "gestion de citas", "gestion de correos", "data entry", "transcripción", "agenda digital"
            ]):
                return "virtual_assistant_admin"

        # 3.5. Video, Reels, Motion Graphics y Edición Audiovisual (Excluido de Diseño Gráfico)
        # Nota: Usamos límites regex o frases compuestas para no colisionar con 'freelancer'
        if any(w in t_low for w in [
            "video", "videos", "tiktok video", "editor de video", "edicion de video",
            "edición de video", "creación de videos", "creacion de videos", "after effects", "premiere",
            "premiere pro", "mogrt", "motion graphics", "capcut", "animacion de video", "intro animado", "intro animada"
        ]) or any(w in text for w in [
            "edición de video", "edicion de video", "editor de video", "editora de video", "cortar videos",
            "after effects", "premiere pro", "capcut", "motion graphics", "mogrt", "crear videos"
        ]) or bool(re.search(r'\b(?:reels?|tiktok)\b', t_low)):
            return "video_production_editing"

        # 4. Diseño Gráfico, Logotipos, Photoshop, Illustrator, Branding & Editorial (Esposa de Jack)
        # ESTRICTAMENTE DISEÑO GRÁFICO 2D: Límites de palabra exactos sobre título y descripción
        graphic_strict_patterns = [
            r"\b(?:diseñ[oó]\s+gr[aá]fico|diseñador[a]?\s+gr[aá]fic[ao])\b",
            r"\b(?:logotipo[s]?|logos?|isotipo[s]?|imagotipo[s]?|diseñ[oó]\s+de\s+logos?|creaci[oó]n\s+de\s+logos?)\b",
            r"\b(?:banners?|flyers?|branding|identidad\s+visual|identidad\s+de\s+marca|manual\s+de\s+marca|manual\s+de\s+identidad)\b",
            r"\b(?:vectorizar|vectorizaci[oó]n|vectores|logo\s+design|graphic\s+design)\b",
            r"\b(?:tarjetas?\s+de\s+presentaci[oó]n|tr[ií]ptico[s]?|d[ií]ptico[s]?|folletos?|brochure[s]?)\b",
            r"\b(?:photoshop|illustrator|retoque\s+fotogr[aá]fico|edici[oó]n\s+en\s+photoshop)\b",
            r"\b(?:piezas?\s+gr[aá]ficas?|artes?\s+para\s+redes?|diseñ[oó]\s+de\s+afiche[s]?|diseñ[oó]\s+de\s+cartel(?:es)?)\b",
            r"\b(?:etiquetas?\s+de\s+producto|diseñ[oó]\s+de\s+empaque[s]?|packaging\s+design|invitaci[oó]n(?:es)?|maquetaci[oó]n\s+para\s+kdp)\b"
        ]
        title_and_desc = f"{title} {description}".lower()
        if not any(sw in t_low for sw in ["bot", "scraping", "python", "software", "api", "sistema", "desarrollo web", "wordpress", "prestashop", "shopify", "convertidor", "frecuencia", "aeronáutico", "aeronautico", "minecraft", "electrónica", "electronica", "circuito"]):
            for gpat in graphic_strict_patterns:
                if re.search(gpat, title_and_desc):
                    return "graphic_design_creative"

        # 5. Redes Sociales, Instagram, TikTok, Reels & Marketing Digital
        if any(w in t_low for w in ["instagram", "tiktok", "redes sociales", "community manager", "crecimiento ig", "crecimiento tiktok"]) or any(w in text for w in [
            "tiktok", "instagram", "community manager", "redes sociales", "crecimiento ig", "crecimiento tiktok",
            "parrilla de contenido", "estrategia de contenido", "seguidores reales", "engagement", "creador de contenido",
            "posts para instagram", "growth marketing", "social media", "crecer en instagram"
        ]) or bool(re.search(r'\breels?\b', t_low)):
            return "social_media_growth"

        # 6. E-Commerce & Tiendas Virtuales (Shopify, WooCommerce, Prestashop, Catálogo)
        if any(w in text for w in [
            "shopify", "woocommerce", "prestashop", "tienda online", "tienda virtual", "subir productos", "catalogo de productos",
            "mercado libre", "amazon fba", "dropshipping", "e-commerce", "ecommerce", "tiendanube", "magento", "opencart"
        ]):
            return "ecommerce_stores"

        # 7. Setter de Ventas & Agendamiento Comercial
        if any(w in text for w in [
            "setter", "asesoría fitness", "asesoria fitness", "llamadas de venta", "appointment setter",
            "agendar llamadas", "agendamiento de llamadas", "prospección", "prospeccion",
            "cold caller", "closer", "cerrador", "lead qualification", "cerrar ventas"
        ]):
            return "sales_setter_crm"

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

        # 11. QA Testing & Pruebas de Software / Usabilidad (Jack)
        if any(w in text for w in [
            "qa", "testing", "tester", "pruebas funcionales", "postman", "casos de prueba",
            "test cases", "reporte de bugs", "control de calidad", "smoke testing", "pruebas de regresion",
            "usabilidad", "usability", "ui/ux", "experiencia de uso", "interaction design",
            "user research", "pruebas de usuario", "auditoría de software", "auditoria funcional",
            "refinar usabilidad", "usabilidad de app", "revisar app", "probar app", "pruebas de software",
            "calidad de software", "bugs y errores", "depuración funcional"
        ]) or any(w in t_low for w in ["usabilidad", "testing", "qa", "pruebas de app", "refinar app"]):
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
                    # Cotizar en el percentil superior del rango del cliente (valorizar el conocimiento técnico)
                    suggested_rate = int(round(min_v + (max_v - min_v) * 0.85))
            else:
                defaults_hourly = {
                    "python_automation_scraping": 28,
                    "web_dev": 25,
                    "ecommerce_stores": 25,
                    "sql_database": 25,
                    "ai_chatbot_system": 28,
                    "graphic_design_creative": 22,
                    "qa_testing": 22,
                    "power_bi_data": 28
                }
                suggested_rate = defaults_hourly.get(category, 25)

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
                # Cotización inteligente de alto valor: maximizar ganancias sin quedar fuera del rango
                if max_v <= 100:
                    target = int(round(min_v + (max_v - min_v) * 0.85))
                elif max_v <= 300:
                    target = int(round(min_v + (max_v - min_v) * 0.70))
                elif max_v <= 800:
                    target = int(round(min_v + (max_v - min_v) * 0.70))
                else:
                    target = int(round(min_v + (max_v - min_v) * 0.65))

            # Plazo de entrega según envergadura
            if max_v <= 100:
                timeline = "24 a 48 horas"
            elif max_v <= 300:
                timeline = "3 a 4 días hábiles"
            elif max_v <= 800:
                timeline = "4 a 6 días hábiles"
            else:
                timeline = "1 a 2 semanas"

            suggested_bid = f"{curr_symbol}{target} {currency}"
            suggested_timeline = timeline
        else:
            defaults_fixed = {
                "web_dev": (f"{curr_symbol}220 {currency}", "3 a 5 días hábiles"),
                "ecommerce_stores": (f"{curr_symbol}240 {currency}", "4 a 6 días hábiles"),
                "python_automation_scraping": (f"{curr_symbol}140 {currency}", "48 horas"),
                "sql_database": (f"{curr_symbol}120 {currency}", "48 horas"),
                "ai_chatbot_system": (f"{curr_symbol}320 {currency}", "5 a 7 días"),
                "graphic_design_creative": (f"{curr_symbol}120 {currency}", "24 a 48 horas"),
                "power_bi_data": (f"{curr_symbol}160 {currency}", "3 días hábiles"),
                "qa_testing": (f"{curr_symbol}110 {currency}", "48 horas")
            }
            suggested_bid, suggested_timeline = defaults_fixed.get(category, (f"{curr_symbol}180 {currency}", "3 a 4 días"))

        return {
            "suggested_bid": suggested_bid,
            "suggested_timeline": suggested_timeline,
            "is_hourly": False,
            "currency": currency
        }

    def _call_external_llm(self, prompt: str, system_instructions: str = None) -> Optional[str]:
        """
        Invoca APIs en la nube de ultra baja latencia y CERO consumo de CPU local:
        1. Groq Cloud (Llama 3.3 70B Versatile en LPUs ultra veloces: 0.3s, 0% CPU local).
        2. Google Gemini 2.5 Flash (Cloud API: 0.8s, 0% CPU local).
        3. OpenRouter Cloud (DeepSeek / Qwen en la nube: 0% CPU local).
        4. Fallback directo a plantillas cognitivas determinísticas de alta fidelidad (0% CPU).

        PROTECCIÓN TÉRMICA Y SILENCIO TOTAL:
        Cero llamadas a Ollama local en CPU para garantizar ventiladores silenciosos y cero recalentamiento.
        """
        # 1. Intentar con Groq Cloud (Ultra veloz: ~0.3s, 0% CPU local)
        if self.groq_key:
            try:
                messages = []
                if system_instructions:
                    messages.append({"role": "system", "content": system_instructions})
                messages.append({"role": "user", "content": prompt})

                req_data = json.dumps({
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
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
                with urllib.request.urlopen(req, timeout=8) as response:
                    res_json = json.loads(response.read().decode())
                    text = res_json["choices"][0]["message"]["content"].strip()
                    if len(text) > 80:
                        return text
            except Exception as e:
                pass

        # 2. Intentar con Gemini Cloud (~0.8s, 0% CPU local)
        if self.gemini_client:
            try:
                full_contents = f"{system_instructions}\n\n{prompt}" if system_instructions else prompt
                resp = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_contents
                )
                text = (resp.text or "").strip()
                if len(text) > 80:
                    return text
            except Exception as e:
                pass

        # 3. Intentar con OpenRouter Cloud (~1.2s, 0% CPU local)
        if self.openrouter_key:
            try:
                messages = []
                if system_instructions:
                    messages.append({"role": "system", "content": system_instructions})
                messages.append({"role": "user", "content": prompt})

                req_data = json.dumps({
                    "model": "deepseek/deepseek-chat",
                    "messages": messages,
                    "temperature": 0.4
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/chat/completions",
                    data=req_data,
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://miam.com.pe",
                        "X-Title": "JobHunter-AI"
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_json = json.loads(response.read().decode())
                    text = res_json["choices"][0]["message"]["content"].strip()
                    if len(text) > 80:
                        return text
            except Exception as e:
                pass

        return None

    def generate_proposal(self, title: str, description: str, client_name: str = "Estimado cliente", budget: str = "", language: str = "auto") -> Dict[str, Any]:
        """
        Genera una propuesta comercial personalizada, detallada y de alto impacto en ESPAÑOL o INGLÉS.
        Cumple estrictamente las Reglas de Oro:
        1. Lee el brief detalle a detalle reconociendo requerimientos específicos y preguntas obligatorias.
        2. Si el cliente pide cotizar escenarios específicos (Escenario 1, Escenario 2), los responde directamente.
        3. Nunca pregunta por cosas que el cliente ya aclaró en el brief.
        4. No usa clichés de IA ni textos genéricos.
        5. Cierre 100% dentro del chat de la plataforma.
        """
        category = self.categorize_project(title, description)
        estimates = self.estimate_bid_and_time(budget, category, f"{title} {description}")

        suggested_bid = estimates["suggested_bid"]
        timeline = estimates["suggested_timeline"]
        is_hourly = estimates.get("is_hourly", False)
        github_url = "https://github.com/JackMBerrocal"

        # Detección de idioma
        is_english = False
        if language == "en":
            is_english = True
        elif language == "es":
            is_english = False
        else:
            detect_text = f" {title} {description} ".lower()
            en_words = [" the ", " to ", " and ", " is ", " for ", " in ", " with ", " looking for ", " need ", " we have ", " app ", " website ", " project ", " build ", " create "]
            es_words = [" el ", " la ", " de ", " en ", " y ", " que ", " para ", " con ", " busco ", " necesito ", " proyecto ", " desarrollo ", " página "]
            en_c = sum(1 for w in en_words if w in detect_text)
            es_c = sum(1 for w in es_words if w in detect_text)
            is_english = en_c > es_c

        # Detección de palabra clave obligatoria (ej: "escribe al inicio FIT" / "write FIT at the start")
        codeword_prefix = ""
        cw_match = re.search(r'(?:escribe|incluye|pon|palabra|write|include|start with|keyword)\s+(?:al inicio|al principio|en tu propuesta|the word)?\s*[\“\"\'\‘]([a-zA-Z0-9_\-]+)[\”\"\'\’]', description, re.IGNORECASE)
        if cw_match:
            codeword_prefix = f"[{cw_match.group(1).upper()}]\n\n"

        # 1. Definir Persona y Prompt Específico para la IA
        is_design = (category == "graphic_design_creative")
        if is_english:
            if is_design:
                sys_inst = (
                    "You are a Senior Creative Graphic Designer (Adobe Illustrator, Photoshop, Branding, Visual Identity, Vector Art, Print & Digital). "
                    "Your objective is to write compelling, human, and professional proposals for design clients on Freelancer.com.\n\n"
                    "CRITICAL WRITING RULES:\n"
                    "1. MANDATORY GRAMMAR: Always write in FIRST PERSON SINGULAR ('I will design...', 'I will create...', 'I have extensive experience in...'). NEVER write in second person ('You will...').\n"
                    "2. FORMAT: Freelancer.com DOES NOT support Markdown. STRICTLY FORBIDDEN to use asterisks (** or *). Use clean plain text with clear paragraphs and simple dashes (-) for lists.\n"
                    "3. GREETING: Natural, direct and warm ('Hi there', 'Hello!'). NEVER use robotic AI clichés like 'I hope this finds you well' or 'I am thrilled to apply'.\n"
                    "4. MANDATORY CONSULTATIVE QUESTIONS: Include at least 2 creative/design questions before closing to start the chat discussion.\n"
                    "5. STRICT PLATFORM CLOSE: Invite the client to share details and references through the Freelancer.com chat. All project coordination is 100% via chat without external calls."
                )
            else:
                sys_inst = (
                    "You are Jack Michael Berrocal (@jmberrocale), a Systems Engineer and Senior Full-Stack Developer (Python, JavaScript, React, Node.js, FastAPI, APIs, SQL, QA Testing, Automation). "
                    "Your objective is to write compelling, technically rigorous, natural, and human proposals for clients on Freelancer.com.\n\n"
                    "CRITICAL WRITING RULES:\n"
                    "1. MANDATORY GRAMMAR: Always write in FIRST PERSON SINGULAR ('I will...', 'I have built...', 'I specialize in...', 'I can implement...'). NEVER write in second person ('You will create...', 'You should...').\n"
                    "2. FORMAT: Freelancer.com DOES NOT support Markdown. STRICTLY FORBIDDEN to use asterisks (** or *). DO NOT use hashtags (#). Use clean plain text with clear, readable paragraphs and simple dashes (-) for bullet points.\n"
                    "3. GREETING: Natural, direct and professional ('Hi [Name]', 'Hello there', or straight to the technical solution). NEVER use robotic AI clichés like 'I hope this proposal finds you well', 'I am thrilled to apply', or 'Dear client'.\n"
                    "4. MANDATORY CONSULTATIVE QUESTIONS: ALWAYS include a dedicated section before closing with at least 2 sharp, direct technical questions to invite the client to reply in the chat.\n"
                    "5. BUDGET & VALUE: Justify the reference quote ({suggested_bid}) by demonstrating solid technical competence and clear deliverables.\n"
                    "6. STRICT PLATFORM CLOSE: Invite the client to coordinate all technical details directly through the Freelancer.com chat. 100% chat-based delivery with no external meetings required."
                )

            ai_prompt = f"""FREELANCER.COM PROJECT:
Title: {title}
Client Budget: {budget or "To be discussed"}
Reference Estimate: {suggested_bid}
Delivery Timeline: {timeline}

CLIENT BRIEF:
{description}

INSTRUCTIONS:
Write a winning technical proposal for this project in ENGLISH.
- Write STRICTLY in FIRST PERSON singular ('I will handle...', 'I will build...').
- Include at least 2 sharp consultative technical questions at the end to prompt a chat response.
- Plain text only, NO markdown asterisks (**).
- Concise (3-4 short paragraphs), human, technically sharp, focused on solving the client requirement.
"""
        else:
            if is_design:
                sys_inst = (
                    "Eres una Diseñadora Gráfica Profesional y Creativa Senior (Adobe Illustrator, Photoshop, Branding, Identidad Visual y Editorial). "
                    "Tu objetivo es redactar propuestas comerciales impecables, directas, criteriosas y humanas para clientes en Freelancer.com.\n\n"
                    "REGLAS CRÍTICAS DE REDACCIÓN:\n"
                    "1. GRAMÁTICA OBLIGATORIA: Escribe SIEMPRE en PRIMERA PERSONA DEL SINGULAR ('Me encargaré de...', 'Desarrollaré...', 'Diseñaré...', 'Puedo crear...', 'Cuento con experiencia en...'). NUNCA escribas en segunda persona ('Crearás...', 'Diseñarás...') ni le des órdenes al cliente.\n"
                    "2. FORMATO: Freelancer.com NO soporta Markdown. TOTALMENTE PROHIBIDO usar asteriscos (** ni *). NO uses almohadillas (#). Escribe en texto plano limpio con párrafos legibles y viñetas simples con guion (-).\n"
                    "3. SALUDO: Saluda de forma natural y cercana ('Hola, qué tal', 'Hola [Nombre]' o entra directo al grano). NUNCA uses clichés robóticos como 'Gracias por tu interés en mi perfil', 'Entiendo completamente tu requerimiento', 'Me complace escuchar...' ni 'Estimado cliente'.\n"
                    "4. PREGUNTAS CONSULTIVAS OBLIGATORIAS: Incluye SIEMPRE antes del cierre un apartado con al menos 2 preguntas técnicas o creativas directas para invitar al cliente a responder por el chat.\n"
                    "5. NUNCA inventes 'Escenario 1' ni 'Escenario 2' salvo que el cliente haya pedido explícitamente cotizar escenarios en su anuncio.\n"
                    "6. Cierre profesional invitando a coordinar por el chat de la plataforma Freelancer.com."
                )
            else:
                sys_inst = (
                    "Eres Jack Michael Berrocal (@jmberrocale), Ingeniero de Sistemas y Desarrollador Full-Stack (Python, JavaScript, React, WordPress, APIs, SQL). "
                    "Tu objetivo es redactar propuestas técnicas directas, profesionales y de alto valor para clientes en Freelancer.com.\n\n"
                    "REGLAS CRÍTICAS DE REDACCIÓN:\n"
                    "1. GRAMÁTICA OBLIGATORIA: Escribe SIEMPRE en PRIMERA PERSONA DEL SINGULAR ('Me encargaré de...', 'Desarrollaré...', 'Implementaré...', 'Configuraré...', 'Tengo experiencia en...'). ESTÁ TOTALMENTE PROHIBIDO conjugar en segunda persona ('Conectarás...', 'Redactarás...', 'Publicarás...', 'Harás...') porque suena a darle órdenes al cliente.\n"
                    "2. FORMATO: Freelancer.com NO soporta Markdown. TOTALMENTE PROHIBIDO usar asteriscos (** ni *). NO uses almohadillas (#). Escribe en texto plano limpio con párrafos legibles y viñetas simples con guion (-).\n"
                    "3. SALUDO: Saluda de forma natural y profesional ('Hola, qué tal', 'Hola [Nombre]' o directo a la propuesta). NUNCA uses clichés robóticos como 'Gracias por tu interés en mi perfil', 'Entiendo completamente tu requerimiento', 'Me complace escuchar...' ni 'Estimado cliente'.\n"
                    "4. PREGUNTAS CONSULTIVAS OBLIGATORIAS: Incluye SIEMPRE antes del cierre un apartado con al menos 2 preguntas técnicas o consultivas directas basadas en el proyecto para invitar al cliente a responder en el chat.\n"
                    "5. PRESUPUESTO Y VALOR: Justifica la cotización de referencia planteada ({suggested_bid}) demostrando alta competencia técnica y entregables concretos.\n"
                    "6. NUNCA inventes 'Escenario 1' ni 'Escenario 2' salvo que el cliente haya pedido explícitamente cotizar escenarios en su anuncio.\n"
                    "7. Cierre directo invitando a coordinar los detalles técnicos por el chat de Freelancer.com."
                )

            scenario_note = ""
            if "escenario" in description.lower():
                scenario_note = "\n- El cliente solicita cotizar escenarios específicos en su brief. Responde punto por punto a lo solicitado."

            ai_prompt = f"""PROYECTO FREELANCER.COM:
Título: {title}
Presupuesto del cliente: {budget or "A convenir"}
Cotización de referencia: {suggested_bid}
Plazo de referencia: {timeline}

ANUNCIO DEL CLIENTE:
{description}

INSTRUCCIÓN:
Redacta la propuesta para postular a este proyecto.
- Escribe SIEMPRE en PRIMERA PERSONA del singular ('Me encargaré...', 'Desarrollaré...'). NUNCA en segunda persona ('Conectarás...').
- OBLIGATORIO: Incluye al final MÍNIMO 2 preguntas consultivas específicas para iniciar la conversación por el chat.
- NO uses asteriscos (** ni *) porque en Freelancer.com se muestran como caracteres rotos.
- NO uses clichés robóticos ('Gracias por tu interés en mi perfil', 'Entiendo completamente tu requerimiento', 'Me complace escuchar...', 'Estimado cliente', etc.).
- Mensaje conciso (3 a 5 párrafos breves), humano, técnico y enfocado en resolver exactamente lo que el cliente pide.{scenario_note}
"""

        proposal_text = None
        try:
            llm_res = self._call_external_llm(ai_prompt, system_instructions=sys_inst)
            if llm_res and len(llm_res.strip()) > 80:
                proposal_text = strip_all_emojis(llm_res.strip())
        except Exception as e:
            print(f"[ProposalGenerator] LLM call error: {e}")

        # Fallback determinístico avanzado si la IA no estuviera disponible
        if not proposal_text:
            if is_english:
                proposal_text = self._generate_cognitive_proposal_en(
                    title=title,
                    description=description,
                    category=category,
                    suggested_bid=suggested_bid,
                    timeline=timeline,
                    is_hourly=is_hourly,
                    budget=budget,
                    github_url=github_url
                )
            else:
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
            proposal_text = strip_all_emojis(proposal_text)

        # Safeguard estricto: Asegurar que la propuesta contenga al menos 2 preguntas consultivas
        if is_english:
            if proposal_text.count("?") < 2:
                en_questions_map = {
                    "web_dev": (
                        "\n\nTo ensure the optimal technical setup, I would like to ask:\n"
                        "1. Do you already have the hosting/domain infrastructure configured, or would you like recommendations?\n"
                        "2. Do you have wireframes or design references ready, or should we refine them in chat?"
                    ),
                    "python_automation_scraping": (
                        "\n\nTo calibrate the extraction pipeline:\n"
                        "1. Do the target sources require login authentication, dynamic pagination, or anti-bot handling?\n"
                        "2. Would you prefer the output in structured CSV/Excel format, or directly integrated into a database/API?"
                    ),
                    "qa_testing": (
                        "\n\nTo tailor the testing scope:\n"
                        "1. Which devices, operating systems, or browsers are your highest priority for this test run?\n"
                        "2. Would you prefer bug reports in a structured spreadsheet or directly logged into a tracker like Jira/Trello?"
                    ),
                    "sql_database": (
                        "\n\nTo structure the best database solution:\n"
                        "1. What is the specific database engine (PostgreSQL, MySQL, SQLite) and estimated data volume?\n"
                        "2. Are you looking for optimized query scripts, or also schema indexing and stored procedures?"
                    ),
                    "graphic_design_creative": (
                        "\n\nTo align on your visual concept:\n"
                        "1. Do you have existing brand guidelines or color palettes to follow, or should we explore new concepts?\n"
                        "2. What specific export formats and dimensions do you need for final delivery?"
                    ),
                    "it_support": (
                        "\n\nTo plan the support configuration:\n"
                        "1. What is the current server/OS environment (Ubuntu, Debian, CentOS, Windows)?\n"
                        "2. Do you have existing configuration documentation or backups ready before making changes?"
                    )
                }
                proposal_text += en_questions_map.get(category, (
                    "\n\nTo get started smoothly:\n"
                    "1. When are you looking to have this completed?\n"
                    "2. Would you like to discuss the technical specifics in chat so I can begin right away?"
                ))
        else:
            if proposal_text.count("?") < 2:
                questions_map = {
                    "web_dev": (
                        "\n\nPara definir la mejor estrategia técnica, me gustaría consultarte:\n"
                        "1. ¿Cuentas ya con el servicio de hosting y dominio configurado, o requieres recomendación sobre la mejor infraestructura?\n"
                        "2. ¿Tienes definida la estructura y contenidos de cada sección, o requieres apoyo en la organización de la información?"
                    ),
                    "ecommerce_stores": (
                        "\n\nPara avanzar de forma precisa:\n"
                        "1. ¿Tienes definido el catálogo de productos con sus imágenes y precios en algún archivo estructurado (Excel o CSV)?\n"
                        "2. ¿Qué pasarelas de pago y operadores logísticos tienes previsto integrar para tu mercado objetivo?"
                    ),
                    "python_automation_scraping": (
                        "\n\nPara calibrar la extracción y entrega:\n"
                        "1. ¿Los sitios de origen cuentan con autenticación previa, paginación dinámica o medidas anti-bot que debamos contemplar?\n"
                        "2. ¿Prefieres la entrega en una hoja estructurada de Excel/CSV o directamente sincronizada con una base de datos?"
                    ),
                    "sql_database": (
                        "\n\nPara estructurar la solución óptima:\n"
                        "1. ¿Cuál es el motor de base de datos específico (PostgreSQL, MySQL, SQLite) y el volumen aproximado de registros?\n"
                        "2. ¿Requieres únicamente los scripts DDL/consultas optimizadas o también la creación de índices y procedimientos almacenados?"
                    ),
                    "ai_chatbot_system": (
                        "\n\nPara definir la arquitectura ideal:\n"
                        "1. ¿Prefieres utilizar directamente la API oficial de WhatsApp Cloud de Meta o una plataforma intermediaria tipo Twilio?\n"
                        "2. ¿Te gustaría gestionar las respuestas y palabras clave desde una hoja vinculada en vivo o desde un panel dedicado?"
                    ),
                    "graphic_design_creative": (
                        "\n\nPara enfocar la propuesta visual:\n"
                        "1. ¿Tienes referencias de estilo, paleta de colores preferida o manual de identidad existente para mantener la coherencia?\n"
                        "2. ¿En qué dimensiones y formatos específicos necesitas la entrega final para impresión o difusión digital?"
                    )
                }
                extra_q = questions_map.get(category, (
                    "\n\nPara iniciar de forma precisa:\n"
                    "1. ¿Cuentas con especificaciones técnicas detalladas o material base para arrancar?\n"
                    "2. ¿Cuál es tu fecha límite ideal para tener esta primera versión funcionando?"
                ))
                if re.search(r'(?i)\bquedo\b', proposal_text):
                    parts = re.split(r'(?i)(?=\bquedo\b)', proposal_text, maxsplit=1)
                    proposal_text = parts[0].strip() + extra_q + "\n\n" + parts[1].strip()
                else:
                    proposal_text = proposal_text.strip() + extra_q

        return {
            "category": category,
            "suggested_bid": suggested_bid,
            "suggested_timeline": timeline,
            "is_hourly": is_hourly,
            "proposal_text": strip_all_emojis(codeword_prefix + proposal_text)
        }

    def _generate_cognitive_proposal_en(
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
        Generates high-impact English technical proposals for international clients.
        100% first-person singular, professional, human, and chat-based.
        """
        budget_mention = f" (within your {budget} budget)" if budget else ""
        commercial_note = f"Proposed rate: {suggested_bid}. Timeline: {timeline}." if is_hourly else f"Fixed quote: {suggested_bid}{budget_mention}. Delivery timeline: {timeline}."
        chat_close = "I am available right now via Freelancer chat to coordinate all details and start immediately. We can manage 100% of this project directly through this chat with no external calls needed."

        if category == "web_dev":
            return f"""Hi there! I reviewed your project "{title}" with great interest.

I am Jack Berrocal, a Systems Engineer and Full-Stack Web Developer. I specialize in building fast, responsive, and robust web applications with clean, maintainable code.

Here is how I will approach your project:
- Review your exact technical requirements and architecture.
- Implement the requested features with full responsiveness across desktop, tablet, and mobile.
- Thoroughly test functionality, user experience, and performance before delivery.
- Provide clean source code and complete deployment support.

Commercial reference: {commercial_note}

To tailor the technical approach:
1. Do you already have the hosting/domain infrastructure configured, or would you like recommendations?
2. Do you have wireframes or design references ready, or should we refine them in chat?

{chat_close}"""

        elif category == "python_automation_scraping":
            return f"""Hi! I specialize in Python automation, robust web scraping, and API integrations.

For "{title}", I can build a clean, efficient script that reliably handles data extraction with proper error handling and rate-limiting.

Deliverables:
- Well-structured Python automation script tailored to your exact target sources.
- Structured data delivery in CSV, Excel, JSON, or direct database sync.
- Anti-detection and pagination handling if required by the target site.
- Complete documentation so you can run the script effortlessly.

Commercial reference: {commercial_note}

To calibrate the pipeline:
1. Do the target sources require login authentication, dynamic pagination, or anti-bot handling?
2. Would you prefer the output in structured CSV/Excel format, or directly integrated into a database/API?

{chat_close}"""

        elif category == "qa_testing":
            return f"""Hello! As a Systems Engineer with a solid background in Software QA and Usability, I can thoroughly test your application and deliver actionable results.

For "{title}", I will execute methodical functional and user experience tests to identify bugs, edge cases, and areas of refinement.

Deliverables:
- Comprehensive test coverage across your prioritized workflows.
- Detailed bug reports with clear reproduction steps, screenshots, and severity ratings.
- Actionable usability feedback to improve user retention and flow.
- Structured summary report ready for your engineering team.

Commercial reference: {commercial_note}

To tailor the testing scope:
1. Which devices, operating systems, or browsers are your highest priority for this test run?
2. Would you prefer bug reports in a structured spreadsheet or directly logged into a tracker like Jira/Trello?

{chat_close}"""

        elif category == "sql_database":
            return f"""Hi! I specialize in database architecture, SQL optimization, and data engineering (PostgreSQL, MySQL, SQLite).

For "{title}", I can structure, optimize, or troubleshoot your database logic ensuring high performance and data integrity.

Deliverables:
- Clean, optimized SQL scripts and schema architecture.
- Indexing and query performance tuning to prevent bottlenecks.
- Stored procedures, triggers, or views as required.
- Full verification and testing of data consistency.

Commercial reference: {commercial_note}

To structure the best database solution:
1. What is the specific database engine and estimated data volume?
2. Are you looking for optimized query scripts, or also schema indexing and stored procedures?

{chat_close}"""

        elif category == "ai_chatbot_system":
            return f"""Hello! I build intelligent chatbots and workflow automations (WhatsApp Cloud API, Telegram, REST APIs).

For "{title}", I can set up a reliable, automated conversational system tailored to your specific interaction flow.

Deliverables:
- Complete conversational logic and message dispatch flow.
- Webhook endpoints and secure API integrations.
- Comprehensive end-to-end testing to verify response accuracy.
- Deployment support and clear administration guidance.

Commercial reference: {commercial_note}

To align on your automation logic:
1. Which platform or API provider will host the bot (WhatsApp Cloud API, Twilio, or another)?
2. Do you have a flowchart or specific FAQ responses already outlined?

{chat_close}"""

        elif category == "graphic_design_creative":
            return f"""Hello! I am a Creative Graphic Designer with extensive experience in Adobe Illustrator, Photoshop, branding, and visual identity.

For "{title}", I will create clean, high-impact, and original designs that elevate your brand and communicate your message effectively.

Deliverables:
- Creative, polished design concepts based on your requirements.
- High-resolution, print-ready and web-ready vector files (AI, PSD, PDF, PNG, SVG).
- Fast turnaround with dedicated revisions until you are 100% satisfied.

Commercial reference: {commercial_note}

To align on your visual concept:
1. Do you have existing brand guidelines or color palettes to follow, or should we explore new concepts?
2. What specific export formats and dimensions do you need for final delivery?

{chat_close}"""

        else:
            return f"""Hello! I am Jack Berrocal, a Systems Engineer with hands-on experience in full-stack development, automation, and technical problem-solving.

For "{title}", I can step in, analyze your requirements, and deliver a clean, reliable solution.

Deliverables:
- Methodical execution following software engineering best practices.
- Clear communication and timely updates throughout the project.
- Complete verification and deployment assistance.

Commercial reference: {commercial_note}

To get started smoothly:
1. When are you looking to have this completed?
2. Would you like to discuss the technical specifics in chat so I can begin right away?

{chat_close}"""

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
            commercial_block = f""" Modalidad de Trabajo & Tarifa:
• Tarifa Propuesta: {suggested_bid}.
• Disponibilidad: {timeline}.
• Control & Transparencia: Registro transparente de actividades, bitácora diaria de tareas cumplidas y total adaptación a tu franja horaria."""
        else:
            budget_mention = f" (dentro de tu presupuesto de {budget})" if budget else ""
            commercial_block = f""" Cotización Cerrada & Plazo Llave en Mano:
• Presupuesto Cerrado: {suggested_bid}{budget_mention}.
• Plazo de Entrega: {timeline} con puesta en producción.
• Garantía de Calidad: Incluye entrega de accesos, archivos fuente y una ronda de ajustes finales para certificar que cada sección quede exactamente como deseas."""

        closing_block = "Quedo disponible en este momento por el chat de la plataforma para resolver cualquier consulta y arrancar de inmediato. Coordinamos el 100% del proyecto por este chat, sin necesidad de llamadas externas ni pérdidas de tiempo. "

        # -------------------------------------------------------------
        # 1. DESARROLLO WEB & WORDPRESS / HOSTINGER / LANDING PAGES (Jack)
        # -------------------------------------------------------------
        if category == "web_dev":
            pages_desc = f"de {details['pages_count']} páginas" if details['pages_count'] else ""
            platform_desc = "en WordPress" if details['has_wordpress'] else "web moderna y responsiva"
            budget_txt = f"{suggested_bid}" if suggested_bid else "a convenir"

            return f"""¡Hola! Leí con atención tu requerimiento para "{title}".

Como desarrollador web full-stack, me especializo en construir sitios y landing pages limpias, rápidas y 100% optimizadas para celulares y computadoras {pages_desc} {platform_desc}.

Me enfoco en entregarte:
- Diseño moderno, fluido y alineado a tu marca (respetando guías, logos o textos que ya tengas).
- Formulario de contacto funcional, certificado SSL y optimización de velocidad de carga.
- Código ordenado y despliegue sin fallas sobre tu hosting para que quede publicado y listo para usar.

Mi cotización de referencia es de {budget_txt} con un plazo de entrega de {timeline}. Puedes ver proyectos reales y código comprobable en mi GitHub ({github_url}).

Para definir la mejor estrategia técnica, me gustaría consultarte:
1. ¿Cuentas ya con el servicio de hosting y dominio configurado, o requieres recomendación sobre la mejor infraestructura?
2. ¿Tienes definida la estructura y contenidos de cada sección, o requieres apoyo en la organización de la información?

Quedo atento por el chat de la plataforma para resolver cualquier duda técnica y comenzar."""

        # -------------------------------------------------------------
        # 2. E-COMMERCE & TIENDAS VIRTUALES (SHOPIFY / WOOCOMMERCE) (Jack)
        # -------------------------------------------------------------
        elif category == "ecommerce_stores":
            items_str = f"de los {details['products_count']} productos" if details['products_count'] else "de tus productos"
            budget_txt = f"{suggested_bid}" if suggested_bid else "a convenir"

            return f"""¡Hola! Revisé con atención tu proyecto para "{title}".

Puedo encargarme de la configuración y puesta a punto de tu tienda online (Shopify / WooCommerce) para que quede lista para vender de forma fluida y segura:

- Carga y organización {items_str} con sus variantes (tallas, colores), fotos y descripciones optimizadas.
- Integración segura de pasarelas de pago y configuración de tarifas/zonas de envío.
- Verificación exhaustiva del checkout para asegurar una compra móvil ágil y sin fricción.

Mi cotización de referencia es de {budget_txt} con plazo de {timeline}.

Para avanzar de forma precisa:
1. ¿Tienes definido el catálogo de productos con sus imágenes y precios en algún archivo estructurado (Excel o CSV)?
2. ¿Qué pasarelas de pago y operadores logísticos tienes previsto integrar para tu mercado objetivo?

Quedo disponible en el chat de Freelancer para coordinar los accesos o la lista de productos y arrancar."""

        # -------------------------------------------------------------
        # 3. WEB SCRAPING & AUTOMATIZACIÓN PYTHON (Jack)
        # -------------------------------------------------------------
        elif category == "python_automation_scraping":
            budget_txt = f"{suggested_bid}" if suggested_bid else "a convenir"

            return f"""¡Hola! Leí tu requerimiento técnico para "{title}".

Trabajo frecuentemente desarrollando scripts de extracción web y automatización en Python (Playwright, Requests, BeautifulSoup, Pandas), con código limpio, modular y manejo robusto de excepciones para que la extracción corra sin fallas:

- Script en Python documentado y listo para ejecutar en tu entorno.
- Exportación estructurada de los datos al formato que necesites (Excel estructurado, CSV o base de datos).
- Soporte para verificar que obtengas exactamente la información requerida.

Mi propuesta de referencia es de {budget_txt} con entrega en {timeline}. Proyectos de código y scripts comprobables en mi GitHub ({github_url}).

Para calibrar la extracción y entrega:
1. ¿Los sitios de origen cuentan con autenticación previa, paginación dinámica o medidas anti-bot que debamos contemplar?
2. ¿Prefieres la entrega en una hoja estructurada de Excel/CSV o directamente sincronizada con una base de datos?

Quedo disponible en el chat de la plataforma para revisar los enlaces o campos que necesitas extraer."""

        # -------------------------------------------------------------
        # 4. SQL & BASES DE DATOS (Jack)
        # -------------------------------------------------------------
        elif category == "sql_database":
            budget_txt = f"{suggested_bid}" if suggested_bid else "a convenir"

            return f"""¡Hola! Revisé tu necesidad técnica sobre "{title}".

Como Ingeniero de Sistemas, tengo amplia experiencia modelando esquemas relacionales y redactando consultas SQL optimizadas (PostgreSQL, MySQL, SQLite) con índices eficientes y tiempos de respuesta mínimos.

Te entrego los scripts limpios, comentados y listos para ejecutar sobre tu motor de base de datos.

Mi cotización de referencia es de {budget_txt} con entrega en {timeline}. Repositorios con proyectos prácticos disponibles en mi GitHub ({github_url}).

Para estructurar la solución óptima:
1. ¿Cuál es el motor de base de datos específico (PostgreSQL, MySQL, SQLite) y el volumen aproximado de registros?
2. ¿Requieres únicamente los scripts DDL/consultas optimizadas o también la creación de índices y procedimientos almacenados?

Quedo atento por el chat de la plataforma para revisar la estructura actual y avanzar."""

        # -------------------------------------------------------------
        # 4.5. CHATBOTS & SISTEMAS DE BOTS CON APIS (Jack)
        # -------------------------------------------------------------
        elif category == "ai_chatbot_system":
            budget_txt = f"{suggested_bid}" if suggested_bid else "a convenir"

            return f"""¡Hola! Revisé con atención los requerimientos de tu proyecto "{title}".

Como Ingeniero de Sistemas, desarrollo bots y flujos automatizados con código limpio (Python, WhatsApp Cloud API, Meta Graph API, Twilio o plataformas visuales) con alta disponibilidad y fácil mantenimiento para tu equipo:

- Configuración y conexión funcional del bot con manejo de eventos y palabras clave.
- Panel o archivo estructurado para que puedas actualizar respuestas y enlaces sin depender de un desarrollador.
- Guía práctica de uso y pruebas conjuntas para validar el flujo al 100%.

Mi cotización de referencia es de {budget_txt} con plazo de {timeline}. Código y proyectos prácticos verificables en mi GitHub ({github_url}).

Para afinar la arquitectura ideal:
1. ¿Tienes preferencia por utilizar directamente la API oficial de WhatsApp Cloud de Meta o una pasarela como Twilio?
2. ¿Te gustaría gestionar las respuestas y palabras clave desde una hoja en vivo (Google Sheets) o desde un panel web dedicado?

Quedo a tu disposición por el chat de la plataforma para coordinar los detalles e iniciar de inmediato."""

        # -------------------------------------------------------------
        # 5. DISEÑO GRÁFICO, PHOTOSHOP, ILUSTRACIÓN & BRANDING (Esposa de Jack)
        # -------------------------------------------------------------
        elif category == "graphic_design_creative":
            t_low = f"{title} {description}".lower()
            has_scenarios = any(w in t_low for w in ["escenario", "escenarios", "dos escenarios", "restyling", "pelada"])
            is_manual = any(w in t_low for w in ["manual", "manuales", "branding", "identidad visual", "guía de estilo"])
            budget_txt = f"{suggested_bid}" if suggested_bid else "a convenir"

            if has_scenarios or is_manual:
                return f"""¡Hola! Revisé con atención los detalles de tu búsqueda para "{title}".

Como diseñadora gráfica especializada en Branding e Identidad Visual (Adobe Illustrator y Photoshop), me encantaría trabajar en este proyecto y acompañar el crecimiento de tus marcas:

• Cobertura completa: Diseño de logotipo, paleta cromática, combinaciones tipográficas, elementos gráficos y manual de comunicación estructurado con usos correctos e incorrectos.
• Entregables profesionales: Archivos fuente editables (.AI vector y .PSD en capas), versiones de alta resolución listas para imprenta (PDF 300 DPI) y formatos digitales optimizados (.PNG transparente y .SVG).
• Compromiso con tus tiempos y flujos: Me adapto con total seriedad a los calendarios de onboarding y entregas que manejan.

Mi cotización de referencia es de {budget_txt} con plazo sugerido de {timeline} (ajustable según el escenario o alcance exacto). Cuento con portfolio de manuales e identidades desarrolladas para compartirte de inmediato.

Para avanzar de forma precisa:
1. ¿Tienes referencias de estilo, paleta de colores preferida o manual de identidad existente para mantener la coherencia?
2. ¿En qué dimensiones y formatos específicos necesitas la entrega final para impresión o difusión digital?

Quedo atenta por el chat de la plataforma para enviarte muestras y coordinar."""
            else:
                return f"""¡Hola! Revisé tu anuncio para "{title}".

Como diseñadora gráfica con amplia experiencia en Adobe Illustrator y Photoshop, puedo ayudarte a crear una propuesta visual atractiva, moderna y alineada con lo que buscas transmitir:

- Conceptos creativos originales adaptados a tu identidad.
- Archivos fuente editables (.AI / .PSD), versiones listas para imprenta (PDF 300 DPI) y formatos digitales (.PNG transparente, .JPG y .SVG).
- Ajustes y revisiones hasta tu total conformidad.

Mi presupuesto de referencia es de {budget_txt} con entrega en {timeline}.

Para enfocar el trabajo creativo:
1. ¿Tienes alguna paleta de colores o referencias visuales que te gusten especialmente para este proyecto?
2. ¿Requieres los archivos optimizados para formato web/redes, imprenta en alta resolución o ambos?

Si gustas, conversemos por el chat de la plataforma para ver referencias o detalles y comenzar."""

        # -------------------------------------------------------------
        # 6. GENERAL / OTROS PROYECTOS TÉCNICOS
        # -------------------------------------------------------------
        else:
            budget_txt = f"{suggested_bid}" if suggested_bid else "a convenir"
            return f"""¡Hola! Revisé los detalles de tu proyecto para "{title}".

Como Ingeniero de Sistemas, puedo ayudarte a resolver este requerimiento con rapidez, código ordenado y buenas prácticas profesionales.

Mi propuesta de referencia es de {budget_txt} con entrega en {timeline}. Cuento con proyectos prácticos verificables en mi GitHub ({github_url}).

Para iniciar con claridad técnica:
1. ¿Cuentas con las especificaciones o material base listo para comenzar la implementación?
2. ¿Cuál es la fecha límite ideal en la que necesitas tener esta entrega operativa?

Quedo a tu disposición por el chat de la plataforma para revisar los detalles e iniciar de inmediato."""

    def generate_execution_plan(self, title: str, description: str, client_name: str, budget: str) -> str:
        """
        Diseña el Blueprint Técnico de Ejecución Paso a Paso para que Jack M. Berrocal
        y Antigravity desarrollen el proyecto adjudicado juntos en pair-programming dentro del IDE.
        """
        extracted = BriefDetailExtractor.extract(title, description)
        category = self.categorize_project(title, description)
        bid_info = self.estimate_bid_and_time(budget, category, f"{title} {description}")
        is_hourly = bid_info.get("is_hourly", False)
        
        # 1. Intentar generación con AiRouter / Ollama Local
        try:
            from core.ai_router import AiRouter
            router = AiRouter()
            if router.is_ollama_online():
                if category == "graphic_design_creative":
                    role_context = (
                        "Este es un proyecto de DISEÑO GRÁFICO Y CREATIVO. En el equipo de Jack, su esposa es la Diseñadora Gráfica Principal. "
                        "El objetivo es preparar una hoja de requerimientos clara, visual y ejecutiva para pasársela directamente a ella: "
                        "1. Especificaciones de diseño (paleta, estilo, tipografía, dimensiones en px/cm). "
                        "2. Formatos finales de entrega (PNG transparente, SVG vectorial, PSD/AI editable, PDF). "
                        "3. Proceso de revisión y entrega rápida al cliente."
                    )
                else:
                    role_context = (
                        "Este es un proyecto de PROGRAMACIÓN / SISTEMAS. Jack M. Berrocal (Ingeniero de Sistemas Senior) supervisa y aprueba, "
                        "y Antigravity (IA Lead Developer en el IDE) se encarga de escribir todo el código fuente, la arquitectura, los tests unitarios "
                        "y la documentación. Los tiempos deben ser realistas y cómodos (3 a 5 días) sin prisas irreales."
                    )

                prompt = (
                    f"PROYECTO ADJUDICADO: {title}\n"
                    f"CATEGORÍA: {category}\n"
                    f"CLIENTE: {client_name}\n"
                    f"PRESUPUESTO ACORDADO: {budget}\n"
                    f"DESCRIPCIÓN Y REQUERIMIENTO DEL CLIENTE:\n{description}\n\n"
                    f"{role_context}\n\n"
                    f"Genera un Plan Técnico de Ejecución Paso a Paso, exhaustivo, seguro y profesional.\n\n"
                    f"Estructura obligatoria en Markdown:\n"
                    f"###  1. Alcance y Entregables Exactos (Para liberar el hito de pago)\n"
                    f"###  2. Stack Tecnológico o Herramientas de Diseño Sugeridas\n"
                    f"###  3. Plan de Ejecución Paso a Paso\n"
                    f"###  4. Mensaje Profesional de Entrega (Para Freelancer.com Chat)\n"
                    f"###  5. Primer Paso Inmediato\n"
                )
                res = router.generate_ai_response(
                    user_message=prompt,
                    system_instructions=(
                        "Eres el Arquitecto de Soluciones Principal de Antigravity colaborando con Jack M. Berrocal y su equipo. "
                        "Tu objetivo es diseñar un plan técnico o creativo impecable, realista en tiempos, sin promesas vacías, listo para ejecutar."
                    ),
                    history=[]
                )
                if res and res.get("content") and len(res["content"].strip()) > 150:
                    return res["content"].strip()
        except Exception as e:
            print(f"[generate_execution_plan] AI generation error: {e}")

        # 2. Fallback Determinístico de Alta Precisión
        return f"""###  1. Alcance y Entregables Exactos (Para liberar el hito de pago de {budget or 'contrato'})
- **Proyecto:** {title}
- **Cliente:** {client_name}
- **Entregable Principal:** Solución técnica completa, funcional y documentada lista para producción o entrega al cliente.
- **Criterio de Aceptación:** Validación del requerimiento descrito por el cliente sin errores de ejecución ni dependencias faltantes.

---

### 2. Stack Tecnológico y Arquitectura Sugerida
- **Lenguaje Principal:** Python 3.11+ / JavaScript según requerimiento del proyecto.
- **Módulos y Librerías:** Requests, Beautiful Soup / Playwright (si hay scraping), FastAPI / Pydantic (si hay backend/APIs), Pandas / OpenPyXL (si hay datos/Excel).
- **Control de Calidad:** Modularización en archivos limpios, tipado estricto y captura exhaustiva de excepciones (`try/except/finally`).
- **Estructura Recomendada:**
  - `main.py` (Punto de entrada)
  - `core/` (Lógica de negocio y transformaciones)
  - `data/` (Archivos de entrada y salida generados)
  - `README.md` (Instrucciones ejecutables para el cliente)

---

### 3. Plan de Desarrollo Paso a Paso (Jack + Antigravity)
- **Paso 1: Entorno y Requerimientos**
  - Creación de entorno virtual o verificación de dependencias en `scratch/projects/{title[:20].lower().replace(' ', '_')}`.
  - Creación del archivo `requirements.txt`.
- **Paso 2: Desarrollo del Motor Principal**
  - Implementación de las funciones nucleares descritas en el proyecto.
  - Validación de estructuras de entrada y salida con logging claro en consola.
- **Paso 3: Blindaje y Manejo Defensivo de Errores**
  - Manejo de desconexiones, tiempos de espera (timeouts) y casos borde (edge cases).
- **Paso 4: Pruebas y Auditoría**
  - Ejecución de pruebas de humo (smoke tests) en entorno local para verificar el 100% de la funcionalidad.
- **Paso 5: Empaquetado y Guía para el Cliente**
  - Creación de archivo ejecutable o script empaquetado (.zip) junto con una guía de 3 pasos para que el cliente lo ponga en marcha.

---

### 4. Mensaje Profesional de Entrega (Para Freelancer.com Chat)
*"Estimado {client_name}, un gusto saludarte.*

*Te confirmo que he completado el desarrollo de '{title}' conforme a todas las especificaciones acordadas.*

*Adjunto el paquete final junto con la documentación técnica y guía de ejecución paso a paso. He realizado pruebas completas para certificar su correcto funcionamiento.*

*Quedo a tu disposición en el chat para cualquier revisión o ajuste que requieras antes de liberar el hito. ¡Muchas gracias por tu confianza!"*

*Atentamente,*  
*Jack M. Berrocal*  
*Ingeniero de Sistemas Senior*

---

### 5. Primer Paso de Trabajo Inmediato
Jack, para arrancar este desarrollo juntos, simplemente escribe en nuestro chat:
 **"Antigravity, desarrollemos el Paso 1 para el proyecto: {title}"**  
¡Y empezaremos a crear los archivos y código en pair-programming de inmediato!"""

