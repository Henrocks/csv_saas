import streamlit as st
import dropbox
import os
import pandas as pd
from pathlib import Path

# === PAGE CONFIG ===
st.set_page_config(page_title="Image CSV Generator", layout="wide")
st.title("📸 CSV Generator mit Dropbox App Folder")

# === SESSION STATE ===
if "dbx_token" not in st.session_state:
    st.session_state.dbx_token = ""

# === UI: DROPBOX TOKEN INPUT ===
st.subheader("🔐 Dropbox App-Zugriff")
st.markdown("""
**Schritt 1:** Erstelle eine Dropbox-App mit Zugriff auf einen App-Ordner (z. B. `Apps/ImageExporter/`)

**Schritt 2:** Generiere ein Zugriffstoken (Scoped App, nur App Folder)

**Schritt 3:** Füge das Token hier ein:
""")
token = st.text_input("🔑 Dropbox Access Token", type="password", value=st.session_state.dbx_token)

# === UI: METHOD SELECTION ===
method = st.radio(
    "📂 Welche Methode möchtest du verwenden, um Itemcode und Farbcode zu extrahieren?",
    ["Ordnerstruktur verwenden", "Dateinamen analysieren"],
    help="Wähle, ob die Informationen aus der Ordnerstruktur oder aus den Dateinamen extrahiert werden sollen."
)

if method == "Dateinamen analysieren":
    st.markdown("**Beispiel:** `CSF440-119.jpg` → Trennzeichen `-` → Itemcode = CSF440, Farbcode = 119")
    filename_separator = st.text_input("Trennzeichen für Dateinamen", value="-", help="Nutze z. B. `-`, `_`, `.`, um die Teile des Dateinamens zu trennen.")

if token:
    st.session_state.dbx_token = token
    dbx = dropbox.Dropbox(token)

    try:
        folders = []
        res = dbx.files_list_folder(path="")
        for entry in res.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                folders.append(entry.name)

        selected_folder = st.selectbox("📁 Wähle einen Unterordner aus dem App Folder:", folders)

        if selected_folder:
            st.success(f"📂 Gewählter Ordner: {selected_folder}")

            # Alle Dateien im Ordner auflisten (rekursiv möglich)
            all_files = []
            def list_files_recursive(path):
                res = dbx.files_list_folder(path)
                for entry in res.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        all_files.append(entry)
                    elif isinstance(entry, dropbox.files.FolderMetadata):
                        list_files_recursive(entry.path_lower)
            list_files_recursive(f"/{selected_folder}")

            image_exts = [".jpg", ".jpeg", ".png", ".webp"]
            image_files = [f for f in all_files if Path(f.name).suffix.lower() in image_exts]

            if not image_files:
                st.warning("Keine Bilddateien gefunden.")
            else:
                st.success(f"✅ {len(image_files)} Bilddateien gefunden.")

                # === CSV-Export-Logik ===
                rows = []
                for file in image_files:
                    path_parts = Path(file.path_display).parts
                    filename = Path(file.name).name
                    link = dbx.sharing_create_shared_link_with_settings(file.path_lower).url.replace("?dl=0", "?raw=1")

                    if method == "Ordnerstruktur verwenden":
                        itemcode = path_parts[-3] if len(path_parts) >= 3 else ""
                        colorcode = path_parts[-2] if len(path_parts) >= 2 else ""
                    else:
                        name_core = filename.rsplit(".", 1)[0]  # ohne Dateiendung
                        parts = name_core.split(filename_separator)
                        itemcode = parts[0] if len(parts) > 0 else ""
                        colorcode = parts[1] if len(parts) > 1 else ""

                    rows.append({
                        "Itemcode": itemcode,
                        "Farbcode": colorcode,
                        "Bildname": filename,
                        "Bildlink": link
                    })

                df = pd.DataFrame(rows)
                st.dataframe(df)
                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 CSV herunterladen", data=csv_data, file_name="dropbox_export.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Fehler beim Dropbox-Zugriff: {e}")
else:
    st.info("Bitte gib dein Dropbox App Folder Token ein, um fortzufahren.")
