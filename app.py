# app.py
import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json
import os
import hashlib

st.set_page_config(page_title="Kite for Life - Avaliação de Desempenho", layout="wide")
st.title("Kite for Life — Avaliação de Desempenho")

# -----------------------------------------------------------------------------
# Paths & constants
# -----------------------------------------------------------------------------
DB_PATH = "evaluations.db"
USERS_PATH = "users.json"
WEIGHTS_PATH = "weights.json"

CRITERIA = [
    ("lideranca", "LIDERANÇA"),
    ("assiduidade", "ASSIDUIDADE"),
    ("flexibilidade", "FLEXIBILIDADE"),
    ("teoria", "TEORIA"),
    ("comando", "COMANDO"),
    ("controle", "CONTROLE"),
    ("badydrag_esq_dir", "BADYDRAG ESQ/DIR"),
    ("water_start", "WATER START"),
    ("prancha_esq_dir", "PRANCHA ESQ/DIR"),
    ("contra_vento", "CONTRA VENTO"),
]
CRITERIA_KEYS = [k for k, _ in CRITERIA]
CRITERIA_LABELS = [label for _k, label in CRITERIA]

# -----------------------------------------------------------------------------
# Basic theming (CSS)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Background and main container */
    .reportview-container .main {
        background: linear-gradient(180deg, #0f1724 0%, #071025 100%);
        color: #e6eef8;
    }
    /* Headers */
    h1, h2, h3, .css-18e3th9 {
        color: #e6eef8;
    }
    /* Sidebar */
    .css-1d391kg { background: #071025; }
    /* Table header */
    .stDataFrame table thead th { background-color: #0b1220; color: #e6eef8; }
    </style>
    """,
    unsafe_allow_html=True,
)

# set default plotly template via px
PX_TEMPLATE = "plotly_dark"

# -----------------------------------------------------------------------------
# Authentication helpers (very simple, local)
# -----------------------------------------------------------------------------
def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_users():
    if not os.path.exists(USERS_PATH):
        # create default user admin/admin (change it with create_user.py)
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump({"admin": hash_pw("admin")}, f, indent=2)
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def check_credentials(username: str, password: str) -> bool:
    users = load_users()
    if username in users and users[username] == hash_pw(password):
        return True
    return False

if "user" not in st.session_state:
    st.session_state.user = None

# Sidebar login/logout
st.sidebar.title("Autenticação")
if st.session_state.user is None:
    u = st.sidebar.text_input("Usuário")
    p = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        if check_credentials(u, p):
            st.session_state.user = u
            st.sidebar.success(f"Logado como {u}")
        else:
            st.sidebar.error("Usuário ou senha incorretos")
    st.sidebar.info("Usuário padrão: admin / admin (mude com create_user.py)")
else:
    st.sidebar.success(f"Logado como: {st.session_state.user}")
    if st.sidebar.button("Sair"):
        st.session_state.user = None
        st.experimental_rerun()

# -----------------------------------------------------------------------------
# Database init + schema ensure
# -----------------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

def ensure_table():
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto TEXT,
            nome TEXT,
            cargo TEXT,
            data TEXT,
            lideranca REAL,
            assiduidade REAL,
            flexibilidade REAL,
            teoria REAL,
            comando REAL,
            controle REAL,
            badydrag_esq_dir REAL,
            water_start REAL,
            prancha_esq_dir REAL,
            contra_vento REAL,
            nota_media REAL,
            nota_ponderada REAL,
            comentarios TEXT
        )
        """
    )
    conn.commit()

def add_missing_columns():
    # ensure nota_ponderada exists (older DBs may not have it)
    info = c.execute("PRAGMA table_info(evaluations)").fetchall()
    cols = [r[1] for r in info]
    if "nota_ponderada" not in cols:
        try:
            c.execute("ALTER TABLE evaluations ADD COLUMN nota_ponderada REAL")
            conn.commit()
        except:
            pass

ensure_table()
add_missing_columns()

# -----------------------------------------------------------------------------
# Weights helpers
# -----------------------------------------------------------------------------
def load_weights():
    if os.path.exists(WEIGHTS_PATH):
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            w = json.load(f)
            # ensure all keys exist
            for k in CRITERIA_KEYS:
                if k not in w:
                    w[k] = round(1.0/len(CRITERIA_KEYS), 4)
            # normalize
            s = sum(w.values()) or 1.0
            for k in w:
                w[k] = w[k] / s
            return w
    else:
        # equal weights
        eq = {k: 1.0/len(CRITERIA_KEYS) for k in CRITERIA_KEYS}
        with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
            json.dump(eq, f, indent=2)
        return eq

def save_weights(w: dict):
    # normalize and save
    s = sum(w.values()) or 1.0
    for k in w:
        w[k] = float(w[k]) / s
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(w, f, indent=2)

def draw_random_weights(seed=None):
    if seed is not None:
        np.random.seed(seed)
    vals = np.random.random(len(CRITERIA_KEYS))
    vals = vals / vals.sum()
    return {k: float(v) for k, v in zip(CRITERIA_KEYS, vals)}

# load weights to session
if "weights" not in st.session_state:
    st.session_state.weights = load_weights()

# -----------------------------------------------------------------------------
# Utility: map uploaded CSV row into criteria (with normalization 0-10)
# -----------------------------------------------------------------------------
def to_float(x):
    try:
        return float(x)
    except:
        return None

def map_row_to_criteria(row):
    def pick(*names):
        for n in names:
            if n in row and pd.notna(row[n]):
                return row[n]
        return None

    projeto = pick("projeto", "PROJETO", "Projeto") or "KITE FOR LIFE"
    nome = pick("nome", "Nome", "NOME") or ""
    cargo = pick("cargo", "Cargo", "CARGO") or ""
    data = pick("data", "Data", "DATA") or ""
    comentarios = pick("comentarios", "Comentários", "Comentarios", "COMENTARIOS") or ""

    mapped_raw = {}
    # attempt mapping variants for each criterion (common variants)
    mapping_variants = {
        "lideranca": ["liderança", "lideranca", "LIDERANÇA", "LIDERANCA"],
        "assiduidade": ["assiduidade", "ASSIDUIDADE"],
        "flexibilidade": ["flexibilidade", "FLEXIBILIDADE"],
        "teoria": ["teoria", "TEORIA"],
        "comando": ["comando", "COMANDO"],
        "controle": ["controle", "CONTROLE", "conrole"],
        "badydrag_esq_dir": ["badydrag esq/dir", "badydrag_esq_dir", "badydrag", "BADYDRAG ESQ/DIR"],
        "water_start": ["water start", "water_start", "WATER START", "water-start"],
        "prancha_esq_dir": ["prancha esq/dir", "prancha_esq_dir", "PRANCHA ESQ/DIR"],
        "contra_vento": ["contra vento", "contra_vento", "contra-vento", "CONTRA VENTO"],
    }
    for key, variants in mapping_variants.items():
        mapped_raw[key] = None
        for v in variants:
            if v in row and pd.notna(row[v]):
                mapped_raw[key] = to_float(row[v])
                break

    mapped = {
        "projeto": projeto,
        "nome": nome,
        "cargo": cargo,
        "data": data,
        "comentarios": comentarios,
    }
    for k in CRITERIA_KEYS:
        mapped[k] = mapped_raw.get(k)

    # Normalize per-row to 0-10 if needed: if any value > 10, rescale all numeric criteria so max -> 10
    vals = [v for v in [mapped[k] for k in CRITERIA_KEYS] if v is not None]
    if len(vals) > 0:
        max_val = max(vals)
        if max_val > 10:
            factor = max_val / 10.0
            for key in CRITERIA_KEYS:
                if mapped[key] is not None:
                    mapped[key] = mapped[key] / factor

    return mapped

# -----------------------------------------------------------------------------
# Data loading helpers
# -----------------------------------------------------------------------------
def load_db_df():
    df = pd.read_sql_query("SELECT * FROM evaluations ORDER BY id DESC", conn)
    if "data" in df.columns:
        try:
            df["data"] = pd.to_datetime(df["data"])
        except:
            pass
    return df

def ensure_numeric_cols(df):
    for k in CRITERIA_KEYS + ["nota_media", "nota_ponderada"]:
        if k in df.columns:
            df[k] = pd.to_numeric(df[k], errors="coerce")

# -----------------------------------------------------------------------------
# Sidebar navigation & global controls
# -----------------------------------------------------------------------------
st.sidebar.title("Menu")
page = st.sidebar.selectbox("Ir para", ["Avaliar", "Importar / Exportar", "Lista", "Radar", "Dashboard", "Reset DB"])

st.sidebar.markdown("---")
st.sidebar.subheader("Pesos (média ponderada)")
st.sidebar.write("Pesos atuais (soma = 1):")
w_display = {CRITERIA_LABELS[i]: round(st.session_state.weights[CRITERIA_KEYS[i]], 3) for i in range(len(CRITERIA_KEYS))}
st.sidebar.json(w_display)

col_draw1, col_draw2 = st.sidebar.columns([1,1])
with col_draw1:
    if st.sidebar.button("Sortear pesos"):
        st.session_state.weights = draw_random_weights()
        save_weights(st.session_state.weights)
        st.experimental_rerun()
with col_draw2:
    if st.sidebar.button("Reset pesos igual"):
        st.session_state.weights = {k: 1.0/len(CRITERIA_KEYS) for k in CRITERIA_KEYS}
        save_weights(st.session_state.weights)
        st.experimental_rerun()

if st.sidebar.button("Salvar pesos atuais"):
    save_weights(st.session_state.weights)
    st.sidebar.success("Pesos salvos em weights.json")

st.sidebar.markdown("---")
st.sidebar.write("Exportações")
df_all = load_db_df()
if not df_all.empty:
    st.sidebar.download_button("Exportar todas avaliações (CSV)", data=df_all.to_csv(index=False), file_name="avaliacoes_kite_for_life.csv", mime="text/csv")

# -----------------------------------------------------------------------------
# Page implementations
# -----------------------------------------------------------------------------
def page_import_export():
    st.header("Importar / Exportar")
    uploaded_file = st.file_uploader("Faça upload de um arquivo CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.success("CSV carregado com sucesso (edite abaixo antes de importar).")
        except Exception as e:
            st.error(f"Erro ao ler CSV: {e}")
            return
        edited = st.experimental_data_editor(df, num_rows="dynamic")
        if st.button("Salvar CSV editado (local)"):
            edited.to_csv("uploaded_saved.csv", index=False)
            st.success("CSV salvo como uploaded_saved.csv")
        if st.button("Importar linhas do CSV para o banco de avaliações"):
            count = 0
            for _, row in edited.iterrows():
                mapped = map_row_to_criteria(row)
                criteria_vals = [mapped[key] for key in CRITERIA_KEYS]
                valid = [v for v in criteria_vals if v is not None]
                nota_media = float(np.mean(valid)) if len(valid) > 0 else None
                # compute weighted if weights present
                weights = st.session_state.weights
                if weights:
                    # if some criteria missing, re-normalize weights for present ones
                    present_keys = [k for k, v in zip(CRITERIA_KEYS, criteria_vals) if v is not None]
                    if len(present_keys) > 0:
                        s = sum([weights[k] for k in present_keys])
                        nota_ponderada = sum([mapped[k] * (weights[k]/s) for k in present_keys])
                    else:
                        nota_ponderada = None
                else:
                    nota_ponderada = None
                try:
                    c.execute(
                        """
                        INSERT INTO evaluations
                        (projeto, nome, cargo, data, lideranca, assiduidade, flexibilidade, teoria, comando, controle, badydrag_esq_dir, water_start, prancha_esq_dir, contra_vento, nota_media, nota_ponderada, comentarios)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            mapped["projeto"], mapped["nome"], mapped["cargo"], mapped["data"],
                            mapped["lideranca"], mapped["assiduidade"], mapped["flexibilidade"],
                            mapped["teoria"], mapped["comando"], mapped["controle"], mapped["badydrag_esq_dir"],
                            mapped["water_start"], mapped["prancha_esq_dir"], mapped["contra_vento"],
                            nota_media, nota_ponderada, mapped["comentarios"]
                        ),
                    )
                    count += 1
                except Exception as e:
                    st.warning(f"Não foi possível importar linha: {e}")
            conn.commit()
            st.success(f"{count} linhas importadas para o banco de avaliações.")
    st.markdown("---")
    df_db = load_db_df()
    if not df_db.empty:
        st.download_button("Baixar todas as avaliações (CSV)", data=df_db.to_csv(index=False), file_name="avaliacoes_kite_for_life.csv", mime="text/csv")
    else:
        st.info("Nenhuma avaliação salva ainda.")

def page_avaliar():
    st.header("Adicionar nova avaliação")
    if st.session_state.user is None:
        st.warning("Você precisa estar autenticado para adicionar avaliações.")
        return

    with st.form("add_eval"):
        col1, col2, col3 = st.columns(3)
        projeto = col1.text_input("Projeto", value="KITE FOR LIFE")
        nome = col2.text_input("Nome do avaliado")
        cargo = col3.text_input("Cargo")
        col4, col5 = st.columns(2)
        data_av = col4.date_input("Data", value=datetime.date.today())

        st.markdown("### Notas por critério (escala 0–10)")
        sliders = {}
        n = len(CRITERIA)
        per_row = 3
        for i in range(0, n, per_row):
            cols = st.columns(per_row)
            for j, (key, label) in enumerate(CRITERIA[i:i+per_row]):
                sliders[key] = cols[j].slider(label, min_value=0.0, max_value=10.0, value=5.0, step=0.1)

        aplicar_pesos = st.checkbox("Aplicar pesos atuais ao salvar (salva nota_ponderada)", value=False)
        comentarios = st.text_area("Comentários", height=100)
        submitted = st.form_submit_button("Salvar avaliação")

    if submitted:
        vals = [float(sliders[key]) for key, _ in CRITERIA]
        nota_media = float(np.mean(vals))
        nota_ponderada = None
        if aplicar_pesos:
            weights = st.session_state.weights
            # weighted sum
            nota_ponderada = sum([vals[i] * weights[CRITERIA_KEYS[i]] for i in range(len(CRITERIA_KEYS))])

        insert_values = (
            projeto, nome, cargo, data_av.isoformat(),
            vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8], vals[9],
            nota_media, nota_ponderada, comentarios
        )
        c.execute(
            """
            INSERT INTO evaluations
            (projeto, nome, cargo, data, lideranca, assiduidade, flexibilidade, teoria, comando, controle, badydrag_esq_dir, water_start, prancha_esq_dir, contra_vento, nota_media, nota_ponderada, comentarios)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_values,
        )
        conn.commit()
        st.success("Avaliação salva com sucesso.")

def page_lista():
    st.header("Avaliações registradas")
    df_db = load_db_df()
    if df_db.empty:
        st.info("Nenhuma avaliação registrada ainda.")
        return
    ensure_numeric_cols(df_db)
    # format numeric columns
    for key in CRITERIA_KEYS:
        if key in df_db.columns:
            df_db[key] = df_db[key].round(2)
    if "nota_media" in df_db.columns:
        df_db["nota_media"] = df_db["nota_media"].round(2)
    if "nota_ponderada" in df_db.columns:
        df_db["nota_ponderada"] = df_db["nota_ponderada"].round(2)
    st.dataframe(df_db)

    st.markdown("---")
    # quick filters & export
    cols = st.columns(3)
    cargo_list = ["Todos"] + sorted(df_db["cargo"].dropna().unique().tolist())
    cargo_sel = cols[0].selectbox("Filtrar por cargo", cargo_list)
    try:
        date_min = df_db["data"].min()
        date_max = df_db["data"].max()
    except:
        date_min = datetime.date.today()
        date_max = datetime.date.today()
    date_range = cols[1].date_input("Filtrar por período", value=(date_min.date() if hasattr(date_min, "date") else date_min, date_max.date() if hasattr(date_max, "date") else date_max))
    if cols[2].button("Aplicar filtro e exportar"):
        df_f = df_db.copy()
        if cargo_sel != "Todos":
            df_f = df_f[df_f["cargo"] == cargo_sel]
        start, end = date_range
        df_f = df_f[(df_f["data"] >= pd.to_datetime(start)) & (df_f["data"] <= pd.to_datetime(end))]
        st.download_button("Baixar CSV filtrado", data=df_f.to_csv(index=False), file_name="avaliacoes_filtradas.csv", mime="text/csv")
        st.success(f"{len(df_f)} linhas prontas para download.")

def page_radar():
    st.header("Gráfico Radar por Avaliação")
    df_db = load_db_df()
    if df_db.empty:
        st.info("Nenhuma avaliação disponível para exibir o radar.")
        return

    options = df_db.apply(lambda r: f"{int(r.id)} — {r.nome} ({r.data.date() if hasattr(r.data, 'date') else r.data})", axis=1).tolist()
    sel = st.selectbox("Selecione a avaliação", options)
    if sel:
        selected_id = int(sel.split(" — ")[0])
        row = df_db[df_db["id"] == selected_id].iloc[0]
        labels = CRITERIA_LABELS
        values = [row[key] if pd.notna(row[key]) else 0.0 for key in CRITERIA_KEYS]
        fig = go.Figure(
            data=[
                go.Scatterpolar(r=values + [values[0]], theta=labels + [labels[0]], fill='toself', name=f"{row['nome']}", marker=dict(color=px.colors.qualitative.Plotly[0]))
            ]
        )
        fig.update_layout(template=PX_TEMPLATE, polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=True, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True)

def page_dashboard():
    st.header("Dashboard — Visão Geral")
    df_db = load_db_df()
    if df_db.empty:
        st.info("Nenhuma avaliação disponível para gerar o dashboard.")
        return
    ensure_numeric_cols(df_db)

    # Filters
    st.sidebar.subheader("Filtros do Dashboard")
    min_date = df_db["data"].min().date() if pd.notna(df_db["data"].min()) else datetime.date.today()
    max_date = df_db["data"].max().date() if pd.notna(df_db["data"].max()) else datetime.date.today()
    date_range = st.sidebar.date_input("Período", value=(min_date, max_date))
    cargos = sorted(df_db["cargo"].dropna().unique().tolist())
    cargo_sel = st.sidebar.multiselect("Cargo (filtrar)", options=cargos, default=cargos)

    # apply filters
    df_f = df_db.copy()
    start, end = date_range
    df_f = df_f[(df_f["data"] >= pd.to_datetime(start)) & (df_f["data"] <= pd.to_datetime(end))]
    if cargo_sel:
        df_f = df_f[df_f["cargo"].isin(cargo_sel)]

    if df_f.empty:
        st.warning("Nenhum registro após aplicar filtros.")
        return

    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric("Número de avaliações", len(df_f))
    k2.metric("Média geral (nota_media)", round(df_f["nota_media"].mean(), 2))
    if "nota_ponderada" in df_f.columns:
        k3.metric("Média ponderada (nota_ponderada)", round(df_f["nota_ponderada"].dropna().mean() if not df_f["nota_ponderada"].dropna().empty else 0.0, 2))
    else:
        pct_above7 = (df_f["nota_media"] > 7).mean() * 100
        k3.metric("Avaliações > 7", f"{pct_above7:.0f}%")

    st.markdown("---")
    # Average per criterion (bar)
    mean_criteria = {label: df_f[key].mean() for key, label in zip(CRITERIA_KEYS, CRITERIA_LABELS)}
    mean_df = pd.DataFrame({"critério": list(mean_criteria.keys()), "média": list(mean_criteria.values())})
    fig_bar = px.bar(mean_df, x="critério", y="média", range_y=[0,10], title="Média por Critério (0–10)", text=mean_df["média"].round(2), template=PX_TEMPLATE, color_discrete_sequence=px.colors.sequential.Plasma)
    fig_bar.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_bar, use_container_width=True)

    # Boxplots per criterion
    st.markdown("### Distribuição por Critério")
    melt_df = df_f.melt(id_vars=["id","nome"], value_vars=CRITERIA_KEYS, var_name="critério_key", value_name="nota")
    fig_box = px.box(melt_df, x="critério_key", y="nota", points="outliers", template=PX_TEMPLATE, color_discrete_sequence=px.colors.sequential.Magma)
    fig_box.update_xaxes(ticktext=CRITERIA_LABELS, tickvals=CRITERIA_KEYS)
    fig_box.update_layout(yaxis=dict(range=[0,10]), xaxis_title=None, yaxis_title="Nota (0–10)")
    st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("---")
    # Top performers
    st.markdown("### Top avaliados (por nota média)")
    top_n = st.selectbox("Quantos mostrar", [5, 10, 20], index=0)
    top_df = df_f.sort_values("nota_media", ascending=False).head(top_n)[["id","nome","cargo","data","nota_media"]]
    top_df["data"] = top_df["data"].dt.date
    st.table(top_df.reset_index(drop=True))

    st.markdown("---")
    # Time series: média por mês
    st.markdown("### Evolução — Média por Período")
    ts = df_f.set_index("data").resample("M")["nota_media"].mean().reset_index()
    ts["data"] = ts["data"].dt.to_period("M").dt.to_timestamp()
    fig_ts = px.line(ts, x="data", y="nota_media", title="Média de nota_media por mês", markers=True, template=PX_TEMPLATE)
    fig_ts.update_yaxes(range=[0,10])
    st.plotly_chart(fig_ts, use_container_width=True)

    st.markdown("---")
    # Radar Comparison: allow choose up to 2 evaluations
    st.markdown("### Comparar avaliações (Radar)")
    options = df_f.apply(lambda r: f"{int(r.id)} — {r.nome} ({r.data.date()})", axis=1).tolist()
    sel_ids = st.multiselect("Selecione 1 ou 2 avaliações para comparar", options, default=options[:2] if len(options) >= 2 else options[:1])
    if sel_ids:
        fig = go.Figure()
        pal = px.colors.qualitative.Plotly
        for idx, s in enumerate(sel_ids[:2]):
            sid = int(s.split(" — ")[0])
            row = df_f[df_f["id"] == sid].iloc[0]
            values = [row[k] if pd.notna(row[k]) else 0.0 for k in CRITERIA_KEYS]
            fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=CRITERIA_LABELS + [CRITERIA_LABELS[0]], fill='toself', name=f"{row['nome']}", marker=dict(color=pal[idx % len(pal)])))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,10])), showlegend=True, template=PX_TEMPLATE)
        st.plotly_chart(fig, use_container_width=True)

def page_reset_db():
    st.header("Resetar banco de dados")
    st.warning("Isto apagará todas as avaliações permanentemente.")
    if st.button("CONFIRMAR: Apagar todas avaliações"):
        c.execute("DROP TABLE IF EXISTS evaluations")
        conn.commit()
        ensure_table()
        add_missing_columns()
        st.success("Banco reiniciado. Todas as avaliações apagadas.")

# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
if page == "Avaliar":
    page_avaliar()
elif page == "Importar / Exportar":
    page_import_export()
elif page == "Lista":
    page_lista()
elif page == "Radar":
    page_radar()
elif page == "Dashboard":
    page_dashboard()
elif page == "Reset DB":
    page_reset_db()
else:
    st.info("Página não encontrada.")