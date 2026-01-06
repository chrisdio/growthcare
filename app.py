#!/usr/bin/env python3
"""
DigiMV Prospect Tool - Interactieve GUI v2
==========================================
Visualiseer en filter zorgorganisaties op een kaart en in een tabel.

Gebruik:
    streamlit run app.py

Vereisten:
    pip install streamlit pandas openpyxl folium streamlit-folium plotly
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from datetime import datetime
import io
import os
import hashlib

# ============================================================================
# CONFIGURATIE - Aanpasbare variabelen
# ============================================================================
FTE_MIN_OMZET_PER_FTE = 20000   # Minimaal €20.000 omzet per FTE
FTE_MAX_OMZET_PER_FTE = 100000  # Maximaal €100.000 omzet per FTE

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
# STYLING
# ============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1E3A5F;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-top: 0;
    }
    .warning-badge {
        background-color: #fff3cd;
        color: #856404;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .success-badge {
        background-color: #d4edda;
        color: #155724;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING
# ============================================================================
@st.cache_data
def load_data(file_path: str) -> pd.DataFrame:
    """Laad de master Excel data."""
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        st.error(f"Fout bij laden data: {e}")
        return pd.DataFrame()

@st.cache_data
def load_postcode_database() -> dict:
    """Laad de PC4 postcode database uit Nederland.csv of fallback naar postcodes_nl.csv."""
    
    # Probeer Nederland.csv eerst (heeft lat/lon kolommen)
    nederland_paths = [
        'Nederland.csv',
        os.path.join(os.getcwd(), 'Nederland.csv'),
    ]
    
    pc_dict = {}
    
    for path in nederland_paths:
        if os.path.exists(path):
            try:
                # Nederland.csv gebruikt ; als separator
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        df = pd.read_csv(path, sep=';', encoding=encoding, dtype=str)
                        break
                    except:
                        continue
                
                # Zoek kolommen (case-insensitive)
                pc_col = lat_col = lon_col = None
                for col in df.columns:
                    col_lower = col.lower()
                    if col_lower == 'postcode':
                        pc_col = col
                    elif col_lower == 'lat':
                        lat_col = col
                    elif col_lower == 'lon':
                        lon_col = col
                
                if pc_col and lat_col and lon_col:
                    # Converteer lat/lon naar float
                    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
                    df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
                    
                    # Groepeer per PC4 en neem gemiddelde coördinaten
                    for _, row in df.iterrows():
                        pc = str(row[pc_col]).strip().replace(' ', '').upper()
                        lat = row[lat_col]
                        lon = row[lon_col]
                        
                        if pd.notna(lat) and pd.notna(lon):
                            digits = ''.join(c for c in pc if c.isdigit())
                            if len(digits) >= 4:
                                pc4 = digits[:4]
                                if pc4 not in pc_dict:
                                    pc_dict[pc4] = (float(lat), float(lon))
                    
                    if pc_dict:
                        break
            except Exception as e:
                continue
    
    # Fallback naar postcodes_nl.csv als Nederland.csv niet werkt
    if not pc_dict:
        fallback_paths = [
            'postcodes_nl.csv',
            os.path.join(os.getcwd(), 'postcodes_nl.csv'),
        ]
        
        for path in fallback_paths:
            if os.path.exists(path):
                try:
                    df = pd.read_csv(path, comment='#', header=None, 
                                    names=['PC4', 'lat', 'lon', 'plaats'])
                    df['PC4'] = df['PC4'].astype(str).str.strip()
                    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
                    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
                    
                    for _, row in df.iterrows():
                        if pd.notna(row['lat']) and pd.notna(row['lon']):
                            pc_dict[row['PC4']] = (row['lat'], row['lon'])
                    
                    if pc_dict:
                        break
                except:
                    continue
    
    # Ultieme fallback: hardcoded regio centrums
    if not pc_dict:
        pc2_coords = {
            "10": (52.37, 4.90), "11": (52.43, 4.81), "12": (52.35, 4.65),
            "13": (52.50, 4.75), "14": (52.63, 4.75), "15": (52.70, 5.00),
            "16": (52.52, 5.47), "17": (52.55, 4.65), "18": (52.44, 4.83),
            "19": (52.27, 4.85), "20": (52.08, 4.31), "21": (52.01, 4.36),
            "22": (51.92, 4.48), "23": (51.85, 4.50), "24": (52.16, 4.50),
            "25": (52.00, 4.70), "26": (51.98, 4.13), "27": (51.81, 4.67),
            "28": (52.09, 5.12), "29": (52.22, 5.17), "30": (52.09, 5.12),
            "31": (52.15, 5.39), "32": (52.22, 5.17), "33": (52.05, 5.10),
            "34": (52.08, 5.00), "35": (52.23, 5.60), "36": (52.09, 5.12),
            "37": (52.18, 5.40), "38": (52.03, 5.67), "39": (52.21, 5.97),
            "40": (51.84, 5.85), "41": (51.96, 5.91), "42": (51.69, 5.30),
            "43": (51.55, 5.08), "44": (51.59, 4.78), "45": (51.44, 5.47),
            "46": (51.50, 3.61), "47": (51.50, 3.85), "48": (51.50, 3.85),
            "49": (51.49, 5.48), "50": (51.44, 5.47), "51": (51.45, 5.65),
            "52": (51.65, 5.29), "53": (51.70, 5.30), "54": (51.44, 5.90),
            "55": (51.22, 5.97), "56": (50.87, 5.98), "57": (50.85, 5.69),
            "58": (51.44, 5.90), "59": (51.35, 6.17), "60": (50.85, 5.70),
            "61": (50.88, 5.98), "62": (50.85, 5.70), "63": (50.91, 5.95),
            "64": (51.83, 5.85), "65": (51.97, 5.92), "66": (51.96, 6.30),
            "67": (52.00, 6.05), "68": (51.98, 5.90), "69": (52.04, 6.62),
            "70": (52.08, 6.12), "71": (52.22, 6.89), "72": (52.51, 6.09),
            "73": (52.44, 6.26), "74": (52.52, 6.47), "75": (52.63, 6.66),
            "76": (52.43, 6.17), "77": (52.35, 6.66), "78": (52.55, 5.92),
            "79": (52.76, 6.90), "80": (52.51, 6.09), "81": (52.52, 5.47),
            "82": (52.35, 5.22), "83": (53.20, 5.80), "84": (53.15, 5.85),
            "85": (53.10, 5.65), "86": (53.25, 5.92), "87": (53.20, 5.80),
            "88": (53.12, 6.05), "89": (53.33, 6.20), "90": (53.25, 5.80),
            "91": (53.00, 6.55), "92": (52.99, 6.56), "93": (52.76, 6.90),
            "94": (52.85, 6.90), "95": (53.22, 6.57), "96": (53.25, 6.85),
            "97": (53.22, 6.57), "98": (53.15, 7.05), "99": (53.11, 7.03),
        }
        for pc2, (base_lat, base_lon) in pc2_coords.items():
            for i in range(100):
                pc4 = f"{pc2}{i:02d}"
                hash_val = int(hashlib.md5(pc4.encode()).hexdigest()[:4], 16)
                lat_offset = ((hash_val % 100) - 50) * 0.003
                lon_offset = (((hash_val >> 8) % 100) - 50) * 0.004
                pc_dict[pc4] = (base_lat + lat_offset, base_lon + lon_offset)
    
    return pc_dict


def add_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Voeg lat/lon toe aan dataframe op basis van PC4 postcode database."""
    pc_db = load_postcode_database()
    
    def get_coords(postcode):
        if pd.isna(postcode):
            return (None, None)
        
        pc_str = str(postcode).strip().replace(' ', '').upper()
        
        # Haal eerste 4 cijfers
        digits = ''.join(c for c in pc_str if c.isdigit())
        if len(digits) >= 4:
            pc4 = digits[:4]
            if pc4 in pc_db:
                return pc_db[pc4]
        
        # Fallback: probeer 2 cijfers
        if len(digits) >= 2:
            pc2 = digits[:2]
            # Zoek een willekeurige PC4 in die regio
            for key in pc_db:
                if key.startswith(pc2):
                    return pc_db[key]
        
        return (None, None)
    
    # Apply en split tuples
    coords_list = df['Postcode'].apply(get_coords).tolist()
    df['lat'] = [c[0] for c in coords_list]
    df['lon'] = [c[1] for c in coords_list]
    
    return df

def add_fte_reliability_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Voeg FTE betrouwbaarheidsvlag toe gebaseerd op omzet per FTE."""
    def check_fte_reliability(row):
        omzet = row.get('Omzet_Totaal')
        fte = row.get('FTE_Totaal')
        
        if pd.isna(omzet) or pd.isna(fte) or fte == 0:
            return None  # Kan niet bepalen
        
        omzet_per_fte = omzet / fte
        
        if omzet_per_fte < FTE_MIN_OMZET_PER_FTE:
            return False  # Te weinig omzet per FTE
        elif omzet_per_fte > FTE_MAX_OMZET_PER_FTE:
            return False  # Te veel omzet per FTE
        else:
            return True  # Binnen normale range
    
    df['FTE_Betrouwbaar'] = df.apply(check_fte_reliability, axis=1)
    return df

# ============================================================================
# FILTER FUNCTIONS
# ============================================================================
def filter_data(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Pas alle filters toe op de data."""
    filtered = df.copy()
    
    # Zoeken op naam
    if filters.get('search_query'):
        query = filters['search_query'].lower()
        mask = (
            filtered['Naam'].str.lower().str.contains(query, na=False) |
            filtered['Plaats'].str.lower().str.contains(query, na=False) |
            filtered['KVK'].astype(str).str.contains(query, na=False)
        )
        filtered = filtered[mask]
    
    # Type instelling
    if filters.get('types'):
        type_mask = pd.Series([False] * len(filtered), index=filtered.index)
        for type_col in filters['types']:
            if type_col in filtered.columns:
                type_mask |= (filtered[type_col] == True)
        filtered = filtered[type_mask]
    
    # Provincie
    if filters.get('provincies'):
        filtered = filtered[filtered['Provincie'].isin(filters['provincies'])]
    
    # Omzet range
    if filters.get('omzet_min') is not None:
        filtered = filtered[filtered['Omzet_Totaal'] >= filters['omzet_min']]
    if filters.get('omzet_max') is not None:
        filtered = filtered[filtered['Omzet_Totaal'] <= filters['omzet_max']]
    
    # FTE range
    if filters.get('fte_min') is not None:
        filtered = filtered[filtered['FTE_Totaal'] >= filters['fte_min']]
    if filters.get('fte_max') is not None:
        filtered = filtered[filtered['FTE_Totaal'] <= filters['fte_max']]
    
    # Alleen met FTE data
    if filters.get('only_with_fte'):
        filtered = filtered[filtered['FTE_Totaal'].notna() & (filtered['FTE_Totaal'] > 0)]
    
    # Huishoudelijke hulp
    if filters.get('only_hh'):
        if 'Mogelijk_HH' in filtered.columns:
            filtered = filtered[filtered['Mogelijk_HH'] == True]
    
    # Ouderenzorg
    if filters.get('only_ouderenzorg'):
        if 'Is_Ouderenzorg' in filtered.columns:
            filtered = filtered[filtered['Is_Ouderenzorg'] == True]
    
    # Verzuim filter
    if 'Verzuim_Percentage_Zorgverleners' in filtered.columns:
        if filters.get('verzuim_min') is not None:
            filtered = filtered[
                (filtered['Verzuim_Percentage_Zorgverleners'] >= filters['verzuim_min']) |
                (filtered['Verzuim_Percentage_Zorgverleners'].isna())
            ]
        if filters.get('verzuim_max') is not None:
            filtered = filtered[
                (filtered['Verzuim_Percentage_Zorgverleners'] <= filters['verzuim_max']) |
                (filtered['Verzuim_Percentage_Zorgverleners'].isna())
            ]
    
    # Vacatures filter
    if filters.get('vacatures_min') is not None and 'Vacatures_Clientgebonden' in filtered.columns:
        filtered = filtered[
            (filtered['Vacatures_Clientgebonden'] >= filters['vacatures_min']) |
            (filtered['Vacatures_Clientgebonden'].isna())
        ]
    
    return filtered

# ============================================================================
# MAP FUNCTION
# ============================================================================
def create_map(df: pd.DataFrame, selected_code: str = None, center: tuple = None, zoom: int = None) -> folium.Map:
    """Maak een Folium kaart met markers."""
    
    # Bepaal center en zoom
    if center and zoom:
        map_center = center
        map_zoom = zoom
    elif selected_code:
        # Zoom naar geselecteerde organisatie
        selected_row = df[df['Code'] == selected_code]
        if len(selected_row) > 0 and pd.notna(selected_row.iloc[0].get('lat')):
            map_center = [selected_row.iloc[0]['lat'], selected_row.iloc[0]['lon']]
            map_zoom = 12  # Ingezoomd
        else:
            map_center = [52.1326, 5.2913]
            map_zoom = 7
    else:
        map_center = [52.1326, 5.2913]
        map_zoom = 7
    
    m = folium.Map(location=map_center, zoom_start=map_zoom, tiles='cartodbpositron')
    
    for idx, row in df.iterrows():
        if pd.notna(row.get('lat')) and pd.notna(row.get('lon')):
            # Bepaal kleur
            color = 'gray'
            if row.get('Is_VVT') == True:
                color = 'blue'
            elif row.get('Is_GGZ') == True:
                color = 'green'
            elif row.get('Is_GHZ') == True:
                color = 'orange'
            elif row.get('Is_MSI') == True:
                color = 'red'
            elif row.get('Is_WMO_Anders') == True or row.get('Is_WMO_Opvang') == True:
                color = 'purple'
            
            # Bepaal grootte
            omzet = row.get('Omzet_Totaal', 0) or 0
            if omzet > 100_000_000:
                radius = 12
            elif omzet > 50_000_000:
                radius = 9
            elif omzet > 10_000_000:
                radius = 6
            else:
                radius = 4
            
            # Highlight geselecteerde
            is_selected = selected_code and row.get('Code') == selected_code
            if is_selected:
                radius = 18
                color = 'darkred'
            
            code = row.get('Code', '')
            naam = row.get('Naam', 'Onbekend')
            
            popup_html = f"""
            <div style="width:220px; font-family: Arial, sans-serif;">
                <b style="font-size: 14px;">{naam}</b><br>
                <hr style="margin: 5px 0;">
                📍 {row.get('Plaats', '')} ({row.get('Postcode', '')})<br>
                💰 €{omzet/1_000_000:.1f}M<br>
                👥 {row.get('FTE_Totaal', 'n.v.t.')} FTE<br>
                <hr style="margin: 5px 0;">
                <small>Code: {code}</small>
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

# ============================================================================
# CHART FUNCTION
# ============================================================================
def create_omzet_chart(row: pd.Series) -> go.Figure:
    """Maak een omzet verdeling chart."""
    labels, values = [], []
    
    if pd.notna(row.get('Omzet_ZVW')) and row.get('Omzet_ZVW', 0) > 0:
        labels.append('ZVW')
        values.append(row['Omzet_ZVW'])
    if pd.notna(row.get('Omzet_WLZ')) and row.get('Omzet_WLZ', 0) > 0:
        labels.append('WLZ')
        values.append(row['Omzet_WLZ'])
    if pd.notna(row.get('Omzet_WMO')) and row.get('Omzet_WMO', 0) > 0:
        labels.append('WMO')
        values.append(row['Omzet_WMO'])
    
    if not values:
        return None
    
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=.4,
        marker_colors=['#667eea', '#764ba2', '#f093fb']
    )])
    fig.update_layout(showlegend=True, height=200, margin=dict(l=20, r=20, t=20, b=20))
    return fig

# ============================================================================
# EXPORT FUNCTION
# ============================================================================
def export_to_excel(df: pd.DataFrame) -> bytes:
    """Exporteer gefilterde data naar Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Gefilterde Data', index=False)
    return output.getvalue()

# ============================================================================
# DETAIL PANEL
# ============================================================================
def show_detail_panel(org: pd.Series):
    """Toon detail panel voor geselecteerde organisatie."""
    
    st.markdown(f"## {org.get('Naam', 'Onbekend')}")
    st.markdown(f"📍 {org.get('Straat', '')} {org.get('Huisnummer', '')}, {org.get('Postcode', '')} {org.get('Plaats', '')}")
    
    # Type badges
    types = []
    if org.get('Is_VVT') == True: types.append("VVT")
    if org.get('Is_GGZ') == True: types.append("GGZ")
    if org.get('Is_GHZ') == True: types.append("GHZ")
    if org.get('Is_MSI') == True: types.append("MSI")
    if org.get('Is_WMO_Anders') == True: types.append("WMO")
    st.markdown(f"**Type:** {', '.join(types) if types else 'Onbekend'}")
    
    # FTE Betrouwbaarheid badge
    fte_betrouwbaar = org.get('FTE_Betrouwbaar')
    if fte_betrouwbaar == False:
        st.markdown('<span class="warning-badge">⚠️ FTE data mogelijk onbetrouwbaar</span>', unsafe_allow_html=True)
    elif fte_betrouwbaar == True:
        st.markdown('<span class="success-badge">✅ FTE data betrouwbaar</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Tabs
    detail_tabs = st.tabs(["📊 Overzicht", "💰 Financieel", "👥 Personeel", "👔 Bestuur"])
    
    with detail_tabs[0]:
        st.markdown("**Kerngegevens**")
        st.markdown(f"- **KVK:** {org.get('KVK', '-')}")
        st.markdown(f"- **Rechtsvorm:** {org.get('Rechtsvorm', '-')}")
        st.markdown(f"- **Provincie:** {org.get('Provincie', '-')}")
        
        if org.get('Is_VVT') == True:
            st.markdown("**VVT Details:**")
            vvt_types = []
            if org.get('VVT_Wijkverpleging') == True: vvt_types.append("Wijkverpleging")
            if org.get('VVT_Verpleeghuiszorg') == True: vvt_types.append("Verpleeghuiszorg")
            if org.get('VVT_Kraamzorg') == True: vvt_types.append("Kraamzorg")
            if org.get('VVT_GRZ') == True: vvt_types.append("GRZ")
            st.markdown(f"  {', '.join(vvt_types) if vvt_types else '-'}")
        
        if 'SBI_Code_1' in org.index and pd.notna(org.get('SBI_Code_1')):
            st.markdown(f"**SBI:** {org.get('SBI_Code_1')} - {org.get('SBI_Omschrijving_1', '')}")
    
    with detail_tabs[1]:
        omzet = org.get('Omzet_Totaal')
        if pd.notna(omzet):
            st.metric("Totale Omzet", f"€{omzet/1_000_000:.1f}M")
            
            omzet_vj = org.get('Omzet_Vorig_Jaar')
            if pd.notna(omzet_vj) and omzet_vj > 0:
                groei = ((omzet - omzet_vj) / omzet_vj) * 100
                st.metric("Groei", f"{groei:+.1f}%")
            
            fig = create_omzet_chart(org)
            if fig:
                st.markdown("**Omzet Verdeling:**")
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("**Details:**")
            for label, col in [("ZVW", "Omzet_ZVW"), ("WLZ", "Omzet_WLZ"), ("WMO", "Omzet_WMO")]:
                val = org.get(col)
                st.markdown(f"- {label}: €{val/1_000_000:.1f}M" if pd.notna(val) else f"- {label}: -")
        else:
            st.info("Geen omzet data beschikbaar")
        
        st.markdown("---")
        st.markdown("**Balans:**")
        for label, col in [("Activa", "Totaal_Activa"), ("Eigen Vermogen", "Eigen_Vermogen")]:
            val = org.get(col)
            st.markdown(f"- {label}: €{val/1_000_000:.1f}M" if pd.notna(val) else f"- {label}: -")
        
        resultaat = org.get('Resultaat_Na_Belasting')
        if pd.notna(resultaat):
            color = "🟢" if resultaat >= 0 else "🔴"
            st.markdown(f"- Resultaat: {color} €{resultaat/1_000_000:.1f}M")
    
    with detail_tabs[2]:
        fte = org.get('FTE_Totaal')
        
        if pd.notna(fte):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.metric("Totaal FTE", f"{fte:,.0f}")
            with col2:
                if org.get('FTE_Betrouwbaar') == False:
                    st.warning("⚠️")
                elif org.get('FTE_Betrouwbaar') == True:
                    st.success("✅")
            
            omzet = org.get('Omzet_Totaal')
            if pd.notna(omzet) and fte > 0:
                omzet_per_fte = omzet / fte
                st.markdown(f"**Omzet per FTE:** €{omzet_per_fte:,.0f}")
                if omzet_per_fte < FTE_MIN_OMZET_PER_FTE or omzet_per_fte > FTE_MAX_OMZET_PER_FTE:
                    st.caption(f"⚠️ Buiten normale range (€{FTE_MIN_OMZET_PER_FTE:,} - €{FTE_MAX_OMZET_PER_FTE:,})")
            
            st.markdown("**Verdeling:**")
            for label, col in [("Zorgpersoneel", "FTE_Zorgpersoneel"), ("Loondienst", "FTE_Loondienst"), 
                              ("Ingehuurd", "FTE_Ingehuurd"), ("Zelfstandig", "FTE_Zelfstandig")]:
                val = org.get(col)
                st.markdown(f"- {label}: {val:,.0f}" if pd.notna(val) else f"- {label}: -")
        else:
            st.info("Geen FTE data beschikbaar")
        
        st.markdown("---")
        st.markdown("**Verzuim & Vacatures:**")
        
        # VERZUIM - Gebruik Verzuim_Percentage_Zorgverleners
        verzuim = org.get('Verzuim_Percentage_Zorgverleners')
        if pd.notna(verzuim):
            verzuim_color = "🟢" if verzuim < 5 else "🟠" if verzuim < 8 else "🔴"
            st.markdown(f"- Verzuim zorgverleners: {verzuim_color} **{verzuim:.1f}%**")
        else:
            st.markdown("- Verzuim zorgverleners: -")
        
        # VACATURES - Gebruik Vacatures_Clientgebonden
        vacatures = org.get('Vacatures_Clientgebonden')
        if pd.notna(vacatures):
            st.markdown(f"- Vacatures (cliëntgebonden): **{vacatures:.0f}**")
        else:
            st.markdown("- Vacatures (cliëntgebonden): -")
        
        vacatures_moeilijk = org.get('Vacatures_Clientgebonden_Moeilijk')
        if pd.notna(vacatures_moeilijk):
            st.markdown(f"- Waarvan moeilijk vervulbaar: {vacatures_moeilijk:.0f}")
    
    with detail_tabs[3]:
        st.markdown("**Functionarissen:**")
        has_func = False
        for i in range(1, 6):
            naam = org.get(f'Func{i}_Naam')
            functie = org.get(f'Func{i}_Functie')
            if pd.notna(naam) and str(naam).strip():
                has_func = True
                st.markdown(f"**👤 {naam}**")
                if pd.notna(functie):
                    st.markdown(f"   {functie}")
                st.markdown("")
        
        if not has_func:
            st.info("Geen functionarissen data beschikbaar")

# ============================================================================
# MAIN APP
# ============================================================================
def main():
    # Header
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.markdown('<p class="main-header">🏥 Primio Prospect Tool</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">DigiMV Zorgorganisaties Database</p>', unsafe_allow_html=True)
    
    # Load data
    data_file = st.sidebar.file_uploader("📂 Upload Master Excel", type=['xlsx', 'xls'])
    
    df = None
    
    if data_file is not None:
        df = pd.read_excel(data_file)
        st.sidebar.success(f"✅ {len(df)} organisaties geladen")
    else:
        default_path = "output/DigiMV_Master_Database.xlsx"
        if os.path.exists(default_path):
            df = load_data(default_path)
            st.sidebar.success(f"✅ Default bestand geladen")
        else:
            st.info("👆 Upload de DigiMV Master Excel om te beginnen, of plaats het bestand in 'output/DigiMV_Master_Database.xlsx'")
            st.stop()
    
    if df is None or df.empty:
        st.error("Geen data geladen")
        st.stop()
    
    # Add coordinates and FTE reliability flag
    df = add_coordinates(df)
    df = add_fte_reliability_flag(df)
    
    # ========================================================================
    # SIDEBAR FILTERS
    # ========================================================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔍 Filters")
    
    filters = {}
    
    # Search
    filters['search_query'] = st.sidebar.text_input(
        "🔎 Zoek organisatie",
        placeholder="Naam, plaats of KVK...",
        help="Zoek op organisatienaam, plaatsnaam of KVK-nummer"
    )
    
    st.sidebar.markdown("---")
    
    # Type instelling
    st.sidebar.markdown("### 🏥 Type Instelling")
    type_options = {
        'Is_VVT': 'VVT',
        'Is_GGZ': 'GGZ',
        'Is_GHZ': 'GHZ',
        'Is_MSI': 'MSI',
        'Is_WMO_Opvang': 'WMO Opvang',
        'Is_WMO_Anders': 'WMO Anders',
        'Is_WLZ_GGZ': 'WLZ-GGZ'
    }
    
    selected_types = []
    for col, label in type_options.items():
        if col in df.columns:
            count = (df[col] == True).sum()
            if st.sidebar.checkbox(f"{label} ({count})", value=(col in ['Is_VVT', 'Is_GGZ', 'Is_GHZ']), key=f"type_{col}"):
                selected_types.append(col)
    filters['types'] = selected_types
    
    st.sidebar.markdown("---")
    
    # Provincie
    st.sidebar.markdown("### 📍 Provincie")
    if 'Provincie' in df.columns:
        all_provinces = sorted(df['Provincie'].dropna().unique().tolist())
        filters['provincies'] = st.sidebar.multiselect(
            "Selecteer provincies",
            options=all_provinces,
            default=[],
            help="Laat leeg voor alle provincies"
        )
        if not filters['provincies']:
            filters['provincies'] = None
    
    st.sidebar.markdown("---")
    
    # Omzet
    st.sidebar.markdown("### 💰 Omzet")
    omzet_col = st.sidebar.columns(2)
    with omzet_col[0]:
        omzet_min = st.number_input("Min (€M)", min_value=0.0, value=0.0, step=1.0, key="omzet_min")
        filters['omzet_min'] = omzet_min * 1_000_000 if omzet_min > 0 else None
    with omzet_col[1]:
        omzet_max = st.number_input("Max (€M)", min_value=0.0, value=0.0, step=1.0, key="omzet_max")
        filters['omzet_max'] = omzet_max * 1_000_000 if omzet_max > 0 else None
    
    st.sidebar.markdown("---")
    
    # FTE
    st.sidebar.markdown("### 👥 FTE (Personeel)")
    fte_categories = ["Alle", "Zeer Klein (<50)", "Klein (50-150)", "Middel (150-500)", "Groot (500-1500)", "Zeer Groot (>1500)"]
    selected_fte_cat = st.sidebar.selectbox("FTE Categorie", fte_categories, key="fte_cat")
    
    if selected_fte_cat != "Alle":
        fte_ranges = {
            "Zeer Klein (<50)": (0, 50),
            "Klein (50-150)": (50, 150),
            "Middel (150-500)": (150, 500),
            "Groot (500-1500)": (500, 1500),
            "Zeer Groot (>1500)": (1500, None)
        }
        filters['fte_min'], filters['fte_max'] = fte_ranges[selected_fte_cat]
    
    filters['only_with_fte'] = st.sidebar.checkbox("Alleen met FTE data", value=False, key="only_fte")
    
    st.sidebar.markdown("---")
    
    # Verzuim filter (NIEUW)
    st.sidebar.markdown("### 🏥 Verzuim Zorgverleners")
    if 'Verzuim_Percentage_Zorgverleners' in df.columns:
        verzuim_range = st.sidebar.slider(
            "Verzuim %",
            min_value=0.0,
            max_value=20.0,
            value=(0.0, 20.0),
            step=0.5,
            key="verzuim_slider"
        )
        if verzuim_range != (0.0, 20.0):
            filters['verzuim_min'] = verzuim_range[0]
            filters['verzuim_max'] = verzuim_range[1]
    else:
        st.sidebar.caption("Verzuim data niet beschikbaar")
    
    st.sidebar.markdown("---")
    
    # Vacatures filter (NIEUW)
    st.sidebar.markdown("### 📋 Vacatures Cliëntgebonden")
    if 'Vacatures_Clientgebonden' in df.columns:
        vacatures_min = st.sidebar.number_input(
            "Minimaal aantal",
            min_value=0,
            value=0,
            step=1,
            key="vacatures_min"
        )
        if vacatures_min > 0:
            filters['vacatures_min'] = vacatures_min
    else:
        st.sidebar.caption("Vacatures data niet beschikbaar")
    
    st.sidebar.markdown("---")
    
    # Extra filters
    st.sidebar.markdown("### 🎯 Extra Filters")
    filters['only_hh'] = st.sidebar.checkbox("Mogelijk huishoudelijke hulp", value=False, key="only_hh")
    filters['only_ouderenzorg'] = st.sidebar.checkbox("Alleen ouderenzorg", value=False, key="only_ouderenzorg")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Reset Filters", use_container_width=True):
        st.rerun()
    
    # ========================================================================
    # APPLY FILTERS
    # ========================================================================
    filtered_df = filter_data(df, filters)
    
    # ========================================================================
    # METRICS BAR
    # ========================================================================
    st.markdown("---")
    metric_cols = st.columns(5)
    
    with metric_cols[0]:
        st.metric("📊 Organisaties", f"{len(filtered_df):,}")
    with metric_cols[1]:
        total_omzet = filtered_df['Omzet_Totaal'].sum() / 1_000_000_000
        st.metric("💰 Totale Omzet", f"€{total_omzet:.1f}B")
    with metric_cols[2]:
        total_fte = filtered_df['FTE_Totaal'].sum()
        st.metric("👥 Totaal FTE", f"{total_fte:,.0f}")
    with metric_cols[3]:
        if 'FTE_Betrouwbaar' in filtered_df.columns:
            unreliable = (filtered_df['FTE_Betrouwbaar'] == False).sum()
            st.metric("⚠️ FTE Onbetrouwbaar", f"{unreliable}")
    with metric_cols[4]:
        if 'Mogelijk_HH' in filtered_df.columns:
            hh_count = (filtered_df['Mogelijk_HH'] == True).sum()
            st.metric("🏠 Mogelijk HH", f"{hh_count}")
    
    # Export button
    with col_header2:
        st.markdown("<br>", unsafe_allow_html=True)
        excel_data = export_to_excel(filtered_df)
        st.download_button(
            label="💾 Export naar Excel",
            data=excel_data,
            file_name=f"DigiMV_Export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # ========================================================================
    # MAIN CONTENT
    # ========================================================================
    st.markdown("---")
    
    # Session state
    if 'selected_org' not in st.session_state:
        st.session_state.selected_org = None
    
    # Layout: Main (map + table) | Details
    col_main, col_details = st.columns([2, 1])
    
    with col_main:
        # KAART
        st.markdown("### 🗺️ Kaart")
        if len(filtered_df) > 0:
            map_df = filtered_df.head(500)
            if len(filtered_df) > 500:
                st.warning(f"⚠️ Toont eerste 500 van {len(filtered_df)} organisaties")
            
            # Maak kaart met eventuele zoom naar geselecteerde org
            m = create_map(map_df, st.session_state.selected_org)
            map_data = st_folium(
                m, 
                width=None, 
                height=400, 
                returned_objects=["last_object_clicked_popup"],
                key="main_map"
            )
            
            # Detecteer klik op kaart → toon details
            if map_data and map_data.get("last_object_clicked_popup"):
                popup_content = str(map_data["last_object_clicked_popup"])
                if "Code:" in popup_content:
                    try:
                        code_start = popup_content.find("Code:") + 5
                        code_end = popup_content.find("</small>", code_start)
                        if code_end == -1:
                            code_end = popup_content.find("</div>", code_start)
                        if code_end == -1:
                            code_end = len(popup_content)
                        clicked_code = popup_content[code_start:code_end].strip()
                        # Clean up any HTML tags
                        clicked_code = clicked_code.replace("</small>", "").replace("</div>", "").strip()
                        
                        if clicked_code and clicked_code != st.session_state.selected_org:
                            st.session_state.selected_org = clicked_code
                            st.rerun()
                    except Exception:
                        pass
            
            st.caption("**Legenda:** 🔵 VVT | 🟢 GGZ | 🟠 GHZ | 🔴 MSI | 🟣 WMO — *Grootte = Omzet* — 🔴 Groot = Geselecteerd")
        else:
            st.info("Geen organisaties gevonden")
        
        st.markdown("---")
        
        # TABEL (onder de kaart)
        st.markdown("### 📋 Tabel")
        if len(filtered_df) > 0:
            display_cols = ['Naam', 'Plaats', 'Postcode', 'Omzet_Totaal', 'FTE_Totaal', 'FTE_Betrouwbaar']
            if 'Verzuim_Percentage_Zorgverleners' in filtered_df.columns:
                display_cols.append('Verzuim_Percentage_Zorgverleners')
            if 'Vacatures_Clientgebonden' in filtered_df.columns:
                display_cols.append('Vacatures_Clientgebonden')
            
            display_df = filtered_df[['Code'] + [c for c in display_cols if c in filtered_df.columns]].copy()
            
            # Format
            if 'Omzet_Totaal' in display_df.columns:
                display_df['Omzet_Totaal'] = display_df['Omzet_Totaal'].apply(
                    lambda x: f"€{x/1_000_000:.1f}M" if pd.notna(x) else "-")
            if 'FTE_Totaal' in display_df.columns:
                display_df['FTE_Totaal'] = display_df['FTE_Totaal'].apply(
                    lambda x: f"{x:,.0f}" if pd.notna(x) else "-")
            if 'FTE_Betrouwbaar' in display_df.columns:
                display_df['FTE_Betrouwbaar'] = display_df['FTE_Betrouwbaar'].apply(
                    lambda x: "✅" if x == True else "⚠️" if x == False else "-")
            if 'Verzuim_Percentage_Zorgverleners' in display_df.columns:
                display_df['Verzuim_Percentage_Zorgverleners'] = display_df['Verzuim_Percentage_Zorgverleners'].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "-")
            if 'Vacatures_Clientgebonden' in display_df.columns:
                display_df['Vacatures_Clientgebonden'] = display_df['Vacatures_Clientgebonden'].apply(
                    lambda x: f"{x:.0f}" if pd.notna(x) else "-")
            
            display_df = display_df.rename(columns={
                'Omzet_Totaal': 'Omzet',
                'FTE_Totaal': 'FTE',
                'FTE_Betrouwbaar': 'FTE OK',
                'Verzuim_Percentage_Zorgverleners': 'Verzuim',
                'Vacatures_Clientgebonden': 'Vacatures'
            })
            
            # Highlight geselecteerde rij
            selected_idx = None
            if st.session_state.selected_org:
                matches = display_df[display_df['Code'] == st.session_state.selected_org].index.tolist()
                if matches:
                    selected_idx = display_df.index.get_loc(matches[0]) if matches[0] in display_df.index else None
            
            st.markdown(f"**{len(filtered_df)} organisaties** - Klik op een rij → details rechts + zoom op kaart")
            
            selected_rows = st.dataframe(
                display_df.drop(columns=['Code']),
                use_container_width=True,
                height=300,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Tabel klik → selecteer organisatie → kaart zoomt in
            if selected_rows and selected_rows.selection.rows:
                selected_idx = selected_rows.selection.rows[0]
                new_code = display_df.iloc[selected_idx]['Code']
                if new_code != st.session_state.selected_org:
                    st.session_state.selected_org = new_code
                    st.rerun()  # Rerun om kaart te updaten met zoom
    
    # DETAILS PANEL
    with col_details:
        st.markdown("### 📋 Details")
        
        if st.session_state.selected_org:
            org_data = filtered_df[filtered_df['Code'] == st.session_state.selected_org]
            
            if len(org_data) > 0:
                show_detail_panel(org_data.iloc[0])
                
                if st.button("❌ Deselecteer", use_container_width=True):
                    st.session_state.selected_org = None
                    st.rerun()
            else:
                st.info("Organisatie niet in huidige filter")
                if st.button("🔄 Reset selectie"):
                    st.session_state.selected_org = None
                    st.rerun()
        else:
            st.info("👈 Klik op de kaart of een rij in de tabel voor details")
    
    # Footer
    st.markdown("---")
    st.caption(f"DigiMV 2024 | {len(df)} organisaties | FTE range: €{FTE_MIN_OMZET_PER_FTE:,} - €{FTE_MAX_OMZET_PER_FTE:,}/FTE")

if __name__ == "__main__":
    main()
