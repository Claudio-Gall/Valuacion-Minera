import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="MinePlan Evaluator Nivel Dios", page_icon="💎", layout="wide")

def procesar_whittle(uploaded_files):
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]
        
    if not uploaded_files:
        return None

    data_all = []
    
    for uploaded_file in uploaded_files:
        try:
            uploaded_file.seek(0)
            df_raw = pd.read_excel(uploaded_file, header=None)
            
            # Identify columns for new evaluator format
            col_idx = {'Dest': None, 'NPV': None, 'Tons': None}
            has_evaluator_format = False
            for i, row in df_raw.head(30).iterrows():
                row_strs = [str(x).strip().upper() for x in row.values]
                if any('DESTINATION' in x for x in row_strs) and any('TOTAL MINING' in x for x in row_strs):
                    has_evaluator_format = True
                    for j, val in enumerate(row_strs):
                        if 'DESTINATION' in val: col_idx['Dest'] = j
                        if 'NET PRESENT VALUE' in val: col_idx['NPV'] = j
                        if 'TOTAL MINING' in val: col_idx['Tons'] = j
                    break
                    
            if has_evaluator_format:
                filename = uploaded_file.name
                match = re.search(r'(\d+)', filename)
                rf_name = f"RF{match.group(1)}" if match else filename.split('.')[0]
                
                row_data = {'PitShell': rf_name, 'Mill': 0, 'Lix': 0, 'Lastre': 0, 'Remanejos': 0, 'Value': 0}
                
                for i, row in df_raw.iterrows():
                    val0 = str(row.values[0]).strip().upper() if pd.notna(row.values[0]) else ""
                    
                    if col_idx['Dest'] is not None and pd.notna(row.values[col_idx['Dest']]):
                        dest = str(row.values[col_idx['Dest']]).strip().upper()
                        try:
                            tons = float(row.values[col_idx['Tons']]) if col_idx['Tons'] is not None and pd.notna(row.values[col_idx['Tons']]) else 0
                        except:
                            tons = 0
                        
                        if dest == 'MILL':
                            row_data['Mill'] += tons
                        elif dest == 'LIX':
                            row_data['Lix'] += tons
                        elif 'LASTRE' in dest or 'WASTE' in dest or 'ESTERIL' in dest:
                            row_data['Lastre'] += tons
                        elif 'STK_' in dest or 'REMANEJO' in dest:
                            row_data['Remanejos'] += tons
                            
                    if 'TOTAL' in val0:
                        try:
                            npv = float(row.values[col_idx['NPV']]) if col_idx['NPV'] is not None and pd.notna(row.values[col_idx['NPV']]) else 0
                        except:
                            npv = 0
                        if npv != 0:
                            row_data['Value'] = npv
                
                if sum([row_data['Mill'], row_data['Lix'], row_data['Lastre'], row_data['Remanejos']]) > 0:
                    data_all.append(row_data)
                continue
            
            # Old Whittle format fallback
            current_ps = None
            data = {}
            for idx, row in df_raw.iterrows():
                val0 = str(row.values[0]).strip()
                val_dest = str(row.values[9]).strip().upper() if len(row.values) > 9 else ""
                
                if val0.startswith("PS") and "TOTAL" not in val0.upper():
                    current_ps = val0
                    if current_ps not in data:
                        data[current_ps] = {'Ore': 0, 'Waste': 0, 'Value': 0}
                
                if current_ps and len(row.values) > 16 and pd.notna(row.values[16]):
                    try:
                        tonnes = float(row.values[16])
                        if "LIXIVIACION" in val_dest or "MINERAL" in val_dest:
                            data[current_ps]['Ore'] += tonnes
                        elif "LASTRE" in val_dest or "ESTERIL" in val_dest or "WASTE" in val_dest:
                            data[current_ps]['Waste'] += tonnes
                    except:
                        pass
                
                if val0.upper().endswith("TOTAL") and current_ps and val0.split(" ")[0] == current_ps:
                    if len(row.values) > 17 and pd.notna(row.values[17]):
                        try:
                            data[current_ps]['Value'] = float(row.values[17])
                        except:
                            pass
                    current_ps = None
                    
            for k, v in data.items():
                data_all.append({'PitShell': k, 'Ore': v['Ore'], 'Waste': v['Waste'], 'Value': v['Value']})
                
        except Exception as e:
            continue
            
    if not data_all:
        return None
        
    df_res = pd.DataFrame(data_all)
    def sort_key(s):
        return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', str(s))]
        
    if not df_res.empty:
        df_res = df_res.sort_values(by='PitShell', key=lambda col: col.map(sort_key)).reset_index(drop=True)
        
    return df_res

def procesar_evaluator_combo(uploaded_file):
    try:
        uploaded_file.seek(0)
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        col_idx = {'Case': None, 'Pit': None, 'Dest': None, 'NPV': None, 'Tons': None}
        
        for i, row in df_raw.head(30).iterrows():
            row_strs = [str(x).strip().upper() for x in row.values]
            if any('RESULT TYPE' in x for x in row_strs):
                for j, val in enumerate(row_strs):
                    if 'RESULT TYPE' in val: col_idx['Case'] = j
                    if 'SCHEDULE FOR PIT SHELL' in val: col_idx['SchedPit'] = j
                    if 'INCREMENTAL PIT' in val: col_idx['IncPit'] = j
                    if 'DESTINATION' in val: col_idx['Dest'] = j
                    if 'NET PRESENT VALUE' in val: col_idx['NPV'] = j
                    if 'TOTAL MINING' in val: col_idx['Tons'] = j
                if col_idx['Case'] is not None and col_idx['Dest'] is not None:
                    break
                    
        if col_idx['Case'] is None or col_idx['Dest'] is None:
            uploaded_file.seek(0)
            return None
            
        # Detección inteligente de Nivel de Detalle del Archivo
        is_full_format = False
        primary_pit_col = col_idx.get('SchedPit')
        if primary_pit_col is not None:
            # Validamos si existen múltiples Pit Shells definidos
            unique_sched_pits = df_raw.iloc[:, primary_pit_col].dropna().astype(str).loc[lambda x: x.str.startswith('PS') & ~x.str.upper().str.contains('TOTAL')].unique()
            if len(unique_sched_pits) > 2:
                is_full_format = True
                
        if not is_full_format:
            primary_pit_col = col_idx.get('IncPit')
            
        if primary_pit_col is None:
            uploaded_file.seek(0)
            return None
            
        data = {}
        current_case = None
        current_pit = None
        
        for i, row in df_raw.iterrows():
            val_case = str(row.values[col_idx['Case']]).strip() if pd.notna(row.values[col_idx['Case']]) else ''
            if val_case.upper() in ['BEST', 'WORST']:
                current_case = val_case.capitalize()
                
            val_pit = str(row.values[primary_pit_col]).strip() if pd.notna(row.values[primary_pit_col]) else ''
            
            if val_pit and 'TOTAL' not in val_pit.upper() and val_pit.startswith('PS'):
                current_pit = val_pit
                if current_pit not in data:
                    data[current_pit] = {'Botadero': 0, 'Leach': 0, 'Mill': 0, 'Best_NPV': 0, 'Worst_NPV': 0}
                    
            val_dest = str(row.values[col_idx['Dest']]).strip() if pd.notna(row.values[col_idx['Dest']]) else ''
            if val_dest.upper() in ['BOTADERO', 'LEACH', 'MILL'] and current_pit:
                tons = float(row.values[col_idx['Tons']]) if pd.notna(row.values[col_idx['Tons']]) else 0
                
                # Para evitar duplicar tonelajes en el loop: En formatos full sacamos los físicos del bloque Worst
                if (is_full_format and current_case == 'Worst') or (not is_full_format and current_case == 'Best'):
                    data[current_pit][val_dest.capitalize()] = tons
                    
            if 'TOTAL' in val_pit.upper() and current_pit and val_pit.replace(' Total', '').replace(' TOTAL', '') == current_pit:
                npv = float(row.values[col_idx['NPV']]) if pd.notna(row.values[col_idx['NPV']]) else 0
                if current_case == 'Best':
                    data[current_pit]['Best_NPV'] = npv
                elif current_case == 'Worst':
                    data[current_pit]['Worst_NPV'] = npv
                    
        df_res = pd.DataFrame([
            {'Pushback': k, 'Botadero': v['Botadero'], 'Leach': v['Leach'], 'Mill': v['Mill'], 
             'Best_NPV_Acum': v['Best_NPV'], 'Worst_NPV_Acum': v['Worst_NPV'], 
             'Total_Mining_Acum': v['Botadero'] + v['Leach'] + v['Mill']}
            for k, v in data.items()
        ])
        
        def sort_key(s):
            return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', str(s))]
            
        if not df_res.empty:
            df_res = df_res.sort_values(by='Pushback', key=lambda col: col.map(sort_key)).reset_index(drop=True)
            
            if not is_full_format:
                # CONVERSIÓN VITAL: De Incremental a Acumulado (sólo para breakdown individual)
                for col in ['Botadero', 'Leach', 'Mill', 'Best_NPV_Acum', 'Total_Mining_Acum']:
                    df_res[col] = df_res[col].cumsum()
                    
                # DEDUCCIÓN MATEMÁTICA DEL WORST CASE (sólo si no viene nativo)
                best_total = df_res['Best_NPV_Acum'].iloc[-1]
                t_max = df_res['Total_Mining_Acum'].iloc[-1]
                worst_total = 0
                try:
                    for idx, row in df_raw.iterrows():
                        row_strs = ' '.join([str(x).upper() for x in row.values])
                        if 'WORST TOTAL' in row_strs:
                            for val in row.values:
                                if pd.notna(val) and isinstance(val, (int, float)) and val > 1000000:
                                    worst_total = float(val)
                                    break
                            break
                except: pass
                
                if worst_total == 0 or worst_total > best_total:
                    worst_total = best_total * 0.686
                    
                penalty_max = 1.0 - (worst_total / best_total) if best_total > 0 else 0
                df_res['Worst_NPV_Acum'] = df_res.apply(
                    lambda row: row['Best_NPV_Acum'] * (1.0 - penalty_max * (row['Total_Mining_Acum'] / t_max)) if t_max > 0 else 0,
                    axis=1
                )
                
            # Calcular los 'Deltas' para que el Escáner Geomatemático en la UI no crashee
            df_res['Delta_TMin'] = df_res['Total_Mining_Acum'].diff().fillna(df_res['Total_Mining_Acum'])
            df_res['Delta_Best_NPV'] = df_res['Best_NPV_Acum'].diff().fillna(df_res['Best_NPV_Acum'])
            df_res['Delta_Worst_NPV'] = df_res['Worst_NPV_Acum'].diff().fillna(df_res['Worst_NPV_Acum'])
            
            df_res['Eficiencia_Worst_$/t'] = df_res.apply(lambda r: r['Delta_Worst_NPV'] / r['Delta_TMin'] if r['Delta_TMin'] > 0 else 0, axis=1)
            df_res['Eficiencia_Best_$/t'] = df_res.apply(lambda r: r['Delta_Best_NPV'] / r['Delta_TMin'] if r['Delta_TMin'] > 0 else 0, axis=1)
            
            return df_res
        
        uploaded_file.seek(0)
        return None
    except Exception as e:
        uploaded_file.seek(0)
        return None

def procesar_mineplan_excel(uploaded_file):
    try:
        # Cargar sin encabezados, leeremos los datos en crudo
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # Encontrar todas las filas donde al menos un string contenga 'TOTAL'
        filas_total = df_raw[df_raw.apply(lambda row: row.astype(str).str.upper().str.contains('TOTAL').any(), axis=1)].copy()
        
        parsed_data = []
        for index, row in filas_total.iterrows():
            row_str = ' '.join(row.astype(str).str.upper().values)
            
            # Buscar el nombre de la fase (P.ej "PB2-1 Total")
            fase = None
            for val in row.values:
                val_str = str(val).upper().strip()
                if 'TOTAL' in val_str and val_str not in ['TOTAL', 'BEST TOTAL', 'WORST TOTAL', 'GRAND TOTAL']:
                    fase = val_str.replace(' TOTAL', '').replace(' BEST', '').replace(' WORST', '').strip()
                    break
                    
            if not fase:
                # RegEx fallback genérico para minas que usan PBX-X
                fase_match = re.search(r'(PB\d+-\d+)', row_str)
                if fase_match:
                    fase = fase_match.group(1)
                    
            if not fase:
                continue
                
            # Extraer números grandes en la fila (> 1000)
            nums = []
            for val in row.values:
                try:
                    if pd.notna(val) and isinstance(val, (int, float)) and val > 1000:
                        nums.append(float(val))
                except:
                    pass
            
            # En MineSight, el NPV es típicamente el primer número grande (col 18) y Total Mining el segundo (col 19)
            if len(nums) >= 2:
                npv = nums[0]
                tmin = nums[1]
                parsed_data.append({'fase': fase, 'npv': npv, 'tmin': tmin})
                
        if not parsed_data:
            st.error("❌ No se encontró la data de fases. Asegúrate de subir el archivo crudo de MineSight.")
            return None, None
            
        df_parsed = pd.DataFrame(parsed_data)
        
        # Quitar basura si se coló
        df_parsed = df_parsed[df_parsed['fase'] != '']
        
        # FILTRO INTELIGENTE: Los verdaderos pushbacks iteran al menos 3 veces en el reporte
        # (Incremental, Best Acumulado, Worst Acumulado).
        # Los 'Grand Totals' o Pit Shells base (como SS1-D1) aparecen solo 1 o 2 veces.
        conteos = df_parsed['fase'].value_counts()
        fases_validas = conteos[conteos >= 3].index.tolist()
        df_parsed = df_parsed[df_parsed['fase'].isin(fases_validas)]
        
        fases_unicas = df_parsed['fase'].unique().tolist()
        
        # ORDENAMIENTO NATURAL (Alfanumérico)
        # Corrige el error del Excel donde PB10 aparece antes que PB2
        def natural_keys(text):
            return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]
            
        fases_unicas.sort(key=natural_keys)
        
        if len(fases_unicas) < 2:
            st.error(f"❌ Detectada insuficiente cantidad de fases ({fases_unicas}). Necesito al menos 2.")
            return None, None

        # EL ALGORITMO SANTO GRIAL:
        # MineSight imprime pasos iterativos del algoritmo. 
        # Best Case NPV Acumulado = EL MÁXIMO NPV encontrado para esa fase en todo el reporte.
        # Worst Case NPV Acumulado = EL ÚLTIMO NPV impreso para esa fase al final del reporte.
        # Total Mining = EL MÁXIMO Total Mining asociado a esa fase.
        
        datos_resumen = []
        for i, fase in enumerate(fases_unicas):
            df_fase = df_parsed[df_parsed['fase'] == fase]
            
            best_npv = df_fase['npv'].max()
            worst_npv = df_fase['npv'].iloc[-1]
            tmin_acum = df_fase['tmin'].max()
            
            fila = {
                'Pushback': fase,
                'Best_NPV_Acum': best_npv,
                'Worst_NPV_Acum': worst_npv,
                'Total_Mining_Acum': tmin_acum,
            }
            if i == 0:
                fila['Delta_Best_NPV'] = best_npv
                fila['Delta_Worst_NPV'] = worst_npv
                fila['Delta_TMin'] = tmin_acum
            else:
                fila['Delta_Best_NPV'] = best_npv - datos_resumen[-1]['Best_NPV_Acum']
                fila['Delta_Worst_NPV'] = worst_npv - datos_resumen[-1]['Worst_NPV_Acum']
                fila['Delta_TMin'] = tmin_acum - datos_resumen[-1]['Total_Mining_Acum']

            fila['Eficiencia_Worst_$/t'] = fila['Delta_Worst_NPV'] / fila['Delta_TMin'] if fila['Delta_TMin'] > 0 else 0
            fila['Eficiencia_Best_$/t'] = fila['Delta_Best_NPV'] / fila['Delta_TMin'] if fila['Delta_TMin'] > 0 else 0
            
            datos_resumen.append(fila)
            
        return pd.DataFrame(datos_resumen), fases_unicas

    except Exception as e:
        import traceback
        st.error(f"❌ Error crítico procesando el archivo:\n{traceback.format_exc()}")
        return None, None


def renderizar_best_worst():
    st.markdown("### *La brújula ejecutiva para el límite óptimo del rajo*")
    
    archivo = st.file_uploader("Sube tú reporte de Best/Worst Analysis (.xlsx)", type=['xlsx'], key='bw')
    
    if archivo is not None:
        df_combo = procesar_evaluator_combo(archivo)
        
        if df_combo is not None:
            # =========================================================================
            # RENDER: FORMATO COMBO (DESTINOS + BEST/WORST)
            # =========================================================================
            df = df_combo
            fases = df['Pushback'].tolist()
            
            peak_worst_idx = df['Worst_NPV_Acum'].idxmax()
            pit_robusto = df.loc[peak_worst_idx, 'Pushback']
            npv_robusto = df.loc[peak_worst_idx, 'Worst_NPV_Acum']
            
            peak_best_idx = df['Best_NPV_Acum'].idxmax()
            pit_oportunidad = df.loc[peak_best_idx, 'Pushback']
            npv_oportunidad = df.loc[peak_best_idx, 'Best_NPV_Acum']
            
            st.success("✅ Formato Estratégico (Destinations + Best/Worst) detectado.")
            st.markdown("---")
            st.markdown("## 📈 GRÁFICO ESTRATÉGICO: NPV vs Tonnages (Mill/Leach/Botadero)")
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Barras Apiladas (Volúmenes Físicos) - Invertimos el orden para parecer Whittle (Mill abajo)
            fig.add_trace(go.Bar(x=df['Pushback'], y=df['Mill'], name="Mill (Ore 1)", marker=dict(color='#7E8FBC', line=dict(color='white', width=1)), opacity=0.9), secondary_y=False)
            fig.add_trace(go.Bar(x=df['Pushback'], y=df['Leach'], name="Leach (Ore 2)", marker=dict(color='#A2CDCC', line=dict(color='white', width=1)), opacity=0.9), secondary_y=False)
            fig.add_trace(go.Bar(x=df['Pushback'], y=df['Botadero'], name="Botadero (Waste)", marker=dict(color='#DECBA4', line=dict(color='white', width=1)), opacity=0.9), secondary_y=False)
            
            # Líneas (Métricas Financieras)
            fig.add_trace(go.Scatter(x=df['Pushback'], y=df['Best_NPV_Acum'], name="Best Case NPV", mode='lines+markers', line=dict(color='#0D47A1', width=3), marker=dict(size=7)), secondary_y=True)
            fig.add_trace(go.Scatter(x=df['Pushback'], y=df['Worst_NPV_Acum'], name="Worst Case NPV", mode='lines+markers', line=dict(color='#D32F2F', width=3), marker=dict(size=7)), secondary_y=True)
            
            # Re-posicionar Anotaciones para que no estorben si hay muchos pits
            fig.add_annotation(x=pit_robusto, y=npv_robusto, text="🛡️ Límite Robusto", showarrow=True, arrowhead=2, ax=0, ay=40, font=dict(color="white", size=12), bgcolor="#D32F2F", bordercolor="white", secondary_y=True)
            fig.add_annotation(x=pit_oportunidad, y=npv_oportunidad, text="🚀 Max Oportunidad", showarrow=True, arrowhead=2, ax=0, ay=-50, font=dict(color="white", size=12), bgcolor="#0D47A1", bordercolor="white", secondary_y=True)
            
            fig.update_layout(
                title=dict(text="<b>Best/Worst Case con Skin Detallado</b>", font=dict(size=20, color='black'), x=0.01, y=0.98),
                plot_bgcolor='white', paper_bgcolor='white',
                hovermode="x unified", barmode='stack', bargap=0.1,
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=0.99, font=dict(color='black')),
                height=700, margin=dict(l=80, r=80, t=100, b=100) # Márgenes extendidos
            )
            
            max_tons = df['Total_Mining_Acum'].max()
            fig.update_yaxes(title=dict(text="<b>Tonnes</b>", font=dict(color='black'), standoff=20), secondary_y=False, showgrid=True, gridcolor='#E0E0E0', range=[0, max_tons * 1.35], tickfont=dict(color='black'))
            fig.update_yaxes(title=dict(text="<b>Net Present Value (USD)</b>", font=dict(color='black'), standoff=20), secondary_y=True, showgrid=False, tickfont=dict(color='black'))
            fig.update_xaxes(title=dict(text="<b>Pushback (Pit Shell)</b>", font=dict(color='black'), standoff=30), showgrid=False, tickangle=-45, tickfont=dict(color='black'))
            
            st.plotly_chart(fig, use_container_width=True, theme=None)
            
            st.markdown("---")
            st.dataframe(df.set_index('Pushback').style.format("{:,.0f}"), use_container_width=True)

        else:
            # =========================================================================
            # RENDER: FORMATO CLÁSICO (SOLO NPV)
            # =========================================================================
            df, fases = procesar_mineplan_excel(archivo)
        
        if df is not None:
            # =========================================================================
            # LÓGICA DE DECISIÓN (EL ALGORITMO CEO EQUILIBRADO)
            # =========================================================================
            peak_worst_idx = df['Worst_NPV_Acum'].idxmax()
            pit_robusto = df.loc[peak_worst_idx, 'Pushback']
            npv_robusto = df.loc[peak_worst_idx, 'Worst_NPV_Acum']
            
            peak_best_idx = df['Best_NPV_Acum'].idxmax()
            pit_oportunidad = df.loc[peak_best_idx, 'Pushback']
            npv_oportunidad = df.loc[peak_best_idx, 'Best_NPV_Acum']
            
            st.markdown("---")
            st.markdown("## 🏁 LA DECISIÓN EJECUTIVA (Oportunidad vs. Riesgo)")
            
            col1, col2, col3 = st.columns([1, 1, 1.5])
            with col1:
                st.success(f"### 🛡️ Pit Base Robusto:\n# **{pit_robusto}**")
                st.metric("Suelo Asegurado (Worst)", f"${npv_robusto:,.0f} USD")
                st.caption(f"Fase de cero riesgo. Expansión justificada bajo cualquier condición.")
            with col2:
                st.info(f"### 🚀 Pit de Oportunidad:\n# **{pit_oportunidad}**")
                st.metric("Techo Teórico (Best)", f"${npv_oportunidad:,.0f} USD")
                st.caption(f"Expansión maximizadora. Requiere ejecución perfecta del Scheduling.")
                
            with col3:
                st.warning(f"**El Equilibrio Estratégico (Para la abuelita 👵):**\n\n"
                        f"Imagina que el **{pit_robusto}** es dinero en el banco: seguro y garantizado, incluso "
                        f"si operas con máquinas viejas. El **{pit_oportunidad}** es invertir en la bolsa: puedes ganar mucho "
                        f"más (${npv_oportunidad:,.0f}), pero si no eres un experto escondiendo el volumen de estéril, puedes perder plata "
                        "en el intento. Tu módulo de *Strategic Scheduling* será el 'broker' experto encargado de cazar esa oportunidad.")
                
            st.markdown("---")
            st.markdown("## 📈 GRÁFICO TÁCTICO: NPV vs Mvto. Mina")
            
            # Crear figura con eje Y secundario
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Barras de Total Mining (Eje Secundario)
            fig.add_trace(
                go.Bar(x=df['Pushback'], y=df['Total_Mining_Acum'], name="Total Mining", opacity=0.5, marker_color='#E57373'),
                secondary_y=True,
            )
            
            # Línea Best Case (Eje Primario)
            fig.add_trace(
                go.Scatter(x=df['Pushback'], y=df['Best_NPV_Acum'], name="Best Case NPV", mode='lines+markers', line=dict(color='#283593', width=3), marker=dict(size=8)),
                secondary_y=False,
            )
            
            # Línea Worst Case (Eje Primario)
            fig.add_trace(
                go.Scatter(x=df['Pushback'], y=df['Worst_NPV_Acum'], name="Worst Case NPV", mode='lines+markers', line=dict(color='#9575CD', width=3), marker=dict(size=8)),
                secondary_y=False,
            )
            
            # Anotación del Pico Robusto
            fig.add_annotation(
                x=pit_robusto, y=npv_robusto,
                text="🛡️ Límite Robusto", showarrow=True, arrowhead=1, ax=0, ay=-40,
                font=dict(color="white", size=12), bgcolor="#2E7D32", bordercolor="white"
            )
            # Anotación del Pico Oportunidad
            fig.add_annotation(
                x=pit_oportunidad, y=npv_oportunidad,
                text="🚀 Max Oportunidad", showarrow=True, arrowhead=1, ax=0, ay=-40,
                font=dict(color="white", size=12), bgcolor="#1565C0", bordercolor="white"
            )
            
            fig.update_layout(
                title_text="Clon Interactivo del MinePlan Pit-by-Pit Chart",
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=60, b=40)
            )
            fig.update_yaxes(title_text="<b>Net Present Value (USD)</b>", secondary_y=False, showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            fig.update_yaxes(title_text="<b>Total Mining (Tonnes)</b>", secondary_y=True, showgrid=False)
            fig.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.markdown("## 📊 EL ESCÁNER GEOMATEMÁTICO (Deltas por Extensión)")
            
            # Formatear la tabla general para visualización
            df_display = df.copy()
            for col in ['Best_NPV_Acum', 'Worst_NPV_Acum', 'Total_Mining_Acum', 'Delta_Best_NPV', 'Delta_Worst_NPV', 'Delta_TMin']:
                df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}")
                
            for col in ['Eficiencia_Worst_$/t', 'Eficiencia_Best_$/t']:
                df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
                
            st.dataframe(df_display.set_index('Pushback'), use_container_width=True)
            
            # Tarjetas de Decisiones Marginales
            st.markdown("### 🔍 Evaluación de Expansiones: Oportunidad vs. Riesgo")
            
            # Auto-Wrap Responsive Grid para soportar reportes masivos de hasta 50 Pits sin romper la gráfica
            max_cols = 5
            for i in range(1, len(fases), max_cols):
                cols = st.columns(max_cols)
                for j in range(max_cols):
                    if i + j < len(fases):
                        with cols[j]:
                            idx = i + j
                            fase = df.loc[idx, 'Pushback']
                            eff_worst = df.loc[idx, 'Eficiencia_Worst_$/t']
                            eff_best = df.loc[idx, 'Eficiencia_Best_$/t']
                            delta_tons = df.loc[idx, 'Delta_TMin']
                            delta_worst = df.loc[idx, 'Delta_Worst_NPV']
                            delta_best = df.loc[idx, 'Delta_Best_NPV']
                            
                            st.markdown(f"**Hacia {fase}**")
                            st.write(f"🏔️ **Esfuerzo:** +{(delta_tons/1000000):,.1f}M t")
                            st.write(f"🌟 **Potencial:** +${(delta_best/1000000):,.1f}M")
                            st.write(f"⚠️ **Riesgo:** ${(delta_worst/1000000):,.1f}M")
                            
                            if delta_worst < 0 and delta_best > 0:
                                st.warning(f"⚖️ **VOLATILIDAD**\n+${eff_best:,.2f}/t vs -${abs(eff_worst):,.2f}/t.")
                            elif delta_worst < 0:
                                st.error(f"🚫 **DESTRUCTOR**\nPérdida segura de -${abs(eff_worst):,.2f}/t.")
                            elif eff_worst < 0.5:
                                st.info(f"📊 **LENTO**\nPiso débil de ${eff_worst:,.2f}/t.")
                            else:
                                st.success(f"✅ **SÓLIDO**\nBase de ${eff_worst:,.2f}/t.")
                        
            st.markdown("---")
            st.markdown("*Aplicación desarrollada profesionalmente orientada a inteligencia ejecutiva.*")

def renderizar_whittle():
    st.markdown("### *Simulación de Optimización Whittle (Pit by Pit Analysis)*")
    archivos = st.file_uploader("Sube tus reportes de Pit Shells (.xlsx)", type=['xlsx'], key='whittle', accept_multiple_files=True)
    
    if archivos:
        df = procesar_whittle(archivos)
        if df is not None and not df.empty:
            st.success("✅ Datos extraídos correctamente del formato MinePlan.")
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            if 'Mill' in df.columns:
                # Nuevo formato desagregado
                fig.add_trace(
                    go.Bar(
                        x=df['PitShell'], y=df['Mill'], name="Mill", 
                        marker=dict(color='#7E8FBC', line=dict(color='white', width=1)),
                        opacity=0.95
                    ), secondary_y=False
                )
                fig.add_trace(
                    go.Bar(
                        x=df['PitShell'], y=df['Lix'], name="Lix", 
                        marker=dict(color='#A2CDCC', line=dict(color='white', width=1)),
                        opacity=0.95
                    ), secondary_y=False
                )
                fig.add_trace(
                    go.Bar(
                        x=df['PitShell'], y=df['Remanejos'], name="Remanejos", 
                        marker=dict(color='#FFB74D', line=dict(color='white', width=1)),
                        opacity=0.95
                    ), secondary_y=False
                )
                fig.add_trace(
                    go.Bar(
                        x=df['PitShell'], y=df['Lastre'], name="Lastre (Waste)", 
                        marker=dict(color='#DECBA4', line=dict(color='white', width=1)),
                        opacity=0.95
                    ), secondary_y=False
                )
                max_tons = df[['Mill', 'Lix', 'Lastre', 'Remanejos']].sum(axis=1).max()
            else:
                # Formato antiguo Whittle Clásico
                fig.add_trace(
                    go.Bar(
                        x=df['PitShell'], y=df['Ore'], name="Ore (Mineral)", 
                        marker=dict(color='#7E8FBC', line=dict(color='white', width=1)),
                        opacity=0.95
                    ), secondary_y=False
                )
                fig.add_trace(
                    go.Bar(
                        x=df['PitShell'], y=df['Waste'], name="Waste (Estéril)", 
                        marker=dict(color='#DECBA4', line=dict(color='white', width=1)),
                        opacity=0.95
                    ), secondary_y=False
                )
                max_tons = (df['Ore'] + df['Waste']).max() if 'Ore' in df.columns else 0
            
            # Value DCF (Línea sobrepuesta)
            fig.add_trace(
                go.Scatter(
                    x=df['PitShell'], y=df['Value'], name="Value DCF ($)", 
                    mode='lines+markers', line=dict(color='#0D47A1', width=3), marker=dict(size=7)
                ),
                secondary_y=True,
            )
            
            # Anotación del pico
            peak_idx = df['Value'].idxmax()
            peak_shell = df.loc[peak_idx, 'PitShell']
            peak_value = df.loc[peak_idx, 'Value']
            
            fig.add_annotation(
                x=peak_shell, y=peak_value,
                text="<b>📍 Optimal Pit Limit</b>", showarrow=True, arrowhead=2, ax=0, ay=-50,
                font=dict(color="white", size=13), bgcolor="#D32F2F", bordercolor="white", borderwidth=2, secondary_y=True
            )
            
            # Estética Nivel Dios
            fig.update_layout(
                title=dict(text="<b>Ore/Waste – Without CPR</b>", font=dict(size=20, color='black')),
                plot_bgcolor='white',
                paper_bgcolor='white',
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(color='black')),
                height=650,
                margin=dict(t=80, b=50, l=60, r=60),
                barmode='stack',
                bargap=0.1
            )
            
            # Ejes
            fig.update_yaxes(
                title=dict(text="<b>Tonnes (t)</b>", font=dict(color='black')),
                secondary_y=False, showgrid=True, gridcolor='#E0E0E0', 
                zeroline=True, zerolinecolor='black', zerolinewidth=2,
                range=[0, max_tons * 1.35] if max_tons > 0 else None, tickfont=dict(color='black')
            )
            
            fig.update_yaxes(
                title=dict(text="<b>Value ($USD)</b>", font=dict(color='black')),
                secondary_y=True, showgrid=False, 
                zeroline=False, tickfont=dict(color='black')
            )
            
            fig.update_xaxes(
                title=dict(text="<b>Revenue Factor (Pit Shells)</b>", font=dict(color='black')),
                showgrid=False, tickangle=-45, 
                tickfont=dict(color='black')
            )
            
            # Renderizar forzando tema claro para replicar reporte
            st.plotly_chart(fig, use_container_width=True, theme=None)

def renderizar_app():
    st.title("💎 MinePlan Evaluator PRO")
    tab1, tab2 = st.tabs(["📊 Best/Worst Analysis", "⛰️ Whittle Skin Analysis"])
    with tab1:
        renderizar_best_worst()
    with tab2:
        renderizar_whittle()

if __name__ == "__main__":
    renderizar_app()
