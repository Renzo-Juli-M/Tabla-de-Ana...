# -*- coding: utf-8 -*-
"""
Interfaz gráfica para tablas de frecuencias (datos agrupados).
Funciona con Tkinter (incluido en Python). Gráficos opcionales con matplotlib.

Autor: tú + ChatGPT :)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ---- matplotlib (opcional) ----
HAS_MPL = False
try:
    import matplotlib.pyplot as plt  # pip install matplotlib
    HAS_MPL = True
except Exception:
    HAS_MPL = False


# ===================== MODELO =====================

@dataclass
class Clase:
    minimo: float
    maximo: float
    fi: int

    @property
    def amplitud(self) -> float:
        return self.maximo - self.minimo

    @property
    def marca(self) -> float:
        return (self.minimo + self.maximo) / 2.0


# ===================== CÁLCULOS =====================

def construir_tabla(clases: List[Clase]) -> Tuple[List[dict], int]:
    filas = []
    n = sum(c.fi for c in clases)
    Fi = 0
    for i, c in enumerate(clases):
        Fi += c.fi
        etiqueta = f"[ {c.minimo:g} , {c.maximo:g} " + ("]" if i == len(clases)-1 else "[")
        filas.append({
            "intervalo": etiqueta,
            "min": c.minimo,
            "max": c.maximo,
            "A": c.amplitud,
            "fi": c.fi,
            "Fi": Fi
        })
    return filas, n


def media_agrupada(clases: List[Clase]) -> float:
    n = sum(c.fi for c in clases)
    if n == 0:
        return float("nan")
    return sum(c.marca * c.fi for c in clases) / n


def buscar_clase_por_posicion(clases: List[Clase], posicion: float) -> Tuple[int, int]:
    Fi = 0
    for i, c in enumerate(clases):
        previo = Fi
        Fi += c.fi
        if posicion <= Fi:
            return i, previo
    return len(clases)-1, Fi - clases[-1].fi


def cuantil_agrupado(clases: List[Clase], k: int, m: int = 4) -> float:
    n = sum(c.fi for c in clases)
    if n == 0:
        return float("nan")
    pos = k * n / m
    i, Fi_1 = buscar_clase_por_posicion(clases, pos)
    c = clases[i]
    return c.minimo + ((pos - Fi_1) / c.fi) * c.amplitud


def mediana_agrupada(clases: List[Clase]) -> float:
    return cuantil_agrupado(clases, 2, 4)


def moda_agrupada(clases: List[Clase]) -> Optional[float]:
    if not clases:
        return None
    idx = max(range(len(clases)), key=lambda i: clases[i].fi)
    c = clases[idx]
    f0 = clases[idx-1].fi if idx-1 >= 0 else 0
    f1 = c.fi
    f2 = clases[idx+1].fi if idx+1 < len(clases) else 0
    d1 = f1 - f0
    d2 = f1 - f2
    if d1 + d2 == 0:
        return (c.minimo + c.maximo) / 2.0
    return c.minimo + (d1 / (d1 + d2)) * c.amplitud


def dispersion_agrupada(clases: List[Clase]) -> dict:
    n = sum(c.fi for c in clases)
    if n == 0:
        return {"rango": float("nan"), "var": float("nan"), "sd": float("nan"), "IQR": float("nan"), "CV%": float("nan")}
    xbar = media_agrupada(clases)
    ss = sum(c.fi * (c.marca - xbar) ** 2 for c in clases)
    var = ss / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    q1 = cuantil_agrupado(clases, 1, 4)
    q3 = cuantil_agrupado(clases, 3, 4)
    return {
        "rango": clases[-1].maximo - clases[0].minimo,
        "var": var,
        "sd": sd,
        "IQR": q3 - q1,
        "CV%": (sd / xbar * 100.0) if xbar != 0 else float("inf")
    }


# ===================== INTERFAZ (Tkinter) =====================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Frecuencias - Sprint 1")
        self.geometry("980x600")
        self.minsize(880, 520)

        self.clases: List[Clase] = []

        self._crear_widgets()
        self._configurar_layout()
        self._refrescar_tabla()

    # ---- UI ----
    def _crear_widgets(self):
        # Panel de entrada
        self.frame_in = ttk.LabelFrame(self, text="Ingresar clase")
        self.var_min = tk.StringVar()
        self.var_max = tk.StringVar()
        self.var_fi  = tk.StringVar()

        self.e_min = ttk.Entry(self.frame_in, width=12, textvariable=self.var_min)
        self.e_max = ttk.Entry(self.frame_in, width=12, textvariable=self.var_max)
        self.e_fi  = ttk.Entry(self.frame_in, width=12, textvariable=self.var_fi)

        self.btn_add = ttk.Button(self.frame_in, text="Agregar / Actualizar", command=self._agregar_clase)
        self.btn_clear = ttk.Button(self.frame_in, text="Limpiar campos", command=self._limpiar_campos)

        # Tabla
        self.frame_tabla = ttk.LabelFrame(self, text="Tabla de frecuencias")
        cols = ("intervalo", "min", "max", "A", "fi", "Fi")
        self.tree = ttk.Treeview(self.frame_tabla, columns=cols, show="headings", height=10)
        headings = {
            "intervalo": "Valores (Intervalo)",
            "min": "Mín",
            "max": "Máx",
            "A": "A",
            "fi": "fi",
            "Fi": "Fi"
        }
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=120 if c == "intervalo" else 80, anchor="center")
        self.tree.bind("<<TreeviewSelect>>", self._cargar_desde_tabla)

        self.btn_del = ttk.Button(self.frame_tabla, text="Eliminar selección", command=self._eliminar_seleccion)
        self.btn_csv = ttk.Button(self.frame_tabla, text="Exportar CSV", command=self._exportar_csv)

        # Acciones/Resultados
        self.frame_ops = ttk.LabelFrame(self, text="Cálculos y Visualización")
        self.btn_tabla = ttk.Button(self.frame_ops, text="Recalcular tabla", command=self._refrescar_tabla)
        self.btn_pos = ttk.Button(self.frame_ops, text="Medidas de posición", command=self._mostrar_posicion)
        self.btn_disp = ttk.Button(self.frame_ops, text="Medidas de dispersión", command=self._mostrar_dispersion)
        self.btn_plot = ttk.Button(self.frame_ops, text="Graficar (fi y ojiva)", command=self._graficar)
        if not HAS_MPL:
            self.btn_plot.configure(state="disabled")
            self.btn_plot.configure(text="Graficar (instala matplotlib)")

        self.txt_res = tk.Text(self.frame_ops, height=10, wrap="word")
        self.txt_res.configure(state="disabled")

    def _configurar_layout(self):
        pad = {"padx": 8, "pady": 6}

        # Entradas
        self.frame_in.grid(row=0, column=0, sticky="nsew", **pad)
        ttk.Label(self.frame_in, text="Mín:").grid(row=0, column=0, sticky="e")
        self.e_min.grid(row=0, column=1, sticky="w")
        ttk.Label(self.frame_in, text="Máx:").grid(row=1, column=0, sticky="e")
        self.e_max.grid(row=1, column=1, sticky="w")
        ttk.Label(self.frame_in, text="fi:").grid(row=2, column=0, sticky="e")
        self.e_fi.grid(row=2, column=1, sticky="w")
        self.btn_add.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.btn_clear.grid(row=4, column=0, columnspan=2, sticky="ew")

        # Tabla
        self.frame_tabla.grid(row=0, column=1, columnspan=2, sticky="nsew", **pad)
        self.tree.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.btn_del.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.btn_csv.grid(row=1, column=1, sticky="e", pady=(6, 0))

        # Resultados
        self.frame_ops.grid(row=1, column=0, columnspan=3, sticky="nsew", **pad)
        self.btn_tabla.grid(row=0, column=0, sticky="w")
        self.btn_pos.grid(row=0, column=1, sticky="w")
        self.btn_disp.grid(row=0, column=2, sticky="w")
        self.btn_plot.grid(row=0, column=3, sticky="w")
        self.txt_res.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(8,0))

        # Pesos de redimensionamiento
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.frame_tabla.grid_rowconfigure(0, weight=1)
        self.frame_tabla.grid_columnconfigure(0, weight=1)
        self.frame_ops.grid_rowconfigure(1, weight=1)
        self.frame_ops.grid_columnconfigure(3, weight=1)

    # ---- Operaciones ----
    def _leer_campos(self) -> Optional[Clase]:
        try:
            a = float(self.var_min.get().replace(",", "."))
            b = float(self.var_max.get().replace(",", "."))
            fi = int(self.var_fi.get())
        except ValueError:
            messagebox.showerror("Error", "Ingresa números válidos en Mín, Máx y fi.")
            return None
        if b <= a:
            messagebox.showerror("Error", "El máximo debe ser mayor que el mínimo.")
            return None
        if fi < 0:
            messagebox.showerror("Error", "fi debe ser ≥ 0.")
            return None
        return Clase(a, b, fi)

    def _agregar_clase(self):
        c = self._leer_campos()
        if not c:
            return
        # Si hay selección, actualiza esa fila; si no, agrega al final.
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            self.clases[idx] = c
        else:
            self.clases.append(c)
        self._refrescar_tabla()
        self._limpiar_campos()

    def _limpiar_campos(self):
        self.var_min.set("")
        self.var_max.set("")
        self.var_fi.set("")
        self.tree.selection_remove(*self.tree.selection())

    def _cargar_desde_tabla(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        c = self.clases[idx]
        self.var_min.set(str(c.minimo))
        self.var_max.set(str(c.maximo))
        self.var_fi.set(str(c.fi))

    def _eliminar_seleccion(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Selecciona una fila para eliminar.")
            return
        idx = self.tree.index(sel[0])
        del self.clases[idx]
        self._refrescar_tabla()
        self._limpiar_campos()

    def _refrescar_tabla(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        filas, n = construir_tabla(self.clases) if self.clases else ([], 0)
        for f in filas:
            self.tree.insert("", "end", values=(f["intervalo"], f["min"], f["max"], f["A"], f["fi"], f["Fi"]))
        # Fila TOTAL (visual)
        if n > 0:
            self.tree.insert("", "end", values=("TOTAL", "", "", "", n, n))

    def _mostrar_posicion(self):
        if not self.clases:
            messagebox.showinfo("Info", "Primero ingresa las clases.")
            return
        media = media_agrupada(self.clases)
        mediana = mediana_agrupada(self.clases)
        moda = moda_agrupada(self.clases)
        q1 = cuantil_agrupado(self.clases, 1, 4)
        q2 = cuantil_agrupado(self.clases, 2, 4)
        q3 = cuantil_agrupado(self.clases, 3, 4)
        texto = (
            "--- Medidas de posición ---\n"
            f"Media (x̄)  : {media:.6g}\n"
            f"Mediana (Q2): {mediana:.6g}\n"
            f"Moda        : {('%.6g' % moda) if moda is not None else 'N/A'}\n"
            f"Q1          : {q1:.6g}\n"
            f"Q2          : {q2:.6g}\n"
            f"Q3          : {q3:.6g}\n"
        )
        self._escribir_resultado(texto)

    def _mostrar_dispersion(self):
        if not self.clases:
            messagebox.showinfo("Info", "Primero ingresa las clases.")
            return
        d = dispersion_agrupada(self.clases)
        texto = (
            "--- Medidas de dispersión ---\n"
            f"Rango         : {d['rango']:.6g}\n"
            f"Varianza (s²) : {d['var']:.6g}\n"
            f"Desv. Est. (s): {d['sd']:.6g}\n"
            f"IQR (Q3-Q1)   : {d['IQR']:.6g}\n"
            f"CV (%)        : {d['CV%']:.6g}\n"
        )
        self._escribir_resultado(texto)

    def _escribir_resultado(self, texto: str):
        self.txt_res.configure(state="normal")
        self.txt_res.delete("1.0", "end")
        self.txt_res.insert("1.0", texto)
        self.txt_res.configure(state="disabled")

    def _exportar_csv(self):
        if not self.clases:
            messagebox.showinfo("Info", "No hay datos para exportar.")
            return
        filas, n = construir_tabla(self.clases)
        # Añadimos fila TOTAL
        filas.append({"intervalo": "TOTAL", "min": "", "max": "", "A": "", "fi": n, "Fi": n})
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Guardar tabla como CSV",
            initialfile="tabla_frecuencias.csv"
        )
        if not ruta:
            return
        with open(ruta, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Valores (Intervalo)", "Mín", "Máx", "A", "fi", "Fi"])
            for f in filas:
                w.writerow([f["intervalo"], f["min"], f["max"], f["A"], f["fi"], f["Fi"]])
        messagebox.showinfo("Éxito", f"CSV guardado en:\n{ruta}")

    def _graficar(self):
        if not HAS_MPL:
            messagebox.showinfo("Info", "Instala matplotlib para graficar:  python -m pip install matplotlib")
            return
        if not self.clases:
            messagebox.showinfo("Info", "Primero ingresa las clases.")
            return

        filas, _ = construir_tabla(self.clases)
        etiquetas = [f["intervalo"] for f in filas]
        fi = [f["fi"] for f in filas]
        Fi = [f["Fi"] for f in filas]

        # Barras de fi
        plt.figure()
        plt.bar(etiquetas, fi)
        plt.title("Frecuencia absoluta (fi)")
        plt.xlabel("Intervalo"); plt.ylabel("fi")
        plt.xticks(rotation=45, ha="right"); plt.tight_layout()

        # Ojiva Fi
        plt.figure()
        plt.plot(range(1, len(Fi)+1), Fi, marker="o")
        plt.title("Ojiva (Frecuencia acumulada Fi)")
        plt.xlabel("Clase"); plt.ylabel("Fi")
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    App().mainloop()
