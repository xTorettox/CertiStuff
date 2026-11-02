# 📄 Generador de Certificados de Alquiler y Servicios | Sullair Argentina

Sistema modular en Python y **Streamlit** diseñado para automatizar la emisión de certificados de alquiler de maquinaria, herramientas y servicios en formato **PDF vectorial** de alta resolución utilizando **ReportLab** y **Pandas**.

---

## 🚀 Características Principales

1. **Gestión de Firmas y Logos:**
   - Estampado de **logo corporativo estático** oficial de Sullair Argentina en alta definición.
   - Soporte para subir **firmas escaneadas transparentes (.PNG)** desde la PC, con opción de restaurar la firma predeterminada del responsable comercial.
2. **Configuración de Perfiles Dinámicos:**
   - Gestor visual para crear, modificar y guardar plantillas personalizadas en formato JSON (`profiles/`).
   - Mapeo inteligente y flexible de columnas (con detección de sinónimos como "Interno", "N° Serie", "CANT DIAS", etc.).
   - Modos de cálculo de tarifas automáticos: **Diario**, **Semanal**, **Mensual** y **Fijo**.
3. **Carga y Edición Interactiva de Datos:**
   - Carga de archivos **Excel (.xlsx, .xls)**.
   - Botón de **"Cargar Datos de Ejemplo"** con datos reales para prueba inmediata sin necesidad de preparar un archivo previo.
   - Botón de descarga de plantillas Excel oficiales para cada cliente.
   - Tabla interactiva con `st.data_editor` que incluye casilla de verificación `_incluir` para seleccionar qué filas certificar.
4. **Modelos de Certificados Soportados:**
   - **Nabors:** Encabezado con N° Certificado, Cliente, Servicio, OC/NP, sucursal Sullair. Tabla dinámica de equipos (con opción de mostrar/ocultar fechas INICIO y FIN). Pie con observaciones, firma y logo.
   - **YPF NOC (IADE):** Encabezado con Contrato SAP y Almacén. Tabla con cabecera negra y texto blanco: IADE, EQUIPO, INTERNO, ALMACEN, REPUESTOS (USD), MANO DE OBRA Y REPARACIONES (USD), TOTAL REP.+ MO y DETALLE de falla multilínea. Pie con SUBTOTAL en USD.
   - **YPF NOC (Mensual / Plataformas):** Encabezado con Contrato SAP, Almacén y Período. Tabla con POSICIÓN, LINEA, U.M, DESCRIPCION, PERIODO, CANTIDAD, TARIFA y TOTAL. Recuadro inferior para Observaciones (deducciones por fuera de servicio).
   - **Pluspetrol:** Encabezado con Certificado N°, Cliente, Obra, Período y OC/NP. Tabla principal de alquiler de equipos y tabla secundaria opcional de **Otros Cargos** (fletes, seguros). Resumen de subtotales y Total General en USD.
5. **Salida y Previsualización en Vivo:**
   - Renderizado vectorial de ReportLab con marco exterior negro continuo exacto al formato corporativo.
   - Previsualización visual instantánea de alta resolución en la propia app antes de descargar.
   - Descarga directa con `st.download_button`.

---

## 📂 Estructura del Proyecto

```text
certificados_sullair/
├── .streamlit/
│   └── config.toml               # Configuración de tema verde Sullair y UI
├── assets/
│   ├── logo_sullair.png          # Logo corporativo oficial Sullair Argentina
│   ├── firma_default.png         # Firma digital por defecto
│   ├── firma_subida.png          # Firma personalizada cargada por el usuario (si aplica)
│   ├── sample_data/              # Archivos Excel de ejemplo listos para usar
│   │   ├── muestra_nabors.xlsx
│   │   ├── muestra_ypf_iade.xlsx
│   │   ├── muestra_ypf_mensual.xlsx
│   │   └── muestra_pluspetrol.xlsx
│   └── generate_samples.py       # Script generador de los archivos de muestra
├── profiles/                     # Plantillas y configuraciones en formato JSON
│   ├── nabors.json
│   ├── ypf_noc_iade.json
│   ├── ypf_noc_mensual.json
│   └── pluspetrol.json
├── generators/                   # Motores de renderizado PDF con ReportLab
│   ├── __init__.py               # Factory selector de generadores
│   ├── base_generator.py         # Clase base abstracta con marco exterior, logo y firma
│   ├── nabors_generator.py       # Generador específico para Nabors
│   ├── ypf_iade_generator.py     # Generador específico para YPF NOC (IADE)
│   ├── ypf_mensual_generator.py  # Generador específico para YPF NOC (Mensual)
│   └── pluspetrol_generator.py   # Generador específico para Pluspetrol
├── utils/                        # Módulos utilitarios y lógica de negocio
│   ├── __init__.py
│   ├── profile_manager.py        # Gestor de perfiles y cálculo de tarifas
│   ├── excel_handler.py          # Mapeador de columnas y formateo latino de monedas
│   └── pdf_preview.py            # Conversor de páginas PDF a imágenes de alta definición
├── app.py                        # Aplicación web Streamlit principal
├── test_generation.py            # Suite de pruebas unitarias automáticas
├── requirements.txt              # Dependencias del proyecto
└── README.md                     # Documentación completa
```

---

## 🛠️ Instalación y Puesta en Marcha

### 1. Requisitos Previos
- Python 3.10 o superior (compatible con Python 3.13).

### 2. Instalar Dependencias
```bash
py -m pip install -r requirements.txt
```

### 3. Ejecutar la Aplicación
```bash
streamlit run app.py
```
O mediante el launcher `py`:
```bash
py -m streamlit run app.py
```

---

## 🧪 Ejecución de Pruebas Automáticas

Para validar que todos los generadores de PDF y el renderizador de previsualización funcionan correctamente:
```bash
py test_generation.py
```
El script generará los archivos `test_nabors.pdf`, `test_ypf_noc_iade.pdf`, `test_ypf_noc_mensual.pdf` y `test_pluspetrol.pdf` en la raíz del proyecto.
