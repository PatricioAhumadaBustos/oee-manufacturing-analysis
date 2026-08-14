# Análisis de Eficiencia de Producción (OEE)

## Descripción

Este proyecto implementa un análisis integral de **Overall Equipment Effectiveness (OEE)** para una línea de manufactura de dos estaciones críticas. El objetivo es medir la eficiencia operativa e identificar las principales causas de pérdida de productividad para recomendar mejoras.

## Problema

Una línea de manufactura con dos estaciones críticas presentaba ineficiencia sin claridad sobre sus causas raíz. Las paradas no planificadas afectaban la producción, pero no había datos consolidados que permitieran priorizar intervenciones. Las causas principales sospechadas eran:
- **Desabastecimiento** de materia prima
- **Fallas de máquina** por mantención correctiva (sin esquema preventivo)

## Metodología

### Datos Simulados
Se generó un dataset de **6 meses de operación** (181 días, 3 turnos diarios) con 1.086 registros de producción y 749 eventos de parada. Los datos incluyen:
- Tiempos planificados y operativos por turno y estación
- Unidades producidas, defectuosas y buenas
- **Historial de mantención** (fecha de última intervención)
- **Causas de parada** clasificadas en 5 categorías

### Cálculo de OEE
El OEE se descompone en tres componentes:
OEE = Disponibilidad × Rendimiento × Calidad

Disponibilidad = Tiempo Operativo / Tiempo Planificado
Rendimiento = Unidades Producidas / (Tiempo Operativo × Velocidad Ideal)
Calidad = Unidades Buenas / Unidades Producidas

### Análisis Exploratorio
1. **Pareto de causas**: identificar qué causa concentra el mayor porcentaje de pérdida
2. **Cruce de datos**: relación entre días desde última mantención y tasa/duración de fallas
3. **Recomendación**: transición de esquema correctivo a preventivo

## Hallazgos Principales

- **OEE global: 79.9%** (Disponibilidad 92.4% | Rendimiento 88.9% | Calidad 97.4%)
- **Falta de materia prima** concentra el 60% de los minutos perdidos (18.801 min)
- **Fallas de máquina** concentran el 26% (8.016 min)
- **Hallazgo crítico**: máquinas sin mantención preventiva fallaban **3 veces más** que las recién intervenidas
  - 0-15 días sin mantención: 3.8 min promedio de falla por turno
  - 31+ días sin mantención: 40.0 min promedio de falla por turno

## Recomendación

Implementar un esquema de **mantención preventiva** reduciría significativamente la duración y frecuencia de paradas por falla de equipo, mejorando la disponibilidad y, por consiguiente, el OEE global.

## Estructura del Proyecto

oee-manufacturing-analysis/
├── generar_datos_oee.py     # Script para generar datos simulados realistas
├── produccion.csv           # Dataset: registros por turno-estación (1.086 filas)
├── paradas.csv              # Dataset: eventos de parada con causas (749 filas)
└── README.md                # Este archivo

## Requisitos

- Python 3.8+
- pandas
- numpy

## Cómo Ejecutar

```bash
# Generar los datos (si quieres reproducir el dataset)
python generar_datos_oee.py

# Esto crea dos archivos CSV:
# - produccion.csv
# - paradas.csv
```

## Próximas Fases

Este proyecto es la **Fase 1** de un portafolio de análisis de datos:
- **Fase 2**: Modelar datos en SQL (tablas relacionales)
- **Fase 3**: Calcular OEE y análisis exploratorio con Python/SQL
- **Fase 4**: Crear dashboard interactivo en Power BI
- **Fase 5**: Cargar datos en BigQuery (Google Cloud Platform)
- **Fase 6**: Documentación y best practices

## Autor

**Patricio Ahumada** | Analista / Ingeniero de Datos  
Santiago, Chile | [LinkedIn](https://linkedin.com/in/patricio-ahumada-bustos) | [GitHub](https://github.com/PatricioAhumadaBustos)

---

*Proyecto de portafolio para demostrar competencias en análisis de datos, modelado, visualización y decisiones basadas en datos.*
