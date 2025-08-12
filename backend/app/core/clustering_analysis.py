import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import plotly.express as px

from backend.app.core.utils import format_numbers  # For hover data


def prepare_data_for_clustering(df_history):
  """
  Prepares lottery draw data for clustering.
  Each draw (Field1 + Field2 numbers) is represented as a single numerical vector.
  The current implementation uses the 8 numbers directly and then scales them.
  Alternatively, binary vector representation (MultiLabelBinarizer) could be used.

  Args:
      df_history (pd.DataFrame): DataFrame with historical draws, must include
                                 'Числа_Поле1_list' and 'Числа_Поле2_list'.

  Returns:
      tuple: (scaled_features_df, original_combinations_str)
             scaled_features_df: pd.DataFrame of scaled numerical features for clustering.
             original_combinations_str: List of strings representing the original combinations for hover info.
             Returns (None, None) if data is insufficient or invalid.
  """
  if df_history.empty or 'Числа_Поле1_list' not in df_history.columns or 'Числа_Поле2_list' not in df_history.columns:
    print("Clustering Prep: Missing required columns.")
    return None, None

  valid_feature_vectors = []
  original_combinations_str = []

  for _, row in df_history.iterrows():
    f1 = row['Числа_Поле1_list']
    f2 = row['Числа_Поле2_list']

    if isinstance(f1, list) and len(f1) == 4 and isinstance(f2, list) and len(f2) == 4:
      # Using direct numbers (8 features per draw). Sorting ensures consistency if order doesn't imply position here.
      # For clustering, the order within f1 or f2 might not matter as much as the set of numbers.
      # If positional significance is key, keep them as extracted.
      # Here, we combine them:
      feature_vector = sorted(f1) + sorted(f2)
      valid_feature_vectors.append(feature_vector)
      original_combinations_str.append(f"П1: {format_numbers(f1)}, П2: {format_numbers(f2)}")
    # else:
    # print(f"Clustering Prep: Skipping row due to malformed lists: F1={f1}, F2={f2}")

  if not valid_feature_vectors:
    print("Clustering Prep: No valid feature vectors generated.")
    return None, None

  features_df = pd.DataFrame(valid_feature_vectors, columns=[f'n{i + 1}' for i in range(8)])

  # Standardize features for algorithms sensitive to feature scaling (like K-Means)
  scaler = StandardScaler()
  scaled_features = scaler.fit_transform(features_df)
  scaled_features_df = pd.DataFrame(scaled_features, columns=features_df.columns)

  return scaled_features_df, original_combinations_str


def run_kmeans_clustering(features_df, n_clusters=5, random_state=42):
  """
  Performs K-Means clustering on the provided features.

  Args:
      features_df (pd.DataFrame): DataFrame of numerical features.
      n_clusters (int): The number of clusters to form.
      random_state (int): Random state for reproducibility.

  Returns:
      np.array or None: Array of cluster labels for each sample, or None on error.
  """
  if features_df is None or features_df.empty or len(features_df) < n_clusters:
    print(f"K-Means: Insufficient data for {n_clusters} clusters. Need at least {n_clusters} samples.")
    return None
  try:
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init='auto')
    labels = kmeans.fit_predict(features_df)
    return labels
  except Exception as e:
    print(f"K-Means Error: {e}")
    return None


def run_dbscan_clustering(features_df, eps=1.5, min_samples=10):  # Values adjusted based on code
  """
  Performs DBSCAN clustering on the provided features.
  DBSCAN is sensitive to 'eps' and 'min_samples' parameters, which often require tuning.

  Args:
      features_df (pd.DataFrame): DataFrame of numerical features (ideally scaled).
      eps (float): The maximum distance between two samples for one to be considered
                   as in the neighborhood of the other.
      min_samples (int): The number of samples in a neighborhood for a point
                         to be considered as a core point.

  Returns:
      np.array or None: Array of cluster labels, or None on error. (-1 indicates noise points).
  """
  if features_df is None or features_df.empty or len(features_df) < min_samples:
    print(f"DBSCAN: Insufficient data for min_samples={min_samples}. Need at least {min_samples} samples.")
    return None
  try:
    # For 8-dimensional standardized data, eps might be around sqrt(8) or tuned.
    # min_samples could be related to dimensionality (e.g., 2*dim).
    # The values from the app.py (eps=1.5, min_samples=10) are used.
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    labels = dbscan.fit_predict(features_df)
    return labels
  except Exception as e:
    print(f"DBSCAN Error: {e}")
    return None


def plot_clusters_pca(features_df, labels, original_combinations_str, title="Кластеризация тиражей (PCA)"):
  """
  Visualizes clustering results using PCA to reduce dimensionality to 2D.

  Args:
      features_df (pd.DataFrame): The original (or scaled) feature DataFrame used for clustering.
      labels (np.array): Array of cluster labels assigned to each sample in features_df.
      original_combinations_str (list): List of string representations of the original combinations.
      title (str): The title for the plot.

  Returns:
      plotly.graph_objects.Figure: A Plotly scatter plot figure.
                                   Returns an empty plot on error or insufficient data.
  """
  if features_df is None or features_df.empty or labels is None or len(features_df) != len(labels):
    print("Plot Clusters: Invalid input data for PCA plot.")
    return px.scatter(title="Ошибка: нет данных или метки не совпадают для визуализации кластеров.")

  if len(features_df.columns) < 2:
    print("Plot Clusters: PCA requires at least 2 features.")  # Should not happen with 8 features
    return px.scatter(title="Ошибка: для PCA требуется как минимум 2 признака.")

  try:
    pca = PCA(n_components=2, random_state=42)
    components = pca.fit_transform(features_df)

    pca_df = pd.DataFrame(data=components, columns=['PCA1', 'PCA2'])
    pca_df['Cluster'] = [str(label) for label in labels]  # Convert labels to string for discrete coloring

    if original_combinations_str and len(original_combinations_str) == len(pca_df):
      pca_df['Combination'] = original_combinations_str
    else:  # Fallback if original combinations are not available or mismatch
      pca_df['Combination'] = [f"Точка {i + 1}" for i in range(len(pca_df))]

    fig = px.scatter(pca_df, x='PCA1', y='PCA2', color='Cluster',
                     hover_data=['Combination'],
                     title=title,
                     color_discrete_map={"-1": "grey"}  # Style noise points from DBSCAN as grey
                     )
    fig.update_layout(
      legend_title_text='Кластер',
      xaxis_title="Главная Компонента 1 (PCA)",
      yaxis_title="Главная Компонента 2 (PCA)",
      margin=dict(l=20, r=20, t=40, b=20)
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=0.5, color='DarkSlateGrey')))
    return fig
  except Exception as e:
    print(f"Error during PCA plotting: {e}")
    return px.scatter(title=f"Ошибка визуализации PCA: {e}")