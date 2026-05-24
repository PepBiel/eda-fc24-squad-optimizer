# EDA FC24 Squad Optimizer

Comparacion experimental entre el algoritmo genetico original del TFG y un EDA categorico (`UMDAcat`) para optimizar plantillas SBC/DCP de FC24.

El objetivo del repositorio es reproducir el problema original con una implementacion controlada, ejecutar UMDA sobre los mismos retos y comparar fiabilidad, coste y tiempo frente al GA historico.

## Estado Actual

El repositorio contiene:

- datos de jugadores y retos en `data/`;
- limites de normalizacion de precio en `config/price_bounds.json`;
- resultados historicos del GA en `results/original_ga/`;
- implementacion comun de carga, restricciones, fitness y reparacion en `src/fc24eda/`;
- ejecucion parametrizable en `scripts/run_comparison.py`;
- generacion de tablas resumen en `scripts/build_report_tables.py`;
- resultados UMDA en `results/raw/` (CSV completos versionados para reproducibilidad);
- resumen comparativo en `results/summary/`.

## Decisiones Metodologicas

### Representacion de Plantilla

Cada solucion UMDA representa una plantilla como 11 variables categoricas. Cada variable selecciona un jugador del JSON original.

No se filtran candidatos por posicion antes de construir la plantilla. Esto replica el comportamiento relevante del algoritmo original: un jugador puede aparecer en una posicion que no sea la suya, pero la quimica se calcula despues y penaliza esa situacion.

La posicion, por tanto, no es una restriccion dura de generacion. Es una condicion evaluada por la funcion de fitness.

### Quimica y Posicion

La quimica no exige que el algoritmo solo genere jugadores en su posicion natural. La plantilla puede contener jugadores fuera de posicion. Si el jugador no cumple las posiciones validas para el slot, su aportacion de quimica es 0.

Esta decision es importante porque evita reducir artificialmente el espacio de busqueda de UMDA frente al GA original.

### Deduplicacion del JSON

No se deduplica `jugadores.json`.

El JSON se considera ya limpiado manualmente. Dos entradas con el mismo nombre no son necesariamente duplicados: pueden tener distinto club, nacionalidad, tipo de carta, precio, media u otros atributos.

Por ese motivo, el pipeline no elimina jugadores por nombre ni por atributos parciales.

### Unicidad Dentro de la Plantilla

Aunque el JSON no se deduplica, se verifico el algoritmo original en `C:\Users\PepBiel\Documents\GitHub\FC24CARDS` y el GA evita repetir el mismo `name` dentro de una misma plantilla.

Para que la comparacion sea justa, UMDA mantiene todas las cartas en el universo de candidatos, pero repara cada solucion para evitar que una misma plantilla tenga dos jugadores con el mismo `name`.

Esto replica la restriccion efectiva del GA original sin destruir informacion del dataset.

### Normalizacion de Precio

Se mantienen dos modos de evaluacion:

- `club`: usa los limites de coste del experimento normal.
- `bd`: usa los limites de coste del experimento con base de datos.

Los limites estan definidos en `config/price_bounds.json`.

## Decisiones Tecnicas

### EDAspy en Windows

En este entorno, `EDAspy` importa internamente `pgmpy`, y `pgmpy` importa `torch`. En Windows se detecto un fallo de carga de DLL (`c10.dll`) cuando `torch` se cargaba indirectamente.

La solucion aplicada es importar `torch` antes de importar `UMDAcat`.

### Versiones de Dependencias

`numpy` se fija por debajo de la version 2 para evitar conflictos con dependencias usadas por `EDAspy`, `pyarrow` y `pybnesian`.

Dependencias principales:

```text
numpy<2
EDAspy==1.1.4
pytest>=7.0
```

### Ruido de UMDAcat

`EDAspy==1.1.4` puede provocar errores internos si el parametro de ruido blanco queda en un valor no numerico durante la evolucion.

La implementacion fuerza `w_noise = 0` y desactiva salida innecesaria para ejecuciones largas.

## Instalacion

Entorno usado:

```bash
conda activate eda-fc24
pip install -r requirements.txt
```

Tambien puede usarse un entorno virtual local:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Prueba Corta

Antes de lanzar una ejecucion larga:

```bash
python scripts/run_comparison.py --algorithm umda --mode club --challenge-limit 1 --seeds 0 --max-iter 20 --size-gen 30
```

Esto valida que:

- carga el JSON de jugadores;
- carga los retos;
- importa correctamente `torch` y `EDAspy`;
- genera soluciones;
- evalua restricciones;
- escribe el CSV de salida.

## Ejecucion Experimental

Configuracion principal usada para UMDA:

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
reparacion: unicidad por name dentro de plantilla
```

### Club

```bash
python scripts/run_comparison.py --algorithm umda --mode club --seeds 0 1 2 3 4 --max-iter 800 --size-gen 200 --output results/raw/umda_club_final.csv
```

### BD

```bash
python scripts/run_comparison.py --algorithm umda --mode bd --seeds 0 1 2 3 4 --max-iter 800 --size-gen 200 --output results/raw/umda_bd_final.csv
```

Si la ejecucion se interrumpe, se puede continuar sin repetir combinaciones ya escritas:

```bash
python scripts/run_comparison.py --algorithm umda --mode bd --seeds 0 1 2 3 4 --max-iter 800 --size-gen 200 --output results/raw/umda_bd_final.csv --resume
```

## Generacion de Tablas

Para reconstruir el resumen comparativo con los CSV disponibles:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv
```

Salida principal:

```text
results/summary/comparison_summary.csv
```

## Resultados Actuales

### GA Historico

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Mediana precio | Precio maximo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GA | club | 100 | 380 | 322 | 84.74% | 23,788.00 | 6,400.00 | 166,150.00 |
| GA | bd | 100 | 380 | 339 | 89.21% | 77,501.50 | 26,100.00 | 506,200.00 |

### UMDA Club

Resultado final disponible en:

```text
results/raw/umda_club_final.csv
```

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Mediana precio | Precio maximo | Runtime medio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UMDA | club | 100 | 380 | 308 | 81.05% | 29,517.00 | 8,575.00 | 272,600.00 | 22.91s |

Lectura inicial:

- UMDA Club queda por debajo del GA Club en fiabilidad: 308/380 frente a 322/380.
- UMDA Club tambien obtiene un coste medio superior: 29,517 frente a 23,788.
- Con estos parametros, UMDA no supera al GA en modo `club`.

### UMDA BD

Resultado final disponible en:

```text
results/raw/umda_bd_final.csv
```

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Mediana precio | Precio maximo | Runtime medio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UMDA | bd | 100 | 380 | 313 | 82.37% | 76,819.50 | 30,975.00 | 584,400.00 | 24.39s |

Lectura inicial:

- UMDA BD queda por debajo del GA BD en fiabilidad: 313/380 frente a 339/380.
- UMDA BD obtiene un precio medio ligeramente inferior: 76,819.50 frente a 77,501.50.
- La mejora en coste no compensa la perdida de fiabilidad con esta configuracion.

## Comparacion Fase 1

| Comparacion | Fiabilidad GA | Fiabilidad UMDA | Diferencia | Precio medio GA | Precio medio UMDA | Diferencia |
|---|---:|---:|---:|---:|---:|---:|
| club | 84.74% | 81.05% | -3.68 pp | 23,788.00 | 29,517.00 | +5,729.00 |
| bd | 89.21% | 82.37% | -6.84 pp | 77,501.50 | 76,819.50 | -682.00 |

Conclusion de la comparacion estricta:

- UMDA no mejora al GA original cuando se mantiene la misma estructura general del problema.
- En modo `club`, UMDA empeora tanto en fiabilidad como en coste.
- En modo `bd`, UMDA reduce ligeramente el coste medio, pero pierde bastante fiabilidad.
- Estos resultados son validos como experimento inicial porque comparan ambos enfoques bajo una formulacion equivalente y reproducible.

## Problema Detectado

La fase 1 muestra que sustituir el GA por UMDA sin modificar la representacion no es suficiente. El motivo principal esta en el espacio de busqueda que recibe UMDA.

En la fase 1, cada una de las 11 variables de la plantilla podia elegir cualquier jugador del JSON:

```text
slot 1 -> cualquier jugador
slot 2 -> cualquier jugador
...
slot 11 -> cualquier jugador
```

Esto era una comparacion justa, pero no una representacion favorable para UMDA. UMDA aprende probabilidades por variable. Si cada variable puede tomar cualquier jugador del dataset, la distribucion inicial es demasiado dispersa y la senal util llega tarde.

Por ejemplo, para un slot `GK`, el algoritmo tambien podia probar delanteros, mediocentros o defensas. La funcion de fitness penaliza esas soluciones, pero la evaluacion ya se ha desperdiciado. Lo mismo ocurre con retos como `Nacion Unica Espana`: si el reto pide jugadores espanoles, UMDA parte igualmente de todo el JSON y descubre el requisito solo despues de evaluar soluciones malas.

El GA tolera mejor esta representacion amplia porque explora mediante cruce, mutacion y seleccion. UMDA necesita dominios categoricos mas informativos para que el aprendizaje probabilistico sea util.

Un matiz importante: el requisito de media minima no solo penaliza cuando se queda por debajo. En el score de fitness se usa una desviacion absoluta respecto al minimo, asi que alejarse demasiado por arriba tambien empeora la puntuacion. Lo que no cambia es el conteo de `unmet_requirements`: ahi solo suma si la media queda por debajo del minimo.

## Arquitectura Fase 2

La variante implementada para la fase 2 se llama `umda_structured`.

La idea es mantener la misma evaluacion, los mismos retos y las mismas restricciones, pero cambiar la forma en que UMDA ve el espacio de busqueda.

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
- el dominio prioriza jugadores compatibles con la posicion del slot;
- se reserva una parte del dominio para jugadores fuera de posicion;
- se priorizan jugadores alineados con requisitos del reto, como nacion, liga, club, version y media;
- la distribucion inicial de UMDA no es uniforme, sino sesgada hacia los candidatos mejor ordenados;
- se mantiene la reparacion de nombres duplicados dentro de plantilla.

Esto no cambia que una solucion sea valida o no. Solo cambia que UMDA empieza buscando en una zona mas razonable.

### Que No Cambia

No cambia:

- la funcion de fitness;
- el calculo de quimica;
- el calculo de precio;
- las restricciones de los SBC;
- los datos de jugadores;
- la regla de no repetir `name` dentro de una plantilla;
- la estructura de 11 slots;
- el uso de `UMDAcat`.

### Que Cambia

Cambia la representacion usada por UMDA:

```text
UMDA fase 1:
cada slot tiene como dominio todos los jugadores

UMDA structured:
cada slot tiene un dominio local de 150 candidatos priorizados
```

La fase 2 no debe interpretarse como la misma comparacion que la fase 1. La lectura correcta es metodologica:

```text
Primero se aplica UMDA directamente y no mejora al GA.
Despues se adapta la representacion al funcionamiento de un EDA.
Con una representacion mas informativa, UMDA si mejora.
```

## Resultados Fase 2

Configuracion usada:

```text
algorithm: umda_structured
seeds: 0 1 2 3 4
retos: 20
ejecuciones por modo: 100
max_iter: 100
size_gen: 100
domain_size: 150
```

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Mediana precio | Precio maximo | Runtime medio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UMDA structured | club | 100 | 380 | 342 | 90.00% | 25,956.50 | 5,975.00 | 265,600.00 | 1.78s |
| UMDA structured | bd | 100 | 380 | 348 | 91.58% | 66,450.00 | 23,100.00 | 336,450.00 | 1.76s |

### Comparacion Global

| Modo | GA fiabilidad | UMDA baseline fiabilidad | UMDA structured fiabilidad | Mejor resultado |
|---|---:|---:|---:|---|
| club | 84.74% | 81.05% | 90.00% | UMDA structured |
| bd | 89.21% | 82.37% | 91.58% | UMDA structured |

| Modo | GA precio medio | UMDA baseline precio medio | UMDA structured precio medio | Mejor resultado |
|---|---:|---:|---:|---|
| club | 23,788.00 | 29,517.00 | 25,956.50 | GA |
| bd | 77,501.50 | 76,819.50 | 66,450.00 | UMDA structured |

| Modo | UMDA baseline runtime medio | UMDA structured runtime medio | Reduccion |
|---|---:|---:|---:|
| club | 22.91s | 1.78s | -92.22% |
| bd | 24.39s | 1.76s | -92.79% |

### Lectura de Resultados

En modo `club`, `umda_structured` mejora la fiabilidad del GA: 90.00% frente a 84.74%. El coste medio queda por encima del GA, pero por debajo de UMDA baseline. Por tanto, en `club` la mejora principal es fiabilidad y tiempo, no coste absoluto.

En modo `bd`, `umda_structured` mejora todos los criterios principales: 91.58% de fiabilidad frente a 89.21% del GA, precio medio de 66,450.00 frente a 77,501.50, y runtime medio muy inferior al UMDA baseline.

La mejora frente a UMDA baseline es clara en ambos modos:

- `club`: de 308/380 a 342/380 requisitos cumplidos.
- `bd`: de 313/380 a 348/380 requisitos cumplidos.
- `club`: coste medio baja de 29,517.00 a 25,956.50.
- `bd`: coste medio baja de 76,819.50 a 66,450.00.
- el runtime medio baja de unos 23-24 segundos a menos de 2 segundos por ejecucion.

Por semillas, el resultado tambien es estable. En `club`, `umda_structured` se mueve entre 88.16% y 90.79%. En `bd`, se mueve entre 90.79% y 93.42%. No depende de una unica semilla excepcional.

Los retos mas dificiles siguen siendo los que combinan requisitos fuertes de version, nacion, quimica o media alta. En `club`, destacan como pendientes `Galacticos Sencillos`, `Heroes de Champions`, `Icon Flash`, `Nacion Unica Brasil Elite` y `TriNacion Elite`. En `bd`, los mas dificiles son `Icon Flash`, `TriNacion Elite`, `Leyendas Supremas` y `Nacion Unica Brasil Elite`.

En la media, los resultados quedan muy cerca del minimo requerido:

| Modo | UMDA baseline gap medio | UMDA structured gap medio |
|---|---:|---:|
| club | -1.03 | -0.71 |
| bd | -0.49 | -0.12 |

El gap es `overall - media_minima`. Valores cercanos a cero indican que el algoritmo aprende a no alejarse demasiado del umbral. Esto encaja con la funcion de fitness: acercarse demasiado por arriba tambien penaliza, asi que la solucion optima suele vivir cerca del minimo, no muy por encima.

## Diagnostico Sin Precio

Para comprobar si algunos fallos vienen del coste o de la dificultad real de los requisitos, se ejecuto una variante sin penalizacion de precio. Esta prueba mantiene los requisitos del desafio, pero anula el termino de coste de la fitness:

```bash
python scripts/run_comparison.py --algorithm umda_structured --mode club --seeds 0 1 2 3 4 --max-iter 100 --size-gen 100 --domain-size 150 --ignore-price --output results/raw/umda_structured_no_price_club_100x100_d150.csv
```

```bash
python scripts/run_comparison.py --algorithm umda_structured --mode bd --seeds 0 1 2 3 4 --max-iter 100 --size-gen 100 --domain-size 150 --ignore-price --output results/raw/umda_structured_no_price_bd_100x100_d150.csv
```

Despues se genero un informe por reto:

```bash
python scripts/build_feasibility_report.py --include-raw results/raw/umda_structured_no_price_club_100x100_d150.csv results/raw/umda_structured_no_price_bd_100x100_d150.csv --output results/summary/feasibility_no_price_summary.csv
```

Resultado global:

| Algoritmo | Modo | Runs | Requisitos | Cumplidos | Fiabilidad | Precio medio | Runtime medio |
|---|---:|---:|---:|---:|---:|---:|---:|
| UMDA structured no price | club | 100 | 380 | 350 | 92.11% | 113,038.50 | 2.10s |
| UMDA structured no price | bd | 100 | 380 | 350 | 92.11% | 113,038.50 | 2.09s |

Al ignorar precio, ambos modos dan el mismo resultado porque la diferencia `club`/`bd` solo afecta a la normalizacion del coste. La fiabilidad sube respecto a `umda_structured`, lo que indica que parte de los fallos anteriores venian del compromiso entre cumplir requisitos y mantener precio bajo.

El informe encontro una solucion completa en 16 de los 20 retos. En los 4 restantes, el mejor intento quedo a un solo requisito:

| Reto | Mejor resultado | Requisito pendiente |
|---|---:|---|
| Icon Flash | 2/3 | `average.min:89` |
| Leyendas Supremas | 6/7 | `versions.min:Dynamic Duos:2` |
| Liga y Nacion Mixta | 5/6 | `average.min:86` |
| TriNacion Elite | 3/4 | `average.min:88` |

Esto no demuestra que esos retos sean imposibles de forma matematica. Demuestra que, con el dataset actual, la regla de no repetir nombre y la configuracion `100x100_d150`, el algoritmo no encontro una plantilla completa incluso cuando el precio dejo de importar. Para afirmar imposibilidad estricta haria falta una busqueda exacta o un modelo de satisfaccion de restricciones.

La lectura practica es que los fallos restantes no parecen depender principalmente del precio. En tres de los cuatro retos pendientes, el obstaculo es alcanzar una media muy alta manteniendo las demas restricciones. En `Leyendas Supremas`, el obstaculo detectado es encontrar dos cartas `Dynamic Duos` compatibles con el resto del reto.

## Conclusion Para el Seminario

La historia experimental queda cerrada en dos fases:

1. Fase 1: UMDA directo sobre la formulacion original no mejora al GA. Esto demuestra que cambiar el algoritmo sin adaptar la representacion no es suficiente.
2. Fase 2: al estructurar los dominios de busqueda por posicion y requisitos del reto, UMDA mejora claramente. Esto demuestra que los EDA dependen mucho de una representacion adecuada del problema.

La conclusion principal no es simplemente que "EDA gana", sino que:

```text
EDA puede mejorar al GA cuando el problema se formula de forma adecuada para el aprendizaje probabilistico.
```

Esta conclusion es mas solida que presentar solo una tabla de resultados, porque explica por que la primera version fallaba y por que la segunda version mejora.

## Reproducibilidad

Para regenerar la tabla de fase 1:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv
```

Para regenerar la tabla completa con fase 1 y fase 2:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv results/raw/umda_structured_club_100x100_d150.csv results/raw/umda_structured_bd_100x100_d150.csv
```

Para regenerar la tabla completa incluyendo el diagnostico sin precio:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv results/raw/umda_structured_club_100x100_d150.csv results/raw/umda_structured_bd_100x100_d150.csv results/raw/umda_structured_no_price_club_100x100_d150.csv results/raw/umda_structured_no_price_bd_100x100_d150.csv
```

Salida:

```text
results/summary/comparison_summary.csv
```
