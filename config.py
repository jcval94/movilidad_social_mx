# config.py

VAR_CATEGORIES = {
    "generation": [
        "Millennial",
        "Gen X",
        "Baby Boomer",
        "NA"
    ],
    "sex": [
        "Hombre",
        "Mujer"
    ],
    "education": [
        "Primaria",
        "Secundaria",
        "Preparatoria",
        "Universidad",
        "Posgrado",
        "Otro",
        "NA"
    ]
}

# Lista de variables disponibles para filtrar
POSSIBLE_VARS = list(VAR_CATEGORIES.keys())

# Límites de memoria/sesión
MAX_UPLOAD_SIZE_MB = 10
MAX_SESSION_OBJECT_SIZE_MB = 5
SESSION_IDLE_TIMEOUT_SECONDS = 30 * 60
SESSION_MAX_RUNTIME_SECONDS = 2 * 60 * 60
