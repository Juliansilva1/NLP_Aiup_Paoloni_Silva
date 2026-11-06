# Procesamiento del Lenguaje Natural - Grupo 9

Repositorio correspondiente a la práctica de la materia NLP.

## Integrantes

| Integrante |
| --- |
| Aiup, Agustín|
| Ferreira da Camara, Facundo |
| Paoloni, Franco |
| Silva, Julián |

## Estructura del repositorio

```
.gitignore
README.md
requirements.txt
src/
  TP_1/
    libros.csv
    queries.json
  TP_2/
  TP_3/
    preferencias.csv
    sospechosos.csv                    
data/
  TP_1/
    Práctica Unidad 1.pdf
    diseno_extraccion.md
  TP_2/
    Práctica Unidad 2.pdf
  TP_3/
    Informe.pdf
    Práctica Unidad 3.pdf                    
docs/
  TP_1/
    TP_1.py
  TP_2/
    TP_2.ipynb
  TP_3/
    TP_3.ipynb  
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
