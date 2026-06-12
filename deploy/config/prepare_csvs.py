"""
Preprocesado de los CSVs antes del mapping RML.
Ejecutar desde la raíz del proyecto: python scripts/prepare_csvs.py

Qué hace:
1. CSV extras (10 PDIs): renombra X→lon, Y→lat, genera ID limpio, normaliza texto
2. CSV playas bandera azul: normaliza y añade ID limpio
3. Detecta y guarda lista de playas duplicadas entre ambas fuentes
"""

import pandas as pd
import unicodedata
import re
import os
from pathlib import Path

DATA_DIR = Path("data")
OUT_DIR  = Path("data/clean")
OUT_DIR.mkdir(exist_ok=True)

# ── Archivos de PDIs extra ────────────────────────────────────────────────────
PDI_FILES = {
    "Castillos, antiguos emplazamientos, pazos, palacios, casas señoriales y zonas militares.csv": "castillos",
    "Fervenzas, ríos, lagos, embalses.csv":                                                         "fervenzas",
    "Iglesias, santuarios, ermitas y capillas.csv":                                                 "iglesias",
    "Molinos, hórreos, cruceiros, petos, construcciones tradicionales, aldeas abandonadas.csv":     "construccion_tradicional",
    "Monasterios y conventos.csv":                                                                   "monasterios",
    "Montañas, miradores, cabos, espacios naturales, sendas y parques.csv":                         "espacios_naturales",
    "OTROS.csv":                                                                                     "otros",
    "Playas de mar y fluviales.csv":                                                                 "playas_genericas",
    "Puentes, pontellas, pasos, poldras.csv":                                                        "puentes",
    "Yacimientos arqueológicos.csv":                                                                 "yacimientos",
}

PLAYAS_AZUL_FILE = "PraiasBandeiraAzul-2025-csv.csv"


def slugify(text: str) -> str:
    """Convierte un texto en un slug seguro para URIs."""
    if not isinstance(text, str):
        text = str(text)
    # Normalizar unicode (quitar acentos)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Minúsculas, espacios y caracteres especiales → guión
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def normalize_text(series: pd.Series) -> pd.Series:
    """Trim + Title Case para nombres de lugares."""
    return series.astype(str).str.strip().str.title()


def process_pdi_csv(filepath: Path, tipo_slug: str) -> pd.DataFrame:
    """
    Procesa un CSV de PDI extra.

    Cambios:
    - Renombra X → lon_original, Y → lat_original (clarifica la confusión GIS)
    - Añade lat y lon como columnas explícitas (Y=lat, X=lon en sistema GIS)
    - Genera id_uri: slug único para construir URIs limpias
    - Normaliza Name, concello, provincia
    - Añade columna tipo_slug para trazabilidad
    """
    df = pd.read_csv(filepath, sep=",", encoding="utf-8-sig")

    # Renombrar para claridad (en GIS: X=longitud, Y=latitud)
    df = df.rename(columns={"X": "lon_gis", "Y": "lat_gis"})

    # Coordenadas correctas
    df["lat"] = pd.to_numeric(df["lat_gis"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon_gis"], errors="coerce")

    # Validar rango Galicia (bounding box aproximado)
    galicia_mask = (
        df["lat"].between(41.8, 44.0) &
        df["lon"].between(-9.5, -6.7)
    )
    n_out = (~galicia_mask & df["lat"].notna()).sum()
    if n_out > 0:
        print(f"  ⚠️  {n_out} filas fuera del bounding box de Galicia en {filepath.name}")
    df = df[galicia_mask | df["lat"].isna()].copy()

    # Normalizar textos
    df["Name"]     = normalize_text(df["Name"])
    df["concello"] = normalize_text(df["concello"])
    df["provincia"] = normalize_text(df["provincia"])
    if "LUGAR_E_PARROQUIA" in df.columns:
        df["LUGAR_E_PARROQUIA"] = normalize_text(df["LUGAR_E_PARROQUIA"])

    # Generar ID limpio para URI — tipo + nombre + coordenadas truncadas
    # Usar coordenadas para garantizar unicidad si hay nombres duplicados
    df["id_uri"] = df.apply(
        lambda r: f"{tipo_slug}-{slugify(r['Name'])}-{round(r['lat'], 4)}-{round(r['lon'], 4)}"
        if pd.notna(r["lat"]) else f"{tipo_slug}-{slugify(r['Name'])}",
        axis=1
    )

    df["tipo_slug"] = tipo_slug

    # Reordenar columnas útiles al principio
    cols_front = ["id_uri", "Name", "lat", "lon", "concello", "provincia"]
    if "LUGAR_E_PARROQUIA" in df.columns:
        cols_front.append("LUGAR_E_PARROQUIA")
    cols_rest = [c for c in df.columns if c not in cols_front]
    df = df[cols_front + cols_rest]

    return df


def process_playas_azul(filepath: Path) -> pd.DataFrame:
    """
    Procesa el CSV de playas bandera azul.
    - Genera id_uri limpio
    - Normaliza nombres
    - Asegura que Coordenada_X = latitud, Coordenada_Y = longitud
    """
    df = pd.read_csv(filepath, sep=",", encoding="utf-8-sig")

    # En este CSV: Coordenada_X=latitud, Coordenada_Y=longitud (ya correcto)
    df["lat"] = pd.to_numeric(df["Coordenada_X"], errors="coerce")
    df["lon"] = pd.to_numeric(df["Coordenada_Y"], errors="coerce")

    df["PRAIA"]    = normalize_text(df["PRAIA"])
    df["CONCELLO"] = normalize_text(df["CONCELLO"])
    df["PROVINCIA"] = normalize_text(df["PROVINCIA"])

    df["id_uri"] = df.apply(
        lambda r: f"praia-azul-{slugify(r['PRAIA'])}-{r['CODIGO_CONCELLO']}",
        axis=1
    )

    return df


def detect_duplicates(df_azul: pd.DataFrame, df_genericas: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta playas que aparecen en ambas fuentes (por nombre normalizado).
    Guarda la lista para poder excluirlas del mapping genérico.
    """
    nombres_azul = set(df_azul["PRAIA"].str.lower().str.strip())
    nombres_gen  = df_genericas["Name"].str.lower().str.strip()
    duplicadas = df_genericas[nombres_gen.isin(nombres_azul)][["Name", "lat", "lon", "concello"]]
    return duplicadas


# ── Ejecutar ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔄 Procesando CSVs...\n")

    # 1. Playas bandera azul
    azul_path = DATA_DIR / PLAYAS_AZUL_FILE
    if azul_path.exists():
        df_azul = process_playas_azul(azul_path)
        out = OUT_DIR / "clean_praias_bandera_azul.csv"
        df_azul.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"✅ Playas bandera azul: {len(df_azul)} filas → {out}")
    else:
        print(f"❌ No encontrado: {azul_path}")
        df_azul = pd.DataFrame()

    # 2. CSVs de PDIs extra
    df_genericas = None
    for filename, tipo_slug in PDI_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            print(f"⚠️  No encontrado: {path}")
            continue
        df = process_pdi_csv(path, tipo_slug)
        out = OUT_DIR / f"clean_{tipo_slug}.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"✅ {tipo_slug}: {len(df)} filas → {out}")
        if tipo_slug == "playas_genericas":
            df_genericas = df

    # 3. Detectar duplicados playas
    if df_azul is not None and df_genericas is not None and len(df_azul) > 0:
        duplicadas = detect_duplicates(df_azul, df_genericas)
        out_dup = OUT_DIR / "playas_duplicadas.csv"
        duplicadas.to_csv(out_dup, index=False, encoding="utf-8-sig")
        print(f"\n📋 Playas duplicadas entre fuentes: {len(duplicadas)} → {out_dup}")
        print("   (Estas aparecen en bandera azul Y en el CSV genérico)")

    print("\n✨ Listo. Usa los CSV de data/clean/ en tus mappings.")
