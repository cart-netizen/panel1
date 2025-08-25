"""
Интеграция генетического алгоритма с системой генерации комбинаций
Профессиональный генератор на основе эволюции
"""

import logging
import time
from typing import List, Tuple, Dict, Optional
import pandas as pd
import numpy as np

from backend.app.core.genetic.evolution import GeneticEvolution, EvolutionConfig
from backend.app.core.genetic.population import Chromosome
from backend.app.core import data_manager
from backend.app.core.combination_generator import generate_random_combination

logger = logging.getLogger(__name__)


class GeneticCombinationGenerator:
    """
    Генератор комбинаций на основе генетического алгоритма
    Интегрируется с существующей системой генерации
    """
    
    def __init__(self):
        self.evolution_cache = {}
        self.last_evolution_result = None
        
    def generate_genetic_combinations(self, 
                                     df_history: pd.DataFrame,
                                     num_to_generate: int = 10,
                                     generations: int = 30,
                                     population_size: int = 50,
                                     use_cache: bool = True) -> List[Tuple[List[int], List[int], str]]:
        """
        Генерация комбинаций с помощью генетического алгоритма
        
        Args:
            df_history: История тиражей
            num_to_generate: Количество комбинаций для генерации
            generations: Количество поколений эволюции
            population_size: Размер популяции
            use_cache: Использовать кэшированные результаты
            
        Returns:
            Список кортежей (field1, field2, описание)
        """
        if df_history.empty or len(df_history) < 10:
            logger.warning("Недостаточно данных для генетического алгоритма")
            return [(f1, f2, "Случайная (мало данных)") 
                    for f1, f2 in [generate_random_combination() for _ in range(num_to_generate)]]
        
        logger.info(f"🧬 Запуск генетической генерации: {num_to_generate} комбинаций")
        start_time = time.time()
        
        # Получаем конфигурацию лотереи
        lottery_config = data_manager.get_current_config()
        
        # Проверяем кэш
        cache_key = f"{data_manager.CURRENT_LOTTERY}_{len(df_history)}_{generations}_{population_size}"
        
        if use_cache and cache_key in self.evolution_cache:
            logger.info("📦 Использование кэшированных результатов эволюции")
            evolution_result = self.evolution_cache[cache_key]
        else:
            # Настройка эволюции
            config = EvolutionConfig(
                population_size=population_size,
                generations=generations,
                elite_size=max(2, population_size // 10),
                mutation_rate=0.1,
                crossover_rate=0.8,
                tournament_size=3,
                diversity_threshold=0.3,
                adaptive_rates=True,
                early_stopping_patience=max(5, generations // 5),
                parallel_evaluation=True,
                save_checkpoints=False  # Отключаем для скорости
            )
            
            # Создаем эволюционный движок
            evolution = GeneticEvolution(df_history, lottery_config, config)
            
            # Инициализация с умными seed комбинациями
            initial_population = self._create_smart_initial_population(df_history, population_size)
            
            # Запускаем эволюцию
            logger.info(f"🚀 Запуск эволюции: {generations} поколений, популяция {population_size}")
            evolution_result = evolution.evolve(initial_population)
            
            # Сохраняем в кэш
            self.evolution_cache[cache_key] = evolution_result
            
            # Ограничиваем размер кэша
            if len(self.evolution_cache) > 10:
                oldest_key = list(self.evolution_cache.keys())[0]
                del self.evolution_cache[oldest_key]
        
        # Извлекаем лучшие решения
        top_chromosomes = sorted(evolution_result.final_population, 
                                key=lambda c: c.fitness, reverse=True)[:num_to_generate]
        
        # Форматируем результаты
        results = []
        for i, chromosome in enumerate(top_chromosomes):
            description = self._create_description(chromosome, i + 1, evolution_result)
            results.append((chromosome.field1, chromosome.field2, description))
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Генетическая генерация завершена за {elapsed:.2f}с")
        logger.info(f"📊 Лучший fitness: {evolution_result.best_chromosome.fitness:.2f}, "
                   f"поколений: {evolution_result.generations_completed}")
        
        # Сохраняем последний результат
        self.last_evolution_result = evolution_result
        
        return results
    
    def _create_smart_initial_population(self, df_history: pd.DataFrame, 
                                        population_size: int) -> List[Tuple[List[int], List[int]]]:
        """Создание умной начальной популяции"""
        initial_pop = []
        
        # Анализируем горячие/холодные числа
        from backend.app.core.combination_generator import _analyze_hot_cold_numbers_for_generator
        
        hot_f1, cold_f1 = _analyze_hot_cold_numbers_for_generator(df_history, 1)
        hot_f2, cold_f2 = _analyze_hot_cold_numbers_for_generator(df_history, 2)
        
        config = data_manager.get_current_config()
        
        # Стратегии для seed популяции
        strategies = [
            ('hot', hot_f1[:15], hot_f2[:15]),
            ('cold', cold_f1[:15], cold_f2[:15]),
            ('mixed', hot_f1[:8] + cold_f1[:8], hot_f2[:8] + cold_f2[:8])
        ]
        
        # Генерируем seed комбинации
        for _ in range(min(population_size // 3, 20)):
            for strategy_name, pool_f1, pool_f2 in strategies:
                if len(pool_f1) >= config['field1_size'] and len(pool_f2) >= config['field2_size']:
                    import random
                    f1 = sorted(random.sample(pool_f1, config['field1_size']))
                    f2 = sorted(random.sample(pool_f2, config['field2_size']))
                    initial_pop.append((f1, f2))
                    
                    if len(initial_pop) >= population_size // 2:
                        break
            
            if len(initial_pop) >= population_size // 2:
                break
        
        logger.info(f"🌱 Создано {len(initial_pop)} seed комбинаций")
        return initial_pop
    
    def _create_description(self, chromosome: Chromosome, rank: int, 
                           evolution_result) -> str:
        """Создание описания для хромосомы"""
        parts = [f"Genetic #{rank}"]
        
        # Добавляем fitness
        parts.append(f"fit:{chromosome.fitness:.1f}")
        
        # Добавляем поколение
        parts.append(f"gen:{chromosome.generation}")
        
        # Добавляем информацию о родителях
        if chromosome.parents:
            parts.append("evolved")
        else:
            parts.append("seed")
        
        # Добавляем информацию о мутациях
        if chromosome.mutation_history:
            last_mutation = chromosome.mutation_history[-1].split('@')[0]
            parts.append(f"mut:{last_mutation}")
        
        # Если это лучшее решение
        if chromosome.chromosome_id == evolution_result.best_chromosome.chromosome_id:
            parts.insert(0, "🏆")
        
        return " ".join(parts)
    
    def get_evolution_statistics(self) -> Optional[Dict]:
        """Получение статистики последней эволюции"""
        if not self.last_evolution_result:
            return None
        
        result = self.last_evolution_result
        
        return {
            'best_fitness': result.best_chromosome.fitness,
            'avg_final_fitness': np.mean([c.fitness for c in result.final_population]),
            'generations_completed': result.generations_completed,
            'converged': result.converged,
            'convergence_generation': result.convergence_generation,
            'total_time': result.total_time,
            'final_diversity': result.diversity_history[-1] if result.diversity_history else 0,
            'best_solution': {
                'field1': result.best_chromosome.field1,
                'field2': result.best_chromosome.field2
            },
            'fitness_progression': result.best_fitness_history[-10:] if len(result.best_fitness_history) > 10 else result.best_fitness_history
        }


# Глобальный экземпляр генератора
GENETIC_GENERATOR = GeneticCombinationGenerator()


def generate_genetic_evolved_combinations(df_history: pd.DataFrame,
                                         num_to_generate: int = 10,
                                         **kwargs) -> List[Tuple[List[int], List[int], str]]:
    """
    Функция-обертка для интеграции с combination_generator.py
    
    Args:
        df_history: История тиражей
        num_to_generate: Количество комбинаций
        **kwargs: Дополнительные параметры (generations, population_size)
        
    Returns:
        Список комбинаций с описаниями
    """
    return GENETIC_GENERATOR.generate_genetic_combinations(
        df_history,
        num_to_generate,
        generations=kwargs.get('generations', 30),
        population_size=kwargs.get('population_size', 50),
        use_cache=kwargs.get('use_cache', True)
    )


def get_genetic_prediction(df_history: pd.DataFrame) -> Tuple[Optional[List[int]], Optional[List[int]]]:
    """
    Получить лучшее генетическое предсказание
    
    Returns:
        Tuple (field1, field2) или (None, None)
    """
    if df_history.empty or len(df_history) < 10:
        return None, None
    
    try:
        # Быстрая эволюция для предсказания
        results = GENETIC_GENERATOR.generate_genetic_combinations(
            df_history,
            num_to_generate=1,
            generations=20,  # Меньше поколений для скорости
            population_size=30,  # Меньшая популяция
            use_cache=True
        )
        
        if results:
            field1, field2, _ = results[0]
            return field1, field2
        
    except Exception as e:
        logger.error(f"Ошибка генетического предсказания: {e}")
    
    return None, None
