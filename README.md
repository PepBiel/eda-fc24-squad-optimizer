# EDA FC24 Squad Optimizer

Comparación experimental entre el algoritmo genético original del TFG y un algoritmo de estimación de distribuciones categórico (`UMDAcat`) para optimizar plantillas SBC/DCP de FC24.

El objetivo del repositorio es reproducir el problema original con una implementación controlada, ejecutar UMDA sobre los mismos retos y comparar fiabilidad, coste y tiempo frente al GA histórico.

📄 Informe del seminario: [`docs/Seminario7.pdf`](docs/Seminario7.pdf)  
📘 Memoria del TFG original: [`Treball_Final_de_Grau_vFinal.pdf`](Treball_Final_de_Grau_vFinal.pdf)

---

## Conclusión principal

UMDA directo no supera al algoritmo genético histórico. Sin embargo, al estructurar el dominio de búsqueda por slot y por requisitos del reto, UMDA mejora la fiabilidad del GA en ambos modos y reduce el coste medio en modo BD.

La conclusión principal es que el EDA puede mejorar al GA cuando la representación del problema se adapta al aprendizaje probabilístico.

| Método | Club fiabilidad | Club coste medio | BD fiabilidad | BD coste medio |
|---|---:|---:|---:|---:|
| GA histórico | 84.74% | 23,788.00 | 89.21% | 77,501.50 |
| UMDA directo | 81.05% | 29,517.00 | 82.37% | 76,819.50 |
| UMDA structured | 90.00% | 25,956.50 | 91.58% | 66,450.00 |

---

## Estructura del repositorio

El repositorio contiene:

- datos de jugadores y retos en `data/`;
- límites de normalización de precio en `config/price_bounds.json`;
- resultados históricos del GA en `results/original_ga/`;
- implementación común de carga, restricciones, fitness y reparación en `src/fc24eda/`;
- ejecución parametrizable en `scripts/run_comparison.py`;
- generación de tablas resumen en `scripts/build_report_tables.py`;
- resultados UMDA en `results/raw/` mediante CSV completos versionados para reproducibilidad;
- resumen comparativo en `results/summary/`;
- informe final del seminario en `docs/`.

---

## Decisiones metodológicas

### Representación de plantilla

Cada solución UMDA representa una plantilla como 11 variables categóricas. Cada variable selecciona un jugador del JSON original.

En la primera fase no se filtran candidatos por posición antes de construir la plantilla. Esto replica el comportamiento relevante del algoritmo original: un jugador puede aparecer en una posición que no sea la suya, pero la química se calcula después y penaliza esa situación.

La posición, por tanto, no es una restricción dura de generación. Es una condición evaluada por la función de fitness.

### Química y posición

La química no exige que el algoritmo solo genere jugadores en su posición natural. La plantilla puede contener jugadores fuera de posición. Si el jugador no cumple las posiciones válidas para el slot, su aportación de química es 0.

Esta decisión es importante porque evita reducir artificialmente el espacio de búsqueda de UMDA frente al GA original. Sin embargo, cuando un reto exige química alta, la compatibilidad posicional vuelve a ser muy importante.

### Deduplicación del JSON

No se deduplica `jugadores.json`.

El JSON se considera ya limpiado manualmente. Dos entradas con el mismo nombre no son necesariamente duplicados: pueden tener distinto club, nacionalidad, tipo de carta, precio, media u otros atributos.

Por ese motivo, el pipeline no elimina jugadores por nombre ni por atributos parciales.

### Unicidad dentro de la plantilla

Aunque el JSON no se deduplica, se verificó el algoritmo original en el proyecto `FC24CARDS` y el GA evita repetir el mismo `name` dentro de una misma plantilla.

Para que la comparación sea justa, UMDA mantiene todas las cartas en el universo de candidatos, pero repara cada solución para evitar que una misma plantilla tenga dos jugadores con el mismo `name`.

Esto replica la restricción efectiva del GA original sin destruir información del dataset.

### Normalización de precio

Se mantienen dos modos de evaluación:

- `club`: usa los límites de coste del experimento normal.
- `bd`: usa los límites de coste del experimento con base de datos.

Los límites están definidos en:

```text
config/price_bounds.json
```

La diferencia entre `club` y `bd` no está en los jugadores que puede elegir el algoritmo, sino en la escala usada para normalizar el coste dentro de la fitness.

En modo `club`, el coste se normaliza con una referencia más ajustada a los jugadores disponibles. Por tanto, el precio pesa más.

En modo `bd`, se usa una referencia global mucho mayor procedente de la base de datos. Por tanto, el mismo coste queda relativamente menos penalizado.

---

## Decisiones técnicas

### EDAspy en Windows

En este entorno, `EDAspy` importa internamente `pgmpy`, y `pgmpy` importa `torch`. En Windows se detectó un fallo de carga de DLL (`c10.dll`) cuando `torch` se cargaba indirectamente.

La solución aplicada es importar `torch` antes de importar `UMDAcat`.

### Versiones de dependencias

`numpy` se fija por debajo de la versión 2 para evitar conflictos con dependencias usadas por `EDAspy`, `pyarrow` y `pybnesian`.

Dependencias principales:

```text
numpy<2
EDAspy==1.1.4
pytest>=7.0
```

### Ruido de UMDAcat

`EDAspy==1.1.4` puede provocar errores internos si el parámetro de ruido blanco queda en un valor no numérico durante la evolución.

La implementación fuerza `w_noise = 0` y desactiva salida innecesaria para ejecuciones largas.

---

## Instalación

Entorno usado:

```bash
conda activate eda-fc24
pip install -r requirements.txt
```

También puede usarse un entorno virtual local:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En Linux o macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Prueba corta

Antes de lanzar una ejecución larga:

```bash
python scripts/run_comparison.py --algorithm umda --mode club --challenge-limit 1 --seeds 0 --max-iter 20 --size-gen 30
```

Esto valida que:

- se carga el JSON de jugadores;
- se cargan los retos;
- se importa correctamente `torch` y `EDAspy`;
- se generan soluciones;
- se evalúan restricciones;
- se escribe el CSV de salida.

---

## Ejecución experimental

### Fase 1: UMDA directo

Configuración principal usada para UMDA directo:

```text
algorithm: umda
eda: UMDAcat
seeds: 0 1 2 3 4
retos: 20
ejecuciones esperadas por modo: 100
max_iter: 800
size_gen: 200
alpha: 0.5
variables: 11
dominio por variable: todos los jugadores del JSON
reparación: unicidad por name dentro de plantilla
```

#### Club

```bash
python scripts/run_comparison.py --algorithm umda --mode club --seeds 0 1 2 3 4 --max-iter 800 --size-gen 200 --output results/raw/umda_club_final.csv
```

#### BD

```bash
python scripts/run_comparison.py --algorithm umda --mode bd --seeds 0 1 2 3 4 --max-iter 800 --size-gen 200 --output results/raw/umda_bd_final.csv
```

Si la ejecución se interrumpe, se puede continuar sin repetir combinaciones ya escritas:

```bash
python scripts/run_comparison.py --algorithm umda --mode bd --seeds 0 1 2 3 4 --max-iter 800 --size-gen 200 --output results/raw/umda_bd_final.csv --resume
```

---

## Generación de tablas

Para reconstruir el resumen comparativo con los CSV disponibles:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv
```

Salida principal:

```text
results/summary/comparison_summary.csv
```

---

## Resultados fase 1: UMDA directo

### GA histórico

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Mediana precio | Precio máximo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GA | club | 100 | 380 | 322 | 84.74% | 23,788.00 | 6,400.00 | 166,150.00 |
| GA | bd | 100 | 380 | 339 | 89.21% | 77,501.50 | 26,100.00 | 506,200.00 |

### UMDA directo Club

Resultado final disponible en:

```text
results/raw/umda_club_final.csv
```

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Mediana precio | Precio máximo | Runtime medio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UMDA | club | 100 | 380 | 308 | 81.05% | 29,517.00 | 8,575.00 | 272,600.00 | 22.91s |

Lectura inicial:

- UMDA Club queda por debajo del GA Club en fiabilidad: 308/380 frente a 322/380.
- UMDA Club también obtiene un coste medio superior: 29,517 frente a 23,788.
- Con estos parámetros, UMDA no supera al GA en modo `club`.

### UMDA directo BD

Resultado final disponible en:

```text
results/raw/umda_bd_final.csv
```

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Mediana precio | Precio máximo | Runtime medio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UMDA | bd | 100 | 380 | 313 | 82.37% | 76,819.50 | 30,975.00 | 584,400.00 | 24.39s |

Lectura inicial:

- UMDA BD queda por debajo del GA BD en fiabilidad: 313/380 frente a 339/380.
- UMDA BD obtiene un precio medio ligeramente inferior: 76,819.50 frente a 77,501.50.
- La mejora en coste no compensa la pérdida de fiabilidad con esta configuración.

### Comparación fase 1

| Comparación | Fiabilidad GA | Fiabilidad UMDA | Diferencia | Precio medio GA | Precio medio UMDA | Diferencia |
|---|---:|---:|---:|---:|---:|---:|
| club | 84.74% | 81.05% | -3.68 pp | 23,788.00 | 29,517.00 | +5,729.00 |
| bd | 89.21% | 82.37% | -6.84 pp | 77,501.50 | 76,819.50 | -682.00 |

Conclusión de la comparación estricta:

- UMDA no mejora al GA original cuando se mantiene la misma estructura general del problema.
- En modo `club`, UMDA empeora tanto en fiabilidad como en coste.
- En modo `bd`, UMDA reduce ligeramente el coste medio, pero pierde bastante fiabilidad.
- Estos resultados son válidos como experimento inicial porque comparan ambos enfoques bajo una formulación equivalente y reproducible.

---

## Diagnóstico de fase 1

La fase 1 muestra que sustituir el GA por UMDA sin modificar la representación no es suficiente. El motivo principal está en el espacio de búsqueda que recibe UMDA.

En la fase 1, cada una de las 11 variables de la plantilla podía elegir cualquier jugador del JSON:

```text
slot 1 -> cualquier jugador
slot 2 -> cualquier jugador
...
slot 11 -> cualquier jugador
```

Esto era una comparación directa con la formulación original, pero no una representación favorable para UMDA. UMDA aprende probabilidades por variable. Si cada variable puede tomar cualquier jugador del dataset, la distribución inicial es demasiado dispersa y la señal útil llega tarde.

Por ejemplo, para un slot `GK`, el algoritmo también podía probar delanteros, mediocentros o defensas. La función de fitness penaliza esas soluciones, pero la evaluación ya se ha desperdiciado. Lo mismo ocurre con retos como `Nación Única España`: si el reto pide jugadores españoles, UMDA parte igualmente de todo el JSON y descubre el requisito solo después de evaluar soluciones malas.

El GA tolera mejor esta representación amplia porque explora mediante cruce, mutación y selección. UMDA necesita dominios categóricos más informativos para que el aprendizaje probabilístico sea útil.

Un matiz importante: el requisito de media mínima no solo penaliza cuando se queda por debajo. En el score de fitness se usa una desviación absoluta respecto al mínimo, así que alejarse demasiado por arriba también empeora la puntuación. Lo que no cambia es el conteo de `unmet_requirements`: ahí solo suma si la media queda por debajo del mínimo.

---

## Arquitectura fase 2: UMDA structured

La variante implementada para la fase 2 se llama `umda_structured`.

La idea es mantener la misma evaluación, los mismos retos y las mismas restricciones, pero cambiar la forma en que UMDA ve el espacio de búsqueda.

Importante: `umda_structured` no cambia la función de fitness ni los requisitos. Solo cambia el dominio de candidatos que recibe cada variable de UMDA.

Antes:

```text
ST -> todos los jugadores
CM -> todos los jugadores
CB -> todos los jugadores
GK -> todos los jugadores
```

Ahora:

```text
ST -> dominio local de candidatos para ST
CM -> dominio local de candidatos para CM
CB -> dominio local de candidatos para CB
GK -> dominio local de candidatos para GK
```

Cada dominio local se construye por slot y por reto:

- cada slot usa un dominio local de candidatos, no todo el JSON;
- el dominio prioriza jugadores compatibles con la posición del slot;
- se reserva una parte del dominio para jugadores fuera de posición;
- se priorizan jugadores alineados con requisitos del reto, como nación, liga, club, versión y media;
- la distribución inicial de UMDA no es uniforme, sino sesgada hacia los candidatos mejor ordenados;
- se mantiene la reparación de nombres duplicados dentro de plantilla.

Esto no cambia que una solución sea válida o no. Solo cambia que UMDA empieza buscando en una zona más razonable.

### Qué no cambia

No cambia:

- la función de fitness;
- el cálculo de química;
- el cálculo de precio;
- las restricciones de los SBC;
- los datos de jugadores;
- la regla de no repetir `name` dentro de una plantilla;
- la estructura de 11 slots;
- el uso de `UMDAcat`.

### Qué cambia

Cambia la representación usada por UMDA:

```text
UMDA fase 1:
cada slot tiene como dominio todos los jugadores

UMDA structured:
cada slot tiene un dominio local de 150 candidatos priorizados
```

La fase 2 no debe interpretarse como la misma comparación que la fase 1. La lectura correcta es metodológica:

```text
Primero se aplica UMDA directamente y no mejora al GA.
Después se adapta la representación al funcionamiento de un EDA.
Con una representación más informativa, UMDA sí mejora.
```

---

## Resultados fase 2

Configuración usada:

```text
algorithm: umda_structured
seeds: 0 1 2 3 4
retos: 20
ejecuciones por modo: 100
max_iter: 100
size_gen: 100
domain_size: 150
```

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Mediana precio | Precio máximo | Runtime medio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UMDA structured | club | 100 | 380 | 342 | 90.00% | 25,956.50 | 5,975.00 | 265,600.00 | 1.78s |
| UMDA structured | bd | 100 | 380 | 348 | 91.58% | 66,450.00 | 23,100.00 | 336,450.00 | 1.76s |

### Comparación global

| Modo | GA fiabilidad | UMDA directo fiabilidad | UMDA structured fiabilidad | Mejor resultado |
|---|---:|---:|---:|---|
| club | 84.74% | 81.05% | 90.00% | UMDA structured |
| bd | 89.21% | 82.37% | 91.58% | UMDA structured |

| Modo | GA precio medio | UMDA directo precio medio | UMDA structured precio medio | Mejor resultado |
|---|---:|---:|---:|---|
| club | 23,788.00 | 29,517.00 | 25,956.50 | GA |
| bd | 77,501.50 | 76,819.50 | 66,450.00 | UMDA structured |

| Modo | UMDA directo runtime medio | UMDA structured runtime medio | Reducción |
|---|---:|---:|---:|
| club | 22.91s | 1.78s | -92.22% |
| bd | 24.39s | 1.76s | -92.79% |

### Lectura de resultados

En modo `club`, `umda_structured` mejora la fiabilidad del GA: 90.00% frente a 84.74%. El coste medio queda por encima del GA, pero por debajo de UMDA directo. Por tanto, en `club` la mejora principal es fiabilidad y tiempo, no coste absoluto.

En modo `bd`, `umda_structured` mejora todos los criterios principales: 91.58% de fiabilidad frente a 89.21% del GA, precio medio de 66,450.00 frente a 77,501.50, y runtime medio muy inferior al UMDA directo.

La mejora frente a UMDA directo es clara en ambos modos:

- `club`: de 308/380 a 342/380 requisitos cumplidos.
- `bd`: de 313/380 a 348/380 requisitos cumplidos.
- `club`: coste medio baja de 29,517.00 a 25,956.50.
- `bd`: coste medio baja de 76,819.50 a 66,450.00.
- el runtime medio baja de unos 23-24 segundos a menos de 2 segundos por ejecución.

Por semillas, el resultado también es estable. En `club`, `umda_structured` se mueve entre 88.16% y 90.79%. En `bd`, se mueve entre 90.79% y 93.42%. No depende de una única semilla excepcional.

Los retos más difíciles siguen siendo los que combinan requisitos fuertes de versión, nación, química o media alta. En `club`, destacan como pendientes `Galácticos Sencillos`, `Héroes de Champions`, `Icon Flash`, `Nación Única Brasil Elite` y `TriNación Elite`. En `bd`, los más difíciles son `Icon Flash`, `TriNación Elite`, `Leyendas Supremas` y `Nación Única Brasil Elite`.

En la media, los resultados quedan muy cerca del mínimo requerido:

| Modo | UMDA directo gap medio | UMDA structured gap medio |
|---|---:|---:|
| club | -1.03 | -0.71 |
| bd | -0.49 | -0.12 |

El gap es `overall - media_minima`. Valores cercanos a cero indican que el algoritmo aprende a no alejarse demasiado del umbral. Esto encaja con la función de fitness: acercarse demasiado por arriba también penaliza, así que la solución óptima suele vivir cerca del mínimo, no muy por encima.

---

## Diagnóstico sin precio

Para comprobar si algunos fallos vienen del coste o de la dificultad real de los requisitos, se ejecutó una variante sin penalización de precio. Esta prueba mantiene los requisitos del desafío, pero anula el término de coste de la fitness.

```bash
python scripts/run_comparison.py --algorithm umda_structured --mode club --seeds 0 1 2 3 4 --max-iter 100 --size-gen 100 --domain-size 150 --ignore-price --output results/raw/umda_structured_no_price_club_100x100_d150.csv
```

```bash
python scripts/run_comparison.py --algorithm umda_structured --mode bd --seeds 0 1 2 3 4 --max-iter 100 --size-gen 100 --domain-size 150 --ignore-price --output results/raw/umda_structured_no_price_bd_100x100_d150.csv
```

Después se generó un informe por reto:

```bash
python scripts/build_feasibility_report.py --include-raw results/raw/umda_structured_no_price_club_100x100_d150.csv results/raw/umda_structured_no_price_bd_100x100_d150.csv --output results/summary/feasibility_no_price_summary.csv
```

Resultado global:

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Runtime medio |
|---|---:|---:|---:|---:|---:|---:|---:|
| UMDA structured no price | club | 100 | 380 | 350 | 92.11% | 113,038.50 | 2.10s |
| UMDA structured no price | bd | 100 | 380 | 350 | 92.11% | 113,038.50 | 2.09s |

Al ignorar precio en la fitness, ambos modos dan el mismo resultado porque la diferencia `club`/`bd` solo afecta a la normalización del coste. La fiabilidad sube respecto a `umda_structured`, lo que indica que parte de los fallos anteriores venían del compromiso entre cumplir requisitos y mantener precio bajo.

El informe encontró una solución completa en 16 de los 20 retos. En los 4 restantes, el mejor intento quedó a un solo requisito:

| Reto | Mejor resultado | Requisito pendiente |
|---|---:|---|
| Icon Flash | 2/3 | `average.min:89` |
| Leyendas Supremas | 6/7 | `versions.min:Dynamic Duos:2` |
| Liga y Nación Mixta | 5/6 | `average.min:86` |
| TriNación Elite | 3/4 | `average.min:88` |

Esto no demuestra que esos retos sean imposibles de forma matemática. Demuestra que, con el dataset actual, la regla de no repetir nombre y la configuración `100x100_d150`, el algoritmo no encontró una plantilla completa incluso cuando el precio dejó de importar. Para afirmar imposibilidad estricta haría falta una búsqueda exacta o un modelo de satisfacción de restricciones.

La lectura práctica es que los fallos restantes no parecen depender principalmente del precio. En tres de los cuatro retos pendientes, el obstáculo es alcanzar una media muy alta manteniendo las demás restricciones. En `Leyendas Supremas`, el obstáculo detectado es encontrar dos cartas `Dynamic Duos` compatibles con el resto del reto.

---

## Conclusión para el seminario

La historia experimental queda cerrada en dos fases:

1. Fase 1: UMDA directo sobre la formulación original no mejora al GA. Esto demuestra que cambiar el algoritmo sin adaptar la representación no es suficiente.
2. Fase 2: al estructurar los dominios de búsqueda por posición y requisitos del reto, UMDA mejora claramente. Esto demuestra que los EDA dependen mucho de una representación adecuada del problema.

La conclusión principal no es simplemente que “EDA gana”, sino que:

```text
EDA puede mejorar al GA cuando el problema se formula de forma adecuada para el aprendizaje probabilístico.
```

Esta conclusión es más sólida que presentar solo una tabla de resultados, porque explica por qué la primera versión fallaba y por qué la segunda versión mejora.

---

## Reproducibilidad

Para regenerar la tabla de fase 1:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv
```

Para regenerar la tabla completa con fase 1 y fase 2:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv results/raw/umda_structured_club_100x100_d150.csv results/raw/umda_structured_bd_100x100_d150.csv
```

Para regenerar la tabla completa incluyendo el diagnóstico sin precio:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv results/raw/umda_structured_club_100x100_d150.csv results/raw/umda_structured_bd_100x100_d150.csv results/raw/umda_structured_no_price_club_100x100_d150.csv results/raw/umda_structured_no_price_bd_100x100_d150.csv
```

Salida:

```text
results/summary/comparison_summary.csv
```

Para regenerar el informe de factibilidad sin precio:

```bash
python scripts/build_feasibility_report.py --include-raw results/raw/umda_structured_no_price_club_100x100_d150.csv results/raw/umda_structured_no_price_bd_100x100_d150.csv --output results/summary/feasibility_no_price_summary.csv
```

---

## Tests

Para ejecutar las pruebas:

```bash
pytest
```

Los tests validan componentes básicos de carga, restricciones y evaluación.

---

## Referencias

- J. G. Fornes Reynes. *Tècniques evolutives per a la presa de decisions en videojocs*. Trabajo de Fin de Grado, Universitat de les Illes Balears, 2024-2025.
- H. Mühlenbein and G. Paaß. *From recombination of genes to the estimation of distributions I. Binary parameters*. PPSN IV, 1996.
- P. Larrañaga, H. Karshenas, C. Bielza and R. Santana. *A review on probabilistic graphical models in evolutionary computation*. Journal of Heuristics, 18:795-819, 2012.
