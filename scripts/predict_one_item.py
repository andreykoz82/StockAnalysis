# %%
# ПРОГНОЗИРОВАНИЕ ДЛЯ ОДНОЙ НОМЕНКЛАТУРНОЙ ПОЗИЦИИ
import warnings
import pandas as pd
from sqlalchemy import create_engine
import timesfm
import os
import numpy as np
warnings.filterwarnings('ignore')
os.environ['CURL_CA_BUNDLE'] = ''


# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

# Список актуальной номенклатуры
item_list = 'Стоматофит 100 мл'


train_end = '2025-01-31'
forecast_start = '2025-02-01'
forecast_end = '2025-02-28'
prediction_length = 1

forecast_results = []

sales_forecast = pd.DataFrame([{'ds':None, 'timesfm':None, 'item':None}])

# %%
tfm = timesfm.TimesFm(
      hparams=timesfm.TimesFmHparams(
          backend="cpu",
          per_core_batch_size=32,
          horizon_len=prediction_length,
          num_layers=50,
          context_len=64,
      ),
      checkpoint=timesfm.TimesFmCheckpoint(
          huggingface_repo_id="google/timesfm-2.0-500m-pytorch"),
  )


sales_by_item_sql = f"""
SELECT "Дата", "Продажи"
FROM public.sales
WHERE "Номенклатура" = '{item_list}'
"""

sales_by_item = pd.read_sql_query(sales_by_item_sql, engine).set_index('Дата')

train = sales_by_item[sales_by_item.index <= train_end].resample('M').sum()
data_train_log = train

df = pd.DataFrame({'unique_id': [1] * len(data_train_log),
                   'ds': data_train_log.index,
                   "y": data_train_log['Продажи']})

timesfm_forecast = tfm.forecast_on_df(
    inputs=df,
    freq="M",
    value_name="y",
    num_jobs=-1,
)
timesfm_forecast['timesfm'] = timesfm_forecast['timesfm']
timesfm_forecast = timesfm_forecast[["ds","timesfm"]]
timesfm_forecast['item'] = item_list
sales_forecast = pd.concat([timesfm_forecast, sales_forecast], axis=0)
