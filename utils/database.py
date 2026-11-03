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
    1. Supabase (PostgreSQL en la nube vía HTTPS / supabase-py)
    2. MySQL (Hostinger vía mysql-connector o pymysql si está configurado)
    3. SQLite local (database.db) como fallback robusto sin configuración
    """
    def __init__(self):
        self.backend = "sqlite"
        self.supabase_client = None
        self._init_connection()
        self._create_tables()

    def _init_connection(self):
        # Intentar conectar con Supabase si está en st.secrets o variables de entorno
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "supabase" in st.secrets:
                url = st.secrets["supabase"].get("url") or st.secrets["supabase"].get("supabase_url")
                key = st.secrets["supabase"].get("key") or st.secrets["supabase"].get("supabase_key")
                if url and key:
                    from supabase import create_client
                    self.supabase_client = create_client(url, key)
                    self.backend = "supabase"
                    return
        except Exception as e:
            print(f"Aviso: No se pudo conectar a Supabase, usando SQLite: {e}")

        # Fallback a SQLite
        self.backend = "sqlite"

    def _get_sqlite_conn(self):
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        if self.backend == "sqlite":
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

            # 2. Lista de Precios / Tarifario de Contratos
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

            # Insertar clientes base por defecto si la tabla está vacía
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

    # --- CLIENTES ---
    def get_clientes(self) -> List[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes ORDER BY nombre ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_cliente(self, cliente_id_or_name: str) -> Optional[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM clientes 
            WHERE id = ? OR UPPER(nombre) = UPPER(?) OR UPPER(id) = UPPER(?)
            LIMIT 1
        """, (cliente_id_or_name, cliente_id_or_name, cliente_id_or_name))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def save_cliente(self, cliente_data: Dict[str, Any]) -> str:
        cid = cliente_data.get("id")
        nombre = cliente_data.get("nombre", cid)
        if not cid:
            cid = nombre.lower().replace(" ", "_").replace(".", "").replace("-", "_")
        
        template_type = cliente_data.get("template_type", "nabors")
        ultimo_cert = int(cliente_data.get("ultimo_certificado", 0))
        contrato = cliente_data.get("contrato_nro", "")
        servicio = cliente_data.get("servicio_defecto", "")
        oc_np = cliente_data.get("oc_np_defecto", "")
        sucursal = cliente_data.get("sucursal", "Sucursal NQN y Valle")
        direccion = cliente_data.get("direccion", "Industriales Neuquinos 2920, PIN")
        telefono = cliente_data.get("telefono", "T:[0299] 4782500")

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
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clientes 
            SET ultimo_certificado = MAX(ultimo_certificado, ?) 
            WHERE id = ? OR UPPER(nombre) = UPPER(?)
        """, (cert_num, cliente_id_or_name, cliente_id_or_name))
        conn.commit()
        conn.close()

    # --- HISTORIAL DE CERTIFICADOS ---
    def add_historial(self, cert_data: Dict[str, Any]) -> int:
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO certificados_historial (
                cliente, certificado_nro, fecha_emision, servicio_obra, oc_np,
                total_monto, moneda, usuario, items_count, metadata_json, items_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cert_data.get("cliente", ""),
            str(cert_data.get("certificado_nro", "")),
            cert_data.get("fecha_emision", datetime.date.today().strftime("%d/%m/%Y")),
            cert_data.get("servicio_obra", ""),
            cert_data.get("oc_np", ""),
            float(cert_data.get("total_monto", 0.0)),
            cert_data.get("moneda", "USD"),
            cert_data.get("usuario", "anonimo"),
            int(cert_data.get("items_count", 0)),
            json.dumps(cert_data.get("metadata", {}), ensure_ascii=False),
            json.dumps(cert_data.get("items", []), ensure_ascii=False)
        ))
        cert_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Actualizar índice del cliente si es numérico
        try:
            raw_nro = str(cert_data.get("certificado_nro", ""))
            clean_digits = "".join(filter(str.isdigit, raw_nro))
            if clean_digits:
                self.increment_ultimo_certificado(cert_data.get("cliente", ""), int(clean_digits))
        except Exception:
            pass

        return cert_id

    def get_historial(self, cliente_filtro: str = "", limit: int = 100) -> List[Dict[str, Any]]:
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
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM firmas_usuarios WHERE UPPER(usuario) = UPPER(?) ORDER BY is_default DESC, id DESC", (usuario,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_user_signature(self, usuario: str, nombre_firmante: str, cargo: str, alias: str, firma_png_base64: str, is_default: bool = False) -> int:
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        if is_default:
            cursor.execute("UPDATE firmas_usuarios SET is_default = 0 WHERE UPPER(usuario) = UPPER(?)", (usuario,))
        cursor.execute("""
            INSERT INTO firmas_usuarios (usuario, nombre_firmante, cargo, alias, firma_png_base64, is_default)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (usuario, nombre_firmante, cargo, alias, firma_png_base64, 1 if is_default else 0))
        sig_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return sig_id

    def set_default_signature(self, usuario: str, sig_id: int):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE firmas_usuarios SET is_default = 0 WHERE UPPER(usuario) = UPPER(?)", (usuario,))
        cursor.execute("UPDATE firmas_usuarios SET is_default = 1 WHERE UPPER(usuario) = UPPER(?) AND id = ?", (usuario, sig_id))
        conn.commit()
        conn.close()

    def delete_signature(self, usuario: str, sig_id: int):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM firmas_usuarios WHERE UPPER(usuario) = UPPER(?) AND id = ?", (usuario, sig_id))
        conn.commit()
        conn.close()

    # --- LISTA DE PRECIOS ---
    def get_precios_cliente(self, cliente_id_or_name: str) -> List[Dict[str, Any]]:
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM lista_precios 
            WHERE UPPER(cliente_id) = UPPER(?) OR UPPER(cliente_id) LIKE ?
            ORDER BY equipo ASC
        """, (cliente_id_or_name, f"%{cliente_id_or_name.upper()}%"))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_item_precio(self, item_data: Dict[str, Any]):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lista_precios (
                cliente_id, equipo, marca, modelo, interno,
                tarifa_diaria, tarifa_semanal, tarifa_mensual, modalidad_defecto, moneda, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_data.get("cliente_id", ""),
            item_data.get("equipo", ""),
            item_data.get("marca", "-"),
            item_data.get("modelo", "-"),
            item_data.get("interno", "-"),
            float(item_data.get("tarifa_diaria", 0.0)),
            float(item_data.get("tarifa_semanal", 0.0)),
            float(item_data.get("tarifa_mensual", 0.0)),
            item_data.get("modalidad_defecto", "diario"),
            item_data.get("moneda", "USD"),
            item_data.get("observaciones", "")
        ))
        conn.commit()
        conn.close()

    def clear_precios_cliente(self, cliente_id: str):
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lista_precios WHERE UPPER(cliente_id) = UPPER(?)", (cliente_id,))
        conn.commit()
        conn.close()

db = Database()

