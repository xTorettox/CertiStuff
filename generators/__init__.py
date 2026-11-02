import importlib
from . import base_generator
from . import nabors_generator
from . import ypf_iade_generator
from . import ypf_mensual_generator
from . import pluspetrol_generator

from .base_generator import BasePDFGenerator
from .nabors_generator import NaborsPDFGenerator
from .ypf_iade_generator import YPFIADEPDFGenerator
from .ypf_mensual_generator import YPFMensualPDFGenerator
from .pluspetrol_generator import PluspetrolPDFGenerator

def get_generator_by_template(template_type: str) -> BasePDFGenerator:
    """Devuelve la instancia del generador de PDF correspondiente a la plantilla recargando módulos."""
    try:
        importlib.reload(base_generator)
        importlib.reload(nabors_generator)
        importlib.reload(ypf_iade_generator)
        importlib.reload(ypf_mensual_generator)
        importlib.reload(pluspetrol_generator)
    except Exception:
        pass

    tt = str(template_type).lower().strip()
    if "nabors" in tt:
        return nabors_generator.NaborsPDFGenerator()
    elif "iade" in tt:
        return ypf_iade_generator.YPFIADEPDFGenerator()
    elif "mensual" in tt or "plataforma" in tt:
        return ypf_mensual_generator.YPFMensualPDFGenerator()
    elif "pluspetrol" in tt:
        return pluspetrol_generator.PluspetrolPDFGenerator()
    else:
        # Por defecto Nabors
        return nabors_generator.NaborsPDFGenerator()
