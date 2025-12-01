import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Valuación Minera Profesional",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CUSTOM (CSS) ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        font-weight: bold;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        background-color: #1E3A8A;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- PERSISTENCIA (URL) ---
def get_param(key, default_val, type_func=float):
    params = st.query_params
    if key in params:
        try:
            return type_func(params[key])
        except:
            return default_val
    return default_val

default_price = get_param("price", 4234.0)
default_mining = get_param("mining", 3.50)

# --- TÍTULO ---
st.markdown('<div class="main-header">⛏️ Simulador de Valuación Minera (NSR & Cut-Off)</div>', unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("⚙️ Parámetros de Entrada")
    
    st.subheader("💰 Mercado")
    def update_url():
        st.query_params["price"] = str(st.session_state.price_input)
        st.query_params["mining"] = str(st.session_state.mining_input)

    price_au = st.number_input("Precio Oro (USD/oz)", value=default_price, step=10.0, format="%.2f", key="price_input", on_change=update_url)
    
    st.subheader("🏭 Costos de Proceso ($/t)")
    cost_mining = st.number_input("Costo Mina (Ore/Waste)", value=default_mining, step=0.1, key="mining_input", on_change=update_url)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Leaching (Óxidos)**")
        cost_leach = st.number_input("Costo Proc.", value=11.00, key="cleach")
        ga_leach = st.number_input("G&A", value=0.50, key="galeach")
        rec_leach = st.number_input("Recuperación (%)", value=80.0, step=1.0, key="recleach") / 100.0
        
    with col2:
        st.markdown("**Milling (Sulfuros)**")
        cost_mill = st.number_input("Costo Proc.", value=20.00, key="cmill")
        ga_mill = st.number_input("G&A", value=0.50, key="gamill")
        rec_mill = st.number_input("Recuperación (%)", value=90.0, step=1.0, key="recmill") / 100.0

    st.subheader("📉 Costos de Venta")
    marketing_pct = st.slider("Marketing Fee (%)", 0.0, 5.0, 1.0, 0.1) / 100.0
    
    with st.expander("Ajustes Avanzados de Venta"):
        fixed_sc_leach = st.number_input("Costo Fijo Venta Leach ($/oz)", value=120.48)
        fixed_sc_mill = st.number_input("Costo Fijo Venta Mill ($/oz)", value=137.51)
        payable_mill = st.number_input("Payable Factor Mill (%)", value=97.5) / 100.0

# --- CÁLCULOS (LOGIC) ---

def calculate_metrics(price, grade, process_type):
    marketing_fee = price * marketing_pct
    
    if process_type == 'LEACH':
        selling_cost = fixed_sc_leach + marketing_fee
        net_price = price - selling_cost
        nsr = grade * rec_leach * net_price / 31.1035
        cost_total = cost_leach + ga_leach + cost_mining
        
    elif process_type == 'MILL':
        selling_cost = fixed_sc_mill + marketing_fee
        net_price = (price * payable_mill) - selling_cost
        nsr = grade * rec_mill * net_price / 31.1035
        cost_total = cost_mill + ga_mill + cost_mining
        
    profit = nsr - cost_total
    return nsr, profit, cost_total

# Calculate Cut-Offs
sc_leach_curr = fixed_sc_leach + (price_au * marketing_pct)
net_price_leach = price_au - sc_leach_curr
factor_leach = rec_leach * net_price_leach / 31.1035
cog_leach = (cost_leach + ga_leach + cost_mining) / factor_leach if factor_leach > 0 else 999

sc_mill_curr = fixed_sc_mill + (price_au * marketing_pct)
net_price_mill = (price_au * payable_mill) - sc_mill_curr
factor_mill = rec_mill * net_price_mill / 31.1035
cog_mill = (cost_mill + ga_mill + cost_mining) / factor_mill if factor_mill > 0 else 999

# --- DASHBOARD ---

# Row 1: KPIs
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <h3>💰 Precio Oro</h3>
        <h2>${price_au:,.2f}</h2>
        <p>USD/oz</p>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <h3>🧪 Cut-Off Leach</h3>
        <h2>{cog_leach:.3f} g/t</h2>
        <p>Óxidos (Low Cost)</p>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="metric-card">
        <h3>⚙️ Cut-Off Mill</h3>
        <h2>{cog_mill:.3f} g/t</h2>
        <p>Sulfuros (High Recovery)</p>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Row 2: Sensitivity Graph
st.subheader("📊 Análisis de Sensibilidad (Beneficio vs Ley)")

grades = np.linspace(0.1, 1.5, 50)
profits_leach = []
profits_mill = []

for g in grades:
    _, p_leach, _ = calculate_metrics(price_au, g, 'LEACH')
    _, p_mill, _ = calculate_metrics(price_au, g, 'MILL')
    profits_leach.append(p_leach)
    profits_mill.append(p_mill)

fig = go.Figure()
fig.add_trace(go.Scatter(x=grades, y=profits_leach, mode='lines', name='Leach (Óxidos)', line=dict(color='#EF4444', width=3)))
fig.add_trace(go.Scatter(x=grades, y=profits_mill, mode='lines', name='Mill (Sulfuros)', line=dict(color='#3B82F6', width=3)))
fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break-even")
fig.add_vline(x=cog_leach, line_dash="dot", line_color="#EF4444", annotation_text=f"COG Leach: {cog_leach:.2f}")
fig.add_vline(x=cog_mill, line_dash="dot", line_color="#3B82F6", annotation_text=f"COG Mill: {cog_mill:.2f}")

fig.update_layout(
    title=f"Rentabilidad por Tonelada @ ${price_au:,.0f}/oz",
    xaxis_title="Ley de Oro (g/t)",
    yaxis_title="Beneficio Neto ($/t)",
    template="plotly_white",
    height=500,
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# Row 3: Data Table & Calculator
c_table, c_calc = st.columns([1, 1])

with c_table:
    st.subheader("📋 Tabla Detallada")
    with st.expander("Ver Tabla", expanded=True):
        data = []
        for g in np.arange(0.1, 1.02, 0.02):
            nsr_l, prof_l, _ = calculate_metrics(price_au, g, 'LEACH')
            nsr_m, prof_m, _ = calculate_metrics(price_au, g, 'MILL')
            data.append({
                "Ley (g/t)": f"{g:.2f}",
                "NSR Leach": f"{nsr_l:.2f}",
                "Profit Leach": f"{prof_l:.2f}",
                "NSR Mill": f"{nsr_m:.2f}",
                "Profit Mill": f"{prof_m:.2f}"
            })
        st.dataframe(pd.DataFrame(data), height=600, use_container_width=True)

with c_calc:
    st.subheader("🧮 Calculadora Didáctica")
    with st.container(border=True):
        st.info("Desglose paso a paso de los cálculos:")
        calc_grade = st.number_input("Ley a probar (g/t)", value=0.50, step=0.01)
        calc_type = st.selectbox("Proceso", ["LEACH", "MILL"])
        
        c_nsr, c_prof, c_cost = calculate_metrics(price_au, calc_grade, calc_type)
        
        st.markdown("### 1. Precio Neto (Net Price)")
        
        # Marketing Fee
        mkt_val = price_au * marketing_pct
        st.write(f"• **Marketing Fee ({marketing_pct*100}%):** ${mkt_val:.2f}/oz")
        
        # Selling Cost Calculation
        if calc_type == 'LEACH':
            fixed_sc = fixed_sc_leach
            total_sc = fixed_sc + mkt_val
            st.write(f"• **Costo Venta (Fijo + Mkt):** ${fixed_sc:.2f} + ${mkt_val:.2f} = ${total_sc:.2f}/oz")
            net_p = price_au - total_sc
            st.markdown(f"👉 **Precio Neto:** ${price_au:.2f} - ${total_sc:.2f} = **${net_p:.2f}/oz**")
            rec_val = rec_leach
            
        else: # MILL
            fixed_sc = fixed_sc_mill
            total_sc = fixed_sc + mkt_val
            st.write(f"• **Costo Venta (Fijo + Mkt):** ${fixed_sc:.2f} + ${mkt_val:.2f} = ${total_sc:.2f}/oz")
            
            # Payable
            payable_price = price_au * payable_mill
            st.write(f"• **Payable ({payable_mill*100}%):** ${price_au:.2f} * {payable_mill} = ${payable_price:.2f}/oz")
            
            net_p = payable_price - total_sc
            st.markdown(f"👉 **Precio Neto:** ${payable_price:.2f} (Payable) - ${total_sc:.2f} (Costos) = **${net_p:.2f}/oz**")
            rec_val = rec_mill

        st.markdown("### 2. Retorno Neto (NSR)")
        st.latex(r"NSR = \frac{Ley \times Rec \times PrecioNeto}{31.1035}")
        st.write(f"• **Cálculo:** {calc_grade} * {rec_val} * {net_p:.2f} / 31.1035")
        st.markdown(f"👉 **NSR:** **${c_nsr:.2f}/t**")
        
        st.markdown("### 3. Beneficio Final")
        st.write(f"• **Ingresos (NSR):** ${c_nsr:.2f}/t")
        st.write(f"• **Costos Totales:** -${c_cost:.2f}/t")
        st.markdown(f"👉 **Beneficio:** **${c_prof:.2f}/t**")
        
        st.markdown("---")
        st.markdown("### 4. El Secreto del Cut-Off 🔍")
        st.info("Para calcular el Cut-Off, primero debemos saber: **¿Cuánto dinero real me deja 1 solo gramo de oro?**")
        
        # NSR_per_gram (Value of 1g/t)
        nsr_per_gram = rec_val * net_p / 31.1035
        
        st.markdown(f"""
        **A. Valor Real de 1 Gramo:**
        *   Imagina que tienes 1 gramo en la roca.
        *   Solo recuperas el **{rec_val*100:.0f}%**.
        *   Te pagan **${net_p:.2f}** por onza (no por gramo).
        """)
        
        st.latex(r"ValorGramo = \frac{Recuperación \times PrecioNeto}{31.1035}")
        st.write(f"• **Cálculo:** {rec_val} * {net_p:.2f} / 31.1035")
        st.markdown(f"👉 **Cada gramo vale:** **${nsr_per_gram:.2f}**")
        
        st.markdown("**B. Cálculo Final:**")
        st.write("Si costear la operación sale **$" + f"{c_cost:.2f}** por tonelada...")
        st.write("¿Cuántos de esos gramos de **$" + f"{nsr_per_gram:.2f}** necesito para pagar la cuenta?")
        
        cutoff_calc = c_cost / nsr_per_gram
        st.latex(r"CutOff = \frac{CostoTotal}{ValorGramo}")
        st.write(f"• **División:** {c_cost:.2f} / {nsr_per_gram:.2f}")
        st.markdown(f"👉 **Necesitas:** **{cutoff_calc:.3f} g/t** (Cut-Off)")

# Footer
st.markdown("---")
st.caption("Desarrollado con Tecnología Antigravity | Basado en modelo CHOQUE v01")
