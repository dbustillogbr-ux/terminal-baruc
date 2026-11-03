import streamlit as st
import requests
import pandas as pd

# Forzar la carga de yfinance como escudo de respaldo institucional
try:
    import yfinance as yf
except ImportError:
    st.error("Por favor agrega yfinance al archivo requirements.txt")

# 1. Configuración de la interfaz del Dashboard (Ajustado para Móvil/PWA)
st.set_page_config(page_title="Terminal Baruc", layout="wide", initial_sidebar_state="collapsed")
st.title("📊 Terminal Analítica Baruc")
st.caption("Fórmula algorítmica de correlaciones cruzadas M1/M5 para Fortrade.")

# =====================================================================
# INYECCIÓN DE SEGURIDAD NATIVA PARA PRODUCCIÓN (SECRETS)
# =====================================================================
# En la nube, la llave se lee desde las variables de entorno encriptadas.
# Localmente buscará en la carpeta .streamlit/secrets.toml
if "TWELVE_DATA_API_KEY" in st.secrets:
    TWELVE_DATA_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]
else:
    # Llave de respaldo local por si corres el script en tu máquina sin configurar secretos
    TWELVE_DATA_API_KEY = "f121cd0a43234c39bef05fae4f93a0cf"

# Tickers adaptados para el intento principal (Twelve Data)
TICKERS_TWELVE = {
    "S&P 500 (EU500)": "SPY",
    "Oro (XAU/USD)": "GLD",
    "Petróleo Crudo": "USO",
    "Yen (USD/JPY)": "USD/JPY"
}

# Tickers de respaldo absoluto (Yahoo Finance - Calibrados con Fortrade)
TICKERS_YFINANCE = {
    "S&P 500 (EU500)": "ES=F",     # Futuro E-mini S&P 500
    "Oro (XAU/USD)": "GC=F",       # Futuro del Oro
    "Petróleo Crudo": "CL=F",      # Futuro WTI
    "Yen (USD/JPY)": "JPY=X"       # Divisa Spot del Yen
}

# 3. Módulo de Controles e Informes en la Barra Lateral
st.sidebar.header("⚙️ Configuración")

soporte_clasico = st.sidebar.number_input(
    "Soporte Crítico EU500", 
    min_value=400.0, 
    max_value=8500.0, 
    value=7590.0,  
    step=5.0
)

FACTOR_CONVERSION = 13.4  

st.sidebar.markdown("---")
pce_status = st.sidebar.selectbox("PCE Inflation", ["Positivo", "Negativo", "Neutral"], index=0)
pmi_status = st.sidebar.selectbox("Chicago PMI", ["Positivo", "Negativo", "Neutral"], index=1)
michigan_status = st.sidebar.selectbox("Michigan Consumer", ["Positivo", "Negativo", "Neutral"], index=1)

# Extracción Híbrida con Ventana Extendida M5
def obtener_datos_flujo():
    datos = {}
    usando_respaldo = False
    
    for nombre in TICKERS_TWELVE.keys():
        ticker_td = TICKERS_TWELVE[nombre]
        ticker_yf = TICKERS_YFINANCE[nombre]
        
        # INTENTO 1: Twelve Data
        try:
            url = f"https://twelvedata.com{ticker_td}&interval=1min&outputsize=10&apikey={TWELVE_DATA_API_KEY}"
            res = requests.get(url)
            response = res.json()
            
            if "values" in response and len(response["values"]) >= 5:
                df_api = pd.DataFrame(response["values"])
                df_api["close"] = pd.to_numeric(df_api["close"])
                df_api = df_api.iloc[::-1].reset_index(drop=True)
                
                ultimo_precio = df_api['close'].iloc[-1]
                precio_anterior = df_api['close'].iloc[-5]
                cambio_micro = ultimo_precio - precio_anterior
                
                df_visual = df_api[['close']].rename(columns={'close': 'Close'})
                datos[nombre] = {"precio": ultimo_precio, "cambio": cambio_micro, "df": df_visual, "api": "TwelveData"}
                continue
        except Exception:
            pass
            
        # INTENTO 2: Escudo de Emergencia (Yahoo Finance)
        try:
            usando_respaldo = True
            activo = yf.Ticker(ticker_yf)
            df = activo.history(period="1d", interval="1m")
            if df.empty or len(df) < 5:
                df = activo.history(period="5d", interval="5m")
                
            if not df.empty:
                ultimo_precio = df['Close'].iloc[-1]
                indice_atras = -5 if len(df) >= 5 else -2
                precio_anterior = df['Close'].iloc[indice_atras]
                cambio_micro = ultimo_precio - precio_anterior
                datos[nombre] = {"precio": ultimo_precio, "cambio": cambio_micro, "df": df, "api": "yfinance"}
            else:
                datos[nombre] = {"precio": 0.0, "cambio": 0.0, "df": pd.DataFrame(), "api": "Falla"}
        except Exception:
            datos[nombre] = {"precio": 0.0, "cambio": 0.0, "df": pd.DataFrame(), "api": "Falla"}
            
    if usando_respaldo:
        st.sidebar.info("🛡️ Escudo Activo: Yahoo Finance")
    else:
        st.sidebar.success("⚡ Conexión Directa: Twelve Data")
        
    return datos

with st.spinner("Sincronizando flujos..."):
    mercado = obtener_datos_flujo()

# 4. Procesamiento Cuantitativo con Factor Geopolítico
def calcular_score(cambio, inverso=False):
    if cambio > 0.0001:
        return 1 if not inverso else -1
    elif cambio < -0.0001:
        return -1 if not inverso else 1
    return 0

score_petroleo_base = calcular_score(mercado["Petróleo Crudo"]["cambio"], inverso=False)
score_oro = calcular_score(mercado["Oro (XAU/USD)"]["cambio"], inverso=True)  
score_yen = calcular_score(mercado["Yen (USD/JPY)"]["cambio"], inverso=True)  

cambio_crudo_puro = mercado["Petróleo Crudo"]["cambio"]
UMBRAL_SENSIBLE = 0.08  

if cambio_crudo_puro > UMBRAL_SENSIBLE:
    score_petroleo = 3   
    geopolitica_status = "🚨 CHOQUE GEOPOLÍTICO DETECTADO en Crudo"
elif cambio_crudo_puro < -UMBRAL_SENSIBLE:
    score_petroleo = -3
    geopolitica_status = "📉 ALIVIO ENERGÉTICO EN CURSO"
else:
    score_petroleo = score_petroleo_base
    geopolitica_status = "🦅 Flujo geopolítico en calma"

score_tecnico = score_petroleo + score_oro + score_yen

score_noticias = 0
for status in [pce_status, pmi_status, michigan_status]:
    if status == "Positivo":
        score_noticias += 1
    elif status == "Negativo":
        score_noticias -= 1

ip_eu500 = score_tecnico + score_noticias

if ip_eu500 >= 2:
    diagnostico = "🚀 REBOTE ALCISTA INMINENTE"
elif ip_eu500 <= -2:
    diagnostico = "⚠️ CONTINUACIÓN BAJISTA"
else:
    diagnostico = "🔄 DISTRIBUCIÓN LATERAL"

# 5. Renderizado Adaptativo para Pantallas Móviles
col1, col2 = st.columns(2)
es_td = mercado['S&P 500 (EU500)']['api'] == "TwelveData"
precio_eu500_visual = mercado['S&P 500 (EU500)']['precio'] * (FACTOR_CONVERSION if es_td else 1.0)
cambio_eu500_visual = mercado['S&P 500 (EU500)']['cambio'] * (FACTOR_CONVERSION if es_td else 1.0)

if 0 < precio_eu500_visual < 1000:
    precio_eu500_visual = precio_eu500_visual * FACTOR_CONVERSION

col1.metric("EE.UU. 500", f"{precio_eu500_visual:.2f}", f"{cambio_eu500_visual:.2f}")
col2.metric("Oro Spot", f"${mercado['Oro (XAU/USD)']['precio']:.1f}", f"{mercado['Oro (XAU/USD)']['cambio']:.2f}")

col3, col4 = st.columns(2)
col3.metric("Crudo WTI", f"${mercado['Petróleo Crudo']['precio']:.2f}", f"{mercado['Petróleo Crudo']['cambio']:.2f}")
col4.metric("Yen (USD/JPY)", f"{mercado['Yen (USD/JPY)']['precio']:.3f}", f"{mercado['Yen (USD/JPY)']['cambio']:.3f}")

st.markdown("---")

st.markdown(f"### Índice de Presión: **{ip_eu500}**")
st.info(f"**Resultado:** {diagnostico}")

if "🚨" in geopolitica_status:
    st.error(geopolitica_status)
elif "📉" in geopolitica_status:
    st.warning(geopolitica_status)
else:
    st.caption(geopolitica_status)

precio_cotejo = precio_eu500_visual if precio_eu500_visual > 0 else mercado['S&P 500 (EU500)']['precio']

if 0 < precio_cotejo < soporte_clasico:
    st.error(f"🚨 SOPORTE PERFORADO ({soporte_clasico:.2f})")
elif precio_cotejo >= soporte_clasico:
    st.success(f"✅ Por encima de soporte ({soporte_clasico:.2f})")

if st.button("🔄 Actualizar Flujos", use_container_width=True):
    st.rerun()
