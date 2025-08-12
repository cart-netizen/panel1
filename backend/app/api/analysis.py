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
  with LotteryContext(lottery_type):
    yield


@router.get("/history", summary="Получить историю тиражей")
def get_history(
    date_start: str = None,
    date_end: str = None,
    draw_start: int = None,
    draw_end: int = None,
    context: None = Depends(set_lottery_context)
):
  """Возвращает историю тиражей с возможностью фильтрации."""
  df = data_manager.fetch_draws_from_db(date_start, date_end, draw_start, draw_end)
  return df.to_dict(orient='records')


@router.post("/clustering", response_model=ClusteringResult, summary="Выполнить кластерный анализ")
def run_clustering(params: ClusteringParams, context: None = Depends(set_lottery_context)):
  """
  Выполняет кластеризацию на исторических данных и возвращает результат,
  готовый для отрисовки на фронтенде.
  """
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