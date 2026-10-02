"""
Local Knowledge Matrix - Base de Conocimiento Experta 100% Local para Scrapy AI.
Proporciona conocimientos profundos y operativos sobre:
1. Diseño Gráfico (Photoshop, Illustrator, Branding, Banners, Retoque, Medidas, Tarifas para la pareja de Jack).
2. Desarrollo de Software y Automatización (Python, FastAPI, Playwright Stealth, Scraping, SQLite, Linux Mint para Jack).
3. Estrategia Freelance y Negociación (Propuestas ganadoras, contratos por hora, WhatsApp, meta de $1,500 USD).
4. Operaciones Locales y Agenda (Reuniones, recordatorios y tareas inspiradas en la tablet holográfica de Scrapy).

Diseñado para funcionar completamente OFFLINE y LOCAL, sin depender de APIs externas.
"""

from typing import Dict, Any, List, Optional
import re


class LocalKnowledgeMatrix:
    """Matriz de Conocimientos Locales para Scrapy AI."""

    # --------------------------------------------------------------------------
    # 1. DISEÑO GRÁFICO (Photoshop & Illustrator - Pareja de Jack)
    # --------------------------------------------------------------------------
    DESIGN_KNOWLEDGE = {
        "logo_creation": {
            "title": "Metodología de Creación de Logotipos en Illustrator",
            "keywords": ["logo", "logotipo", "vector", "illustrator", "vectorizar", "branding", "isotipo", "imagotipo"],
            "summary": "Proceso profesional para crear y entregar logotipos vectoriales de alto impacto:",
            "content": """🎨 **Guía Maestra de Creación de Logotipos en Illustrator:**

1. **Briefing y Concepto:**
   - Identificar los 3 valores clave de la marca y su público objetivo.
   - Definir el tipo de identificador: *Isotipo* (solo símbolo), *Logotipo* (solo texto tipográfico), *Imagotipo* (símbolo + texto separados) o *Isologo* (símbolo y texto fusionados).

2. **Vectorización en Adobe Illustrator:**
   - Trabajar siempre en modo de color **CMYK para impresión** y duplicar en **RGB para digital**.
   - Construcción con la herramienta Pluma (`P`) y Creador de Formas (`Shift + M`) para trazos limpios y geométricamente perfectos.
   - Convertir todos los textos a contornos (`Ctrl + Shift + O`) antes de exportar para evitar fuentes faltantes en el cliente.

3. **Paleta de Colores y Tipografía:**
   - Primario, Secundario y Acento. Entregar siempre los códigos: **HEX** (web), **RGB** (pantallas) y **CMYK** (imprenta).
   - Tipografía principal para el nombre y tipografía secundaria legible para el subtítulo o eslogan (ej. *Montserrat* + *Playfair Display* o *Poppins* + *Inter*).

4. **Kit de Entrega al Cliente (Archivos Finales):**
   - Vector editable: `.AI` (Adobe Illustrator) y `.EPS` (estándar universal).
   - Vector web: `.SVG` (escalable sin pixelarse).
   - Formatos listos para usar: `.PNG` con fondo transparente (alta resolución 300 DPI) y `.JPG` sobre fondo blanco y negro."""
        },
        "photoshop_banners": {
            "title": "Diseño de Banners y Piezas para Redes Sociales en Photoshop",
            "keywords": ["banner", "banners", "photoshop", "redes", "social media", "instagram", "facebook", "post", "flyer"],
            "summary": "Estándares y medidas exactas para banners publicitarios y piezas de redes en Photoshop:",
            "content": """🖼️ **Estándares Profesionales de Banners en Photoshop:**

1. **Medidas Oficiales Actualizadas:**
   - **Instagram / Facebook Post Cuadrado:** `1080 x 1080 px` (Ratio 1:1, 72 DPI, RGB).
   - **Instagram Post Vertical:** `1080 x 1350 px` (Ratio 4:5 - Máxima visibilidad en móviles).
   - **Stories / Reels / TikTok:** `1080 x 1920 px` (Ratio 9:16 vertical).
   - **Facebook Cover / Banner Fanpage:** `820 x 312 px` (Zona segura central `640 x 312 px`).
   - **LinkedIn Banner de Empresa:** `1128 x 191 px` (Personal: `1584 x 396 px`).
   - **Banners Google Display:** `300 x 250 px` (Robapáginas), `728 x 90 px` (Leaderboard), `160 x 600 px` (Rascacielos).

2. **Jerarquía Visual y Composición:**
   - **Regla del 60-30-10:** 60% color dominante, 30% color secundario, 10% color de llamada a la acción (CTA).
   - **Fórmula de Contenido:** 
     • 1 Titular claro y corto (máximo 5-7 palabras).
     • 1 Imagen de producto o persona en alta definición con máscara de recorte limpia.
     • 1 Botón o llamada a la acción visible (*«Compra Hoy»*, *«Agenda tu Cita»*, *«Contáctanos»*).
     • Logotipo en esquina superior o inferior."""
        },
        "photo_retouching": {
            "title": "Retoque Digital y Fotografía de Producto en Photoshop",
            "keywords": ["retoque", "foto", "fotografía", "producto", "e-commerce", "recorte", "fondo blanco", "sujeto"],
            "summary": "Técnicas de retoque fotográfico profesional para catálogos y e-commerce:",
            "content": """📸 **Técnicas de Retoque Profesional en Photoshop:**

1. **Recorte de Productos Perfecto:**
   - Trazado vectorial con la Pluma (`P`) para bordes nítidos y orgánicos en productos.
   - Para cabello o bordes complejos: Selección de Sujeto + comando *«Seleccionar y aplicar máscara»* usando el pincel para perfeccionar bordes.

2. **Corrección de Color y Exposición:**
   - Curvas y Niveles en capas de ajuste no destructivas para calibrar blancos y negros puros.
   - Capa de Tono/Saturación para corregir dominantes de color no deseadas.

3. **Sombra y Reflejo Realista:**
   - Crear sombra de contacto suave bajo el producto con pincel difuso negro a baja opacidad (20-30%) y modo de fusión *Multiplicar*.
   - Aumenta la conversión de venta en tiendas Shopify, Amazon o MercadoLibre en más de un 40%."""
        },
        "design_pricing": {
            "title": "Estrategia de Precios y Paquetes de Diseño para la Pareja de Jack",
            "keywords": ["precio diseño", "cuanto cobrar diseño", "tarifa diseño", "paquete diseño", "precios logo", "precios banner"],
            "summary": "Estructura de precios competitiva para ganar clientes rápido en Freelancer y directos:",
            "content": """💰 **Estructura de Tarifas Sugeridas para tu Pareja (Ganar Clientes Rápido):**

• **Paquete Express 24 Horas (Logotipo Esencial):**
  - Precio: **$45 - $80 USD**.
  - Incluye: 2 propuestas iniciales, revisiones ilimitadas, entrega de archivos en `.AI`, `.PNG` transparente y `.JPG`.
  - Ventaja competitiva: La entrega en 24h cierra clientes que tienen urgencia.

• **Paquete Identidad Visual Completa (PYMEs y Marcas):**
  - Precio: **$150 - $280 USD**.
  - Incluye: Logotipo principal, versión secundaria/submarca, paleta cromática HEX/RGB/CMYK, tipografías corporativas, favicon y plantilla para posts de redes sociales.

• **Pack Redes Sociales (Empresas y Creadores):**
  - Precio: **$50 - $90 USD** por pack de 5 piezas editables o listas para publicar.
  - Genera clientes recurrentes mes a mes.

• **Retoque E-commerce por Lotes:**
  - Precio: **$3 - $6 USD** por imagen en lotes de 10 a 50 fotos (limpieza de fondo blanco, sombra y optimización web)."""
        }
    }

    # --------------------------------------------------------------------------
    # 2. DESARROLLO Y AUTOMATIZACIÓN (Python, Web, Linux - Jack)
    # --------------------------------------------------------------------------
    TECH_KNOWLEDGE = {
        "fastapi_architecture": {
            "title": "Arquitectura Backend con FastAPI y AsyncIO",
            "keywords": ["fastapi", "python", "backend", "api", "async", "uvicorn", "pydantic"],
            "summary": "Mejores prácticas de desarrollo backend en Python con FastAPI:",
            "content": """⚡ **Fundamentos de Arquitectura FastAPI:**

1. **Rendimiento Asíncrono:**
   - Usar `async def` para endpoints que realizan I/O de red o base de datos asíncrona.
   - Para tareas pesadas de CPU o scraping síncrono, utilizar `starlette.background.BackgroundTasks` o ejecutores en thread pool para no bloquear el bucle de eventos (`asyncio.to_thread`).

2. **Modelos y Validación con Pydantic:**
   - Definir esquemas de entrada (`RequestModel`) y salida (`ResponseModel`) con tipos estrictos para autogenerar documentación Swagger OpenAPI en `/docs`.

3. **Gestión de Base de Datos (SQLAlchemy 2.0):**
   - Usar `NullPool` en SQLite para evitar bloqueos por concurrencia entre procesos de background y el servidor HTTP.
   - Sesiones manejadas mediante generador con inyección de dependencias `Depends(get_db)` y bloque `finally: db.close()`."""
        },
        "playwright_stealth": {
            "title": "Scraping y Automatización Antidetección con Playwright Stealth",
            "keywords": ["playwright", "scraping", "stealth", "crawler", "cloudflare", "antibot", "bot"],
            "summary": "Técnicas avanzadas para evitar bloqueos en scraping de portales laborales y web:",
            "content": """🕵️ **Ingeniería de Automatización con Playwright Stealth:**

1. **Ocultar Huellas de Automatización:**
   - Aplicar `playwright_stealth` para parchear variables críticas (`navigator.webdriver = undefined`, permisos falsos de notificaciones, plugins reales de Chrome).
   - Iniciar Chromium con argumentos: `--disable-blink-features=AutomationControlled`, `--no-sandbox`, `--disable-infobars`.

2. **Comportamiento Humano Simulado:**
   - Retardos aleatorios entre interacciones con distribución normal/gaussiana (ej. pausas de 1.8 a 3.5 segundos).
   - Scroll suave y paulatino mediante scripts inyectados en la página antes de interactuar con botones de postulación.
   - Reutilización de cookies y perfiles persistentes en disco (`launch_persistent_context`) para no requerir logins repetidos."""
        },
        "linux_system_admin": {
            "title": "Administración de Linux Mint (Cinnamon) y Monitoreo de Hardware",
            "keywords": ["linux", "mint", "cinnamon", "systemd", "gpu", "nvidia", "hardware", "terminal", "servicio"],
            "summary": "Gestión del entorno local de Jack en Linux Mint:",
            "content": """🐧 **Gestión del Entorno Linux Mint:**

1. **Servicios Systemd en Modo Usuario:**
   - JobHunter y Scrapy corren como servicio permanente de usuario en `~/.config/systemd/user/jobhunter.service`.
   - Comandos clave:
     • Ver estado: `./service_ctl.sh status`
     • Reiniciar: `./service_ctl.sh restart`
     • Ver logs en vivo: `journalctl --user -u jobhunter.service -f`

2. **Tarjeta Gráfica NVIDIA GTX 1660 SUPER (6GB):**
   - Monitoreo directo: `nvidia-smi`
   - Soporte CUDA disponible para procesamiento de datos, pipelines de IA y visión computacional.

3. **Gestión de Gadgets de Escritorio:**
   - Ventanas en modo app de Chromium con flags `--app=http://localhost:8000/scrapy_widget`.
   - Fijación siempre visible en escritorio Cinnamon usando `wmctrl -b add,above,sticky`."""
        }
    }

    # --------------------------------------------------------------------------
    # 3. ESTRATEGIA FREELANCE, VENTAS Y META DE $1,500 USD
    # --------------------------------------------------------------------------
    FREELANCE_KNOWLEDGE = {
        "winning_proposals": {
            "title": "Estructura de una Propuesta Ganadora en Freelancer y Upwork",
            "keywords": ["propuesta", "oferta", "postular", "bidding", "freelancer", "upwork", "como ganar", "carta de presentacion"],
            "summary": "Fórmula infalible para ganar ofertas en las primeras 2 líneas:",
            "content": """🏆 **Estructura de una Propuesta que Cierra Contratos:**

1. **El Gancho Inicial (Primeras 2 líneas):**
   - El cliente solo ve las primeras dos líneas antes de abrir la propuesta.
   - *Prohibido:* «Hola, soy ingeniero con 5 años de experiencia y me interesa su proyecto...» (Eso hacen los 50 competidores genéricos).
   - *Fórmula Ganadora:* «Hola [Nombre], entiendo que necesitas [problema exacto del cliente, ej: un bot en Python que extraiga datos sin bloqueos] y tenerlo listo [tiempo, ej: este fin de semana]. Ya he solucionado este mismo desafío anteriormente.»

2. **Solución en 3 Viñetas Directas:**
   - Viñeta 1: Enfoque técnico o de diseño exacto.
   - Viñeta 2: Entregable concreto con garantía de pruebas o revisiones.
   - Viñeta 3: Tiempo exacto de entrega del primer avance.

3. **Llamado a la Acción (CTA) de Cero Fricción:**
   - «Tengo un par de preguntas rápidas sobre tu flujo de trabajo para ajustar el presupuesto a tu favor. ¿Podemos conversar 5 minutos por el chat?»"""
        },
        "revenue_roadmap": {
            "title": "Hoja de Ruta para Generar $1,500 USD Netos Mensuales",
            "keywords": ["1500", "meta", "ingresos", "dinero", "rentabilidad", "finanzas", "dólares", "dolares"],
            "summary": "Cálculo matemático exacto para alcanzar los $1,500 USD mensuales entre Jack y su pareja:",
            "content": """🎯 **Plan Matemático hacia los $1,500 USD Mensuales:**

• **Estrategia Combinada Jack + Pareja (La más sólida y de menor estrés):**
  1. **Jack (Desarrollo & Automatización):**
     - 1 contrato recurrente de soporte técnico o WhatsApp por horas: 15 hrs/semana a $18 USD/hr = **$1,080 USD/mes**.
  2. **Pareja de Jack (Diseño Gráfico & Redes):**
     - 4 clientes de diseño al mes (packs de identidad o lotes de banners a $120 USD c/u) = **$480 USD/mes**.
  3. **Total Mensual:** **$1,560 USD netos**.
  4. **Costos fijos:** Freelancer Plus ($9.90 USD).
  5. **Beneficio Neto:** Más de **$1,550 USD limpios** en el bolsillo cada mes.

• **Clave del éxito:**
  - No depender de proyectos únicos de 1 sola vez.
  - Convertir a cada cliente de diseño o de software en un cliente con mantenimiento mensual o paquetes continuos."""
        },
        "whatsapp_support_hourly": {
            "title": "Contratos por Hora de Soporte WhatsApp y Atención Técnica",
            "keywords": ["whatsapp", "por hora", "soporte", "hourly", "contrato por hora", "atencion al cliente"],
            "summary": "Cómo monetizar soporte remoto por hora para clientes de habla hispana:",
            "content": """⏱️ **Monetización de Contratos por Hora (Soporte WhatsApp & Técnico):**

1. **Perfil del Cliente:**
   - Dueños de negocios digitales, e-commerce y agencias que no tienen tiempo de atender chats técnicos de WhatsApp o resolver incidencias operativas.

2. **Tarifa Recomendada:**
   - **$15 a $25 USD por hora**.
   - Con solo un turno de 4 horas diarias de lunes a viernes (20 horas semanales) a $20/hr, son **$400 USD por semana = $1,600 USD al mes**.

3. **Por qué contratan a Jack:**
   - Jack es Ingeniero de Sistemas: no solo responde mensajes, sino que puede automatizar respuestas, integrar bases de datos y resolver problemas técnicos reales que un asistente convencional no puede."""
        }
    }

    # --------------------------------------------------------------------------
    # 4. OPERACIONES DE LA TABLET HOLOGRÁFICA DE SCRAPY (Agenda & Tareas)
    # --------------------------------------------------------------------------
    OPERATIONAL_HUD = {
        "agenda": [
            {"time": "10:30 AM", "event": "Reunión de Coordinación & Seguimiento de Proyectos"},
            {"time": "03:00 PM", "event": "Revisión de Nuevas Oportunidades en Freelancer y WhatsApp"},
            {"time": "06:00 PM", "event": "Control de Métricas, Postulaciones y Meta de $1,500 USD"}
        ],
        "reminders": [
            "Verificar propuestas enviadas de diseño en Freelancer Plus",
            "Monitorear estado del servicio JobHunter (puerto 8000 activo)",
            "Dar seguimiento a ofertas de contratos por hora de WhatsApp"
        ],
        "tasks": [
            {"task": "Enviar informe de oportunidades activas a Jack", "done": False},
            {"task": "Preparar propuesta de diseño de logo para la pareja de Jack", "done": False},
            {"task": "Rastrear contratos remotos en Torre y Get on Board", "done": True}
        ]
    }

    # --------------------------------------------------------------------------
    # 5. CASCADA DE INTELIGENCIA ARTIFICIAL (Miambot SaaS Multi-Provider)
    # --------------------------------------------------------------------------
    AI_CASCADE_KNOWLEDGE = {
        "miambot_ai": {
            "title": "Cascada Multi-Proveedor de Inteligencia Artificial (Miambot SaaS)",
            "keywords": ["miambot", "modelo", "modelos", "ia", "ias", "openrouter", "groq", "nvidia", "zhipu", "glm", "gemini", "openai", "deepseek", "cascada", "proveedor", "proveedores"],
            "summary": "Arquitectura y jerarquía de modelos de IA con auto-sanación de Miambot:",
            "content": """🤖 **Cascada Jerárquica de Inteligencia Artificial de Miambot en Scrapy AI:**

Scrapy cuenta con la arquitectura completa y priorización idéntica a Miambot SaaS con **Auto-Sanación (Auto-Healing)** activa:

1. **Tier 1 — OpenRouter (Prioridad Absoluta - 38 Modelos Gratuitos y de Pago):**
   - `deepseek/deepseek-r1:free` (Prioridad 1 - Razonamiento profundo)
   - `deepseek/deepseek-chat:free` (Prioridad 2)
   - `deepseek/deepseek-chat` (Prioridad 3 - De Pago)
   - `qwen/qwen-2.5-72b-instruct:free` (Prioridad 4)
   - `google/gemini-2.5-flash:free` y `meta-llama/llama-3.3-70b-instruct:free` (Prioridad 5)
   - `openchat/openchat-7b:free`, `google/gemma-2-9b-it:free` (Prioridad 6)
   - `meta-llama/llama-3.1-8b-instruct:free`, `mistralai/mistral-nemo:free`, etc.

2. **Tier 2 — Groq (Ultra Baja Latencia):**
   - `llama-3.3-70b-versatile` y `llama-3.1-8b-instant`.

3. **Tier 3 — NVIDIA NIM Cloud:**
   - `meta/llama-3.3-70b-instruct`, `nvidia/llama-3.1-nemotron-70b-instruct`, `NVIDIABuild-Autogen-34`.

4. **Tier 4 — Zhipu AI / GLM (BigModel):**
   - `glm-4-flash` (Ultra eficiente y gratis).

5. **Tier 5 — Google Gemini Nativo:**
   - `gemini-2.5-flash` y `gemini-1.5-flash` (Misma base de Antigravity).

6. **Tier 6 — OpenAI Nativo:**
   - `gpt-4o-mini` y `gpt-4o`.

7. **Tier 7 — Fallback Local Offline + Live Web Research:**
   - Base de conocimiento local + búsqueda web en tiempo real + automatización en Linux Mint.

⚡ *Auto-Sanación:* Si un modelo devuelve 429, 402 o timeout (>8s), se marca temporalmente offline y salta al siguiente proveedor sin interrumpir tu experiencia. Tras 60s de enfriamiento, se reintenta automáticamente."""
        }
    }

    @classmethod
    def find_knowledge(cls, query: str) -> Optional[Dict[str, Any]]:
        """
        Busca el conocimiento local más relevante para la consulta del usuario.
        Aplica coincidencia estricta y evita interceptar consultas conversacionales, creativas o de código.
        """
        q_low = query.lower()

        # Si el usuario pide generar, escribir o programar algo específico, no interceptar con plantilla estática
        generative_patterns = [
            r'\b(?:escribe|escribir|redacta|redactar|crea|crear|genera|generar|inventa|poema|cancion|historia|chiste)\b',
            r'\b(?:corrige|corregir|depura|depurar|analiza|analizar|revisa|revisar|optimiza|optimizar)\s+(?:este|mi|el)?\s*(?:c[oó]digo|script|funci[oó]n|error|bug)\b',
            r'\b(?:haz|hacer|dame|muestra|propon|proponer)\s+(?:un|una)\s+(?:ejemplo|soluci[oó]n|idea|propuesta|c[oó]digo|script)\b'
        ]
        for gp in generative_patterns:
            if re.search(gp, q_low):
                return None

        # Exigir intención explícita de consultar guía/documentación O al menos 2 palabras clave exactas
        is_explicit_guide_request = bool(re.search(
            r'\b(?:gu[ií]a|manual|apunte|tutorial|documentaci[oó]n|medidas\s+de|tarifas?\s+de|requisitos?\s+de|c[oó]mo\s+(?:se\s+diseña|vectorizar|exportar))\b',
            q_low
        ))

        all_topics = {
            **cls.DESIGN_KNOWLEDGE,
            **cls.TECH_KNOWLEDGE,
            **cls.FREELANCE_KNOWLEDGE,
            **cls.AI_CASCADE_KNOWLEDGE
        }

        best_match = None
        max_matches = 0

        for key, topic in all_topics.items():
            # Coincidencia con límites de palabra para evitar falsos positivos
            matches = sum(1 for kw in topic["keywords"] if re.search(r'\b' + re.escape(kw) + r'\b', q_low))
            if matches > max_matches:
                max_matches = matches
                best_match = topic

        # Requiere al menos 2 coincidencias de palabras clave, o 1 coincidencia si pidió explícitamente una guía/manual
        if max_matches >= 2 or (max_matches >= 1 and is_explicit_guide_request):
            return best_match
        return None

    @classmethod
    def get_hud_summary(cls) -> Dict[str, Any]:
        """Devuelve el estado de la agenda, recordatorios y tareas (Tablet Holográfica de Scrapy)."""
        return cls.OPERATIONAL_HUD

    @classmethod
    def add_task(cls, task_text: str) -> bool:
        """Agrega una nueva tarea a la tablet operativa."""
        if not task_text.strip():
            return False
        cls.OPERATIONAL_HUD["tasks"].insert(0, {"task": task_text.strip(), "done": False})
        return True

    @classmethod
    def add_reminder(cls, reminder_text: str) -> bool:
        """Agrega un nuevo recordatorio a la tablet operativa."""
        if not reminder_text.strip():
            return False
        cls.OPERATIONAL_HUD["reminders"].insert(0, reminder_text.strip())
        return True

    @classmethod
    def complete_task(cls, index: int) -> bool:
        """Marca una tarea como completada."""
        tasks = cls.OPERATIONAL_HUD["tasks"]
        if 0 <= index < len(tasks):
            tasks[index]["done"] = True
            return True
        return False
