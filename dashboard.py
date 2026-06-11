"""
Social Afbeelding Agent — Dashboard (cloud)

Dit dashboard wordt gehost op Streamlit Community Cloud zodat het hele team
de voortgang kan volgen en afbeeldingen kan aanvragen. Het haakt aan op
dezelfde Google Sheet als de Social Media Agent (Marketing Agent Social
Media). Het dashboard zelf voert geen InDesign-generatie uit (dat kan niet in
de cloud) — een gebruiker kiest een foto en klikt op "Vraag generatie aan",
waarna een **lokale worker** (`python systems/run_worker.py`, handmatig
gestart) de afbeelding genereert, naar Drive uploadt en terugkoppelt naar de
"📅 Planning"-tab van het hoofddashboard.

Lokaal starten:
    streamlit run dashboard.py

Credentials: lokaal via .env (GOOGLE_SHEETS_SPREADSHEET_ID,
GOOGLE_SERVICE_ACCOUNT_JSON), in de cloud via Streamlit secrets (zelfde keys,
of GOOGLE_SERVICE_ACCOUNT_B64 voor het service-account JSON base64-encoded).
"""

import base64
import json
import os

import streamlit as st
from dotenv import load_dotenv

from systems import client_settings, sheet_queue, task_queue

load_dotenv()

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Paginaconfiguratie ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Top Socials · Beelden",
    page_icon="https://www.topmediagroep.nl/data/pam/public/logo/logo_topmediagroep_transparent.png",
    layout="wide",
)

# ── Stijl (1-op-1 gebaseerd op Marketing Agent Social Media/dashboard.py) ───────

BRAND = {
    "primary":      "#4F46E5",
    "primary_dark": "#3730A3",
    "primary_soft": "#F0F0FF",
    "success":      "#34C759",
    "warning":      "#FF9F0A",
    "danger":       "#FF3B30",
    "ink":          "#1D1D1F",
    "ink_soft":     "#86868B",
    "ink_xsoft":    "#C7C7CC",
    "line":         "rgba(0,0,0,.08)",
    "surface":      "#FFFFFF",
    "canvas":       "#F5F5F7",
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800;0,14..32,900&display=swap');

:root {{
    --p:     {BRAND['primary']};
    --pd:    {BRAND['primary_dark']};
    --ps:    {BRAND['primary_soft']};
    --ok:    {BRAND['success']};
    --warn:  {BRAND['warning']};
    --err:   {BRAND['danger']};
    --ink:   {BRAND['ink']};
    --ink2:  {BRAND['ink_soft']};
    --ink3:  {BRAND['ink_xsoft']};
    --line:  {BRAND['line']};
    --surf:  {BRAND['surface']};
    --bg:    {BRAND['canvas']};
    --r-card: 20px;
    --r-btn:  10px;
    --r-inp:  12px;
    --shadow: 0 2px 12px rgba(0,0,0,.07), 0 0 0 0.5px rgba(0,0,0,.04);
    --shadow-hover: 0 8px 32px rgba(0,0,0,.12), 0 0 0 0.5px rgba(0,0,0,.05);
}}

/* ── Font ── */
html, body, .stApp,
.stMarkdown, .stMarkdown p, .stMarkdown li,
.stMarkdown span:not([class*="material"]),
.stCaption, .stText, p, label,
.stButton button, .stDownloadButton button, .stLinkButton a,
input, textarea, select,
[data-testid="stMetricLabel"], [data-testid="stMetricValue"],
[data-testid="stWidgetLabel"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}}

/* ── Canvas ── */
html, body, .stApp,
[data-testid="stAppViewContainer"], [data-testid="stMain"],
.main, .main > div {{ background: var(--bg) !important; }}
.block-container {{ padding: 2rem 2.5rem 5rem !important; max-width: 1240px !important; }}

/* ── Streamlit chrome verbergen ── */
#MainMenu, footer, header[data-testid="stHeader"] {{
    visibility: hidden; height: 0; overflow: hidden;
}}
[data-testid="stToolbar"], [data-testid="manage-app-button"],
.stDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[class*="viewerBadge"], [data-testid="stAppViewerBadge"] {{
    display: none !important;
}}

/* ── Koppen ── */
h1, h2, h3, h4 {{
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    color: var(--ink) !important;
    letter-spacing: -0.03em !important;
}}

/* ── Divider ── */
hr {{ border-color: var(--line) !important; margin: 1.5rem 0 !important; }}

/* ── Tabs: gesegmenteerde pill-stijl ── */
.stTabs [data-baseweb="tab-list"] {{
    background: rgba(0,0,0,.05);
    border-radius: 14px;
    padding: 4px;
    gap: 2px;
    border: none !important;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 11px;
    padding: 7px 18px;
    font-weight: 600; font-size: 13px;
    color: var(--ink2);
    background: transparent;
    border: none !important;
    transition: all .18s ease;
}}
.stTabs [aria-selected="true"] {{
    background: var(--surf) !important;
    color: var(--ink) !important;
    box-shadow: 0 1px 6px rgba(0,0,0,.14) !important;
    border: none !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{ display: none; }}
.stTabs [data-baseweb="tab-border"]    {{ display: none; }}

/* ── Knoppen ── */
.stButton > button, .stDownloadButton > button,
.stButton button, .stDownloadButton button,
[data-testid^="stBaseButton"] {{
    border-radius: var(--r-btn) !important;
    font-weight: 600 !important; font-size: 13px !important;
    border: 1px solid var(--line) !important;
    background: var(--surf) !important;
    color: var(--ink) !important;
    transition: all .18s cubic-bezier(.4,0,.2,1);
    letter-spacing: -.01em;
}}
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {{
    background: var(--p) !important;
    border-color: var(--p) !important;
    color: #fff !important;
    box-shadow: 0 2px 10px rgba(79,70,229,.35) !important;
}}
.stButton > button:hover:not(:disabled),
[data-testid^="stBaseButton"]:hover:not(:disabled) {{
    box-shadow: var(--shadow) !important;
    transform: translateY(-1px);
}}
.stButton > button[kind="primary"]:hover:not(:disabled),
[data-testid="stBaseButton-primary"]:hover:not(:disabled) {{
    background: var(--pd) !important;
    border-color: var(--pd) !important;
}}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {{
    border-radius: var(--r-inp) !important;
    border: 1px solid var(--line) !important;
    background: var(--surf) !important;
    font-size: 14px !important;
    color: var(--ink) !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: var(--p) !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,.12) !important;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    background: var(--surf) !important;
    border: none !important;
    border-radius: 16px !important;
    box-shadow: var(--shadow) !important;
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{
    font-weight: 600 !important; font-size: 13px !important;
    color: var(--ink2) !important;
    padding: 12px 16px !important;
}}

/* ── Merk-header ── */
.ts-header {{
    display: flex; align-items: center;
    justify-content: space-between;
    padding: 18px 28px;
    margin-bottom: 22px;
    background: var(--surf);
    border-radius: var(--r-card);
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
}}
.ts-header::before {{
    content: "";
    position: absolute; left: 0; top: 0; bottom: 0; width: 5px;
    background: linear-gradient(180deg, var(--p), var(--pd));
}}
.ts-name {{
    font-size: 21px; font-weight: 800;
    color: var(--ink); letter-spacing: -0.03em;
    line-height: 1.2;
}}
.ts-brandtag {{
    display: inline-block; margin-left: 8px;
    font-size: 10px; font-weight: 700; letter-spacing: .08em;
    color: var(--p); background: var(--ps);
    padding: 2px 8px; border-radius: 99px; vertical-align: middle;
    text-transform: uppercase;
}}
.ts-sub {{
    font-size: 12px; font-weight: 400;
    color: var(--ink2); margin-top: 3px; letter-spacing: .01em;
}}
</style>
""", unsafe_allow_html=True)


PLATFORM_COLORS = {
    "instagram": "#E1306C",
    "linkedin":  "#0077B5",
    "facebook":  "#1877F2",
}
PLATFORM_LABELS = {
    "instagram": "IG",
    "linkedin":  "IN",
    "facebook":  "FB",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _from_secrets(key):
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def _credentials():
    spreadsheet_id = _from_secrets("GOOGLE_SHEETS_SPREADSHEET_ID") or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

    sa_json = _from_secrets("GOOGLE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        b64 = _from_secrets("GOOGLE_SERVICE_ACCOUNT_B64")
        if not b64:
            part1, part2 = _from_secrets("GOOGLE_SA_B64_1"), _from_secrets("GOOGLE_SA_B64_2")
            if part1 and part2:
                b64 = part1 + part2
        if b64:
            sa_json = base64.b64decode(b64).decode("utf-8")

    if not spreadsheet_id or not sa_json:
        st.error(
            "GOOGLE_SHEETS_SPREADSHEET_ID en/of GOOGLE_SERVICE_ACCOUNT_JSON "
            "ontbreken. Stel deze lokaal in via .env, of in de cloud via "
            "Streamlit secrets."
        )
        st.stop()
    # Valideer dat het JSON-blob geldig is
    try:
        json.loads(sa_json)
    except json.JSONDecodeError:
        st.error("GOOGLE_SERVICE_ACCOUNT_JSON is geen geldige JSON.")
        st.stop()
    return spreadsheet_id, sa_json


@st.cache_data(ttl=60)
def _load_post_tabs(spreadsheet_id, sa_json):
    return sheet_queue.load_post_tabs(spreadsheet_id, sa_json)


@st.cache_data(ttl=30)
def _load_rows(tab_name, spreadsheet_id, sa_json):
    return sheet_queue.load_rows(tab_name, spreadsheet_id, sa_json)


@st.cache_data(ttl=60)
def _load_clients_basic(spreadsheet_id, sa_json):
    return sheet_queue.load_clients_basic(spreadsheet_id, sa_json)


@st.cache_data(ttl=30)
def _load_client_settings(spreadsheet_id, sa_json):
    return client_settings.load_client_settings(spreadsheet_id, sa_json)


@st.cache_data(ttl=30)
def _load_photo_index(spreadsheet_id, sa_json):
    return task_queue.load_photo_index(spreadsheet_id, sa_json)


@st.cache_data(ttl=15)
def _load_tasks(spreadsheet_id, sa_json):
    return task_queue.load_tasks(spreadsheet_id, sa_json)


def _check_password():
    """Toont een wachtwoordveld en stopt de app als het wachtwoord ontbreekt of onjuist is.

    Wachtwoord wordt ingesteld via APP_PASSWORD in .env (lokaal) of Streamlit
    secrets (cloud). De repo is publiek (alleen code, geen credentials), dus
    deze simpele check houdt het dashboard zelf afgeschermd voor het team.
    """
    app_password = _from_secrets("APP_PASSWORD") or os.getenv("APP_PASSWORD")
    if not app_password:
        st.error("APP_PASSWORD is niet ingesteld (.env of Streamlit secrets).")
        st.stop()

    if st.session_state.get("authenticated"):
        return

    st.markdown(
        """
        <div class="ts-header">
            <div>
                <span class="ts-name">Social Afbeelding Agent</span>
                <span class="ts-brandtag">Beelden</span>
                <div class="ts-sub">Log in om verder te gaan</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pwd = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen", type="primary"):
        if pwd == app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Onjuist wachtwoord.")
    st.stop()


def _format_tab_label(tab_name):
    # "Posts_2026_W24" → "2026 · Week 24"
    parts = tab_name.split("_")
    if len(parts) == 3:
        _, year, week = parts
        return f"{year} · Week {week.lstrip('W')}"
    return tab_name


# ── UI: login + header ───────────────────────────────────────────────────────

_check_password()

st.markdown(
    """
    <div class="ts-header">
        <div>
            <span class="ts-name">Social Afbeelding Agent</span>
            <span class="ts-brandtag">Beelden</span>
            <div class="ts-sub">Genereer InDesign-afbeeldingen voor goedgekeurde posts</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

spreadsheet_id, sa_json = _credentials()

tab_generate, tab_settings = st.tabs(["🖼️ Afbeeldingen genereren", "⚙️ Instellingen"])


# ── Tab: Afbeeldingen genereren ──────────────────────────────────────────────

with tab_generate:
    post_tabs = _load_post_tabs(spreadsheet_id, sa_json)

    if not post_tabs:
        st.info("Geen 'Posts_*'-tabbladen gevonden in de Sheet.")
    else:
        selected_tab = st.selectbox(
            "Week",
            post_tabs,
            format_func=_format_tab_label,
        )

        rows = _load_rows(selected_tab, spreadsheet_id, sa_json)
        clients_basic = _load_clients_basic(spreadsheet_id, sa_json)
        settings = _load_client_settings(spreadsheet_id, sa_json)
        photo_index = _load_photo_index(spreadsheet_id, sa_json)
        tasks = _load_tasks(spreadsheet_id, sa_json)

        def _find_task(tab_name, row_idx):
            for task in tasks:
                if str(task.get("tab_name", "")) == str(tab_name) and str(task.get("row_index", "")) == str(row_idx):
                    return task
            return None

        nodig = [r for r in rows if r["_beeld_status"] == "nodig"]
        klaar = [r for r in rows if r["_beeld_status"] == "klaar"]
        totaal = len(nodig) + len(klaar)

        if totaal == 0:
            st.info("Geen goedgekeurde posts in dit tabblad.")
        else:
            st.markdown(
                f"<p style='font-size:13px;color:var(--ink2);margin-bottom:18px;'>"
                f"{len(klaar)} van {totaal} goedgekeurde posts hebben al een afbeelding</p>",
                unsafe_allow_html=True,
            )

        # Groepeer "nodig"-rijen per klant
        by_client = {}
        for row in nodig:
            by_client.setdefault(row.get("klant_id", ""), []).append(row)

        for klant_id, klant_rows in by_client.items():
            client_info = clients_basic.get(klant_id, {})
            bedrijfsnaam = client_info.get("bedrijfsnaam", klant_id)
            client_settings_row = settings.get(klant_id, {})
            foto_map = client_settings_row.get("foto_map", "")
            template_pad = client_settings_row.get("template_pad", "")

            st.markdown(f"### {bedrijfsnaam}")

            if not foto_map or not template_pad:
                st.warning(
                    f"Geen foto-map en/of template ingesteld voor **{bedrijfsnaam}** — "
                    f"stel dit in via het tabblad ⚙️ Instellingen."
                )

            for row in klant_rows:
                row_idx = row["_row_index"]
                platform = row.get("platform", "")
                color = PLATFORM_COLORS.get(platform, "#999")
                badge = PLATFORM_LABELS.get(platform, platform.upper())

                with st.container(border=True):
                    col_post, col_photo, col_action = st.columns([4, 3, 3])

                    with col_post:
                        st.markdown(
                            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
                            f'width:20px;height:20px;border-radius:6px;background:{color};color:#fff;'
                            f'font-size:9px;font-weight:800;margin-right:7px;">{badge}</span>'
                            f'<b>{row.get("dag", "")}</b> — {row.get("publicatiedatum", "")}',
                            unsafe_allow_html=True,
                        )
                        if row.get("beeldtitel"):
                            st.caption(f"🖼️ {row['beeldtitel']}")
                        caption_preview = (row.get("caption", "") or "")[:200]
                        st.caption(caption_preview)

                    foto_choices = photo_index.get(klant_id, [])
                    task = _find_task(selected_tab, row_idx)
                    task_status = str(task.get("status", "")).strip() if task else ""

                    gekozen_foto = None
                    with col_photo:
                        if not foto_choices:
                            st.caption(
                                "Geen foto's geïndexeerd voor deze klant. Run de "
                                "lokale worker (`python systems/run_worker.py`)."
                            )
                        else:
                            gekozen_foto = st.selectbox(
                                "Foto",
                                foto_choices,
                                key=f"photo_{selected_tab}_{row_idx}",
                                label_visibility="collapsed",
                            )

                    with col_action:
                        if not template_pad:
                            st.caption("⚠️ Geen template ingesteld voor deze klant.")

                        if not row.get("beeldtitel"):
                            st.caption("⚠️ Geen beeldtitel ingevuld voor deze post.")

                        if task_status in (task_queue.STATUS_WACHTEND, task_queue.STATUS_BEZIG):
                            st.info(
                                "⏳ Wordt verwerkt door de lokale agent "
                                "(`python systems/run_worker.py`)."
                            )
                        elif task_status == task_queue.STATUS_KLAAR:
                            st.info("⏳ Bijna klaar — wachten op koppeling met de Planning-tab.")
                        else:
                            if task_status == task_queue.STATUS_FOUT:
                                st.error(f"Vorige poging mislukt: {task.get('log', '')}")
                            label = "🔁 Opnieuw proberen" if task_status == task_queue.STATUS_FOUT else "🪄 Vraag generatie aan"

                            request_disabled = not (
                                gekozen_foto and template_pad and row.get("beeldtitel")
                            )
                            if st.button(
                                label,
                                key=f"req_{selected_tab}_{row_idx}",
                                disabled=request_disabled,
                                type="primary",
                                use_container_width=True,
                            ):
                                task_queue.upsert_task(
                                    spreadsheet_id, sa_json,
                                    selected_tab, row_idx, klant_id,
                                    row.get("beeldtitel", ""), gekozen_foto,
                                )
                                _load_tasks.clear()
                                st.success("Aangevraagd — wordt opgepakt door de lokale agent.")
                                st.rerun()

        for row in klaar:
            st.markdown(f"✅ {row.get('beeldtitel', '(geen beeldtitel)')} — al gekoppeld")


# ── Tab: Instellingen ─────────────────────────────────────────────────────────

with tab_settings:
    st.markdown("### Foto-mappen en templates per klant")
    st.caption(
        "Stel per klant in waar de bronfoto's staan en welk InDesign-template "
        "(.indd/.indt) gebruikt moet worden. Wordt opgeslagen in de "
        "'Beeld_Config'-tab van de gedeelde Sheet."
    )

    clients_basic = _load_clients_basic(spreadsheet_id, sa_json)
    settings = _load_client_settings(spreadsheet_id, sa_json)
    photo_index = _load_photo_index(spreadsheet_id, sa_json)

    new_settings = {}
    for klant_id, info in clients_basic.items():
        bedrijfsnaam = info.get("bedrijfsnaam", klant_id)
        current = settings.get(klant_id, {})

        with st.container(border=True):
            st.markdown(f"**{bedrijfsnaam}** ({klant_id})")
            col1, col2 = st.columns(2)
            with col1:
                foto_map = st.text_input(
                    "Foto-map (lokaal pad voor de worker)",
                    value=current.get("foto_map", ""),
                    key=f"foto_map_{klant_id}",
                )
                n_photos = len(photo_index.get(klant_id, []))
                st.caption(f"📂 Laatst geïndexeerd door de worker: {n_photos} foto('s)")
            with col2:
                template_pad = st.text_input(
                    "InDesign-template (.indd/.indt, lokaal pad voor de worker)",
                    value=current.get("template_pad", ""),
                    key=f"template_pad_{klant_id}",
                )

        new_settings[klant_id] = {"foto_map": foto_map, "template_pad": template_pad}

    if st.button("Opslaan", type="primary"):
        client_settings.save_client_settings(spreadsheet_id, sa_json, new_settings)
        _load_client_settings.clear()
        st.success("Instellingen opgeslagen.")
        st.rerun()
