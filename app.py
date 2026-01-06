#!/usr/bin/env python3
"""
DigiMV Prospect Tool - Cloud Versie (Uitgebreide Filters)
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
st.set_page_config(page_title="Primio Prospect Tool", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

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
    .filter-section { background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

PROVINCIE_FALLBACK = {
    "10": "Noord-Holland", "11": "Noord-Holland", "12": "Noord-Holland", "13": "Noord-Holland", "14": "Noord-Holland", "15": "Noord-Holland",
    "16": "Flevoland", "17": "Noord-Holland", "18": "Noord-Holland", "19": "Noord-Holland",
    "20": "Zuid-Holland", "21": "Zuid-Holland", "22": "Zuid-Holland", "23": "Zuid-Holland", "24": "Zuid-Holland", "25": "Zuid-Holland", "26": "Zuid-Holland", "27": "Zuid-Holland",
    "28": "Utrecht", "29": "Utrecht", "30": "Utrecht", "31": "Utrecht", "32": "Utrecht", "33": "Utrecht", "34": "Utrecht", "35": "Utrecht", "36": "Utrecht", "37": "Utrecht", "38": "Utrecht",
    "39": "Gelderland", "40": "Gelderland", "41": "Gelderland", "42": "Noord-Brabant", "43": "Noord-Brabant", "44": "Noord-Brabant", "45": "Noord-Brabant",
    "46": "Zeeland", "47": "Zeeland", "48": "Noord-Brabant", "49": "Noord-Brabant", "50": "Noord-Brabant", "51": "Noord-Brabant", "52": "Noord-Brabant", "53": "Noord-Brabant",
    "54": "Limburg", "55": "Limburg", "56": "Limburg", "57": "Limburg", "58": "Limburg", "59": "Limburg", "60": "Limburg", "61": "Limburg", "62": "Limburg", "63": "Limburg",
    "64": "Gelderland", "65": "Gelderland", "66": "Gelderland", "67": "Gelderland", "68": "Gelderland", "69": "Gelderland", "70": "Gelderland",
    "71": "Overijssel", "72": "Overijssel", "73": "Overijssel", "74": "Overijssel", "75": "Overijssel", "76": "Overijssel", "77": "Overijssel", "78": "Overijssel", "79": "Drenthe", "80": "Overijssel",
    "81": "Flevoland", "82": "Flevoland", "83": "Friesland", "84": "Friesland", "85": "Friesland", "86": "Friesland", "87": "Friesland", "88": "Friesland", "89": "Friesland",
    "90": "Groningen", "91": "Drenthe", "92": "Drenthe", "93": "Drenthe", "94": "Drenthe", "95": "Groningen", "96": "Groningen", "97": "Groningen", "98": "Groningen", "99": "Groningen",
}

REGIO_MAPPING = {
    "Noord": ["Groningen", "Friesland", "Drenthe"],
    "Oost": ["Overijssel", "Gelderland", "Flevoland"],
    "West": ["Noord-Holland", "Zuid-Holland", "Utrecht", "Zeeland"],
    "Zuid": ["Noord-Brabant", "Limburg"],
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

def get_regio(provincie: str) -> Optional[str]:
    if pd.isna(provincie): return None
    for regio, provs in REGIO_MAPPING.items():
        if provincie in provs: return regio
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

def add_calculated_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Voeg berekende velden toe voor filtering."""
    
    # FTE Betrouwbaarheid
    def calc_fte_reliable(row):
        omzet, fte = row.get('Omzet_Totaal'), row.get('FTE_Totaal')
        if pd.isna(omzet) or pd.isna(fte) or fte == 0: return None
        ratio = omzet / fte
        return FTE_MIN_OMZET_PER_FTE <= ratio <= FTE_MAX_OMZET_PER_FTE
    if 'FTE_Betrouwbaar' not in df.columns:
        df['FTE_Betrouwbaar'] = df.apply(calc_fte_reliable, axis=1)
    
    # Omzet per FTE
    if 'Omzet_Totaal' in df.columns and 'FTE_Totaal' in df.columns:
        df['Omzet_per_FTE'] = df.apply(lambda r: r['Omzet_Totaal']/r['FTE_Totaal'] if pd.notna(r['FTE_Totaal']) and r['FTE_Totaal']>0 else None, axis=1)
    
    # Omzet groei %
    if 'Omzet_Totaal' in df.columns and 'Omzet_Vorig_Jaar' in df.columns:
        df['Omzet_Groei_Pct'] = df.apply(lambda r: ((r['Omzet_Totaal']-r['Omzet_Vorig_Jaar'])/r['Omzet_Vorig_Jaar'])*100 
                                         if pd.notna(r['Omzet_Vorig_Jaar']) and r['Omzet_Vorig_Jaar']>0 else None, axis=1)
    
    # Dominant omzet type
    def get_dominant_type(row):
        types = {'ZVW': row.get('Omzet_ZVW',0) or 0, 'WLZ': row.get('Omzet_WLZ',0) or 0, 'WMO': row.get('Omzet_WMO',0) or 0}
        if sum(types.values()) == 0: return None
        return max(types, key=types.get)
    df['Omzet_Dominant'] = df.apply(get_dominant_type, axis=1)
    
    # Regio
    if 'Provincie' in df.columns:
        df['Regio'] = df['Provincie'].apply(get_regio)
    
    # Mogelijk Huishoudelijke Hulp (WMO zonder VVT specialisaties)
    if 'Omzet_WMO' in df.columns:
        df['Mogelijk_HH'] = df.apply(lambda r: (pd.notna(r.get('Omzet_WMO')) and r.get('Omzet_WMO',0) > 0 and 
                                                r.get('VVT_Wijkverpleging') != True and r.get('VVT_Verpleeghuiszorg') != True), axis=1)
    
    # Grootte categorie
    def get_size_cat(fte):
        if pd.isna(fte): return "Onbekend"
        if fte < 50: return "Micro (<50)"
        if fte < 150: return "Klein (50-150)"
        if fte < 500: return "Middel (150-500)"
        if fte < 1500: return "Groot (500-1500)"
        return "Enterprise (>1500)"
    if 'FTE_Totaal' in df.columns:
        df['Grootte_Cat'] = df['FTE_Totaal'].apply(get_size_cat)
    
    # Omzet categorie
    def get_omzet_cat(omzet):
        if pd.isna(omzet): return "Onbekend"
        m = omzet / 1_000_000
        if m < 1: return "<€1M"
        if m < 5: return "€1-5M"
        if m < 10: return "€5-10M"
        if m < 50: return "€10-50M"
        if m < 100: return "€50-100M"
        return ">€100M"
    if 'Omzet_Totaal' in df.columns:
        df['Omzet_Cat'] = df['Omzet_Totaal'].apply(get_omzet_cat)
    
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
                'VVT_Kraamzorg': ja_nee_to_bool(row.get('qTypeWTZaZorgVenV_1')),
                'VVT_Crisiszorg': ja_nee_to_bool(row.get('qTypeWTZaZorgVenV_2')),
                'VVT_Wijkverpleging': ja_nee_to_bool(row.get('qTypeWTZaZorgVenV_3')),
                'VVT_Verpleeghuiszorg': ja_nee_to_bool(row.get('qTypeWTZaZorgVenV_4')),
                'VVT_GRZ': ja_nee_to_bool(row.get('qTypeWTZaZorgVenV_5')),
                'Omzet_Totaal': row.get('qTotaalBaten_0'), 'Omzet_Vorig_Jaar': row.get('qTotaalBaten_1'),
                'Omzet_ZVW': row.get('qBatenZorgZvw_0'), 'Omzet_WLZ': row.get('qBatenZorgWlz_0'), 'Omzet_WMO': row.get('qBatenZorgWmo_0'),
                'FTE_Totaal': row.get('qPersTotTot_AantalFte'), 'FTE_Zorgpersoneel': row.get('qPersTotZorg_AantalFte'),
                'FTE_Loondienst': row.get('qPersTotLoonTot_AantalFte'), 'FTE_Ingehuurd': row.get('qPersTotHuurTot_AantalFte'),
                'Verzuim_Pct': row.get('qPersVerzuimPct_0'), 'Vacatures': row.get('qPersVacatures_0'),
                'Instroom_FTE': row.get('qPersVerloopTot_InstroomFte'), 'Uitstroom_FTE': row.get('qPersVerloopTot_UitstroomFte'),
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
    
    # Zoekterm
    if filters.get('search'):
        search = filters['search'].lower()
        mask = pd.Series([False] * len(result))
        for col in ['Naam', 'Name', 'Plaats', 'Town', 'KVK', 'Code']:
            if col in result.columns: mask |= result[col].astype(str).str.lower().str.contains(search, na=False)
        result = result[mask]
    
    # Type
    if filters.get('types'):
        existing = [c for c in filters['types'] if c in result.columns]
        if existing: result = result[result[existing].any(axis=1)]
    
    # VVT Subtypes
    if filters.get('vvt_subtypes'):
        existing = [c for c in filters['vvt_subtypes'] if c in result.columns]
        if existing: result = result[result[existing].any(axis=1)]
    
    # Regio
    if filters.get('regios') and 'Regio' in result.columns:
        result = result[result['Regio'].isin(filters['regios'])]
    
    # Provincie
    if filters.get('provincies') and 'Provincie' in result.columns:
        result = result[result['Provincie'].isin(filters['provincies'])]
    
    # Omzet
    if 'Omzet_Totaal' in result.columns:
        if filters.get('omzet_min'): result = result[pd.to_numeric(result['Omzet_Totaal'], errors='coerce') >= filters['omzet_min']]
        if filters.get('omzet_max'): result = result[pd.to_numeric(result['Omzet_Totaal'], errors='coerce') <= filters['omzet_max']]
    
    # Omzet categorie
    if filters.get('omzet_cats') and 'Omzet_Cat' in result.columns:
        result = result[result['Omzet_Cat'].isin(filters['omzet_cats'])]
    
    # Omzet dominant type
    if filters.get('omzet_dominant') and 'Omzet_Dominant' in result.columns:
        result = result[result['Omzet_Dominant'].isin(filters['omzet_dominant'])]
    
    # Omzet groei
    if 'Omzet_Groei_Pct' in result.columns:
        if filters.get('groei_positief'): result = result[result['Omzet_Groei_Pct'] > 0]
        if filters.get('groei_min') is not None: result = result[result['Omzet_Groei_Pct'] >= filters['groei_min']]
        if filters.get('groei_max') is not None: result = result[result['Omzet_Groei_Pct'] <= filters['groei_max']]
    
    # FTE / Grootte
    if filters.get('grootte_cats') and 'Grootte_Cat' in result.columns:
        result = result[result['Grootte_Cat'].isin(filters['grootte_cats'])]
    
    if 'FTE_Totaal' in result.columns:
        if filters.get('fte_min') is not None: result = result[pd.to_numeric(result['FTE_Totaal'], errors='coerce') >= filters['fte_min']]
        if filters.get('fte_max') is not None: result = result[pd.to_numeric(result['FTE_Totaal'], errors='coerce') <= filters['fte_max']]
        if filters.get('only_with_fte'): result = result[pd.to_numeric(result['FTE_Totaal'], errors='coerce') > 0]
    
    # FTE Betrouwbaarheid
    if filters.get('only_reliable_fte') and 'FTE_Betrouwbaar' in result.columns:
        result = result[result['FTE_Betrouwbaar'] == True]
    
    # Verzuim
    if 'Verzuim_Pct' in result.columns:
        if filters.get('verzuim_min') is not None: result = result[pd.to_numeric(result['Verzuim_Pct'], errors='coerce') >= filters['verzuim_min']]
        if filters.get('verzuim_max') is not None: result = result[pd.to_numeric(result['Verzuim_Pct'], errors='coerce') <= filters['verzuim_max']]
    
    # Mogelijk HH
    if filters.get('only_hh') and 'Mogelijk_HH' in result.columns:
        result = result[result['Mogelijk_HH'] == True]
    
    # Heeft inhuur
    if filters.get('has_inhuur') and 'FTE_Ingehuurd' in result.columns:
        result = result[pd.to_numeric(result['FTE_Ingehuurd'], errors='coerce') > 0]
    
    return result

# ============================================================================
# KAART (Plotly)
# ============================================================================

def create_map(df: pd.DataFrame, selected_code: str = None, color_by: str = 'Type') -> go.Figure:
    df_map = df.dropna(subset=['lat', 'lon']).head(500).copy()
    if df_map.empty: return None
    
    # Bepaal kleur kolom
    if color_by == 'Type':
        def get_type(row):
            if row.get('Is_VVT') == True: return 'VVT'
            if row.get('Is_GGZ') == True: return 'GGZ'
            if row.get('Is_GHZ') == True: return 'GHZ'
            if row.get('Is_MSI') == True: return 'MSI'
            return 'Anders'
        df_map['color_cat'] = df_map.apply(get_type, axis=1)
        color_map = {'VVT': '#1f77b4', 'GGZ': '#2ca02c', 'GHZ': '#ff7f0e', 'MSI': '#d62728', 'Anders': '#7f7f7f'}
    elif color_by == 'Regio' and 'Regio' in df_map.columns:
        df_map['color_cat'] = df_map['Regio'].fillna('Onbekend')
        color_map = {'Noord': '#3498db', 'Oost': '#2ecc71', 'West': '#e74c3c', 'Zuid': '#f39c12', 'Onbekend': '#95a5a6'}
    elif color_by == 'Grootte' and 'Grootte_Cat' in df_map.columns:
        df_map['color_cat'] = df_map['Grootte_Cat']
        color_map = {'Micro (<50)': '#bdc3c7', 'Klein (50-150)': '#3498db', 'Middel (150-500)': '#2ecc71', 
                     'Groot (500-1500)': '#f39c12', 'Enterprise (>1500)': '#e74c3c', 'Onbekend': '#95a5a6'}
    elif color_by == 'Omzet Dominant' and 'Omzet_Dominant' in df_map.columns:
        df_map['color_cat'] = df_map['Omzet_Dominant'].fillna('Onbekend')
        color_map = {'ZVW': '#667eea', 'WLZ': '#764ba2', 'WMO': '#f093fb', 'Onbekend': '#95a5a6'}
    else:
        df_map['color_cat'] = 'Alle'
        color_map = {'Alle': '#3498db'}
    
    # Grootte
    df_map['Omzet_M'] = pd.to_numeric(df_map.get('Omzet_Totaal', 0), errors='coerce').fillna(0) / 1_000_000
    df_map['size'] = df_map['Omzet_M'].apply(lambda x: max(8, min(35, 8 + x / 5)))
    if selected_code and 'Code' in df_map.columns: df_map.loc[df_map['Code'] == selected_code, 'size'] = 50
    
    naam_col = find_column(df_map, ['Naam', 'Name'])
    df_map['display_name'] = df_map[naam_col] if naam_col else 'Onbekend'
    plaats_col = find_column(df_map, ['Plaats', 'Town'])
    df_map['Plaats_display'] = df_map[plaats_col].fillna('') if plaats_col else ''
    
    fig = px.scatter_mapbox(df_map, lat='lat', lon='lon', color='color_cat', size='size',
        custom_data=['Code'] if 'Code' in df_map.columns else None,
        hover_name='display_name',
        hover_data={'lat': False, 'lon': False, 'size': False, 'color_cat': True, 'Omzet_M': ':.1f', 'Plaats_display': True},
        color_discrete_map=color_map,
        zoom=6, center={'lat': 52.1, 'lon': 5.3}, mapbox_style='carto-positron')
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None))
    return fig

# ============================================================================
# CHARTS
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

def create_distribution_chart(df: pd.DataFrame, column: str, title: str) -> go.Figure:
    if column not in df.columns: return None
    counts = df[column].value_counts()
    fig = px.bar(x=counts.index, y=counts.values, title=title)
    fig.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20), xaxis_title="", yaxis_title="Aantal")
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
        c1, c2 = st.columns(2)
        c1.markdown(f"**KVK:** {org.get('KVK', '-')}")
        c2.markdown(f"**Code:** {org.get('Code', '-')}")
        c1.markdown(f"**Provincie:** {org.get('Provincie', '-')}")
        c2.markdown(f"**Regio:** {org.get('Regio', '-')}")
        
        if org.get('Is_VVT') == True:
            vvt = [t for t,c in [('Kraamzorg','VVT_Kraamzorg'),('Crisiszorg','VVT_Crisiszorg'),('Wijkverpleging','VVT_Wijkverpleging'),
                                  ('Verpleeghuiszorg','VVT_Verpleeghuiszorg'),('GRZ','VVT_GRZ')] if org.get(c)==True]
            if vvt: st.markdown(f"**VVT specialisaties:** {', '.join(vvt)}")
        
        if org.get('Mogelijk_HH'): st.info("🏠 Mogelijk huishoudelijke hulp aanbieder")
    
    with tabs[1]:
        omzet = org.get('Omzet_Totaal')
        if pd.notna(omzet):
            c1, c2, c3 = st.columns(3)
            c1.metric("Omzet", f"€{omzet/1_000_000:.1f}M")
            groei = org.get('Omzet_Groei_Pct')
            if pd.notna(groei): c2.metric("Groei", f"{groei:+.1f}%")
            dominant = org.get('Omzet_Dominant')
            if dominant: c3.metric("Dominant", dominant)
            
            fig = create_omzet_chart(org)
            if fig: st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("**Omzet details:**")
            for lbl,col in [("ZVW","Omzet_ZVW"),("WLZ","Omzet_WLZ"),("WMO","Omzet_WMO")]:
                val = org.get(col)
                if pd.notna(val): st.markdown(f"- {lbl}: €{val/1_000_000:.1f}M")
        else: st.info("Geen omzet data")
    
    with tabs[2]:
        fte = org.get('FTE_Totaal')
        if pd.notna(fte):
            c1, c2 = st.columns(2)
            c1.metric("FTE Totaal", f"{fte:,.0f}")
            c2.metric("Grootte", org.get('Grootte_Cat', '-'))
            
            omzet = org.get('Omzet_Totaal')
            if pd.notna(omzet) and fte > 0:
                st.markdown(f"**Omzet/FTE:** €{omzet/fte:,.0f}")
            
            st.markdown("**FTE verdeling:**")
            for lbl,col in [("Loondienst","FTE_Loondienst"),("Ingehuurd","FTE_Ingehuurd"),("Zorgpersoneel","FTE_Zorgpersoneel")]:
                val = org.get(col)
                if pd.notna(val): st.markdown(f"- {lbl}: {val:,.0f}")
            
            st.markdown("**Verloop:**")
            for lbl,col in [("Instroom","Instroom_FTE"),("Uitstroom","Uitstroom_FTE")]:
                val = org.get(col)
                if pd.notna(val): st.markdown(f"- {lbl}: {val:,.0f} FTE")
            
            verzuim = org.get('Verzuim_Pct')
            if pd.notna(verzuim):
                color = "🟢" if verzuim < 5 else "🟠" if verzuim < 8 else "🔴"
                st.markdown(f"**Verzuim:** {color} {verzuim:.1f}%")
        else: st.info("Geen FTE data")

# ============================================================================
# MAIN
# ============================================================================

def main():
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown('<p class="main-header">🏥 Primio Prospect Tool</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">DigiMV Zorgorganisaties Analyse - Uitgebreide Filters</p>', unsafe_allow_html=True)
    
    for key in ['master_df', 'selected_org', 'provincie_map', 'coords_map']:
        if key not in st.session_state:
            st.session_state[key] = None if key in ['master_df', 'selected_org'] else {}
    
    # SIDEBAR
    st.sidebar.markdown("## 📁 Data")
    data_mode = st.sidebar.radio("Bron:", ["📊 Master Excel", "📤 DigiMV Parts"], horizontal=True)
    
    nederland_file = st.sidebar.file_uploader("🗺️ Nederland.csv", type=['csv'], key='nl')
    if nederland_file:
        prov_map, coords_map = load_nederland_csv(nederland_file.read())
        st.session_state.provincie_map, st.session_state.coords_map = prov_map, coords_map
        st.sidebar.success(f"✅ {len(coords_map)} postcodes")
    
    if data_mode == "📊 Master Excel":
        master_file = st.sidebar.file_uploader("Excel bestand", type=['xlsx','xls'], key='master')
        if master_file:
            df = pd.read_excel(master_file)
            df = add_calculated_fields(add_coordinates(df, st.session_state.coords_map))
            st.session_state.master_df = df
            st.sidebar.success(f"✅ {len(df)} organisaties")
    else:
        parts = [st.sidebar.file_uploader(f"Part {i}", type=['xls','xlsx'], key=f'p{i}') for i in [1,2,3]]
        parts = [p for p in parts if p]
        if parts and st.sidebar.button("🔄 Genereer", type="primary"):
            with st.spinner("Verwerken..."):
                loaded = load_digimv_parts(parts)
                if loaded:
                    df = create_master_database(loaded, st.session_state.provincie_map)
                    df = add_calculated_fields(add_coordinates(df, st.session_state.coords_map))
                    st.session_state.master_df = df
                    st.sidebar.success(f"✅ {len(df)} organisaties")
    
    if st.session_state.master_df is None:
        st.info("👈 Upload bestanden om te beginnen")
        return
    
    df = st.session_state.master_df
    
    # ========== FILTERS ==========
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔍 Filters")
    filters = {}
    
    filters['search'] = st.sidebar.text_input("🔎 Zoek", placeholder="Naam, KVK, plaats...")
    
    # Type filter
    with st.sidebar.expander("🏥 Type Instelling", expanded=True):
        type_cols = ['Is_VVT', 'Is_GGZ', 'Is_GHZ', 'Is_MSI']
        filters['types'] = [c for c in type_cols if c in df.columns and st.checkbox(
            f"{c.replace('Is_','')} ({int(df[c].sum()) if df[c].dtype==bool else 0})", value=True, key=f"t_{c}")]
    
    # VVT Subtypes
    if 'Is_VVT' in df.columns:
        with st.sidebar.expander("🩺 VVT Specialisaties"):
            vvt_cols = ['VVT_Kraamzorg', 'VVT_Crisiszorg', 'VVT_Wijkverpleging', 'VVT_Verpleeghuiszorg', 'VVT_GRZ']
            vvt_available = [c for c in vvt_cols if c in df.columns]
            selected_vvt = []
            for col in vvt_available:
                count = int(df[col].sum()) if col in df.columns and df[col].dtype == bool else 0
                if st.checkbox(f"{col.replace('VVT_','')} ({count})", value=False, key=f"vvt_{col}"):
                    selected_vvt.append(col)
            filters['vvt_subtypes'] = selected_vvt if selected_vvt else None
    
    # Locatie
    with st.sidebar.expander("📍 Locatie"):
        if 'Regio' in df.columns:
            regios = ['Noord', 'Oost', 'West', 'Zuid']
            filters['regios'] = st.multiselect("Regio", regios, key="regios")
        
        if 'Provincie' in df.columns:
            provincies = sorted([p for p in df['Provincie'].dropna().unique() if p])
            filters['provincies'] = st.multiselect("Provincie", provincies, key="provs")
    
    # Omzet
    with st.sidebar.expander("💰 Omzet"):
        c1, c2 = st.columns(2)
        omzet_min = c1.number_input("Min (€M)", min_value=0.0, value=0.0, step=1.0, key="om_min")
        omzet_max = c2.number_input("Max (€M)", min_value=0.0, value=0.0, step=1.0, key="om_max")
        filters['omzet_min'] = omzet_min * 1e6 if omzet_min > 0 else None
        filters['omzet_max'] = omzet_max * 1e6 if omzet_max > 0 else None
        
        if 'Omzet_Cat' in df.columns:
            cats = ['<€1M', '€1-5M', '€5-10M', '€10-50M', '€50-100M', '>€100M']
            filters['omzet_cats'] = st.multiselect("Omzet categorie", cats, key="om_cats")
        
        if 'Omzet_Dominant' in df.columns:
            filters['omzet_dominant'] = st.multiselect("Dominant type", ['ZVW', 'WLZ', 'WMO'], key="om_dom")
        
        if 'Omzet_Groei_Pct' in df.columns:
            filters['groei_positief'] = st.checkbox("Alleen groeiende organisaties", key="groei_pos")
            groei_range = st.slider("Groei %", min_value=-50, max_value=100, value=(-50, 100), key="groei_range")
            if groei_range != (-50, 100):
                filters['groei_min'], filters['groei_max'] = groei_range
    
    # Grootte / FTE
    with st.sidebar.expander("👥 Grootte & FTE"):
        if 'Grootte_Cat' in df.columns:
            cats = ['Micro (<50)', 'Klein (50-150)', 'Middel (150-500)', 'Groot (500-1500)', 'Enterprise (>1500)']
            filters['grootte_cats'] = st.multiselect("Grootte categorie", cats, key="gr_cats")
        
        filters['only_with_fte'] = st.checkbox("Alleen met FTE data", key="only_fte")
        filters['only_reliable_fte'] = st.checkbox("Alleen betrouwbare FTE", key="rel_fte")
        
        if 'FTE_Ingehuurd' in df.columns:
            filters['has_inhuur'] = st.checkbox("Heeft ingehuurd personeel", key="has_inhuur")
    
    # Verzuim
    if 'Verzuim_Pct' in df.columns:
        with st.sidebar.expander("🏥 Verzuim"):
            verzuim_range = st.slider("Verzuim %", 0.0, 15.0, (0.0, 15.0), 0.5, key="verzuim")
            if verzuim_range != (0.0, 15.0):
                filters['verzuim_min'], filters['verzuim_max'] = verzuim_range
    
    # Speciale filters
    with st.sidebar.expander("🎯 Speciale Filters"):
        if 'Mogelijk_HH' in df.columns:
            hh_count = int(df['Mogelijk_HH'].sum()) if df['Mogelijk_HH'].dtype == bool else 0
            filters['only_hh'] = st.checkbox(f"Mogelijk huishoudelijke hulp ({hh_count})", key="only_hh")
    
    if st.sidebar.button("🔄 Reset alle filters", use_container_width=True): st.rerun()
    
    # Apply filters
    filtered_df = filter_data(df, filters)
    st.sidebar.markdown(f"### 📊 {len(filtered_df)} resultaten")
    
    # ========== MAIN CONTENT ==========
    st.markdown("---")
    
    # Metrics
    mc = st.columns(5)
    mc[0].metric("Organisaties", f"{len(filtered_df):,}")
    if 'Omzet_Totaal' in filtered_df.columns:
        mc[1].metric("Totale Omzet", f"€{pd.to_numeric(filtered_df['Omzet_Totaal'],errors='coerce').sum()/1e9:.1f}B")
    if 'FTE_Totaal' in filtered_df.columns:
        mc[2].metric("Totale FTE", f"{pd.to_numeric(filtered_df['FTE_Totaal'],errors='coerce').sum():,.0f}")
    if 'FTE_Betrouwbaar' in filtered_df.columns:
        mc[3].metric("Betrouwbaar", f"{(filtered_df['FTE_Betrouwbaar']==True).sum()}")
    if 'Mogelijk_HH' in filtered_df.columns:
        mc[4].metric("Mogelijk HH", f"{(filtered_df['Mogelijk_HH']==True).sum()}")
    
    # Export
    with col_h2:
        output = io.BytesIO(); filtered_df.to_excel(output, index=False)
        st.download_button("💾 Export", data=output.getvalue(), file_name=f"Export_{datetime.now().strftime('%Y%m%d')}.xlsx")
    
    # Layout
    st.markdown("---")
    col_main, col_det = st.columns([2, 1])
    
    with col_main:
        # Kaart opties
        map_col1, map_col2 = st.columns([3, 1])
        with map_col1:
            st.markdown("### 🗺️ Kaart")
        with map_col2:
            color_by = st.selectbox("Kleur op", ["Type", "Regio", "Grootte", "Omzet Dominant"], key="color_by", label_visibility="collapsed")
        
        if len(filtered_df) > 0 and 'lat' in filtered_df.columns and filtered_df['lat'].notna().any():
            if len(filtered_df) > 500: st.caption(f"⚠️ Toont 500/{len(filtered_df)} organisaties")
            fig = create_map(filtered_df, st.session_state.selected_org, color_by)
            if fig:
                sel = st.plotly_chart(fig, use_container_width=True, key="map", on_select="rerun")
                if sel and sel.selection and sel.selection.points:
                    pt = sel.selection.points[0]
                    if 'customdata' in pt and pt['customdata']:
                        code = pt['customdata'][0]
                        if code != st.session_state.selected_org:
                            st.session_state.selected_org = code; st.rerun()
        else: st.info("Upload Nederland.csv voor kaart")
        
        st.markdown("---")
        
        # Tabel
        st.markdown("### 📋 Tabel")
        if len(filtered_df) > 0:
            disp_cols = [c for c in ['Code','Naam','Plaats','Provincie','Regio','Omzet_Totaal','FTE_Totaal','Grootte_Cat','FTE_Betrouwbaar','Mogelijk_HH'] if c in filtered_df.columns]
            disp_df = filtered_df[disp_cols].copy()
            if 'Omzet_Totaal' in disp_df.columns: disp_df['Omzet_Totaal'] = disp_df['Omzet_Totaal'].apply(lambda x: f"€{x/1e6:.1f}M" if pd.notna(x) else "-")
            if 'FTE_Totaal' in disp_df.columns: disp_df['FTE_Totaal'] = disp_df['FTE_Totaal'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")
            if 'FTE_Betrouwbaar' in disp_df.columns: disp_df['FTE_Betrouwbaar'] = disp_df['FTE_Betrouwbaar'].apply(lambda x: "✅" if x==True else "⚠️" if x==False else "-")
            if 'Mogelijk_HH' in disp_df.columns: disp_df['Mogelijk_HH'] = disp_df['Mogelijk_HH'].apply(lambda x: "🏠" if x==True else "")
            
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
                st.info("Niet in huidige filter")
                if st.button("❌ Deselecteren"): st.session_state.selected_org = None; st.rerun()
        else: st.info("👆 Klik op een organisatie voor details")
        
        # Mini statistieken
        st.markdown("---")
        st.markdown("### 📈 Quick Stats")
        if 'Grootte_Cat' in filtered_df.columns:
            fig = create_distribution_chart(filtered_df, 'Grootte_Cat', 'Verdeling naar grootte')
            if fig: st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
