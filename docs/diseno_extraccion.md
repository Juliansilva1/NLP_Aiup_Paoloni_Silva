# Diseño de la extracción

Se describe qué se extrae, de dónde y con qué estrategia, antes de pasar a la implementación en
`src/scraper.py`.

## 1. Categoría seleccionada

| | |
| --- | --- |
| **Categoría** | Realismo |
| **URL de la categoría** | `https://ww3.lectulandia.com/genero/realista/` |
| **Cantidad de libros a extraer** | 120 |
| **Fecha del relevamiento** | 05/09/2026 |

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
120 libros del objetivo alcanza con recorrer **5 páginas** (`120 / 24 = 5`).

## 2. Datos a extraer

| Campo | Descripción |
| --- | --- |
| `titulo` | Título del libro |
| `autores` | Autor o autores |
| `generos` | Géneros |
| `serie` | Serie a la que pertenece el libro |
| `sinopsis` | Texto de la sinopsis |
| `url_libro` | URL absoluta de la ficha |
| `categoria_origen` | Categoría desde la que se llegó al libro |
| `fecha_extraccion` | Fecha en que se obtuvo el registro |

## 3. Localización de los datos

Los selectores se obtuvieron inspeccionando el HTML del sitio con las
herramientas de desarrollador del navegador.

### Página de listado

| Dato | Tipo de página | Etiqueta HTML | Selector propuesto |
| --- | --- | --- | --- |
| Ficha de un libro | Listado de la categoría | `<article class="card">` | `article.card` |
| URL de la ficha | Listado de la categoría | `<a class="title" href="...">` | `article.card a.title` → atributo `href` |

### Ficha individual

Todos los datos están dentro del contenedor `div#bookWrapper > div#book`.

| Dato | Tipo de página | Etiqueta HTML | Selector propuesto |
| --- | --- | --- | --- |
| Título | Ficha individual | `<div id="title"><h1>` | `#title h1` |
| Autores | Ficha individual | `<div id="autor">` con uno o varios `<a class="dinSource">` | `#autor a.dinSource` |
| Géneros | Ficha individual | `<div id="genero">` con varios `<a class="dinSource">` | `#genero a.dinSource` |
| Serie | Ficha individual | `<div id="serie">` con un `<a class="dinSource">` | `#serie a.dinSource` |
| Sinopsis | Ficha individual | `<div id="sinopsis">` | `#sinopsis` |

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
  pantalla y el programa sigue con la siguiente, sin cortar la ejecución.
- Se hace una pausa de 2 segundos entre páginas del listado y de 0,5 segundos
  entre fichas, para no sobrecargar el servidor.

### Guardado incremental

El CSV se escribe fila por fila a medida que se extrae cada libro, en lugar de
acumular todo en memoria y volcarlo al final. Además, al arrancar, el programa
lee las `url_libro` que ya están en el archivo y las saltea. De esta forma una
corrida interrumpida se puede retomar sin volver a descargar lo ya obtenido.

El archivo se guarda con codificación `utf-8-sig` para que los acentos se vean
correctamente al abrirlo con Excel.