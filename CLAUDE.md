# Práctica Unidad 1 — NLP (UNR / FCEIA)

Extracción de metadatos y sinopsis de libros desde Lectulandia con Playwright +
BeautifulSoup, para armar un corpus que luego se usa en procesamiento de texto y
en un recomendador de libros.

Consigna completa: `docs/Práctica Unidad 1 - NLP.pdf` (5 páginas, sin capa de texto —
para leerlo hay que renderizarlo a imágenes con PyMuPDF, `pdftotext` devuelve vacío).

## Estado actual

- Repo: `NLP_Aiup_Paoloni_Silva`, remote `https://github.com/Juliansilva1/NLP_Aiup_Paoloni_Silva`,
  rama `main`. Primer commit hecho y pusheado (`f840347`, solo `README.md`).
- **`CLAUDE.md` y `docs/` todavía NO están trackeados en git** — decidir si se
  suben o si van al `.gitignore`.
- **Integrantes: Agustín Aiup, Franco Paoloni, Julián Silva.**
- **Categoría elegida por el grupo: Realismo.**
- `README.md` ya escrito (versión no definitiva, ajustada por Julián): descripción,
  integrantes, tabla de campos del dataset, criterio, estructura, instalación y
  ejecución. Quedan pendientes en él: cantidad de libros extraídos y dificultades
  encontradas. Detalles menores a corregir: la columna dice "Legajo" pero contiene
  los nombres de pila, y hay un typo ("se rrecorre").
- **Criterio de selección de páginas ya decidido** (ver abajo).
- **Selectores ya relevados** (ver abajo). Falta escribir el scraper y redactar
  `docs/diseno_extraccion.md`.
- Dependencias `playwright` (+ chromium) y `beautifulsoup4` ya instaladas.

## Decisiones tomadas

### Criterio de selección de páginas

Barrido secuencial desde la primera página, sin filtros:

> Se recorren las páginas del listado del género *Realista* en el orden por
> defecto del sitio, empezando por la página 1 y avanzando secuencialmente
> (`/genero/realista/`, `/genero/realista/page/2/`, …). Se toman todas las fichas
> de cada página, sin filtros de autor, año, idioma ni valoración. El recorrido se
> detiene al alcanzar el objetivo de libros o al agotarse las páginas.

Motivos: es reproducible, no introduce sesgo del grupo (importa para el
recomendador posterior) y es trivial de programar (`for pagina in range(1, N+1)`
con corte por cantidad).

Números ya relevados: **24 fichas por página**, 162 páginas de Realista. Para 100
libros → `ceil(100/24) = 5` páginas, +1 de margen = **6**. El bucle igual corta al
llegar al objetivo de registros únicos por `url_libro`.

### Objetivo de cantidad: 100 libros

El enunciado se contradice: pide 100–200 libros en tres lugares y "entre 50 y 100"
en los controles mínimos. **Pendiente: preguntar en clase.** Mientras tanto se
apunta a 100, que cumple con ambos rangos.

## Resumen de la consigna

### Parte 1 — Diseño de la extracción (documento previo, va en `docs/diseno_extraccion.md`)

1. **Categoría seleccionada:** nombre, URL, cantidad de libros a extraer, criterio
   de selección de páginas.
2. **Datos a extraer** (mínimo): `titulo`, `autores`, `generos`, `serie`,
   `sinopsis`, `url_libro`, `categoria_origen`, `fecha_extraccion`. Portada opcional.
3. **Localización de los datos:** tabla Dato / Tipo de página / Etiqueta HTML /
   Selector propuesto, para título, autores, géneros y sinopsis (todos en la ficha
   individual). Los selectores se obtienen inspeccionando el HTML con las devtools.
4. **Estrategia de extracción** (10 pasos): abrir la categoría con Playwright →
   recorrer páginas → obtener HTML → parsear con BS4 → extraer URLs de fichas →
   visitar cada ficha → extraer metadatos y sinopsis → limpiar y validar →
   eliminar duplicados → guardar CSV.

### Parte 2 — Implementación

Programa en Python que: inicie Chromium con Playwright (puede correr headless),
recorra la categoría, obtenga las fichas, use BeautifulSoup para extraer, incluya
pausas entre páginas, maneje errores sin cortar la ejecución, evite duplicados,
guarde de forma incremental y genere `libros.csv`.

**No se descargan libros, EPUB, PDF ni otros contenidos: solo metadatos y sinopsis
públicas.**

Controles mínimos antes de entregar:
- Sin duplicados por `url_libro`.
- Todos los registros con título y con URL válida.
- La mayoría con sinopsis.
- Sin espacios ni saltos de línea sobrantes.
- Campos ausentes representados de forma consistente.
- Cantidad dentro del rango pedido (ver contradicción arriba).

### Entrega

```
README.md
src/scraper.py
data/libros.csv
docs/diseno_extraccion.md
```

`README.md` debe indicar: integrantes del grupo, categoría seleccionada, cantidad
de libros extraídos, instrucciones de instalación, instrucciones de ejecución y
principales dificultades encontradas.

Cada integrante incorpora el trabajo a su repositorio personal.

## Selectores relevados (2026-09-05)

El sitio **no** usa `/categoria/realismo/` (404). El dominio redirige a
`https://ww3.lectulandia.com` y el género se llama **Realista**:

- Listado: `https://ww3.lectulandia.com/genero/realista/`
- Paginación: `/genero/realista/page/N/` (no `/genero/realista/N/`, que da 404)
- 24 fichas por página, 162 páginas.

**Listado** — ficha: `article.card`; URL del libro: `article.card a.title` → `href`
(relativo, `/book/<slug>/`).

**Ficha individual** (`/book/<slug>/`), todo dentro de `div#bookWrapper > div#book`:

| Dato | Selector | Nota |
|---|---|---|
| `titulo` | `#title h1` | el `h1` de la página es el logo del sitio, no sirve |
| `autores` | `#autor a.dinSource` | puede haber varios `<a>` |
| `serie` | `#serie a.dinSource` | el div no existe si el libro no es de serie; `span.tagTitle` trae el número ("Libro 1 de: ") |
| `generos` | `#genero a.dinSource` | varios `<a>` |
| `sinopsis` | `#sinopsis` | texto completo; el del listado viene truncado con `[…]` |
| portada (opcional) | `#cover img` → `src` | |

De 48 fichas de Realista revisadas, **ninguna tenía `#serie`**: el campo va a estar
vacío en la mayoría de los registros. No es un error, hay que representarlo con el
marcador de ausente elegido.

## Próximos pasos

1. Completar `docs/diseno_extraccion.md` (Parte 1) — el criterio y los campos ya
   están redactados acá, falta la tabla de selectores.
2. Escribir `src/scraper.py` y correrlo.
3. Crear `src/` y `data/`, completar las secciones pendientes del README y
   preguntar en clase por la contradicción de cantidad (100–200 vs 50–100).

## Entorno

- Python en `C:\Users\Juli\AppData\Local\Programs\Python\Python314\`.
- Ya instalados: pandas, PyMuPDF, pdfplumber, pypdf, requests, lxml.
- Instalados también: `playwright` (+ chromium) y `beautifulsoup4`.
