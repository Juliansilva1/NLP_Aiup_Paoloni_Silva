# Práctica Unidad 1: Extracción y Procesamiento de Texto

Repositorio correspondiente a la práctica de la materia NLP.

El objetivo de la primera unidad es construir un corpus de libros a partir de la información disponible en la página **Lectulandia**.

## Integrantes

| Integrante | Legajo |
| --- | --- |
| Aiup | Agustín|
| Paoloni | Franco |
| Silva | Julián |

## El dataset

Cada fila de `data/libros.csv` es un libro:

| Campo | Descripción |
| --- | --- |
| `titulo` | Título del libro |
| `autores` | Autor o autores |
| `generos` | Género o géneros |
| `serie` | Serie a la que pertenece, si corresponde |
| `sinopsis` | Texto de la sinopsis |
| `url_libro` | Dirección de la ficha |
| `categoria_origen` | Categoría seleccionada: Realismo |
| `fecha_extraccion` | Fecha en que se obtuvo el registro |

**Cantidad de libros extraídos:** 120

**Criterio de selección:** se recorren las páginas del género Realismo (`/genero/realista/`
en el sitio) en orden secuencial, empezando por la página 1 y avanzando. Se toman todas
las fichas de cada página, sin filtros de autor, año, idioma, etc., hasta alcanzar la
cantidad objetivo de libros (`OBJETIVO_LIBROS` en `src/scraper.py`, actualmente 120). Con
ese objetivo el recorrido llega hasta la página 5.

## Estructura del repositorio

```
README.md
src/
  scraper.py                    # extracción con Playwright + BeautifulSoup
data/
  libros.csv                    # dataset resultante
docs/
  diseno_extraccion.md          # Parte 1: diseño de la extracción
  Práctica Unidad 1 - NLP.pdf   # consigna
```

## Instalación

Requiere Python 3.10 o superior.

```bash
git clone https://github.com/Juliansilva1/NLP_Aiup_Paoloni_Silva
cd NLP_Aiup_Paoloni_Silva

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt      # o: pip install playwright beautifulsoup4 pandas lxml
playwright install chromium
```

El último comando descarga el navegador que usa Playwright; es necesario una sola
vez por máquina.

## Ejecución

```bash
python src/scraper.py
```

El programa abre Chromium sin ventana (headless), recorre las páginas de la
categoría, visita cada ficha, extrae los datos y va guardando los resultados de
forma incremental en `data/libros.csv`. Incluye una pausa entre páginas y continúa
ante errores puntuales en vez de cortar la ejecución, de modo que una corrida
interrumpida se puede retomar sin perder lo ya obtenido.

## Dificultades encontradas

*(pendiente — se completa al final del trabajo)*
