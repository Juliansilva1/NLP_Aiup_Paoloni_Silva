# Práctica Unidad 1: Extracción y Procesamiento de Texto

Repositorio correspondiente a la práctica de la materia NLP.

El objetivo de la primera unidad es construir un corpus de libros a partir de la información disponible en la página **Lectulandia**.

## Integrantes

| Integrante |
| --- |
| Aiup, Agustín|
| Ferreira da Camara, Facundo |
| Paoloni, Franco |
| Silva, Julián |

## El dataset

Cada fila de `data/libros.csv` es un libro:

| Campo | Descripción |
| --- | --- |
| `id` | Identificador asignado al libro |
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
cantidad objetivo de libros.

## Estructura del repositorio

```
README.md
CLAUDE.md
.gitignore
src/
  scraper.py                    
data/
  libros.csv                    
docs/
  diseno_extraccion.md          
  Práctica Unidad 1 - NLP.pdf   
```

## Instalación

Requiere Python 3.10 o superior.

1. Clonar el repositorio:

```bash
git clone https://github.com/Juliansilva1/NLP_Aiup_Paoloni_Silva
```

2. Dentro de la carpeta del repositorio, crear un entorno virtual y activarlo:

```bash
cd NLP_Aiup_Paoloni_Silva
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
```

3. Instalar los requerimientos y el browser Chromium:

```bash
pip install -r requirements.txt
playwright install chromium
```

## Ejecución

Posicionarse dentro de la carpeta del repositorio y ejecutar:
```bash
python src/scraper.py     # Windows: python .\src\scraper.py
```

El programa abre Chromium sin ventana (headless), recorre las páginas de la
categoría, visita cada ficha, extrae los datos y va guardando los resultados de
forma incremental en `data/libros.csv`. Incluye una pausa entre páginas y continúa
ante errores puntuales en vez de cortar la ejecución, de modo que una corrida
interrumpida se puede retomar sin perder lo ya obtenido.

## Dificultades encontradas

*(pendiente — se completa al final del trabajo)*
