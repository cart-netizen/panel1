"""
Генетические операторы: кроссовер и мутация
Продвинутые операторы для эффективной эволюции
"""

import random
import numpy as np
from typing import List, Tuple, Dict, Optional
from backend.app.core.genetic.population import Chromosome
import logging

logger = logging.getLogger(__name__)


class GeneticOperators:
  """
  Набор генетических операторов для эволюции популяции
  Включает различные виды кроссовера и мутации
  """

  def __init__(self, lottery_config: Dict):
    """
    Args:
        lottery_config: Конфигурация лотереи
    """
    self.lottery_config = lottery_config
    self.field1_size = lottery_config['field1_size']
    self.field2_size = lottery_config['field2_size']
    self.field1_max = lottery_config['field1_max']
    self.field2_max = lottery_config['field2_max']

    # Статистика использования операторов
    self.operator_stats = {
      'crossover': {'uniform': 0, 'single_point': 0, 'two_point': 0, 'arithmetic': 0},
      'mutation': {'swap': 0, 'replace': 0, 'inversion': 0, 'scramble': 0}
    }

    logger.info(f"✅ Генетические операторы инициализированы для лотереи "
                f"{self.field1_size}x{self.field1_max} + {self.field2_size}x{self.field2_max}")

  # ============== ОПЕРАТОРЫ КРОССОВЕРА ==============

  def crossover(self, parent1: Chromosome, parent2: Chromosome,
                method: str = 'auto') -> Tuple[Chromosome, Chromosome]:
    """
    Главная функция кроссовера

    Args:
        parent1: Первый родитель
        parent2: Второй родитель
        method: Метод кроссовера ('uniform', 'single_point', 'two_point', 'arithmetic', 'auto')

    Returns:
        Два потомка
    """
    if method == 'auto':
      # Автоматический выбор метода на основе разнообразия родителей
      distance = parent1.distance_to(parent2)
      if distance < 0.2:
        method = 'uniform'  # Для похожих родителей
      elif distance < 0.5:
        method = 'two_point'
      else:
        method = 'single_point'  # Для разных родителей

    if method == 'uniform':
      return self.uniform_crossover(parent1, parent2)
    elif method == 'single_point':
      return self.single_point_crossover(parent1, parent2)
    elif method == 'two_point':
      return self.two_point_crossover(parent1, parent2)
    elif method == 'arithmetic':
      return self.arithmetic_crossover(parent1, parent2)
    else:
      logger.warning(f"Неизвестный метод кроссовера: {method}, используем uniform")
      return self.uniform_crossover(parent1, parent2)

  def uniform_crossover(self, parent1: Chromosome, parent2: Chromosome) -> Tuple[Chromosome, Chromosome]:
    """
    Равномерный кроссовер - каждый ген выбирается случайно от одного из родителей
    """
    self.operator_stats['crossover']['uniform'] += 1

    # Создаем пулы генов
    pool1_f1 = set(parent1.field1) | set(parent2.field1)
    pool1_f2 = set(parent1.field2) | set(parent2.field2)

    # Генерируем потомков
    child1_f1 = self._select_unique_subset(pool1_f1, self.field1_size, self.field1_max)
    child1_f2 = self._select_unique_subset(pool1_f2, self.field2_size, self.field2_max)

    child2_f1 = self._select_unique_subset(pool1_f1, self.field1_size, self.field1_max)
    child2_f2 = self._select_unique_subset(pool1_f2, self.field2_size, self.field2_max)

    # Создаем хромосомы потомков
    child1 = Chromosome(
      field1=sorted(child1_f1),
      field2=sorted(child1_f2),
      generation=max(parent1.generation, parent2.generation) + 1,
      parents=(parent1.chromosome_id, parent2.chromosome_id)
    )

    child2 = Chromosome(
      field1=sorted(child2_f1),
      field2=sorted(child2_f2),
      generation=max(parent1.generation, parent2.generation) + 1,
      parents=(parent1.chromosome_id, parent2.chromosome_id)
    )

    return child1, child2

  def single_point_crossover(self, parent1: Chromosome, parent2: Chromosome) -> Tuple[Chromosome, Chromosome]:
    """
    Одноточечный кроссовер - обмен генами после случайной точки
    """
    self.operator_stats['crossover']['single_point'] += 1

    # Точки разреза для каждого поля
    cut1 = random.randint(1, self.field1_size - 1)
    cut2 = random.randint(1, self.field2_size - 1)

    # Кроссовер field1
    child1_f1_genes = parent1.field1[:cut1] + parent2.field1[cut1:]
    child2_f1_genes = parent2.field1[:cut1] + parent1.field1[cut1:]

    # Кроссовер field2
    child1_f2_genes = parent1.field2[:cut2] + parent2.field2[cut2:]
    child2_f2_genes = parent2.field2[:cut2] + parent1.field2[cut2:]

    # Исправляем дубликаты
    child1_f1 = self._fix_duplicates(child1_f1_genes, self.field1_max)
    child2_f1 = self._fix_duplicates(child2_f1_genes, self.field1_max)
    child1_f2 = self._fix_duplicates(child1_f2_genes, self.field2_max)
    child2_f2 = self._fix_duplicates(child2_f2_genes, self.field2_max)

    child1 = Chromosome(
      field1=sorted(child1_f1),
      field2=sorted(child1_f2),
      generation=max(parent1.generation, parent2.generation) + 1,
      parents=(parent1.chromosome_id, parent2.chromosome_id)
    )

    child2 = Chromosome(
      field1=sorted(child2_f1),
      field2=sorted(child2_f2),
      generation=max(parent1.generation, parent2.generation) + 1,
      parents=(parent1.chromosome_id, parent2.chromosome_id)
    )

    return child1, child2

  def two_point_crossover(self, parent1: Chromosome, parent2: Chromosome) -> Tuple[Chromosome, Chromosome]:
    """
    Двухточечный кроссовер - обмен сегментом между двумя точками
    """
    self.operator_stats['crossover']['two_point'] += 1

    # Две точки разреза для field1
    cuts1 = sorted(random.sample(range(1, self.field1_size), min(2, self.field1_size - 1)))
    if len(cuts1) == 1:
      cuts1.append(self.field1_size - 1)

    # Две точки разреза для field2
    cuts2 = sorted(random.sample(range(1, self.field2_size), min(2, self.field2_size - 1)))
    if len(cuts2) == 1:
      cuts2.append(self.field2_size - 1)

    # Кроссовер field1
    child1_f1_genes = (parent1.field1[:cuts1[0]] +
                       parent2.field1[cuts1[0]:cuts1[1]] +
                       parent1.field1[cuts1[1]:])
    child2_f1_genes = (parent2.field1[:cuts1[0]] +
                       parent1.field1[cuts1[0]:cuts1[1]] +
                       parent2.field1[cuts1[1]:])

    # Кроссовер field2
    child1_f2_genes = (parent1.field2[:cuts2[0]] +
                       parent2.field2[cuts2[0]:cuts2[1]] +
                       parent1.field2[cuts2[1]:])
    child2_f2_genes = (parent2.field2[:cuts2[0]] +
                       parent1.field2[cuts2[0]:cuts2[1]] +
                       parent2.field2[cuts2[1]:])

    # Исправляем дубликаты
    child1_f1 = self._fix_duplicates(child1_f1_genes, self.field1_max)
    child2_f1 = self._fix_duplicates(child2_f1_genes, self.field1_max)
    child1_f2 = self._fix_duplicates(child1_f2_genes, self.field2_max)
    child2_f2 = self._fix_duplicates(child2_f2_genes, self.field2_max)

    child1 = Chromosome(
      field1=sorted(child1_f1),
      field2=sorted(child1_f2),
      generation=max(parent1.generation, parent2.generation) + 1,
      parents=(parent1.chromosome_id, parent2.chromosome_id)
    )

    child2 = Chromosome(
      field1=sorted(child2_f1),
      field2=sorted(child2_f2),
      generation=max(parent1.generation, parent2.generation) + 1,
      parents=(parent1.chromosome_id, parent2.chromosome_id)
    )

    return child1, child2

  def arithmetic_crossover(self, parent1: Chromosome, parent2: Chromosome) -> Tuple[Chromosome, Chromosome]:
    """
    Арифметический кроссовер - взвешенная комбинация генов родителей
    Подходит для числовых представлений
    """
    self.operator_stats['crossover']['arithmetic'] += 1

    # Веса для комбинирования
    alpha = random.random()

    # Объединяем гены с весами (выбираем с вероятностью alpha)
    child1_f1 = []
    child2_f1 = []

    # Для field1
    pool_f1 = list(set(parent1.field1) | set(parent2.field1))
    for num in pool_f1:
      in_p1 = num in parent1.field1
      in_p2 = num in parent2.field1

      if in_p1 and in_p2:
        # Число есть у обоих - выбираем с вероятностью
        if random.random() < alpha:
          child1_f1.append(num)
        if random.random() < (1 - alpha):
          child2_f1.append(num)
      elif in_p1:
        if random.random() < alpha:
          child1_f1.append(num)
        else:
          child2_f1.append(num)
      else:  # in_p2
        if random.random() < (1 - alpha):
          child1_f1.append(num)
        else:
          child2_f1.append(num)

    # Дополняем до нужного размера
    child1_f1 = self._ensure_size(child1_f1, self.field1_size, self.field1_max)
    child2_f1 = self._ensure_size(child2_f1, self.field1_size, self.field1_max)

    # Аналогично для field2
    child1_f2 = []
    child2_f2 = []

    pool_f2 = list(set(parent1.field2) | set(parent2.field2))
    for num in pool_f2:
      in_p1 = num in parent1.field2
      in_p2 = num in parent2.field2

      if in_p1 and in_p2:
        if random.random() < alpha:
          child1_f2.append(num)
        if random.random() < (1 - alpha):
          child2_f2.append(num)
      elif in_p1:
        if random.random() < alpha:
          child1_f2.append(num)
        else:
          child2_f2.append(num)
      else:
        if random.random() < (1 - alpha):
          child1_f2.append(num)
        else:
          child2_f2.append(num)

    child1_f2 = self._ensure_size(child1_f2, self.field2_size, self.field2_max)
    child2_f2 = self._ensure_size(child2_f2, self.field2_size, self.field2_max)

    child1 = Chromosome(
      field1=sorted(child1_f1),
      field2=sorted(child1_f2),
      generation=max(parent1.generation, parent2.generation) + 1,
      parents=(parent1.chromosome_id, parent2.chromosome_id)
    )

    child2 = Chromosome(
      field1=sorted(child2_f1),
      field2=sorted(child2_f2),
      generation=max(parent1.generation, parent2.generation) + 1,
      parents=(parent1.chromosome_id, parent2.chromosome_id)
    )

    return child1, child2

  # ============== ОПЕРАТОРЫ МУТАЦИИ ==============

  def mutate(self, chromosome: Chromosome, mutation_rate: float = 0.1,
             method: str = 'auto') -> Chromosome:
    """
    Главная функция мутации

    Args:
        chromosome: Хромосома для мутации
        mutation_rate: Вероятность мутации
        method: Метод мутации ('swap', 'replace', 'inversion', 'scramble', 'auto')

    Returns:
        Мутированная хромосома (или оригинал если мутация не произошла)
    """
    if random.random() > mutation_rate:
      return chromosome  # Мутация не происходит

    if method == 'auto':
      # Автоматический выбор метода
      methods = ['swap', 'replace', 'inversion', 'scramble']
      weights = [0.3, 0.4, 0.2, 0.1]  # Веса для выбора
      method = random.choices(methods, weights=weights)[0]

    # Создаем копию для мутации
    mutated = chromosome.copy()

    if method == 'swap':
      mutated = self.swap_mutation(mutated)
    elif method == 'replace':
      mutated = self.replace_mutation(mutated)
    elif method == 'inversion':
      mutated = self.inversion_mutation(mutated)
    elif method == 'scramble':
      mutated = self.scramble_mutation(mutated)
    else:
      logger.warning(f"Неизвестный метод мутации: {method}, используем replace")
      mutated = self.replace_mutation(mutated)

    # Записываем историю мутации
    mutated.mutation_history.append(f"{method}@gen{mutated.generation}")

    return mutated

  def swap_mutation(self, chromosome: Chromosome) -> Chromosome:
    """
    Мутация обмена - меняем местами два гена
    """
    self.operator_stats['mutation']['swap'] += 1

    mutated = chromosome.copy()

    # Мутация field1
    if len(mutated.field1) >= 2 and random.random() < 0.5:
      idx1, idx2 = random.sample(range(len(mutated.field1)), 2)
      mutated.field1[idx1], mutated.field1[idx2] = mutated.field1[idx2], mutated.field1[idx1]

    # Мутация field2
    if len(mutated.field2) >= 2 and random.random() < 0.5:
      idx1, idx2 = random.sample(range(len(mutated.field2)), 2)
      mutated.field2[idx1], mutated.field2[idx2] = mutated.field2[idx2], mutated.field2[idx1]

    return mutated

  def replace_mutation(self, chromosome: Chromosome) -> Chromosome:
    """
    Мутация замены - заменяем один или несколько генов новыми
    """
    self.operator_stats['mutation']['replace'] += 1

    mutated = chromosome.copy()

    # Мутация field1
    if random.random() < 0.5:
      num_replacements = random.randint(1, max(1, self.field1_size // 3))
      for _ in range(num_replacements):
        idx = random.randint(0, len(mutated.field1) - 1)
        available = set(range(1, self.field1_max + 1)) - set(mutated.field1)
        if available:
          mutated.field1[idx] = random.choice(list(available))
      mutated.field1 = sorted(mutated.field1)

    # Мутация field2
    if random.random() < 0.5:
      num_replacements = random.randint(1, max(1, self.field2_size // 3))
      for _ in range(num_replacements):
        idx = random.randint(0, len(mutated.field2) - 1)
        available = set(range(1, self.field2_max + 1)) - set(mutated.field2)
        if available:
          mutated.field2[idx] = random.choice(list(available))
      mutated.field2 = sorted(mutated.field2)

    return mutated

  def inversion_mutation(self, chromosome: Chromosome) -> Chromosome:
    """
    Мутация инверсии - переворачиваем подпоследовательность генов
    """
    self.operator_stats['mutation']['inversion'] += 1

    mutated = chromosome.copy()

    # Мутация field1
    if len(mutated.field1) >= 3 and random.random() < 0.5:
      start = random.randint(0, len(mutated.field1) - 2)
      end = random.randint(start + 1, len(mutated.field1) - 1)
      mutated.field1[start:end + 1] = reversed(mutated.field1[start:end + 1])
      mutated.field1 = sorted(mutated.field1)  # Сохраняем порядок

    # Мутация field2
    if len(mutated.field2) >= 3 and random.random() < 0.5:
      start = random.randint(0, len(mutated.field2) - 2)
      end = random.randint(start + 1, len(mutated.field2) - 1)
      mutated.field2[start:end + 1] = reversed(mutated.field2[start:end + 1])
      mutated.field2 = sorted(mutated.field2)

    return mutated

  def scramble_mutation(self, chromosome: Chromosome) -> Chromosome:
    """
    Мутация перемешивания - случайно перемешиваем часть генов
    """
    self.operator_stats['mutation']['scramble'] += 1

    mutated = chromosome.copy()

    # Мутация field1 - полная замена на случайную комбинацию
    if random.random() < 0.3:  # Низкая вероятность для радикальной мутации
      mutated.field1 = sorted(random.sample(range(1, self.field1_max + 1), self.field1_size))

    # Мутация field2
    if random.random() < 0.3:
      mutated.field2 = sorted(random.sample(range(1, self.field2_max + 1), self.field2_size))

    return mutated

  # ============== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==============

  def _select_unique_subset(self, pool: set, size: int, max_value: int) -> List[int]:
    """Выбор уникального подмножества из пула"""
    pool_list = list(pool)

    if len(pool_list) >= size:
      return random.sample(pool_list, size)
    else:
      # Дополняем случайными числами
      result = pool_list.copy()
      available = set(range(1, max_value + 1)) - pool
      needed = size - len(result)
      if available and needed > 0:
        additional = random.sample(list(available), min(needed, len(available)))
        result.extend(additional)

      # Если все еще не хватает
      while len(result) < size:
        result.append(random.randint(1, max_value))

      return result[:size]

  def _fix_duplicates(self, genes: List[int], max_value: int) -> List[int]:
    """Исправление дубликатов в списке генов"""
    unique_genes = []
    seen = set()

    for gene in genes:
      if gene not in seen:
        unique_genes.append(gene)
        seen.add(gene)

    # Дополняем если не хватает
    while len(unique_genes) < len(genes):
      available = set(range(1, max_value + 1)) - seen
      if available:
        new_gene = random.choice(list(available))
        unique_genes.append(new_gene)
        seen.add(new_gene)
      else:
        break

    return unique_genes

  def _ensure_size(self, genes: List[int], target_size: int, max_value: int) -> List[int]:
    """Гарантирует нужный размер списка генов"""
    genes = list(set(genes))  # Убираем дубликаты

    if len(genes) > target_size:
      # Обрезаем
      return random.sample(genes, target_size)
    elif len(genes) < target_size:
      # Дополняем
      available = set(range(1, max_value + 1)) - set(genes)
      needed = target_size - len(genes)

      if available:
        additional = random.sample(list(available), min(needed, len(available)))
        genes.extend(additional)

      # Если все еще не хватает (не должно происходить при правильной конфигурации)
      while len(genes) < target_size:
        genes.append(random.randint(1, max_value))

    return genes

  def get_statistics(self) -> Dict:
    """Получение статистики использования операторов"""
    return {
      'crossover': self.operator_stats['crossover'].copy(),
      'mutation': self.operator_stats['mutation'].copy(),
      'total_crossovers': sum(self.operator_stats['crossover'].values()),
      'total_mutations': sum(self.operator_stats['mutation'].values())
    }

  def reset_statistics(self):
    """Сброс статистики"""
    for key in self.operator_stats['crossover']:
      self.operator_stats['crossover'][key] = 0
    for key in self.operator_stats['mutation']:
      self.operator_stats['mutation'][key] = 0
    logger.info("📊 Статистика операторов сброшена")