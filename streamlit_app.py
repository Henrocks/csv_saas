import streamlit as st
import dropbox
import pandas as pd
from pathlib import Path
import re

# === PAGE CONFIG ===
st.set_page_config(page_title="CSV Generator mit Dropbox", layout="wide")
st.markdown("# CSV Generator mit Dropbox")

# === EINLEITUNG & ANLEITUNG ===
with st.expander("ℹ️ Anleitung anzeigen / ausblenden", expanded=True):
    st.markdown("""
    ## 📘 Anleitung

    1. **Dropbox-Zugriff vorbereiten**
       - Gehe auf die [Dropbox App Console](https://www.dropbox.com/developers/apps)
       - Klicke auf **"Create App"** und wähle:
         - **Scoped Access**
         - **App Folder**
       - Vergib einen eindeutigen App-Namen (z. B. `ImageExporter`)
       - Klicke nach der Erstellung auf den Tab **Permissions**
         - Aktiviere:
           - `files.metadata.read`
           - `files.content.read`
           - `sharing.read`
       - Dann oben in **Settings** wechseln
         - Scrolle nach unten und generiere unter **OAuth 2** dein Access Token
       - Kopiere das Token in dieses Tool

       🔄 **Wichtig:** Dropbox legt automatisch einen Ordner an:  
       `Apps/DeinAppName/`  
       → Lege deine Bilder dort in **einen beliebigen Unterordner**, z. B.:  
       `Apps/ImageExporter/Sommer/Artikel XY/`

    2. **Methode wählen**
       - **Ordnerstruktur**: Pfad wird analysiert
       - **Dateiname**: Tokens im Dateinamen werden genutzt

    3. **Regeln festlegen**
       - Weise jeder Ebene oder jedem Token eine Bedeutung zu (Itemcode, Farbe etc.)

    4. **CSV exportieren**
       - CSV prüfen und direkt herunterladen
    """)

# === SESSION STATE ===
if "dbx_token" not in st.session_state:
    st.session_state.dbx_token = ""
if "folder_mapping" not in st.session_state:
    st.session_state.folder_mapping = {}
if "token_mapping" not in st.session_state:
    st.session_state.token_mapping = {}
if "separator_count" not in st.session_state:
    st.session_state.separator_count = 1

# === Dropbox: Bestehenden Link oder neuen generieren ===
def get_shared_link(dbx, path):
    try:
        links = dbx.sharing_list_shared_links(path=path, direct_only=True).links
        if links:
            return links[0].url.replace("?dl=0", "?raw=1")
        else:
            link = dbx.sharing_create_shared_link_with_settings(path).url
            return link.replace("?dl=0", "?raw=1")
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Linkzugriff für {path}: {e}")
        return ""

# === UI: DROPBOX TOKEN ===
st.subheader("1. 🔐 Dropbox-Zugriff")
token = st.text_input("Dropbox Access Token", type="password", value=st.session_state.dbx_token)

# === UI: METHODE WÄHLEN ===
st.subheader("2. 📂 Extraktionsmethode wählen")
method = st.radio("Methode", ["Ordnerstruktur", "Dateiname"])

# === Dropbox Initialisierung ===
if token:
    st.session_state.dbx_token = token
    dbx = dropbox.Dropbox(token)

    try:
        folders = []
        res = dbx.files_list_folder(path="")
        for entry in res.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                folders.append(entry.name)

        selected_folder = st.selectbox("📁 Wähle einen Ordner im App-Folder:", folders)

        if selected_folder:
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

            if image_files:
                st.success(f"{len(image_files)} Bilder gefunden")

                # Beispielpfad mit maximaler Tiefe finden
                longest_path_file = max(image_files, key=lambda f: len(Path(f.path_display).parts))
                example_path_parts = Path(longest_path_file.path_display).parts
                editable_parts = list(example_path_parts[:-1])

                rows = []
                itemcode = colorcode = ""

                if method == "Ordnerstruktur":
                    st.subheader("3. 📁 Ordnerstruktur zuordnen")
                    st.markdown(f"Beispielpfad (tiefster gefunden): `/{'/'.join(example_path_parts)}`")
                    folder_mapping = {}
                    for i, part in enumerate(editable_parts):
                        key = f"level_{i}"
                        val = st.selectbox(
                            f"Ebene {i+1} – Ordnername: '{part}'",
                            ["Ignorieren", "Itemcode", "Farbcode", "Custom"],
                            key=key
                        )
                        folder_mapping[i] = val
                    st.session_state.folder_mapping = folder_mapping

                elif method == "Dateiname":
                    st.subheader("3. 📝 Dateiname analysieren")
                    filename = Path(image_files[0].name).stem
                    st.markdown(f"Beispieldatei: `{image_files[0].name}`")

                    sep_count = st.number_input("Anzahl der Trennzeichen-Felder", min_value=1, max_value=5, value=st.session_state.separator_count, key="sep_count")
                    st.session_state.separator_count = sep_count
                    sep_inputs = []
                    for i in range(sep_count):
                        sep = st.text_input(f"Trennzeichen {i+1}", key=f"sep_{i}")
                        if sep:
                            sep_inputs.append(sep)

                    pattern = '|'.join(map(re.escape, sep_inputs))
                    tokens = re.split(pattern, filename)

                    token_mapping = {}
                    for i, token in enumerate(tokens):
                        key = f"token_{i}"
                        val = st.selectbox(
                            f"Token {i+1} – '{token}'",
                            ["Ignorieren", "Itemcode", "Farbcode", "Custom"],
                            key=key
                        )
                        token_mapping[i] = val
                    st.session_state.token_mapping = token_mapping

                # === Verarbeitung aller Bilder ===
                for file in image_files:
                    link = get_shared_link(dbx, file.path_lower)
                    path_parts = Path(file.path_display).parts
                    filename = Path(file.name).stem

                    if method == "Ordnerstruktur":
                        parts = list(path_parts[:-1])
                        itemcode = colorcode = ""
                        for i, part in enumerate(parts):
                            tag = st.session_state.folder_mapping.get(i)
                            if tag == "Itemcode":
                                itemcode = part
                            elif tag == "Farbcode":
                                colorcode = part

                    elif method == "Dateiname":
                        pattern = '|'.join(map(re.escape, sep_inputs))
                        tokens = re.split(pattern, filename)
                        itemcode = colorcode = ""
                        for i, token in enumerate(tokens):
                            tag = st.session_state.token_mapping.get(i)
                            if tag == "Itemcode":
                                itemcode = token
                            elif tag == "Farbcode":
                                colorcode = token

                    rows.append({
                        "Itemcode": itemcode,
                        "Farbcode": colorcode,
                        "Bildname": file.name,
                        "Bildlink": link
                    })

                df = pd.DataFrame(rows)
                st.dataframe(df)
                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button("📅 CSV herunterladen", data=csv_data, file_name="export.csv", mime="text/csv")

            else:
                st.warning("Keine Bilddateien gefunden.")

    except Exception as e:
        st.error(f"Fehler beim Dropbox-Zugriff: {e}")
else:
    st.info("Bitte gib dein Dropbox Access Token ein.")
