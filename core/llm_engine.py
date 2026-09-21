import os
import re
import yaml
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Cargar google-genai si está disponible
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class LLMEngine:
    def __init__(self, profile_path: str = "config/candidate_profile.yaml"):
        self.profile_path = profile_path
        self.profile = self.load_profile()
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.client = None
        if HAS_GENAI and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[LLMEngine] Advertencia: No se pudo inicializar Gemini Client: {e}")

    def load_profile(self) -> Dict[str, Any]:
        """Carga el perfil estructurado del candidato desde YAML."""
        if not Path(self.profile_path).exists():
            return {}
        with open(self.profile_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save_profile(self, updated_profile: Dict[str, Any]):
        """Actualiza el archivo YAML con nuevos datos del perfil."""
        self.profile = updated_profile
        with open(self.profile_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(updated_profile, f, allow_unicode=True, sort_keys=False)

    def get_target_roles(self) -> List[Dict[str, Any]]:
        """Obtiene la lista estructurada de puestos objetivo configurados."""
        self.profile = self.load_profile()
        roles = self.profile.get("job_preferences", {}).get("target_roles", [])
        structured_roles = []
        for idx, r in enumerate(roles):
            if isinstance(r, dict):
                structured_roles.append({
                    "id": r.get("id", f"role_{idx}"),
                    "name": r.get("name", "Puesto General"),
                    "category": r.get("category", "Tecnología"),
                    "icon": r.get("icon", "💼"),
                    "keywords": r.get("keywords", []),
                    "search_query": r.get("search_query", r.get("name", "junior sistemas")),
                    "enabled": r.get("enabled", True)
                })
            elif isinstance(r, str):
                slug = r.lower().replace(" ", "_")
                structured_roles.append({
                    "id": slug,
                    "name": r,
                    "category": "General",
                    "icon": "💼",
                    "keywords": [w.lower() for w in r.split() if len(w) > 2],
                    "search_query": r.lower(),
                    "enabled": True
                })
        return structured_roles

    def save_target_roles(self, roles: List[Dict[str, Any]]):
        """Guarda la lista de puestos objetivo en candidate_profile.yaml."""
        self.profile = self.load_profile()
        if "job_preferences" not in self.profile:
            self.profile["job_preferences"] = {}
        self.profile["job_preferences"]["target_roles"] = roles
        self.save_profile(self.profile)

    def toggle_target_role(self, role_id: str, enabled: Optional[bool] = None) -> bool:
        """Activa o desactiva un rol específico."""
        roles = self.get_target_roles()
        found = False
        new_state = True
        for r in roles:
            if r["id"] == role_id:
                if enabled is not None:
                    r["enabled"] = enabled
                else:
                    r["enabled"] = not r.get("enabled", True)
                new_state = r["enabled"]
                found = True
                break
        if found:
            self.save_target_roles(roles)
        return new_state

    def add_target_role(self, name: str, keywords: List[str] = None, search_query: str = None, category: str = "Personalizado", icon: str = "🎯") -> Dict[str, Any]:
        """Añade un nuevo puesto de trabajo objetivo."""
        roles = self.get_target_roles()
        import re
        role_id = re.sub(r'[^a-zA-Z0-9_]', '', name.lower().replace(" ", "_"))
        if not keywords:
            keywords = [w.lower() for w in name.split() if len(w) > 2]
        if not search_query:
            search_query = f"{name.lower()} junior"
        
        new_role = {
            "id": role_id or f"custom_{len(roles)+1}",
            "name": name,
            "category": category,
            "icon": icon,
            "keywords": keywords,
            "search_query": search_query,
            "enabled": True
        }
        roles.append(new_role)
        self.save_target_roles(roles)
        return new_role

    def delete_target_role(self, role_id: str) -> bool:
        """Elimina un puesto de trabajo de la lista."""
        roles = self.get_target_roles()
        initial_len = len(roles)
        roles = [r for r in roles if r["id"] != role_id]
        if len(roles) < initial_len:
            self.save_target_roles(roles)
            return True
        return False

    def get_active_search_queries(self) -> List[str]:
        """Devuelve las consultas de búsqueda de los roles que están activados."""
        roles = self.get_target_roles()
        queries = [r["search_query"] for r in roles if r.get("enabled", True) and r.get("search_query")]
        return queries or ["junior sistemas", "trainee sistemas"]

    def match_job_to_role(self, title: str, description: str = "") -> Dict[str, Any]:
        """
        Determina si una vacante coincide con alguno de los puestos configurados
        y si dicho puesto está activo / habilitado por el candidato.
        """
        roles = self.get_target_roles()
        title_lower = title.lower()
        desc_lower = (description or "").lower()

        best_role = None
        max_matches = 0

        for r in roles:
            match_count = 0
            for kw in r.get("keywords", []):
                kw_l = kw.lower()
                # Búsqueda con límite de palabra exacto para evitar falsos positivos (ej: 'bi' en 'sostenibilidad')
                pattern = rf'\b{re.escape(kw_l)}\b'
                if re.search(pattern, title_lower):
                    match_count += 3
                elif re.search(pattern, desc_lower):
                    match_count += 1
            if match_count > max_matches:
                max_matches = match_count
                best_role = r

        # Si el mejor rol es de prácticas pero el título no contiene ningún indicio de tecnología, descartarlo
        tech_affirmative = [
            "sistemas", "software", "programador", "programacion", "programación",
            "developer", "desarrollador", "frontend", "backend", "fullstack", "full-stack",
            "web", "devops", "sre", "cloud", "qa", "tester", "testing", "calidad de software",
            "helpdesk", "help desk", "soporte ti", "soporte técnico", "soporte tecnico",
            "mesa de ayuda", "it support", "redes", "active directory", "base de datos",
            "bases de datos", "sql", "postgresql", "mysql", "data analyst", "analista de datos",
            "business intelligence", "python", "javascript", "typescript", "java", "c#",
            "fastapi", "django", "react", "node", "linux", "infraestructura ti", "data", "ti", "it"
        ]

        if best_role and max_matches > 0:
            # Si el match fue solo por palabras de trainee/practicante pero el rol es no-tech (ej: sostenibilidad, pricing, psicología, facturación)
            if best_role["id"] == "practicante_sistemas":
                has_tech_in_title = any(re.search(rf'\b{re.escape(k)}\b', title_lower) for k in tech_affirmative)
                if not has_tech_in_title:
                    best_role = None

            if best_role:
                return {
                    "matched": True,
                    "role_id": best_role["id"],
                    "role_name": best_role["name"],
                    "category": best_role.get("category", "Tecnología"),
                    "icon": best_role.get("icon", "💼"),
                    "is_enabled": best_role.get("enabled", True),
                    "is_allowed": best_role.get("enabled", True)
                }
        
        # Si no coincidió con ningún rol explícito, verificar si es un rol genuino de TI
        is_real_tech = any(re.search(rf'\b{re.escape(k)}\b', title_lower) for k in tech_affirmative)
        if is_real_tech:
            return {
                "matched": True,
                "role_id": "general_sistemas",
                "role_name": "Ingeniería de Sistemas / TI General",
                "category": "Sistemas",
                "icon": "⚙️",
                "is_enabled": True,
                "is_allowed": True
            }

        return {
            "matched": False,
            "role_id": "non_tech",
            "role_name": "No afín a Sistemas (Descartado)",
            "category": "No Afín",
            "icon": "🚫",
            "is_enabled": False,
            "is_allowed": False
        }

    def analyze_requirements_fit(self, title: str, description: str, company: str, location: str = "") -> Dict[str, Any]:
        """
        Analiza exhaustivamente una vacante frente al perfil de un Ingeniero de Sistemas
        sin experiencia laboral previa (Búsqueda de primer empleo formal).
        Retorna un desglose detallado con lo que SÍ cumplimos, lo que NO cumplimos y la estrategia.
        """
        title_lower = title.lower()
        desc_lower = (description or "").lower()
        full_text = f"{title_lower} {desc_lower}"

        cumplimos = []
        no_cumplimos = []
        score = 0.5
        reasons = []

        # 0.0 Filtro Absoluto Anti-Explotación / Sin Remuneración (Ad Honorem, Voluntariado, Sin Sueldo)
        unpaid_disqualifiers = [
            "ad honorem", "ad-honorem", "adhonorem", "sin remuneración", "sin remuneracion",
            "sin sueldo", "sin goce", "no remunerado", "unpaid", "voluntario", "voluntariado",
            "a comisión pura", "comisión pura", "comisiones puras"
        ]
        if any(ud in full_text for ud in unpaid_disqualifiers):
            no_cumplimos.append("Filtro Salarial: Oferta no remunerada / Ad Honorem descartada")
            return {
                "score": 0.0,
                "reason": "Descartada: Práctica o empleo no remunerado (Ad Honorem / Sin Sueldo).",
                "cumplimos": cumplimos,
                "no_cumplimos": no_cumplimos,
                "estrategia": "Descarte automático: El candidato busca empleo o prácticas remuneradas.",
                "is_recommended": False,
                "target_role": "No Remunerado (Descartado)",
                "target_role_id": "disqualified_unpaid",
                "target_role_enabled": False
            }

        # 0. Filtro Estricto Anti-No-Tech (Contabilidad, Impuestos, Ventas, Finanzas, Salud, Oficios, Sostenibilidad, Pricing, RRHH)
        non_tech_disqualifiers = [
            # Sostenibilidad, Medio Ambiente y Seguridad Ocupacional
            "sostenibilidad", "medio ambiente", "ambiental", "seguridad e higiene", "seguridad industrial",
            "seguridad y salud en el trabajo", "higiene", "somma", "ssoma", "hse",
            # Pricing, Finanzas no tech, Tesorería y Facturación
            "pricing", "revenue management", "revenue", "facturación", "facturacion", "tesorería", "tesoreria",
            "planeamiento financiero", "finanzas", "asistente contable", "asistente financiero", "tax specialist",
            "finance trainee", "banca corporativa", "banca comercial", "cajero", "créditos", "creditos",
            # Ventas y Comercial
            "ventas", "venta", "comercial", "televentas", "teleoperador", "cobranza", "cobranzas",
            "prospección", "promotor", "ejecutivo comercial", "asesor comercial", "cross-selling",
            # Contabilidad, Finanzas y Tributación
            "contable", "contabilidad", "impuestos", "tributari", "auditoría contable", "auditoria contable",
            # Operaciones manuales, Logística administrativa y Almacén
            "almacén", "almacenes", "logística", "logistica", "compras", "arrendamiento", "inventarios",
            "impulsadora", "anfitriona", "mozo", "camarero", "cocinero", "limpieza", "seguridad física",
            # No-IT Engineering & Oficios
            "contra incendio", "contra incendios", "sistemas de bombeo", "cadista", "dibujante técnico",
            "dibujante tecnico", "ingeniería civil", "ingenieria civil", "minería", "mineria", "mantenimiento mecánico",
            # Audiovisual, Marketing no técnico y Diseño Gráfico
            "audiovisual", "audiovisuales", "editor de video", "diseñador gráfico", "diseñador grafico",
            "diseño gráfico", "diseño grafico", "creación de contenido", "creacion de contenido",
            "community manager", "social media", "paid media",
            # Salud, Psicología y RRHH administrativo
            "psicología", "psicologia", "psicólogo", "psicologo", "enfermera", "enfermería", "enfermeria",
            "médico", "medico", "medicina", "clinician", "behavioral health", "people ops", "employee experience",
            "reclutamiento y seleccion", "reclutamiento", "seleccion de personal"
        ]
        
        tech_protective_keywords = [
            "desarrollador", "developer", "software", "sistemas", "soporte ti", "helpdesk",
            "mesa de ayuda", "qa", "tester", "testing", "base de datos", "sql", "programador"
        ]
        is_disqualified_domain = any(nd in title_lower for nd in non_tech_disqualifiers)
        has_tech_protection = any(tp in title_lower for tp in tech_protective_keywords)

        if is_disqualified_domain and not has_tech_protection:
            no_cumplimos.append("Filtro Estricto: Oferta fuera del área de Sistemas / TI (Descartada)")
            return {
                "score": 0.0,
                "reason": "Descartada: Oferta no afín a Ingeniería de Sistemas (Contabilidad, Ventas, Finanzas, Salud u Oficios).",
                "cumplimos": cumplimos,
                "no_cumplimos": no_cumplimos,
                "estrategia": "Descarte automático: Puesto fuera del alcance profesional del candidato.",
                "is_recommended": False,
                "target_role": "No afín a Sistemas (Descartado)",
                "target_role_id": "disqualified_non_tech",
                "target_role_enabled": False
            }

        # 0.1 Verificación de Puesto Laboral Objetivo Seleccionado por el Candidato
        role_match = self.match_job_to_role(title, description)
        matched_role_name = role_match["role_name"]
        matched_role_id = role_match["role_id"]
        is_role_allowed = role_match["is_allowed"]

        if not is_role_allowed:
            no_cumplimos.append(f"Puesto no seleccionado: El puesto '{matched_role_name}' está pausado en tus preferencias.")
            return {
                "score": 0.10,
                "reason": f"Descartada: El puesto '{matched_role_name}' fue pausado por el usuario en sus preferencias.",
                "cumplimos": cumplimos,
                "no_cumplimos": no_cumplimos,
                "estrategia": f"Descarte automático: Puesto '{matched_role_name}' desactivado para postulación.",
                "is_recommended": False,
                "target_role": matched_role_name,
                "target_role_id": matched_role_id,
                "target_role_enabled": False
            }
        else:
            cumplimos.append(f"Puesto Laboral Autorizado: {matched_role_name}")

        # 1. Análisis de Formación y Titulación
        degree_name = self.profile.get("education", {}).get("degree", "Ingeniería de Sistemas")
        cumplimos.append(f"Formación Académica: Graduado / Egresado en {degree_name}")

        # 2. Análisis de Modalidad: 100% REMOTO ESTRICTO
        is_remote = any(k in full_text for k in ["remoto", "remote", "teletrabajo", "home office", "work from home", "desde casa"])
        is_presencial_only = any(k in full_text for k in ["100% presencial", "trabajo en oficina", "presencial en sede", "asistencia diaria a oficina"]) or ("presencial" in full_text and not is_remote)

        if is_remote:
            cumplimos.append("Modalidad de Trabajo: 100% Remoto (Cumple política estricta)")
            score += 0.25
        elif is_presencial_only:
            no_cumplimos.append("Modalidad: Oferta Presencial (Descartada por política 100% Remoto)")
            return {
                "score": 0.05,
                "reason": "Descartada: Exige trabajo presencial en oficina. El candidato requiere 100% Remoto.",
                "cumplimos": cumplimos,
                "no_cumplimos": no_cumplimos,
                "estrategia": "Descarte automático: Oferta no remota.",
                "is_recommended": False
            }
        else:
            # Si no especifica explícitamente pero no dice presencial
            cumplimos.append("Modalidad: Remota / Teletrabajo")
            score += 0.10

        # 3. Análisis de Salario (Línea obligatoria: > S/ 2,000 PEN o > $800 USD)
        low_salary_patterns = [
            "sueldo mínimo", "sueldo basico", "remuneracion minima", "1025", "1,025",
            "1200 soles", "1,200 soles", "1500 soles", "1,500 soles", "1800 soles", "1,800 soles",
            "300 usd", "400 usd", "500 usd", "600 usd"
        ]
        if any(bad_sal in full_text for bad_sal in low_salary_patterns):
            no_cumplimos.append("Salario: Oferta por debajo de la línea salarial mínima (> S/ 2,000 / > $800 USD)")
            return {
                "score": 0.05,
                "reason": "Descartada: Salario publicado inferior al mínimo establecido (Mínimo > S/ 2,000 PEN o > $800 USD).",
                "cumplimos": cumplimos,
                "no_cumplimos": no_cumplimos,
                "estrategia": "Descarte automático: No cumple con la pretensión económica requerida.",
                "is_recommended": False
            }
        else:
            cumplimos.append("Rango Salarial: Compatible con pretensión económica (> S/ 2,000 PEN / > $800 USD)")
            score += 0.10

        # 4. Stack Técnico y Habilidades Comprobadas
        skills_matched = []
        key_skills = ["python", "javascript", "sql", "react", "node", "git", "java", "c#", "docker", "qa", "testing", "api"]
        for sk in key_skills:
            if sk in full_text:
                skills_matched.append(sk.capitalize())

        if skills_matched:
            cumplimos.append(f"Habilidades Técnicas: Dominio práctico en {', '.join(skills_matched[:4])}")
            score += 0.15
        else:
            cumplimos.append("Habilidades Técnicas: Bases de desarrollo de software y algoritmos de Sistemas")

        # Proyectos prácticos en GitHub para compensar
        cumplimos.append("Proyectos Comprobables: Repositorio en GitHub con APIs y desarrollo web")
        cumplimos.append("Disponibilidad: Incorporación inmediata a tiempo completo (Remoto)")

        # 5. Experiencia Previa: Primer Empleo formal
        senior_keywords = ["senior", "sr.", "sr ", "lead", "principal", "arquitecto", "tech lead", "manager", "5+ años", "5 años", "4 años"]
        is_senior = any(kw in full_text for kw in senior_keywords)

        junior_keywords = ["junior", "jr", "trainee", "practicante", "entry level", "entry-level", "sin experiencia", "recién egresado", "primer empleo", "asistente"]
        is_junior = any(kw in full_text for kw in junior_keywords)

        if is_senior:
            no_cumplimos.append("Experiencia Laboral: La oferta exige nivel Senior/Lead (5+ años de experiencia previa)")
            score = 0.10
            reasons.append("Puesto Senior descartado para primer empleo")
            estrategia = "No recomendada: Puesto con barrera de entrada Senior alta. Conviene enfocar esfuerzos en vacantes Junior."
            is_rec = False
        elif is_junior:
            no_cumplimos.append("Experiencia Formal Previa: Candidato busca su primer empleo formal (compensado con proyectos)")
            score = max(score + 0.20, 0.88)
            reasons.append("Vacante 100% remota ideal para recién egresados y nivel Junior")
            estrategia = "¡Oportunidad óptima! La empresa busca talento en formación y valora las bases universitarias y proyectos prácticos."
            is_rec = True
        else:
            # Si pide 1 o 2 años
            no_cumplimos.append("Experiencia Formal: Podría solicitar 1 a 2 años de experiencia previa en empresas")
            score = max(min(score + 0.10, 0.78), 0.55)
            reasons.append("Vacante intermedia afín a Sistemas")
            estrategia = "Postulación viable: Aunque mencionen experiencia previa, el perfil compensa con proyectos en GitHub y formación en Sistemas."
            is_rec = True

        reason_text = "; ".join(reasons) if reasons else "Afinidad técnica con perfil de Sistemas 100% Remoto"

        return {
            "score": min(max(round(score, 2), 0.10), 0.98),
            "reason": reason_text,
            "cumplimos": cumplimos,
            "no_cumplimos": no_cumplimos,
            "estrategia": estrategia,
            "is_recommended": is_rec,
            "target_role": matched_role_name,
            "target_role_id": matched_role_id,
            "target_role_enabled": is_role_allowed
        }

    def evaluate_job_fit(self, title: str, description: str, company: str, location: str = "") -> Tuple[float, str]:
        """Wrapper compatible con los adaptadores existentes."""
        res = self.analyze_requirements_fit(title, description, company, location)
        return res["score"], res["reason"]

    def answer_screening_question(
        self,
        question_text: str,
        options: Optional[List[str]] = None,
        location: str = "",
        platform: str = ""
    ) -> str:
        """
        Responde inteligentemente a una pregunta de filtro o cuestionario de postulación
        utilizando la base de conocimiento del candidato, respetando estrictamente:
        - Si la oferta es de PERÚ (Computrabajo, Bumeran, Lima, etc.) -> Pretensión en SOLES (>= S/ 2,000 PEN).
        - Si la oferta es FUERA DE PERÚ (Internacional, Global, LatAm, USA) -> Pretensión en DÓLARES (>= $800 USD).
        - Modalidad 100% remota.
        """
        q_clean = question_text.lower().strip()
        screening = self.profile.get("screening_answers", {})
        skills = self.profile.get("skills", {})
        personal = self.profile.get("personal_info", {})

        loc_lower = (location or "").lower()
        plat_lower = (platform or "").lower()

        # Determinar origen de la oferta (Perú vs Internacional)
        is_peru_origin = (
            plat_lower in ["computrabajo", "bumeran"] or
            any(k in loc_lower for k in ["perú", "peru", "lima", "arequipa", "san isidro", "miraflores", "callao", "trujillo", "chiclayo", "cusco", "piura"]) or
            bool(re.search(r'\bpe\b', loc_lower))
        )

        # Si la pregunta exige explícitamente una moneda, prevalece lo requerido por el formulario
        # Usamos límites de palabra (\b) para evitar falsos positivos como 'pen' dentro de 'compensation'
        has_explicit_usd = bool(re.search(r'\b(usd|dólar|dolar|dólares|dolares|dollars?)\b', q_clean))
        has_explicit_pen = bool(re.search(r'\b(pen|soles|s/\.?|moneda local)\b', q_clean)) or "soles" in q_clean or "s/." in q_clean

        if has_explicit_usd:
            is_soles = False
            is_usd = True
        elif has_explicit_pen:
            is_soles = True
            is_usd = False
        else:
            # Según procedencia geográfica de la vacante
            if is_peru_origin:
                is_soles = True
                is_usd = False
            else:
                is_soles = False
                is_usd = True

        # Si hay Gemini configurado, responder con IA
        if self.client:
            try:
                options_str = f"Opciones disponibles: {options}" if options else "Pregunta abierta."
                moneda_prompt = "Soles (PEN) superior a S/ 2,000 (S/ 2,200 - 2,800)" if is_soles else "Dólares (USD) superior a 800 USD (850 - 1,200 USD)"
                github_url = personal.get('github_url', 'https://github.com/JackMBerrocal')
                linkedin_url = personal.get('linkedin_url', 'https://www.linkedin.com/in/jackmberrocal')
                portfolio_url = personal.get('portfolio_url', github_url)
                prompt = f"""
                Eres el asistente de postulación de un Ingeniero de Sistemas que busca su primer empleo formal.
                Perfil del candidato:
                - Título: {self.profile.get('education', {}).get('degree', 'Ingeniería de Sistemas')}
                - Proyectos realizados: {self.profile.get('projects', [])}
                - GitHub / Repositorio: {github_url}
                - LinkedIn: {linkedin_url}
                - Portafolio: {portfolio_url}
                - Habilidades: {skills}
                - Disponibilidad: Inmediata
                - Modalidad obligatoria: 100% Remoto
                - Origen de la vacante: {'Perú (Responder en SOLES)' if is_soles else 'Fuera de Perú / Internacional (Responder en DÓLARES USD)'}
                - Pretensión salarial requerida: {moneda_prompt}
                
                Pregunta del formulario de postulación: "{question_text}"
                {options_str}
                
                Instrucciones:
                - Si pide un enlace a GitHub, perfil de GitHub o repositorio de proyectos, responde exactamente con: {github_url}
                - Si pide un enlace a LinkedIn o perfil profesional, responde exactamente con: {linkedin_url}
                - Si pide un portafolio web o enlace a código, responde con: {portfolio_url}
                - Si es una pregunta de opciones, elige exactamente una de las opciones disponibles.
                - Si pide un número para salario en Soles, pon 2200. Si es en Dólares, pon 850.
                - Si pide años de experiencia en una tecnología que domina por proyectos, responde con un número entero (ej. 1).
                - Si es una pregunta abierta, sé profesional, conciso y destaca proyectos prácticos y motivación.
                - Responde ÚNICAMENTE con la respuesta final para el formulario, sin saludos ni explicaciones.
                """
                resp = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                reply = (resp.text or "").strip()
                if options:
                    for opt in options:
                        if opt.lower() == reply.lower() or reply.lower() in opt.lower():
                            return opt
                return reply
            except Exception as e:
                print(f"[LLMEngine] Fallback en respuesta a pregunta: {e}")

        # Reglas heurísticas y respuestas estructuradas por categoría (100% basadas en el CV de Jack Michael Berrocal)
        github_url = personal.get("github_url", "https://github.com/JackMBerrocal")
        linkedin_url = personal.get("linkedin_url", "https://www.linkedin.com/in/jackmberrocal")
        portfolio_url = personal.get("portfolio_url", github_url)

        # 1. Enlaces a perfiles profesionales y repositorios (Uso estricto de límite de palabra para no chocar con 'reporte')
        if "linkedin" in q_clean:
            return linkedin_url
        if bool(re.search(r'\b(github|portafolio|portfolio)\b', q_clean)) or (bool(re.search(r'\b(repositorio|repositorios|repo)\b', q_clean)) and "reporte" not in q_clean):
            if any(k in q_clean for k in ["cuentas con", "tienes", "posees", "proyectos prácticos", "verificable", "portafolio verificable"]):
                return f"Sí, cuento con proyectos prácticos con código fuente documentado y de acceso público en mi GitHub: {github_url}. Entre ellos destacan mi Plataforma de Gestión y Automatización de Procesos (Python/FastAPI/PostgreSQL/Postman) y mi Laboratorio de Soporte, Diagnóstico de Redes y Configuración de Sistemas (Active Directory/Linux)."
            return github_url

        # 2. Formación Académica, Carrera, Grado o Universidad (Verificar ANTES de filtros de sede/ubicación)
        salary_conflict_kws = ["salario", "salarial", "pretensión", "pretension", "sueldo", "remuneración", "remuneracion", "cuánto deseas", "cuanto deseas", "aspiración", "aspiracion"]
        is_salary_question = any(sk in q_clean for sk in salary_conflict_kws)
        academic_kws = [
            "formación académica", "formacion academica", "formación", "formacion",
            "carrera", "qué estudiaste", "que estudiaste", "grado", "universidad",
            "estudios", "egresado", "bachiller", "titulado", "educación", "educacion",
            "académica", "academica", "titulación", "titulacion"
        ]
        has_academic_kw = any(k in q_clean for k in academic_kws) or bool(re.search(r'\b(profesión|profesion)\b', q_clean))
        if has_academic_kw and not is_salary_question and not any(k in q_clean for k in ["años de experiencia", "years of experience"]):
            if options:
                for opt in options:
                    if any(w in opt.lower() for w in ["universitari", "superior", "egresado", "bachiller", "sistemas", "completo"]):
                        return opt
            return "Soy egresado de la carrera de Ingeniería de Sistemas en Lima, Perú. Cuento con sólida formación técnica orientada a ingeniería de software, arquitectura de sistemas, diagnóstico de redes, administración de bases de datos relacionales y aseguramiento de la calidad (QA)."

        # 3. Reporte de bugs y documentación de calidad (QA)
        if any(k in q_clean for k in ["reporte y documentación de bugs", "reporte de bugs", "documentación de bugs", "documentacion de bugs", "reporte de incidencias", "cómo estructuras el reporte", "como estructuras el reporte", "matrices de prueba", "matriz de prueba"]):
            return "Estructuro el reporte de incidencias con rigor metodológico: título descriptivo y conciso, nivel de severidad y prioridad, precondiciones del entorno de prueba, pasos exactos y numerados para la reproducción del fallo, resultado esperado vs. resultado obtenido, evidencias gráficas o logs adjuntos, y seguimiento formal del ciclo de vida del bug mediante Jira Service Management."

        # 4. Ticketing y Asistencia Remota en Soporte TI
        if any(k in q_clean for k in ["ticketing", "herramientas de ticketing", "asistencia remota", "soporte remoto", "anydesk", "teamviewer", "glpi", "atención de usuarios", "atencion de usuarios", "resolución de incidencias"]):
            return "Cuento con experiencia práctica gestionando tickets de soporte bajo acuerdos de nivel de servicio (SLA) con Jira Service Management y GLPI. Para soporte remoto y diagnóstico en estaciones de trabajo y clientes, utilizo herramientas como AnyDesk y TeamViewer, asegurando resolución sistemática y comunicación asertiva con el usuario."

        # 5. Active Directory, Redes y Sistemas Operativos
        if any(k in q_clean for k in ["active directory", "redes tcp/ip", "redes", "tcp/ip", "windows 10/11", "ubuntu linux", "sistemas operativos", "diagnóstico de redes", "diagnostico de redes"]):
            return "Manejo administración básica de Active Directory (gestión de usuarios, grupos y permisos de acceso), diagnóstico de conectividad de redes LAN/WAN (TCP/IP, DNS, DHCP, VPN) con herramientas nativas (ping, traceroute, nslookup, netstat) y soporte en sistemas operativos Windows 10/11 y Linux (Ubuntu)."

        # 6. Tipos de pruebas y validación de APIs con Postman
        if any(k in q_clean for k in ["tipos de pruebas", "tipo de pruebas", "smoke testing", "pruebas funcionales", "postman", "validación de apis", "validacion de apis", "testing", "qa", "pruebas de software"]):
            return "Cuento con formación y proyectos prácticos en control de calidad (QA): diseño y ejecución de casos de prueba funcionales, regresión y smoke testing. Domino la validación y pruebas de endpoints de APIs REST con Postman (verificación de códigos de estado HTTP, validación de estructuras JSON y tiempos de respuesta), así como la verificación de consistencia mediante consultas SQL."

        # 7. Preguntas técnicas específicas y retos de código
        if any(k in q_clean for k in ["problema más interesante", "problema que resolviste con código", "reto técnico", "proyecto más interesante", "resolviste con código"]):
            return "En mi proyecto de Plataforma de Automatización de Procesos con Python y FastAPI, el reto más interesante fue estructurar la capa de persistencia con PostgreSQL optimizando consultas SQL complejas para evitar cuellos de botella bajo concurrencia. Implementé validaciones estrictas en la API, diseño estructurado de consultas e índices, y cobertura de pruebas con Postman y Pytest, garantizando integridad de datos y tiempos de respuesta mínimos."

        if any(k in q_clean for k in ["nivel y alcance tienes en python", "nivel en python", "experiencia en python", "alcance en python", "python"]):
            if options:
                for opt in options:
                    if any(w in opt.lower() for w in ["intermedio", "intermediate", "medio"]):
                        return opt
            return "Cuento con un nivel intermedio sólido en Python. Desarrollo APIs REST con FastAPI y Django básico, estructurando endpoints seguros con autenticación, validación de esquemas y conexión a bases de datos relacionales con SQLAlchemy ORM. Aplico principios de Clean Code y control de versiones con Git/GitHub."

        if any(k in q_clean for k in ["alcance en el uso de las ia", "uso de las ia", "copilot", "chatgpt", "claude", "cursor", "inteligencia artificial"]):
            return "Utilizo de forma cotidiana herramientas de IA asistida (GitHub Copilot, Cursor, ChatGPT y Claude) integradas en mi entorno de desarrollo para acelerar flujos de trabajo, análisis de código, depuración y creación de tests unitarios. A nivel de integración de software, cuento con conocimientos consumiendo APIs de modelos LLM en servicios backend en Python para automatizar el procesamiento estructurado de información."

        # 8. Bases de Datos y SQL
        if any(k in q_clean for k in ["bases de datos", "base de datos", "sql", "postgresql", "mysql"]):
            return "Manejo bases de datos relacionales con SQL a nivel intermedio (PostgreSQL, MySQL y SQLite). Realizo diseño de esquemas entidad-relación, consultas complejas con JOINs, filtros, agrupaciones y transacciones conectadas a aplicaciones backend en Python mediante SQLAlchemy ORM."

        # 9. Salario / Pretensiones Económicas (Estrictamente >= S/ 2,000 PEN / >= $600 USD)
        salary_keywords = [
            "expectativa", "expectativas", "salario", "salarial", "salariales",
            "pretensión", "pretension", "pretensiones", "remuneración", "remuneracion",
            "sueldo", "sueldos", "salary", "compensation", "aspiración", "aspiracion",
            "aspiraciones", "honorarios", "cuánto deseas ganar", "cuanto deseas ganar",
            "cuánto pretendes", "cuanto pretendes", "expected salary", "desired salary",
            "expected compensation", "tarifa", "wage", "deseas percibir"
        ]
        if any(k in q_clean for k in salary_keywords):
            if any(k in q_clean for k in ["número", "monto", "cifra", "ingrese valor", "solo número", "solo valor", "numérica", "number"]):
                return "2200" if is_soles else "650"

            if options:
                if is_soles:
                    target_kws = ["2000", "2200", "2500", "2,000", "2,200", "2,500", "soles", "pen"]
                    for opt in options:
                        if any(k in opt.lower() for k in target_kws):
                            return opt
                else:
                    for opt in options:
                        if any(k in opt.lower() for k in ["600", "650", "700", "800", "usd", "dólares", "dolares"]):
                            return opt
                return options[0]

            if is_soles:
                return "Mi pretensión salarial es a partir de S/ 2,200 - 2,500 soles mensuales, abierta a evaluación y negociación según el paquete de beneficios."
            else:
                return "Mi pretensión salarial es a partir de $650 - 850 USD mensuales para contrato remoto, abierta a evaluación según el paquete de beneficios."

        # 10. Nivel de inglés (Básico / Técnico)
        if any(k in q_clean for k in ["inglés", "ingles", "english", "idioma"]):
            if options:
                # 1ro: Priorizar explícitamente básico / técnico / A2
                for opt in options:
                    if any(lvl in opt.lower() for lvl in ["básico", "basico", "técnico", "tecnico", "a2", "elemental", "inicial"]):
                        return opt
                # 2do: Si solo hay Intermedio o Avanzado, elegir la opción más accesible
                for opt in options:
                    if any(lvl in opt.lower() for lvl in ["intermedio", "intermediate", "medio", "b1"]):
                        return opt
                return options[0]
            return "Nivel Básico / Técnico (A2). Cuento con comprensión y lectura de documentación técnica, código y manuales; comunicación fluida y nativa en español."

        # 11. Disponibilidad horaria y modalidad de trabajo (100% Remoto)
        if any(k in q_clean for k in ["disponibilidad", "incorporación", "incorporacion", "cuándo puedes empezar", "fecha de inicio", "availability", "remoto", "modalidad", "home office", "teletrabajo", "remote", "presencial", "híbrido", "hibrido", "horaria"]):
            if options:
                for opt in options:
                    if any(k in opt.lower() for k in ["remoto", "remote", "teletrabajo", "inmediata", "inmediato", "100%"]):
                        return opt
            return "Cuento con disponibilidad inmediata a tiempo completo para modalidad 100% remota, equipado con computadora propia de alto rendimiento, conexión de fibra óptica estable y herramientas de colaboración en línea."

        # 12. Experiencia Previa y Búsqueda de Primer Empleo Formal
        if any(k in q_clean for k in ["empresa anterior", "empresa actual", "última empresa", "compañía", "empleador", "company"]):
            return "Proyectos Académicos y de Laboratorio en Ingeniería de Sistemas (Búsqueda de Primer Empleo Formal)"

        if any(k in q_clean for k in ["cargo", "puesto", "rol anterior", "rol actual", "job title", "ocupación", "posición"]):
            return "Desarrollador / Analista QA en proyectos prácticos de Sistemas"

        if any(k in q_clean for k in ["motivo de salida", "razón de salida"]):
            return "Culminación de estudios universitarios / Graduación en Ingeniería de Sistemas"

        if any(k in q_clean for k in ["experiencia previa", "experiencia laboral formal", "experiencia formal"]):
            if options:
                for opt in options:
                    if any(w in opt.lower() for w in ["sin experiencia", "no", "primer empleo", "recién egresado"]):
                        return opt
            return "Egresado de Ingeniería de Sistemas en búsqueda de mi primer empleo formal; compenso con proyectos prácticos verificables en mi repositorio de GitHub."

        if any(k in q_clean for k in ["años de experiencia", "years of experience", "cuantos años", "tiempo de experiencia"]):
            tech_match = any(t.lower() in q_clean for t in ["python", "javascript", "react", "sql", "sistemas", "software", "program", "qa", "pruebas", "soporte"])
            if tech_match:
                return "1"
            return "0"

        # 13. Motivación / Por qué deberíamos contratarte / Cuéntanos de ti
        if any(k in q_clean for k in ["¿por qué", "por qué deberíamos contratarte", "por que deberiamos contratarte", "motivación", "motivacion", "cuéntanos de ti", "cuentanos de ti", "sobre ti"]):
            return (
                "Soy egresado de Ingeniería de Sistemas con sólida preparación técnica en desarrollo de software (Python/SQL), control de calidad (QA Testing) y soporte de infraestructura TI. "
                "Me distingo por mi capacidad de aprendizaje rápido, pensamiento analítico, disciplina técnica y proactividad. Cuento con proyectos prácticos comprobables en GitHub y un alto compromiso "
                "para integrarme al equipo y aportar soluciones eficientes desde el primer día."
            )

        # 14. Respuestas a opciones booleanas (Sí / No)
        if options:
            negative_questions = ["antecedentes penales", "antecedentes policiales", "enfermedad inhabilitante", "conflicto de interés"]
            if any(nq in q_clean for nq in negative_questions):
                for opt in options:
                    if opt.strip().lower() in ["no", "falso", "false"]:
                        return opt
            for opt in options:
                if opt.strip().lower() in ["sí", "si", "yes", "verdadero", "true"]:
                    return opt
            return options[0]

        return "Cuento con las competencias técnicas requeridas, formación en Ingeniería de Sistemas y disponibilidad inmediata para aportar al equipo."

    RHETORICAL_PATTERNS = [
        r'\bbuscamos\b', r'\bofrecemos\b', r'\bquiénes somos\b', r'\bquienes somos\b',
        r'\bsobre nosotros\b', r'\bbeneficios\b', r'\bte gustaría\b', r'\bte gustaria\b',
        r'\bsabías\b', r'\bsabias\b', r'\bte apasiona\b', r'\bpor qué unirte\b', r'\bpor que unirte\b',
        r'\bpor qué trabajar\b', r'\bpor que trabajar\b', r'\bpor qué nosotros\b', r'\brequisitos\b',
        r'\btienes que hacer\b', r'\bqué harás\b', r'\bque haras\b', r'\brealizarás\b', r'\brealizaras\b',
        r'\btus retos\b', r'\btus funciones\b', r'\btus responsabilidades\b', r'\bprincipales retos\b',
        r'\bpostula\b', r'\brecién egresado\b', r'\brecien egresado\b', r'\bnuestro equipo\b'
    ]

    @classmethod
    def extract_real_questions(cls, text: str) -> List[str]:
        """Extrae únicamente preguntas reales formuladas al candidato, descartando títulos retóricos."""
        if not text:
            return []
        raw_matches = re.findall(r'¿([^?]+)\?', text)
        detected = []
        for q in raw_matches:
            q_clean = q.strip()
            q_low = q_clean.lower()
            if len(q_clean) >= 14:
                is_rhetorical = any(re.search(p, q_low) for p in cls.RHETORICAL_PATTERNS)
                if not is_rhetorical:
                    full_q = f"¿{q_clean}?"
                    if full_q not in detected:
                        detected.append(full_q)
        return detected

    def get_job_screening_questions(
        self,
        job_title: str,
        description: str,
        platform: str = "",
        location: str = "",
        company: str = ""
    ) -> Dict[str, Any]:
        """
        Detecta y responde únicamente las preguntas específicas REALES formuladas por el reclutador en la oferta.
        Si la empresa no incluyó preguntas en su convocatoria, retorna lista vacía sin inventar preguntas genéricas.
        """
        raw_text = description or ""
        company_name = company or "el equipo de selección"
        detected_questions = self.extract_real_questions(raw_text)

        # Si la empresa formuló preguntas reales en su convocatoria, responderlas con el CV
        if detected_questions:
            qa_list = []
            for q in detected_questions[:5]:
                ans = self.answer_screening_question(
                    question_text=q,
                    location=location,
                    platform=platform
                )
                qa_list.append({
                    "question": q,
                    "suggested_answer": ans,
                    "is_from_employer": True,
                    "source_label": "🎯 Pregunta explícita del empleador en la convocatoria"
                })

            cover_letter = self.generate_cover_letter(job_title, company_name, description, platform, location)

            return {
                "has_custom_questions": True,
                "has_employer_questions": True,
                "employer_questions_count": len(detected_questions),
                "questions": qa_list,
                "cover_letter": cover_letter,
                "cv_highlights": self.get_cv_summary_highlights(job_title, location, platform)
            }
        else:
            # Caso estándar: La empresa no incluyó preguntas abiertas en el texto.
            # NUNCA inventar ni adivinar preguntas genéricas o al azar.
            cover_letter = self.generate_cover_letter(job_title, company_name, description, platform, location)
            return {
                "has_custom_questions": False,
                "has_employer_questions": False,
                "employer_questions_count": 0,
                "questions": [],
                "cover_letter": cover_letter,
                "cv_highlights": self.get_cv_summary_highlights(job_title, location, platform)
            }

    def generate_cover_letter(self, job_title: str, company: str, description: str = "", platform: str = "", location: str = "") -> str:
        """Genera una carta de presentación formal y profesional adaptada al puesto usando el CV real."""
        personal = self.profile.get("personal_info", {})
        name = personal.get("full_name", "Jack Michael Berrocal")
        phone = personal.get("phone", "+51 963979996")
        email = personal.get("email", "jmberrocale@gmail.com")
        linkedin = personal.get("linkedin_url", "https://www.linkedin.com/in/jackmberrocal")
        github = personal.get("github_url", "https://github.com/JackMBerrocal")

        return (
            f"Estimado equipo de selección de {company},\n\n"
            f"Me dirijo a ustedes con gran interés para presentar mi postulación a la posición de {job_title}. "
            f"Soy egresado de la carrera de Ingeniería de Sistemas en Lima, Perú, con una sólida base técnica en soporte de infraestructura TI, "
            f"control de calidad de software (QA & Testing) y desarrollo backend con Python y bases de datos relacionales (SQL).\n\n"
            f"A lo largo de mi formación y desarrollo de proyectos prácticos he diseñado e implementado soluciones que abarcan desde APIs REST con FastAPI y PostgreSQL "
            f"hasta la configuración de entornos de soporte L1/L2, diagnóstico de conectividad de redes TCP/IP y administración de usuarios en Active Directory. "
            f"Asimismo, cuento con experiencia práctica diseñando matrices de prueba, ejecutando pruebas funcionales y validando endpoints con Postman.\n\n"
            f"Cuento con nivel de inglés B2 (Upper-Intermediate), disponibilidad inmediata y excelente disposición para el trabajo 100% remoto, "
            f"con capacidad de autoaprendizaje continuo y disciplina técnica. Los invito a revisar mis proyectos en mi repositorio de GitHub: {github}.\n\n"
            f"Agradezco de antemano el tiempo dedicado a evaluar mi postulación y quedo a su entera disposición para una entrevista.\n\n"
            f"Atentamente,\n"
            f"{name}\n"
            f"Egresado de Ingeniería de Sistemas\n"
            f"Teléfono: {phone} | Correo: {email}\n"
            f"LinkedIn: {linkedin}"
        )

    def get_cv_summary_highlights(self, job_title: str = "", location: str = "", platform: str = "") -> List[Dict[str, str]]:
        """Devuelve los puntos clave verificados del CV de Jack Michael Berrocal."""
        plat_low = (platform or "").lower()
        loc_low = (location or "").lower()
        is_soles = plat_low in ["computrabajo", "bumeran"] or any(k in loc_low for k in ["perú", "peru", "lima", "callao"])
        salary_text = "S/ 2,200 mensual (negociable)" if is_soles else "$850 USD mensual (negociable)"

        return [
            {"label": "Formación Académica", "value": "Egresado de Ingeniería de Sistemas (Lima, Perú)"},
            {"label": "Especialidades Técnicas", "value": "Soporte TI L1/L2, QA & Testing de APIs/Postman, Python & SQL"},
            {"label": "Proyectos Comprobables", "value": "API REST con FastAPI & PostgreSQL | Lab Virtual de Redes y Active Directory"},
            {"label": "Modalidad de Trabajo", "value": "100% Remoto (Prioritario)"},
            {"label": "Pretensión Salarial", "value": salary_text},
            {"label": "Nivel de Inglés", "value": "B2 - Upper-Intermediate (lectura técnica y comunicación fluida)"},
            {"label": "Disponibilidad", "value": "Inmediata a tiempo completo"},
            {"label": "Currículum Oficial", "value": "CV_Jack_Michael_Berrocal.pdf"},
            {"label": "Contacto", "value": "Jack Michael Berrocal | +51 963979996 | jmberrocale@gmail.com"}
        ]

    def classify_and_draft_email(self, subject: str, sender: str, body: str) -> Dict[str, Any]:
        """
        Analiza un correo entrante de RRHH o portal de empleo:
        Clasifica (interview_invite, coding_challenge, rejection, info)
        y genera un borrador de respuesta profesional.
        """
        text_corpus = f"{subject} {body}".lower()

        # Si Gemini está activo, clasificar y redactar con alta precisión
        if self.client:
            try:
                prompt = f"""
                Analiza el siguiente correo recibido por un candidato a puestos de Ingeniería de Sistemas Junior:
                Remitente: {sender}
                Asunto: {subject}
                Cuerpo: {body[:1500]}
                
                Tareas:
                1. Clasifica la categoría en una de: 'interview_invite', 'coding_challenge', 'rejection', 'info', 'other'.
                2. Si es 'interview_invite' o solicita disponibilidad, redacta una respuesta formal y entusiasta aceptando la entrevista, confirmando disponibilidad completa (o sugiriendo horarios) y agradeciendo el contacto. Firma como: {self.profile.get('personal_info', {}).get('full_name', 'El Candidato')}.
                3. Si es 'coding_challenge', redacta confirmación de recibido indicando que se completará antes de la fecha límite.
                4. Si es 'rejection', redacta un breve y educado mensaje agradeciendo haber sido considerado para futuros procesos.
                
                Responde en formato JSON exacto:
                {{
                   "category": "interview_invite" | "coding_challenge" | "rejection" | "info" | "other",
                   "confidence": 0.95,
                   "summary": "Resumen en 1 frase de lo que pide el reclutador",
                   "proposed_reply": "Texto redactado para responder el correo"
                }}
                """
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                content = response.text or ""
                # Extraer json
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    import json
                    return json.loads(json_match.group(0))
            except Exception as e:
                print(f"[LLMEngine] Fallback en análisis de email: {e}")

        # Heurísticas de Clasificación
        candidate_name = self.profile.get("personal_info", {}).get("full_name", "El Candidato")
        
        # 1. Invitación a entrevista
        interview_kws = ["entrevista", "interview", "videollamada", "meet", "teams", "zoom", "calendly", "agenda", "coordinar reunión"]
        if any(kw in text_corpus for kw in interview_kws):
            return {
                "category": "interview_invite",
                "confidence": 0.88,
                "summary": "Invitación a entrevista o coordinación de reunión",
                "proposed_reply": (
                    f"Estimado/a equipo de selección,\n\n"
                    f"Muchas gracias por la oportunidad de avanzar en el proceso. Con mucho gusto confirmo mi disponibilidad para la entrevista. Quedo atento a la fecha y enlace correspondiente.\n\n"
                    f"Saludos cordiales,\n{candidate_name}"
                )
            }

        # 2. Desafío técnico
        code_kws = ["prueba técnica", "desafío", "coding", "hackerrank", "codility", "evaluación técnica", "test técnico"]
        if any(kw in text_corpus for kw in code_kws):
            return {
                "category": "coding_challenge",
                "confidence": 0.85,
                "summary": "Invitación a prueba o evaluación técnica",
                "proposed_reply": (
                    f"Estimado equipo,\n\n"
                    f"Confirmo la recepción de la prueba técnica. La completaré y enviaré oportunamente antes de la fecha límite establecida.\n\n"
                    f"Muchas gracias por la oportunidad.\n\n"
                    f"Atentamente,\n{candidate_name}"
                )
            }

        # 3. Rechazo
        rejection_kws = ["no continuaremos", "no seleccionado", "otro candidato", "desestimar", "proceso cerrado", "lamentamos informarte"]
        if any(kw in text_corpus for kw in rejection_kws):
            return {
                "category": "rejection",
                "confidence": 0.90,
                "summary": "Aviso de no selección en la vacante",
                "proposed_reply": (
                    f"Estimado equipo,\n\n"
                    f"Agradezco el tiempo dedicado a revisar mi postulación y la retroalimentación. Quedo a su disposición para futuras oportunidades acordes a mi perfil.\n\n"
                    f"Éxitos en el proceso de selección.\n\n"
                    f"Saludos,\n{candidate_name}"
                )
            }

        return {
            "category": "info",
            "confidence": 0.60,
            "summary": "Mensaje informativo o confirmación de postulación",
            "proposed_reply": ""
        }

    def get_best_cv_for_job(self, title: str, description: str = "") -> str:
        """
        Determina dinámicamente cuál de los CVs especializados de Jack
        debe adjuntarse a la postulación según el perfil de la vacante.
        """
        text = f"{title} {description}".lower()
        personal = self.profile.get("personal_info", {})

        # 1. Puestos de Aseguramiento de Calidad / QA / Pruebas de Software
        if any(w in text for w in ["qa", "tester", "testing", "calidad", "pruebas", "postman", "test"]):
            qa_cv = personal.get("cv_qa_path", "data/cv/CV_Jack_Berrocal_QA_Tester.pdf")
            if Path(qa_cv).exists():
                return qa_cv

        # 2. Puestos de Datos / Business Intelligence / Power BI / SQL
        if any(w in text for w in ["power bi", "bi", "data", "datos", "analytics", "sql", "analista de datos"]):
            data_cv = personal.get("cv_data_path", "data/cv/CV_Jack_Berrocal_Data_Analyst.pdf")
            if Path(data_cv).exists():
                return data_cv

        # 3. Default: CV de QA Tester / Sistemas
        default_cv = personal.get("cv_path", "data/cv/CV_Jack_Berrocal_QA_Tester.pdf")
        return default_cv if Path(default_cv).exists() else "data/cv/CV_Jack_Berrocal_QA_Tester.pdf"
