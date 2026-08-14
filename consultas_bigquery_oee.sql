-- =============================================================
-- Análisis de OEE en Google BigQuery
-- Fase 5 del proyecto: Migración a la nube
-- Patricio Ahumada | github.com/PatricioAhumadaBustos
-- =============================================================
--
-- Dataset esperado: oee_manufactura
-- Tablas: produccion, paradas  (cargadas desde los CSV del proyecto)
--
-- Nota: si tus consultas no encuentran las tablas, antepón el ID
-- del proyecto:  `mi-proyecto.oee_manufactura.produccion`
-- =============================================================


-- -------------------------------------------------------------
-- 1. OEE GLOBAL
-- Los tres componentes del OEE sobre toda la operación.
-- SAFE_DIVIDE evita el error de división por cero.
-- -------------------------------------------------------------
SELECT
  ROUND(SAFE_DIVIDE(SUM(tiempo_operativo_min), SUM(tiempo_planificado_min)), 4) AS disponibilidad,
  ROUND(SAFE_DIVIDE(SUM(unidades_producidas), SUM(tiempo_operativo_min * velocidad_ideal_upm)), 4) AS rendimiento,
  ROUND(SAFE_DIVIDE(SUM(unidades_buenas), SUM(unidades_producidas)), 4) AS calidad,
  ROUND(
      SAFE_DIVIDE(SUM(tiempo_operativo_min), SUM(tiempo_planificado_min))
    * SAFE_DIVIDE(SUM(unidades_producidas), SUM(tiempo_operativo_min * velocidad_ideal_upm))
    * SAFE_DIVIDE(SUM(unidades_buenas), SUM(unidades_producidas))
  , 4) AS oee_global
FROM oee_manufactura.produccion;


-- -------------------------------------------------------------
-- 2. OEE POR ESTACIÓN
-- Compara las dos estaciones críticas de la línea.
-- -------------------------------------------------------------
SELECT
  estacion_id,
  estacion_nombre,
  ROUND(SAFE_DIVIDE(SUM(tiempo_operativo_min), SUM(tiempo_planificado_min)), 4) AS disponibilidad,
  ROUND(SAFE_DIVIDE(SUM(unidades_producidas), SUM(tiempo_operativo_min * velocidad_ideal_upm)), 4) AS rendimiento,
  ROUND(SAFE_DIVIDE(SUM(unidades_buenas), SUM(unidades_producidas)), 4) AS calidad,
  ROUND(
      SAFE_DIVIDE(SUM(tiempo_operativo_min), SUM(tiempo_planificado_min))
    * SAFE_DIVIDE(SUM(unidades_producidas), SUM(tiempo_operativo_min * velocidad_ideal_upm))
    * SAFE_DIVIDE(SUM(unidades_buenas), SUM(unidades_producidas))
  , 4) AS oee
FROM oee_manufactura.produccion
GROUP BY estacion_id, estacion_nombre
ORDER BY oee DESC;


-- -------------------------------------------------------------
-- 3. PARETO DE CAUSAS DE PARADA
-- Usa una función de ventana para el porcentaje acumulado,
-- que es la forma correcta de construir un Pareto en SQL.
-- -------------------------------------------------------------
WITH totales AS (
  SELECT
    causa,
    SUM(minutos) AS minutos_totales,
    COUNT(*)     AS eventos
  FROM oee_manufactura.paradas
  GROUP BY causa
)
SELECT
  causa,
  minutos_totales,
  eventos,
  ROUND(minutos_totales * 100.0 / SUM(minutos_totales) OVER (), 2) AS porcentaje,
  ROUND(
    SUM(minutos_totales) OVER (ORDER BY minutos_totales DESC)
    * 100.0 / SUM(minutos_totales) OVER ()
  , 2) AS porcentaje_acumulado
FROM totales
ORDER BY minutos_totales DESC;


-- -------------------------------------------------------------
-- 4. HALLAZGO CLAVE: MANTENCIÓN vs FALLAS
-- Cruza la producción con las paradas por falla de máquina y
-- agrupa por antigüedad desde la última mantención.
-- Este es el análisis que sustenta la recomendación del proyecto.
-- -------------------------------------------------------------
WITH fallas_por_turno AS (
  SELECT
    fecha,
    turno,
    estacion_id,
    SUM(minutos) AS minutos_falla
  FROM oee_manufactura.paradas
  WHERE causa LIKE 'Falla de máquina%'
  GROUP BY fecha, turno, estacion_id
),
base AS (
  SELECT
    p.dias_desde_mantencion,
    IFNULL(f.minutos_falla, 0) AS minutos_falla,
    CASE
      WHEN p.dias_desde_mantencion <= 15 THEN '0-15 dias'
      WHEN p.dias_desde_mantencion <= 30 THEN '16-30 dias'
      ELSE '31+ dias'
    END AS rango_mantencion
  FROM oee_manufactura.produccion p
  LEFT JOIN fallas_por_turno f
    ON  p.fecha       = f.fecha
    AND p.turno       = f.turno
    AND p.estacion_id = f.estacion_id
)
SELECT
  rango_mantencion,
  COUNT(*) AS turnos,
  ROUND(AVG(minutos_falla), 1) AS minutos_falla_promedio,
  ROUND(COUNTIF(minutos_falla > 0) * 100.0 / COUNT(*), 1) AS tasa_falla_pct
FROM base
GROUP BY rango_mantencion
ORDER BY rango_mantencion;


-- -------------------------------------------------------------
-- 5. TENDENCIA MENSUAL DEL OEE
-- Evolución de la eficiencia a lo largo de los 6 meses.
-- -------------------------------------------------------------
SELECT
  FORMAT_DATE('%Y-%m', DATE(fecha)) AS mes,
  ROUND(
      SAFE_DIVIDE(SUM(tiempo_operativo_min), SUM(tiempo_planificado_min))
    * SAFE_DIVIDE(SUM(unidades_producidas), SUM(tiempo_operativo_min * velocidad_ideal_upm))
    * SAFE_DIVIDE(SUM(unidades_buenas), SUM(unidades_producidas))
  , 4) AS oee_mensual,
  SUM(tiempo_paradas_min) AS minutos_parada,
  SUM(unidades_buenas)    AS unidades_buenas
FROM oee_manufactura.produccion
GROUP BY mes
ORDER BY mes;
