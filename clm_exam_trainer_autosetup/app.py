import os
import streamlit as st
import pandas as pd
import random, uuid

# --- base paths robustas ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(BASE_DIR, "images")

SPECIES_CSV = os.path.join(DATA_DIR, "species.csv")
SPECIES_TEMPLATE = os.path.join(DATA_DIR, "species_template.csv")
MAPPING_CSV = os.path.join(DATA_DIR, "image_species_mapping.csv")

# --- auto-creación de carpetas/archivos mínimos ---
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

if not os.path.exists(SPECIES_TEMPLATE):
    with open(SPECIES_TEMPLATE, "w", encoding="utf-8") as f:
        f.write("id,common_name,scientific_name,group,crea_category,is_invasive,is_cinegetica,cinegetica_comercializable_vivo,cinegetica_comercializable_muerto,has_hunting_quota,is_pescable,pescable_tipo,talla_minima_mm,notas\n")

if not os.path.exists(SPECIES_CSV):
    with open(SPECIES_CSV, "w", encoding="utf-8") as f:
        f.write("id,common_name,scientific_name,group,crea_category,is_invasive,is_cinegetica,cinegetica_comercializable_vivo,cinegetica_comercializable_muerto,has_hunting_quota,is_pescable,pescable_tipo,talla_minima_mm,notas\n")
        f.write("conejo,Oryctolagus cuniculus,Oryctolagus cuniculus,mamífero,,FALSE,TRUE,,,,,,,Ejemplo inicial\n")

if not os.path.exists(MAPPING_CSV):
    with open(MAPPING_CSV, "w", encoding="utf-8") as f:
        f.write("image_filename,species_id,scientific_name,common_name\n")

st.set_page_config(page_title="AAMM Trainer (auto-setup)", page_icon="🌿", layout="wide")
st.title("🌿 Entrenador práctico AAMM CLM (auto-configurado)")

with st.expander("📌 Cómo empezar (ultra simple)"):
    st.markdown("""
    - Esta app **crea sola** `data/` y los CSV si faltan.  
    - Para practicar, sube 1–2 imágenes en la pestaña *Cargar imágenes y vincular* y vincúlalas a una especie.  
    - Luego ve a *Modo Quiz*.
    """)

@st.cache_data
def load_species():
    df = pd.read_csv(SPECIES_CSV, comment="#", dtype=str).fillna("")
    need = ["id","common_name","scientific_name","group","crea_category","is_invasive","is_cinegetica",
            "cinegetica_comercializable_vivo","cinegetica_comercializable_muerto","has_hunting_quota",
            "is_pescable","pescable_tipo","talla_minima_mm","notas"]
    for c in need:
        if c not in df.columns:
            df[c] = ""
    for i, row in df.iterrows():
        if not row["id"]:
            base = (row.get("scientific_name") or row.get("common_name") or f"sp{i}").lower().replace(" ", "_")
            df.at[i, "id"] = f"{base}_{uuid.uuid4().hex[:6]}"
    return df

@st.cache_data
def load_mapping():
    return pd.read_csv(MAPPING_CSV, comment="#", dtype=str).fillna("")

species_df = load_species()
mapping_df = load_mapping()

tab1, tab2, tab3 = st.tabs(["📚 Base de especies", "🖼️ Cargar imágenes y vincular", "🧠 Modo Quiz"])

with tab1:
    st.subheader("Base de especies (CSV)")
    st.dataframe(species_df, use_container_width=True)
    st.download_button("⬇️ Descargar plantilla species_template.csv", data=open(SPECIES_TEMPLATE,"rb").read(), file_name="species_template.csv")

with tab2:
    st.subheader("Sube imágenes y vincula")
    upl = st.file_uploader("Arrastra tus imágenes", type=["jpg","jpeg","png","webp"], accept_multiple_files=True)
    if upl:
        for f in upl:
            with open(os.path.join(IMAGES_DIR, f.name), "wb") as out:
                out.write(f.read())
        st.success(f"Guardadas {len(upl)} imagen(es).")
    imgs = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".jpg",".jpeg",".png",".webp"))])
    if not imgs:
        st.info("Sube una imagen para empezar.")
    else:
        image_name = st.selectbox("Imagen", imgs)
        st.image(os.path.join(IMAGES_DIR, image_name), use_column_width=True)

        def label(row):
            return f"{row.get('common_name','')} — {row.get('scientific_name','')}"
        options = [{"key": row["id"], "label": label(row)} for _, row in species_df.iterrows()]
        chosen = st.selectbox("Especie", options, format_func=lambda o: o["label"])

        if st.button("➕ Guardar vínculo"):
            mapping_df = load_mapping()
            mapping_df.loc[len(mapping_df)] = {
                "image_filename": image_name,
                "species_id": chosen["key"],
                "scientific_name": "",
                "common_name": ""
            }
            mapping_df.to_csv(MAPPING_CSV, index=False)
            st.success("Vínculo guardado.")
            st.cache_data.clear()

        st.markdown("#### Vínculos existentes")
        st.dataframe(load_mapping(), use_container_width=True)

with tab3:
    st.subheader("Generador de preguntas")
    q_types = st.multiselect("Tipos de pregunta", [
        "Identificación (nombre científico)",
        "¿Es exótica invasora (EEI)?",
        "¿Es cinegética?"
    ], default=[
        "Identificación (nombre científico)",
        "¿Es exótica invasora (EEI)?"
    ])
    num_q = st.slider("Número total de preguntas", 1, 20, 6)

    def yn(flag): return "Sí" if str(flag).strip().upper()=="TRUE" else "No"

    def build_question(img_row, sp, qtype):
        img_path = os.path.join(IMAGES_DIR, img_row["image_filename"])
        if qtype == "Identificación (nombre científico)":
            correct = sp.get("scientific_name","").strip()
            pool = [x for x in species_df["scientific_name"].tolist() if x and x != correct]
            pool = pool[:3] + ["—"]*(3-len(pool[:3])) if len(pool)<3 else pool[:3]
            opts = pool + [correct]; random.shuffle(opts)
            return "Nombre científico:", opts, correct, f"Es {sp.get('common_name','')} ({correct}).", img_path
        if qtype == "¿Es exótica invasora (EEI)?":
            correct = yn(sp.get("is_invasive",""))
            return "¿Es EEI en CLM?", ["Sí","No","Solo en ZEPA","Solo en humedales"], correct, f"is_invasive={sp.get('is_invasive','')}.", img_path
        if qtype == "¿Es cinegética?":
            correct = yn(sp.get("is_cinegetica",""))
            return "¿Es cinegética en CLM?", ["Sí","No","Solo en reservas","Solo control de daños"], correct, f"is_cinegetica={sp.get('is_cinegetica','')}.", img_path
        return "",[], "", "", None

    if st.button("🎯 Empezar quiz"):
        pairs = []
        for _, m in load_mapping().iterrows():
            g = species_df[species_df["id"] == m["species_id"]]
            if not g.empty and os.path.exists(os.path.join(IMAGES_DIR, m["image_filename"])):
                pairs.append((m, g.iloc[0].to_dict()))
        if not pairs:
            st.warning("Añade al menos un vínculo imagen↔especie en la pestaña anterior.")
        else:
            questions = []
            while len(questions) < num_q:
                m, sp = random.choice(pairs)
                qtype = random.choice(q_types if q_types else ["Identificación (nombre científico)"])
                enun, opts, corr, exp, img_path = build_question(m, sp, qtype)
                if enun:
                    questions.append({"img": img_path, "qtype": qtype, "q": enun, "opts": opts, "correct": corr, "exp": exp})
            st.session_state["questions"] = questions
            st.session_state["answers"] = [None]*len(questions)
            st.success(f"Generadas {len(questions)} preguntas.")

    questions = st.session_state.get("questions", [])
    answers = st.session_state.get("answers", [])
    if questions:
        for i, q in enumerate(questions):
            st.markdown("---")
            cols = st.columns([2,3])
            with cols[0]:
                if q["img"] and os.path.exists(q["img"]):
                    st.image(q["img"], use_column_width=True)
                st.caption(q["qtype"])
            with cols[1]:
                st.markdown(f"**Pregunta {i+1}.** {q['q']}")
                choice = st.radio("Elige una opción:", q["opts"], index=None, key=f"q{i}")
                answers[i] = choice
        if st.button("✅ Corregir"):
            okc = 0
            for i, q in enumerate(questions):
                ok = answers[i] == q["correct"]
                if ok: okc += 1
                st.markdown(f"**Pregunta {i+1}:** {'✅ Correcta' if ok else '❌ Incorrecta'}")
                st.markdown(f"- Respuesta correcta: **{q['correct']}**")
                st.markdown(f"- Explicación: {q['exp']}")
            st.markdown(f"### Puntuación: {okc} / {len(questions)}")
