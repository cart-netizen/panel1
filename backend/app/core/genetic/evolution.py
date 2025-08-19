"""
Главный эволюционный движок генетического алгоритма
Управляет полным циклом эволюции популяции
"""

import time
import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import asyncio
import json

from backend.app.core.genetic.population import Population, Chromosome, PopulationStats
from backend.app.core.genetic.operators import GeneticOperators
from backend.app.core.genetic.fitness import FitnessEvaluator, MultiObjectiveFitness

logger = logging.getLogger(__name__)


@dataclass
class EvolutionConfig:
  """Конфигурация эволюционного процесса"""
  population_size: int = 100
  generations: int = 50
  elite_size: int = 10
  mutation_rate: float = 0.1
  crossover_rate: float = 0.8
  tournament_size: int = 3
  diversity_threshold: float = 0.3
  adaptive_rates: bool = True
  early_stopping_patience: int = 10
  target_fitness: Optional[float] = None
  multi_objective: bool = False
  parallel_evaluation: bool = True
  save_checkpoints: bool = True
  checkpoint_interval: int = 10


@dataclass
class EvolutionResult:
  """Результаты эволюции"""
  best_chromosome: Chromosome
  final_population: List[Chromosome]
  statistics: List[PopulationStats]
  total_time: float
  generations_completed: int
  converged: bool
  convergence_generation: Optional[int]
  best_fitness_history: List[float]
  diversity_history: List[float]
  operator_statistics: Dict

  def to_dict(self) -> Dict:
    """Сериализация результатов"""
    return {
      'best_solution': {
        'field1': self.best_chromosome.field1,
        'field2': self.best_chromosome.field2,
        'fitness': self.best_chromosome.fitness,
        'generation': self.best_chromosome.generation
      },
      'top_10_solutions': [
        {
          'field1': c.field1,
          'field2': c.field2,
          'fitness': c.fitness
        }
        for c in sorted(self.final_population, key=lambda x: x.fitness, reverse=True)[:10]
      ],
      'total_time_seconds': self.total_time,
      'generations': self.generations_completed,
      'converged': self.converged,
      'convergence_generation': self.convergence_generation,
      'final_avg_fitness': np.mean([c.fitness for c in self.final_population]),
      'final_max_fitness': max(c.fitness for c in self.final_population),
      'final_diversity': self.diversity_history[-1] if self.diversity_history else 0
    }


class GeneticEvolution:
  """
  Главный класс управления генетической эволюцией
  Профессиональная реализация с адаптивными параметрами
  """

  def __init__(self,
               df_history: pd.DataFrame,
               lottery_config: Dict,
               config: EvolutionConfig = None):
    """
    Args:
        df_history: История тиражей
        lottery_config: Конфигурация лотереи
        config: Конфигурация эволюции
    """
    self.df_history = df_history
    self.lottery_config = lottery_config
    self.config = config or EvolutionConfig()

    # Инициализация компонентов
    self.population = Population(
      size=self.config.population_size,
      lottery_config=lottery_config,
      elite_size=self.config.elite_size,
      diversity_threshold=self.config.diversity_threshold,
      adaptive_rates=self.config.adaptive_rates
    )

    self.operators = GeneticOperators(lottery_config)

    # Выбор fitness функции
    if self.config.multi_objective:
      self.fitness_evaluator = MultiObjectiveFitness(df_history, lottery_config)
    else:
      self.fitness_evaluator = FitnessEvaluator(df_history, lottery_config)

    # История эволюции
    self.best_fitness_history = []
    self.diversity_history = []
    self.stagnation_counter = 0
    self.best_fitness_ever = -float('inf')

    # Флаги состояния
    self.is_running = False
    self.should_stop = False

    logger.info(f"✅ GeneticEvolution инициализирован: "
                f"популяция={self.config.population_size}, "
                f"поколения={self.config.generations}")

  def evolve(self, initial_population: Optional[List[Tuple[List[int], List[int]]]] = None) -> EvolutionResult:
    """
    Запуск полного цикла эволюции

    Args:
        initial_population: Начальная популяция (опционально)

    Returns:
        Результаты эволюции
    """
    start_time = time.time()
    self.is_running = True
    self.should_stop = False

    logger.info("🧬 ЗАПУСК ГЕНЕТИЧЕСКОЙ ЭВОЛЮЦИИ")
    logger.info(f"Конфигурация: {self.config}")

    try:
      # Инициализация популяции
      if initial_population:
        self.population.initialize_from_seeds(initial_population)
      else:
        self.population.initialize_random()

      # Начальная оценка
      self._evaluate_population()
      initial_stats = self.population.get_statistics()
      logger.info(f"📊 Начальная популяция: avg_fitness={initial_stats.avg_fitness:.2f}, "
                  f"max_fitness={initial_stats.max_fitness:.2f}")

      # Основной эволюционный цикл
      for generation in range(self.config.generations):
        if self.should_stop:
          logger.info("⛔ Эволюция остановлена пользователем")
          break

        logger.info(f"\n{'=' * 50}")
        logger.info(f"🧬 ПОКОЛЕНИЕ {generation + 1}/{self.config.generations}")

        # Выполняем один шаг эволюции
        self._evolution_step()

        # Статистика поколения
        stats = self.population.get_statistics()
        self.best_fitness_history.append(stats.max_fitness)
        self.diversity_history.append(stats.diversity_index)

        logger.info(f"📊 Статистика: avg={stats.avg_fitness:.2f}, "
                    f"max={stats.max_fitness:.2f}, "
                    f"diversity={stats.diversity_index:.3f}")

        # Проверка на улучшение
        if stats.max_fitness > self.best_fitness_ever:
          self.best_fitness_ever = stats.max_fitness
          self.stagnation_counter = 0
          logger.info(f"🎯 Новый рекорд fitness: {self.best_fitness_ever:.2f}")
        else:
          self.stagnation_counter += 1

        # Проверка критериев остановки
        if self._check_stopping_criteria(stats):
          logger.info(f"✅ Достигнут критерий остановки на поколении {generation + 1}")
          break

        # Сохранение чекпоинта
        if self.config.save_checkpoints and (generation + 1) % self.config.checkpoint_interval == 0:
          self._save_checkpoint(generation + 1)

        # Увеличиваем счетчик поколений
        self.population.generation += 1

      # Финальная оценка
      self._evaluate_population()

      # Сбор результатов
      result = self._collect_results(time.time() - start_time)

      logger.info(f"\n{'=' * 50}")
      logger.info(f"🏁 ЭВОЛЮЦИЯ ЗАВЕРШЕНА")
      logger.info(f"Лучший результат: fitness={result.best_chromosome.fitness:.2f}")
      logger.info(f"Время выполнения: {result.total_time:.2f} сек")

      return result

    except Exception as e:
      logger.error(f"❌ Ошибка эволюции: {e}")
      import traceback
      traceback.print_exc()
      raise
    finally:
      self.is_running = False

  def _evolution_step(self):
    """Один шаг эволюции"""

    # 1. Селекция элиты
    elite = self.population.select_elite()
    logger.info(f"👑 Отобрано {len(elite)} элитных особей")

    # 2. Создание нового поколения
    new_population = elite.copy()  # Элита переходит без изменений

    # 3. Заполнение оставшихся мест через кроссовер и мутацию
    while len(new_population) < self.population.size:
      # Выбор родителей
      if np.random.random() < self.config.crossover_rate:
        parent1, parent2 = self.population.select_parents(self.config.tournament_size)

        # Кроссовер
        child1, child2 = self.operators.crossover(parent1, parent2, method='auto')

        # Мутация
        child1 = self.operators.mutate(child1, self.population.current_mutation_rate)
        child2 = self.operators.mutate(child2, self.population.current_mutation_rate)

        new_population.append(child1)
        if len(new_population) < self.population.size:
          new_population.append(child2)
      else:
        # Только мутация существующей особи
        parent = self.population.select_parents(self.config.tournament_size)[0]
        child = self.operators.mutate(parent.copy(), self.population.current_mutation_rate * 1.5)
        new_population.append(child)

    # 4. Обрезаем до нужного размера
    new_population = new_population[:self.population.size]

    # 5. Обновляем популяцию
    self.population.chromosomes = new_population

    # 6. Оценка новой популяции
    self._evaluate_population()

    # 7. Инъекция разнообразия при необходимости
    if self.population.calculate_diversity() < self.config.diversity_threshold:
      self._inject_diversity()

  def _evaluate_population(self):
    """Оценка приспособленности всей популяции"""

    if self.config.parallel_evaluation:
      # Параллельная оценка для ускорения
      self._parallel_evaluate()
    else:
      # Последовательная оценка
      self.population.evaluate_fitness(
        lambda f1, f2: self.fitness_evaluator.evaluate(f1, f2)
      )

  def _parallel_evaluate(self):
    """Параллельная оценка fitness"""
    # Собираем комбинации для оценки
    combinations = [(c.field1, c.field2) for c in self.population.chromosomes]

    # Пакетная оценка
    fitness_values = self.fitness_evaluator.batch_evaluate(combinations)

    # Присваиваем значения
    for chromosome, fitness in zip(self.population.chromosomes, fitness_values):
      chromosome.fitness = fitness

    # Обновляем лучшую особь
    best_current = max(self.population.chromosomes, key=lambda c: c.fitness)
    if self.population.best_ever is None or best_current.fitness > self.population.best_ever.fitness:
      self.population.best_ever = best_current.copy()
      logger.info(f"🏆 Новый рекорд fitness: {self.population.best_ever.fitness:.4f}")

  def _inject_diversity(self):
    """Инъекция разнообразия в популяцию при стагнации"""
    logger.info("💉 Инъекция разнообразия в популяцию")

    # Заменяем 20% худших особей новыми случайными
    num_to_replace = self.population.size // 5
    sorted_pop = sorted(self.population.chromosomes, key=lambda c: c.fitness)

    for i in range(num_to_replace):
      # Генерируем новую случайную особь
      from backend.app.core.combination_generator import generate_random_combination
      f1, f2 = generate_random_combination()

      new_chromosome = Chromosome(
        field1=sorted(f1),
        field2=sorted(f2),
        generation=self.population.generation
      )

      # Заменяем худшую особь
      sorted_pop[i] = new_chromosome

    self.population.chromosomes = sorted_pop

    # Увеличиваем мутацию временно
    self.population.current_mutation_rate = min(0.3, self.population.current_mutation_rate * 1.5)

  def _check_stopping_criteria(self, stats: PopulationStats) -> bool:
    """Проверка критериев остановки"""

    # Достигнут целевой fitness
    if self.config.target_fitness and stats.max_fitness >= self.config.target_fitness:
      logger.info(f"✅ Достигнут целевой fitness: {stats.max_fitness:.2f}")
      return True

    # Стагнация
    if self.stagnation_counter >= self.config.early_stopping_patience:
      logger.info(f"⏹ Стагнация в течение {self.stagnation_counter} поколений")
      return True

    # Полная сходимость (все особи одинаковые)
    if stats.diversity_index < 0.01:
      logger.info("⏹ Полная сходимость популяции")
      return True

    return False

  def _save_checkpoint(self, generation: int):
    """Сохранение промежуточного состояния"""
    checkpoint_file = f"genetic_checkpoint_gen{generation}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    self.population.save_to_file(checkpoint_file)
    logger.info(f"💾 Чекпоинт сохранен: {checkpoint_file}")

  def _collect_results(self, total_time: float) -> EvolutionResult:
    """Сбор результатов эволюции"""

    # Определяем сходимость
    converged = False
    convergence_gen = None

    if len(self.best_fitness_history) > 10:
      # Проверяем последние 10 поколений
      recent_fitness = self.best_fitness_history[-10:]
      if max(recent_fitness) - min(recent_fitness) < 0.01:
        converged = True
        # Находим поколение сходимости
        for i in range(len(self.best_fitness_history) - 10):
          window = self.best_fitness_history[i:i + 10]
          if max(window) - min(window) < 0.01:
            convergence_gen = i
            break

    return EvolutionResult(
      best_chromosome=self.population.best_ever or self.population.chromosomes[0],
      final_population=self.population.chromosomes,
      statistics=self.population.evolution_history,
      total_time=total_time,
      generations_completed=self.population.generation,
      converged=converged,
      convergence_generation=convergence_gen,
      best_fitness_history=self.best_fitness_history,
      diversity_history=self.diversity_history,
      operator_statistics=self.operators.get_statistics()
    )

  async def evolve_async(self,
                         initial_population: Optional[List[Tuple[List[int], List[int]]]] = None) -> EvolutionResult:
    """Асинхронная версия эволюции"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self.evolve, initial_population)

  def stop_evolution(self):
    """Остановка эволюции"""
    self.should_stop = True
    logger.info("🛑 Запрошена остановка эволюции")

  def update_fitness_weights(self, new_weights: Dict[str, float]):
    """Обновление весов fitness функции"""
    self.fitness_evaluator.update_weights(new_weights)
    # Пересчитываем fitness популяции
    if self.population.chromosomes:
      self._evaluate_population()

  def get_current_statistics(self) -> Dict:
    """Получение текущей статистики"""
    if not self.population.chromosomes:
      return {}

    current_stats = self.population.get_statistics()

    return {
      'generation': self.population.generation,
      'population_size': len(self.population.chromosomes),
      'avg_fitness': current_stats.avg_fitness,
      'max_fitness': current_stats.max_fitness,
      'min_fitness': current_stats.min_fitness,
      'diversity': current_stats.diversity_index,
      'mutation_rate': self.population.current_mutation_rate,
      'crossover_rate': self.population.current_crossover_rate,
      'stagnation_counter': self.stagnation_counter,
      'best_solution': {
        'field1': self.population.best_ever.field1 if self.population.best_ever else [],
        'field2': self.population.best_ever.field2 if self.population.best_ever else [],
        'fitness': self.population.best_ever.fitness if self.population.best_ever else 0
      }
    }