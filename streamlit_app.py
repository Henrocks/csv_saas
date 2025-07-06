# =============================================================
# 📸 Image CSV Export Tool (Streamlit App)
# Zweck: Nutzer lädt Bilder (ZIP-Ordner oder Einzeldateien) hoch,
# und erhält eine CSV mit Itemcode, Farbcode und weiteren optionalen Tags.
# =============================================================

import streamlit as st
import zipfile
import os
import shutil
import tempfile
import pandas as pd
from pathlib import Path

# -------------------------------------------------------------
# 🔧 App Setup
# -------------------------------------------------------------
st.set_page_config(page_title="Image CSV Generator", layout="wide")
st.title("📸 CSV Generator for Structured Image Exports")

MODE = st.radio("Wähle Upload-Methode:", ["Ordnerstruktur (ZIP-Upload)", "Dateinamen (Einzel-Upload)"])

SEPARATOR_OPTIONS = ["-", "_", " ", "."]

# -------------------------------------------------------------
# 🔧 Hilfsfunktionen
# -------------------------------------------------------------
def extract_zip(zip_file):
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def get_all_image_paths(directory):
    valid_exts = ['.jpg', '.jpeg', '.png', '.webp']
    image_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in valid_exts:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, directory)
                image_paths.append((rel_path, full_path))
    return image_paths

# -------------------------------------------------------------
# 📂 Modus 1: Ordnerstruktur analysieren
# -------------------------------------------------------------
if MODE == "Ordnerstruktur (ZIP-Upload)":
    zip_file = st.file_uploader("Lade deine ZIP-Datei mit Bildern hoch:", type="zip")

    if zip_file:
        with st.spinner("Extrahiere ZIP und analysiere Struktur..."):
            base_dir = extract_zip(zip_file)
            image_paths = get_all_image_paths(base_dir)

            records = []
            for rel_path, full_path in image_paths:
                parts = Path(rel_path).parts
                records.append({
                    "Pfad": rel_path,
                    **{f"Ebene_{i+1}": parts[i] for i in range(len(parts) - 1)},
                    "Datei": parts[-1]
                })

            df = pd.DataFrame(records)

        st.subheader("🔧 Ordnerstruktur zuweisen")
        col_names = [col for col in df.columns if col.startswith("Ebene")]

        tag_names = []
        selected_tags = {}
        for col in col_names:
            tag = st.text_input(f"Benennung für {col} (leer lassen zum Ignorieren):", key=col)
            if tag.strip():
                selected_tags[col] = tag.strip()
                tag_names.append(f"{tag} ({col})")

        output_rows = []
        for _, row in df.iterrows():
            entry = {"Bildlink": row["Pfad"]}
            for col, label in selected_tags.items():
                entry[label] = row[col]
            output_rows.append(entry)

        export_df = pd.DataFrame(output_rows)
        if export_df.shape[0] > 0:
            export_df.insert(0, "Itemcode", export_df.iloc[:, 1] if len(export_df.columns) > 1 else "")
            export_df.insert(1, "Farbcode", export_df.iloc[:, 2] if len(export_df.columns) > 2 else "")

        st.dataframe(export_df)
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV herunterladen", data=csv_data, file_name="export_folders.csv", mime="text/csv")

        shutil.rmtree(base_dir)

# -------------------------------------------------------------
# 🖼️ Modus 2: Dateinamen analysieren
# -------------------------------------------------------------
elif MODE == "Dateinamen (Einzel-Upload)":
    uploaded_files = st.file_uploader("Lade deine Bilddateien hoch:", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True)

    if uploaded_files:
        separator = st.selectbox("Wähle primäres Trennzeichen im Dateinamen:", SEPARATOR_OPTIONS + ["Custom"])
        custom_sep = ""
        if separator == "Custom":
            custom_sep = st.text_input("Eigener Trenner (z. B. '__' oder '--'):")

        sep = custom_sep if separator == "Custom" else separator

        ignore_chars = st.text_input("Optional: Weitere Zeichen oder Kombinationen zum Entfernen (z. B. '-thumb', '__v2'):")
        ignore_list = [s.strip() for s in ignore_chars.split(',')] if ignore_chars else []

        preview_names = [file.name for file in uploaded_files[:5]]
        st.write("Beispiel Dateinamen:", preview_names)

        part_mapping = ["Ignorieren", "Itemcode", "Farbcode", "Eigener Tag"]

        example_name = uploaded_files[0].name
        for ignore in ignore_list:
            example_name = example_name.replace(ignore, "")
        example_split = example_name.split(sep)

        st.write(f"Dateiname aufgeteilt in {len(example_split)} Teile:", example_split)

        st.subheader("🔧 Teile zuweisen")
        assignments = []
        for i, part in enumerate(example_split):
            assign = st.selectbox(f"Teil {i+1} ('{part}') ist:", part_mapping, key=f"part_{i}")
            assignments.append(assign)

        rows = []
        for file in uploaded_files:
            cleaned_name = file.name
            for ignore in ignore_list:
                cleaned_name = cleaned_name.replace(ignore, "")
            parts = cleaned_name.split(sep)

            mapped = {"Itemcode": "", "Farbcode": "", "Eigener Tag": ""}
            for i, label in enumerate(assignments):
                if i < len(parts) and label != "Ignorieren":
                    if label == "Eigener Tag":
                        mapped[label] += parts[i] + " "
                    else:
                        mapped[label] = parts[i]
            mapped['Bildlink'] = file.name
            rows.append(mapped)

        df = pd.DataFrame(rows)
        df['Eigener Tag'] = df['Eigener Tag'].str.strip()

        st.dataframe(df)
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV herunterladen", data=csv_data, file_name="export_filenames.csv", mime="text/csv")
