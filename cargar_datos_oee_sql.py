"""
Carga de datos y modelado SQL para análisis de OEE
===================================================
Fase 2 del proyecto: Diseño de esquema relacional y consultas SQL

Crea una base de datos SQLite con tablas normalizadas:
  - estaciones (dimensión)
  - causas (dimensión)
  - produccion (hecho: métricas por turno-estación)
  - paradas (hecho: eventos de parada)

Incluye consultas SQL para calcular OEE, disponibilidad, rendimiento y calidad.
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = "oee_analisis.db"


def crear_conexion():
    """Crea conexión a la BD SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # permite acceder por nombre de columna
    return conn


def crear_tablas(conn):
    """Define y crea las tablas del esquema relacional."""
    cursor = conn.cursor()

    # Tabla de dimensión: estaciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estaciones (
            estacion_id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            velocidad_upm REAL NOT NULL
        )
    """)

    # Tabla de dimensión: causas de parada
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS causas (
            causa_id INTEGER PRIMARY KEY AUTOINCREMENT,
            causa TEXT NOT NULL UNIQUE
        )
    """)

    # Tabla de hechos: producción (un registro por turno-estación)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produccion (
            produccion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            turno TEXT NOT NULL,
            estacion_id TEXT NOT NULL,
            tiempo_planificado_min INTEGER NOT NULL,
            tiempo_paradas_min INTEGER NOT NULL,
            tiempo_operativo_min INTEGER NOT NULL,
            velocidad_ideal_upm REAL NOT NULL,
            unidades_producidas INTEGER NOT NULL,
            unidades_defectuosas INTEGER NOT NULL,
            unidades_buenas INTEGER NOT NULL,
            dias_desde_mantencion INTEGER NOT NULL,
            fecha_ultima_mantencion DATE NOT NULL,
            FOREIGN KEY (estacion_id) REFERENCES estaciones(estacion_id)
        )
    """)

    # Tabla de hechos: paradas (un registro por evento de parada)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paradas (
            parada_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            turno TEXT NOT NULL,
            estacion_id TEXT NOT NULL,
            causa_id INTEGER NOT NULL,
            minutos INTEGER NOT NULL,
            FOREIGN KEY (estacion_id) REFERENCES estaciones(estacion_id),
            FOREIGN KEY (causa_id) REFERENCES causas(causa_id)
        )
    """)

    conn.commit()
    print("✓ Tablas creadas correctamente")


def cargar_datos(conn):
    """Lee los CSV y carga los datos en las tablas."""
    cursor = conn.cursor()

    # Leer CSV
    prod_df = pd.read_csv("produccion.csv")
    paradas_df = pd.read_csv("paradas.csv")

    # --- Cargar estaciones (desde produccion.csv, deduplicar) ---
    estaciones_unicas = prod_df[["estacion_id", "estacion_nombre", "velocidad_ideal_upm"]].drop_duplicates()
    for _, row in estaciones_unicas.iterrows():
        cursor.execute("""
            INSERT OR IGNORE INTO estaciones (estacion_id, nombre, velocidad_upm)
            VALUES (?, ?, ?)
        """, (row["estacion_id"], row["estacion_nombre"], row["velocidad_ideal_upm"]))
    conn.commit()
    print(f"✓ {len(estaciones_unicas)} estaciones cargadas")

    # --- Cargar causas (desde paradas.csv, deduplicar) ---
    causas_unicas = paradas_df["causa"].unique()
    for causa in causas_unicas:
        cursor.execute("""
            INSERT OR IGNORE INTO causas (causa)
            VALUES (?)
        """, (causa,))
    conn.commit()
    print(f"✓ {len(causas_unicas)} causas cargadas")

    # --- Cargar produccion ---
    for _, row in prod_df.iterrows():
        cursor.execute("""
            INSERT INTO produccion (
                fecha, turno, estacion_id, tiempo_planificado_min, tiempo_paradas_min,
                tiempo_operativo_min, velocidad_ideal_upm, unidades_producidas,
                unidades_defectuosas, unidades_buenas, dias_desde_mantencion,
                fecha_ultima_mantencion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["fecha"], row["turno"], row["estacion_id"],
            row["tiempo_planificado_min"], row["tiempo_paradas_min"],
            row["tiempo_operativo_min"], row["velocidad_ideal_upm"],
            row["unidades_producidas"], row["unidades_defectuosas"],
            row["unidades_buenas"], row["dias_desde_mantencion"],
            row["fecha_ultima_mantencion"]
        ))
    conn.commit()
    print(f"✓ {len(prod_df)} registros de producción cargados")

    # --- Cargar paradas ---
    for _, row in paradas_df.iterrows():
        # Obtener causa_id desde la tabla causas
        cursor.execute("SELECT causa_id FROM causas WHERE causa = ?", (row["causa"],))
        causa_id = cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO paradas (fecha, turno, estacion_id, causa_id, minutos)
            VALUES (?, ?, ?, ?, ?)
        """, (row["fecha"], row["turno"], row["estacion_id"], causa_id, row["minutos"]))
    conn.commit()
    print(f"✓ {len(paradas_df)} eventos de parada cargados")


def crear_consultas_sql(conn):
    """Define consultas SQL clave para el análisis OEE."""
    consultas = {
        "oee_global": """
            -- OEE Global
            SELECT
                ROUND(
                    (SUM(tiempo_operativo_min) * 1.0 / SUM(tiempo_planificado_min)) *
                    (SUM(unidades_producidas) * 1.0 / (SUM(tiempo_operativo_min) * AVG(velocidad_ideal_upm))) *
                    (SUM(unidades_buenas) * 1.0 / SUM(unidades_producidas)),
                    4
                ) AS oee_global,
                ROUND(SUM(tiempo_operativo_min) * 1.0 / SUM(tiempo_planificado_min), 4) AS disponibilidad,
                ROUND(SUM(unidades_producidas) * 1.0 / (SUM(tiempo_operativo_min) * AVG(velocidad_ideal_upm)), 4) AS rendimiento,
                ROUND(SUM(unidades_buenas) * 1.0 / SUM(unidades_producidas), 4) AS calidad
            FROM produccion;
        """,

        "oee_por_estacion": """
            -- OEE por estación
            SELECT
                estacion_id,
                ROUND(
                    (SUM(tiempo_operativo_min) * 1.0 / SUM(tiempo_planificado_min)) *
                    (SUM(unidades_producidas) * 1.0 / (SUM(tiempo_operativo_min) * velocidad_ideal_upm)) *
                    (SUM(unidades_buenas) * 1.0 / SUM(unidades_producidas)),
                    4
                ) AS oee,
                ROUND(SUM(tiempo_operativo_min) * 1.0 / SUM(tiempo_planificado_min), 4) AS disponibilidad,
                ROUND(SUM(unidades_producidas) * 1.0 / (SUM(tiempo_operativo_min) * velocidad_ideal_upm), 4) AS rendimiento,
                ROUND(SUM(unidades_buenas) * 1.0 / SUM(unidades_producidas), 4) AS calidad
            FROM produccion
            GROUP BY estacion_id
            ORDER BY oee DESC;
        """,

        "pareto_causas": """
            -- Pareto de causas (minutos totales)
            SELECT
                c.causa,
                SUM(p.minutos) AS minutos_totales,
                ROUND(SUM(p.minutos) * 100.0 / (SELECT SUM(minutos) FROM paradas), 2) AS porcentaje
            FROM paradas p
            JOIN causas c ON p.causa_id = c.causa_id
            GROUP BY p.causa_id
            ORDER BY minutos_totales DESC;
        """,

        "mantencion_vs_fallas": """
            -- Relación entre días sin mantención y minutos de falla
            SELECT
                CASE
                    WHEN dias_desde_mantencion BETWEEN 0 AND 15 THEN '0-15 días'
                    WHEN dias_desde_mantencion BETWEEN 16 AND 30 THEN '16-30 días'
                    ELSE '31+ días'
                END AS rango_dias,
                COUNT(*) AS turnos,
                ROUND(AVG(CASE WHEN p.minutos IS NOT NULL THEN p.minutos ELSE 0 END), 1) AS min_falla_promedio,
                ROUND(
                    COUNT(DISTINCT CASE WHEN p.minutos > 0 THEN prod.produccion_id END) * 100.0 / COUNT(*),
                    1
                ) AS tasa_falla_pct
            FROM produccion prod
            LEFT JOIN paradas p ON prod.fecha = p.fecha AND prod.turno = p.turno AND prod.estacion_id = p.estacion_id
            LEFT JOIN causas c ON p.causa_id = c.causa_id AND c.causa LIKE '%Falla de máquina%'
            GROUP BY rango_dias
            ORDER BY
                CASE
                    WHEN rango_dias = '0-15 días' THEN 1
                    WHEN rango_dias = '16-30 días' THEN 2
                    ELSE 3
                END;
        """,

        "produccion_vs_calidad": """
            -- Producción y tasa de defecto por estación
            SELECT
                estacion_id,
                SUM(unidades_producidas) AS total_producidas,
                SUM(unidades_defectuosas) AS total_defectuosas,
                ROUND(SUM(unidades_defectuosas) * 100.0 / SUM(unidades_producidas), 2) AS tasa_defecto_pct
            FROM produccion
            GROUP BY estacion_id
            ORDER BY tasa_defecto_pct DESC;
        """
    }

    return consultas


def ejecutar_consultas(conn, consultas):
    """Ejecuta las consultas y muestra los resultados."""
    cursor = conn.cursor()

    for nombre, sql in consultas.items():
        print(f"\n{'='*70}")
        print(f"CONSULTA: {nombre.upper()}")
        print(f"{'='*70}")
        try:
            cursor.execute(sql)
            filas = cursor.fetchall()
            if filas:
                # Encabezados
                columnas = [descripcion[0] for descripcion in cursor.description]
                print(f"{' | '.join(columnas)}")
                print("-" * 70)
                # Datos
                for fila in filas:
                    print(f"{' | '.join(str(v) for v in fila)}")
            else:
                print("(sin resultados)")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    # Verificar que los CSV existen
    if not Path("produccion.csv").exists() or not Path("paradas.csv").exists():
        print("❌ Falta generar los datos primero. Ejecuta: python generar_datos_oee.py")
        exit(1)

    # Crear/conectar BD
    conn = crear_conexion()

    # Crear tablas
    crear_tablas(conn)

    # Cargar datos
    cargar_datos(conn)

    # Ejecutar consultas
    consultas = crear_consultas_sql(conn)
    ejecutar_consultas(conn, consultas)

    print(f"\n✓ Base de datos guardada en: {DB_PATH}")
    print("  Puedes consultar manualmente con: sqlite3 oee_analisis.db")
    conn.close()
