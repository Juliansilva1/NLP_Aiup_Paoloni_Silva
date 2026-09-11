"""Scraper de Lectulandia para construir un corpus de libros del genero Realista. """

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# La consola de Windows usa cp1252 y no puede representar algunos caracteres que
# aparecen en los titulos. Sin esto, imprimir un titulo con "u" macron corta la
# corrida entera con UnicodeEncodeError. Los caracteres que no entran se
# reemplazan por "?" solo en pantalla; el CSV se escribe aparte en utf-8.
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(errors="replace")
    except (AttributeError, ValueError):  # flujo redirigido o sin soporte
        pass


# --- Configuracion -----------------------------------------------------------

BASE_URL = "https://ww3.lectulandia.com"
CATEGORIA_PATH = "/genero/realista/"        # primera pagina del genero
CATEGORIA_ORIGEN = "Realismo"               # etiqueta que queda en cada fila

# Codificacion del CSV: utf-8-sig agrega un BOM para que Excel reconozca los
# acentos automaticamente al abrir el archivo con doble clic.
ENCODING_CSV = "utf-8-sig"

OBJETIVO_LIBROS = 120                        # cantidad de libros a extraer
PAUSA_ENTRE_PAGINAS = 2.0                    # segundos de cortesia entre paginas
PAUSA_ENTRE_FICHAS = 1.5                     # segundos de cortesia entre fichas
TIMEOUT_MS = 30_000                          # espera maxima por navegacion

# Cuando se le piden muchas paginas seguidas, el sitio deja de devolver la ficha
# y responde con una pagina de espera ("Estamos siendo atacados") que pide
# aguardar unos segundos. Hay que esperar y volver a pedirla, porque descartar
# el libro seria perder un dato que el sitio si tiene.
REINTENTOS_FICHA = 3                         # intentos por ficha antes de rendirse
ESPERA_REINTENTO = 6.0                       # segundos de espera antes de reintentar

# Columnas del dataset, en el orden en que se escriben al CSV.
COLUMNAS = [
    "id",
    "titulo",
    "autores",
    "generos",
    "serie",
    "sinopsis",
    "url_libro",
    "categoria_origen",
    "fecha_extraccion",
]

# Campos que son listas. En memoria se manejan como listas de Python; al
# escribir el CSV se serializan a JSON, porque una celda solo puede contener
# texto. Para recuperarlos como listas hay que usar ``leer_dataset``.
CAMPOS_LISTA = ("autores", "generos")

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
    """Extrae los campos de interes de la ficha de un libro.

    ``autores`` y ``generos`` se devuelven como listas de Python, que pueden
    venir vacias si la ficha no trae el dato. El campo ``id`` no se asigna aca:
    lo pone ``main`` al momento de guardar, porque es un numero secuencial que
    depende de cuantos libros haya en el CSV.
    """
    soup = BeautifulSoup(html, "lxml")
    libro = soup.select_one("#book")
    if libro is None:  # estructura inesperada: devolvemos lo minimo
        libro = soup

    titulo = _texto(libro.select_one("#title h1"))
    autores = [_texto(a) for a in libro.select("#autor a.dinSource")]
    generos = [_texto(a) for a in libro.select("#genero a.dinSource")]
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

def cargar_estado() -> tuple[set[str], int]:
    """Devuelve las URLs ya guardadas y el ultimo id asignado.

    Sirve para retomar una corrida interrumpida sin repetir libros y sin
    reiniciar la numeracion. Se toma el id maximo y no la cantidad de filas,
    para que la secuencia siga siendo correcta aunque se haya borrado alguna.
    """
    vacio: tuple[set[str], int] = (set(), 0)
    if not SALIDA_CSV.exists():
        return vacio
    try:
        previo = pd.read_csv(SALIDA_CSV, encoding=ENCODING_CSV)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return vacio

    urls = set(previo.get("url_libro", pd.Series(dtype=str)).dropna())
    ids = pd.to_numeric(
        previo.get("id", pd.Series(dtype="float")), errors="coerce"
    ).dropna()
    ultimo_id = int(ids.max()) if not ids.empty else 0
    return urls, ultimo_id


def guardar_fila(fila: dict) -> None:
    """Agrega una fila al CSV, escribiendo el encabezado solo la primera vez."""
    SALIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    escribir_encabezado = not SALIDA_CSV.exists()

    # Las listas van al CSV como JSON: ["Ensayo", "Novela"]. Con
    # ensure_ascii=False los acentos quedan legibles en vez de escapados.
    fila_csv = dict(fila)
    for campo in CAMPOS_LISTA:
        fila_csv[campo] = json.dumps(fila_csv[campo], ensure_ascii=False)

    pd.DataFrame([fila_csv], columns=COLUMNAS).to_csv(
        SALIDA_CSV,
        mode="a",
        header=escribir_encabezado,
        index=False,
        encoding=ENCODING_CSV,
    )


def leer_dataset(ruta: Path | None = None) -> pd.DataFrame:
    """Lee el CSV devolviendo ``autores`` y ``generos`` como listas de Python.

    Es la contraparte de ``guardar_fila``. Quien consuma el corpus deberia usar
    esta funcion en vez de ``pd.read_csv`` directo, porque si no las listas
    quedan en forma de texto JSON sin parsear.
    """
    datos = pd.read_csv(ruta or SALIDA_CSV, encoding=ENCODING_CSV)
    for campo in CAMPOS_LISTA:
        datos[campo] = datos[campo].apply(
            lambda celda: json.loads(celda) if isinstance(celda, str) else []
        )
    return datos


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


def obtener_ficha(page, url: str) -> str | None:
    """Descarga la ficha de un libro, reintentando si el sitio pide esperar.

    La pagina de espera que devuelve el limitador de velocidad no tiene el
    bloque ``#book``, asi que se usa su ausencia para detectarla. Devuelve None
    si despues de ``REINTENTOS_FICHA`` intentos sigue sin llegar la ficha.
    """
    for intento in range(1, REINTENTOS_FICHA + 1):
        html = obtener_html(page, url)
        if html is not None and BeautifulSoup(html, "lxml").select_one("#book"):
            return html
        if intento < REINTENTOS_FICHA:
            print(f"  . el sitio pidio esperar; reintento {intento}/{REINTENTOS_FICHA - 1}")
            time.sleep(ESPERA_REINTENTO)
    return None


def url_de_pagina(numero: int) -> str:
    """URL de la pagina ``numero`` del listado (la pagina 1 no lleva sufijo)."""
    if numero == 1:
        return urljoin(BASE_URL, CATEGORIA_PATH)
    return urljoin(BASE_URL, f"{CATEGORIA_PATH}page/{numero}/")


# --- Flujo principal ---------------------------------------------------------

def main() -> None:
    ya_extraidos, ultimo_id = cargar_estado()
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

                html_ficha = obtener_ficha(page, url_libro)
                if html_ficha is None:
                    print(f"  ! no se pudo obtener la ficha: {url_libro}", file=sys.stderr)
                    continue  # error puntual: seguimos con la siguiente ficha

                try:
                    fila = parsear_ficha(html_ficha, url_libro)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! error al parsear {url_libro}: {exc}", file=sys.stderr)
                    continue

                if not fila["titulo"]:
                    print(f"  ! ficha sin titulo, se omite: {url_libro}", file=sys.stderr)
                    continue

                ultimo_id += 1
                fila["id"] = ultimo_id

                guardar_fila(fila)
                ya_extraidos.add(url_libro)
                total += 1
                print(f"  [{total:>3}/{OBJETIVO_LIBROS}] #{fila['id']} {fila['titulo']}")
                time.sleep(PAUSA_ENTRE_FICHAS)

            numero_pagina += 1
            time.sleep(PAUSA_ENTRE_PAGINAS)

        navegador.close()

    print(f"Listo. {total} libros en {SALIDA_CSV}.")


if __name__ == "__main__":
    main()
