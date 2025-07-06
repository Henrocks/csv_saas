import streamlit as st
import os
import pandas as pd
from urllib.parse import urlparse

st.title("CSV Generator for Image Directories")

mode = st.radio("Wie sind deine Dateien organisiert?", ["Nach Ordnerstruktur", "Nach Dateiname"])

uploaded_files = st.file_uploader("Lade deine Bilder hoch", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

def parse_filename(name):
    parts = name.split(".")[0].split("-")
    if len(parts) == 2:
        return parts[0], parts[1]
    return name, ""

if st.button("CSV generieren"):
    if not uploaded_files:
        st.warning("Bitte zuerst Dateien hochladen.")
    else:
        data = []
        for file in uploaded_files:
            item_code, color_code = parse_filename(file.name)
            public_url = f"https://fakehost.com/images/{file.name}"  # ← hier kommt später dein echter Link rein
            data.append({
                "Handle": item_code,
                "Title": item_code,
                "Image Src": public_url,
                "Image Position": 1,
                "Variant SKU": f"{item_code}-{color_code}",
                "Option1 Name": "Color",
                "Option1 Value": color_code
            })

        df = pd.DataFrame(data)
        st.success("CSV wurde erfolgreich erstellt:")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "export.csv", "text/csv")
