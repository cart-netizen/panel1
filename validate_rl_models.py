from backend.app.core.rl.validation_utils import *
from backend.app.core.rl.rl_generator import GLOBAL_RL_MANAGER
import backend.app.core.data_manager as data_manager


def main():
  for lottery_type in data_manager.LOTTERY_CONFIGS.keys():
    df = data_manager.fetch_draws_from_db()
    config = data_manager.LOTTERY_CONFIGS[lottery_type]

    # Валидируем модели
    validate_trained_models(lottery_type, config, df)


if __name__ == "__main__":
  main()