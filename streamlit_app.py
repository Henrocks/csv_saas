import streamlit as st
import zipfile
import os
import shutil
import tempfile
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Image CSV Generator", layout="wide")
st.title("📸 CSV Generator for Structured Image Exports")

MODE = st.radio("Wähle Upload-Methode:", ["Ordnerstruktur (ZIP-Upload)", "Dateinamen (Einzel-Upload)"])

SEPARATOR_OPTIONS = ["-", "_", " ", "."]

# --- COMMON UTILITIES ---
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

# --- MODE 1: FOLDER STRUCTURE ---
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
        col_names = df.columns.tolist()
        item_col = st.selectbox("Itemcode-Ebene:", col_names)
        color_col = st.selectbox("Farbcode-Ebene:", col_names)

        df['Itemcode'] = df[item_col]
        df['Farbcode'] = df[color_col]
        df['Bildlink'] = df['Pfad']  # Platzhalter

        final_df = df[['Itemcode', 'Farbcode', 'Bildlink']]
        st.dataframe(final_df)

        csv_data = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV herunterladen", data=csv_data, file_name="export_folders.csv", mime="text/csv")

        shutil.rmtree(base_dir)

# --- MODE 2: FILENAME PARSING ---
elif MODE == "Dateinamen (Einzel-Upload)":
    uploaded_files = st.file_uploader("Lade deine Bilddateien hoch:", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True)

    if uploaded_files:
        separator = st.selectbox("Wähle Trennzeichen im Dateinamen:", SEPARATOR_OPTIONS + ["Custom"])
        custom_sep = ""
        if separator == "Custom":
            custom_sep = st.text_input("Eigener Trenner (z. B. '__' oder '--'):")

        sep = custom_sep if separator == "Custom" else separator

        preview_names = [file.name for file in uploaded_files[:5]]
        st.write("Beispiel Dateinamen:", preview_names)

        part_mapping = ["Ignorieren", "Itemcode", "Farbcode", "Eigener Tag"]

        example_split = uploaded_files[0].name.split(sep)
        st.write(f"Dateiname aufgeteilt in {len(example_split)} Teile:", example_split)

        st.subheader("🔧 Teile zuweisen")
        assignments = []
        for i, part in enumerate(example_split):
            assign = st.selectbox(f"Teil {i+1} ('{part}') ist:", part_mapping, key=f"part_{i}")
            assignments.append(assign)

        rows = []
        for file in uploaded_files:
            parts = file.name.split(sep)
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
