# %%
# ПРОГНОЗИРОВАНИЕ ПО ВСЕЙ НОМЕНКЛАТУРЕ
import warnings
import pandas as pd
from sqlalchemy import create_engine
from nixtla import NixtlaClient
import os
warnings.filterwarnings('ignore')
os.environ['CURL_CA_BUNDLE'] = ''


# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

# API token TimeGPT
nixtla_client = NixtlaClient(
    api_key = 'nixak-luVZeRxZBPbarLJ6hOSvQoWkWt8Yta9HbGx3PEsipsxQiMuRDEEGAgqAqvNfDjsszJgPNHN0LDeyQqYS'
)

train_end = '2025-01-31'
forecast_start = '2025-02-01'
forecast_end = '2025-12-31'
prediction_length = 11


forecast_results = []

sales_forecast = pd.DataFrame([{'timestamp':None, 'value':None}])




sales_by_month_sql = f"""
SELECT
    DATE_TRUNC('month', Дата) + INTERVAL '1 month - 1 day' AS timestamp,
    SUM(Продажи) AS value
FROM
    sales
GROUP BY
    DATE_TRUNC('month', Дата) + INTERVAL '1 month - 1 day'
ORDER BY
    timestamp;
"""

sales_by_month = pd.read_sql_query(sales_by_month_sql, engine).set_index('timestamp')

train = sales_by_month[sales_by_month.index <= train_end].resample('M').sum().reset_index()

timegpt_fcst_df = nixtla_client.forecast(df=train,
                                         model='timegpt-1-long-horizon',
                                         h=prediction_length,
                                         freq='M',
                                         time_col='timestamp', target_col='value')
timegpt_fcst_df
