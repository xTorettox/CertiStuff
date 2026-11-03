import os
import json
import sqlite3
import datetime
from typing import Dict, List, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.db")

class Database:
    """
    Capa de acceso a datos para Certificados Sullair.
    Soporta:
    1. Supabase (PostgreSQL en la nube vía HTTPS / supabase-py con detección inteligente de secrets)
    2. SQLite local (database.db) como respaldo offline y persistencia local inmediata
    """
    def __init__(self):
        self.backend = "sqlite"
        self.supabase_client = None
        self._init_sqlite_tables()
        self._init_connection()

    def _init_sqlite_tables(self):
        """Crea siempre la estructura SQLite para asegurar disponibilidad inmediata y fallback."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        # 1. Clientes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            template_type TEXT NOT NULL DEFAULT 'nabors',
            ultimo_certificado INTEGER NOT NULL DEFAULT 0,
            contrato_nro TEXT DEFAULT '',
            servicio_defecto TEXT DEFAULT '',
            oc_np_defecto TEXT DEFAULT '',
            sucursal TEXT DEFAULT 'Sucursal NQN y Valle',
            direccion TEXT DEFAULT 'Industriales Neuquinos 2920, PIN',
            telefono TEXT DEFAULT 'T:[0299] 4782500',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 2. Lista de Precios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lista_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id TEXT NOT NULL,
            equipo TEXT NOT NULL,
            marca TEXT DEFAULT '-',
            modelo TEXT DEFAULT '-',
            interno TEXT DEFAULT '-',
            tarifa_diaria REAL DEFAULT 0.0,
            tarifa_semanal REAL DEFAULT 0.0,
            tarifa_mensual REAL DEFAULT 0.0,
            modalidad_defecto TEXT DEFAULT 'diario',
            moneda TEXT DEFAULT 'USD',
            observaciones TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 3. Historial de Certificados
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificados_historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            certificado_nro TEXT NOT NULL,
            fecha_emision TEXT NOT NULL,
            servicio_obra TEXT DEFAULT '',
            oc_np TEXT DEFAULT '',
            total_monto REAL DEFAULT 0.0,
            moneda TEXT DEFAULT 'USD',
            usuario TEXT NOT NULL,
            items_count INTEGER DEFAULT 0,
            metadata_json TEXT DEFAULT '{}',
            items_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 4. Firmas de Usuarios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS firmas_usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            nombre_firmante TEXT NOT NULL,
            cargo TEXT NOT NULL,
            alias TEXT NOT NULL,
            firma_png_base64 TEXT NOT NULL,
            is_default INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Insertar clientes base por defecto en SQLite si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM clientes")
        if cursor.fetchone()[0] == 0:
            base_clients = [
                ("nabors", "NABORS", "nabors", 46, "", "F10", "19084166"),
                ("pluspetrol", "PLUSPETROL S.A.", "pluspetrol", 112, "Yacimiento La Calera", "Alquiler Equipos", "4500987621"),
                ("ypf_noc_iade", "YPF NOC - IADE", "ypf_noc_iade", 501013, "4900102848", "Reparaciones", "NOC"),
                ("ypf_noc_mensual", "YPF NOC - Mensual / Plataformas", "ypf_noc_mensual", 4900114308, "4900114308", "Servicio Alquiler", "NOC"),
                ("pae", "PAN AMERICAN ENERGY", "nabors", 101, "Lindero Atravesado", "Servicio Alquiler", "PAE-2026-99"),
                ("vista", "VISTA ENERGY", "pluspetrol", 205, "Bajada del Palo Oeste", "Alquiler Equipos", "VISTA-8841"),
            ]
            cursor.executemany("""
            INSERT INTO clientes (id, nombre, template_type, ultimo_certificado, contrato_nro, servicio_defecto, oc_np_defecto)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, base_clients)

        conn.commit()
        conn.close()

    def _init_connection(self):
        """Conecta a Supabase leyendo tanto variables raíz como secciones de Streamlit secrets."""
        url = None
        key = None
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                # 1. Variables directas en la raíz del secrets.toml
                url = st.secrets.get("SUPABASE_URL") or st.secrets.get("supabase_url")
                key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("supabase_key")
                # 2. Sección [supabase]
                if (not url or not key) and "supabase" in st.secrets:
                    sec = st.secrets["supabase"]
                    if isinstance(sec, dict):
                        url = url or sec.get("url") or sec.get("supabase_url")
                        key = key or sec.get("key") or sec.get("supabase_key")
        except Exception:
            pass

        if not url:
            url = os.environ.get("SUPABASE_URL") or os.environ.get("supabase_url")
        if not key:
            key = os.environ.get("SUPABASE_KEY") or os.environ.get("supabase_key")

        if url and key:
            try:
                from supabase import create_client
                self.supabase_client = create_client(str(url).strip(), str(key).strip())
                self.backend = "supabase"
                print(f"[DB] Conexión establecida exitosamente con Supabase: {url}")
                return
            except Exception as e:
                print(f"[DB] Aviso: No se pudo instanciar cliente Supabase ({e}). Se continúa con SQLite.")

        self.backend = "sqlite"

    def _get_sqlite_conn(self):
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # --- CLIENTES ---
    def _seed_supabase_clientes(self):
        """Puebla la tabla de clientes en Supabase si está recién creada y vacía."""
        if not self.supabase_client:
            return
        base_clients = [
            {"id": "nabors", "nombre": "NABORS", "template_type": "nabors", "ultimo_certificado": 46, "contrato_nro": "", "servicio_defecto": "F10", "oc_np_defecto": "19084166"},
            {"id": "pluspetrol", "nombre": "PLUSPETROL S.A.", "template_type": "pluspetrol", "ultimo_certificado": 112, "contrato_nro": "Yacimiento La Calera", "servicio_defecto": "Alquiler Equipos", "oc_np_defecto": "4500987621"},
            {"id": "ypf_noc_iade", "nombre": "YPF NOC - IADE", "template_type": "ypf_noc_iade", "ultimo_certificado": 501013, "contrato_nro": "4900102848", "servicio_defecto": "Reparaciones", "oc_np_defecto": "NOC"},
            {"id": "ypf_noc_mensual", "nombre": "YPF NOC - Mensual / Plataformas", "template_type": "ypf_noc_mensual", "ultimo_certificado": 4900114308, "contrato_nro": "4900114308", "servicio_defecto": "Servicio Alquiler", "oc_np_defecto": "NOC"},
            {"id": "pae", "nombre": "PAN AMERICAN ENERGY", "template_type": "nabors", "ultimo_certificado": 101, "contrato_nro": "Lindero Atravesado", "servicio_defecto": "Servicio Alquiler", "oc_np_defecto": "PAE-2026-99"},
            {"id": "vista", "nombre": "VISTA ENERGY", "template_type": "pluspetrol", "ultimo_certificado": 205, "contrato_nro": "Bajada del Palo Oeste", "servicio_defecto": "Alquiler Equipos", "oc_np_defecto": "VISTA-8841"},
        ]
        try:
            self.supabase_client.table("clientes").upsert(base_clients).execute()
        except Exception as e:
            print(f"[DB] Aviso inicializando clientes en Supabase: {e}")

    def get_clientes(self) -> List[Dict[str, Any]]:
        if self.supabase_client:
            try:
                res = self.supabase_client.table("clientes").select("*").order("nombre").execute()
                if res.data and len(res.data) > 0:
                    return res.data
                elif res.data == []:
                    self._seed_supabase_clientes()
                    res = self.supabase_client.table("clientes").select("*").order("nombre").execute()
                    if res.data:
                        return res.data
            except Exception as e:
                print(f"[DB] Aviso consulta Supabase get_clientes ({e}), usando SQLite.")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes ORDER BY nombre ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_cliente(self, cliente_id_or_name: str) -> Optional[Dict[str, Any]]:
        target = str(cliente_id_or_name).strip()
        if self.supabase_client:
            try:
                res = self.supabase_client.table("clientes").select("*").eq("id", target.lower()).execute()
                if res.data:
                    return res.data[0]
                res = self.supabase_client.table("clientes").select("*").ilike("nombre", target).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"[DB] Aviso consulta Supabase get_cliente ({e}), usando SQLite.")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM clientes 
            WHERE id = ? OR UPPER(nombre) = UPPER(?) OR UPPER(id) = UPPER(?)
            LIMIT 1
        """, (target, target, target))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def save_cliente(self, cliente_data: Dict[str, Any]) -> str:
        cid = cliente_data.get("id")
        nombre = cliente_data.get("nombre", cid)
        if not cid:
            cid = str(nombre).lower().replace(" ", "_").replace(".", "").replace("-", "_")
        
        template_type = cliente_data.get("template_type", "nabors")
        ultimo_cert = int(cliente_data.get("ultimo_certificado", 0))
        contrato = cliente_data.get("contrato_nro", "")
        servicio = cliente_data.get("servicio_defecto", "")
        oc_np = cliente_data.get("oc_np_defecto", "")
        sucursal = cliente_data.get("sucursal", "Sucursal NQN y Valle")
        direccion = cliente_data.get("direccion", "Industriales Neuquinos 2920, PIN")
        telefono = cliente_data.get("telefono", "T:[0299] 4782500")

        # 1. Supabase
        if self.supabase_client:
            try:
                existing = self.get_cliente(cid)
                if existing and int(existing.get("ultimo_certificado", 0)) > ultimo_cert:
                    ultimo_cert = int(existing["ultimo_certificado"])
                row = {
                    "id": cid,
                    "nombre": nombre,
                    "template_type": template_type,
                    "ultimo_certificado": ultimo_cert,
                    "contrato_nro": contrato,
                    "servicio_defecto": servicio,
                    "oc_np_defecto": oc_np,
                    "sucursal": sucursal,
                    "direccion": direccion,
                    "telefono": telefono
                }
                self.supabase_client.table("clientes").upsert(row).execute()
            except Exception as e:
                print(f"[DB] Aviso Supabase save_cliente ({e}).")

        # 2. SQLite
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clientes (id, nombre, template_type, ultimo_certificado, contrato_nro, servicio_defecto, oc_np_defecto, sucursal, direccion, telefono)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nombre = excluded.nombre,
                template_type = excluded.template_type,
                ultimo_certificado = CASE WHEN excluded.ultimo_certificado > clientes.ultimo_certificado THEN excluded.ultimo_certificado ELSE clientes.ultimo_certificado END,
                contrato_nro = excluded.contrato_nro,
                servicio_defecto = excluded.servicio_defecto,
                oc_np_defecto = excluded.oc_np_defecto,
                sucursal = excluded.sucursal,
                direccion = excluded.direccion,
                telefono = excluded.telefono
        """, (cid, nombre, template_type, ultimo_cert, contrato, servicio, oc_np, sucursal, direccion, telefono))
        conn.commit()
        conn.close()
        return cid

    def increment_ultimo_certificado(self, cliente_id_or_name: str, cert_num: int):
        target = str(cliente_id_or_name).strip()
        if self.supabase_client:
            try:
                cli = self.get_cliente(target)
                if cli:
                    curr = int(cli.get("ultimo_certificado", 0) or 0)
                    if cert_num > curr:
                        self.supabase_client.table("clientes").update({"ultimo_certificado": cert_num}).eq("id", cli["id"]).execute()
            except Exception as e:
                print(f"[DB] Aviso Supabase increment_ultimo_certificado ({e}).")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clientes 
            SET ultimo_certificado = MAX(ultimo_certificado, ?) 
            WHERE id = ? OR UPPER(nombre) = UPPER(?)
        """, (cert_num, target, target))
        conn.commit()
        conn.close()

    # --- HISTORIAL DE CERTIFICADOS ---
    def add_historial(self, cert_data: Dict[str, Any]) -> int:
        cliente = str(cert_data.get("cliente", ""))
        cert_nro = str(cert_data.get("certificado_nro", ""))
        fecha = str(cert_data.get("fecha_emision", datetime.date.today().strftime("%d/%m/%Y")))
        servicio = str(cert_data.get("servicio_obra", ""))
        oc_np = str(cert_data.get("oc_np", ""))
        total = float(cert_data.get("total_monto", 0.0))
        moneda = str(cert_data.get("moneda", "USD"))
        usuario = str(cert_data.get("usuario", "anonimo"))
        items_count = int(cert_data.get("items_count", 0))
        metadata_json = json.dumps(cert_data.get("metadata", {}), ensure_ascii=False)
        items_json = json.dumps(cert_data.get("items", []), ensure_ascii=False)

        if self.supabase_client:
            try:
                payload = {
                    "cliente": cliente,
                    "certificado_nro": cert_nro,
                    "fecha_emision": fecha,
                    "servicio_obra": servicio,
                    "oc_np": oc_np,
                    "total_monto": total,
                    "moneda": moneda,
                    "usuario": usuario,
                    "items_count": items_count,
                    "metadata_json": metadata_json,
                    "items_json": items_json
                }
                self.supabase_client.table("certificados_historial").insert(payload).execute()
            except Exception as e:
                print(f"[DB] Aviso Supabase add_historial ({e}).")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO certificados_historial (
                cliente, certificado_nro, fecha_emision, servicio_obra, oc_np,
                total_monto, moneda, usuario, items_count, metadata_json, items_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cliente, cert_nro, fecha, servicio, oc_np, total, moneda, usuario, items_count, metadata_json, items_json))
        cert_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Actualizar índice del cliente si es numérico
        try:
            clean_digits = "".join(filter(str.isdigit, cert_nro))
            if clean_digits:
                self.increment_ultimo_certificado(cliente, int(clean_digits))
        except Exception:
            pass

        return cert_id or 1

    def get_historial(self, cliente_filtro: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        if self.supabase_client:
            try:
                query = self.supabase_client.table("certificados_historial").select("*").order("id", desc=True).limit(limit)
                if cliente_filtro and cliente_filtro != "TODOS":
                    query = query.ilike("cliente", f"%{cliente_filtro}%")
                res = query.execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"[DB] Aviso Supabase get_historial ({e}), usando SQLite.")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        if cliente_filtro and cliente_filtro != "TODOS":
            cursor.execute("""
                SELECT * FROM certificados_historial
                WHERE UPPER(cliente) = UPPER(?) OR UPPER(cliente) LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (cliente_filtro, f"%{cliente_filtro.upper()}%", limit))
        else:
            cursor.execute("SELECT * FROM certificados_historial ORDER BY id DESC LIMIT ?", (limit,))
        
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    # --- FIRMAS DE USUARIOS ---
    def get_user_signatures(self, usuario: str) -> List[Dict[str, Any]]:
        target_user = str(usuario).strip().lower()
        if self.supabase_client:
            try:
                res = self.supabase_client.table("firmas_usuarios").select("*").ilike("usuario", target_user).order("is_default", desc=True).order("id", desc=True).execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"[DB] Aviso Supabase get_user_signatures ({e}), usando SQLite.")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM firmas_usuarios WHERE UPPER(usuario) = UPPER(?) ORDER BY is_default DESC, id DESC", (target_user,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_user_signature(self, usuario: str, nombre_firmante: str, cargo: str, alias: str, firma_png_base64: str, is_default: bool = False) -> int:
        target_user = str(usuario).strip().lower()
        if self.supabase_client:
            try:
                if is_default:
                    self.supabase_client.table("firmas_usuarios").update({"is_default": 0}).ilike("usuario", target_user).execute()
                payload = {
                    "usuario": target_user,
                    "nombre_firmante": nombre_firmante,
                    "cargo": cargo,
                    "alias": alias,
                    "firma_png_base64": firma_png_base64,
                    "is_default": 1 if is_default else 0
                }
                self.supabase_client.table("firmas_usuarios").insert(payload).execute()
            except Exception as e:
                print(f"[DB] Aviso Supabase save_user_signature ({e}).")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        if is_default:
            cursor.execute("UPDATE firmas_usuarios SET is_default = 0 WHERE UPPER(usuario) = UPPER(?)", (target_user,))
        cursor.execute("""
            INSERT INTO firmas_usuarios (usuario, nombre_firmante, cargo, alias, firma_png_base64, is_default)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (target_user, nombre_firmante, cargo, alias, firma_png_base64, 1 if is_default else 0))
        sig_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return sig_id or 1

    def set_default_signature(self, usuario: str, sig_id: int):
        target_user = str(usuario).strip().lower()
        if self.supabase_client:
            try:
                self.supabase_client.table("firmas_usuarios").update({"is_default": 0}).ilike("usuario", target_user).execute()
                self.supabase_client.table("firmas_usuarios").update({"is_default": 1}).eq("id", sig_id).execute()
            except Exception as e:
                print(f"[DB] Aviso Supabase set_default_signature ({e}).")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE firmas_usuarios SET is_default = 0 WHERE UPPER(usuario) = UPPER(?)", (target_user,))
        cursor.execute("UPDATE firmas_usuarios SET is_default = 1 WHERE UPPER(usuario) = UPPER(?) AND id = ?", (target_user, sig_id))
        conn.commit()
        conn.close()

    def delete_signature(self, usuario: str, sig_id: int):
        target_user = str(usuario).strip().lower()
        if self.supabase_client:
            try:
                self.supabase_client.table("firmas_usuarios").delete().eq("id", sig_id).execute()
            except Exception as e:
                print(f"[DB] Aviso Supabase delete_signature ({e}).")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM firmas_usuarios WHERE UPPER(usuario) = UPPER(?) AND id = ?", (target_user, sig_id))
        conn.commit()
        conn.close()

    # --- LISTA DE PRECIOS ---
    def get_precios_cliente(self, cliente_id_or_name: str) -> List[Dict[str, Any]]:
        target = str(cliente_id_or_name).strip()
        if self.supabase_client:
            try:
                res = self.supabase_client.table("lista_precios").select("*").ilike("cliente_id", f"%{target}%").order("equipo").execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                print(f"[DB] Aviso Supabase get_precios_cliente ({e}), usando SQLite.")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM lista_precios 
            WHERE UPPER(cliente_id) = UPPER(?) OR UPPER(cliente_id) LIKE ?
            ORDER BY equipo ASC
        """, (target, f"%{target.upper()}%"))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_item_precio(self, item_data: Dict[str, Any]):
        cid = str(item_data.get("cliente_id", "")).strip()
        equipo = str(item_data.get("equipo", "")).strip()
        marca = str(item_data.get("marca", "-"))
        modelo = str(item_data.get("modelo", "-"))
        interno = str(item_data.get("interno", "-"))
        tarifa_d = float(item_data.get("tarifa_diaria", 0.0))
        tarifa_s = float(item_data.get("tarifa_semanal", 0.0))
        tarifa_m = float(item_data.get("tarifa_mensual", 0.0))
        modalidad = str(item_data.get("modalidad_defecto", "diario"))
        moneda = str(item_data.get("moneda", "USD"))
        obs = str(item_data.get("observaciones", ""))

        if self.supabase_client:
            try:
                payload = {
                    "cliente_id": cid,
                    "equipo": equipo,
                    "marca": marca,
                    "modelo": modelo,
                    "interno": interno,
                    "tarifa_diaria": tarifa_d,
                    "tarifa_semanal": tarifa_s,
                    "tarifa_mensual": tarifa_m,
                    "modalidad_defecto": modalidad,
                    "moneda": moneda,
                    "observaciones": obs
                }
                self.supabase_client.table("lista_precios").insert(payload).execute()
            except Exception as e:
                print(f"[DB] Aviso Supabase save_item_precio ({e}).")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lista_precios (
                cliente_id, equipo, marca, modelo, interno,
                tarifa_diaria, tarifa_semanal, tarifa_mensual, modalidad_defecto, moneda, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cid, equipo, marca, modelo, interno, tarifa_d, tarifa_s, tarifa_m, modalidad, moneda, obs))
        conn.commit()
        conn.close()

    def clear_precios_cliente(self, cliente_id: str):
        target = str(cliente_id).strip()
        if self.supabase_client:
            try:
                self.supabase_client.table("lista_precios").delete().ilike("cliente_id", target).execute()
            except Exception as e:
                print(f"[DB] Aviso Supabase clear_precios_cliente ({e}).")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lista_precios WHERE UPPER(cliente_id) = UPPER(?)", (target,))
        conn.commit()
        conn.close()

db = Database()
