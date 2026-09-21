import re
import urllib.parse
from typing import Optional, Tuple


def normalize_company_name(name: str) -> str:
    """Limpia y da formato profesional al nombre de una empresa."""
    if not name:
        return ""
    name = name.strip()
    
    # Reemplazar guiones o puntos múltiples
    name = re.sub(r'[-_]+', ' ', name)
    
    # Siglas comunes peruanas e internacionales
    acronyms = {
        "s a c": "S.A.C.",
        "s.a.c.": "S.A.C.",
        "s.a.c": "S.A.C.",
        "sac": "S.A.C.",
        "s a a": "S.A.A.",
        "s.a.a.": "S.A.A.",
        "s.a.a": "S.A.A.",
        "saa": "S.A.A.",
        "s a": "S.A.",
        "s.a.": "S.A.",
        "s.a": "S.A.",
        "sa": "S.A.",
        "s r l": "S.R.L.",
        "s.r.l.": "S.R.L.",
        "s.r.l": "S.R.L.",
        "srl": "S.R.L.",
        "bcp": "BCP",
        "bbva": "BBVA",
        "solgas": "SOLGAS",
        "icbc": "ICBC",
        "sanna": "SANNA",
        "g4s": "G4S",
        "ti": "TI",
        "it": "IT",
        "qa": "QA",
        "latam": "LATAM",
        "noc": "NOC",
        "sezzle": "Sezzle",
        "valtx": "Valtx",
        "monnet": "Monnet",
        "panzofi": "Panzofi",
        "netomi": "Netomi"
    }

    words = name.split()
    formatted_words = []
    for w in words:
        wl = w.lower().strip(",.")
        if wl in acronyms:
            formatted_words.append(acronyms[wl])
        elif wl in ["de", "la", "el", "en", "y", "del", "por", "al", "los", "las"]:
            formatted_words.append(wl)
        else:
            formatted_words.append(w.capitalize())

    result = " ".join(formatted_words)
    # Corrección de mayúscula en la primera palabra
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    return result


def extract_company_from_bumeran_url(url: str, title: str = "") -> Optional[str]:
    """
    Extrae el nombre de la empresa a partir de la estructura del slug en URLs de Bumeran.
    Ejemplo: https://www.bumeran.com.pe/empleos/practicante-de-sostenibilidad-solgas-s.a.-1118441906.html
    Retorna: 'SOLGAS S.A.'
    """
    if not url or "bumeran" not in url:
        return None

    # Extraer el path del empleo
    match = re.search(r'/empleos/([^/?#]+)-(\d+)\.html', url)
    if not match:
        return None

    full_slug = match.group(1)  # ej: practicante-de-sostenibilidad-solgas-s.a.
    
    # Si tenemos el título, podemos restar el slug del título
    if title:
        # Normalizar título a slug
        title_slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')
        if full_slug.lower().startswith(title_slug[:18]):
            comp_slug = full_slug[len(title_slug):].strip('-.')
            if comp_slug:
                return normalize_company_name(comp_slug)

    # Intentar separar por partes comunes al final
    parts = full_slug.split('-')
    if len(parts) >= 2:
        for split_idx in range(1, min(7, len(parts))):
            cand_slug = "-".join(parts[-split_idx:])
            if any(term in cand_slug.lower() for term in ["s.a", "sac", "srl", "solgas", "monnet", "valtx", "sanna", "icbc", "wiener", "anddes", "manpower", "falabella", "entel"]):
                return normalize_company_name(cand_slug)

    return None


def resolve_clean_company_name(company: str, url: str = "", title: str = "", description: str = "") -> str:
    """
    Resuelve el nombre limpio y verificado de la empresa descartando
    placeholders genéricos ('Empresa de Tecnología', '4,3', etc.).
    """
    comp_clean = (company or "").strip()
    
    is_rating = bool(re.match(r'^\d+[\.,]\d+$', comp_clean))
    is_generic = comp_clean in [
        "Empresa de Tecnología",
        "Empresa de Tecnologia",
        "Empresa Confidencial",
        "Importante empresa del sector",
        "Importante Empresa",
        "Importante empresa",
        "Destacado",
        "Urgente",
        "4,3",
        "4,1",
        "4.3",
        "4.1",
        "4,0",
        "4,2",
        "4,4",
        "4,5",
        ""
    ] or is_rating

    if not is_generic:
        return comp_clean

    # 1. Intentar deducir desde la URL de Bumeran
    if url and "bumeran" in url:
        from_bumeran = extract_company_from_bumeran_url(url, title)
        if from_bumeran and len(from_bumeran) > 2:
            return from_bumeran

    # 2. Intentar buscar en la descripción si dice 'Empresa: X' o similar
    if description:
        m = re.search(r'(?:empresa|compañía|cliente)\s*:\s*([A-Za-z0-9\.\s\-]{3,40})(?:\n|\.|\,)', description, re.IGNORECASE)
        if m:
            found = m.group(1).strip()
            if not any(bad in found.lower() for bad in ["confidencial", "importante", "tecnología", "destacado"]):
                return normalize_company_name(found)

    # 3. Si era rating en Computrabajo
    if is_rating or "computrabajo" in (url or ""):
        return "Empresa Confidencial (Computrabajo)"

    if comp_clean:
        return comp_clean
    return "Empresa Empleadora"
