"""
Патч для добавления улучшенной системы наград в LotteryEnvironment
Сохраните этот код в backend/app/core/rl/environment_patch.py
и выполните его для применения патча
"""


def patch_lottery_environment():
  """Применяет патч к классу LotteryEnvironment"""

  from backend.app.core.rl.environment import LotteryEnvironment
  import logging

  logger = logging.getLogger(__name__)

  # Сохраняем оригинальный __init__
  original_init = LotteryEnvironment.__init__

  def patched_init(self, df_history, lottery_config, window_size=50):
    # Вызываем оригинальный init
    original_init(self, df_history, lottery_config, window_size)

    # Добавляем инициализацию улучшенной системы наград
    try:
      from backend.app.core.rl.improved_rewards import ImprovedRewardCalculator, CuriosityDrivenBonus
      self.reward_calculator = ImprovedRewardCalculator(lottery_config)
      self.curiosity_module = CuriosityDrivenBonus(state_dim=10)
      logger.info("✅ Улучшенная система наград инициализирована")
    except ImportError as e:
      logger.warning(f"Не удалось загрузить улучшенную систему наград: {e}")
      self.reward_calculator = None
      self.curiosity_module = None
    except Exception as e:
      logger.error(f"Ошибка при инициализации системы наград: {e}")
      self.reward_calculator = None
      self.curiosity_module = None

  # Заменяем метод __init__
  LotteryEnvironment.__init__ = patched_init

  # Сохраняем оригинальный _calculate_reward
  original_calculate_reward = LotteryEnvironment._calculate_reward

  def patched_calculate_reward(self, pred_field1, pred_field2, actual_field1, actual_field2):
    # Если есть улучшенный калькулятор - используем его
    if hasattr(self, 'reward_calculator') and self.reward_calculator is not None:
      try:
        # Получаем дополнительные признаки
        state_features = {}
        if self.current_state:
          state_features = self.current_state.to_dict()

          # Пытаемся добавить hot/cold числа
          try:
            window_df = self.df_history.iloc[
                        max(0, self.current_position - self.window_size):self.current_position
                        ]
            from backend.app.core.combination_generator import _analyze_hot_cold_numbers_for_generator
            hot_f1, cold_f1 = _analyze_hot_cold_numbers_for_generator(window_df, 1)
            state_features['hot_numbers'] = hot_f1[:10] if isinstance(hot_f1, list) else []
            state_features['cold_numbers'] = cold_f1[:10] if isinstance(cold_f1, list) else []
          except:
            pass

        # Расчет награды
        reward, info = self.reward_calculator.calculate_reward(
          pred_field1, pred_field2,
          actual_field1, actual_field2,
          state_features
        )

        # Curiosity bonus
        if hasattr(self, 'curiosity_module') and self.curiosity_module and self.current_state:
          try:
            if self.current_position < len(self.df_history) - 2:
              next_state = self._compute_state(self.current_position + 1)
              curiosity_reward = self.curiosity_module.calculate_curiosity_reward(
                self.current_state.to_vector(),
                next_state.to_vector(),
                (pred_field1, pred_field2)
              )
              reward += curiosity_reward
          except:
            pass

        return reward

      except Exception as e:
        logger.debug(f"Ошибка в улучшенной системе наград, используем базовую: {e}")
        # Fallback на оригинальный метод
        return original_calculate_reward(self, pred_field1, pred_field2, actual_field1, actual_field2)
    else:
      # Используем оригинальный метод
      return original_calculate_reward(self, pred_field1, pred_field2, actual_field1, actual_field2)

  # Заменяем метод _calculate_reward
  LotteryEnvironment._calculate_reward = patched_calculate_reward

  logger.info("✅ LotteryEnvironment успешно пропатчен")
  return True


# Автоматически применяем патч при импорте
if __name__ != "__main__":
  try:
    patch_lottery_environment()
  except Exception as e:
    print(f"Не удалось применить патч: {e}")