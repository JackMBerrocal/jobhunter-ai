import os
import re
import json
import urllib.request
from typing import Dict, Any, Optional


class MiamBotSalesCopilot:
    """
    Motor de Cierre de Ventas y Negociación en Chat derivado de la inteligencia de MiamBot.
    Diseñado para asistir a Jack y su equipo en el chat directo de Freelancer.com cuando un cliente
    responde a una propuesta de Desarrollo de Software o de Diseño Gráfico & Creativo.

    Aplica las 4 Reglas de Oro de MiamBot:
    1. Trato empático, educado y profesional en español nativo (de "usted") o inglés si el cliente escribe en inglés.
    2. Enfoque en resolver el dolor del cliente y demostrar seguridad técnica o artística absoluta.
    3. Manejo magistral de objeciones (precio, tiempo, experiencia, alcance).
    4. Cierre obligatorio con Llamado a la Acción (CTA) para que el cliente cree el Milestone (Hito de pago).
    5. CERO llamadas externas, CERO WhatsApp, CERO Zoom: 100% garantía y ejecución dentro de Freelancer.com.
    """

    @classmethod
    def _call_llm(cls, prompt: str) -> Optional[str]:
        """Invoca Gemini o Groq si están disponibles en las variables de entorno."""
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                text = (resp.text or "").strip()
                if len(text) > 30:
                    return text
            except Exception:
                pass

        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                req_data = json.dumps({
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.35
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=req_data,
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "JobHunter-MiamBot"
                    }
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    res_body = response.read().decode("utf-8")
                    parsed = json.loads(res_body)
                    text = parsed["choices"][0]["message"]["content"].strip()
                    if len(text) > 30:
                        return text
            except Exception:
                pass

        return None

    @classmethod
    def generate_chat_reply(
        cls,
        client_message: str,
        project_title: str = "",
        category: str = "web_dev",
        goal: str = "close_milestone",
        offered_bid: str = "",
        timeline: str = ""
    ) -> Dict[str, Any]:
        c_low = client_message.lower()

        # Detección de idioma
        is_english = any(w in c_low for w in ["hello", "hi", "how are you", "can you", "what is", "price", "budget", "timeline", "portfolio", "when can", "sample"])

        # Identificación del tipo de duda del cliente si no se especificó un goal
        detected_intent = goal
        if any(w in c_low for w in ["descuento", "muy caro", "rebaja", "menos", "caro", "presupuesto bajo", "expensive", "discount", "cheaper", "lower price"]):
            detected_intent = "negotiate_price"
        elif any(w in c_low for w in ["cuándo", "cuando", "tiempo", "plazo", "urgente", "días", "dias", "hours", "how long", "urgent", "deadline", "fast"]):
            detected_intent = "timeline_urgency"
        elif any(w in c_low for w in ["ejemplo", "muestra", "portafolio", "portfolio", "trabajos anteriores", "samples", "previous work", "logos anteriores"]):
            detected_intent = "portfolio_proof"
        elif any(w in c_low for w in ["llamada", "zoom", "meet", "whatsapp", "call", "phone", "celular", "número", "telefono", "skype"]):
            detected_intent = "prevent_external_call"
        elif any(w in c_low for w in ["empezar", "arrancar", "comenzamos", "start", "hacerlo", "dale", "de acuerdo", "perfecto", "me parece", "ok"]):
            detected_intent = "close_milestone"

        is_design = category == "graphic_design_creative" or any(w in (project_title + " " + client_message).lower() for w in ["logo", "diseño", "photoshop", "illustrator", "banner", "flyer", "vector"])

        # Intentar síntesis LLM personalizada con MiamBot Prompt si hay mensaje del cliente
        if client_message and len(client_message.strip()) > 8:
            llm_prompt = f"""Eres MiamBot Sales Copilot, el agente de ventas consultivo de alta conversión integrado en JobHunter AI (para Jack Berrocal y su equipo multidisciplinario de software y diseño gráfico).
Estás respondiendo un mensaje en el chat directo de un cliente en Freelancer.com.

DATOS DEL PROYECTO:
- Título: {project_title or 'Proyecto Freelance'}
- Especialidad / Categoría: {'Diseño Gráfico & Creativo (Photoshop / Illustrator)' if is_design else 'Ingeniería de Software / Desarrollo / Datos'}
- Cotización acordada / Presupuesto: {offered_bid or 'Según propuesta'}
- Plazo estimado: {timeline or 'Inmediato'}
- Mensaje del cliente: "{client_message}"
- Intención detectada: {detected_intent}

REGLAS DE ORO DE MIAMBOT (OBLIGATORIAS):
1. EMPATÍA Y PROFESIONALISMO: Saludo formal y educado (de "usted") en {'inglés' if is_english else 'español'}. Directo al punto, transmitiendo total confianza y dominio.
2. MANEJO DE OBJECIONES:
   - Si pide rebaja: protege el valor y ofrece ajustar alcance o lanzar primera fase.
   - Si pregunta por tiempo: confirma disponibilidad inmediata.
   - Si pide portafolio: {'resalta entregables en Adobe Photoshop e Illustrator (.AI, .PSD en capas, .SVG vector y PDF 300 DPI con revisiones ilimitadas)' if is_design else 'remite a proyectos reales y código verificable en GitHub: https://github.com/JackMBerrocal'}.
   - Si pide llamada o WhatsApp: CERO llamadas. Explica con total diplomacia que por normas de seguridad de Freelancer.com todo se coordina 100% por este chat protegiendo al cliente.
3. CIERRE CONVERSACIONAL (CTA): Finaliza invitando al cliente a adjudicar el proyecto y habilitar el Milestone (Hito de pago) para iniciar el trabajo hoy mismo.

Responde ÚNICAMENTE con el mensaje exacto para enviar al cliente."""
            llm_reply = cls._call_llm(llm_prompt)
            if llm_reply:
                return {
                    "intent": detected_intent,
                    "suggested_reply": llm_reply,
                    "is_english": is_english,
                    "source": "miambot_llm"
                }

        github_url = "https://github.com/JackMBerrocal"

        # ---------------- CASO 1: CLIENTE PIDE LLAMADA / WHATSAPP EXTERNO ----------------
        if detected_intent == "prevent_external_call":
            if is_english:
                reply = f"""Thank you for the message! To strictly comply with Freelancer.com terms of service and keep all communications protected under platform warranty, I handle all project coordination directly through this chat. 

We can iron out every single detail, review files, and share updates right here seamlessly without needing external calls. 

I am online right now—could you please share the details or files here so we can review them together and get started?"""
            else:
                reply = f"""¡Muchas gracias por su respuesta! Para cumplir rigurosamente con las políticas de seguridad de Freelancer.com y mantener el proyecto 100% protegido con las garantías de la plataforma, coordino todo el trabajo directamente a través de este chat.

Por aquí podemos resolver cualquier duda técnica, revisar archivos, enviar capturas de avance y coordinar entregas con total agilidad y transparencia, sin necesidad de llamadas externas.

Estoy en línea en este momento. ¿Me comparte los detalles o el documento por aquí para revisarlo de inmediato y ponernos en marcha? 🚀"""

        # ---------------- CASO 2: CLIENTE PIDE DESCUENTO / REBAJA DE PRECIO ----------------
        elif detected_intent == "negotiate_price":
            if is_design:
                if is_english:
                    reply = f"""I understand your budget considerations, and our priority is to deliver a top-tier visual identity that elevates your brand and requires zero rework.

To match your target budget and kick off right away, we can either:
1. Keep the full scope and deliver within a competitive closed rate with priority 24-48h turnaround.
2. Deliver the most critical creative asset first (e.g. main logo or key banner) so you can launch immediately at minimal cost.

Which option works best for your schedule? I am ready to start as soon as we confirm! 🤝🎨"""
                else:
                    reply = f"""Entiendo perfectamente el cuidado de su presupuesto. Nuestra prioridad es entregarle piezas gráficas de alto impacto visual que destaquen a su marca y no requieran retrabajo.

Para adaptarnos a lo que busca y arrancar hoy mismo, propongo:
1. Mantener el alcance completo acordado ajustando el presupuesto al número más competitivo posible con entrega prioritaria en 24 a 48 horas.
2. O desarrollar primero la pieza visual más urgente (ej. logotipo principal o banner central) para que pueda utilizarla de inmediato a menor inversión.

¿Cuál de las dos alternativas le resulta más conveniente? Si le parece bien, definimos el monto cerrado aquí mismo en el chat y creamos el hito para comenzar hoy. 🤝🎨"""
            else:
                if is_english:
                    reply = f"""I understand your budget considerations, and my priority is to deliver a robust, high-quality solution that works flawlessly without requiring rework later. 

To help meet your target budget, we can either:
1. Keep the full scope and adjust to a competitive closed budget with immediate priority delivery.
2. Focus on the core critical features for phase 1 so you can launch right away at a reduced cost.

Which approach works best for your current plan? I am ready to start as soon as we agree."""
                else:
                    reply = f"""Entiendo perfectamente el cuidado de su presupuesto. Mi prioridad es entregarle una solución profesional, limpia y bien estructurada que funcione de inmediato sin darle dolores de cabeza ni gastos posteriores.

Para adaptarnos a lo que busca y arrancar hoy mismo, propongo:
1. Mantener el alcance completo acordado ajustando el presupuesto al número más competitivo posible con entrega prioritaria.
2. O enfocar la primera entrega en las funcionalidades esenciales para que salga a producción de inmediato con la menor inversión.

¿Cuál de las dos alternativas le resulta más conveniente? Si le parece bien, definimos el monto cerrado aquí mismo en el chat y creamos el hito para comenzar hoy. 🤝"""

        # ---------------- CASO 3: CLIENTE PREGUNTA POR TIEMPO / URGENCIA ----------------
        elif detected_intent == "timeline_urgency":
            time_str = timeline if timeline else ("24 a 48 horas" if is_design else "3 a 4 días hábiles")
            if is_english:
                reply = f"""I have immediate availability to start right now. With the details and requirements defined, I can have the complete deliverable ready within {time_str}, including testing and final adjustments.

If you have an urgent deadline, please let me know and I will prioritize your project immediately. 

Shall we create the milestone deposit here on Freelancer.com so I can start working today?"""
            else:
                reply = f"""Cuento con disponibilidad inmediata para comenzar hoy mismo. Con los requerimientos que me indicó, el proyecto quedará completamente listo y funcionando en un plazo de {time_str}, incluyendo pruebas de funcionamiento y una ronda de ajustes finales.

Si tiene una fecha límite o urgencia especial, hágamelo saber y con gusto priorizo su proyecto en mi turno de hoy.

¿Le parece si creamos el hito de pago (Milestone) en Freelancer para comenzar de inmediato con la primera fase? ⏱️🚀"""

        # ---------------- CASO 4: CLIENTE PIDE PORTAFOLIO / PRUEBAS DE EXPERIENCIA ----------------
        elif detected_intent == "portfolio_proof":
            if is_design:
                if is_english:
                    reply = f"""Absolutely! We specialize in professional graphic design, brand identity, Photoshop image composition, and vector art in Adobe Illustrator.

We deliver layered master files (.AI, .PSD), vector formats (.SVG, .EPS), and print-ready high-resolution files (300 DPI CMYK PDF and transparent PNGs) with unlimited refinements until you are 100% satisfied.

Would you like to share your color palette or visual references so I can show you the exact creative direction we can take?"""
                else:
                    reply = f"""¡Con mucho gusto! Contamos con amplia trayectoria en diseño gráfico publicitario, identidad de marca, retoque digital en Photoshop y vectorización avanzada en Adobe Illustrator.

Entregamos siempre los archivos editables originales (.AI, .PSD con capas organizadas), versiones vectoriales escalables (.SVG, .EPS) y formatos en alta definición (PDF imprenta 300 DPI y PNG transparentes) con revisiones ágiles hasta su plena conformidad.

¿Tiene a mano alguna referencia visual, boceto o paleta de colores para mostrarle de inmediato la dirección conceptual que proponemos? 🎨"""
            else:
                if is_english:
                    reply = f"""Absolutely! As a Systems Engineer specialized in Software & Data, you can review my verifiable technical projects, source code, and real deployed web solutions directly on my GitHub: {github_url}.

I apply clean architecture, responsive UI/UX standards, and high-performance loading speeds on all my builds.

Would you like me to share a specific example related to your project requirements?"""
                else:
                    reply = f"""¡Con mucho gusto! Como Ingeniero de Sistemas especializado en Software y Datos, puede revisar proyectos reales, código fuente y aplicaciones funcionales directamente en mi repositorio verificado de GitHub: {github_url}.

Aplico código limpio, estándares modernos de diseño UI/UX responsivo y optimización de velocidad de carga en cada trabajo.

¿Hay alguna función o sección en particular que le gustaría que le muestre cómo implementarla para su proyecto?"""

        # ---------------- CASO 5: CIERRE DE TRATO / CREAR MILESTONE (DEFAULT) ----------------
        else:
            bid_str = f" de {offered_bid}" if offered_bid else ""
            if is_design:
                if is_english:
                    reply = f"""Excellent! Everything is clear and I am ready to begin the creative process.

To initiate the project under Freelancer.com warranty:
1. Please award the project and create the initial milestone deposit{bid_str}.
2. Share any logos, texts, or style preferences here in the chat.

Once funded, we will immediately start working on the initial concept drafts for your review. Looking forward to creating something outstanding for your brand! 🎨🚀"""
                else:
                    reply = f"""¡Excelente! El alcance creativo y los requerimientos visuales están sumamente claros.

Para arrancar de inmediato bajo el protocolo de garantía de Freelancer.com:
1. Puede proceder a adjudicar el proyecto y habilitar el hito de pago (Milestone){bid_str}.
2. Me comparte por aquí los textos, logotipos o detalles que tenga preparados.

En cuanto se cree el hito en la plataforma, iniciaremos de inmediato con las primeras propuestas visuales para su revisión. ¡Será un gran gusto trabajar en este proyecto con usted! 🎨🚀"""
            else:
                if is_english:
                    reply = f"""Excellent! Everything is clear and I am ready to get to work.

To initiate the project under Freelancer.com warranty:
1. Please award the project and create the initial milestone deposit{bid_str}.
2. Share the necessary access or documents here in the chat.

Once funded, I will begin execution immediately and keep you updated every step of the way. Looking forward to building this with you! 🚀"""
                else:
                    reply = f"""¡Excelente! Todo el alcance ha quedado sumamente claro y estoy listo para poner manos a la obra.

Para arrancar de inmediato bajo el protocolo de garantía de Freelancer.com:
1. Puede proceder a adjudicar el proyecto y habilitar el hito de pago (Milestone){bid_str}.
2. Me comparte los archivos o accesos necesarios directamente por este chat.

En cuanto se cree el hito en la plataforma, inicio el desarrollo de inmediato y le iré reportando los avances en tiempo real. ¡Será un gusto trabajar en este proyecto con usted! 🚀"""

        return {
            "intent": detected_intent,
            "suggested_reply": reply,
            "is_english": is_english,
            "source": "miambot_cognitive"
        }
