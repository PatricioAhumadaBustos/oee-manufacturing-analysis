"""
Generador de datos simulados para análisis de OEE
==================================================
Proyecto de portafolio - Análisis de Eficiencia de Producción (OEE)
Patricio Ahumada

Genera datos realistas de una línea de manufactura con dos estaciones
críticas, durante 6 meses, con tres turnos diarios.

La simulación avanza día a día: cada máquina acumula días desde su última
mantención y, bajo un esquema CORRECTIVO (se interviene solo cuando falla),
su probabilidad y severidad de falla aumentan con el tiempo. Así el patrón
"a más días sin mantención, más fallas" NO está puesto a mano: emerge de la
dinámica y el análisis posterior lo descubre.

Salida: dos tablas relacionadas por (fecha, turno, estacion_id)
  - produccion.csv : una fila por turno-estación (para calcular OEE)
  - paradas.csv    : una fila por evento de parada (para el Pareto de causas)
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Parámetros configurables
# ---------------------------------------------------------------------------
SEMILLA = 42                       # reproducibilidad: mismos datos cada corrida
FECHA_INICIO = "2025-01-01"
FECHA_FIN = "2025-06-30"
TURNOS = ["Mañana", "Tarde", "Noche"]
MIN_POR_TURNO = 480                # 8 horas planificadas por turno

ESTACIONES = [
    {"id": "EST-01", "nombre": "Aserrado",  "velocidad_upm": 12},
    {"id": "EST-02", "nombre": "Prensado",  "velocidad_upm": 8},
]

# Causas de parada "independientes" (frecuencia y rango de minutos).
# La falta de materia prima es la más frecuente, tal como ocurría en planta.
CAUSAS_INDEP = {
    "Falta de materia prima": {"prob": 0.28, "min": 20, "max": 120},
    "Cambio de formato":      {"prob": 0.15, "min": 15, "max": 45},
    "Falta de personal":      {"prob": 0.08, "min": 20, "max": 90},
    "Ajustes de calidad":     {"prob": 0.12, "min": 10, "max": 40},
}
# La quinta causa, "Falla de máquina (espera mantención)", se modela aparte
# porque depende de los días desde la última mantención.

rng = np.random.default_rng(SEMILLA)


def probabilidad_falla(dias_sin_mantencion: int) -> float:
    """Probabilidad de que la máquina falle en un turno. Crece con los días."""
    return float(np.clip(0.02 + 0.006 * dias_sin_mantencion, 0.0, 0.9))


def minutos_falla(dias_sin_mantencion: int) -> int:
    """Duración de la parada por falla. Más larga si la máquina está más 'vieja'."""
    base = 40 + 3.0 * dias_sin_mantencion
    ruido = rng.normal(0, 15)
    return int(np.clip(base + ruido, 20, 300))


def generar():
    fechas = pd.date_range(FECHA_INICIO, FECHA_FIN, freq="D")

    # Estado por estación: días desde la última mantención y su fecha.
    estado = {
        e["id"]: {"dias": int(rng.integers(0, 20)),
                  "ultima": pd.Timestamp(FECHA_INICIO)}
        for e in ESTACIONES
    }

    filas_prod = []
    filas_paradas = []

    for fecha in fechas:
        for est in ESTACIONES:
            eid = est["id"]
            fallo_hoy = False  # para decidir la mantención correctiva del día

            for turno in TURNOS:
                dias = estado[eid]["dias"]
                paradas_turno = []  # (causa, minutos)

                # --- Causas independientes ---
                for causa, cfg in CAUSAS_INDEP.items():
                    if rng.random() < cfg["prob"]:
                        m = int(rng.integers(cfg["min"], cfg["max"] + 1))
                        paradas_turno.append((causa, m))

                # --- Falla de máquina (depende de la mantención) ---
                if rng.random() < probabilidad_falla(dias):
                    m = minutos_falla(dias)
                    paradas_turno.append(("Falla de máquina (espera mantención)", m))
                    fallo_hoy = True

                # Los minutos de parada no pueden superar el turno completo.
                total_paradas = min(sum(m for _, m in paradas_turno), MIN_POR_TURNO)
                t_operativo = MIN_POR_TURNO - total_paradas

                # --- Producción (rendimiento y calidad empeoran con la 'edad') ---
                rendimiento = float(np.clip(0.92 - 0.003 * dias + rng.normal(0, 0.03), 0.5, 0.99))
                producidas = int(t_operativo * est["velocidad_upm"] * rendimiento)

                tasa_defecto = 0.02 + 0.0005 * dias + rng.normal(0, 0.005)
                if any(c == "Cambio de formato" for c, _ in paradas_turno):
                    tasa_defecto += 0.01  # los cambios de formato meten ruido de calidad
                tasa_defecto = float(np.clip(tasa_defecto, 0.0, 0.25))
                defectuosas = int(producidas * tasa_defecto)

                filas_prod.append({
                    "fecha": fecha.date(),
                    "turno": turno,
                    "estacion_id": eid,
                    "estacion_nombre": est["nombre"],
                    "tiempo_planificado_min": MIN_POR_TURNO,
                    "tiempo_paradas_min": total_paradas,
                    "tiempo_operativo_min": t_operativo,
                    "velocidad_ideal_upm": est["velocidad_upm"],
                    "unidades_producidas": producidas,
                    "unidades_defectuosas": defectuosas,
                    "unidades_buenas": producidas - defectuosas,
                    "dias_desde_mantencion": dias,
                    "fecha_ultima_mantencion": estado[eid]["ultima"].date(),
                })

                for causa, m in paradas_turno:
                    filas_paradas.append({
                        "fecha": fecha.date(),
                        "turno": turno,
                        "estacion_id": eid,
                        "causa": causa,
                        "minutos": m,
                    })

                estado[eid]["dias"] += 1  # pasa un turno -> envejece un poco

            # --- Mantención correctiva al cierre del día ---
            # Esquema correctivo: se interviene SOLO si hubo falla (o si ya es
            # demasiado riesgoso seguir). Al intervenir, se resetea el contador.
            if fallo_hoy and rng.random() < 0.7:
                estado[eid]["dias"] = 0
                estado[eid]["ultima"] = fecha
            elif estado[eid]["dias"] >= 60:  # tope: nadie aguanta tanto sin parar
                estado[eid]["dias"] = 0
                estado[eid]["ultima"] = fecha

    prod = pd.DataFrame(filas_prod)
    paradas = pd.DataFrame(filas_paradas)
    return prod, paradas


if __name__ == "__main__":
    produccion, paradas = generar()
    produccion.to_csv("produccion.csv", index=False, encoding="utf-8-sig")
    paradas.to_csv("paradas.csv", index=False, encoding="utf-8-sig")
    print(f"produccion.csv: {len(produccion):>5} filas")
    print(f"paradas.csv   : {len(paradas):>5} filas")
