# Modelos locales y demostración

Este documento describe el registro de modelos de riesgo. La proyección numérica
por alumno/aula usa un artefacto sintético independiente y está documentada en
[predicción de rendimiento](prediccion-rendimiento.md), con su contrato y evidencia.

La API mantiene REQ-29–32 separados del cálculo académico oficial. No incorpora
servicios externos, claves, costos ni modelos de deserción. No extrae datos reales
para entrenar. Las decisiones institucionales siguen pendientes.

## Flujo actual

1. Administrador solicita `POST /risk-models/demonstration/train`, reconociendo el
   carácter ficticio. Configura semilla, 80–200 alumnos, corte experimental del
   resultado futuro y probabilidades media/alta (API). Umbrales por defecto 10,4
   y 0,3/0,7 solo demostrativos; no representan política de la institución.
2. La solicitud queda persistida. `PAIDEIA_AI_AUTORUN=true` habilita un proceso
   Python auxiliar por trabajo; por defecto está deshabilitado. Alternativa de
   operador en el laboratorio: `python -B scripts/run_lab_ai_worker.py UUID`.
   No servicio permanente ni cola externa; solo un trabajo pendiente/en ejecución.
3. El worker crea `ai_demo_UUID` y aplica Alembic exclusivamente en ese esquema;
   usa los modelos académicos existentes y población completamente ficticia.
   No escribe notas en public. Nunca reutiliza ni borra un esquema previo.
4. Extrae notas y asistencia estrictamente anteriores al periodo objetivo. Features:
   promedio previo, tendencia, presencia, tardanzas, cantidad/cobertura de historia
   y fracción literal C. Nombres, documentos, contactos y texto libre quedan fuera.
   Datos faltantes se imputan con medianas ajustadas solo sobre entrenamiento.
5. Entrena regresión logística y baseline mayoritario. Evalúa el último periodo
   en alumnos separados de entrenamiento; publica precisión/recall/F1, Brier,
   matriz de confusión, split, versiones de biblioteca, parámetros y huella.
   Artefacto: coeficientes/intercepto, normalización/imputación y nombres de features
   numéricos en JSON. No pickle/joblib ni cargas de archivos ejecutables.
6. El candidato requiere revisión y `POST /risk-models/UUID/approve`; activación
   independiente con `expected_version`, motivo y reconocimiento sintético.
   Conflictos devuelven 409. Activar una versión previa hace rollback explícito;
   no se sobrescriben las métricas del modelo anterior. run_id identifica la versión.
7. Inferencia demostrativa solo sobre su propio esquema ficticio. Expone estado,
   probabilidades, asociaciones (no causas), versión, fecha y cobertura. Menos de
   dos periodos observados produce historia insuficiente, sin riesgo fabricado.

Lectura demostrativa: personal autorizado; entrenamiento/aprobación/activación y
eventos de auditoría: administrador. Alumno/apoderado no accede a este panel.
El dashboard BI muestra conteos ficticios en una sección independiente. Ninguna
predicción sintética se asocia con estudiantes del esquema académico de trabajo.

## Recursos y recuperación

Compose de entornos limita backend/operaciones a 768 MiB de memoria/swap y un CPU,
ajustables mediante `BACKEND_MEMORY_LIMIT` / `BACKEND_CPU_LIMIT`. Worker: un hilo
BLAS y máximo 180 segundos de CPU. No construir frontend mientras se entrena.
La prueba con navegador reserva 1,5 GiB; reentrenamiento por API sin Edge reserva
1 GiB. Navegador BI de solo lectura, sin entrenamiento/build concurrente: 1 GiB.
Los márgenes corresponden a la carga de cada recorrido; detener la operación
si no están disponibles, sin forzar un recorrido más pesado.

Un fallo queda como `failed` con código genérico; se conserva el esquema para
inspección autorizada, sin imprimir URLs, datos ni credenciales. Una terminación
externa (OOM/SIGKILL) puede dejar `running`: revisar proceso/recursos y estado antes
de recuperar esa ejecución; no solicitar trabajos ilimitados ni activar candidatos
sin resultados. La recuperación automática de trabajos interrumpidos no está validada.
Backups y recuperación productiva requieren el procedimiento institucional separado;
el laboratorio conserva el único volumen sintético, sin limpiar otros recursos.

## Habilitación institucional futura

Reutilizar extractor temporal y pipeline; exigir fuente autorizada, etiquetas reales,
historia y calidad suficientes, objetivo/horizonte/cortes confirmados, evaluación
temporal y por alumno, comparación/calibración y revisión pedagógica explícita.
Datos adicionales deben entrar por los flujos académicos existentes, sin editar el
algoritmo. El panel actual no ofrece activación institucional ni entrenamiento real:
esas salvaguardas y aceptación con historia real están pendientes. No interpretar
resultados sintéticos como validación institucional. No inventar reglas de fórmulas
o criterios opcionales para fabricar etiquetas de entrenamiento oficiales.

Referencias técnicas: [regresión logística sklearn 1.7.2](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html)
y [seguridad de persistencia](https://scikit-learn.org/1.7/model_persistence.html).
