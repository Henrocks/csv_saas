import streamlit as st
import zipfile
import os
import shutil
import tempfile
import pandas as pd
from pathlib import Path

# === PAGE CONFIG ===
st.set_page_config(page_title="Image CSV Generator", layout="wide")
st.title("📸 CSV Generator for Structured Image Exports")

# === UI SETUP ===
MODE = st.radio("Wähle Upload-Methode:", ["Ordnerstruktur (ZIP-Upload)", "Dateinamen (Einzel-Upload)"])
SEPARATOR_OPTIONS = ["-", "_", " ", "."]

# === UTILITIES ===
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

# === FOLDER STRUCTURE MODE ===
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
                    **{f"Ebene {i+1}": parts[i] for i in range(len(parts) - 1)},
                    "Datei": parts[-1]
                })

            df = pd.DataFrame(records)

        st.subheader("🔧 Ordnerstruktur zuweisen")
        col_names = [col for col in df.columns if col.startswith("Ebene")]
        export_df = df.copy()

        for col in col_names:
            example_value = df[col].iloc[0] if not df[col].isna().all() else "(leer)"
            with st.expander(f"{col} (z. B. '{example_value}')"):
                role = st.selectbox(f"Was ist '{example_value}'?", ["Ignorieren", "Itemcode", "Farbcode", "Custom"], key=f"role_{col}")
                if role == "Itemcode":
                    export_df.insert(0, "Itemcode", df[col])
                elif role == "Farbcode":
                    export_df.insert(1, "Farbcode", df[col])
                elif role == "Custom":
                    custom_label = st.text_input(f"Eigene Bezeichnung für {col}:", key=f"label_{col}")
                    export_df[custom_label] = df[col]

        export_df["Bildlink"] = df["Pfad"]

        final_cols = [col for col in export_df.columns if col not in df.columns or col == "Bildlink"]
        final_df = export_df[final_cols]
        st.dataframe(final_df)

        csv_data = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV herunterladen", data=csv_data, file_name="export_folders.csv", mime="text/csv")

        shutil.rmtree(base_dir)

# === FILENAME MODE ===
elif MODE == "Dateinamen (Einzel-Upload)":
    uploaded_files = st.file_uploader("Lade deine Bilddateien hoch:", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True)

    if uploaded_files:
        separator = st.selectbox("Wähle Haupt-Trennzeichen im Dateinamen:", SEPARATOR_OPTIONS + ["Custom"])
        custom_sep = ""
        if separator == "Custom":
            custom_sep = st.text_input("Eigener Trenner (z. B. '__' oder '--'):")

        sep = custom_sep if separator == "Custom" else separator

        additional_separators = st.text_input("Weitere Trennzeichen (kommagetrennt):", value="")
        all_seps = [sep] + [s.strip() for s in additional_separators.split(",") if s.strip()]

        remove_parts = st.text_input("Entferne Teile aus Dateinamen (kommagetrennt):", value="")
        remove_keywords = [x.strip() for x in remove_parts.split(",") if x.strip()]

        preview_names = [file.name for file in uploaded_files[:5]]
        st.write("Beispiel Dateinamen:", preview_names)

        # Aufteilen eines Beispielnamens mit allen Trennern
        example_name = uploaded_files[0].name
        for keyword in remove_keywords:
            example_name = example_name.replace(keyword, "")
        for sp in all_seps:
            example_name = example_name.replace(sp, "|")
        example_split = example_name.split("|")

        st.subheader("🔧 Teile zuweisen")
        part_mapping = ["Ignorieren", "Itemcode", "Farbcode", "Eigener Tag"]
        assignments = []
        for i, part in enumerate(example_split):
            assign = st.selectbox(f"Teil {i+1} ('{part}') ist:", part_mapping, key=f"part_{i}")
            assignments.append(assign)

        rows = []
        for file in uploaded_files:
            filename = file.name
            for keyword in remove_keywords:
                filename = filename.replace(keyword, "")
            for sp in all_seps:
                filename = filename.replace(sp, "|")
            parts = filename.split("|")
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
