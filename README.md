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
- resultados UMDA en `results/raw/`;
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

## Comparacion Final

| Comparacion | Fiabilidad GA | Fiabilidad UMDA | Diferencia | Precio medio GA | Precio medio UMDA | Diferencia |
|---|---:|---:|---:|---:|---:|---:|
| club | 84.74% | 81.05% | -3.68 pp | 23,788.00 | 29,517.00 | +5,729.00 |
| bd | 89.21% | 82.37% | -6.84 pp | 77,501.50 | 76,819.50 | -682.00 |

Conclusion de la comparacion estricta:

- UMDA no mejora al GA original cuando se mantiene la misma estructura general del problema.
- En modo `club`, UMDA empeora tanto en fiabilidad como en coste.
- En modo `bd`, UMDA reduce ligeramente el coste medio, pero pierde bastante fiabilidad.
- Estos resultados son validos como experimento inicial porque comparan ambos enfoques bajo una formulacion equivalente y reproducible.

## Validez Para el Seminario

Estos resultados pueden servir como resultados finales de una primera parte del trabajo:

- Se ha implementado UMDA sobre el mismo problema que el GA.
- Se han usado los mismos retos, semillas controladas y numero de ejecuciones.
- Se han mantenido las restricciones relevantes del GA, incluida la unicidad por `name`.
- El resultado negativo tambien es defendible: aplicar EDA directamente no garantiza mejorar un GA ya adaptado al problema.

Para una demostracion mas fuerte, conviene plantear una segunda fase:

- Fase 1: comparacion justa, misma estructura, UMDA no mejora al GA.
- Fase 2: reformulacion orientada a EDA, donde se modifica la estructura de busqueda para que el modelo probabilistico tenga informacion mas util.

La segunda fase no deberia presentarse como la misma comparacion, sino como una mejora metodologica: "cuando adaptamos la representacion al tipo de algoritmo, EDA puede explotar mejor el problema".

## Linea de Mejora Propuesta

La debilidad principal de la representacion actual es que cada posicion puede elegir cualquier jugador del JSON. El dominio de cada variable es demasiado grande y poco informado. UMDA aprende probabilidades por slot, pero parte de una busqueda muy dispersa.

Una variante mas favorable para EDA seria:

- reducir el dominio de cada slot con candidatos compatibles por posicion o semi-compatibles;
- mantener una cuota de jugadores fuera de posicion para no romper la logica original de quimica;
- construir dominios por reto, filtrando por requisitos relevantes como rareza, liga, nacion, club, media minima o tipo de carta;
- usar una poblacion inicial heuristica, no completamente uniforme;
- mantener la reparacion de nombres duplicados;
- comparar esta variante como `umda_guided` o `umda_structured`, no como sustituto del baseline.

Esta linea permitiria contar una historia experimental clara:

1. UMDA directo sobre el problema original no supera al GA.
2. El motivo probable es la representacion: demasiadas categorias y poca estructura para aprender dependencias utiles.
3. Al introducir conocimiento del dominio en la generacion de candidatos, EDA deberia mejorar fiabilidad, coste o ambas.
4. La mejora se puede atribuir a una formulacion mas adecuada para EDA, no a una comparacion injusta.

## Reproducibilidad

Para regenerar la tabla final:

```bash
python scripts/build_report_tables.py --include-raw results/raw/umda_club_final.csv results/raw/umda_bd_final.csv
```

Salida:

```text
results/summary/comparison_summary.csv
```
