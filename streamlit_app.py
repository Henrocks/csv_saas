import streamlit as st
import zipfile
import os
import tempfile
import shutil
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Image Folder to CSV Mapper", layout="wide")
st.title("📦 Bildstruktur zu CSV-Export")

st.markdown("""
Willkommen! Du kannst entweder:
- Eine **ZIP-Datei mit Ordnerstruktur** hochladen (z. B. Produkt > Farbe > Bilder)
- Oder **einzelne Bilddateien mit bestimmten Dateinamen** (z. B. `CSF440-119.jpg`) hochladen

Danach kannst du selbst festlegen, was im Pfad oder Dateinamen was bedeutet.
""")

# --- Auswahl der Upload-Methode ---
mode = st.radio("Wie möchtest du deine Bilder hochladen?", ["Ordnerstruktur als ZIP", "Einzeldateien mit Dateinamenslogik"])

# --- Gemeinsame CSV-Exportfunktion ---
def export_csv(data, filename="export.csv"):
    df = pd.DataFrame(data)
    csv_path = os.path.join(tempfile.gettempdir(), filename)
    df.to_csv(csv_path, index=False)
    st.success("✅ CSV erfolgreich erstellt!")
    with open(csv_path, "rb") as f:
        st.download_button("📥 CSV herunterladen", f, file_name=filename)

# --- 1. ZIP-Modus ---
if mode == "Ordnerstruktur als ZIP":
    zip_file = st.file_uploader("ZIP-Datei hochladen", type="zip")

    if zip_file:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "upload.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_file.read())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            base_folder = Path(tmpdir)
            image_data = []

            st.subheader("📂 Gefundene Pfade & Definition")

            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(base_folder)
                        parts = rel_path.parts

                        if len(parts) < 3:
                            continue  # Nicht tief genug

                        product = parts[-3]
                        color = parts[-2]
                        filename = parts[-1]

                        public_url = f"https://example.com/{rel_path.as_posix()}"

                        image_data.append({
                            "Item Code": product,
                            "Color Code": color,
                            "Image File": filename,
                            "Public URL": public_url
                        })

            if image_data:
                export_csv(image_data, filename="zip_folder_export.csv")
            else:
                st.warning("Keine geeigneten Bildpfade gefunden.")

# --- 2. Dateinamen-Modus ---
elif mode == "Einzeldateien mit Dateinamenslogik":
    uploaded_files = st.file_uploader("Bilddateien hochladen", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

    trenner = st.selectbox("Wie ist der Dateiname getrennt?", ["-", "_", " ", "."])
    reihenfolge = st.radio("Was kommt zuerst im Dateinamen?", ["Item Code zuerst", "Color Code zuerst"])

    if uploaded_files:
        image_data = []
        for file in uploaded_files:
            filename = Path(file.name).stem
            parts = filename.split(trenner)

            if len(parts) < 2:
                continue

            item, color = (parts[0], parts[1]) if reihenfolge == "Item Code zuerst" else (parts[1], parts[0])

            temp_path = os.path.join(tempfile.gettempdir(), file.name)
            with open(temp_path, "wb") as f:
                f.write(file.read())

            # In echtem Tool hier: Hochladen oder Link erzeugen
            fake_url = f"https://example.com/uploads/{file.name}"

            image_data.append({
                "Item Code": item,
                "Color Code": color,
                "Image File": file.name,
                "Public URL": fake_url
            })

        if image_data:
            export_csv(image_data, filename="filename_based_export.csv")
