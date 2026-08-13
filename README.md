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
