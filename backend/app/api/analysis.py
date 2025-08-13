from fastapi import APIRouter, Depends, Path, HTTPException
import pandas as pd

from backend.app.core import clustering_analysis, data_manager
from backend.app.models.schemas import ClusteringParams, ClusteringResult
from backend.app.core.lottery_context import LotteryContext

router = APIRouter()


async def set_lottery_context(
    lottery_type: str = Path(..., description="Тип лотереи: '4x20' или '5x36plus'")
):
  if lottery_type not in data_manager.LOTTERY_CONFIGS:
    raise HTTPException(status_code=404, detail="Lottery type not found")
  
  data_manager.set_current_lottery(lottery_type)
  print(f"[CONTEXT] Установлен контекст лотереи: {lottery_type}")
  yield


@router.get("/history", summary="Получить историю тиражей")
def get_history(
    lottery_type: str = Path(..., description="Тип лотереи: '4x20' или '5x36plus'"),
    date_start: str = None,
    date_end: str = None,
    draw_start: int = None,
    draw_end: int = None
):
  """Возвращает историю тиражей с возможностью фильтрации."""
  if lottery_type not in data_manager.LOTTERY_CONFIGS:
    raise HTTPException(status_code=404, detail="Lottery type not found")
  
  with LotteryContext(lottery_type):
    df = data_manager.fetch_draws_from_db(date_start, date_end, draw_start, draw_end)
    return df.to_dict(orient='records')


@router.post("/clustering", response_model=ClusteringResult, summary="Выполнить кластерный анализ")
def run_clustering(
    params: ClusteringParams, 
    lottery_type: str = Path(..., description="Тип лотереи: '4x20' или '5x36plus'")
):
  """
  Выполняет кластеризацию на исторических данных и возвращает результат,
  готовый для отрисовки на фронтенде.
  """
  if lottery_type not in data_manager.LOTTERY_CONFIGS:
    raise HTTPException(status_code=404, detail="Lottery type not found")
  
  with LotteryContext(lottery_type):
    df_history = data_manager.fetch_draws_from_db()
    if df_history.empty:
      raise HTTPException(status_code=404, detail="No historical data found for clustering")

    features_df, original_combos = clustering_analysis.prepare_data_for_clustering(df_history)  #

    if features_df is None:
      raise HTTPException(status_code=500, detail="Failed to prepare data for clustering")

    labels = None
    if params.method == 'kmeans':
      labels = clustering_analysis.run_kmeans_clustering(features_df, n_clusters=params.n_clusters)  #
    else:  # dbscan
      labels = clustering_analysis.run_dbscan_clustering(features_df, eps=params.eps, min_samples=params.min_samples)  #

    if labels is None:
      raise HTTPException(status_code=500, detail="Clustering execution failed")

    # Вместо отрисовки, возвращаем данные для нее
    pca_df = clustering_analysis.plot_clusters_pca(features_df, labels, original_combos, title="").data[0]  #

    return ClusteringResult(
      pca_components=pd.DataFrame({'PCA1': pca_df['x'], 'PCA2': pca_df['y']}).to_dict(orient='records'),
      labels=pca_df['customdata'][0],
      hover_data=pca_df['hovertext']
    )


@router.get("/latest-draw", summary="Получить последний тираж")
def get_latest_draw(lottery_type: str = Path(..., description="Тип лотереи: '4x20' или '5x36plus'")):
  """Возвращает информацию о последнем тираже для текущей лотереи"""
  if lottery_type not in data_manager.LOTTERY_CONFIGS:
    raise HTTPException(status_code=404, detail="Lottery type not found")
  
  with LotteryContext(lottery_type):
    df_history = data_manager.fetch_draws_from_db()
    
    if df_history.empty:
      raise HTTPException(status_code=404, detail="Нет данных тиражей")
    
    # Последний тираж (первая строка, так как данные отсортированы по убыванию)
    latest_draw = df_history.iloc[0]
    
    return {
      "draw_number": int(latest_draw["Тираж"]),
      "draw_date": latest_draw["Дата"].isoformat() if hasattr(latest_draw["Дата"], 'isoformat') else str(latest_draw["Дата"]),
      "field1_numbers": latest_draw["Числа_Поле1_list"],
      "field2_numbers": latest_draw["Числа_Поле2_list"],
      "lottery_type": lottery_type
    }