import streamlit as st
import zipfile
import tempfile
import os
import pandas as pd

st.set_page_config(page_title="Bild-CSV Generator", layout="centered")

st.title("📁 CSV Generator für Bildverzeichnisse")

# Auswahl: Struktur-Modus
mode = st.radio(
    "Wie sind deine Dateien organisiert?",
    ["Nach Ordnerstruktur", "Nach Dateiname"],
    index=0
)

# Hinweis
if mode == "Nach Ordnerstruktur":
    st.markdown("**Hinweis:** Lade eine ZIP-Datei hoch, die deine Ordnerstruktur enthält.")
else:
    st.markdown("**Hinweis:** Lade einzelne Bilder hoch, die nach Artikelnamen/Farbcode benannt sind.")

uploaded_file = st.file_uploader(
    "Lade deine Dateien hoch",
    type=["zip"] if mode == "Nach Ordnerstruktur" else ["jpg", "jpeg", "png"],
    accept_multiple_files=(mode == "Nach Dateiname")
)

if st.button("📄 CSV generieren") and uploaded_file:
    data = []

    if mode == "Nach Ordnerstruktur":
        with tempfile.TemporaryDirectory() as tmp_dir:
            # ZIP entpacken
            with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Alle Bilder rekursiv durchsuchen
            for root, _, files in os.walk(tmp_dir):
                for file in files:
                    if file.lower().endswith((".jpg", ".jpeg", ".png")):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, tmp_dir)
                        parts = rel_path.split(os.sep)

                        product = parts[0] if len(parts) > 0 else ""
                        color = parts[1] if len(parts) > 1 else ""
                        filename = parts[-1]

                        data.append({
                            "Product Name": product,
                            "Color": color,
                            "Filename": filename,
                            "Image URL": f"https://example.com/{rel_path.replace(os.sep, '/')}"
                        })
    else:
        for file in uploaded_file:
            filename = file.name
            name_part = os.path.splitext(filename)[0]
            parts = name_part.split("-")
            product = parts[0] if len(parts) > 0 else ""
            color = parts[1] if len(parts) > 1 else ""

            data.append({
                "Product Name": product,
                "Color": color,
                "Filename": filename,
                "Image URL": f"https://example.com/{filename}"
            })

    df = pd.DataFrame(data)
    st.success(f"{len(df)} Einträge verarbeitet.")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 CSV herunterladen", csv, file_name="export.csv", mime="text/csv")
