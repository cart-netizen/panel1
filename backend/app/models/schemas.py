from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

# --- Модели для генерации (без изменений) ---

class GenerationParams(BaseModel):
    generator_type: Literal['multi_strategy', 'ml_based_rf', 'hot', 'cold', 'balanced', 'rf_ranked'] = Field(
        'multi_strategy',
        description="Тип генератора для использования"
    )
    num_combinations: int = Field(
        10,
        gt=0,
        le=50,
        description="Количество комбинаций для генерации (от 1 до 50)"
    )

class Combination(BaseModel):
    field1: List[int]
    field2: List[int]
    description: str

class GenerationResponse(BaseModel):
    combinations: List[Combination]
    rf_prediction: Optional[Combination]
    lstm_prediction: Optional[Combination]


# --- Модели для верификации (без изменений) ---

class TicketVerificationRequest(BaseModel):
    field1: List[int]
    field2: List[int]

class VerificationResult(BaseModel):
    draw_number: int
    draw_date: str
    winning_numbers: str
    matches: str
    category: str

# --- Модели для симуляции банкролла (без изменений) ---

class SimulationParams(BaseModel):
    initial_bankroll: int = Field(50000, gt=0)
    ticket_cost: int = Field(250, gt=0)
    strategy: Literal['multi', 'hot', 'cold', 'balanced', 'rf_ranked'] = 'multi'
    combos_per_draw: int = Field(10, gt=0, le=50)
    num_draws_to_simulate: int = Field(50, gt=10, le=200)

class SimulationResponse(BaseModel):
    initial_bankroll: float
    final_bankroll: float
    total_profit: float
    total_roi_percent: float
    max_drawdown_percent: float
    sharpe_ratio: float
    went_broke: bool
    bankroll_history: List[float]

# --- Модели для кластеризации (без изменений) ---

class ClusteringParams(BaseModel):
    method: Literal['kmeans', 'dbscan'] = 'kmeans'
    n_clusters: int = Field(5, ge=2, le=15)
    eps: float = Field(1.5, ge=0.1, le=5.0)
    min_samples: int = Field(10, ge=2, le=50)

class ClusteringResult(BaseModel):
    pca_components: List[dict]
    labels: List[int]
    hover_data: List[str]

# --- НОВЫЕ МОДЕЛИ ДЛЯ НЕДОСТАЮЩИХ ЭНДПОИНТОВ ---

# Модель для ответа при проверке ОДНОГО билета.
# Использует существующую модель VerificationResult для описания каждого выигрыша.
class TicketCheckResponse(BaseModel):
    ticket_checked: str = Field(description="Строковое представление проверенного билета")
    is_winner: bool = Field(description="Является ли билет выигрышным хотя бы в одном тираже")
    wins: List[VerificationResult] = Field(description="Список всех выигрышных тиражей для этого билета")

# --- Модели для эндпоинта анализа паттернов ---

class HotColdNumbers(BaseModel):
    hot: List[List[Any]] = Field(description="Горячие числа в формате [[число, частота], ...]")
    cold: List[List[Any]] = Field(description="Холодные числа в формате [[число, частота], ...]")

class PatternAnalysisResponse(BaseModel):
    field1: HotColdNumbers
    field2: HotColdNumbers
    # В будущем можно будет расширить для корреляций и циклов

# --- Модель для ответа от эндпоинта обновления данных ---

class DataUpdateResponse(BaseModel):
    status: str
    message: str
    draws_in_db: int

class CorrelationPair(BaseModel):
    pair: str
    frequency_percent: float
    count: int

class CycleStat(BaseModel):
    number: int
    last_seen_ago: int
    avg_cycle: float
    is_overdue: bool

class FullPatternAnalysis(BaseModel):
    hot_cold: PatternAnalysisResponse # Используем уже существующую модель
    correlations_field1: List[CorrelationPair]
    correlations_field2: List[CorrelationPair]
    cycles_field1: List[CycleStat]
    cycles_field2: List[CycleStat]

#--