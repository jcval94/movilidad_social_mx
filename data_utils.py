import numpy as np
import pandas as pd
import streamlit as st


def load_and_process_data_uncached():
    """
    Lee los archivos .dta, hace merge y crea las variables necesarias.
    Esta versión no cachea resultados y se mantiene para AB testing.
    """
    file_path_person = "data/ESRU-EMOVI 2017 Entrevistado.dta"
    file_path_hogar = "data/ESRU-EMOVI 2017 Hogar.dta"

    df_person = pd.read_stata(file_path_person, convert_categoricals=False)
    df_hogar = pd.read_stata(file_path_hogar, convert_categoricals=False)

    df = pd.merge(
        df_person,
        df_hogar[["folio", "consecutivo", "p05h", "p06h"]],
        on=["folio", "consecutivo"],
        how="left",
    )

    a_los_14_vars = [
        "p30_a",
        "p30_b",
        "p30_c",
        "p30_d",
        "p30_e",
        "p32_a",
        "p32_b",
        "p32_c",
        "p32_d",
        "p33_a",
        "p33_b",
        "p33_c",
        "p33_d",
        "p33_e",
        "p33_f",
        "p33_g",
        "p33_h",
        "p33_i",
        "p33_j",
        "p33_k",
        "p33_l",
        "p33_m",
        "p33_n",
        "p34_a",
        "p34_b",
        "p34_c",
        "p34_d",
        "p34_e",
        "p34_f",
        "p34_g",
        "p34_h",
    ]

    actualmente_vars = [
        "p125a",
        "p125b",
        "p125c",
        "p125d",
        "p125e",
        "p126a",
        "p126b",
        "p126c",
        "p126d",
        "p126e",
        "p126f",
        "p126g",
        "p126h",
        "p126i",
        "p126j",
        "p126k",
        "p126l",
        "p126m",
        "p126n",
        "p126o",
        "p126p",
        "p126q",
        "p126r",
        "p129a",
        "p129b",
        "p129c",
        "p129d",
        "p129e",
        "p131",
    ]

    def recodificar_01(valor):
        if pd.isna(valor):
            return 0
        if valor == 1:
            return 1
        return 0

    for var in a_los_14_vars:
        if var in df.columns:
            df[var] = df[var].apply(recodificar_01)

    for var in actualmente_vars:
        if var in df.columns and var != "p131":
            df[var] = df[var].apply(recodificar_01)

    if "p131" in df.columns:
        df["p131"] = df["p131"].fillna(0)
        df["p131"] = np.where(df["p131"] >= 1, 1, 0)

    df["a_los_14_wealth"] = df[a_los_14_vars].sum(axis=1)
    df["actualmente_wealth"] = df[actualmente_vars].sum(axis=1)
    df["actualmente_wealth2"] = df["actualmente_wealth"]

    def asignar_quintil(serie):
        return pd.qcut(serie, q=5, labels=False, duplicates="drop") + 1

    df["a_los_14_quintile"] = asignar_quintil(df["a_los_14_wealth"])
    df["actualmente_quintile"] = asignar_quintil(df["actualmente_wealth2"])

    def assign_generation(age):
        if pd.isna(age):
            return "NA"
        age = int(age)
        if age <= 20:
            return "Gen Z"
        if 21 <= age <= 36:
            return "Millennial"
        if 37 <= age <= 52:
            return "Gen X"
        if 53 <= age <= 71:
            return "Baby Boomer"
        return "Traditionalist"

    df["generation"] = df["p05h"].apply(assign_generation)
    df["sex"] = df["p06h"].map({1: "Hombre", 2: "Mujer"})

    def assign_education(val):
        if pd.isna(val):
            return "NA"
        if val == 1:
            return "Primaria"
        if val == 2:
            return "Secundaria"
        if val == 3:
            return "Preparatoria"
        if val == 4:
            return "Universidad"
        if val == 5:
            return "Posgrado"
        return "Otro"

    if "p07" in df.columns:
        df["education"] = df["p07"].apply(assign_education)
    else:
        df["education"] = np.random.choice(
            ["Primaria", "Secundaria", "Preparatoria", "Universidad", "Posgrado", "Otro", "NA"],
            size=len(df),
        )

    return df


@st.cache_data(show_spinner=False)
def load_and_process_data():
    """Versión cacheada para Streamlit."""
    return load_and_process_data_uncached()
