# Plan de trabajo: comparación entre Algoritmo Genético y EDA para optimización de plantillas SBC/DCP en FC24

**Autor:** Josep Fornes  
**Contexto:** Seminario de Computación Natural  
**Idea central:** reutilizar el problema de optimización del TFG y comparar el algoritmo genético original con un *Estimation of Distribution Algorithm* implementado con EDAspy.

**Nota local:** cuando este documento menciona `FC24CARDS` o el `.zip` del TFG, se refiere a la carpeta local `C:\Users\PepBiel\Documents\GitHub\FC24CARDS`.

---

## 0. Correcciones y decisiones tras revisar el código real

Después de contrastar el plan con los archivos de `FC24CARDS`, hay varios puntos que conviene fijar desde el principio:

- `jugadores.json` contiene **1008 jugadores** y `sbc_results.json` contiene **20 retos**.
- Los 20 retos suman **76 requisitos por repetición**. Con 5 repeticiones se obtienen los **380 requisitos** usados en las tablas del TFG.
- Los resultados históricos se han comprobado en los `.txt`: `Resultados_normal_1.txt` suma 58 requisitos incumplidos y `Resultados_bd_1.txt` suma 41.
- En `jugadores.json` no aparece ningún jugador con `club == "Mi Club"`. Por tanto, el modo Club/Normal no debe implementarse filtrando por esa etiqueta; debe usar el conjunto completo de `jugadores.json`, salvo que se cree explícitamente un subconjunto nuevo y se aplique igual al GA y al EDA.
- `algritmo_genetico_results.py` carga MySQL al importar y fija `MAX_TEAM_PRICE = max_team_price_db(connection)`. Para el nuevo repositorio esto no es aceptable como dependencia obligatoria: la conexión a BD debe eliminarse del camino principal y sustituirse por una referencia de precio guardada en configuración.
- El modo BD debe tratarse como una **normalización de coste distinta**, no como un cambio seguro del conjunto de jugadores candidatos, porque el código revisado usa `jugadores.json` como población y la BD principalmente para calcular `MAX_TEAM_PRICE`.
- `best_params.json` en `FC24CARDS/app` está malformado porque la clave `mut_rate` está partida en dos líneas. No debe usarse sin corregirlo.
- `algritmo_genetico_results.py` contiene `for iteration in range(4)`, mientras que los `.txt` finales contienen 5 iteraciones. Los `.txt` deben considerarse el baseline histórico y el nuevo experimento debe declarar explícitamente sus repeticiones.
- El JSON no debe limpiarse ni deduplicarse por nombre: contiene cartas distintas que pueden compartir `name`. Sin embargo, el GA original impone una restricción de plantilla: dentro de una misma plantilla no repite `player["name"]`. Para comparar de forma justa, el EDA debe aplicar esa misma restricción durante la generación/evaluación.

Mi decisión operativa sería:

> Preparar un experimento reproducible `GA-Club/Normal` vs `UMDAcat-Club/Normal`, usando `jugadores.json`, `sbc_results.json`, la misma función de fitness y una referencia de precio calculada y guardada. Yo dejaré los scripts listos, pero las ejecuciones largas sobre 20 retos y 5 semillas las realizará Josep manualmente. Después, cuando existan los archivos generados, se analizarán los resultados. BD se añadirá solo como segunda normalización de coste, sin obligar al profesor a levantar MySQL.

---

## 1. Objetivo de este documento

Este documento resume todo lo necesario para convertir el TFG en un trabajo práctico del seminario de Computación Natural. La idea no es repetir toda la memoria del TFG, sino aislar la parte de optimización de plantillas y adaptarla a un experimento con EDAs.

El trabajo del seminario debería responder a la siguiente pregunta:

> ¿Puede un EDA categórico, aplicado con EDAspy, igualar o mejorar el algoritmo genético utilizado en el TFG para resolver desafíos de creación de plantillas, manteniendo o reduciendo el coste de las plantillas generadas?

La comparación debe centrarse en resultados empíricos: fiabilidad, coste, requisitos no cumplidos, fitness y tiempo de ejecución.

---

## 2. Resumen necesario del TFG

El TFG se titula **“Tècniques evolutives per a la presa de decisions en videojocs”** y está aplicado al modo **Ultimate Team** de FC24. En este modo, cada jugador del juego se representa como una carta con atributos como media, posición, club, liga, nacionalidad, versión y precio.

La parte relevante para este seminario es la resolución automática de **Desafiamientos de Creación de Plantillas** o **DCP/SBC**. Un DCP consiste en construir una plantilla de 11 jugadores que cumpla un conjunto de requisitos concretos. Estos requisitos pueden estar relacionados con:

- media mínima de la plantilla;
- química mínima total o por jugador;
- número de ligas;
- número de clubes;
- número de nacionalidades;
- cartas especiales, como Icon, Hero, Thunderstruck, Dynamic Duos, etc.;
- restricciones de máximo o mínimo número de jugadores por liga, club o nacionalidad;
- coste total de la plantilla.

El TFG completo incluye más partes, como la captura de imágenes, segmentación de cartas, OCR, identificación de jugadores y una interfaz visual. Para el trabajo del seminario, estas partes solo deben mencionarse como contexto. La parte importante es el **motor de generación automática de plantillas**, ya que es donde aparece el algoritmo genético y donde se puede introducir el EDA.

El flujo simplificado del TFG es:

```text
Capturas del club -> OCR / YOLO -> jugadores disponibles -> requisitos del DCP -> algoritmo genético -> plantilla generada
```

Para el seminario, el flujo quedaría:

```text
jugadores disponibles + requisitos del DCP -> GA original vs EDA categórico -> comparación empírica
```

---

## 3. Problema de optimización original

El problema puede formularse como una optimización combinatoria con restricciones.

Dado:

- un conjunto de jugadores disponibles `J`;
- un conjunto de desafíos `SBC`;
- una plantilla formada por 11 huecos;
- una función de evaluación que calcula media, química, coste y cumplimiento de requisitos;

se busca encontrar una plantilla:

```text
x = [j_1, j_2, ..., j_11]
```

donde cada `j_i` es un jugador, minimizando una función de coste/fitness que penaliza:

1. incumplir requisitos del DCP;
2. tener un precio elevado;
3. generar una plantilla no válida, por ejemplo con jugadores repetidos.

En el TFG original se utiliza un algoritmo genético. Cada individuo es una plantilla completa. La población inicial se genera aleatoriamente, se evalúa con la función de aptitud y se aplican operadores evolutivos:

- selección;
- elitismo;
- cruce;
- mutación;
- reemplazo generacional.

La función de fitness es el elemento más importante que conviene reutilizar. Esta función calcula la información de la plantilla y devuelve una puntuación menor para mejores soluciones. También devuelve el número de requisitos incumplidos.

---

## 4. Decisión importante: usar slots de plantilla, no posiciones obligatorias

Para el EDA, la representación recomendada no debe imponer que cada jugador esté en su posición natural.

La representación correcta para este trabajo es:

```text
x = [slot_1, slot_2, ..., slot_11]
```

Cada variable representa un hueco de la plantilla. Cada valor posible representa un jugador candidato.

Por tanto:

```text
slot_i ∈ {todos los jugadores candidatos}
```

No se debe filtrar cada slot por posición natural del jugador.

### Justificación

En muchos DCP/SBC lo importante no es que todos los jugadores estén en su posición natural, sino cumplir requisitos de media, liga, club, nacionalidad, versión, química o coste. Si un desafío no exige mucha química, puede ser perfectamente válido usar jugadores fuera de posición para conseguir una plantilla más barata.

Además, el algoritmo genético original también genera equipos permitiendo cualquier jugador en cualquier posición y después deja que la función de evaluación calcule la química. En el código original aparece explícitamente este comentario:

```python
# Generar un equipo aleatorio permitiendo cualquier jugador en cualquier posición
```

Por tanto, restringir posiciones en el EDA haría que el EDA resolviera un problema diferente al del GA. Para que la comparación sea justa, ambos algoritmos deben buscar en el mismo espacio de soluciones.

### Consecuencia

La química se calculará igual que en el TFG: si un jugador no ocupa una posición compatible, su química será 0. Esto no invalida la plantilla automáticamente, salvo que el DCP exija química mínima. De este modo, la función de fitness decide si merece la pena usar jugadores fuera de posición.

---

## 5. Resultados originales del TFG y significado de los modos Club/Normal y BD

En el TFG se comparan dos modos principales de ejecución del algoritmo genético. Es importante explicarlos bien, porque no representan necesariamente dos algoritmos distintos, sino dos formas de ponderar el coste dentro de la función de fitness.

Los dos modos aparecen nombrados de forma ligeramente distinta entre la memoria y los archivos del proyecto:

- en la memoria se habla de **modo Club**;
- en los archivos de resultados aparece como **modo Normal**;
- para este trabajo se pueden considerar equivalentes: **Club / Normal**.

### 5.1 Modo Club / Normal

El modo **Club / Normal** corresponde a los resultados almacenados en:

```text
FC24CARDS/Analisis resultados/Resultados_normal/Resultados_normal_1.txt
```

La interpretación correcta para este trabajo es que el algoritmo trabaja con los jugadores disponibles en el archivo procesado de jugadores del proyecto:

```text
FC24CARDS/app/jugadores.json
```

Aunque en algunos comentarios del código aparece la idea de "club", el archivo revisado no contiene una etiqueta usable `club == "Mi Club"`. Por tanto, para reproducir el experimento sin cambiar el problema, **Club / Normal debe usar todos los jugadores de `jugadores.json` como candidatos**.

En este modo, el coste se normaliza usando como referencia el propio conjunto de jugadores disponible. Por tanto, el valor máximo usado para normalizar el precio no es extremadamente alto. Esto hace que el término económico tenga más peso relativo dentro del fitness.

De forma conceptual:

```text
Modo Club / Normal = coste más penalizado = plantillas más baratas, pero algo menos fiables
```

Es decir, el algoritmo tiende a encontrar soluciones económicas, pero en algunos desafíos complejos puede dejar más requisitos sin cumplir.

### 5.2 Modo BD

El modo **BD** corresponde a los resultados almacenados en:

```text
FC24CARDS/Analisis resultados/Resultados_bd/Resultados_bd_1.txt
```

Este modo no debe explicarse simplemente como “usar todos los jugadores de la base de datos para construir plantillas”, salvo que se confirme en una revisión posterior del código. Según la interpretación del código revisado, la diferencia principal del modo BD está en la **normalización del coste**.

En concreto, la base de datos global se usa para obtener una referencia de precio mucho mayor, por ejemplo mediante funciones como:

```python
max_team_price_db(connection)
```

Esta función calcula una referencia de coste asociada a los jugadores más caros de la base de datos. Al usar una referencia de precio tan alta, el coste de una plantilla normal queda relativamente más pequeño cuando se normaliza.

De forma conceptual:

```text
Modo BD = coste menos penalizado = plantillas más caras, pero mayor cumplimiento de requisitos
```

Por eso el modo BD obtiene una fiabilidad mayor, pero con un coste medio mucho más elevado.

### 5.3 Diferencia esencial entre ambos modos

La diferencia central no es el algoritmo, porque en ambos casos se utiliza el mismo algoritmo genético. La diferencia está en el peso efectivo del coste dentro del fitness.

En modo Club / Normal:

```text
coste_normalizado = coste_plantilla / referencia_de_coste_del_club
```

Como la referencia de coste es menor, el coste pesa más. El resultado son plantillas más baratas, pero con algo menos de fiabilidad.

En modo BD:

```text
coste_normalizado = coste_plantilla / referencia_de_coste_de_la_BD_global
```

Como la referencia de coste es mucho mayor, el coste pesa menos. El resultado son plantillas más caras, pero con mayor capacidad para cumplir requisitos.

Esta distinción es importante para el trabajo del seminario: el EDA no debe compararse únicamente contra “GA Club” o “GA BD” como si fueran problemas completamente distintos, sino contra el GA usando las mismas dos normalizaciones de coste.

### 5.4 Resultados globales del TFG

Los resultados finales almacenados en el `.zip` muestran 5 iteraciones sobre 20 desafíos. El número total de requisitos evaluados es 380.

| Modo | Requisitos cumplidos | Requisitos incumplidos | Fiabilidad | Coste medio | Mediana | Máximo |
|---|---:|---:|---:|---:|---:|---:|
| GA - Club / Normal | 322 / 380 | 58 | 84,7 % | 23.788 | 6.400 | 166.150 |
| GA - BD | 339 / 380 | 41 | 89,2 % | 77.501,5 | 26.100 | 506.200 |

### 5.5 Interpretación de los resultados

El modo BD consigue mayor fiabilidad porque el coste queda menos penalizado dentro de la función objetivo. Esto permite aceptar plantillas más caras si con ello se cumplen más requisitos del DCP.

El modo Club / Normal obtiene plantillas mucho más económicas, pero al penalizar más el coste puede sacrificar el cumplimiento de algunos requisitos.

La conclusión del TFG puede resumirse así:

> Existe un compromiso claro entre fiabilidad y coste. El modo BD mejora la tasa de cumplimiento, pero lo hace a costa de plantillas mucho más caras. El modo Club / Normal es más económico y puede ser suficiente para desafíos sencillos o medios.

Para el trabajo del seminario, la comparación justa debería mantener exactamente esta lógica:

| Variante | Qué representa |
|---|---|
| `GA-normal` o `GA-club` | Algoritmo genético con normalización de coste Club / Normal. |
| `GA-BD` | Algoritmo genético con normalización de coste basada en la BD global. |
| `EDA-normal` o `EDA-club` | EDA categórico con la misma normalización Club / Normal. |
| `EDA-BD` | EDA categórico con la misma normalización BD. |

De esta forma se puede afirmar que se ha sustituido el mecanismo evolutivo del GA por un EDA categórico, manteniendo constantes el conjunto de retos, los jugadores candidatos, la función objetivo y los dos modos de normalización del coste.

El objetivo no debe ser afirmar de antemano que el EDA será mejor, sino comprobar empíricamente si el aprendizaje probabilístico mejora el equilibrio entre fiabilidad y coste.

---

## 6. Archivos importantes del `.zip`

### 6.1 Archivos de datos

| Archivo | Uso |
|---|---|
| `FC24CARDS/app/jugadores.json` | Lista de jugadores disponibles para el modo Club / Normal. Contiene nombre, media, posición, precio, club, nacionalidad, liga, versión y atributos. |
| `FC24CARDS/app/sbc_results.json` | Lista de los 20 desafíos usados en los resultados finales. Incluye formación, posiciones y requisitos. |
| `FC24CARDS/app/Datasets/ScrapDatabase/fc24_futbinstats.sql` | Base de datos global usada en el modo BD, principalmente como referencia para normalizar el coste. Para el repositorio final es preferible no depender de MySQL y guardar la referencia calculada en `config/price_bounds.json`. |
| `FC24CARDS/app/sbc.json`, `sbc_complete.json`, `sbc_model.json` | Versiones alternativas o auxiliares de retos SBC. No parecen ser los resultados finales del capítulo 7. |

### 6.2 Código principal

| Archivo | Uso |
|---|---|
| `FC24CARDS/app/algritmo_genetico.py` | Implementación principal del algoritmo genético y funciones de fitness. También contiene una función `run_ga` pensada para experimentación. |
| `FC24CARDS/app/algritmo_genetico_results.py` | Variante usada para generar resultados experimentales. Contiene `NUM_GENERATIONS = 800`, `POPULATION_SIZE = 200`, `MUTATION_RATE = 0.15`, `CROSSOVER_RATE = 0.25`. |
| `FC24CARDS/app/tune_ga.py` | Script para búsqueda de hiperparámetros. |
| `FC24CARDS/app/optuna_trials.csv` | Resultados de ensayos de Optuna. |
| `FC24CARDS/app/best_params.json` | Archivo con mejores parámetros, pero en la copia revisada aparece malformado porque `mut_rate` está partido en dos líneas. Conviene no usarlo directamente sin corregirlo. |

### 6.3 Resultados finales

Estos son los archivos más importantes para comparar con el EDA:

| Archivo | Uso |
|---|---|
| `FC24CARDS/Analisis resultados/Resultados_normal/Resultados_normal_1.txt` | Resultados finales del GA en modo Club / Normal. Contiene 5 iteraciones sobre los 20 retos. |
| `FC24CARDS/Analisis resultados/Resultados_bd/Resultados_bd_1.txt` | Resultados finales del GA en modo BD. Contiene 5 iteraciones sobre los 20 retos. |

### 6.4 Análisis de hiperparámetros

| Archivo | Uso |
|---|---|
| `FC24CARDS/Analisis genetico/SBC/best_params.json` | Mejores parámetros para un conjunto de prueba SBC. |
| `FC24CARDS/Analisis genetico/SBC/optuna_trials.csv` | Ensayos de Optuna para el estudio de hiperparámetros. |
| `FC24CARDS/Analisis genetico/SBC/analisis-sbc.Rmd` | Análisis en R Markdown del estudio de hiperparámetros. |
| `FC24CARDS/Analisis genetico/SBC_COMPLETO/best_params_complete.json` | Mejores parámetros para el conjunto completo. |
| `FC24CARDS/Analisis genetico/SBC_COMPLETO/optuna_trials_complete.csv` | Ensayos de Optuna para el conjunto completo. |

### 6.5 Archivos que no son centrales para el seminario

Estos archivos son importantes para el TFG completo, pero no para el trabajo del EDA:

- scripts de OCR;
- scripts de segmentación;
- imágenes de presentación;
- modelos YOLO;
- interfaz visual;
- datasets brutos no usados directamente en el experimento.

Para el seminario, se debería trabajar con un subconjunto limpio centrado en optimización.

---

## 7. Trabajo que se debe realizar para el seminario

El trabajo práctico consistirá en implementar un EDA categórico con EDAspy y compararlo con el algoritmo genético original.

La hipótesis de trabajo puede formularse así:

> Un EDA categórico puede ser competitivo frente al algoritmo genético original porque aprende, a partir de las mejores plantillas, qué jugadores tienden a ocupar cada slot de la plantilla. Sin embargo, al usar un modelo univariante como UMDAcat, puede tener dificultades para capturar dependencias entre jugadores, ligas, clubes y nacionalidades.

Esta hipótesis es académicamente interesante porque incluso si el EDA no mejora al GA, el resultado sigue siendo explicable: UMDAcat aprende distribuciones marginales independientes y el problema tiene muchas dependencias entre variables.

---

## 8. EDA propuesto

### 8.1 Algoritmo inicial recomendado

El algoritmo inicial debería ser **UMDAcat** de EDAspy.

Motivos:

- es categórico;
- es sencillo de explicar en 2/3 folios;
- encaja con el contenido básico del seminario;
- permite comparar directamente la idea de GA frente a EDA;
- cada variable puede representar un slot de plantilla;
- cada valor posible puede ser un jugador.

EDAspy también ofrece **EBNA**, que aprende una red bayesiana discreta. EBNA podría ser una extensión interesante porque puede capturar dependencias entre variables, pero para el trabajo principal conviene empezar con UMDAcat.

### 8.2 Representación

```text
Individuo = [p_1, p_2, ..., p_11]
```

Donde:

- `p_i` es el identificador o índice de un jugador;
- hay 11 variables, una por slot de plantilla;
- cada variable tiene como dominio todos los jugadores candidatos;
- no se filtra por posición.

Ejemplo conceptual:

```text
x = [23, 501, 87, 90, 12, 44, 678, 301, 77, 11, 4]
```

Cada número representa el índice de un jugador dentro de `jugadores.json` o de la base de datos usada.

### 8.3 Función objetivo

La función objetivo del EDA debe reutilizar la misma lógica que el GA:

```text
fitness = penalización_requisitos + coste_normalizado + penalización_repetidos
```

En la práctica, conviene reutilizar:

- `calculate_info(team)`;
- `calculate_fitness(team_info, requirements)`;
- `calculate_player_chemistry(...)`;
- `calculate_team_average_from_info(...)`;
- funciones de normalización de precio.

El EDA debe minimizar el fitness.

### 8.4 Gestión de cartas repetidas

El JSON no debe modificarse ni limpiarse por nombres repetidos. En Ultimate Team puede haber varias cartas del mismo jugador con distinta media, versión, precio o tipo de carta.

Se ha revisado `jugadores.json` y no existen objetos JSON completamente idénticos. Sí existen nombres repetidos, pero eso no implica duplicado inválido.

Ahora bien, el GA original sí aplica una restricción durante la construcción de plantillas: no permite que el mismo `player["name"]` aparezca dos veces en una misma solución. Esta regla aparece en la población inicial, el cruce y la mutación.

Recomendación:

> Mantener todas las cartas del JSON como candidatos, pero reparar las soluciones del EDA para que cada plantilla tenga nombres únicos, igual que el GA original. Esto no elimina cartas del dataset; solo impone la misma restricción de plantilla que usa el baseline.

---

## 9. Comparación justa entre GA y EDA

### 9.0 Decisión sobre los resultados del GA: reutilizar o volver a ejecutar

Hay que distinguir entre dos objetivos diferentes:

1. **Usar los resultados históricos del TFG como baseline.**  
   En este caso **no es obligatorio volver a generar los resultados del algoritmo genético**. Se pueden utilizar directamente los archivos ya existentes:

   ```text
   FC24CARDS/Analisis resultados/Resultados_normal/Resultados_normal_1.txt
   FC24CARDS/Analisis resultados/Resultados_bd/Resultados_bd_1.txt
   ```

   Esta opción es válida si el trabajo del seminario se plantea como una extensión del TFG: se conserva el baseline ya reportado y se ejecuta el nuevo EDA sobre los mismos retos para comparar fiabilidad y coste.

2. **Hacer una comparación experimental completamente controlada.**  
   En este caso sí conviene **volver a ejecutar tanto el GA como el EDA** desde el nuevo repositorio, usando las mismas semillas, los mismos retos, el mismo conjunto de jugadores, la misma función de fitness y el mismo presupuesto de evaluaciones. Esta opción permite comparar también tiempo de ejecución y reduce dudas sobre diferencias producidas por cambios de entorno o de código.

La recomendación práctica es la siguiente:

- **mínimo necesario:** usar los resultados históricos del GA y ejecutar solo el EDA;
- **opción más sólida:** reejecutar el GA y el EDA con el mismo código experimental y las mismas semillas;
- si al reejecutar el GA no salen exactamente los mismos números que en el TFG, documentar la diferencia y tratar los `.txt` originales como baseline histórico.

Para el informe, puede escribirse así:

> Los resultados originales del algoritmo genético se toman como baseline histórico del TFG. Además, cuando es necesario garantizar igualdad de condiciones experimentales, el GA se reejecuta desde el nuevo repositorio con las mismas instancias y el mismo presupuesto que el EDA.

### 9.1 Modos que deben evaluarse: Club/Normal y BD

El experimento debería generar resultados en los **dos modos**, porque el TFG ya comparaba ambos y porque representan dos ponderaciones distintas del coste:

| Comparación | Qué mide | Prioridad |
|---|---|---|
| `GA-Club/Normal` vs `EDA-Club/Normal` | Compara los algoritmos cuando el coste está más penalizado. | Obligatoria |
| `GA-BD` vs `EDA-BD` | Compara los algoritmos cuando el coste está menos penalizado por la normalización basada en BD. | Muy recomendable |

Si hay poco tiempo, se puede empezar por **Club/Normal**, porque es el modo más ligado al conjunto de jugadores disponibles. Sin embargo, para una comparación completa conviene incluir también **BD**, ya que en el TFG fue el modo que obtuvo mayor fiabilidad.

Los nuevos archivos de salida deberían ser equivalentes a los originales:

```text
FC24CARDS/Analisis resultados/Resultados_eda/Resultados_eda_umda_club_1.txt
FC24CARDS/Analisis resultados/Resultados_eda/Resultados_eda_umda_bd_1.txt
```

Y, si se reejecuta el GA:

```text
FC24CARDS/Analisis resultados/Resultados_ga_reproducido/Resultados_ga_club_1.txt
FC24CARDS/Analisis resultados/Resultados_ga_reproducido/Resultados_ga_bd_1.txt
```

La tabla final del trabajo debería tener, idealmente, las cuatro filas:

```text
GA Club/Normal
EDA Club/Normal
GA BD
EDA BD
```

### 9.2 Copiar archivos desde el repositorio original del GA

Sí: para adaptar el trabajo a GitHub, lo correcto es crear un repositorio nuevo y **copiar desde el proyecto original únicamente los archivos necesarios** para reproducir la parte de optimización. No hace falta subir todo el TFG ni toda la aplicación visual.

Archivos que sí conviene copiar:

| Archivo original | Motivo | Destino recomendado en el nuevo repositorio |
|---|---|---|
| `FC24CARDS/app/jugadores.json` | Jugadores candidatos del modo Club/Normal. | `data/players/jugadores.json` |
| `FC24CARDS/app/sbc_results.json` | Retos usados en el experimento. | `data/challenges/sbc_results.json` |
| `FC24CARDS/app/algritmo_genetico.py` | Contiene lógica útil del GA, fitness, química y evaluación. | Refactorizar en `src/fc24eda/fitness.py`, `sbc_core.py` y `ga_solver.py` |
| `FC24CARDS/app/algritmo_genetico_results.py` | Script orientado a generar resultados. | Usarlo como referencia para `scripts/run_ga.py` |
| `FC24CARDS/Analisis resultados/Resultados_normal/Resultados_normal_1.txt` | Baseline histórico GA Club/Normal. | `results/original_ga/Resultados_normal_1.txt` |
| `FC24CARDS/Analisis resultados/Resultados_bd/Resultados_bd_1.txt` | Baseline histórico GA BD. | `results/original_ga/Resultados_bd_1.txt` |
| `FC24CARDS/app/Datasets/ScrapDatabase/fc24_futbinstats.sql` o referencia calculada | Necesario solo si se recalcula la normalización BD. | Preferible guardar la referencia ya calculada en `config/price_bounds.json`; subir el `.sql` solo si el profesor exige reproducir ese cálculo desde cero. |

Archivos que no conviene copiar al repositorio del seminario, salvo necesidad:

- modelos YOLO;
- capturas de pantalla;
- imágenes personales o pesadas;
- interfaz visual completa;
- datasets brutos que no afecten al experimento;
- carpetas de IDE o cachés;
- archivos `.zip` grandes.

La idea es que el nuevo repositorio sea una versión reducida y reproducible centrada en:

```text
Datos mínimos + función de fitness + GA baseline + EDA nuevo + resultados + informe
```

---

La comparación debe ser justa en términos de presupuesto computacional.

El GA de resultados usa aproximadamente:

```text
800 generaciones × 200 individuos = 160.000 evaluaciones por reto
```

Por tanto, el EDA debería usar un presupuesto similar, por ejemplo:

```text
max_iter = 800
size_gen = 200
```

o una combinación equivalente.

Si se reduce el presupuesto por tiempo, debe reducirse igual para GA y EDA.

### Métricas recomendadas

| Métrica | Descripción |
|---|---|
| Fitness final | Valor de la función objetivo del mejor individuo. |
| Requisitos incumplidos | Número de restricciones que no cumple la plantilla. |
| Fiabilidad | Porcentaje de requisitos cumplidos sobre el total. |
| Coste total | Precio total de la plantilla generada. |
| Química | Química total de la plantilla. |
| Media | Media global de la plantilla. |
| Tiempo de ejecución | Segundos por reto o por experimento completo. |

### Formato de salida recomendado

Crear archivos equivalentes a los originales:

```text
FC24CARDS/Analisis resultados/Resultados_eda/Resultados_eda_umda_club_1.txt
FC24CARDS/Analisis resultados/Resultados_eda/Resultados_eda_umda_bd_1.txt
```

Y también CSV para análisis:

```text
results/raw/ga_club.csv
results/raw/ga_bd.csv
results/raw/eda_umda_club.csv
results/raw/eda_umda_bd.csv
results/summary/comparison_summary.csv
```

Columnas recomendadas:

```text
algorithm,mode,seed,iteration,challenge_name,total_requirements,unmet_requirements,met_requirements,fitness,team_price,overall,chemistry,runtime_seconds
```

---

## 10. Diseño experimental recomendado

### Experimento mínimo

- 20 retos de `sbc_results.json`.
- 5 repeticiones, como en el TFG.
- Mismos retos, mismos jugadores candidatos y misma función de fitness para GA y EDA.
- Mismas semillas si se reejecuta todo.
- Comparar:
  - GA Club / Normal vs EDA Club / Normal;
  - GA BD vs EDA BD, si es viable, usando la misma normalización de coste basada en BD.

### Experimento ideal

- 20 retos.
- 10 repeticiones.
- 3 algoritmos:
  - GA original;
  - UMDAcat;
  - EBNA como extensión opcional.
- Mismo número de evaluaciones de fitness.
- Análisis por dificultad del reto.

### Tabla final esperada

| Algoritmo | Modo | Requisitos cumplidos | Fiabilidad | Coste medio | Mediana coste | Tiempo medio | Fitness medio |
|---|---|---:|---:|---:|---:|---:|---:|
| GA | Club | 322 / 380 | 84,7 % | 23.788 | 6.400 | pendiente | pendiente |
| UMDAcat | Club | pendiente | pendiente | pendiente | pendiente | pendiente | pendiente |
| GA | BD | 339 / 380 | 89,2 % | 77.501,5 | 26.100 | pendiente | pendiente |
| UMDAcat | BD | pendiente | pendiente | pendiente | pendiente | pendiente | pendiente |

La tabla debe completarse después de ejecutar el nuevo EDA.

---

## 11. Posible interpretación de resultados

El resultado puede salir de varias maneras. Todas son defendibles.

### Caso 1: EDA mejora al GA

Interpretación:

> UMDAcat aprende distribuciones útiles sobre qué jugadores tienden a aparecer en buenas plantillas. Esto guía mejor la búsqueda que el cruce y la mutación del GA original.

### Caso 2: EDA iguala al GA pero con menor coste o menor tiempo

Interpretación:

> El EDA es competitivo y puede ser una alternativa más simple o eficiente para el problema.

### Caso 3: EDA no mejora al GA

Interpretación:

> El problema tiene dependencias fuertes entre jugadores. La química, las ligas, los clubes y las nacionalidades dependen de combinaciones de cartas, no solo de decisiones independientes por slot. Por tanto, UMDAcat puede quedarse corto porque modela cada variable de manera independiente.

Este tercer caso también es interesante porque justifica modelos multivariantes como EBNA.

---

## 12. Implementación propuesta

### 12.1 Refactorización mínima necesaria

Antes de implementar EDAspy, conviene separar la lógica del GA en módulos limpios.

Estructura recomendada:

```text
fc24-eda-sbc/
│
├── README.md
├── requirements.txt
├── pyproject.toml                    # opcional
├── .gitignore
│
├── config/
│   └── price_bounds.json             # referencias de coste para modo club y modo BD
│
├── data/
│   ├── players/
│   │   └── jugadores.json
│   └── challenges/
│       └── sbc_results.json
│
├── src/
│   └── fc24eda/
│       ├── __init__.py
│       ├── data_loader.py
│       ├── price_reference.py # calcula MAX_TEAM_PRICE_CLUB y MAX_TEAM_PRICE_BD
│       ├── sbc_core.py
│       ├── fitness.py
│       ├── ga_solver.py
│       ├── eda_solver.py
│       ├── experiments.py
│       └── reporting.py
│
├── scripts/
│   ├── run_ga.py
│   ├── run_eda_umda.py
│   ├── run_comparison.py
│   └── build_report_tables.py
│
├── results/
│   ├── raw/
│   ├── summary/
│   └── figures/
│
├── report/
│   ├── seminario_eda_fc24.tex
│   ├── resultados_empiricos_1folio.tex
│   └── figures/
│
└── notebooks/
    └── exploratory_analysis.ipynb
```

### 12.2 Módulo `sbc_core.py`

Debe contener funciones independientes del algoritmo:

```python
def build_team_from_indices(indices, players, positions):
    team = []
    for idx, assigned_position in zip(indices, positions):
        team.append({
            "player": players[int(idx)],
            "assigned_position": assigned_position
        })
    return team
```

### 12.3 Módulo `fitness.py`

Debe contener:

- cálculo de información del equipo;
- cálculo de química;
- cálculo de media;
- cálculo de fitness;
- penalización de repetidos;
- normalización del coste.

La función central debería ser:

```python
def evaluate_solution(indices, players, challenge, price_bounds):
    positions = challenge["positions"]
    requirements = challenge["requirements"]

    team = build_team_from_indices(indices, players, positions)
    team_info = calculate_info(team)
    fitness, unmet = calculate_fitness(team_info, requirements, price_bounds)

    return fitness, team_info, unmet
```

### 12.4 Módulo `eda_solver.py`

Esqueleto orientativo:

```python
import numpy as np
from EDAspy.optimization import UMDAcat


def run_umda_for_challenge(players, challenge, price_bounds, seed, size_gen=200, max_iter=800):
    n_variables = 11
    player_ids = np.arange(len(players), dtype=object)

    possible_values = np.array(
        [player_ids.copy() for _ in range(n_variables)],
        dtype=object
    )

    frequency = np.array(
        [np.ones(len(players)) / len(players) for _ in range(n_variables)],
        dtype=object
    )

    def cost_function(solution):
        fitness, team_info, unmet = evaluate_solution(
            solution,
            players,
            challenge,
            price_bounds=price_bounds
        )
        return fitness

    eda = UMDAcat(
        size_gen=size_gen,
        max_iter=max_iter,
        dead_iter=max_iter,
        n_variables=n_variables,
        alpha=0.5,
        frequency=frequency,
        possible_values=possible_values
    )

    result = eda.minimize(cost_function, True)
    best_solution = result.best_ind
    best_fitness, team_info, unmet = evaluate_solution(
        best_solution,
        players,
        challenge,
        price_bounds=price_bounds
    )

    return {
        "solution": best_solution.tolist(),
        "fitness": best_fitness,
        "team_info": team_info,
        "unmet_requirements": unmet,
        "history": result.history
    }
```

Este código debe ajustarse a la versión exacta de EDAspy instalada. La documentación actual de EDAspy muestra el uso de `UMDAcat` y `EBNA` para optimización categórica, con `possible_values`, `frequency`, `size_gen`, `max_iter`, `dead_iter`, `n_variables` y `alpha`. También confirma que `UMDAcat` usa una distribución independiente por variable, mientras que `EBNA` aprende una red bayesiana discreta.

---

## 13. Adaptación a GitHub

El repositorio debería estar preparado para que el profesor pueda revisar el trabajo sin depender de rutas locales, MySQL configurado a mano o archivos innecesarios del TFG.

### 13.1 Qué subir

Subir:

- código limpio del experimento;
- `jugadores.json`, si no hay problemas de licencia o privacidad;
- `sbc_results.json`;
- scripts de ejecución;
- resultados agregados;
- memoria corta en LaTeX;
- README con instrucciones.

No subir o evitar:

- bases SQL muy pesadas si no son necesarias. Si se usa el modo BD solo para normalizar el coste, conviene guardar directamente la referencia calculada en un archivo de configuración o documentar cómo obtenerla;
- modelos YOLO;
- capturas personales;
- archivos de interfaz no usados;
- carpetas `.idea`, `.RData`, caches, etc.;
- archivos grandes de datasets brutos si el experimento puede ejecutarse con JSON ya procesado.

### 13.2 `.gitignore` recomendado

```gitignore
__pycache__/
*.pyc
.venv/
.env
.ipynb_checkpoints/
.RData
.Rhistory
.idea/
.DS_Store

results/raw/*.json
results/raw/*.txt
results/raw/*.csv
!results/raw/.gitkeep

*.sqlite
*.sql
*.zip
*.png
*.jpg
*.jpeg
*.pt
*.onnx

Treball_Final_de_Grau_vFinal2.pdf

!report/figures/*.png
```

Si se quieren subir figuras finales, se puede permitir `report/figures/*.png`.

### 13.3 `README.md` recomendado

El README debería incluir:

1. objetivo del trabajo;
2. resumen del TFG reutilizado;
3. explicación de GA vs EDA;
4. instalación;
5. cómo ejecutar los experimentos;
6. cómo generar las tablas;
7. estructura del repositorio;
8. resultados principales;
9. enlace al informe en PDF.

Ejemplo de comandos:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/run_comparison.py --mode club --algorithm ga --seeds 0 1 2 3 4
python scripts/run_comparison.py --mode club --algorithm umda --seeds 0 1 2 3 4
python scripts/build_report_tables.py
```

---

## 14. Informe para entregar al profesor

El profesor ha mostrado interés en los resultados empíricos. Por tanto, el trabajo debe priorizar la comparación experimental.

### 14.1 Trabajo de 2/3 folios

Estructura recomendada:

1. **Introducción.**  
   Explicar que se parte del TFG y se sustituye/compara el algoritmo genético con un EDA.

2. **Formulación del problema.**  
   Plantilla como vector de 11 variables categóricas. Cada variable es un slot y cada valor es un jugador.

3. **Método.**  
   Explicar GA original y UMDAcat. Dejar claro que UMDAcat aprende una distribución independiente por slot a partir de las mejores plantillas.

4. **Experimento.**  
   Mismos 20 retos, mismas repeticiones, mismo presupuesto de evaluaciones, mismas métricas.

5. **Resultados.**  
   Tabla comparativa y una figura sencilla.

6. **Discusión y conclusión.**  
   Interpretar si el EDA mejora o no. Discutir la limitación del modelo univariante y proponer EBNA como extensión.

### 14.2 Folio adicional de resultados empíricos en LaTeX

Además del informe principal, conviene preparar un folio específico de resultados empíricos. Este folio debería ser directo, visual y muy claro.

Debe incluir:

- una frase con el objetivo;
- configuración experimental;
- tabla principal;
- gráfico de coste/fiabilidad;
- discusión breve de 5-8 líneas;
- conclusión final.

Plantilla orientativa:

```latex
\documentclass[10pt,a4paper]{article}
\usepackage[margin=1.6cm]{geometry}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{siunitx}
\usepackage{caption}

\title{Resultados empíricos: GA vs UMDAcat en la optimización de plantillas SBC}
\author{Josep Fornes}
\date{}

\begin{document}
\maketitle

\section*{Objetivo}
Se compara el algoritmo genético utilizado en el TFG con un EDA categórico implementado mediante UMDAcat. Cada solución representa una plantilla de 11 jugadores y cada variable corresponde a un slot de la plantilla.

\section*{Configuración experimental}
Se evaluaron 20 desafíos SBC durante 5 repeticiones. Ambos algoritmos utilizaron el mismo conjunto de jugadores, los mismos requisitos, las mismas normalizaciones de coste y un presupuesto equivalente de evaluaciones de fitness.

\begin{table}[h]
\centering
\caption{Comparación global de resultados.}
\begin{tabular}{l l r r r r}
\toprule
Algoritmo & Modo & Requisitos cumplidos & Fiabilidad & Coste medio & Tiempo medio \\
\midrule
GA & Club & 322/380 & 84.7\% & 23788 & -- \\
UMDAcat & Club & --/380 & --\% & -- & -- \\
GA & BD & 339/380 & 89.2\% & 77501.5 & -- \\
UMDAcat & BD & --/380 & --\% & -- & -- \\
\bottomrule
\end{tabular}
\end{table}

\section*{Discusión}
Los resultados deben interpretarse en términos de compromiso coste--fiabilidad. Si UMDAcat mejora el coste manteniendo una fiabilidad similar, se puede considerar competitivo. Si no mejora, la explicación principal es que el modelo univariante no captura dependencias entre jugadores, ligas, clubes y nacionalidades.

\section*{Conclusión}
El experimento permite evaluar empíricamente si sustituir operadores genéticos por aprendizaje probabilístico resulta beneficioso en un problema real de optimización combinatoria.

\end{document}
```

---

## 15. Narrativa recomendada para el trabajo

La narrativa más sólida es:

> En el TFG se resolvió un problema real de optimización combinatoria mediante un algoritmo genético. En este trabajo se plantea una variante basada en EDAs, donde la generación de nuevas plantillas no se realiza mediante cruce y mutación, sino aprendiendo una distribución probabilística sobre las mejores soluciones encontradas. La comparación empírica permite estudiar si el aprendizaje probabilístico es competitivo frente al GA original y qué limitaciones aparecen en un problema con dependencias fuertes entre variables.

Esta narrativa conecta perfectamente:

- el TFG;
- el seminario de Computación Natural;
- los EDAs;
- EDAspy;
- los resultados empíricos que espera el profesor.

---

## 16. Checklist de trabajo

### Fase 1: limpieza del proyecto

- [ ] Crear repositorio GitHub limpio.
- [ ] Copiar solo archivos necesarios.
- [ ] Crear `requirements.txt`.
- [ ] Corregir rutas relativas.
- [ ] Eliminar dependencia obligatoria de MySQL para el modo Club.
- [ ] Separar funciones de fitness del script del GA.
- [ ] Crear módulo común `sbc_core.py`.

### Fase 2: baseline del GA

- [ ] Leer `jugadores.json`.
- [ ] Leer `sbc_results.json`.
- [ ] Incorporar los resultados históricos del GA: `Resultados_normal_1.txt` y `Resultados_bd_1.txt`.
- [ ] Decidir si se reejecuta el GA o si se usa únicamente el baseline histórico.
- [ ] Si se reejecuta, generar resultados para GA Club/Normal y GA BD.
- [ ] Comprobar que los resultados reejecutados son comparables a los `.txt` originales.
- [ ] Si no coinciden exactamente, documentar la diferencia.

### Fase 3: implementar EDA

- [ ] Crear `eda_solver.py`.
- [ ] Implementar representación categórica con 11 variables.
- [ ] Usar todos los jugadores como dominio de cada slot.
- [ ] Aplicar la restricción del GA: nombres únicos dentro de cada plantilla.
- [ ] Reutilizar la función de fitness del GA.
- [ ] Guardar resultados por reto y semilla.
- [ ] Generar resultados EDA en modo Club/Normal.
- [ ] Generar resultados EDA en modo BD, si se incluye la comparación completa.

### Fase 4: análisis

- [ ] Calcular fiabilidad global.
- [ ] Calcular coste medio, mediana y máximo.
- [ ] Calcular tiempo medio.
- [ ] Comparar por reto.
- [ ] Generar tabla final.
- [ ] Generar gráfico coste--fiabilidad.

### Fase 5: entrega

- [ ] Redactar informe de 2/3 folios.
- [ ] Crear folio LaTeX de resultados empíricos.
- [ ] Subir código y resultados a GitHub.
- [ ] Añadir README claro.
- [ ] Verificar que el repositorio se puede ejecutar desde cero.

---

## 17. Riesgos y cómo tratarlos

### Riesgo 1: EDAspy no acepta dominios muy grandes

`jugadores.json` contiene 1008 jugadores. Esto implica una distribución de tamaño `11 x 1008`, que es razonable, pero puede ralentizar el muestreo o el aprendizaje.

Solución:

- empezar con Club;
- si es lento, filtrar candidatos por precio/media razonable;
- mantener el filtrado igual para GA y EDA si se aplica.

### Riesgo 2: confundir limpieza del dataset con restricción de plantilla

Como UMDAcat muestrea índices de `jugadores.json`, puede seleccionar entradas con el mismo `name`. El dataset no debe limpiarse por eso, pero la plantilla final sí debe respetar la misma regla que el GA: no repetir `name`.

Solución:

- conservar todas las filas del JSON como candidatos;
- reparar la plantilla muestreada si repite `name`;
- documentar que esta restricción se introduce para igualar el espacio de búsqueda del GA original.

### Riesgo 3: el EDA no mejora

No es un problema. La discusión será interesante:

- UMDAcat no modela dependencias;
- la química depende de combinaciones;
- ligas, clubes y nacionalidades generan relaciones entre slots;
- EBNA sería la extensión natural.

### Riesgo 4: resultados no reproducibles

El código original no parece estar diseñado desde cero para reproducibilidad estricta.

Solución:

- fijar semillas;
- guardar configuración JSON;
- guardar resultados crudos;
- documentar versión de Python y librerías.

### Riesgo 5: discrepancia entre script y resultados `.txt`

El archivo `algritmo_genetico_results.py` revisado contiene un bucle de 4 iteraciones, mientras que los `.txt` finales contienen 5 iteraciones. Por tanto, los `.txt` deben tratarse como resultados finales históricos, y el nuevo experimento debe documentar explícitamente cuántas repeticiones ejecuta.

---

## 18. Conclusión operativa

La mejor opción para el seminario es implementar **UMDAcat con representación categórica libre por slots**, sin filtrar jugadores por posición. Esta decisión mantiene la comparación justa con el GA original y respeta la naturaleza de los SBC: no siempre es necesario colocar jugadores en su posición si el reto no exige química alta.

El trabajo debe entregar tres cosas:

1. **Código en GitHub** capaz de ejecutar el GA y el EDA sobre los mismos retos.
2. **Informe corto de 2/3 folios** explicando el problema, la formulación EDA y la comparación.
3. **Folio LaTeX de resultados empíricos** con tabla, gráfico y discusión breve.

La aportación principal no será simplemente “usar EDAspy”, sino demostrar experimentalmente si un EDA categórico puede competir con el algoritmo genético original en un problema real procedente del TFG.

---

## 19. Plan que yo ejecutaría

Este sería mi plan práctico, priorizado para maximizar opciones de entregar algo sólido sin atascarse con dependencias del TFG original.

### 19.1 Fase 0: cerrar el alcance

Objetivo:

```text
Comparar GA original y UMDAcat sobre los mismos 20 retos SBC, usando la misma función de fitness y el mismo conjunto de jugadores candidatos.
```

Decisiones:

- Algoritmo EDA obligatorio: `UMDAcat`.
- Algoritmo EDA opcional: `EBNA`, solo si sobra tiempo.
- Modo obligatorio: `Club/Normal`.
- Modo recomendable: `BD`, implementado como segunda referencia de normalización de coste.
- No depender de OCR, YOLO, interfaz ni MySQL para ejecutar el experimento principal.

### 19.2 Fase 1: construir repositorio mínimo reproducible

Crear esta estructura primero:

```text
config/price_bounds.json
data/players/jugadores.json
data/challenges/sbc_results.json
src/fc24eda/
scripts/
results/original_ga/
results/raw/
results/summary/
report/
```

Copiar:

- `jugadores.json`;
- `sbc_results.json`;
- `Resultados_normal_1.txt`;
- `Resultados_bd_1.txt`;
- solo las funciones necesarias de `algritmo_genetico.py` y `algritmo_genetico_results.py`.

No copiar inicialmente:

- `.sql`;
- modelos YOLO;
- imágenes;
- capturas;
- interfaz;
- notebooks antiguos;
- carpetas `.idea`.

### 19.3 Fase 2: refactorizar la evaluación antes de tocar EDAspy

Esta fase es la más importante. Antes de implementar el EDA, dejaría funcionando una evaluación pura:

```python
evaluate_solution(indices, players, challenge, price_bounds) -> EvaluationResult
```

Debe devolver:

- fitness;
- requisitos incumplidos;
- precio;
- química;
- media;
- plantilla generada;
- desglose mínimo para depurar.

Reglas:

- Nada de variables globales como `MAX_TEAM_PRICE`.
- Nada de conexión MySQL dentro de la evaluación.
- Nada de rutas relativas implícitas como `with open("jugadores.json")`.
- La misma función debe servir para GA y EDA.

### 19.4 Fase 3: reproducir el baseline histórico

Primero parsearía los `.txt` originales y generaría:

```text
results/summary/original_ga_summary.csv
```

Con estas filas:

| Algoritmo | Modo | Requisitos cumplidos | Fiabilidad | Coste medio | Mediana | Máximo |
|---|---|---:|---:|---:|---:|---:|
| GA | Club/Normal | 322 / 380 | 84,7 % | 23.788 | 6.400 | 166.150 |
| GA | BD | 339 / 380 | 89,2 % | 77.501,5 | 26.100 | 506.200 |

Esto permite tener una comparación inmediata aunque el GA refactorizado no reproduzca exactamente los números del TFG.

### 19.5 Fase 4: implementar UMDAcat en modo Club/Normal

Implementaría `eda_solver.py` con:

- 11 variables categóricas;
- dominio completo `0..len(players)-1` para cada slot;
- inicialización uniforme;
- reparación por `name` dentro de la plantilla para igualar el GA original;
- `size_gen = 200`;
- `max_iter = 800`, o una versión reducida solo para pruebas rápidas;
- semillas fijas.

Yo dejaría preparado un script de ejecución largo, pero **no lo ejecutaría automáticamente**. La ejecución real la haría Josep desde terminal cuando quiera lanzar el experimento completo:

```text
UMDAcat Club/Normal, 20 retos, 5 semillas
```

Salida:

```text
results/raw/eda_umda_club.csv
results/summary/comparison_summary.csv
```

El script debe aceptar parámetros para poder hacer primero pruebas cortas:

```bash
python scripts/run_comparison.py --algorithm umda --mode club --challenge-limit 1 --seeds 0 --max-iter 20 --size-gen 30
```

Y después la ejecución completa:

```bash
python scripts/run_comparison.py --algorithm umda --mode club --seeds 0 1 2 3 4 --max-iter 800 --size-gen 200
```

Cuando esa ejecución termine, el análisis se hará en una fase separada a partir de los CSV generados.

### 19.6 Fase 5: decidir si reejecutar el GA

Después de tener UMDAcat funcionando, decidiría:

- Si hay poco tiempo: comparar UMDAcat contra los `.txt` históricos.
- Si hay tiempo suficiente: reejecutar GA y UMDAcat con el mismo runner, mismas semillas y mismo presupuesto.

La comparación más defendible sería:

```text
GA reproducido Club/Normal vs UMDAcat Club/Normal
```

Y en el informe se dejaría el baseline histórico como referencia adicional.

### 19.7 Fase 6: añadir modo BD sin MySQL obligatorio

Para BD no levantaría MySQL en el experimento principal. Haría esto:

1. Calcular una vez la referencia BD desde el dump o desde la BD original.
2. Guardarla en:

```json
{
  "club": {
    "min_team_price": 0,
    "max_team_price": 721050
  },
  "bd": {
    "min_team_price": 0,
    "max_team_price": "valor_calculado"
  }
}
```

3. Ejecutar el mismo código cambiando solo `price_mode`.

Así el modo BD queda reproducible sin dependencia externa.

### 19.8 Fase 7: análisis y entrega

Después de que Josep ejecute los scripts largos y confirme que los resultados están en `results/raw/`, analizaría:

- tabla global de fiabilidad, coste y tiempo;
- tabla por reto;
- gráfico coste medio vs fiabilidad;
- gráfico de requisitos incumplidos por reto;
- informe de 2/3 folios;
- folio de resultados empíricos.

La conclusión debe escribirse después de ver resultados. No conviene prometer que el EDA será mejor. La pregunta correcta es:

> ¿UMDAcat mejora el equilibrio coste-fiabilidad respecto al GA, o se queda limitado por no modelar dependencias entre jugadores?

### 19.9 Orden real de trabajo

Si tuviera que ejecutarlo en el repositorio desde cero, lo haría en este orden:

1. Crear `.gitignore`, `requirements.txt` y estructura mínima.
2. Copiar JSON de jugadores y retos.
3. Copiar resultados históricos del GA.
4. Implementar `data_loader.py`.
5. Implementar `sbc_core.py`.
6. Portar y limpiar `fitness.py`.
7. Crear tests pequeños para `calculate_info`, química, media y normalización de precio.
8. Implementar parser de resultados históricos.
9. Implementar `eda_solver.py` con UMDAcat.
10. Ejecutar UMDAcat Club/Normal con 1 reto y 1 semilla.
11. Dejar documentado el comando para que Josep ejecute UMDAcat Club/Normal con 20 retos y 5 semillas.
12. Esperar a que Josep confirme que la ejecución larga ha terminado.
13. Construir `comparison_summary.csv` a partir de los resultados generados.
14. Decidir si reejecutar GA.
15. Añadir BD solo si Club/Normal ya está cerrado.
16. Escribir informe y folio final.

### 19.10 Criterio de éxito

El trabajo estará bien aunque UMDAcat no supere al GA si cumple estas condiciones:

- la comparación usa el mismo conjunto de jugadores;
- la función de fitness es común;
- el presupuesto de evaluaciones está documentado;
- las semillas y resultados crudos están guardados;
- la discusión explica claramente la limitación univariante de UMDAcat;
- el repositorio puede ejecutarse sin rutas locales absolutas ni MySQL obligatorio.
