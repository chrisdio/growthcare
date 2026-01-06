#!/usr/bin/env python3
"""
DigiMV Prospect Tool - Cloud Versie (zonder folium)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import hashlib
from typing import Optional

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
    if uploaded_file is None:
        return {}, {}
    
    try:
        uploaded_file.seek(0)
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';', encoding=encoding, dtype=str)
                break
            except:
                continue
        
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
                    
                    if prov_col and pc4 not in provincie_map:
                        prov = str(row[prov_col]).strip()
                        if prov and prov != 'nan':
                            provincie_map[pc4] = prov
                    
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
    if pd.isna(postcode):
        return None, None
    
    pc_str = str(postcode).strip().replace(' ', '').upper()
    digits = ''.join(c for c in pc_str if c.isdigit())
    
    if len(digits) >= 4:
        pc4 = digits[:4]
        if pc4 in coords_map:
            return coords_map[pc4]
    
    if len(digits) >= 2:
        pc2 = digits[:2]
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
    all_rows = []
    
    for part_data in parts:
        part_num = part_data.get('_part_number', 0)
        
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
        
        for _, row in base_df.iterrows():
            output_row = {
                'Bron_Part': part_num,
                'Code': row.get('Code'),
                'Naam': row.get('Name'),
                'KVK': row.get('qNawKvk'),
                'Postcode': row.get('PostalCode'),
                'Plaats': row.get('Town'),
                'Is_VVT': ja_nee_to_bool(row.get('qTypeWTZaZorg_13')),
                'Is_GGZ': ja_nee_to_bool(row.get('qTypeWTZaZorg_8')),
                'Is_GHZ': ja_nee_to_bool(row.get('qTypeWTZaZorg_10')),
                'Is_MSI': ja_nee_to_bool(row.get('qTypeWTZaZorg_6')),
                'Omzet_Totaal': row.get('qTotaalBaten_0'),
                'Omzet_ZVW': row.get('qBatenZorgZvw_0'),
                'Omzet_WLZ': row.get('qBatenZorgWlz_0'),
                'Omzet_WMO': row.get('qBatenZorgWmo_0'),
                'FTE_Totaal': row.get('qPersTotTot_AantalFte'),
                'FTE_Zorgpersoneel': row.get('qPersTotZorg_AantalFte'),
                'Verzuim_Pct': row.get('qPersVerzuimPct_0'),
                'Vacatures': row.get('qPersVacatures_0'),
            }
            
            output_row['Provincie'] = get_provincie(output_row.get('Postcode'), provincie_map)
            all_rows.append(output_row)
    
    df = pd.DataFrame(all_rows)
    
    type_cols = ['Is_VVT', 'Is_GGZ', 'Is_GHZ', 'Is_MSI']
    existing_type_cols = [c for c in type_cols if c in df.columns]
    
    if existing_type_cols:
        mask = df[existing_type_cols].any(axis=1)
        df = df[mask]
    
    if 'Omzet_Totaal' in df.columns:
        df = df.sort_values('Omzet_Totaal', ascending=False, na_position='last')
    
    return df.reset_index(drop=True)

# ============================================================================
# GUI FUNCTIONS
# ============================================================================

def add_coordinates(df: pd.DataFrame, coords_map: dict) -> pd.DataFrame:
    coords = df['Postcode'].apply(lambda pc: get_coords(pc, coords_map))
    df['lat'] = coords.apply(lambda x: x[0] if x else None)
    df['lon'] = coords.apply(lambda x: x[1] if x else None)
    return df

def create_plotly_map(df: pd.DataFrame) -> px.scatter_mapbox:
    df_map = df.dropna(subset=['lat', 'lon']).head(500).copy()
    
    if df_map.empty:
        return None
    
    # Bepaal kleur
    def get_type(row):
        if row.get('Is_VVT') == True:
            return 'VVT'
        elif row.get('Is_GGZ') == True:
            return 'GGZ'
        elif row.get('Is_GHZ') == True:
            return 'GHZ'
        elif row.get('Is_MSI') == True:
            return 'MSI'
        return 'Anders'
    
    df_map['Type'] = df_map.apply(get_type, axis=1)
    df_map['Omzet_M'] = df_map['Omzet_Totaal'].fillna(0) / 1_000_000
    df_map['size'] = df_map['Omzet_M'].apply(lambda x: max(5, min(30, x / 5)))
    
    fig = px.scatter_mapbox(
        df_map,
        lat='lat',
        lon='lon',
        color='Type',
        size='size',
        hover_name='Naam',
        hover_data={
            'Plaats': True,
            'Omzet_M': ':.1f',
            'FTE_Totaal': True,
            'lat': False,
            'lon': False,
            'size': False,
            'Type': False,
        },
        color_discrete_map={
            'VVT': '#1f77b4',
            'GGZ': '#2ca02c',
            'GHZ': '#ff7f0e',
            'MSI': '#d62728',
            'Anders': '#7f7f7f',
        },
        zoom=6,
        center={'lat': 52.1, 'lon': 5.3},
        mapbox_style='carto-positron',
    )
    
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=600,
    )
    
    return fig

def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    result = df.copy()
    
    if filters.get('search'):
        search = filters['search'].lower()
        mask = (
            result['Naam'].astype(str).str.lower().str.contains(search, na=False) |
            result['Plaats'].astype(str).str.lower().str.contains(search, na=False) |
            result['KVK'].astype(str).str.contains(search, na=False)
        )
        result = result[mask]
    
    if filters.get('types'):
        type_mask = result[filters['types']].any(axis=1)
        result = result[type_mask]
    
    if filters.get('provincies'):
        result = result[result['Provincie'].isin(filters['provincies'])]
    
    if filters.get('omzet_min'):
        result = result[result['Omzet_Totaal'] >= filters['omzet_min'] * 1_000_000]
    if filters.get('omzet_max'):
        result = result[result['Omzet_Totaal'] <= filters['omzet_max'] * 1_000_000]
    
    return result

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.markdown("# 🏥 DigiMV Prospect Tool")
    st.markdown("*Analyseer Nederlandse zorgorganisaties*")
    
    if 'master_df' not in st.session_state:
        st.session_state.master_df = None
    if 'provincie_map' not in st.session_state:
        st.session_state.provincie_map = {}
    if 'coords_map' not in st.session_state:
        st.session_state.coords_map = {}
    
    st.sidebar.markdown("## 📁 Data Laden")
    
    data_mode = st.sidebar.radio("Data bron:", ["📤 Upload bestanden", "📊 Upload Master Excel"])
    
    if data_mode == "📤 Upload bestanden":
        st.sidebar.markdown("### DigiMV Bronbestanden")
        
        part1 = st.sidebar.file_uploader("Part 1 (.xls)", type=['xls', 'xlsx'], key='p1')
        part2 = st.sidebar.file_uploader("Part 2 (.xlsx)", type=['xls', 'xlsx'], key='p2')
        part3 = st.sidebar.file_uploader("Part 3 (.xls)", type=['xls', 'xlsx'], key='p3')
        
        st.sidebar.markdown("### Nederland.csv")
        nederland_file = st.sidebar.file_uploader("Nederland.csv", type=['csv'], key='nl')
        
        if nederland_file:
            prov_map, coords_map = load_nederland_csv(nederland_file)
            st.session_state.provincie_map = prov_map
            st.session_state.coords_map = coords_map
            st.sidebar.success(f"✅ {len(prov_map)} postcodes")
        
        parts = [p for p in [part1, part2, part3] if p is not None]
        
        if parts:
            if st.sidebar.button("🔄 Genereer Database", type="primary"):
                with st.spinner("Data verwerken..."):
                    loaded_parts = load_digimv_parts(parts)
                    if loaded_parts:
                        df = create_master_database(loaded_parts, st.session_state.provincie_map)
                        df = add_coordinates(df, st.session_state.coords_map)
                        st.session_state.master_df = df
                        st.sidebar.success(f"✅ {len(df)} organisaties!")
    
    else:
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
            df = add_coordinates(df, st.session_state.coords_map)
            st.session_state.master_df = df
            st.sidebar.success(f"✅ {len(df)} organisaties!")
    
    if st.session_state.master_df is None:
        st.info("👈 Upload bestanden via de sidebar om te beginnen")
        return
    
    df = st.session_state.master_df
    
    # Filters
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔍 Filters")
    
    filters = {}
    filters['search'] = st.sidebar.text_input("🔎 Zoek", placeholder="Naam, plaats of KVK...")
    
    st.sidebar.markdown("### Type")
    type_cols = ['Is_VVT', 'Is_GGZ', 'Is_GHZ', 'Is_MSI']
    available_types = [c for c in type_cols if c in df.columns]
    
    selected_types = []
    for col in available_types:
        count = df[col].sum() if df[col].dtype == bool else (df[col] == True).sum()
        if st.sidebar.checkbox(f"{col.replace('Is_', '')} ({int(count)})", value=True, key=f"t_{col}"):
            selected_types.append(col)
    filters['types'] = selected_types
    
    if 'Provincie' in df.columns:
        provincies = sorted(df['Provincie'].dropna().unique().tolist())
        filters['provincies'] = st.sidebar.multiselect("📍 Provincie", provincies)
    
    st.sidebar.markdown("### 💰 Omzet (€M)")
    c1, c2 = st.sidebar.columns(2)
    filters['omzet_min'] = c1.number_input("Min", value=0, min_value=0)
    filters['omzet_max'] = c2.number_input("Max", value=0, min_value=0)
    if filters['omzet_max'] == 0:
        filters['omzet_max'] = None
    
    filtered_df = apply_filters(df, filters)
    st.sidebar.markdown(f"**{len(filtered_df)} organisaties**")
    
    # Export
    if st.sidebar.button("💾 Export Excel"):
        output = io.BytesIO()
        filtered_df.to_excel(output, index=False)
        st.sidebar.download_button(
            "📥 Download",
            data=output.getvalue(),
            file_name=f"DigiMV_Export_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Main content
    tab1, tab2 = st.tabs(["🗺️ Kaart", "📋 Tabel"])
    
    with tab1:
        fig = create_plotly_map(filtered_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Geen locatiedata beschikbaar voor kaart")
    
    with tab2:
        cols = ['Naam', 'Plaats', 'Provincie', 'Omzet_Totaal', 'FTE_Totaal', 'Is_VVT', 'Is_GGZ', 'Is_GHZ']
        available = [c for c in cols if c in filtered_df.columns]
        st.dataframe(filtered_df[available], use_container_width=True, height=500)
    
    # Stats
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Totaal", len(filtered_df))
    if 'Is_VVT' in filtered_df.columns:
        c2.metric("VVT", int(filtered_df['Is_VVT'].sum()))
    if 'Omzet_Totaal' in filtered_df.columns:
        c3.metric("Totale Omzet", f"€{filtered_df['Omzet_Totaal'].sum()/1e9:.1f}B")
    if 'FTE_Totaal' in filtered_df.columns:
        c4.metric("Totale FTE", f"{filtered_df['FTE_Totaal'].sum():,.0f}")

if __name__ == "__main__":
    main()
