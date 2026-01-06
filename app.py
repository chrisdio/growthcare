#!/usr/bin/env python3
"""
DigiMV Prospect Tool - Cloud Versie
===================================
Complete tool voor het analyseren van DigiMV zorgorganisaties.
Draait volledig in de browser via Streamlit Cloud.

Features:
- Upload DigiMV bronbestanden (Part 1, 2, 3)
- Upload Nederland.csv voor provincie/coördinaten
- Genereer Master Database
- Interactieve kaart en tabel
- Export naar Excel
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from datetime import datetime
import io
import hashlib
from typing import Optional, Any

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="DigiMV Prospect Tool",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CONFIGURATIE
# ============================================================================
FTE_MIN_OMZET_PER_FTE = 20000
FTE_MAX_OMZET_PER_FTE = 100000

# Kolom configuratie voor Master Creator
COLUMN_CONFIG = {
    'basis': [
        {'output': 'Code', 'sheet': 'RowData_01', 'col': 'Code'},
        {'output': 'Naam', 'sheet': 'RowData_01', 'col': 'Name'},
        {'output': 'KVK', 'sheet': 'RowData_01', 'col': 'qNawKvk'},
        {'output': 'Straat', 'sheet': 'RowData_01', 'col': 'Street'},
        {'output': 'Huisnummer', 'sheet': 'RowData_01', 'col': 'HouseNumber'},
        {'output': 'Postcode', 'sheet': 'RowData_01', 'col': 'PostalCode'},
        {'output': 'Plaats', 'sheet': 'RowData_01', 'col': 'Town'},
    ],
    'type': [
        {'output': 'Is_VVT', 'sheet': 'RowData_09', 'col': 'qTypeWTZaZorg_13', 'transform': 'ja_nee'},
        {'output': 'Is_GGZ', 'sheet': 'RowData_09', 'col': 'qTypeWTZaZorg_8', 'transform': 'ja_nee'},
        {'output': 'Is_GHZ', 'sheet': 'RowData_09', 'col': 'qTypeWTZaZorg_10', 'transform': 'ja_nee'},
        {'output': 'Is_MSI', 'sheet': 'RowData_09', 'col': 'qTypeWTZaZorg_6', 'transform': 'ja_nee'},
        {'output': 'VVT_Wijkverpleging', 'sheet': 'RowData_09', 'col': 'qTypeWTZaZorgVenV_3', 'transform': 'ja_nee'},
        {'output': 'VVT_Verpleeghuiszorg', 'sheet': 'RowData_09', 'col': 'qTypeWTZaZorgVenV_4', 'transform': 'ja_nee'},
        {'output': 'VVT_Crisiszorg', 'sheet': 'RowData_09', 'col': 'qTypeWTZaZorgVenV_2', 'transform': 'ja_nee'},
        {'output': 'VVT_GRZ', 'sheet': 'RowData_09', 'col': 'qTypeWTZaZorgVenV_5', 'transform': 'ja_nee'},
    ],
    'financieel': [
        {'output': 'Omzet_Totaal', 'sheet': 'RowData_10', 'col': 'qTotaalBaten_0'},
        {'output': 'Omzet_Vorig_Jaar', 'sheet': 'RowData_10', 'col': 'qTotaalBaten_1'},
        {'output': 'Omzet_ZVW', 'sheet': 'RowData_10', 'col': 'qBatenZorgZvw_0'},
        {'output': 'Omzet_WLZ', 'sheet': 'RowData_10', 'col': 'qBatenZorgWlz_0'},
        {'output': 'Omzet_WMO', 'sheet': 'RowData_10', 'col': 'qBatenZorgWmo_0'},
    ],
    'personeel': [
        {'output': 'FTE_Totaal', 'sheet': 'RowData_15', 'col': 'qPersTotTot_AantalFte'},
        {'output': 'FTE_Zorgpersoneel', 'sheet': 'RowData_15', 'col': 'qPersTotZorg_AantalFte'},
        {'output': 'Verzuim_Pct', 'sheet': 'RowData_16', 'col': 'qPersVerzuimPct_0'},
        {'output': 'Vacatures', 'sheet': 'RowData_16', 'col': 'qPersVacatures_0'},
    ],
}

SHEETS_NEEDED = ['RowData_01', 'RowData_09', 'RowData_10', 'RowData_15', 'RowData_16']

PROVINCIE_FALLBACK = {
    "10": "Noord-Holland", "11": "Noord-Holland", "12": "Noord-Holland",
    "13": "Noord-Holland", "14": "Noord-Holland", "15": "Noord-Holland",
    "16": "Flevoland", "17": "Noord-Holland", "18": "Noord-Holland",
    "19": "Noord-Holland", "20": "Zuid-Holland", "21": "Zuid-Holland",
    "22": "Zuid-Holland", "23": "Zuid-Holland", "24": "Zuid-Holland",
    "25": "Zuid-Holland", "26": "Zuid-Holland", "27": "Zuid-Holland",
    "28": "Utrecht", "29": "Utrecht", "30": "Utrecht",
    "31": "Utrecht", "32": "Utrecht", "33": "Utrecht",
    "34": "Utrecht", "35": "Utrecht", "36": "Utrecht",
    "37": "Utrecht", "38": "Utrecht", "39": "Gelderland",
    "40": "Gelderland", "41": "Gelderland", "42": "Noord-Brabant",
    "43": "Noord-Brabant", "44": "Noord-Brabant", "45": "Noord-Brabant",
    "46": "Zeeland", "47": "Zeeland", "48": "Noord-Brabant",
    "49": "Noord-Brabant", "50": "Noord-Brabant", "51": "Noord-Brabant",
    "52": "Noord-Brabant", "53": "Noord-Brabant", "54": "Limburg",
    "55": "Limburg", "56": "Limburg", "57": "Limburg",
    "58": "Limburg", "59": "Limburg", "60": "Limburg",
    "61": "Limburg", "62": "Limburg", "63": "Limburg",
    "64": "Gelderland", "65": "Gelderland", "66": "Gelderland",
    "67": "Gelderland", "68": "Gelderland", "69": "Gelderland",
    "70": "Gelderland", "71": "Overijssel", "72": "Overijssel",
    "73": "Overijssel", "74": "Overijssel", "75": "Overijssel",
    "76": "Overijssel", "77": "Overijssel", "78": "Overijssel",
    "79": "Drenthe", "80": "Overijssel", "81": "Flevoland",
    "82": "Flevoland", "83": "Friesland", "84": "Friesland",
    "85": "Friesland", "86": "Friesland", "87": "Friesland",
    "88": "Friesland", "89": "Friesland", "90": "Groningen",
    "91": "Drenthe", "92": "Drenthe", "93": "Drenthe",
    "94": "Drenthe", "95": "Groningen", "96": "Groningen",
    "97": "Groningen", "98": "Groningen", "99": "Groningen",
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def ja_nee_to_bool(value) -> Optional[bool]:
    """Converteer ja/nee naar boolean."""
    if pd.isna(value):
        return None
    val_str = str(value).strip().lower()
    if val_str == 'ja':
        return True
    elif val_str == 'nee':
        return False
    return None

@st.cache_data
def load_nederland_csv(uploaded_file) -> tuple:
    """Laad Nederland.csv en retourneer (provincie_mapping, coords_mapping)."""
    if uploaded_file is None:
        return {}, {}
    
    try:
        # Reset file pointer
        uploaded_file.seek(0)
        
        # Probeer verschillende encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';', encoding=encoding, dtype=str)
                break
            except:
                continue
        
        # Zoek kolommen
        pc_col = lat_col = lon_col = prov_col = None
        for col in df.columns:
            col_lower = col.lower()
            if col_lower == 'postcode':
                pc_col = col
            elif col_lower == 'lat':
                lat_col = col
            elif col_lower == 'lon':
                lon_col = col
            elif col_lower == 'provincie':
                prov_col = col
        
        provincie_map = {}
        coords_map = {}
        
        if pc_col:
            if lat_col and lon_col:
                df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
                df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
            
            for _, row in df.iterrows():
                pc = str(row[pc_col]).strip().replace(' ', '').upper()
                digits = ''.join(c for c in pc if c.isdigit())
                
                if len(digits) >= 4:
                    pc4 = digits[:4]
                    
                    # Provincie
                    if prov_col and pc4 not in provincie_map:
                        prov = str(row[prov_col]).strip()
                        if prov and prov != 'nan':
                            provincie_map[pc4] = prov
                    
                    # Coördinaten
                    if lat_col and lon_col and pc4 not in coords_map:
                        lat = row[lat_col]
                        lon = row[lon_col]
                        if pd.notna(lat) and pd.notna(lon):
                            coords_map[pc4] = (float(lat), float(lon))
        
        return provincie_map, coords_map
    except Exception as e:
        st.error(f"Fout bij laden Nederland.csv: {e}")
        return {}, {}

def get_provincie(postcode: str, pc4_map: dict) -> Optional[str]:
    """Bepaal provincie op basis van postcode."""
    if pd.isna(postcode):
        return None
    
    pc_str = str(postcode).strip().replace(' ', '').upper()
    digits = ''.join(c for c in pc_str if c.isdigit())
    
    if len(digits) >= 4:
        pc4 = digits[:4]
        if pc4 in pc4_map:
            return pc4_map[pc4]
    
    if len(digits) >= 2:
        return PROVINCIE_FALLBACK.get(digits[:2])
    
    return None

def get_coords(postcode: str, coords_map: dict) -> tuple:
    """Haal coördinaten op basis van postcode."""
    if pd.isna(postcode):
        return None, None
    
    pc_str = str(postcode).strip().replace(' ', '').upper()
    digits = ''.join(c for c in pc_str if c.isdigit())
    
    if len(digits) >= 4:
        pc4 = digits[:4]
        if pc4 in coords_map:
            return coords_map[pc4]
    
    # Fallback naar regio centrum
    if len(digits) >= 2:
        pc2 = digits[:2]
        # Gebruik hash voor consistente maar gespreide locaties
        hash_val = int(hashlib.md5(digits[:4].encode() if len(digits) >= 4 else pc2.encode()).hexdigest()[:4], 16)
        
        base_coords = {
            "10": (52.37, 4.90), "20": (52.08, 4.31), "30": (52.09, 5.12),
            "40": (51.84, 5.85), "50": (51.44, 5.47), "60": (50.85, 5.70),
            "70": (52.22, 6.89), "80": (52.51, 6.09), "90": (53.22, 6.57),
        }
        
        base = base_coords.get(pc2[0] + "0", (52.1, 5.3))
        lat_offset = ((hash_val % 100) - 50) * 0.005
        lon_offset = (((hash_val >> 8) % 100) - 50) * 0.007
        return (base[0] + lat_offset, base[1] + lon_offset)
    
    return None, None

# ============================================================================
# MASTER CREATOR FUNCTIONS
# ============================================================================

def load_digimv_parts(uploaded_files: list) -> list:
    """Laad alle DigiMV bronbestanden."""
    all_parts = []
    
    for i, uploaded_file in enumerate(uploaded_files, 1):
        if uploaded_file is None:
            continue
        
        try:
            xl = pd.ExcelFile(uploaded_file)
            part_data = {'_part_number': i}
            
            for sheet in SHEETS_NEEDED:
                if sheet in xl.sheet_names:
                    part_data[sheet] = pd.read_excel(xl, sheet_name=sheet)
            
            all_parts.append(part_data)
        except Exception as e:
            st.warning(f"Fout bij laden Part {i}: {e}")
    
    return all_parts

def create_master_database(parts: list, provincie_map: dict) -> pd.DataFrame:
    """Maak de Master Database van alle parts."""
    all_rows = []
    
    for part_data in parts:
        part_num = part_data.get('_part_number', 0)
        
        # Merge sheets op Code
        if 'RowData_01' not in part_data:
            continue
        
        base_df = part_data['RowData_01'].copy()
        
        for sheet_name in SHEETS_NEEDED[1:]:
            if sheet_name in part_data:
                sheet_df = part_data[sheet_name]
                if 'Code' in sheet_df.columns:
                    new_cols = [c for c in sheet_df.columns if c != 'Code' and c not in base_df.columns]
                    if new_cols:
                        base_df = base_df.merge(sheet_df[['Code'] + new_cols], on='Code', how='left')
        
        # Verwerk elke rij
        for _, row in base_df.iterrows():
            output_row = {'Bron_Part': part_num}
            
            # Basis kolommen
            for cfg in COLUMN_CONFIG['basis']:
                output_row[cfg['output']] = row.get(cfg['col'])
            
            # Type kolommen
            for cfg in COLUMN_CONFIG['type']:
                val = row.get(cfg['col'])
                if cfg.get('transform') == 'ja_nee':
                    output_row[cfg['output']] = ja_nee_to_bool(val)
                else:
                    output_row[cfg['output']] = val
            
            # Financieel
            for cfg in COLUMN_CONFIG['financieel']:
                output_row[cfg['output']] = row.get(cfg['col'])
            
            # Personeel
            for cfg in COLUMN_CONFIG['personeel']:
                output_row[cfg['output']] = row.get(cfg['col'])
            
            # Provincie
            output_row['Provincie'] = get_provincie(output_row.get('Postcode'), provincie_map)
            
            all_rows.append(output_row)
    
    df = pd.DataFrame(all_rows)
    
    # Filter: moet minstens één type hebben
    type_cols = ['Is_VVT', 'Is_GGZ', 'Is_GHZ', 'Is_MSI']
    existing_type_cols = [c for c in type_cols if c in df.columns]
    
    if existing_type_cols:
        mask = df[existing_type_cols].any(axis=1)
        df = df[mask]
    
    # Sorteer op omzet
    if 'Omzet_Totaal' in df.columns:
        df = df.sort_values('Omzet_Totaal', ascending=False, na_position='last')
    
    return df.reset_index(drop=True)

# ============================================================================
# GUI FUNCTIONS
# ============================================================================

def add_fte_reliability_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Voeg FTE betrouwbaarheid vlag toe."""
    def check_reliability(row):
        omzet = row.get('Omzet_Totaal')
        fte = row.get('FTE_Totaal')
        
        if pd.isna(omzet) or pd.isna(fte) or fte == 0:
            return None
        
        omzet_per_fte = omzet / fte
        return FTE_MIN_OMZET_PER_FTE <= omzet_per_fte <= FTE_MAX_OMZET_PER_FTE
    
    df['FTE_Betrouwbaar'] = df.apply(check_reliability, axis=1)
    return df

def add_coordinates(df: pd.DataFrame, coords_map: dict) -> pd.DataFrame:
    """Voeg lat/lon coördinaten toe."""
    coords = df['Postcode'].apply(lambda pc: get_coords(pc, coords_map))
    df['lat'] = coords.apply(lambda x: x[0] if x else None)
    df['lon'] = coords.apply(lambda x: x[1] if x else None)
    return df

def create_map(df: pd.DataFrame, selected_code: str = None) -> folium.Map:
    """Maak een Folium kaart."""
    if selected_code:
        selected_row = df[df['Code'] == selected_code]
        if len(selected_row) > 0 and pd.notna(selected_row.iloc[0].get('lat')):
            map_center = [selected_row.iloc[0]['lat'], selected_row.iloc[0]['lon']]
            map_zoom = 12
        else:
            map_center = [52.1326, 5.2913]
            map_zoom = 7
    else:
        map_center = [52.1326, 5.2913]
        map_zoom = 7
    
    m = folium.Map(location=map_center, zoom_start=map_zoom, tiles='cartodbpositron')
    
    # Beperk markers voor performance
    df_map = df.head(500)
    
    for _, row in df_map.iterrows():
        if pd.notna(row.get('lat')) and pd.notna(row.get('lon')):
            # Kleur
            color = 'gray'
            if row.get('Is_VVT') == True:
                color = 'blue'
            elif row.get('Is_GGZ') == True:
                color = 'green'
            elif row.get('Is_GHZ') == True:
                color = 'orange'
            elif row.get('Is_MSI') == True:
                color = 'red'
            
            # Grootte
            omzet = row.get('Omzet_Totaal', 0) or 0
            if omzet > 100_000_000:
                radius = 12
            elif omzet > 50_000_000:
                radius = 9
            elif omzet > 10_000_000:
                radius = 6
            else:
                radius = 4
            
            # Highlight selected
            is_selected = selected_code and row.get('Code') == selected_code
            if is_selected:
                radius = 18
                color = 'darkred'
            
            naam = row.get('Naam', 'Onbekend')
            
            popup_html = f"""
            <div style="width:200px;">
                <b>{naam}</b><br>
                📍 {row.get('Plaats', '')} ({row.get('Postcode', '')})<br>
                💰 €{omzet/1_000_000:.1f}M<br>
                👥 {row.get('FTE_Totaal', 'n.v.t.')} FTE
            </div>
            """
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=radius,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.8 if is_selected else 0.6,
                weight=3 if is_selected else 1,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{'⭐ ' if is_selected else ''}{naam}"
            ).add_to(m)
    
    return m

def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Pas filters toe op dataframe."""
    result = df.copy()
    
    # Zoekterm
    if filters.get('search'):
        search = filters['search'].lower()
        mask = (
            result['Naam'].astype(str).str.lower().str.contains(search, na=False) |
            result['Plaats'].astype(str).str.lower().str.contains(search, na=False) |
            result['KVK'].astype(str).str.contains(search, na=False)
        )
        result = result[mask]
    
    # Type filter
    if filters.get('types'):
        type_mask = result[filters['types']].any(axis=1)
        result = result[type_mask]
    
    # Provincie
    if filters.get('provincies'):
        result = result[result['Provincie'].isin(filters['provincies'])]
    
    # Omzet
    if filters.get('omzet_min'):
        result = result[result['Omzet_Totaal'] >= filters['omzet_min'] * 1_000_000]
    if filters.get('omzet_max'):
        result = result[result['Omzet_Totaal'] <= filters['omzet_max'] * 1_000_000]
    
    # FTE betrouwbaar
    if filters.get('fte_betrouwbaar'):
        result = result[result['FTE_Betrouwbaar'] == True]
    
    return result

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.markdown("# 🏥 DigiMV Prospect Tool")
    st.markdown("*Analyseer Nederlandse zorgorganisaties*")
    
    # Sidebar: Data laden
    st.sidebar.markdown("## 📁 Data Laden")
    
    # Check of we al data hebben
    if 'master_df' not in st.session_state:
        st.session_state.master_df = None
    if 'provincie_map' not in st.session_state:
        st.session_state.provincie_map = {}
    if 'coords_map' not in st.session_state:
        st.session_state.coords_map = {}
    
    # Tab keuze: Upload of Demo
    data_mode = st.sidebar.radio("Data bron:", ["📤 Upload bestanden", "📊 Upload Master Excel"])
    
    if data_mode == "📤 Upload bestanden":
        st.sidebar.markdown("### DigiMV Bronbestanden")
        st.sidebar.caption("Upload de 3 DigiMV Excel parts")
        
        part1 = st.sidebar.file_uploader("Part 1 (.xls)", type=['xls', 'xlsx'], key='p1')
        part2 = st.sidebar.file_uploader("Part 2 (.xlsx)", type=['xls', 'xlsx'], key='p2')
        part3 = st.sidebar.file_uploader("Part 3 (.xls)", type=['xls', 'xlsx'], key='p3')
        
        st.sidebar.markdown("### Nederland.csv")
        st.sidebar.caption("Voor provincie en kaart coördinaten")
        nederland_file = st.sidebar.file_uploader("Nederland.csv", type=['csv'], key='nl')
        
        if nederland_file:
            prov_map, coords_map = load_nederland_csv(nederland_file)
            st.session_state.provincie_map = prov_map
            st.session_state.coords_map = coords_map
            st.sidebar.success(f"✅ {len(prov_map)} postcodes geladen")
        
        # Genereer knop
        parts = [p for p in [part1, part2, part3] if p is not None]
        
        if parts:
            if st.sidebar.button("🔄 Genereer Master Database", type="primary"):
                with st.spinner("Data verwerken..."):
                    loaded_parts = load_digimv_parts(parts)
                    if loaded_parts:
                        df = create_master_database(loaded_parts, st.session_state.provincie_map)
                        df = add_fte_reliability_flag(df)
                        df = add_coordinates(df, st.session_state.coords_map)
                        st.session_state.master_df = df
                        st.sidebar.success(f"✅ {len(df)} organisaties geladen!")
                    else:
                        st.sidebar.error("Geen data kunnen laden")
    
    else:  # Upload Master Excel
        st.sidebar.markdown("### Master Database")
        master_file = st.sidebar.file_uploader("Upload Master Excel", type=['xlsx', 'xls'], key='master')
        
        st.sidebar.markdown("### Nederland.csv (optioneel)")
        nederland_file = st.sidebar.file_uploader("Nederland.csv", type=['csv'], key='nl2')
        
        if nederland_file:
            prov_map, coords_map = load_nederland_csv(nederland_file)
            st.session_state.provincie_map = prov_map
            st.session_state.coords_map = coords_map
        
        if master_file:
            df = pd.read_excel(master_file)
            df = add_fte_reliability_flag(df)
            df = add_coordinates(df, st.session_state.coords_map)
            st.session_state.master_df = df
            st.sidebar.success(f"✅ {len(df)} organisaties geladen!")
    
    # Hoofdinhoud
    if st.session_state.master_df is None:
        st.info("👈 Upload bestanden via de sidebar om te beginnen")
        
        st.markdown("""
        ### Hoe te gebruiken:
        
        **Optie 1: Genereer vanuit bronbestanden**
        1. Upload de 3 DigiMV Excel bestanden (Part 1, 2, 3)
        2. Upload Nederland.csv voor provincie/coördinaten
        3. Klik op "Genereer Master Database"
        
        **Optie 2: Upload bestaande Master**
        1. Selecteer "Upload Master Excel"
        2. Upload je bestaande Master Database
        3. Optioneel: upload Nederland.csv voor kaart
        """)
        return
    
    df = st.session_state.master_df
    
    # Sidebar: Filters
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔍 Filters")
    
    filters = {}
    
    filters['search'] = st.sidebar.text_input("🔎 Zoek", placeholder="Naam, plaats of KVK...")
    
    # Type filter
    st.sidebar.markdown("### Type Instelling")
    type_cols = ['Is_VVT', 'Is_GGZ', 'Is_GHZ', 'Is_MSI']
    available_types = [c for c in type_cols if c in df.columns]
    
    selected_types = []
    for col in available_types:
        count = df[col].sum() if df[col].dtype == bool else (df[col] == True).sum()
        if st.sidebar.checkbox(f"{col.replace('Is_', '')} ({count})", value=True, key=f"type_{col}"):
            selected_types.append(col)
    filters['types'] = selected_types
    
    # Provincie filter
    if 'Provincie' in df.columns:
        provincies = df['Provincie'].dropna().unique().tolist()
        provincies.sort()
        filters['provincies'] = st.sidebar.multiselect("📍 Provincie", provincies)
    
    # Omzet filter
    st.sidebar.markdown("### 💰 Omzet (€M)")
    col1, col2 = st.sidebar.columns(2)
    filters['omzet_min'] = col1.number_input("Min", value=0, min_value=0)
    filters['omzet_max'] = col2.number_input("Max", value=0, min_value=0)
    if filters['omzet_max'] == 0:
        filters['omzet_max'] = None
    
    # FTE betrouwbaar
    filters['fte_betrouwbaar'] = st.sidebar.checkbox("✅ Alleen betrouwbare FTE data")
    
    # Pas filters toe
    filtered_df = apply_filters(df, filters)
    
    st.sidebar.markdown(f"**Resultaat: {len(filtered_df)} organisaties**")
    
    # Export knop
    if st.sidebar.button("💾 Export naar Excel"):
        output = io.BytesIO()
        filtered_df.to_excel(output, index=False)
        st.sidebar.download_button(
            label="📥 Download Excel",
            data=output.getvalue(),
            file_name=f"DigiMV_Export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Hoofdweergave
    tab1, tab2 = st.tabs(["🗺️ Kaart", "📋 Tabel"])
    
    with tab1:
        # Kaart
        selected_code = st.session_state.get('selected_code')
        m = create_map(filtered_df, selected_code)
        
        map_data = st_folium(m, width=None, height=500, key="map")
        
        # Toon info als marker geklikt
        if map_data and map_data.get('last_object_clicked_popup'):
            st.info(f"Klik op een marker voor details")
    
    with tab2:
        # Tabel
        display_cols = ['Naam', 'Plaats', 'Provincie', 'Omzet_Totaal', 'FTE_Totaal', 
                       'Is_VVT', 'Is_GGZ', 'Is_GHZ']
        available_cols = [c for c in display_cols if c in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_cols],
            use_container_width=True,
            height=500
        )
    
    # Statistieken
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Totaal", len(filtered_df))
    with col2:
        if 'Is_VVT' in filtered_df.columns:
            vvt = filtered_df['Is_VVT'].sum()
            st.metric("VVT", int(vvt))
    with col3:
        if 'Omzet_Totaal' in filtered_df.columns:
            totaal = filtered_df['Omzet_Totaal'].sum() / 1_000_000_000
            st.metric("Totale Omzet", f"€{totaal:.1f}B")
    with col4:
        if 'FTE_Totaal' in filtered_df.columns:
            fte = filtered_df['FTE_Totaal'].sum()
            st.metric("Totale FTE", f"{fte:,.0f}")

if __name__ == "__main__":
    main()
