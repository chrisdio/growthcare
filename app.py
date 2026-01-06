#!/usr/bin/env python3
"""
DigiMV Prospect Tool - Cloud Versie (Volledige Features)
=========================================================
Identieke functionaliteit als de lokale versie, maar draait in de cloud.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io
import hashlib
from typing import Optional

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Primio Prospect Tool",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CONFIGURATIE
# ============================================================================
FTE_MIN_OMZET_PER_FTE = 20000
FTE_MAX_OMZET_PER_FTE = 100000
SHEETS_NEEDED = ['RowData_01', 'RowData_09', 'RowData_10', 'RowData_15', 'RowData_16']

# ============================================================================
# STYLING
# ============================================================================
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1E3A5F; margin-bottom: 0; }
    .sub-header { font-size: 1rem; color: #666; margin-top: 0; }
    .warning-badge { background-color: #fff3cd; color: #856404; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
    .success-badge { background-color: #d4edda; color: #155724; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PROVINCIE MAPPING
# ============================================================================
PROVINCIE_FALLBACK = {
    "10": "Noord-Holland", "11": "Noord-Holland", "12": "Noord-Holland", "13": "Noord-Holland", "14": "Noord-Holland", "15": "Noord-Holland",
    "16": "Flevoland", "17": "Noord-Holland", "18": "Noord-Holland", "19": "Noord-Holland",
    "20": "Zuid-Holland", "21": "Zuid-Holland", "22": "Zuid-Holland", "23": "Zuid-Holland", "24": "Zuid-Holland",
    "25": "Zuid-Holland", "26": "Zuid-Holland", "27": "Zuid-Holland",
    "28": "Utrecht", "29": "Utrecht", "30": "Utrecht", "31": "Utrecht", "32": "Utrecht", "33": "Utrecht", "34": "Utrecht", "35": "Utrecht", "36": "Utrecht", "37": "Utrecht", "38": "Utrecht",
    "39": "Gelderland", "40": "Gelderland", "41": "Gelderland",
    "42": "Noord-Brabant", "43": "Noord-Brabant", "44": "Noord-Brabant", "45": "Noord-Brabant", "46": "Zeeland", "47": "Zeeland", "48": "Noord-Brabant",
    "49": "Noord-Brabant", "50": "Noord-Brabant", "51": "Noord-Brabant", "52": "Noord-Brabant", "53": "Noord-Brabant",
    "54": "Limburg", "55": "Limburg", "56": "Limburg", "57": "Limburg", "58": "Limburg", "59": "Limburg", "60": "Limburg", "61": "Limburg", "62": "Limburg", "63": "Limburg",
    "64": "Gelderland", "65": "Gelderland", "66": "Gelderland", "67": "Gelderland", "68": "Gelderland", "69": "Gelderland", "70": "Gelderland",
    "71": "Overijssel", "72": "Overijssel", "73": "Overijssel", "74": "Overijssel", "75": "Overijssel", "76": "Overijssel", "77": "Overijssel", "78": "Overijssel", "79": "Drenthe", "80": "Overijssel",
    "81": "Flevoland", "82": "Flevoland",
    "83": "Friesland", "84": "Friesland", "85": "Friesland", "86": "Friesland", "87": "Friesland", "88": "Friesland", "89": "Friesland",
    "90": "Groningen", "91": "Drenthe", "92": "Drenthe", "93": "Drenthe", "94": "Drenthe", "95": "Groningen", "96": "Groningen", "97": "Groningen", "98": "Groningen", "99": "Groningen",
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def find_column(df: pd.DataFrame, possible_names: list) -> Optional[str]:
    df_cols_lower = {c.lower(): c for c in df.columns}
    for name in possible_names:
        if name.lower() in df_cols_lower:
            return df_cols_lower[name.lower()]
    return None

def ja_nee_to_bool(value) -> Optional[bool]:
    if pd.isna(value): return None
    val_str = str(value).strip().lower()
    if val_str == 'ja': return True
    elif val_str == 'nee': return False
    return None

@st.cache_data
def load_nederland_csv(file_content: bytes) -> tuple:
    try:
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(io.BytesIO(file_content), sep=';', encoding=encoding, dtype=str)
                break
            except: continue
        
        pc_col = find_column(df, ['postcode', 'postal_code', 'pc'])
        lat_col = find_column(df, ['lat', 'latitude'])
        lon_col = find_column(df, ['lon', 'lng', 'longitude'])
        prov_col = find_column(df, ['provincie', 'province'])
        
        provincie_map, coords_map = {}, {}
        
        if pc_col:
            if lat_col and lon_col:
                df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
                df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
            
            for _, row in df.iterrows():
                pc = str(row[pc_col]).strip().replace(' ', '').upper()
                digits = ''.join(c for c in pc if c.isdigit())
                if len(digits) >= 4:
                    pc4 = digits[:4]
                    if prov_col and pc4 not in provincie_map:
                        prov = str(row[prov_col]).strip()
                        if prov and prov != 'nan': provincie_map[pc4] = prov
                    if lat_col and lon_col and pc4 not in coords_map:
                        lat, lon = row[lat_col], row[lon_col]
                        if pd.notna(lat) and pd.notna(lon): coords_map[pc4] = (float(lat), float(lon))
        return provincie_map, coords_map
    except Exception as e:
        st.error(f"Fout Nederland.csv: {e}")
        return {}, {}

def get_provincie(postcode, pc4_map: dict) -> Optional[str]:
    if pd.isna(postcode): return None
    pc_str = str(postcode).strip().replace(' ', '').upper()
    digits = ''.join(c for c in pc_str if c.isdigit())
    if len(digits) >= 4 and digits[:4] in pc4_map: return pc4_map[digits[:4]]
    if len(digits) >= 2: return PROVINCIE_FALLBACK.get(digits[:2])
    return None

def get_coords(postcode, coords_map: dict) -> tuple:
    if pd.isna(postcode): return None, None
    pc_str = str(postcode).strip().replace(' ', '').upper()
    digits = ''.join(c for c in pc_str if c.isdigit())
    if len(digits) >= 4 and digits[:4] in coords_map: return coords_map[digits[:4]]
    if len(digits) >= 2:
        pc2 = digits[:2]
        hash_val = int(hashlib.md5(digits[:4].encode() if len(digits)>=4 else pc2.encode()).hexdigest()[:4], 16)
        base = {"10":(52.37,4.90),"20":(52.08,4.31),"30":(52.09,5.12),"40":(51.84,5.85),"50":(51.44,5.47),
                "60":(50.85,5.70),"70":(52.22,6.89),"80":(52.51,6.09),"90":(53.22,6.57)}.get(pc2[0]+"0",(52.1,5.3))
        return (base[0]+((hash_val%100)-50)*0.003, base[1]+(((hash_val>>8)%100)-50)*0.004)
    return None, None

def add_fte_reliability(df: pd.DataFrame) -> pd.DataFrame:
    def check(row):
        omzet, fte = row.get('Omzet_Totaal'), row.get('FTE_Totaal')
        if pd.isna(omzet) or pd.isna(fte) or fte == 0: return None
        ratio = omzet / fte
        return FTE_MIN_OMZET_PER_FTE <= ratio <= FTE_MAX_OMZET_PER_FTE
    if 'FTE_Betrouwbaar' not in df.columns:
        df['FTE_Betrouwbaar'] = df.apply(check, axis=1)
    return df

def add_coordinates(df: pd.DataFrame, coords_map: dict) -> pd.DataFrame:
    pc_col = find_column(df, ['Postcode', 'PostalCode', 'postcode'])
    if pc_col is None:
        df['lat'], df['lon'] = None, None
        return df
    coords = df[pc_col].apply(lambda pc: get_coords(pc, coords_map))
    df['lat'] = coords.apply(lambda x: x[0] if x else None)
    df['lon'] = coords.apply(lambda x: x[1] if x else None)
    return df

# ============================================================================
# MASTER CREATOR
# ============================================================================

def load_digimv_parts(uploaded_files: list) -> list:
    all_parts = []
    for i, f in enumerate(uploaded_files, 1):
        if f is None: continue
        try:
            xl = pd.ExcelFile(f)
            part_data = {'_part_number': i}
            for sheet in SHEETS_NEEDED:
                if sheet in xl.sheet_names:
                    part_data[sheet] = pd.read_excel(xl, sheet_name=sheet)
            all_parts.append(part_data)
        except Exception as e:
            st.warning(f"Fout Part {i}: {e}")
    return all_parts

def create_master_database(parts: list, provincie_map: dict) -> pd.DataFrame:
    all_rows = []
    for part_data in parts:
        part_num = part_data.get('_part_number', 0)
        if 'RowData_01' not in part_data: continue
        base_df = part_data['RowData_01'].copy()
        for sheet_name in SHEETS_NEEDED[1:]:
            if sheet_name in part_data:
                sheet_df = part_data[sheet_name]
                if 'Code' in sheet_df.columns:
                    new_cols = [c for c in sheet_df.columns if c != 'Code' and c not in base_df.columns]
                    if new_cols: base_df = base_df.merge(sheet_df[['Code'] + new_cols], on='Code', how='left')
        
        for _, row in base_df.iterrows():
            output_row = {
                'Bron_Part': part_num, 'Code': row.get('Code'), 'Naam': row.get('Name'), 'KVK': row.get('qNawKvk'),
                'Straat': row.get('Street'), 'Huisnummer': row.get('HouseNumber'),
                'Postcode': row.get('PostalCode'), 'Plaats': row.get('Town'),
                'Is_VVT': ja_nee_to_bool(row.get('qTypeWTZaZorg_13')), 'Is_GGZ': ja_nee_to_bool(row.get('qTypeWTZaZorg_8')),
                'Is_GHZ': ja_nee_to_bool(row.get('qTypeWTZaZorg_10')), 'Is_MSI': ja_nee_to_bool(row.get('qTypeWTZaZorg_6')),
                'VVT_Wijkverpleging': ja_nee_to_bool(row.get('qTypeWTZaZorgVenV_3')),
                'VVT_Verpleeghuiszorg': ja_nee_to_bool(row.get('qTypeWTZaZorgVenV_4')),
                'VVT_GRZ': ja_nee_to_bool(row.get('qTypeWTZaZorgVenV_5')),
                'Omzet_Totaal': row.get('qTotaalBaten_0'), 'Omzet_Vorig_Jaar': row.get('qTotaalBaten_1'),
                'Omzet_ZVW': row.get('qBatenZorgZvw_0'), 'Omzet_WLZ': row.get('qBatenZorgWlz_0'), 'Omzet_WMO': row.get('qBatenZorgWmo_0'),
                'FTE_Totaal': row.get('qPersTotTot_AantalFte'), 'FTE_Zorgpersoneel': row.get('qPersTotZorg_AantalFte'),
                'Verzuim_Pct': row.get('qPersVerzuimPct_0'), 'Vacatures': row.get('qPersVacatures_0'),
            }
            output_row['Provincie'] = get_provincie(output_row.get('Postcode'), provincie_map)
            all_rows.append(output_row)
    
    df = pd.DataFrame(all_rows)
    type_cols = ['Is_VVT', 'Is_GGZ', 'Is_GHZ', 'Is_MSI']
    existing = [c for c in type_cols if c in df.columns]
    if existing: df = df[df[existing].any(axis=1)]
    if 'Omzet_Totaal' in df.columns: df = df.sort_values('Omzet_Totaal', ascending=False, na_position='last')
    return df.reset_index(drop=True)

# ============================================================================
# FILTER
# ============================================================================

def filter_data(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    result = df.copy()
    if filters.get('search'):
        search = filters['search'].lower()
        mask = pd.Series([False] * len(result))
        for col in ['Naam', 'Name', 'Plaats', 'Town', 'KVK', 'Code']:
            if col in result.columns: mask |= result[col].astype(str).str.lower().str.contains(search, na=False)
        result = result[mask]
    if filters.get('types'):
        existing = [c for c in filters['types'] if c in result.columns]
        if existing: result = result[result[existing].any(axis=1)]
    prov_col = find_column(result, ['Provincie', 'Province'])
    if filters.get('provincies') and prov_col: result = result[result[prov_col].isin(filters['provincies'])]
    omzet_col = find_column(result, ['Omzet_Totaal', 'Omzet'])
    if omzet_col:
        if filters.get('omzet_min'): result = result[pd.to_numeric(result[omzet_col], errors='coerce') >= filters['omzet_min']]
        if filters.get('omzet_max'): result = result[pd.to_numeric(result[omzet_col], errors='coerce') <= filters['omzet_max']]
    fte_col = find_column(result, ['FTE_Totaal', 'FTE'])
    if fte_col:
        if filters.get('fte_min') is not None: result = result[pd.to_numeric(result[fte_col], errors='coerce') >= filters['fte_min']]
        if filters.get('fte_max') is not None: result = result[pd.to_numeric(result[fte_col], errors='coerce') <= filters['fte_max']]
        if filters.get('only_with_fte'): result = result[pd.to_numeric(result[fte_col], errors='coerce') > 0]
    return result

# ============================================================================
# KAART (Plotly)
# ============================================================================

def create_map(df: pd.DataFrame, selected_code: str = None) -> go.Figure:
    df_map = df.dropna(subset=['lat', 'lon']).head(500).copy()
    if df_map.empty: return None
    
    def get_type(row):
        if row.get('Is_VVT') == True: return 'VVT'
        if row.get('Is_GGZ') == True: return 'GGZ'
        if row.get('Is_GHZ') == True: return 'GHZ'
        if row.get('Is_MSI') == True: return 'MSI'
        return 'Anders'
    
    df_map['Type'] = df_map.apply(get_type, axis=1)
    omzet_col = find_column(df_map, ['Omzet_Totaal', 'Omzet'])
    df_map['Omzet_M'] = pd.to_numeric(df_map[omzet_col], errors='coerce').fillna(0) / 1_000_000 if omzet_col else 1
    df_map['size'] = df_map['Omzet_M'].apply(lambda x: max(8, min(35, 8 + x / 5)))
    if selected_code and 'Code' in df_map.columns: df_map.loc[df_map['Code'] == selected_code, 'size'] = 50
    
    naam_col = find_column(df_map, ['Naam', 'Name'])
    df_map['display_name'] = df_map[naam_col] if naam_col else 'Onbekend'
    plaats_col = find_column(df_map, ['Plaats', 'Town'])
    df_map['Plaats_display'] = df_map[plaats_col].fillna('') if plaats_col else ''
    
    fig = px.scatter_mapbox(df_map, lat='lat', lon='lon', color='Type', size='size',
        custom_data=['Code'] if 'Code' in df_map.columns else None,
        hover_name='display_name',
        hover_data={'lat': False, 'lon': False, 'size': False, 'Type': True, 'Omzet_M': ':.1f', 'Plaats_display': True},
        color_discrete_map={'VVT': '#1f77b4', 'GGZ': '#2ca02c', 'GHZ': '#ff7f0e', 'MSI': '#d62728', 'Anders': '#7f7f7f'},
        zoom=6, center={'lat': 52.1, 'lon': 5.3}, mapbox_style='carto-positron')
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# ============================================================================
# OMZET CHART
# ============================================================================

def create_omzet_chart(row: pd.Series) -> go.Figure:
    labels, values = [], []
    for lbl, col in [('ZVW','Omzet_ZVW'),('WLZ','Omzet_WLZ'),('WMO','Omzet_WMO')]:
        if pd.notna(row.get(col)) and row.get(col, 0) > 0:
            labels.append(lbl); values.append(row[col])
    if not values: return None
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker_colors=['#667eea','#764ba2','#f093fb'])])
    fig.update_layout(showlegend=True, height=200, margin=dict(l=20,r=20,t=20,b=20))
    return fig

# ============================================================================
# DETAIL PANEL
# ============================================================================

def show_detail_panel(org: pd.Series):
    naam = org.get('Naam') or org.get('Name') or 'Onbekend'
    st.markdown(f"## {naam}")
    st.markdown(f"📍 {org.get('Straat','')} {org.get('Huisnummer','')}, {org.get('Postcode','')} {org.get('Plaats') or org.get('Town') or ''}")
    
    types = [t for t,c in [('VVT','Is_VVT'),('GGZ','Is_GGZ'),('GHZ','Is_GHZ'),('MSI','Is_MSI')] if org.get(c)==True]
    st.markdown(f"**Type:** {', '.join(types) if types else 'Onbekend'}")
    
    fte_b = org.get('FTE_Betrouwbaar')
    if fte_b == False: st.markdown('<span class="warning-badge">⚠️ FTE mogelijk onbetrouwbaar</span>', unsafe_allow_html=True)
    elif fte_b == True: st.markdown('<span class="success-badge">✅ FTE betrouwbaar</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    tabs = st.tabs(["📊 Overzicht", "💰 Financieel", "👥 Personeel"])
    
    with tabs[0]:
        st.markdown(f"- **KVK:** {org.get('KVK', '-')}")
        st.markdown(f"- **Code:** {org.get('Code', '-')}")
        st.markdown(f"- **Provincie:** {org.get('Provincie', '-')}")
        if org.get('Is_VVT') == True:
            vvt = [t for t,c in [('Wijkverpleging','VVT_Wijkverpleging'),('Verpleeghuiszorg','VVT_Verpleeghuiszorg'),('GRZ','VVT_GRZ')] if org.get(c)==True]
            if vvt: st.markdown(f"**VVT:** {', '.join(vvt)}")
    
    with tabs[1]:
        omzet = org.get('Omzet_Totaal')
        if pd.notna(omzet):
            st.metric("Totale Omzet", f"€{omzet/1_000_000:.1f}M")
            omzet_vj = org.get('Omzet_Vorig_Jaar')
            if pd.notna(omzet_vj) and omzet_vj > 0:
                st.metric("Groei", f"{((omzet-omzet_vj)/omzet_vj)*100:+.1f}%")
            fig = create_omzet_chart(org)
            if fig: st.plotly_chart(fig, use_container_width=True)
            for lbl,col in [("ZVW","Omzet_ZVW"),("WLZ","Omzet_WLZ"),("WMO","Omzet_WMO")]:
                val = org.get(col)
                st.markdown(f"- {lbl}: €{val/1_000_000:.1f}M" if pd.notna(val) else f"- {lbl}: -")
        else: st.info("Geen omzet data")
    
    with tabs[2]:
        fte = org.get('FTE_Totaal')
        if pd.notna(fte):
            st.metric("Totaal FTE", f"{fte:,.0f}")
            omzet = org.get('Omzet_Totaal')
            if pd.notna(omzet) and fte > 0:
                ratio = omzet / fte
                st.markdown(f"**Omzet/FTE:** €{ratio:,.0f}")
                if ratio < FTE_MIN_OMZET_PER_FTE or ratio > FTE_MAX_OMZET_PER_FTE: st.caption("⚠️ Buiten normale range")
            for lbl,col in [("Zorgpersoneel","FTE_Zorgpersoneel")]:
                val = org.get(col)
                if pd.notna(val): st.markdown(f"- {lbl}: {val:,.0f}")
            verzuim = org.get('Verzuim_Pct')
            if pd.notna(verzuim): st.markdown(f"- Verzuim: {verzuim:.1f}%")
        else: st.info("Geen FTE data")

# ============================================================================
# MAIN
# ============================================================================

def main():
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown('<p class="main-header">🏥 Primio Prospect Tool</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">DigiMV Zorgorganisaties Analyse</p>', unsafe_allow_html=True)
    
    for key in ['master_df', 'selected_org', 'provincie_map', 'coords_map']:
        if key not in st.session_state:
            st.session_state[key] = None if key in ['master_df', 'selected_org'] else {}
    
    # SIDEBAR: Data laden
    st.sidebar.markdown("## 📁 Data Laden")
    data_mode = st.sidebar.radio("Bron:", ["📊 Master Excel", "📤 DigiMV Parts"])
    
    st.sidebar.markdown("### 🗺️ Nederland.csv")
    nederland_file = st.sidebar.file_uploader("Voor kaart", type=['csv'], key='nl')
    if nederland_file:
        prov_map, coords_map = load_nederland_csv(nederland_file.read())
        st.session_state.provincie_map, st.session_state.coords_map = prov_map, coords_map
        st.sidebar.success(f"✅ {len(coords_map)} postcodes")
    
    st.sidebar.markdown("---")
    
    if data_mode == "📊 Master Excel":
        master_file = st.sidebar.file_uploader("Master Database", type=['xlsx','xls'], key='master')
        if master_file:
            df = pd.read_excel(master_file)
            df = add_fte_reliability(add_coordinates(df, st.session_state.coords_map))
            st.session_state.master_df = df
            st.sidebar.success(f"✅ {len(df)} organisaties")
    else:
        st.sidebar.markdown("### DigiMV Parts")
        parts = [st.sidebar.file_uploader(f"Part {i}", type=['xls','xlsx'], key=f'p{i}') for i in [1,2,3]]
        parts = [p for p in parts if p]
        if parts and st.sidebar.button("🔄 Genereer", type="primary"):
            with st.spinner("Verwerken..."):
                loaded = load_digimv_parts(parts)
                if loaded:
                    df = create_master_database(loaded, st.session_state.provincie_map)
                    df = add_fte_reliability(add_coordinates(df, st.session_state.coords_map))
                    st.session_state.master_df = df
                    st.sidebar.success(f"✅ {len(df)} organisaties")
    
    if st.session_state.master_df is None:
        st.info("👈 Upload bestanden om te beginnen")
        return
    
    df = st.session_state.master_df
    
    # FILTERS
    st.sidebar.markdown("## 🔍 Filters")
    filters = {'search': st.sidebar.text_input("🔎 Zoek", placeholder="Naam, KVK...")}
    
    st.sidebar.markdown("### Type")
    type_cols = ['Is_VVT', 'Is_GGZ', 'Is_GHZ', 'Is_MSI']
    filters['types'] = [c for c in type_cols if c in df.columns and st.sidebar.checkbox(
        f"{c.replace('Is_','')} ({int(df[c].sum()) if df[c].dtype==bool else 0})", value=True, key=f"t_{c}")]
    
    prov_col = find_column(df, ['Provincie'])
    if prov_col:
        provincies = sorted([p for p in df[prov_col].dropna().unique() if p])
        filters['provincies'] = st.sidebar.multiselect("📍 Provincie", provincies)
    
    st.sidebar.markdown("### 💰 Omzet (€M)")
    c1, c2 = st.sidebar.columns(2)
    omzet_min = c1.number_input("Min", min_value=0.0, value=0.0, step=1.0, key="om_min")
    omzet_max = c2.number_input("Max", min_value=0.0, value=0.0, step=1.0, key="om_max")
    filters['omzet_min'] = omzet_min * 1e6 if omzet_min > 0 else None
    filters['omzet_max'] = omzet_max * 1e6 if omzet_max > 0 else None
    
    st.sidebar.markdown("### 👥 FTE")
    fte_cat = st.sidebar.selectbox("Categorie", ["Alle","<50","50-150","150-500","500-1500",">1500"])
    filters['fte_min'], filters['fte_max'] = {"Alle":(None,None),"<50":(0,50),"50-150":(50,150),"150-500":(150,500),"500-1500":(500,1500),">1500":(1500,None)}[fte_cat]
    filters['only_with_fte'] = st.sidebar.checkbox("Alleen met FTE")
    
    if st.sidebar.button("🔄 Reset"): st.rerun()
    
    filtered_df = filter_data(df, filters)
    
    # METRICS
    st.markdown("---")
    mc = st.columns(4)
    mc[0].metric("📊 Organisaties", f"{len(filtered_df):,}")
    omzet_col = find_column(filtered_df, ['Omzet_Totaal'])
    if omzet_col: mc[1].metric("💰 Omzet", f"€{pd.to_numeric(filtered_df[omzet_col],errors='coerce').sum()/1e9:.1f}B")
    fte_col = find_column(filtered_df, ['FTE_Totaal'])
    if fte_col: mc[2].metric("👥 FTE", f"{pd.to_numeric(filtered_df[fte_col],errors='coerce').sum():,.0f}")
    if 'FTE_Betrouwbaar' in filtered_df.columns: mc[3].metric("⚠️ Onbetrouwbaar", f"{(filtered_df['FTE_Betrouwbaar']==False).sum()}")
    
    with col_h2:
        output = io.BytesIO(); filtered_df.to_excel(output, index=False)
        st.download_button("💾 Export", data=output.getvalue(), file_name=f"Export_{datetime.now().strftime('%Y%m%d')}.xlsx")
    
    # MAIN CONTENT
    st.markdown("---")
    col_main, col_det = st.columns([2, 1])
    
    with col_main:
        st.markdown("### 🗺️ Kaart")
        if len(filtered_df) > 0 and 'lat' in filtered_df.columns and filtered_df['lat'].notna().any():
            map_df = filtered_df.head(500)
            if len(filtered_df) > 500: st.warning(f"Toont 500/{len(filtered_df)}")
            fig = create_map(map_df, st.session_state.selected_org)
            if fig:
                sel = st.plotly_chart(fig, use_container_width=True, key="map", on_select="rerun")
                if sel and sel.selection and sel.selection.points:
                    pt = sel.selection.points[0]
                    if 'customdata' in pt and pt['customdata']:
                        code = pt['customdata'][0]
                        if code != st.session_state.selected_org:
                            st.session_state.selected_org = code; st.rerun()
            st.caption("🔵VVT 🟢GGZ 🟠GHZ 🔴MSI — Klik voor details")
        else: st.info("Upload Nederland.csv voor kaart")
        
        st.markdown("---")
        st.markdown("### 📋 Tabel")
        if len(filtered_df) > 0:
            disp_cols = [c for c in ['Code','Naam','Name','Plaats','Town','Omzet_Totaal','FTE_Totaal','FTE_Betrouwbaar'] if c in filtered_df.columns]
            disp_df = filtered_df[disp_cols].copy()
            if 'Omzet_Totaal' in disp_df.columns: disp_df['Omzet_Totaal'] = disp_df['Omzet_Totaal'].apply(lambda x: f"€{x/1e6:.1f}M" if pd.notna(x) else "-")
            if 'FTE_Totaal' in disp_df.columns: disp_df['FTE_Totaal'] = disp_df['FTE_Totaal'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")
            if 'FTE_Betrouwbaar' in disp_df.columns: disp_df['FTE_Betrouwbaar'] = disp_df['FTE_Betrouwbaar'].apply(lambda x: "✅" if x==True else "⚠️" if x==False else "-")
            
            sel = st.dataframe(disp_df, use_container_width=True, height=300, hide_index=True, on_select="rerun", selection_mode="single-row")
            if sel and sel.selection and sel.selection.rows:
                idx = sel.selection.rows[0]
                if 'Code' in filtered_df.columns:
                    code = filtered_df.iloc[idx]['Code']
                    if code != st.session_state.selected_org:
                        st.session_state.selected_org = code; st.rerun()
    
    with col_det:
        st.markdown("### 📄 Details")
        if st.session_state.selected_org:
            org_df = filtered_df[filtered_df['Code'] == st.session_state.selected_org] if 'Code' in filtered_df.columns else pd.DataFrame()
            if len(org_df) > 0: show_detail_panel(org_df.iloc[0])
            else:
                st.info("Niet in filter")
                if st.button("❌ Deselecteren"): st.session_state.selected_org = None; st.rerun()
        else: st.info("👆 Klik op een organisatie")

if __name__ == "__main__":
    main()
