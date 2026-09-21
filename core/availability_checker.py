import re
from typing import Tuple, Optional
from playwright.async_api import Page, Response


# Patrones textuales y selectores que indican que una oferta expiró, fue cerrada o eliminada
EXPIRED_TEXT_PATTERNS = [
    # Computrabajo
    r"404\s*-\s*página no encontrada",
    r"página no encontrada",
    r"esta oferta (?:de trabajo )?ya no está disponible",
    r"esta oferta ha caducado",
    r"oferta finalizada",
    r"la oferta a la que intentas acceder ya no está activa",
    r"oferta no disponible",
    
    # Bumeran
    r"el aviso ha finalizado",
    r"aviso finalizado",
    r"aviso no disponible",
    r"aviso pausado",
    r"este empleo ya no se encuentra activo",
    r"el aviso no se encuentra disponible",
    
    # Get on Board
    r"esta oferta ha expirado",
    r"este empleo ya no recibe postulaciones",
    r"this job is no longer accepting applications",
    r"this job has expired",
    
    # LinkedIn
    r"no longer accepting applications",
    r"ya no se aceptan solicitudes",
    r"this job is closed",
    r"el empleo ya no está disponible",
    r"esta vacante está cerrada",
    
    # Torre
    r"opportunity closed",
    r"this opportunity has been closed",
    
    # Portales Externos / ATS / Genéricos
    r"job (?:has )?(?:been )?closed",
    r"job no longer available",
    r"position closed",
    r"position is no longer open",
    r"vacante cerrada",
    r"puesto cubierto",
    r"el puesto ha sido cubierto",
    r"la posición ha sido cerrada",
    r"404 not found",
    r"page not found"
]

EXPIRED_SELECTORS = [
    ".b_expired",
    "div[class*='AvisoFinalizado' i]",
    "div[class*='aviso-finalizado' i]",
    "div[class*='expired' i]",
    "div[class*='closed' i]",
    ".job-closed",
    ".badge-expired",
    "div:has-text('El aviso ha finalizado')",
    "div:has-text('Esta oferta ha expirado')",
    "div:has-text('Esta oferta ya no está disponible')",
    "p:has-text('Página no encontrada')",
    "h1:has-text('404')"
]


async def is_job_expired_or_deleted(page: Page, response: Optional[Response] = None) -> Tuple[bool, str]:
    """
    Analiza exhaustivamente la página cargada para determinar si la vacante
    ha expirado, fue eliminada por la empresa, o el enlace arroja error 404.
    
    Retorna: (is_expired: bool, reason: str)
    """
    # 1. Comprobar código de estado HTTP (404 Not Found, 410 Gone)
    if response:
        if response.status in [404, 410]:
            return True, f"Error HTTP {response.status}: La página de la oferta ya no existe (eliminada)."

    curr_url = page.url.lower()

    # 2. Comprobar redirección a páginas de error o búsqueda genérica
    if any(k in curr_url for k in ["/error-404", "/404", "/not-found", "/pagina-no-encontrada"]):
        return True, "Redirección a página de error 404: La vacante fue dada de baja."

    # Si redirigió a la raíz del portal (indicativo típico de empleo borrado)
    clean_url = curr_url.rstrip("/")
    if clean_url in [
        "https://pe.computrabajo.com",
        "https://www.computrabajo.com.pe",
        "https://www.bumeran.com.pe",
        "https://www.bumeran.com.pe/empleos",
        "https://www.getonbrd.com",
        "https://www.getonbrd.com/jobs"
    ]:
        return True, "Redirigido a la página de inicio del portal: La oferta expiró y fue retirada."

    # 3. Comprobar título de la página
    try:
        page_title = (await page.title()).lower()
        if "404" in page_title or "no encontrada" in page_title or "not found" in page_title:
            return True, f"Título de página 404 detectado: '{page_title}'."
    except Exception:
        pass

    # 4. Comprobar selectores específicos de ofertas finalizadas
    for sel in EXPIRED_SELECTORS:
        try:
            elem = await page.query_selector(sel)
            if elem and await elem.is_visible():
                txt = (await elem.inner_text()).strip()[:80]
                return True, f"Elemento de expiración detectado ({sel}): '{txt}'"
        except Exception:
            continue

    # 5. Comprobar patrones de texto en el contenido de la página
    try:
        body_elem = await page.query_selector("body")
        if body_elem:
            body_text = (await body_elem.inner_text()).lower()
            # Limitar longitud para evitar evaluar megabytes
            sample_text = body_text[:12000]
            for pattern in EXPIRED_TEXT_PATTERNS:
                if re.search(pattern, sample_text, re.IGNORECASE):
                    return True, f"Aviso de vacante cerrada detectado: '{pattern}'"
    except Exception:
        pass

    return False, ""
