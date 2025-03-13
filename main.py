# %%
import warnings
import pandas as pd
from sqlalchemy import create_engine
import timesfm
import os
import torch
from chronos import BaseChronosPipeline
from nixtla import NixtlaClient

warnings.filterwarnings('ignore')
os.environ['CURL_CA_BUNDLE'] = ''

# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

# Обновление текущих остатков НФП
current_stocks = pd.read_excel('data/semifinished_stocks.xlsx')
current_stocks.to_sql('semifinished_stocks', con=engine, if_exists='replace', index=False)

# Обновление текущих остатков готовой продукции
current_stocks = pd.read_excel('data/finished_goods_stocks.xlsx')
# current_stocks['По дням'] = pd.to_datetime(current_stocks['По дням'], dayfirst=True)
current_stocks.to_sql('current_stocks', con=engine, if_exists='replace', index=False)

# Обновление текущих продаж
sales = pd.read_excel('data/sales.xlsx')
sales['Дата'] = pd.to_datetime(sales['Дата'])
sales.to_sql('sales', con=engine, if_exists='replace', index=False)

# Текущие заказы
actual_orders = pd.read_excel('data/actual_orders_2stage.xlsx')
actual_orders.to_sql('actual_orders', con=engine, if_exists='replace', index=False)

# Обновление остатков печатных материалов
materials_current_stocks = pd.read_excel('data/materials_stocks.xlsx')
materials_current_stocks.to_sql('materials_stocks', con=engine, if_exists='replace', index=False)

# Обновление данных по выпуску ГП
production_2_stage = pd.read_excel('data/production_2_stage.xlsx')
production_2_stage['Период'] = pd.to_datetime(production_2_stage['Период'])
production_2_stage.to_sql('production_2_stage', con=engine, if_exists='replace', index=False)

# Обновление текущей номенклатуры
actual_items = pd.read_excel('data/actual_items.xlsx')
actual_items.to_sql('actual_items', con=engine, if_exists='replace', index=False)

# %%
# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

# Список актуальной номенклатуры
actual_items = pd.read_sql_query(
    """
    SELECT "Наименование"
    FROM public.actual_items
    """,
    con=engine
)
item_list = actual_items['Наименование'].sort_values().to_list()

train_end = '2025-02-28'
forecast_start = '2025-03-01'
forecast_end = '2025-12-31'
# prediction_length = (pd.to_datetime(forecast_end) - pd.to_datetime(forecast_start)).days
prediction_length = 10


forecast_results = []

sales_forecast = pd.DataFrame([{'ds':None, 'timesfm':None, 'item':None}])

tfm = timesfm.TimesFm(
      hparams=timesfm.TimesFmHparams(
          backend="сpu",
          per_core_batch_size=32,
          horizon_len=prediction_length,
      ),
      checkpoint=timesfm.TimesFmCheckpoint(
          huggingface_repo_id="google/timesfm-1.0-200m-pytorch"),
  )

for item in item_list:
    # Выгрузка данных по номенклатуре
    sales_by_item_sql = f"""
    SELECT "Дата", "Продажи"
    FROM public.sales
    WHERE "Номенклатура" = '{item}'
    """
    sales_by_item = pd.read_sql_query(sales_by_item_sql, engine).set_index('Дата')

    if sales_by_item.empty:
        continue

    train = sales_by_item[sales_by_item.index <= train_end].resample('M').sum()

    df = pd.DataFrame({'unique_id': [1] * len(train),
                       'ds': train.index,
                       "y": train['Продажи']})

    timesfm_forecast = tfm.forecast_on_df(
        inputs=df,
        freq="M",
        value_name="y",
        num_jobs=-1,
    )

    timesfm_forecast = timesfm_forecast[["ds","timesfm"]]
    timesfm_forecast['item'] = item
    sales_forecast = pd.concat([timesfm_forecast, sales_forecast], axis=0)
# %%
sales_forecast.to_excel('data/sales_forecast_03_12.xlsx')
# %%
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')
sales_forecast.to_sql('sales_forecast', con=engine, if_exists='append', index=False)

# %% AMAZON CHRONOS

# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

# Список актуальной номенклатуры
actual_items = pd.read_sql_query(
    """
    SELECT "Наименование"
    FROM public.actual_items
    """,
    con=engine
)
item_list = actual_items['Наименование'].sort_values().to_list()

train_end = '2025-01-31'
forecast_start = '2025-02-01'
forecast_end = '2025-12-31'
prediction_length = 11
date_range = pd.date_range(start=forecast_start, end=forecast_end, freq='M')

forecast_results = []

sales_forecast = pd.DataFrame([{'ds':None, 'timesfm':None, 'item':None}])

pipeline = BaseChronosPipeline.from_pretrained(
    "amazon/chronos-bolt-base",
    device_map="cpu",
    torch_dtype=torch.bfloat16,

)

for item in item_list:

    # Выгрузка данных по номенклатуре
    sales_by_item_sql = f"""
    SELECT "Дата", "Продажи"
    FROM public.sales
    WHERE "Номенклатура" = '{item}'
    """
    sales_by_item = pd.read_sql_query(sales_by_item_sql, engine).set_index('Дата')

    if sales_by_item.empty:
        continue

    train = sales_by_item[sales_by_item.index <= train_end].resample('M').sum()

    df = pd.DataFrame({'unique_id': [1] * len(train),
                       'ds': train.index,
                       "y": train['Продажи']})

    quantiles, mean = pipeline.predict_quantiles(
        context=torch.tensor(df['y']),
        prediction_length=prediction_length,
        quantile_levels=[0.1, 0.5, 0.9],
    )
    low, median, high = quantiles[0, :, 0], quantiles[0, :, 1], quantiles[0, :, 2]

    df_amazon = pd.DataFrame({'ds': date_range, "timesfm": median, 'item': item})

    sales_forecast = pd.concat([df_amazon, sales_forecast], axis=0)
# %%
sales_forecast.to_excel('data/sales_forecast_amazon.xlsx')
# %%
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')
sales_forecast.to_sql('sales_forecast', con=engine, if_exists='append', index=False)

# %% TIMEGPT

# Подключение к базе данных
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')

# Список актуальной номенклатуры
actual_items = pd.read_sql_query(
    """
    SELECT "Наименование"
    FROM public.actual_items
    """,
    con=engine
)
item_list = actual_items['Наименование'].sort_values().to_list()

train_end = '2025-01-31'
forecast_start = '2025-02-01'
forecast_end = '2025-12-31'
prediction_length = 11
date_range = pd.date_range(start=forecast_start, end=forecast_end, freq='M')

forecast_results = []

sales_forecast = pd.DataFrame([{'ds':None, 'timesfm':None, 'item':None}])

# API token TimeGPT до 27.03.2025
nixtla_client = NixtlaClient(
    api_key = 'nixak-aKPeLOieXpOAG4sy20UoDPB2IOJg4iIo9Cfw1uiHtK4T7DTLYS1ZOBsv1mo12HL66AMs7KRL9HDhd7fv'
)

for item in item_list:

    # Выгрузка данных по номенклатуре
    sales_by_item_sql = f"""
    SELECT "Дата", "Продажи"
    FROM public.sales
    WHERE "Номенклатура" = '{item}'
    """
    sales_by_item = pd.read_sql_query(sales_by_item_sql, engine).set_index('Дата')

    if sales_by_item.empty:
        continue

    train = sales_by_item[sales_by_item.index <= train_end].resample('M').sum()

    df = pd.DataFrame({'unique_id': [1] * len(train),
                       'ds': train.index,
                       "y": train['Продажи']})

    timegpt_fcst_df = nixtla_client.forecast(df=df,
                                             model='timegpt-1-long-horizon',
                                             h=prediction_length,
                                             freq='ME',
                                             time_col='ds', target_col='y')

    df_timegpt = pd.DataFrame({'ds': timegpt_fcst_df['ds'], "timesfm": timegpt_fcst_df['TimeGPT'], 'item': item})

    sales_forecast = pd.concat([df_timegpt, sales_forecast], axis=0)
# %%
sales_forecast.to_excel('data/sales_forecast_timegpt.xlsx')
# %%
engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')
sales_forecast.to_sql('sales_forecast', con=engine, if_exists='append', index=False)
# %% Загрузка плана продаж
sales_forecast = pd.read_excel('data/sales_plan.xlsx')
sales_forecast['ds'] = pd.to_datetime(sales_forecast['ds'])

engine = create_engine('postgresql+psycopg2://gen_user:Body0906rock@93.183.81.166/stock_analysis')
sales_forecast.to_sql('sales_forecast', con=engine, if_exists='append', index=False)
