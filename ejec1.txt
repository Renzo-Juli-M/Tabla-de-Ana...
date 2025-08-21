# -*- coding: utf-8 -*-
"""
Interfaz gráfica (Tkinter) para tablas de frecuencias de datos agrupados.
Incluye:
- Tabla con: Intervalo, Amplitud A, fi, hi, Fi, Hi
- Medidas de posición (media, mediana, moda, Q1-Q3)
- Medidas de dispersión (rango, var, sd, IQR, CV)
- Cálculo general de Cuartiles Qk, Deciles Dk y Percentiles Pk
- Exportación a CSV
- Gráficas (fi y ojiva Fi) si hay matplotlib

Autor: tú + ChatGPT
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# --- Gráficos (opcional) ---
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
    """Devuelve filas con fi, hi, Fi, Hi."""
    filas = []
    n = sum(c.fi for c in clases)
    if n == 0:
        return filas, 0
    Fi = 0
    Hi = 0.0
    for i, c in enumerate(clases):
        Fi += c.fi
        hi = c.fi / n
        Hi += hi
        etiqueta = f"[ {c.minimo:g} , {c.maximo:g} " + ("]" if i == len(clases)-1 else "[")
        filas.append({
            "intervalo": etiqueta,
            "min": c.minimo,
            "max": c.maximo,
            "A": c.amplitud,
            "fi": c.fi,
            "hi": hi,
            "Fi": Fi,
            "Hi": Hi
        })
    return filas, n


def media_agrupada(clases: List[Clase]) -> float:
    n = sum(c.fi for c in clases)
    if n == 0:
        return float("nan")
    return sum(c.marca * c.fi for c in clases) / n


def buscar_clase_por_posicion(clases: List[Clase], posicion: float) -> Tuple[int, int]:
    """Retorna (índice, Fi_prev) para una posición acumulada."""
    Fi = 0
    for i, c in enumerate(clases):
        previo = Fi
        Fi += c.fi
        if posicion <= Fi:
            return i, previo
    return len(clases)-1, Fi - clases[-1].fi


def cuantil_agrupado(clases: List[Clase], k: int, m: int) -> float:
    """
    Cuantil general (k de m): 
    L_i + ((k*N/m - F_{i-1}) / f_i) * A
    - Cuartil: m=4 (k=1..3)
    - Decil : m=10 (k=1..9)
    - Percentil: m=100 (k=1..99)
    """
    n = sum(c.fi for c in clases)
    if n == 0:
        return float("nan")
    if not (1 <= k < m):
        return float("nan")
    pos = k * n / m
    i, Fi_1 = buscar_clase_por_posicion(clases, pos)
    c = clases[i]
    return c.minimo + ((pos - Fi_1) / c.fi) * c.amplitud


def mediana_agrupada(clases: List[Clase]) -> float:
    return cuantil_agrupado(clases, 2, 4)  # Q2


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
        self.title("Sistema de Frecuencias · Sprint 1")
        self.geometry("1060x640")
        self.minsize(960, 560)

        # Estilo "bonito"
        self._setup_style()

        self.clases: List[Clase] = []

        self._crear_widgets()
        self._configurar_layout()
        self._refrescar_tabla()

    # ---- Estética ----
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # usar el que haya

        base_bg = "#f6f7fb"
        accent = "#3b82f6"   # azul
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TLabel", background=base_bg)
        style.configure("TFrame", background=base_bg)
        style.configure("TLabelframe", background=base_bg, padding=10)
        style.configure("TLabelframe.Label", font=("Segoe UI Semibold", 11))
        style.configure("TButton", padding=6)
        style.map("TButton",
                  foreground=[("active", "white")],
                  background=[("active", accent)])
        self.configure(bg=base_bg)

    # ---- UI ----
    def _crear_widgets(self):
        # Panel de entrada
        self.frame_in = ttk.LabelFrame(self, text="Ingresar clase")
        self.var_min = tk.StringVar()
        self.var_max = tk.StringVar()
        self.var_fi  = tk.StringVar()

        self.e_min = ttk.Entry(self.frame_in, width=14, textvariable=self.var_min)
        self.e_max = ttk.Entry(self.frame_in, width=14, textvariable=self.var_max)
        self.e_fi  = ttk.Entry(self.frame_in, width=14, textvariable=self.var_fi)

        self.btn_add = ttk.Button(self.frame_in, text="Agregar / Actualizar", command=self._agregar_clase)
        self.btn_clear = ttk.Button(self.frame_in, text="Limpiar", command=self._limpiar_campos)

        # Tabla
        self.frame_tabla = ttk.LabelFrame(self, text="Tabla de frecuencias")
        cols = ("intervalo", "min", "max", "A", "fi", "hi", "Fi", "Hi")
        self.tree = ttk.Treeview(self.frame_tabla, columns=cols, show="headings", height=12)
        headings = {
            "intervalo": "Valores (Intervalo)",
            "min": "Mín",
            "max": "Máx",
            "A": "A",
            "fi": "fi",
            "hi": "hi",
            "Fi": "Fi",
            "Hi": "Hi"
        }
        for c in cols:
            self.tree.heading(c, text=headings[c])
            w = 160 if c == "intervalo" else 90
            self.tree.column(c, width=w, anchor="center")
        self.tree.bind("<<TreeviewSelect>>", self._cargar_desde_tabla)

        self.btn_del = ttk.Button(self.frame_tabla, text="Eliminar fila", command=self._eliminar_seleccion)
        self.btn_csv = ttk.Button(self.frame_tabla, text="Exportar CSV", command=self._exportar_csv)

        # Cálculos / Visual
        self.frame_ops = ttk.LabelFrame(self, text="Cálculos y visualización")
        self.btn_tabla = ttk.Button(self.frame_ops, text="Recalcular tabla", command=self._refrescar_tabla)
        self.btn_pos = ttk.Button(self.frame_ops, text="Medidas de posición", command=self._mostrar_posicion)
        self.btn_disp = ttk.Button(self.frame_ops, text="Medidas de dispersión", command=self._mostrar_dispersion)

        self.btn_plot = ttk.Button(self.frame_ops, text=("Graficar (fi y ojiva)" if HAS_MPL else "Graficar (instala matplotlib)"),
                                   command=self._graficar)
        if not HAS_MPL:
            self.btn_plot.state(["disabled"])

        # Cuantiles generales
        self.frame_q = ttk.LabelFrame(self, text="Cuantiles (Qk, Dk, Pk)")
        self.tipo_q = tk.StringVar(value="Cuartil (Qk)")
        self.k_q = tk.IntVar(value=1)
        self.cmb_tipo = ttk.Combobox(self.frame_q, width=18, state="readonly",
                                     values=["Cuartil (Qk)", "Decil (Dk)", "Percentil (Pk)"],
                                     textvariable=self.tipo_q)
        self.cmb_tipo.bind("<<ComboboxSelected>>", self._ajustar_rango_k)
        self.sp_k = tk.Spinbox(self.frame_q, from_=1, to=3, width=6, textvariable=self.k_q, justify="center")
        self.btn_calc_q = ttk.Button(self.frame_q, text="Calcular", command=self._calcular_cuantil)
        self.lbl_q_res = ttk.Label(self.frame_q, text="Resultado: —", font=("Segoe UI", 10, "bold"))

        # Resultados de texto
        self.frame_res = ttk.LabelFrame(self, text="Resultados")
        self.txt_res = tk.Text(self.frame_res, height=10, wrap="word", relief="flat",
                               font=("Consolas", 10))
        self.txt_res.configure(background="#ffffff", borderwidth=1)
        self.scroll = ttk.Scrollbar(self.frame_res, command=self.txt_res.yview)
        self.txt_res.configure(yscrollcommand=self.scroll.set)

    def _configurar_layout(self):
        pad = {"padx": 10, "pady": 8}

        # Entradas
        self.frame_in.grid(row=0, column=0, sticky="nsew", **pad)
        ttk.Label(self.frame_in, text="Mín:").grid(row=0, column=0, sticky="e", padx=(0,6))
        self.e_min.grid(row=0, column=1, sticky="w")
        ttk.Label(self.frame_in, text="Máx:").grid(row=1, column=0, sticky="e", padx=(0,6))
        self.e_max.grid(row=1, column=1, sticky="w")
        ttk.Label(self.frame_in, text="fi (frecuencia absoluta):").grid(row=2, column=0, sticky="e", padx=(0,6))
        self.e_fi.grid(row=2, column=1, sticky="w")
        self.btn_add.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.btn_clear.grid(row=4, column=0, columnspan=2, sticky="ew")

        # Tabla
        self.frame_tabla.grid(row=0, column=1, columnspan=2, sticky="nsew", **pad)
        self.tree.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.btn_del.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.btn_csv.grid(row=1, column=1, sticky="e", pady=(6, 0))
        self.frame_tabla.grid_rowconfigure(0, weight=1)
        self.frame_tabla.grid_columnconfigure(0, weight=1)

        # Cuantiles
        self.frame_q.grid(row=1, column=0, sticky="nsew", **pad)
        ttk.Label(self.frame_q, text="Tipo:").grid(row=0, column=0, sticky="e")
        self.cmb_tipo.grid(row=0, column=1, sticky="w")
        ttk.Label(self.frame_q, text="k:").grid(row=1, column=0, sticky="e")
        self.sp_k.grid(row=1, column=1, sticky="w")
        self.btn_calc_q.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8,0))
        self.lbl_q_res.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6,0))

        # Botones de cálculos y gráficos
        self.frame_ops.grid(row=1, column=1, sticky="nsew", **pad)
        self.btn_tabla.grid(row=0, column=0, sticky="w")
        self.btn_pos.grid(row=0, column=1, sticky="w", padx=(6,0))
        self.btn_disp.grid(row=0, column=2, sticky="w", padx=(6,0))
        self.btn_plot.grid(row=0, column=3, sticky="w", padx=(6,0))

        # Resultados
        self.frame_res.grid(row=1, column=2, sticky="nsew", **pad)
        self.txt_res.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")
        self.frame_res.grid_rowconfigure(0, weight=1)
        self.frame_res.grid_columnconfigure(0, weight=1)

        # Pesos generales
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=2)
        self.grid_rowconfigure(1, weight=3)

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
            self.tree.insert("", "end", values=(
                f["intervalo"], _fmt(f["min"]), _fmt(f["max"]), _fmt(f["A"]),
                f["fi"], _fmt(f["hi"], 4), f["Fi"], _fmt(f["Hi"], 4)
            ))
        if n > 0:
            self.tree.insert("", "end", values=("TOTAL", "", "", "", n, _fmt(1.0, 4), n, _fmt(1.0, 4)))

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
            f"Media (x̄)  : {_fmt(media)}\n"
            f"Mediana (Q2): {_fmt(mediana)}\n"
            f"Moda        : {_fmt(moda) if moda is not None else 'N/A'}\n"
            f"Q1          : {_fmt(q1)}\n"
            f"Q2          : {_fmt(q2)}\n"
            f"Q3          : {_fmt(q3)}\n"
        )
        self._escribir_resultado(texto)

    def _mostrar_dispersion(self):
        if not self.clases:
            messagebox.showinfo("Info", "Primero ingresa las clases.")
            return
        d = dispersion_agrupada(self.clases)
        texto = (
            "--- Medidas de dispersión ---\n"
            f"Rango         : {_fmt(d['rango'])}\n"
            f"Varianza (s²) : {_fmt(d['var'])}\n"
            f"Desv. Est. (s): {_fmt(d['sd'])}\n"
            f"IQR (Q3-Q1)   : {_fmt(d['IQR'])}\n"
            f"CV (%)        : {_fmt(d['CV%'])}\n"
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
        filas.append({"intervalo": "TOTAL", "min": "", "max": "", "A": "", "fi": n, "hi": 1.0, "Fi": n, "Hi": 1.0})
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
            w.writerow(["Valores (Intervalo)", "Mín", "Máx", "A", "fi", "hi", "Fi", "Hi"])
            for f in filas:
                w.writerow([f["intervalo"], f["min"], f["max"], f["A"], f["fi"], f["hi"], f["Fi"], f["Hi"]])
        messagebox.showinfo("Éxito", f"CSV guardado en:\n{ruta}")

    def _graficar(self):
        if not HAS_MPL:
            messagebox.showinfo("Info", "Instala matplotlib:  python -m pip install matplotlib")
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

    # ---- Cuantiles (Qk, Dk, Pk) ----
    def _ajustar_rango_k(self, _evt=None):
        tipo = self.tipo_q.get()
        if tipo.startswith("Cuartil"):
            self.sp_k.config(from_=1, to=3)
            if self.k_q.get() > 3: self.k_q.set(1)
        elif tipo.startswith("Decil"):
            self.sp_k.config(from_=1, to=9)
            if self.k_q.get() > 9: self.k_q.set(1)
        else:
            self.sp_k.config(from_=1, to=99)
            if self.k_q.get() > 99: self.k_q.set(1)

    def _calcular_cuantil(self):
        if not self.clases:
            messagebox.showinfo("Info", "Primero ingresa las clases.")
            return
        k = self.k_q.get()
        tipo = self.tipo_q.get()
        if tipo.startswith("Cuartil"):
            m, etiqueta = 4, "Q"
        elif tipo.startswith("Decil"):
            m, etiqueta = 10, "D"
        else:
            m, etiqueta = 100, "P"

        valor = cuantil_agrupado(self.clases, k, m)
        if math.isnan(valor):
            self.lbl_q_res.config(text="Resultado: —")
        else:
            self.lbl_q_res.config(text=f"Resultado: {etiqueta}{k} = {_fmt(valor)}")

# ---- util formateo ----
def _fmt(x, dec=6):
    try:
        return f"{float(x):.{dec}g}"
    except Exception:
        return str(x)


if __name__ == "__main__":
    App().mainloop()
