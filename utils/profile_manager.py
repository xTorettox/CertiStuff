import os
import json
from typing import Dict, List, Any, Optional

PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "profiles")

class ProfileManager:
    """Gestiona los perfiles y plantillas dinámicas de certificados."""
    
    def __init__(self, profiles_dir: str = PROFILES_DIR):
        self.profiles_dir = profiles_dir
        os.makedirs(self.profiles_dir, exist_ok=True)
        
    def list_profiles(self) -> Dict[str, str]:
        """Devuelve un mapeo {id: nombre_descriptivo}."""
        profiles = {}
        for filename in os.listdir(self.profiles_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.profiles_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        pid = data.get("id", os.path.splitext(filename)[0])
                        pname = data.get("name", pid)
                        profiles[pid] = pname
                except Exception as e:
                    print(f"Error al leer perfil {filename}: {e}")
        return profiles

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Carga los datos completos de un perfil."""
        filepath = os.path.join(self.profiles_dir, f"{profile_id}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_profile(self, profile_data: Dict[str, Any]) -> str:
        """Guarda o actualiza un perfil en disco."""
        pid = profile_data.get("id")
        if not pid:
            name = profile_data.get("name", "perfil_personalizado")
            pid = name.lower().replace(" ", "_").replace("-", "_")
            profile_data["id"] = pid
            
        filepath = os.path.join(self.profiles_dir, f"{pid}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        return pid

    def delete_profile(self, profile_id: str) -> bool:
        """Elimina un perfil personalizado."""
        protected = ["nabors", "ypf_noc_iade", "ypf_noc_mensual", "pluspetrol"]
        if profile_id in protected:
            return False
        filepath = os.path.join(self.profiles_dir, f"{profile_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    @staticmethod
    def calculate_row_total(row: dict, calc_mode: str) -> float:
        """Calcula el total de una fila según la modalidad de tarifa."""
        try:
            # Buscar campos numéricos potenciales
            dias = float(row.get("dias_alq") or row.get("cant_dias") or row.get("DÍAS ALQ") or row.get("CANT DIAS") or 0)
            cantidad = float(row.get("cantidad") or row.get("cant_equipos") or row.get("CANTIDAD") or row.get("CANT EQUIPOS") or 1)
            tarifa = float(row.get("tarifa") or row.get("tarifa_diario") or row.get("TARIFA") or row.get("TARIFA DIARIO") or 0)
            repuestos = float(row.get("repuestos_usd") or row.get("REPUESTOS (USD)") or 0)
            mo = float(row.get("mo_usd") or row.get("MANO DE OBRA Y REPARACIONES (USD)") or 0)
            
            if repuestos > 0 or mo > 0:
                return repuestos + mo
                
            if calc_mode == "diario":
                return (dias * tarifa * cantidad) if cantidad > 0 else (dias * tarifa)
            elif calc_mode == "semanal":
                return ((dias / 7.0) * tarifa * cantidad)
            elif calc_mode == "mensual":
                # Si cantidad es un decimal representativo (ej: 0.667 de mes)
                if 0 < cantidad < 1.0:
                    return cantidad * tarifa
                elif dias > 0:
                    return (dias / 30.0) * tarifa * cantidad
                else:
                    return cantidad * tarifa
            elif calc_mode == "fijo":
                val = row.get("total") or row.get("TOTAL") or row.get("total_rep_mo") or row.get("TOTAL REP.+ MO")
                return float(val) if val is not None else 0.0
            else:
                return dias * tarifa
        except Exception:
            return 0.0
