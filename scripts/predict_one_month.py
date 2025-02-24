# %%
# ПРОГНОЗИРОВАНИЕ ДЛЯ ОДНОЙ НОМЕНКЛАТУРНОЙ ПОЗИЦИИ
import warnings
import pandas as pd
from sqlalchemy import create_engine
import timesfm
import os
warnings.filterwarnings('ignore')
os.environ['CURL_CA_BUNDLE'] = ''


# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')


train_end = '2025-01-31'
forecast_start = '2025-02-01'
forecast_end = '2025-02-28'
prediction_length = 1


forecast_results = []

sales_forecast = pd.DataFrame([{'ds':None, 'timesfm':None, 'item':None}])

tfm = timesfm.TimesFm(
      hparams=timesfm.TimesFmHparams(
          backend="cpu",
          per_core_batch_size=32,
          horizon_len=prediction_length,
          num_layers=50,
          context_len=2048,
      ),
      checkpoint=timesfm.TimesFmCheckpoint(
          huggingface_repo_id="google/timesfm-2.0-500m-pytorch"),
  )


sales_by_month_sql = f"""
SELECT
    DATE_TRUNC('month', Дата) + INTERVAL '1 month - 1 day' AS Дата,
    SUM(Продажи) AS ОбщиеПродажи
FROM
    sales
GROUP BY
    DATE_TRUNC('month', Дата) + INTERVAL '1 month - 1 day'
ORDER BY
    Дата;
"""

sales_by_month = pd.read_sql_query(sales_by_month_sql, engine).set_index('Дата')

train = sales_by_month[sales_by_month.index <= train_end].resample('M').sum()

df = pd.DataFrame({'unique_id': [1] * len(train),
                   'ds': train.index,
                   "y": train['ОбщиеПродажи']})

timesfm_forecast = tfm.forecast_on_df(
    inputs=df,
    freq="M",
    value_name="y",
    num_jobs=-1,
)
timesfm_forecast = timesfm_forecast[["ds","timesfm"]]
