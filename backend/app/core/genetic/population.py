"""
Управление популяцией для генетического алгоритма
Профессиональная реализация с элитизмом и адаптивными параметрами
"""

import numpy as np
import random
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field
import logging
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Chromosome:
  """
  Хромосома - представление одной комбинации в генетическом алгоритме
  """
  field1: List[int]
  field2: List[int]
  fitness: float = 0.0
  generation: int = 0
  parents: Optional[Tuple[str, str]] = None  # ID родителей
  mutation_history: List[str] = field(default_factory=list)
  evaluation_details: Dict[str, Any] = field(default_factory=dict)
  chromosome_id: str = field(default_factory=lambda: "")

  def __post_init__(self):
    """Генерация уникального ID после инициализации"""
    if not self.chromosome_id:
      self.chromosome_id = self._generate_id()

  def _generate_id(self) -> str:
    """Генерация уникального ID на основе генов"""
    gene_str = f"{sorted(self.field1)}_{sorted(self.field2)}_{self.generation}"
    return hashlib.md5(gene_str.encode()).hexdigest()[:12]

  def to_tuple(self) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Преобразование в кортеж для хеширования"""
    return (tuple(sorted(self.field1)), tuple(sorted(self.field2)))

  def distance_to(self, other: 'Chromosome') -> float:
    """Расстояние Хэмминга до другой хромосомы"""
    set1_self = set(self.field1 + self.field2)
    set1_other = set(other.field1 + other.field2)
    symmetric_diff = set1_self.symmetric_difference(set1_other)
    max_possible = len(set1_self) + len(set1_other)
    return len(symmetric_diff) / max_possible if max_possible > 0 else 0

  def to_dict(self) -> Dict:
    """Сериализация в словарь"""
    return {
      'id': self.chromosome_id,
      'field1': self.field1,
      'field2': self.field2,
      'fitness': self.fitness,
      'generation': self.generation,
      'parents': self.parents,
      'mutation_history': self.mutation_history,
      'evaluation_details': self.evaluation_details
    }

  def copy(self) -> 'Chromosome':
    """Создание глубокой копии хромосомы"""
    return Chromosome(
      field1=self.field1.copy(),
      field2=self.field2.copy(),
      fitness=self.fitness,
      generation=self.generation,
      parents=self.parents,
      mutation_history=self.mutation_history.copy(),
      evaluation_details=self.evaluation_details.copy()
    )


@dataclass
class PopulationStats:
  """Статистика популяции"""
  generation: int
  size: int
  avg_fitness: float
  max_fitness: float
  min_fitness: float
  std_fitness: float
  diversity_index: float  # Индекс генетического разнообразия
  elite_percentage: float
  mutation_rate: float
  crossover_rate: float
  convergence_rate: float  # Скорость сходимости

  def to_dict(self) -> Dict:
    return {
      'generation': self.generation,
      'size': self.size,
      'avg_fitness': self.avg_fitness,
      'max_fitness': self.max_fitness,
      'min_fitness': self.min_fitness,
      'std_fitness': self.std_fitness,
      'diversity_index': self.diversity_index,
      'elite_percentage': self.elite_percentage,
      'mutation_rate': self.mutation_rate,
      'crossover_rate': self.crossover_rate,
      'convergence_rate': self.convergence_rate
    }


class Population:
  """
  Популяция хромосом для генетического алгоритма
  Включает управление разнообразием и адаптивные параметры
  """

  def __init__(self,
               size: int,
               lottery_config: Dict[str, Any],
               elite_size: int = None,
               diversity_threshold: float = 0.3,
               adaptive_rates: bool = True):
    """
    Args:
        size: Размер популяции
        lottery_config: Конфигурация лотереи
        elite_size: Размер элиты (лучшие особи)
        diversity_threshold: Минимальный порог разнообразия
        adaptive_rates: Использовать адаптивные коэффициенты мутации/кроссовера
    """
    self.size = size
    self.lottery_config = lottery_config
    self.elite_size = elite_size or max(2, size // 10)  # 10% элиты по умолчанию
    self.diversity_threshold = diversity_threshold
    self.adaptive_rates = adaptive_rates

    # Параметры лотереи
    self.field1_size = lottery_config['field1_size']
    self.field2_size = lottery_config['field2_size']
    self.field1_max = lottery_config['field1_max']
    self.field2_max = lottery_config['field2_max']

    # Текущая популяция
    self.chromosomes: List[Chromosome] = []
    self.generation = 0

    # История эволюции
    self.evolution_history: List[PopulationStats] = []
    self.best_ever: Optional[Chromosome] = None

    # Адаптивные параметры
    self.current_mutation_rate = 0.1
    self.current_crossover_rate = 0.8

    # Кэш для ускорения
    self._fitness_cache = {}
    self._diversity_cache = None
    self._last_diversity_gen = -1

    logger.info(f"✅ Популяция инициализирована: размер={size}, элита={self.elite_size}")

  def initialize_random(self):
    """Инициализация случайной популяции с гарантией разнообразия"""
    logger.info(f"🎲 Генерация случайной популяции из {self.size} особей...")

    seen_combinations = set()
    attempts = 0
    max_attempts = self.size * 10

    while len(self.chromosomes) < self.size and attempts < max_attempts:
      # Генерируем случайную комбинацию
      field1 = sorted(random.sample(range(1, self.field1_max + 1), self.field1_size))
      field2 = sorted(random.sample(range(1, self.field2_max + 1), self.field2_size))

      # Проверяем уникальность
      combo_key = (tuple(field1), tuple(field2))
      if combo_key not in seen_combinations:
        chromosome = Chromosome(
          field1=field1,
          field2=field2,
          generation=0
        )
        self.chromosomes.append(chromosome)
        seen_combinations.add(combo_key)

      attempts += 1

    # Дозаполняем если не хватило уникальных
    while len(self.chromosomes) < self.size:
      field1 = sorted(random.sample(range(1, self.field1_max + 1), self.field1_size))
      field2 = sorted(random.sample(range(1, self.field2_max + 1), self.field2_size))

      chromosome = Chromosome(
        field1=field1,
        field2=field2,
        generation=0
      )
      self.chromosomes.append(chromosome)

    logger.info(f"✅ Создано {len(self.chromosomes)} уникальных особей")

  def initialize_from_seeds(self, seed_combinations: List[Tuple[List[int], List[int]]]):
    """
    Инициализация популяции на основе seed комбинаций
    Полезно для старта с известных хороших решений
    """
    logger.info(f"🌱 Инициализация популяции из {len(seed_combinations)} seed комбинаций")

    # Добавляем seed комбинации
    for field1, field2 in seed_combinations[:self.size]:
      chromosome = Chromosome(
        field1=sorted(field1),
        field2=sorted(field2),
        generation=0
      )
      self.chromosomes.append(chromosome)

    # Дополняем случайными если не хватает
    remaining = self.size - len(self.chromosomes)
    if remaining > 0:
      logger.info(f"Дополняем {remaining} случайными особями")
      for _ in range(remaining):
        # Можем мутировать существующие seed для разнообразия
        if self.chromosomes and random.random() < 0.5:
          parent = random.choice(self.chromosomes)
          field1 = self._mutate_genes(parent.field1.copy(), self.field1_max)
          field2 = self._mutate_genes(parent.field2.copy(), self.field2_max)
        else:
          field1 = sorted(random.sample(range(1, self.field1_max + 1), self.field1_size))
          field2 = sorted(random.sample(range(1, self.field2_max + 1), self.field2_size))

        chromosome = Chromosome(
          field1=field1,
          field2=field2,
          generation=0
        )
        self.chromosomes.append(chromosome)

    # Обрезаем если слишком много
    self.chromosomes = self.chromosomes[:self.size]

  def _mutate_genes(self, genes: List[int], max_value: int) -> List[int]:
    """Вспомогательная функция для мутации генов"""
    if random.random() < 0.5 and len(genes) > 0:
      # Заменяем один ген
      idx = random.randint(0, len(genes) - 1)
      available = set(range(1, max_value + 1)) - set(genes)
      if available:
        genes[idx] = random.choice(list(available))
    return sorted(genes)

  def evaluate_fitness(self, fitness_function):
    """
    Оценка приспособленности всех особей в популяции

    Args:
        fitness_function: Функция вида (field1, field2) -> float
    """
    logger.info(f"📊 Оценка fitness для поколения {self.generation}")

    evaluated = 0
    cached = 0

    for chromosome in self.chromosomes:
      # Проверяем кэш
      cache_key = chromosome.to_tuple()
      if cache_key in self._fitness_cache:
        chromosome.fitness = self._fitness_cache[cache_key]
        cached += 1
      else:
        # Вычисляем fitness
        try:
          fitness_value = fitness_function(chromosome.field1, chromosome.field2)
          chromosome.fitness = fitness_value
          self._fitness_cache[cache_key] = fitness_value
          evaluated += 1
        except Exception as e:
          logger.warning(f"Ошибка оценки fitness: {e}")
          chromosome.fitness = 0.0

    # Обновляем лучшую особь
    best_current = max(self.chromosomes, key=lambda c: c.fitness)
    if self.best_ever is None or best_current.fitness > self.best_ever.fitness:
      self.best_ever = best_current.copy()
      logger.info(f"🏆 Новый рекорд fitness: {self.best_ever.fitness:.4f}")

    logger.info(f"✅ Оценено: {evaluated} новых, {cached} из кэша")

    # Обновляем адаптивные параметры
    if self.adaptive_rates:
      self._update_adaptive_rates()

  def _update_adaptive_rates(self):
    """Адаптивная настройка коэффициентов мутации и кроссовера"""
    diversity = self.calculate_diversity()

    # Если разнообразие низкое - увеличиваем мутацию
    if diversity < self.diversity_threshold:
      self.current_mutation_rate = min(0.3, self.current_mutation_rate * 1.2)
      self.current_crossover_rate = max(0.6, self.current_crossover_rate * 0.95)
      logger.info(f"📈 Низкое разнообразие ({diversity:.3f}), увеличиваем мутацию до {self.current_mutation_rate:.3f}")
    else:
      # Постепенно снижаем мутацию для стабилизации
      self.current_mutation_rate = max(0.05, self.current_mutation_rate * 0.98)
      self.current_crossover_rate = min(0.9, self.current_crossover_rate * 1.01)

  def select_parents(self, tournament_size: int = 3) -> Tuple[Chromosome, Chromosome]:
    """
    Турнирная селекция родителей

    Args:
        tournament_size: Размер турнира

    Returns:
        Пара родителей
    """

    def tournament_select() -> Chromosome:
      """Один турнир"""
      tournament = random.sample(self.chromosomes, min(tournament_size, len(self.chromosomes)))
      return max(tournament, key=lambda c: c.fitness)

    parent1 = tournament_select()
    parent2 = tournament_select()

    # Гарантируем что родители разные
    attempts = 0
    while parent1.chromosome_id == parent2.chromosome_id and attempts < 10:
      parent2 = tournament_select()
      attempts += 1

    return parent1, parent2

  def select_elite(self) -> List[Chromosome]:
    """Отбор элитных особей"""
    sorted_pop = sorted(self.chromosomes, key=lambda c: c.fitness, reverse=True)
    elite = sorted_pop[:self.elite_size]

    # Логируем элиту
    logger.info(f"👑 Элита поколения {self.generation}: "
                f"лучший fitness={elite[0].fitness:.4f}, "
                f"худший в элите={elite[-1].fitness:.4f}")

    return [c.copy() for c in elite]  # Возвращаем копии

  def calculate_diversity(self) -> float:
    """
    Расчет индекса генетического разнообразия популяции

    Returns:
        Значение от 0 (все одинаковые) до 1 (максимальное разнообразие)
    """
    if self.generation == self._last_diversity_gen and self._diversity_cache is not None:
      return self._diversity_cache

    if len(self.chromosomes) < 2:
      return 0.0

    # Считаем уникальные комбинации
    unique_combos = set()
    for chromosome in self.chromosomes:
      unique_combos.add(chromosome.to_tuple())

    # Базовое разнообразие
    uniqueness_ratio = len(unique_combos) / len(self.chromosomes)

    # Среднее попарное расстояние (выборочно для скорости)
    sample_size = min(20, len(self.chromosomes))
    sample = random.sample(self.chromosomes, sample_size)

    distances = []
    for i in range(len(sample)):
      for j in range(i + 1, len(sample)):
        distances.append(sample[i].distance_to(sample[j]))

    avg_distance = np.mean(distances) if distances else 0

    # Комбинированный индекс
    diversity = uniqueness_ratio * 0.6 + avg_distance * 0.4

    # Кэшируем результат
    self._diversity_cache = diversity
    self._last_diversity_gen = self.generation

    return diversity

  def get_statistics(self) -> PopulationStats:
    """Получение статистики текущей популяции"""
    if not self.chromosomes:
      return PopulationStats(
        generation=self.generation,
        size=0,
        avg_fitness=0,
        max_fitness=0,
        min_fitness=0,
        std_fitness=0,
        diversity_index=0,
        elite_percentage=0,
        mutation_rate=self.current_mutation_rate,
        crossover_rate=self.current_crossover_rate,
        convergence_rate=0
      )

    fitness_values = [c.fitness for c in self.chromosomes]

    # Рассчитываем скорость сходимости
    convergence_rate = 0.0
    if len(self.evolution_history) > 1:
      prev_avg = self.evolution_history[-1].avg_fitness
      curr_avg = np.mean(fitness_values)
      if prev_avg > 0:
        convergence_rate = (curr_avg - prev_avg) / prev_avg

    stats = PopulationStats(
      generation=self.generation,
      size=len(self.chromosomes),
      avg_fitness=np.mean(fitness_values),
      max_fitness=np.max(fitness_values),
      min_fitness=np.min(fitness_values),
      std_fitness=np.std(fitness_values),
      diversity_index=self.calculate_diversity(),
      elite_percentage=(self.elite_size / self.size) * 100,
      mutation_rate=self.current_mutation_rate,
      crossover_rate=self.current_crossover_rate,
      convergence_rate=convergence_rate
    )

    self.evolution_history.append(stats)
    return stats

  def get_best_chromosomes(self, n: int = 10) -> List[Chromosome]:
    """Получение n лучших хромосом"""
    sorted_pop = sorted(self.chromosomes, key=lambda c: c.fitness, reverse=True)
    return sorted_pop[:n]

  def save_to_file(self, filepath: str):
    """Сохранение популяции в файл"""
    data = {
      'generation': self.generation,
      'size': self.size,
      'lottery_config': self.lottery_config,
      'chromosomes': [c.to_dict() for c in self.chromosomes],
      'best_ever': self.best_ever.to_dict() if self.best_ever else None,
      'evolution_history': [s.to_dict() for s in self.evolution_history],
      'timestamp': datetime.now().isoformat()
    }

    with open(filepath, 'w') as f:
      json.dump(data, f, indent=2)

    logger.info(f"💾 Популяция сохранена в {filepath}")

  @classmethod
  def load_from_file(cls, filepath: str, lottery_config: Dict) -> 'Population':
    """Загрузка популяции из файла"""
    with open(filepath, 'r') as f:
      data = json.load(f)

    pop = cls(
      size=data['size'],
      lottery_config=lottery_config
    )

    pop.generation = data['generation']

    # Восстанавливаем хромосомы
    for c_data in data['chromosomes']:
      chromosome = Chromosome(
        field1=c_data['field1'],
        field2=c_data['field2'],
        fitness=c_data['fitness'],
        generation=c_data['generation']
      )
      pop.chromosomes.append(chromosome)

    # Восстанавливаем лучшую особь
    if data['best_ever']:
      pop.best_ever = Chromosome(
        field1=data['best_ever']['field1'],
        field2=data['best_ever']['field2'],
        fitness=data['best_ever']['fitness'],
        generation=data['best_ever']['generation']
      )

    logger.info(f"📂 Популяция загружена из {filepath}, поколение {pop.generation}")
    return pop

  def clear_cache(self):
    """Очистка кэшей"""
    self._fitness_cache.clear()
    self._diversity_cache = None
    self._last_diversity_gen = -1
    logger.info("🧹 Кэш популяции очищен")