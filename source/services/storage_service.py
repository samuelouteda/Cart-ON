import json
import os

# ruta relativa al archivo de memoria en la raiz
memory_file = "memoria_compra.json"

def load_list():
    # carga la memoria del disco si existe
    if os.path.exists(memory_file):
        with open(memory_file, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_list(shopping_dict):
    # guarda la memoria en el disco actualizando el estado del sistema
    with open(memory_file, "w", encoding="utf-8") as file:
        json.dump(shopping_dict, file, ensure_ascii=False, indent=4)