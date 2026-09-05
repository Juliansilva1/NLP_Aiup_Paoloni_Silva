# Diseño de la extracción

**Práctica Unidad 1 — Extracción y Procesamiento de Texto (NLP, UNR / FCEIA)**

Integrantes: Agustín Aiup, Franco Paoloni, Julián Silva.

Documento correspondiente a la Parte 1 de la práctica. Describe qué se extrae, de
dónde y con qué estrategia, antes de pasar a la implementación en
`src/scraper.py`.

---

## 1. Categoría seleccionada

| | |
| --- | --- |
| **Categoría** | Realismo |
| **URL del listado** | `https://ww3.lectulandia.com/genero/realista/` |
| **Cantidad de libros a extraer** | 120 |
| **Fecha del relevamiento** | 05/09/2026 |

### Nota sobre la URL

El sitio no expone la categoría bajo el nombre "Realismo" ni bajo la ruta
`/categoria/`. El relevamiento con las herramientas de desarrollador mostró que:

- El dominio `lectulandia.com` redirige a `ww3.lectulandia.com`.
- Las categorías cuelgan de `/genero/`, no de `/categoria/`.
- El género se llama **Realista**, no "Realismo": la ruta `/genero/realismo/`
  devuelve un 404 y `/genero/realista/` es la correcta.

Se mantiene "Realismo" como nombre de la categoría en el informe y en el campo
`categoria_origen` del dataset, por ser el término con el que el grupo eligió la
categoría, y se documenta acá la correspondencia con el slug real del sitio.

### Criterio de selección de páginas

Se recorren las páginas del listado del género Realista en el orden por defecto
del sitio, empezando por la página 1 y avanzando secuencialmente:

```
https://ww3.lectulandia.com/genero/realista/            (página 1)
https://ww3.lectulandia.com/genero/realista/page/2/     (página 2)
https://ww3.lectulandia.com/genero/realista/page/N/     (página N)
```

Se toman **todas** las fichas de cada página, sin filtros de autor, año, idioma
ni valoración. El recorrido se detiene al alcanzar la cantidad objetivo de libros
o al agotarse las páginas disponibles.

Se eligió este criterio por tres motivos:

1. **Es reproducible.** Cualquiera que corra el programa sobre el mismo listado
   obtiene el mismo conjunto de libros.
2. **No introduce sesgo del grupo.** Como el corpus se usa después en un
   recomendador, filtrar por preferencias propias contaminaría los resultados.
3. **Es simple de programar.** Un bucle sobre el número de página con corte por
   cantidad, sin lógica de filtrado.

El género Realista tiene **162 páginas de 24 fichas cada una**. Para llegar a los
120 libros del objetivo alcanza con recorrer **5 páginas** (`120 / 24 = 5`). El
bucle igual corta por cantidad de registros únicos y no por número de página, así
que el objetivo se puede cambiar sin recalcular nada.

---

## 2. Datos a extraer

| Campo | Descripción | Tipo | Si falta |
| --- | --- | --- | --- |
| `titulo` | Título del libro | Texto | No debería faltar; la ficha se descarta |
| `autores` | Autor o autores, separados por `, ` | Texto | Cadena vacía |
| `generos` | Géneros asignados por el sitio, separados por `, ` | Texto | Cadena vacía |
| `serie` | Serie a la que pertenece el libro | Texto | Cadena vacía |
| `sinopsis` | Texto de la sinopsis | Texto | Cadena vacía |
| `url_libro` | URL absoluta de la ficha; identifica al registro | Texto | No debería faltar |
| `categoria_origen` | Categoría desde la que se llegó al libro (`Realismo`) | Texto | Constante |
| `fecha_extraccion` | Fecha en que se obtuvo el registro, en formato ISO | Fecha | Constante por corrida |

Los campos ausentes se representan siempre con la **cadena vacía**, nunca con
`None`, `NaN` ni textos como "N/D", de modo que el criterio sea uniforme en todo
el archivo.

`autores` y `generos` pueden contener más de un valor: se guardan en una sola
celda separados por coma y espacio.

No se descarga la portada, ni los archivos EPUB o PDF de los libros: se extraen
únicamente metadatos y sinopsis públicas.

### Sobre el campo `serie`

La mayoría de los libros del género no pertenece a ninguna serie. En el
relevamiento, sobre 48 fichas revisadas ninguna tenía el dato, y en el dataset
final quedó vacío en 111 de los 120 registros. **No es un error de extracción**:
el sitio directamente omite el bloque de serie en las fichas de libros sueltos,
por lo que el campo vacío es el valor correcto.

---

## 3. Localización de los datos

Los selectores se obtuvieron inspeccionando el HTML del sitio con las
herramientas de desarrollador del navegador.

### Página de listado

| Dato | Tipo de página | Etiqueta HTML | Selector propuesto |
| --- | --- | --- | --- |
| Ficha de un libro | Listado de la categoría | `<article class="card">` | `article.card` |
| URL de la ficha | Listado de la categoría | `<a class="title" href="...">` | `article.card a.title` → atributo `href` |

Cada página del listado contiene 24 elementos `article.card`. El `href` es
relativo (`/book/<slug>/`), así que hay que combinarlo con el dominio para
obtener la URL absoluta.

El listado también muestra un fragmento de la sinopsis dentro de
`article.card .description`, pero **viene truncado** con puntos suspensivos entre
corchetes. Por eso la sinopsis se toma de la ficha individual y no del listado.

### Ficha individual

Todos los datos están dentro del contenedor `div#bookWrapper > div#book`.

| Dato | Tipo de página | Etiqueta HTML | Selector propuesto |
| --- | --- | --- | --- |
| Título | Ficha individual | `<div id="title"><h1>` | `#title h1` |
| Autores | Ficha individual | `<div id="autor">` con uno o varios `<a class="dinSource">` | `#autor a.dinSource` |
| Géneros | Ficha individual | `<div id="genero">` con varios `<a class="dinSource">` | `#genero a.dinSource` |
| Serie | Ficha individual | `<div id="serie">` con un `<a class="dinSource">` | `#serie a.dinSource` |
| Sinopsis | Ficha individual | `<div id="sinopsis">` | `#sinopsis` |

Tres observaciones del relevamiento:

- **El título no se toma del `<h1>` de la página.** El primer `<h1>` del documento
  es el logo del sitio (`h1.site-title`). El título del libro está en el `<h1>`
  que cuelga de `div#title`, de ahí que el selector sea `#title h1` y no `h1`.
- **El `div#serie` no existe** cuando el libro no pertenece a una serie, con lo
  cual el selector no devuelve nada y el campo queda vacío. Cuando sí existe, el
  `<span class="tagTitle">` que lo precede indica además el número de orden
  ("Libro 1 de: "); ese número no se guarda, solo el nombre de la serie.
- Los enlaces de autor y género llevan `class="dinSource"`, lo que permite
  distinguirlos de otros enlaces del mismo bloque.

---

## 4. Estrategia de extracción

1. **Abrir el navegador.** Iniciar Chromium con Playwright en modo headless (sin
   ventana) y crear una página.
2. **Recorrer las páginas del listado.** Construir la URL de la página `N` según
   el patrón de paginación del sitio (la página 1 sin sufijo, el resto con
   `page/N/`) y navegar hasta ella.
3. **Obtener el HTML.** Esperar a que el documento cargue y tomar el HTML
   renderizado de la página.
4. **Parsear el listado con BeautifulSoup.** Construir el árbol del documento
   para poder consultarlo con selectores CSS.
5. **Extraer las URLs de las fichas.** Aplicar `article.card a.title`, leer el
   `href` de cada resultado y convertirlo en URL absoluta.
6. **Visitar cada ficha.** Navegar a cada URL de libro y obtener su HTML,
   respetando una pausa entre pedidos.
7. **Extraer los metadatos y la sinopsis.** Parsear la ficha con BeautifulSoup y
   aplicar los selectores de la sección 3 para obtener título, autores, géneros,
   serie y sinopsis. Agregar `url_libro`, `categoria_origen` y
   `fecha_extraccion`.
8. **Limpiar y validar.** Colapsar espacios múltiples y saltos de línea del texto
   extraído, dejar en cadena vacía los campos ausentes y descartar la ficha si no
   tiene título.
9. **Eliminar duplicados.** Mantener el conjunto de `url_libro` ya procesadas y
   saltear las repetidas, tanto dentro de una misma corrida como respecto de lo
   que ya esté guardado en el CSV.
10. **Guardar en CSV.** Escribir cada registro validado en `data/libros.csv` en el
    momento, con las columnas en un orden fijo.

### Manejo de errores y cortesía

- Cada navegación va dentro de un bloque de manejo de errores con un tiempo
  máximo de espera de 30 segundos. Un error puntual en una ficha se informa por
  pantalla y el programa **sigue con la siguiente**, sin cortar la ejecución.
- Se hace una pausa de 2 segundos entre páginas del listado y de 0,5 segundos
  entre fichas, para no sobrecargar el servidor.

### Guardado incremental

El CSV se escribe fila por fila a medida que se extrae cada libro, en lugar de
acumular todo en memoria y volcarlo al final. Además, al arrancar, el programa
lee las `url_libro` que ya están en el archivo y las saltea. De esta forma una
corrida interrumpida se puede retomar sin volver a descargar lo ya obtenido.

El archivo se guarda con codificación `utf-8-sig` para que los acentos se vean
correctamente al abrirlo con Excel.

---

## 5. Controles previstos sobre el dataset

Antes de la entrega se verifica que:

- No haya duplicados por `url_libro`.
- Todos los registros tengan título y una URL válida.
- La mayoría de los registros tenga sinopsis.
- No queden espacios ni saltos de línea sobrantes.
- Los campos ausentes estén representados de forma consistente.
- La cantidad de registros esté dentro del rango pedido.
