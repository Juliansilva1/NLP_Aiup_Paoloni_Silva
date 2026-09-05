"""Scraper de Lectulandia para construir un corpus de libros del genero Realista.

Recorre las paginas del genero Realista en https://ww3.lectulandia.com, visita la
ficha de cada libro y extrae los campos definidos en el README. Los resultados se
guardan de forma incremental en ``data/libros.csv``, de modo que una corrida
interrumpida se puede retomar sin volver a descargar lo ya obtenido.

Uso:
    python src/scraper.py

Requiere ``playwright install chromium`` una vez por maquina.
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# --- Configuracion -----------------------------------------------------------

BASE_URL = "https://ww3.lectulandia.com"
CATEGORIA_PATH = "/genero/realista/"        # primera pagina del genero
CATEGORIA_ORIGEN = "Realismo"               # etiqueta que queda en cada fila

# Codificacion del CSV: utf-8-sig agrega un BOM para que Excel reconozca los
# acentos automaticamente al abrir el archivo con doble clic.
ENCODING_CSV = "utf-8-sig"

OBJETIVO_LIBROS = 120                        # cantidad de libros a extraer
PAUSA_ENTRE_PAGINAS = 2.0                    # segundos de cortesia entre paginas
PAUSA_ENTRE_FICHAS = 0.5                     # segundos de cortesia entre fichas
TIMEOUT_MS = 30_000                          # espera maxima por navegacion

# Columnas del dataset, en el orden en que se escriben al CSV.
COLUMNAS = [
    "titulo",
    "autores",
    "generos",
    "serie",
    "sinopsis",
    "url_libro",
    "categoria_origen",
    "fecha_extraccion",
]

# Ruta del CSV de salida: <raiz-del-repo>/data/libros.csv
RAIZ = Path(__file__).resolve().parent.parent
SALIDA_CSV = RAIZ / "data" / "libros.csv"


# --- Utilidades de parseo ----------------------------------------------------

def _texto(nodo) -> str:
    """Devuelve el texto de un nodo colapsando espacios; "" si el nodo es None."""
    if nodo is None:
        return ""
    return " ".join(nodo.get_text(" ", strip=True).split())


def urls_de_libros(html: str) -> list[str]:
    """Extrae las URLs absolutas de las fichas listadas en una pagina de genero."""
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for enlace in soup.select("article.card a.title"):
        href = enlace.get("href")
        if href:
            urls.append(urljoin(BASE_URL, href))
    # Elimina duplicados conservando el orden de aparicion.
    return list(dict.fromkeys(urls))


def parsear_ficha(html: str, url: str) -> dict:
    """Extrae los campos de interes de la ficha de un libro."""
    soup = BeautifulSoup(html, "lxml")
    libro = soup.select_one("#book")
    if libro is None:  # estructura inesperada: devolvemos lo minimo
        libro = soup

    titulo = _texto(libro.select_one("#title h1"))
    autores = ", ".join(_texto(a) for a in libro.select("#autor a.dinSource"))
    generos = ", ".join(_texto(a) for a in libro.select("#genero a.dinSource"))
    serie = _texto(libro.select_one("#serie a.dinSource"))  # "" si no pertenece
    sinopsis = _texto(libro.select_one("#sinopsis"))

    return {
        "titulo": titulo,
        "autores": autores,
        "generos": generos,
        "serie": serie,
        "sinopsis": sinopsis,
        "url_libro": url,
        "categoria_origen": CATEGORIA_ORIGEN,
        "fecha_extraccion": date.today().isoformat(),
    }


# --- Persistencia incremental ------------------------------------------------

def cargar_urls_existentes() -> set[str]:
    """Lee las URLs ya guardadas para poder retomar una corrida interrumpida."""
    if not SALIDA_CSV.exists():
        return set()
    try:
        previo = pd.read_csv(SALIDA_CSV, encoding=ENCODING_CSV)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return set()
    return set(previo.get("url_libro", pd.Series(dtype=str)).dropna())


def guardar_fila(fila: dict) -> None:
    """Agrega una fila al CSV, escribiendo el encabezado solo la primera vez."""
    SALIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    escribir_encabezado = not SALIDA_CSV.exists()
    pd.DataFrame([fila], columns=COLUMNAS).to_csv(
        SALIDA_CSV,
        mode="a",
        header=escribir_encabezado,
        index=False,
        encoding=ENCODING_CSV,
    )


# --- Descarga con Playwright -------------------------------------------------

def obtener_html(page, url: str) -> str | None:
    """Navega a ``url`` y devuelve el HTML renderizado; None ante un error."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        return page.content()
    except PlaywrightTimeoutError:
        print(f"  ! timeout al cargar {url}", file=sys.stderr)
        return None
    except Exception as exc:  # noqa: BLE001 - queremos continuar ante cualquier error
        print(f"  ! error al cargar {url}: {exc}", file=sys.stderr)
        return None


def url_de_pagina(numero: int) -> str:
    """URL de la pagina ``numero`` del listado (la pagina 1 no lleva sufijo)."""
    if numero == 1:
        return urljoin(BASE_URL, CATEGORIA_PATH)
    return urljoin(BASE_URL, f"{CATEGORIA_PATH}page/{numero}/")


# --- Flujo principal ---------------------------------------------------------

def main() -> None:
    ya_extraidos = cargar_urls_existentes()
    total = len(ya_extraidos)
    if total:
        print(f"Retomando: {total} libros ya presentes en {SALIDA_CSV.name}.")

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        page = navegador.new_page()

        numero_pagina = 1
        while total < OBJETIVO_LIBROS:
            url_pagina = url_de_pagina(numero_pagina)
            print(f"Pagina {numero_pagina}: {url_pagina}")

            html_listado = obtener_html(page, url_pagina)
            if html_listado is None:
                print("  ! no se pudo cargar la pagina; se corta el recorrido.")
                break

            urls = urls_de_libros(html_listado)
            if not urls:
                print("  ! la pagina no tiene fichas; se corta el recorrido.")
                break

            for url_libro in urls:
                if total >= OBJETIVO_LIBROS:
                    break
                if url_libro in ya_extraidos:
                    continue

                html_ficha = obtener_html(page, url_libro)
                if html_ficha is None:
                    continue  # error puntual: seguimos con la siguiente ficha

                try:
                    fila = parsear_ficha(html_ficha, url_libro)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! error al parsear {url_libro}: {exc}", file=sys.stderr)
                    continue

                if not fila["titulo"]:
                    print(f"  ! ficha sin titulo, se omite: {url_libro}", file=sys.stderr)
                    continue

                guardar_fila(fila)
                ya_extraidos.add(url_libro)
                total += 1
                print(f"  [{total:>3}/{OBJETIVO_LIBROS}] {fila['titulo']}")
                time.sleep(PAUSA_ENTRE_FICHAS)

            numero_pagina += 1
            time.sleep(PAUSA_ENTRE_PAGINAS)

        navegador.close()

    print(f"Listo. {total} libros en {SALIDA_CSV}.")


if __name__ == "__main__":
    main()
