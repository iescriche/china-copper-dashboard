import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time
import locale
from datetime import datetime, timedelta
from scipy.stats import linregress

# Configurar formato europeo
import locale
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')


# Configuración de página
st.set_page_config(layout="wide")
st.title("Dashboard: Análisis de Pedido desde China (100.000 EUR)")

# Tabs
tab1, tab2, tab3 = st.tabs(["Dashboard", "Análisis de Compra Pasada", "Explicación"])

# Pestaña de Explicación (estática)
with tab3:
    st.header("Explicación del Dashboard")
    st.write("""
    Este dashboard te ayuda a calcular cuánto cobre puedes comprar con un presupuesto en euros (por defecto 100.000 EUR) para un pedido desde China y a decidir el mejor momento para comprar, considerando una demora de 4 meses. A continuación, se explica cada sección:
    ### 1. Configuración del Pedido (Sidebar)
    - **Presupuesto en Euros**: Cantidad disponible (ej. 100.000 EUR).
    - **Porcentaje del Coste por Cobre**: Porcentaje para cobre (por defecto 50%).
    - **Factor Coste Transporte**: Porcentaje del precio del petróleo que representa los costes de transporte (por defecto 1%).
    - **Tasa de Refresco**: Frecuencia de actualización de datos en tiempo real (segundos).
    ### 2. Evolución Últimos 9 Meses
    - **Gráficos históricos**:
      - **Cobre y EUR/CNY**: Precio del cobre (USD/lb) y tipo de cambio EUR/CNY con líneas de promedio, máximo y mínimo.
      - **Petróleo**: Precio del petróleo (USD/barril) con líneas de promedio, máximo y mínimo.
      - **Cantidad de Cobre Comprable**: Toneladas de cobre comprables con el presupuesto actual.
    - **Propósito**: Comparar precios actuales con históricos para evaluar tendencias.
    ### 3. Datos en Tiempo Real
    - **KPIs**:
      - **Cobre ($/lb)**: Precio actual del cobre.
      - **Petróleo ($/barril)**: Precio del petróleo (WTI), para transporte.
      - **EUR/CNY**: Cuántos yuanes por euro (alto = euro fuerte).
      - **USD/CNY**: Dólares por yuan, para conversión de precios.
    - **Gráficos en tiempo real**: Evolución reciente de precios con líneas suavizadas.
    - **Propósito**: Monitoreo para decisiones inmediatas.
    ### 4. Cálculo del Pedido
    - **Presupuesto en CNY**: Conversión de euros a yuanes.
    - **Coste del cobre**: 50% del presupuesto para cobre (toneladas/libra).
    - **Costes de transporte**: Porcentaje del precio del petróleo (ajustable).
    - **Otros costes**: Resto del presupuesto.
    - **Coste total**: Suma de todos los costes en CNY.
    - **Sobrante/Déficit**: Indica si el presupuesto es suficiente.
    - **Propósito**: Ver cuánto cobre puedes comprar y si alcanza el presupuesto.
    ### 5. Mejor Momento para Comprar
    - **Tendencias (30 días)**: Indica si los precios suben (alcista) o bajan (bajista) con pendiente de regresión lineal.
    - **Indicadores Técnicos**:
      - **RSI (14, 30, 50 días)**: Evalúa si el cobre está en sobrecompra (>70) o sobreventa (<30).
      - **Correlaciones**: Entre cobre, petróleo y EUR/CNY.
      - **Volatilidad**: Mide la estabilidad de los precios del cobre.
      - **Bandas de Bollinger**: Identifica si el cobre está en sobrecompra o sobreventa.
      - **MACD**: Detecta cambios de tendencia en el precio del cobre.
    - **Recomendaciones**: Basadas en cantidad comprable, tendencias, RSI, volatilidad y EUR/CNY.
    - **Proyección a 4 meses**: Cantidad de cobre proyectada (escenario esperado, mínimo, máximo) basada en EMA y tendencia lineal.
    - **Propósito**: Decidir si comprar ahora o esperar.
    ### 6. Análisis Avanzado
    - **Análisis de Sensibilidad**: Evalúa el impacto de cambios del ±5% en precios y divisas.
    - **Simulación Monte Carlo**: Estima la distribución de toneladas de cobre comprables a 4 meses con 1000 escenarios.
    - **Gráficos Mejorados**:
      - Histograma Monte Carlo para distribución de resultados.
      - Gráfico de área para proyecciones con intervalos de confianza.
    ### 7. Análisis de Compra Pasada (Tab Separada)
    - **Input**: Fecha de compra, fecha de venta ficticia.
    - **Comparación**: Precios del cobre (USD/lb, CNY/lb) y tasas de cambio (EUR/CNY, USD/CNY).
    - **Propósito**: Evaluar cambios en precios y tasas entre fechas.
    ### Suposiciones
    - Cobre: 50% del presupuesto, en USD/lb, convertido a CNY.
    - Transporte: Porcentaje del precio del petróleo (ajustable).
    - Otros costes: Resto del presupuesto.
    - Datos: De yfinance. Pueden faltar en días no hábiles.
    - Proyección: Basada en promedios y tendencias, especulativa.
    ### Cómo Usar
    - Ajusta el presupuesto, porcentaje de cobre y factor de transporte.
    - Revisa gráficos históricos, en tiempo real y proyecciones.
    - Usa las recomendaciones y análisis técnico para decidir si comprar ahora o esperar.
    - En el tab "Análisis de Compra Pasada", compara precios y tasas de cambio.
    """)

with tab1:
    # Sidebar para inputs
    st.sidebar.header("Configuración del Pedido")
    budget_eur = st.sidebar.number_input("Presupuesto en Euros", min_value=1000.0, value=100000.0, step=1000.0)
    copper_percentage = st.sidebar.slider("Porcentaje del Coste por Cobre (%)", 0.0, 100.0, 50.0)
    transport_cost_factor = st.sidebar.slider("Factor Coste Transporte (% del precio del petróleo)", 0.1, 10.0, 1.0, help="Porcentaje del precio del petróleo que representa los costes de transporte")
    refresh_rate = st.sidebar.slider("Tasa de Refresco (segundos)", 10, 300, 180)  # Default to 180 seconds (3 minutes)

    # Estado de sesión
    if "data" not in st.session_state:
        st.session_state.data = {
            "copper": [], "oil": [], "eur_cny": [], "usd_cny": [], "copper_quantity_ton": [], "timestamps": []
        }

    @st.cache_data(ttl=3600)
    def fetch_historical_data():
        end_date = datetime.now()
        start_date = end_date - timedelta(days=270)  # 9 meses
        max_retries = 3
        for attempt in range(max_retries):
            try:
                copper = yf.download("HG=F", start=start_date, end=end_date, interval="1d", auto_adjust=False)
                oil = yf.download("CL=F", start=start_date, end=end_date, interval="1d", auto_adjust=False)
                eur_cny = yf.download("EURCNY=X", start=start_date, end=end_date, interval="1d", auto_adjust=False)
                usd_cny = yf.download("USDCNY=X", start=start_date, end=end_date, interval="1d", auto_adjust=False)
                if any(df.empty for df in [copper, oil, eur_cny, usd_cny]):
                    st.warning(f"Intento {attempt + 1}: Uno o más conjuntos de datos históricos están vacíos.")
                    time.sleep(2)
                    continue
                if any(len(df) < 30 for df in [copper, oil, eur_cny, usd_cny]):
                    st.warning(f"Intento {attempt + 1}: Datos insuficientes (menos de 30 filas).")
                    time.sleep(2)
                    continue
                return copper, oil, eur_cny, usd_cny
            except Exception as e:
                st.error(f"Error al obtener datos históricos (intento {attempt + 1}): {e}")
                time.sleep(2)
        st.error("No se pudieron obtener datos históricos después de varios intentos.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def fetch_realtime_data():
        try:
            copper = yf.Ticker("HG=F").history(period="1d", interval="1m")
            copper_price = float(copper["Close"].iloc[-1]) if not copper.empty else np.nan
            oil = yf.Ticker("CL=F").history(period="1d", interval="1m")
            oil_price = float(oil["Close"].iloc[-1]) if not oil.empty else np.nan
            eur_cny = yf.Ticker("EURCNY=X").history(period="1d", interval="1m")
            eur_cny_price = float(eur_cny["Close"].iloc[-1]) if not eur_cny.empty else np.nan
            usd_cny = yf.Ticker("USDCNY=X").history(period="1d", interval="1m")
            usd_cny_price = float(usd_cny["Close"].iloc[-1]) if not usd_cny.empty else np.nan
            timestamp = datetime.now()
            return copper_price, oil_price, eur_cny_price, usd_cny_price, timestamp
        except Exception as e:
            st.error(f"Error al obtener datos en tiempo real: {e}")
            return np.nan, np.nan, np.nan, np.nan, datetime.now()

    def append_realtime_data(copper_price, oil_price, eur_cny_price, usd_cny_price, copper_quantity_ton, timestamp):
        st.session_state.data["copper"].append(copper_price)
        st.session_state.data["oil"].append(oil_price)
        st.session_state.data["eur_cny"].append(eur_cny_price)
        st.session_state.data["usd_cny"].append(usd_cny_price)
        st.session_state.data["copper_quantity_ton"].append(copper_quantity_ton)
        st.session_state.data["timestamps"].append(timestamp)
        for key in st.session_state.data:
            st.session_state.data[key] = st.session_state.data[key][-100:]

    def calculate_order(budget_eur, copper_pct, transport_factor, copper_price, oil_price, eur_cny_price, usd_cny_price):
        if any(np.isnan(x) for x in [copper_price, oil_price, eur_cny_price, usd_cny_price]):
            return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
        budget_cny = budget_eur * eur_cny_price
        copper_budget_cny = budget_cny * (copper_pct / 100)
        other_budget_cny = budget_cny * (1 - copper_pct / 100)
        copper_price_cny = copper_price * usd_cny_price
        oil_price_cny = oil_price * usd_cny_price
        copper_quantity_lb = copper_budget_cny / copper_price_cny if copper_price_cny != 0 else np.nan
        copper_quantity_ton = copper_quantity_lb * 0.000453592 if not np.isnan(copper_quantity_lb) else np.nan
        transport_cost_cny = oil_price_cny * transport_factor / 100 if not np.isnan(oil_price_cny) else 0
        other_cost_cny = other_budget_cny - transport_cost_cny if other_budget_cny >= transport_cost_cny else 0
        total_order_cost_cny = copper_budget_cny + transport_cost_cny + other_cost_cny
        budget_status = budget_cny - total_order_cost_cny
        return budget_cny, copper_budget_cny, other_budget_cny, copper_quantity_lb, copper_quantity_ton, transport_cost_cny, other_cost_cny, total_order_cost_cny, budget_status

    def calculate_historical_orders(historical_df, budget_eur, copper_pct, transport_factor):
        historical_df["Budget CNY"] = budget_eur * historical_df["EUR/CNY"]
        historical_df["Copper Budget CNY"] = historical_df["Budget CNY"] * (copper_pct / 100)
        historical_df["Other Budget CNY"] = historical_df["Budget CNY"] * (1 - copper_pct / 100)
        historical_df["Copper Price CNY"] = historical_df["Copper"] * historical_df["USD/CNY"]
        historical_df["Transport Cost CNY"] = (historical_df["Oil"] * historical_df["USD/CNY"]) * (transport_factor / 100)
        historical_df["Other Cost CNY"] = historical_df["Other Budget CNY"] - historical_df["Transport Cost CNY"]
        historical_df["Other Cost CNY"] = historical_df["Other Cost CNY"].clip(lower=0)
        historical_df["Copper Quantity lb"] = historical_df["Copper Budget CNY"] / historical_df["Copper Price CNY"]
        historical_df["Copper Quantity ton"] = historical_df["Copper Quantity lb"] * 0.000453592
        historical_df["Total Order Cost CNY"] = historical_df["Copper Budget CNY"] + historical_df["Transport Cost CNY"] + historical_df["Other Cost CNY"]
        historical_df["Budget Status CNY"] = historical_df["Budget CNY"] - historical_df["Total Order Cost CNY"]
        return historical_df

    def project_future_price(historical_data, span=30):
        if historical_data.empty:
            st.warning("Datos históricos vacíos para proyección.")
            return np.nan, np.nan, np.nan
        try:
            close_data = historical_data["Close"].dropna()
            if len(close_data) < 2:
                st.warning(f"Datos insuficientes para proyección: solo {len(close_data)} filas disponibles.")
                return np.nan, np.nan, np.nan
            tail_len = min(span, len(close_data))
            ema_series = close_data.ewm(span=tail_len, adjust=False).mean().dropna()
            if ema_series.empty:
                return np.nan, np.nan, np.nan
            ema_value = float(ema_series.iloc[-1])
            std_value = float(close_data.tail(tail_len).std())
            if np.isnan(ema_value):
                st.warning(f"Valor NaN detectado en EMA para período de {span} días.")
                return np.nan, np.nan, np.nan
            return ema_value, ema_value - std_value, ema_value + std_value
        except Exception as e:
            st.error(f"Error en project_future_price: {e}")
            return np.nan, np.nan, np.nan

    def calculate_rsi(historical_data, period=14):
        if historical_data.empty or len(historical_data) < period + 1:
            return np.nan
        close = historical_data["Close"]
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def calculate_trend(historical_data, period=30):
        if historical_data.empty or len(historical_data) < period:
            return np.nan, "Indeterminada"
        last_period = historical_data["Close"].tail(period).values.flatten()
        x = np.arange(len(last_period))
        slope, _, _, _, _ = linregress(x, last_period)
        return slope, "Alcista" if slope > 0 else "Bajista"

    def create_historical_plot_copper_eurcny(historical_df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=historical_df.index, y=historical_df["Copper"], mode="lines", name="Cobre ($/lb)"))
        fig.add_trace(go.Scatter(x=historical_df.index, y=historical_df["EUR/CNY"], mode="lines", name="EUR/CNY"))
        fig.add_hline(y=historical_df["Copper"].mean(), line_dash="dash", line_color="gray", annotation_text="Promedio Cobre")
        fig.add_hline(y=historical_df["EUR/CNY"].mean(), line_dash="dash", line_color="gray", annotation_text="Promedio EUR/CNY", annotation_position="top left")
        fig.add_hline(y=historical_df["Copper"].max(), line_dash="dot", line_color="red", annotation_text="Máximo Cobre")
        fig.add_hline(y=historical_df["Copper"].min(), line_dash="dot", line_color="green", annotation_text="Mínimo Cobre")
        fig.update_layout(
            title="Evolución Cobre y EUR/CNY (9 Meses)",
            xaxis_title="Fecha",
            yaxis_title="Precio/Valor",
            hovermode="x unified",
            showlegend=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        return fig

    def create_historical_plot_oil(historical_df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=historical_df.index, y=historical_df["Oil"], mode="lines", name="Petróleo ($/barril)"))
        fig.add_hline(y=historical_df["Oil"].mean(), line_dash="dash", line_color="gray", annotation_text="Promedio Petróleo")
        fig.add_hline(y=historical_df["Oil"].max(), line_dash="dot", line_color="red", annotation_text="Máximo Petróleo")
        fig.add_hline(y=historical_df["Oil"].min(), line_dash="dot", line_color="green", annotation_text="Mínimo Petróleo")
        fig.update_layout(
            title="Evolución Petróleo (9 Meses)",
            xaxis_title="Fecha",
            yaxis_title="Precio ($/barril)",
            hovermode="x unified",
            showlegend=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        return fig

    def create_historical_plot_copper_quantity(historical_df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=historical_df.index, y=historical_df["Copper Quantity ton"], mode="lines", name="Cantidad Cobre (toneladas)"))
        fig.add_hline(y=historical_df["Copper Quantity ton"].mean(), line_dash="dash", line_color="gray", annotation_text="Promedio Cantidad")
        fig.add_hline(y=historical_df["Copper Quantity ton"].max(), line_dash="dot", line_color="red", annotation_text="Máximo Cantidad")
        fig.add_hline(y=historical_df["Copper Quantity ton"].min(), line_dash="dot", line_color="green", annotation_text="Mínimo Cantidad")
        fig.update_layout(
            title="Cantidad de Cobre Comprable (9 Meses)",
            xaxis_title="Fecha",
            yaxis_title="Toneladas",
            hovermode="x unified",
            showlegend=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        return fig

    def create_realtime_plot(realtime_df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=realtime_df["timestamps"], y=realtime_df["copper"], mode="lines+markers", name="Cobre ($/lb)", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=realtime_df["timestamps"], y=realtime_df["eur_cny"], mode="lines+markers", name="EUR/CNY", line=dict(width=2)))
        fig.update_layout(
            title="Tiempo Real Cobre y EUR/CNY",
            xaxis_title="Tiempo",
            yaxis_title="Precio/Valor",
            hovermode="x unified",
            showlegend=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        return fig

    def create_realtime_plot_oil(realtime_df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=realtime_df["timestamps"], y=realtime_df["oil"], mode="lines+markers", name="Petróleo ($/barril)", line=dict(width=2)))
        fig.update_layout(
            title="Tiempo Real Petróleo",
            xaxis_title="Tiempo",
            yaxis_title="Precio ($/barril)",
            hovermode="x unified",
            showlegend=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        return fig

    # Datos históricos
    copper_hist, oil_hist, eur_cny_hist, usd_cny_hist = fetch_historical_data()
    if not copper_hist.empty and not oil_hist.empty and not eur_cny_hist.empty and not usd_cny_hist.empty:
        common_index = copper_hist.index.intersection(oil_hist.index).intersection(eur_cny_hist.index).intersection(usd_cny_hist.index)
        historical_df = pd.DataFrame({
            "Date": common_index,
            "Copper": copper_hist.loc[common_index, "Close"].values.flatten(),
            "Oil": oil_hist.loc[common_index, "Close"].values.flatten(),
            "EUR/CNY": eur_cny_hist.loc[common_index, "Close"].values.flatten(),
            "USD/CNY": usd_cny_hist.loc[common_index, "Close"].values.flatten()
        }).dropna()
        historical_df.set_index("Date", inplace=True)
        historical_df = calculate_historical_orders(historical_df, budget_eur, copper_percentage, transport_cost_factor)
    else:
        historical_df = pd.DataFrame()
        st.warning("No se pudieron obtener datos históricos.")

    # Gráficos históricos
    st.subheader("Evolución Últimos 9 Meses")
    if not historical_df.empty:
        col_hist1, col_hist2 = st.columns(2)
        with col_hist1:
            fig_hist_copper = create_historical_plot_copper_eurcny(historical_df)
            st.plotly_chart(fig_hist_copper, use_container_width=True)
        with col_hist2:
            fig_hist_oil = create_historical_plot_oil(historical_df)
            st.plotly_chart(fig_hist_oil, use_container_width=True)
        st.subheader("Cantidad de Cobre Comprable")
        fig_copper_quantity = create_historical_plot_copper_quantity(historical_df)
        st.plotly_chart(fig_copper_quantity, use_container_width=True)
    else:
        st.info("Sin datos históricos.")

    # Checkbox para actualización automática
    auto_update = st.checkbox("Activar actualización automática cada 3 minutos", value=False, key="auto_update")

    # Placeholder for dynamic content
    placeholder = st.empty()

    def update_dashboard():
        with placeholder.container():
            copper_price, oil_price, eur_cny_price, usd_cny_price, timestamp = fetch_realtime_data()
            budget_cny, copper_budget_cny, other_budget_cny, copper_quantity_lb, copper_quantity_ton, transport_cost_cny, other_cost_cny, total_order_cost_cny, budget_status = calculate_order(
                budget_eur, copper_percentage, transport_cost_factor, copper_price, oil_price, eur_cny_price, usd_cny_price
            )
            append_realtime_data(copper_price, oil_price, eur_cny_price, usd_cny_price, copper_quantity_ton, timestamp)
            realtime_df = pd.DataFrame(st.session_state.data)
            # KPIs
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Cobre ($/lb)", locale.format_string('%.2f', copper_price, grouping=True) if not np.isnan(copper_price) else "N/A")
            with col2:
                st.metric("Petróleo ($/barril)", locale.format_string('%.2f', oil_price, grouping=True) if not np.isnan(oil_price) else "N/A")
            with col3:
                st.metric("EUR/CNY", locale.format_string('%.4f', eur_cny_price, grouping=True) if not np.isnan(eur_cny_price) else "N/A")
            with col4:
                st.metric("USD/CNY", locale.format_string('%.4f', usd_cny_price, grouping=True) if not np.isnan(usd_cny_price) else "N/A")
            # Gráficos en tiempo real
            st.subheader("Datos en Tiempo Real")
            col_rt1, col_rt2 = st.columns(2)
            with col_rt1:
                if not realtime_df.empty:
                    fig_rt = create_realtime_plot(realtime_df)
                    st.plotly_chart(fig_rt, use_container_width=True)
            with col_rt2:
                if not realtime_df.empty:
                    fig_rt_oil = create_realtime_plot_oil(realtime_df)
                    st.plotly_chart(fig_rt_oil, use_container_width=True)
            # Cálculo del pedido
            st.subheader(f"Cálculo del Pedido con Presupuesto de {locale.format_string('%.2f', budget_eur, grouping=True)} EUR")
            if not np.isnan(budget_cny):
                st.write(f"Presupuesto en CNY: {locale.format_string('%.2f', budget_cny, grouping=True)} CNY")
                st.write(f"- Coste del cobre ({copper_percentage}%): {locale.format_string('%.2f', copper_budget_cny, grouping=True)} CNY")
                st.write(f" - Cantidad de cobre: {locale.format_string('%.2f', copper_quantity_ton, grouping=True)} toneladas (~{locale.format_string('%.2f', copper_quantity_lb, grouping=True)} lb)")
                st.write(f"- Costes de transporte ({transport_cost_factor}% del precio del petróleo): {locale.format_string('%.2f', transport_cost_cny, grouping=True)} CNY")
                st.write(f"- Otros costes: {locale.format_string('%.2f', other_cost_cny, grouping=True)} CNY")
                st.write(f"**Coste total del pedido**: {locale.format_string('%.2f', total_order_cost_cny, grouping=True)} CNY")
                if budget_status >= 0:
                    st.write(f"**Sobrante**: {locale.format_string('%.2f', budget_status, grouping=True)} CNY")
                else:
                    st.warning(f"**Déficit**: {locale.format_string('%.2f', -budget_status, grouping=True)} CNY")
            else:
                st.warning("No se pudo calcular el pedido debido a datos faltantes.")
            # Análisis para comprar
            st.subheader("Mejor Momento para Comprar")
            if not historical_df.empty:
                copper_slope_30, copper_trend_30 = calculate_trend(copper_hist, 30)
                oil_slope_30, oil_trend_30 = calculate_trend(oil_hist, 30)
                eur_cny_slope_30, eur_cny_trend_30 = calculate_trend(eur_cny_hist, 30)
                usd_cny_slope_30, usd_cny_trend_30 = calculate_trend(usd_cny_hist, 30)
                st.write("**Tendencias (30 días):**")
                trends_df = pd.DataFrame({
                    "Indicador": ["Tendencia Cobre", "Tendencia Petróleo", "Tendencia EUR/CNY", "Tendencia USD/CNY"],
                    "Período": ["30 días", "30 días", "30 días", "30 días"],
                    "Tendencia": [copper_trend_30, oil_trend_30, eur_cny_trend_30, usd_cny_trend_30],
                    "Pendiente": [locale.format_string('%.4f', copper_slope_30, grouping=True),
                                  locale.format_string('%.4f', oil_slope_30, grouping=True),
                                  locale.format_string('%.4f', eur_cny_slope_30, grouping=True),
                                  locale.format_string('%.4f', usd_cny_slope_30, grouping=True)]
                })
                st.table(trends_df)
                # Indicadores técnicos adicionales
                rsi_copper = calculate_rsi(copper_hist)
                rsi_copper_30 = calculate_rsi(copper_hist, period=30)
                rsi_copper_50 = calculate_rsi(copper_hist, period=50)
                rsi_oil = calculate_rsi(oil_hist)
                corr_copper_oil = historical_df['Copper'].corr(historical_df['Oil']) if not historical_df.empty else np.nan
                corr_copper_eurcny = historical_df['Copper'].corr(historical_df['EUR/CNY']) if not historical_df.empty else np.nan
                st.write("**Indicadores Técnicos Adicionales:**")
                tech_df = pd.DataFrame({
                    "Indicador": [
                        "RSI Cobre (14 días)",
                        "RSI Cobre (30 días)",
                        "RSI Cobre (50 días)",
                        "RSI Petróleo (14 días)",
                        "Correlación Cobre-Petróleo",
                        "Correlación Cobre-EUR/CNY"
                    ],
                    "Valor": [
                        locale.format_string('%.2f', rsi_copper, grouping=True) if not pd.isna(rsi_copper) else "N/A",
                        locale.format_string('%.2f', rsi_copper_30, grouping=True) if not pd.isna(rsi_copper_30) else "N/A",
                        locale.format_string('%.2f', rsi_copper_50, grouping=True) if not pd.isna(rsi_copper_50) else "N/A",
                        locale.format_string('%.2f', rsi_oil, grouping=True) if not pd.isna(rsi_oil) else "N/A",
                        locale.format_string('%.4f', corr_copper_oil, grouping=True) if not pd.isna(corr_copper_oil) else "N/A",
                        locale.format_string('%.4f', corr_copper_eurcny, grouping=True) if not pd.isna(corr_copper_eurcny) else "N/A"
                    ]
                })
                st.table(tech_df)
                # Recomendaciones
                st.write("**Recomendaciones Analíticas:**")
                recommendations = []
                max_copper_quantity_ton = historical_df["Copper Quantity ton"].max()
                min_copper_quantity_ton = historical_df["Copper Quantity ton"].min()
                avg_copper_quantity_ton = historical_df["Copper Quantity ton"].mean()
                std_copper_quantity = historical_df["Copper Quantity ton"].std()
                z_score = (copper_quantity_ton - avg_copper_quantity_ton) / std_copper_quantity if std_copper_quantity != 0 else 0
                savings_vs_avg_ton = copper_quantity_ton - avg_copper_quantity_ton
                pct_vs_avg = (savings_vs_avg_ton / avg_copper_quantity_ton * 100) if avg_copper_quantity_ton != 0 else 0
                savings_vs_min_ton = copper_quantity_ton - min_copper_quantity_ton
                pct_vs_min = (savings_vs_min_ton / min_copper_quantity_ton * 100) if min_copper_quantity_ton != 0 else 0
                savings_vs_max_ton = copper_quantity_ton - max_copper_quantity_ton
                pct_vs_max = (savings_vs_max_ton / max_copper_quantity_ton * 100) if max_copper_quantity_ton != 0 else 0
                if savings_vs_avg_ton > 0:
                    recommendations.append(f"La cantidad actual de cobre comprable supera el promedio histórico en {locale.format_string('%.2f', savings_vs_avg_ton, grouping=True)} toneladas, lo que representa un incremento del {locale.format_string('%.2f', pct_vs_avg, grouping=True)}%. Con un Z-score de {locale.format_string('%.2f', z_score, grouping=True)}, esto indica una desviación positiva significativa, sugiriendo una ventana óptima para adquisición.")
                else:
                    recommendations.append(f"La cantidad actual de cobre comprable es inferior al promedio histórico en {locale.format_string('%.2f', -savings_vs_avg_ton, grouping=True)} toneladas, equivalente a una reducción del {locale.format_string('%.2f', -pct_vs_avg, grouping=True)}%. El Z-score de {locale.format_string('%.2f', z_score, grouping=True)} resalta una desviación negativa, recomendando evaluación de factores macroeconómicos.")
                if savings_vs_min_ton > 0:
                    recommendations.append(f"Comparado con el mínimo histórico, la cantidad actual muestra una mejora de {locale.format_string('%.2f', savings_vs_min_ton, grouping=True)} toneladas ({locale.format_string('%.2f', pct_vs_min, grouping=True)}%), ofreciendo un buffer robusto contra volatilidades.")
                if savings_vs_max_ton < 0:
                    recommendations.append(f"La cantidad actual está {locale.format_string('%.2f', -savings_vs_max_ton, grouping=True)} toneladas por debajo del máximo histórico ({locale.format_string('%.2f', pct_vs_max, grouping=True)}%), lo que sugiere espacio para optimización si las tendencias alcistas persisten.")
                if copper_trend_30 == "Bajista":
                    recommendations.append(f"La tendencia bajista del cobre en los últimos 30 días, con una pendiente de {locale.format_string('%.4f', copper_slope_30, grouping=True)}, sugiere postergar la compra 2-4 semanas para maximizar la cantidad comprable.")
                else:
                    recommendations.append(f"La tendencia alcista del cobre, con pendiente de {locale.format_string('%.4f', copper_slope_30, grouping=True)}, aconseja una adquisición inmediata para mitigar riesgos de escalada de precios.")
                if oil_trend_30 == "Bajista":
                    recommendations.append(f"La declinación en el precio del petróleo (pendiente: {locale.format_string('%.4f', oil_slope_30, grouping=True)}) podría reducir los costes de transporte del 2-5%, beneficiando operaciones logísticas.")
                else:
                    recommendations.append(f"El ascenso en el precio del petróleo (pendiente: {locale.format_string('%.4f', oil_slope_30, grouping=True)}) urge a actuar para eludir incrementos en costes de flete.")
                if eur_cny_price < 8.5:
                    recommendations.append(f"El tipo de cambio EUR/CNY por debajo de 8.5 erosiona el poder adquisitivo; monitorear políticas monetarias del BCE es clave.")
                else:
                    recommendations.append(f"El tipo de cambio EUR/CNY ≥ 8.5 robustece el euro, maximizando la conversión a yuanes y negociaciones con contrapartes chinas.")
                copper_vol = historical_df["Copper"].tail(30).std() / historical_df["Copper"].tail(30).mean() * 100 if not historical_df.empty else 0
                if copper_vol > 5:
                    recommendations.append(f"La volatilidad del cobre en {locale.format_string('%.2f', copper_vol, grouping=True)}% indica un mercado inestable. Se recomienda cobertura o compras fraccionadas.")
                else:
                    recommendations.append(f"Con una volatilidad del cobre en {locale.format_string('%.2f', copper_vol, grouping=True)}%, el mercado es estable, favoreciendo compromisos a mediano plazo.")
                if not pd.isna(rsi_copper):
                    if rsi_copper > 70:
                        recommendations.append(f"El RSI del cobre en {locale.format_string('%.2f', rsi_copper, grouping=True)} indica sobrecompra, sugiriendo una posible corrección bajista.")
                    elif rsi_copper < 30:
                        recommendations.append(f"El RSI del cobre en {locale.format_string('%.2f', rsi_copper, grouping=True)} señala sobreventa, presentando una oportunidad de compra.")
                    else:
                        recommendations.append(f"El RSI del cobre en {locale.format_string('%.2f', rsi_copper, grouping=True)} refleja equilibrio de mercado.")
                if not pd.isna(corr_copper_oil) and corr_copper_oil > 0.5:
                    recommendations.append(f"La correlación positiva cobre-petróleo ({locale.format_string('%.4f', corr_copper_oil, grouping=True)}) sugiere monitorear indicadores energéticos.")
                for rec in recommendations:
                    st.write(rec)

                # Proyección a 4 Meses mejorada
                st.subheader("Proyección a 4 Meses (Toneladas de Cobre Comprable)")
                if not historical_df.empty:
                    span = 30
                    days_ahead = 80  # Días hábiles en 4 meses
                    # Proyección para cobre
                    copper_ema, copper_min, copper_max = project_future_price(copper_hist, span)
                    if not np.isnan(copper_ema):
                        copper_slope_30, _ = calculate_trend(copper_hist, span)
                        copper_future = copper_ema + (copper_slope_30 * days_ahead)
                        copper_future_min = copper_min + (copper_slope_30 * days_ahead) - (historical_df["Copper"].std() * np.sqrt(days_ahead) / np.sqrt(252))
                        copper_future_max = copper_max + (copper_slope_30 * days_ahead) + (historical_df["Copper"].std() * np.sqrt(days_ahead) / np.sqrt(252))
                    else:
                        copper_future, copper_future_min, copper_future_max = copper_price, copper_price, copper_price
                    # Proyección para petróleo
                    oil_ema, oil_min, oil_max = project_future_price(oil_hist, span)
                    if not np.isnan(oil_ema):
                        oil_slope_30, _ = calculate_trend(oil_hist, span)
                        oil_future = oil_ema + (oil_slope_30 * days_ahead)
                        oil_future_min = oil_min + (oil_slope_30 * days_ahead) - (historical_df["Oil"].std() * np.sqrt(days_ahead) / np.sqrt(252))
                        oil_future_max = oil_max + (oil_slope_30 * days_ahead) + (historical_df["Oil"].std() * np.sqrt(days_ahead) / np.sqrt(252))
                    else:
                        oil_future, oil_future_min, oil_future_max = oil_price, oil_price, oil_price
                    # Proyección para EUR/CNY
                    eur_cny_ema, eur_cny_min, eur_cny_max = project_future_price(eur_cny_hist, span)
                    if not np.isnan(eur_cny_ema):
                        eur_cny_slope_30, _ = calculate_trend(eur_cny_hist, span)
                        eur_cny_future = eur_cny_ema + (eur_cny_slope_30 * days_ahead)
                        eur_cny_future_min = eur_cny_min + (eur_cny_slope_30 * days_ahead) - (historical_df["EUR/CNY"].std() * np.sqrt(days_ahead) / np.sqrt(252))
                        eur_cny_future_max = eur_cny_max + (eur_cny_slope_30 * days_ahead) + (historical_df["EUR/CNY"].std() * np.sqrt(days_ahead) / np.sqrt(252))
                    else:
                        eur_cny_future, eur_cny_future_min, eur_cny_future_max = eur_cny_price, eur_cny_price, eur_cny_price
                    # Proyección para USD/CNY
                    usd_cny_ema, usd_cny_min, usd_cny_max = project_future_price(usd_cny_hist, span)
                    if not np.isnan(usd_cny_ema):
                        usd_cny_slope_30, _ = calculate_trend(usd_cny_hist, span)
                        usd_cny_future = usd_cny_ema + (usd_cny_slope_30 * days_ahead)
                        usd_cny_future_min = usd_cny_min + (usd_cny_slope_30 * days_ahead) - (historical_df["USD/CNY"].std() * np.sqrt(days_ahead) / np.sqrt(252))
                        usd_cny_future_max = usd_cny_max + (usd_cny_slope_30 * days_ahead) + (historical_df["USD/CNY"].std() * np.sqrt(days_ahead) / np.sqrt(252))
                    else:
                        usd_cny_future, usd_cny_future_min, usd_cny_future_max = usd_cny_price, usd_cny_price, usd_cny_price
                    # Cálculo de cantidades proyectadas
                    _, _, _, _, future_copper_quantity_ton, _, _, _, _ = calculate_order(
                        budget_eur, copper_percentage, transport_cost_factor, copper_future, oil_future, eur_cny_future, usd_cny_future
                    )
                    _, _, _, _, min_copper_quantity_ton, _, _, _, _ = calculate_order(
                        budget_eur, copper_percentage, transport_cost_factor, copper_future_max, oil_future_max, eur_cny_future_min, usd_cny_future_max
                    )
                    _, _, _, _, max_copper_quantity_ton, _, _, _, _ = calculate_order(
                        budget_eur, copper_percentage, transport_cost_factor, copper_future_min, oil_future_min, eur_cny_future_max, usd_cny_future_min
                    )
                    delta_copper = future_copper_quantity_ton - copper_quantity_ton if not np.isnan(copper_quantity_ton) else np.nan
                    proj_data = {
                        "Esperado (ton)": locale.format_string('%.2f', future_copper_quantity_ton, grouping=True),
                        "Min (ton)": locale.format_string('%.2f', min_copper_quantity_ton, grouping=True),
                        "Max (ton)": locale.format_string('%.2f', max_copper_quantity_ton, grouping=True),
                        "Delta vs Actual (ton)": locale.format_string('%.2f', delta_copper, grouping=True)
                    }
                    st.table(pd.DataFrame([proj_data]))
                    # Gráfico de proyección mejorado con área de confianza
                    fig_proj = go.Figure()
                    fig_proj.add_trace(go.Scatter(
                        x=["Actual", "Esperado", "Mínimo", "Máximo"],
                        y=[copper_quantity_ton, future_copper_quantity_ton, min_copper_quantity_ton, max_copper_quantity_ton],
                        mode="lines+markers",
                        name="Cantidad Proyectada",
                        line=dict(width=2)
                    ))
                    fig_proj.add_trace(go.Scatter(
                        x=["Mínimo", "Máximo", "Máximo", "Mínimo"],
                        y=[min_copper_quantity_ton, max_copper_quantity_ton, max_copper_quantity_ton, min_copper_quantity_ton],
                        fill="toself",
                        fillcolor="rgba(0,100,80,0.2)",
                        line=dict(color="rgba(255,255,255,0)"),
                        name="Intervalo de Confianza",
                        showlegend=True
                    ))
                    fig_proj.update_layout(
                        title="Proyección de Cantidad de Cobre Comprable a 4 Meses",
                        xaxis_title="Escenario",
                        yaxis_title="Toneladas de Cobre",
                        hovermode="x unified",
                        showlegend=True
                    )
                    st.plotly_chart(fig_proj, use_container_width=True)
                else:
                    st.info("No hay datos históricos suficientes para la proyección.")

                # Indicadores Técnicos: Bollinger Bands y MACD
                st.subheader("🔍 Indicadores Técnicos: Bollinger Bands y MACD para el Cobre")
                if not copper_hist.empty and 'Close' in copper_hist.columns and len(copper_hist) >= 26:
                    # Bollinger Bands
                    st.markdown("### Bandas de Bollinger")
                    if len(copper_hist) >= 20:
                        window = 20
                        copper_hist['SMA'] = copper_hist['Close'].rolling(window=window).mean()
                        copper_hist['STD'] = copper_hist['Close'].rolling(window=window).std()
                        copper_hist['Upper Band'] = copper_hist['SMA'] + (copper_hist['STD'] * 2)
                        copper_hist['Lower Band'] = copper_hist['SMA'] - (copper_hist['STD'] * 2)
                        try:
                            latest_price = float(copper_hist['Close'].iloc[-1])
                            latest_upper = float(copper_hist['Upper Band'].iloc[-1])
                            latest_lower = float(copper_hist['Lower Band'].iloc[-1])
                            if np.isnan(latest_price) or np.isnan(latest_upper) or np.isnan(latest_lower):
                                st.warning("Datos insuficientes o valores NaN en las Bandas de Bollinger.")
                            else:
                                if latest_price > latest_upper:
                                    st.write("**Estado:** Sobrecompra (el precio está por encima de la banda superior)")
                                elif latest_price < latest_lower:
                                    st.write("**Estado:** Sobreventa (el precio está por debajo de la banda inferior)")
                                else:
                                    st.write("**Estado:** Dentro de las bandas (neutral)")
                                fig_bb = go.Figure()
                                fig_bb.add_trace(go.Scatter(x=copper_hist.index, y=copper_hist['Close'], name='Precio Cobre', line=dict(color='royalblue')))
                                fig_bb.add_trace(go.Scatter(x=copper_hist.index, y=copper_hist['Upper Band'], name='Banda Superior', line=dict(color='red', dash='dash')))
                                fig_bb.add_trace(go.Scatter(x=copper_hist.index, y=copper_hist['SMA'], name='Media Móvil (20)', line=dict(color='green')))
                                fig_bb.add_trace(go.Scatter(x=copper_hist.index, y=copper_hist['Lower Band'], name='Banda Inferior', line=dict(color='red', dash='dash')))
                                fig_bb.update_layout(
                                    title="Bandas de Bollinger para el Cobre",
                                    xaxis_title="Fecha",
                                    yaxis_title="Precio (USD/lb)",
                                    hovermode="x unified",
                                    showlegend=True
                                )
                                st.plotly_chart(fig_bb, use_container_width=True, key="bollinger_chart")
                        except Exception as e:
                            st.error(f"Error al calcular las Bandas de Bollinger: {e}")
                    else:
                        st.error("No se encontraron datos históricos suficientes para el cobre (mínimo 20 días).")
                    # MACD
                    st.markdown("### MACD (Convergencia/Divergencia de Medias Móviles)")
                    if len(copper_hist) >= 26:
                        try:
                            short_ema = copper_hist['Close'].ewm(span=12, adjust=False).mean()
                            long_ema = copper_hist['Close'].ewm(span=26, adjust=False).mean()
                            copper_hist['MACD'] = short_ema - long_ema
                            copper_hist['Signal'] = copper_hist['MACD'].ewm(span=9, adjust=False).mean()
                            copper_hist['Histogram'] = copper_hist['MACD'] - copper_hist['Signal']
                            latest_macd = float(copper_hist['MACD'].iloc[-1])
                            latest_signal = float(copper_hist['Signal'].iloc[-1])
                            if np.isnan(latest_macd) or np.isnan(latest_signal):
                                st.warning("Datos insuficientes o valores NaN en el cálculo del MACD.")
                            else:
                                if latest_macd > latest_signal:
                                    st.write("**Señal:** Alcista (MACD por encima de la línea de señal)")
                                else:
                                    st.write("**Señal:** Bajista (MACD por debajo de la línea de señal)")
                                fig_macd = go.Figure()
                                fig_macd.add_trace(go.Scatter(x=copper_hist.index, y=copper_hist['MACD'], name='MACD', line=dict(color='blue')))
                                fig_macd.add_trace(go.Scatter(x=copper_hist.index, y=copper_hist['Signal'], name='Línea de Señal', line=dict(color='orange')))
                                fig_macd.add_trace(go.Bar(x=copper_hist.index, y=copper_hist['Histogram'], name='Histograma', marker_color='gray'))
                                fig_macd.update_layout(
                                    title="MACD para el Cobre",
                                    xaxis_title="Fecha",
                                    yaxis_title="Valor",
                                    hovermode="x unified",
                                    showlegend=True
                                )
                                st.plotly_chart(fig_macd, use_container_width=True, key="macd_chart")
                        except Exception as e:
                            st.error(f"Error al calcular el MACD: {e}")
                    else:
                        st.error("No se encontraron datos históricos suficientes para el MACD (mínimo 26 días).")
                else:
                    st.error("No se encontraron datos históricos del cobre o la columna 'Close' no está disponible.")

                # Análisis de Sensibilidad y Monte Carlo
                st.subheader("🔍 Análisis de Sensibilidad y Simulación Monte Carlo")
                if not np.isnan(copper_price) and not np.isnan(oil_price) and not np.isnan(eur_cny_price) and not np.isnan(usd_cny_price):
                    # Sensibilidad
                    st.markdown("### Análisis de Sensibilidad (±5% en variables clave)")
                    variations = {
                        "Cobre +5%": (copper_price * 1.05, oil_price, eur_cny_price, usd_cny_price),
                        "Cobre -5%": (copper_price * 0.95, oil_price, eur_cny_price, usd_cny_price),
                        "Petróleo +5%": (copper_price, oil_price * 1.05, eur_cny_price, usd_cny_price),
                        "Petróleo -5%": (copper_price, oil_price * 0.95, eur_cny_price, usd_cny_price),
                        "EUR/CNY +5%": (copper_price, oil_price, eur_cny_price * 1.05, usd_cny_price),
                        "EUR/CNY -5%": (copper_price, oil_price, eur_cny_price * 0.95, usd_cny_price),
                    }
                    sensitivity_results = {}
                    for label, (c_p, o_p, e_c, u_c) in variations.items():
                        _, _, _, _, copper_qty_ton, _, _, _, _ = calculate_order(
                            budget_eur, copper_percentage, transport_cost_factor, c_p, o_p, e_c, u_c
                        )
                        sensitivity_results[label] = copper_qty_ton
                    sens_df = pd.DataFrame.from_dict(sensitivity_results, orient="index", columns=["Toneladas de Cobre"])
                    st.table(sens_df)
                    fig_sens = go.Figure(go.Bar(
                        x=sens_df.index,
                        y=sens_df["Toneladas de Cobre"],
                        marker_color="teal"
                    ))
                    fig_sens.update_layout(
                        title="Impacto de ±5% en Variables Clave",
                        xaxis_title="Escenario",
                        yaxis_title="Toneladas de Cobre",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_sens, use_container_width=True)
                    # Monte Carlo
                    st.markdown("### Simulación Monte Carlo (1000 escenarios a 4 meses)")
                    n_sim = 1000
                    days_ahead = 80
                    np.random.seed(42)
                    pct_changes_copper = copper_hist["Close"].pct_change().dropna()
                    vol_copper = np.std(pct_changes_copper) if len(pct_changes_copper) > 0 else 0.012
                    pct_changes_oil = oil_hist["Close"].pct_change().dropna()
                    vol_oil = np.std(pct_changes_oil) if len(pct_changes_oil) > 0 else 0.02
                    pct_changes_eurcny = eur_cny_hist["Close"].pct_change().dropna()
                    vol_eurcny = np.std(pct_changes_eurcny) if len(pct_changes_eurcny) > 0 else 0.004
                    pct_changes_usdcny = usd_cny_hist["Close"].pct_change().dropna()
                    vol_usdcny = np.std(pct_changes_usdcny) if len(pct_changes_usdcny) > 0 else 0.004
                    sim_results = []
                    for _ in range(n_sim):
                        sim_copper = copper_price * np.exp(np.random.normal(0, vol_copper * np.sqrt(days_ahead)))
                        sim_oil = oil_price * np.exp(np.random.normal(0, vol_oil * np.sqrt(days_ahead)))
                        sim_eurcny = eur_cny_price * np.exp(np.random.normal(0, vol_eurcny * np.sqrt(days_ahead)))
                        sim_usdcny = usd_cny_price * np.exp(np.random.normal(0, vol_usdcny * np.sqrt(days_ahead)))
                        _, _, _, _, sim_qty_ton, _, _, _, _ = calculate_order(
                            budget_eur, copper_percentage, transport_cost_factor, sim_copper, sim_oil, sim_eurcny, sim_usdcny
                        )
                        if not np.isnan(sim_qty_ton):
                            sim_results.append(sim_qty_ton)
                    if len(sim_results) > 0:
                        mean_qty = np.mean(sim_results)
                        std_qty = np.std(sim_results)
                        min_qty = np.min(sim_results)
                        max_qty = np.max(sim_results)
                        p5 = np.percentile(sim_results, 5)
                        p50 = np.median(sim_results)
                        p95 = np.percentile(sim_results, 95)
                        mc_summary = pd.DataFrame({
                            "Estadístico": ["Media", "Desviación Estándar", "Mínimo", "Percentil 5%", "Mediana", "Percentil 95%", "Máximo"],
                            "Valor (ton)": [locale.format_string('%.2f', mean_qty, grouping=True),
                                            locale.format_string('%.2f', std_qty, grouping=True),
                                            locale.format_string('%.2f', min_qty, grouping=True),
                                            locale.format_string('%.2f', p5, grouping=True),
                                            locale.format_string('%.2f', p50, grouping=True),
                                            locale.format_string('%.2f', p95, grouping=True),
                                            locale.format_string('%.2f', max_qty, grouping=True)]
                        })
                        st.table(mc_summary)
                        # Histograma Monte Carlo
                        fig_mc = px.histogram(
                            sim_results,
                            nbins=50,
                            title="Distribución de Toneladas de Cobre (Monte Carlo)",
                            labels={"value": "Toneladas de Cobre", "count": "Frecuencia"}
                        )
                        fig_mc.add_vline(x=mean_qty, line_dash="dash", line_color="red", annotation_text="Media")
                        fig_mc.add_vline(x=p5, line_dash="dot", line_color="green", annotation_text="P5")
                        fig_mc.add_vline(x=p95, line_dash="dot", line_color="green", annotation_text="P95")
                        fig_mc.update_layout(
                            xaxis_title="Toneladas de Cobre",
                            yaxis_title="Frecuencia",
                            hovermode="x unified",
                            showlegend=True
                        )
                        st.plotly_chart(fig_mc, use_container_width=True)
                    else:
                        st.info("No se pudieron generar simulaciones válidas debido a datos insuficientes.")
                else:
                    st.error("Faltan datos de precios actuales para realizar el análisis.")

    update_dashboard()
    if auto_update:
        time.sleep(refresh_rate)
        st.rerun()

with tab2:
    st.header("Análisis de Compra Pasada: Comparación de Precios y Tasas de Cambio")
    purchase_date = st.date_input("Fecha de la compra pasada", value=datetime.now() - timedelta(days=30))
    sale_date = st.date_input("Fecha de venta ficticia", value=datetime.now() - timedelta(days=15), min_value=purchase_date)
    
    if st.button("Analizar Comparación de Compra y Venta"):
        def get_closest_data(ticker, target_date):
            start_date = target_date - timedelta(days=10)
            end_date = target_date + timedelta(days=10)
            try:
                df = yf.download(ticker, start=start_date, end=end_date, interval="1d", auto_adjust=False)
                if df.empty:
                    return np.nan
                dates = df.index
                target = pd.to_datetime(target_date)
                diff = np.abs(dates - target)
                closest_idx = diff.argmin()
                return float(df.iloc[closest_idx]["Close"])
            except Exception as e:
                st.error(f"Error al descargar datos para {ticker}: {e}")
                return np.nan
        
        try:
            copper_price_usd_past = get_closest_data("HG=F", purchase_date)
            eur_cny_price_past = get_closest_data("EURCNY=X", purchase_date)
            usd_cny_price_past = get_closest_data("USDCNY=X", purchase_date)
            if any(np.isnan(x) for x in [copper_price_usd_past, eur_cny_price_past, usd_cny_price_past]):
                st.warning("No se encontraron datos cercanos para la fecha de compra.")
            else:
                copper_price_cny_past = copper_price_usd_past * usd_cny_price_past
                copper_price_usd_sale = get_closest_data("HG=F", sale_date)
                eur_cny_price_sale = get_closest_data("EURCNY=X", sale_date)
                usd_cny_price_sale = get_closest_data("USDCNY=X", sale_date)
                if any(np.isnan(x) for x in [copper_price_usd_sale, eur_cny_price_sale, usd_cny_price_sale]):
                    st.warning("No se encontraron datos cercanos para la fecha de venta ficticia.")
                else:
                    copper_price_cny_sale = copper_price_usd_sale * usd_cny_price_sale
                    st.subheader("Comparación de Precios y Tasas de Cambio")
                    comparison_df = pd.DataFrame({
                        "Métrica": ["Precio del cobre (USD/lb)", "Precio del cobre (CNY/lb)", "EUR/CNY", "USD/CNY"],
                        "Fecha de Compra ({})".format(purchase_date): [
                            locale.format_string('%.2f', copper_price_usd_past, grouping=True),
                            locale.format_string('%.2f', copper_price_cny_past, grouping=True),
                            locale.format_string('%.4f', eur_cny_price_past, grouping=True),
                            locale.format_string('%.4f', usd_cny_price_past, grouping=True)
                        ],
                        "Fecha de Venta ({})".format(sale_date): [
                            locale.format_string('%.2f', copper_price_usd_sale, grouping=True),
                            locale.format_string('%.2f', copper_price_cny_sale, grouping=True),
                            locale.format_string('%.4f', eur_cny_price_sale, grouping=True),
                            locale.format_string('%.4f', usd_cny_price_sale, grouping=True)
                        ],
                        "Diferencia (Venta - Compra)": [
                            locale.format_string('%.2f', copper_price_usd_sale - copper_price_usd_past, grouping=True),
                            locale.format_string('%.2f', copper_price_cny_sale - copper_price_cny_past, grouping=True),
                            locale.format_string('%.4f', eur_cny_price_sale - eur_cny_price_past, grouping=True),
                            locale.format_string('%.4f', usd_cny_price_sale - usd_cny_price_past, grouping=True)
                        ]
                    })
                    st.table(comparison_df)
        except Exception as e:
            st.error(f"Error general al obtener datos: {e}")
