# %%
import itertools
import statsmodels.api as sm
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine

FONT_COLOR = "(0.8,0.8,0.8)"
BACKGROUND_COLOR = '(0.22, 0.22, 0.22)'
plt.rcParams['axes.facecolor'] = BACKGROUND_COLOR
plt.rcParams['figure.facecolor'] = BACKGROUND_COLOR
plt.rcParams['text.color'] = FONT_COLOR
plt.rcParams['axes.labelcolor'] = FONT_COLOR
plt.rcParams['xtick.color'] = FONT_COLOR
plt.rcParams['ytick.color'] = FONT_COLOR

# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

sales_by_item_sql = f"""
SELECT "Дата", "Продажи"
FROM public.sales
"""
dataset = pd.read_sql_query(sales_by_item_sql, engine).set_index('Дата')
dataset = dataset.groupby(pd.Grouper(freq='M')).sum()


p = d = q = range(0, 2)
pdq = list(itertools.product(p, d, q))
seasonal_pdq = [(x[0], x[1], x[2], 12) for x in list(itertools.product(p, d, q))]

res_aic = 9999
arima_param = 0
arima_param_seas = 0

for param in pdq:
    for param_seasonal in seasonal_pdq:
        try:
            mod = sm.tsa.statespace.SARIMAX(dataset,
                                            order=param,
                                            seasonal_order=param_seasonal,
                                            enforce_stationarity=False,
                                            enforce_invertibility=False)
            model = mod.fit()
            if model.aic < res_aic:
                res_aic = model.aic
                arima_param = param
                arima_param_seas = param_seasonal
        except:
            continue

mod = sm.tsa.statespace.SARIMAX(dataset,
                                order=arima_param,
                                seasonal_order=arima_param_seas,
                                enforce_stationarity=False,
                                enforce_invertibility=False)
model = mod.fit()



predictions = model.get_prediction(start=dataset.index[0]).predicted_mean
mape = np.mean(np.abs((dataset.values - predictions.values) / dataset.to_numpy())) * 100
forecast = model.get_forecast(steps=12).predicted_mean



plt.figure(figsize=(8, 4))
plt.plot(forecast.index, forecast, marker='o', markersize=5, c='#7FFFD4', mfc='red')
plt.xticks(forecast.index, rotation=90)
plt.xlabel('Date')
plt.ylabel('Quantity')
plt.title(f"Forecast plot. MAPE = {round(mape, 0)} %", pad=20)
plt.grid(linestyle='--', c='grey')

for x, y in zip(forecast.index, forecast):
    label = y
    plt.annotate(f"{round(label):,}", (x, y),
                 xycoords="data",
                 textcoords="offset points",
                 xytext=(0, 10), ha="center")
plt.tight_layout()    
plt.show()