# -*- coding: utf-8 -*-
"""
Tabla de frecuencias con entradas de min, max y fi.
Calcula Amplitud (A) y Frecuencia acumulada (Fi).
Opcional: guarda a CSV/Excel.
"""

from dataclasses import dataclass
from typing import List
import pandas as pd

@dataclass
class Clase:
    minimo: float
    maximo: float
    fi: int

def pedir_entero(msg: str, minimo: int = 1) -> int:
    while True:
        try:
            v = int(input(msg).strip())
            if v < minimo:
                raise ValueError
            return v
        except ValueError:
            print(f"❌ Ingresa un entero ≥ {minimo}.")

def pedir_float(msg: str) -> float:
    while True:
        try:
            return float(input(msg).replace(",", ".").strip())
        except ValueError:
            print("❌ Ingresa un número válido (usa punto o coma).")

def leer_clases() -> List[Clase]:
    k = pedir_entero("¿Cuántas clases quieres? (p. ej., 6): ", 1)
    clases: List[Clase] = []
    print("\nIntroduce los intervalos y frecuencias. Ejemplo: mínimo=20, máximo=30, fi=20")
    for i in range(1, k + 1):
        print(f"\nClase {i}")
        a = pedir_float("  Valor mínimo: ")
        b = pedir_float("  Valor máximo: ")
        while b <= a:
            print("  ❌ El máximo debe ser mayor que el mínimo.")
            b = pedir_float("  Valor máximo: ")
        fi = pedir_entero("  Frecuencia absoluta (fi): ", 0)
        clases.append(Clase(a, b, fi))
    return clases

def construir_tabla(clases: List[Clase]) -> pd.DataFrame:
    # Construye etiquetas tipo [a, b[ excepto la última que se cierra con ]
    etiquetas = []
    for i, c in enumerate(clases):
        if i < len(clases) - 1:
            etiquetas.append(f"[ {c.minimo:g} , {c.maximo:g} [")
        else:
            etiquetas.append(f"[ {c.minimo:g} , {c.maximo:g} ]")
    amplitud = [c.maximo - c.minimo for c in clases]
    fi = [c.fi for c in clases]
    Fi = pd.Series(fi).cumsum().tolist()

    df = pd.DataFrame({
        "Valores (Intervalo)": etiquetas,
        "Valor mínimo": [c.minimo for c in clases],
        "Valor máximo": [c.maximo for c in clases],
        "Amplitud (A)": amplitud,
        "Frecuencia absoluta (fi)": fi,
        "Frecuencia acumulada (Fi)": Fi
    })

    # Fila TOTAL
    total = pd.DataFrame({
        "Valores (Intervalo)": ["TOTAL"],
        "Valor mínimo": [""],
        "Valor máximo": [""],
        "Amplitud (A)": [""],
        "Frecuencia absoluta (fi)": [sum(fi)],
        "Frecuencia acumulada (Fi)": [Fi[-1] if Fi else 0]
    })
    df = pd.concat([df, total], ignore_index=True)
    return df

def main():
    clases = leer_clases()
    tabla = construir_tabla(clases)
    print("\n📊 Tabla de frecuencias:\n")
    print(tabla.to_string(index=False))

    # Guardar (opcional)
    guardar = input("\n¿Guardar la tabla? (n=No / c=CSV / x=Excel): ").strip().lower()
    if guardar == "c":
        nombre = input("Nombre del archivo CSV (sin extensión): ").strip() or "tabla_frecuencias"
        tabla.to_csv(f"{nombre}.csv", index=False)
        print(f"✅ Guardado como {nombre}.csv")
    elif guardar == "x":
        nombre = input("Nombre del archivo Excel (sin extensión): ").strip() or "tabla_frecuencias"
        tabla.to_excel(f"{nombre}.xlsx", index=False)
        print(f"✅ Guardado como {nombre}.xlsx")

if __name__ == "__main__":
    main()
