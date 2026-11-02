import os
import pandas as pd

def generate_sample_excels(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Nabors
    nabors_data = {
        "EQUIPO": [
            "Generador 480V / 60 Hz",
            "Generador 380V / 50 Hz",
            "Tablero Distribución",
            "Compresor 375Q"
        ],
        "MARCA": ["-", "-", "-", "-"],
        "MODELO": ["-", "-", "-", "-"],
        "INICIO": ["25/06/2026", "25/06/2026", "25/06/2026", "25/06/2026"],
        "FIN": ["08/07/2026", "08/07/2026", "08/07/2026", "03/07/2026"],
        "DÍAS ALQ": [13, 13, 13, 8],
        "CANT EQUIPOS": [2, 1, 1, 1]
    }
    df_nabors = pd.DataFrame(nabors_data)
    df_nabors.to_excel(os.path.join(output_dir, "muestra_nabors.xlsx"), index=False)
    
    # 2. YPF NOC IADE
    ypf_iade_data = {
        "IADE": [499520, 501013],
        "EQUIPO": ["Manipulador 23TN X10230", "Carro 23tn"],
        "INTERNO": ["E040204", "A040154"],
        "ALMACEN": ["NOC", "NOC"],
        "REPUESTOS (USD)": [1808.80, 20255.00],
        "MANO DE OBRA Y REPARACIONES (USD)": [43.20, 360.00],
        "TOTAL REP.+ MO": [1852.00, 20615.00],
        "DETALLE": [
            "Falta Baliza indicadora de carga",
            "Se genera IADE por ambos cilindros con vástagos deformados tuercas partidas debido a la deformación del vástago. Roscas barridas y bulones dañados en chapas guía de uñas."
        ]
    }
    df_ypf_iade = pd.DataFrame(ypf_iade_data)
    df_ypf_iade.to_excel(os.path.join(output_dir, "muestra_ypf_iade.xlsx"), index=False)
    
    # 3. YPF NOC MENSUAL
    ypf_mensual_data = {
        "POSICIÓN": [14, 14, 14, 18, 1, 27, 27, 27, 27, 27, 27, 14, 14],
        "LINEA": [10, 10, 10, 10, 10, 20, 10, 10, 10, 10, 20, 10, 10],
        "U.M": ["MES"] * 13,
        "DESCRIPCION": [
            "ALQ. MENS. AUTOEL. 2,5TN (E040172)",
            "ALQ. MENS. AUTOEL. 2,5TN (E040179)",
            "ALQ. MENS. AUTOEL. 2,5TN (E040174)",
            "ALQ. MENS. MANIP. 2,5TN X625H (E040257)",
            "ALQ. MENS. AUTOEL. 1,5TN (E040180)",
            "ALQ. MENS. GANCHO P/GRUA 21TN - (A040153)",
            "ALQ. MENS. MANIP. 21TN (E040207) + CARRO (A040175)",
            "ALQ. MENS. MANIP. 21TN (E040188)",
            "ALQ. MENS. MANIP. 21TN (E040204) + CARRO (A040171)",
            "ALQ. MENS. MANIP. 21TN (E040205) + CARRO (A040164)",
            "ALQ. MENS. GANCHO P/GRUA 21TN - (A040173)",
            "ALQ. MENS. AUTOEL. 2,5TN (E040169)",
            "ALQ. MENS. MANIP. 2,5TN X625H (E040314)"
        ],
        "PERIODO": ["AGO - SEP"] * 13,
        "CANTIDAD": [0.667, 0.267, 1.000, 1.000, 1.000, 1.000, 0.167, 0.233, 0.033, 0.933, 1.000, 1.000, 1.000],
        "TARIFA": [1400.0, 1400.0, 1400.0, 3600.0, 1500.0, 378.0, 16300.0, 16300.0, 16300.0, 16300.0, 378.0, 1400.0, 3600.0],
        "TOTAL": [933.24, 373.24, 1400.00, 3600.00, 1500.00, 378.00, 2715.58, 3802.79, 542.79, 15212.79, 378.00, 1400.00, 3600.00]
    }
    df_ypf_mensual = pd.DataFrame(ypf_mensual_data)
    df_ypf_mensual.to_excel(os.path.join(output_dir, "muestra_ypf_mensual.xlsx"), index=False)
    
    # 4. Pluspetrol
    pluspetrol_data = {
        "EQUIPO": [
            "Generador 500 kVA",
            "Compresor 750 CFM",
            "Torre de Iluminación 4x1000W",
            "Manipulador Telescópico 17m"
        ],
        "MARCA": ["Atlas Copco", "Sullair", "Generac", "Manitou"],
        "MODELO": ["QAS 500", "750XH", "VT8", "MT 1840"],
        "INTERNO": ["G040012", "C030045", "T010089", "M020033"],
        "CANT DIAS": [30, 30, 20, 15],
        "INICIO PERIODO": ["01/10/2026", "01/10/2026", "11/10/2026", "16/10/2026"],
        "FIN PERIODO": ["30/10/2026", "30/10/2026", "30/10/2026", "30/10/2026"],
        "TARIFA DIARIO": [280.00, 210.00, 95.00, 340.00],
        "TARIFA TOTAL (USD)": [8400.00, 6300.00, 1900.00, 5100.00]
    }
    df_plus = pd.DataFrame(pluspetrol_data)
    df_plus.to_excel(os.path.join(output_dir, "muestra_pluspetrol.xlsx"), index=False)
    print("Muestras generadas con éxito en:", output_dir)

if __name__ == "__main__":
    generate_sample_excels(os.path.join(os.path.dirname(__file__), "sample_data"))
