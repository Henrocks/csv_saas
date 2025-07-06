import streamlit as st
import dropbox
import pandas as pd
from pathlib import Path
import re

# === PAGE CONFIG ===
st.set_page_config(page_title="CSV Generator mit Dropbox", layout="wide")
st.markdown("# CSV Generator mit Dropbox")

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
                example_file = image_files[0]

                rows = []
                itemcode = colorcode = ""

                if method == "Ordnerstruktur":
                    st.subheader("3. 📁 Ordnerstruktur zuordnen")
                    path_parts = Path(example_file.path_display).parts
                    editable_parts = list(path_parts[:-1])

                    st.markdown(f"Beispielpfad: `/{'/'.join(path_parts)}`")
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
                    filename = Path(example_file.name).stem
                    st.markdown(f"Beispieldatei: `{example_file.name}`")

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
                st.download_button("📥 CSV herunterladen", data=csv_data, file_name="export.csv", mime="text/csv")

            else:
                st.warning("Keine Bilddateien gefunden.")

    except Exception as e:
        st.error(f"Fehler beim Dropbox-Zugriff: {e}")
else:
    st.info("Bitte gib dein Dropbox Access Token ein.")
