"""
API для симуляции стратегий с интеграцией bankroll_manager
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from backend.app.core.auth import get_current_user
from backend.app.core.lottery_context import LotteryContext
from backend.app.core import data_manager, combination_generator, pattern_analyzer
from backend.app.core.database import User, UserPreferences, get_db
from backend.app.core.bankroll_manager import BankrollManager
from enum import Enum
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class BettingStrategy(Enum):
    FIXED = "fixed"
    KELLY = "kelly"
    PERCENTAGE = "percentage"
    MARTINGALE = "martingale"
    FIBONACCI = "fibonacci"

class StrategySimulationRequest(BaseModel):
    """Запрос на симуляцию стратегии"""
    lottery_type: str = "4x20"
    strategy: str = "random"  # random, hot, cold, mixed, ai, martingale, fibonacci
    num_draws: int = 100
    combinations_per_draw: int = 1
    use_favorites: bool = False
    initial_bankroll: float = 10000.0
    bet_size: float = 100.0


class ROICalculationRequest(BaseModel):
    """Запрос на расчёт ROI"""
    lottery_type: str = "4x20"
    investment: float = 1000.0
    ticket_price: float = 100.0
    duration_days: int = 30
    strategy: str = "mixed"


class BankrollSimulationRequest(BaseModel):
    """Запрос на симуляцию управления банкроллом"""
    lottery_type: str = "4x20"
    initial_bankroll: float = 10000.0
    strategy: str = "kelly"  # kelly, fixed, percentage, martingale, fibonacci
    num_simulations: int = 1000
    num_draws: int = 100
    risk_level: float = 0.02  # 2% риска по умолчанию
    bet_size: float = 100.0

@router.post("/strategy")
async def simulate_strategy(
    request: StrategySimulationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Детальная симуляция стратегии на исторических данных"""
    try:
        logger.info(f"🚀 Запуск симуляции стратегии: {request.strategy} для {request.lottery_type}")
        logger.info(
            f"📊 Параметры: тиражей={request.num_draws}, банкролл={request.initial_bankroll}, ставка={request.bet_size}")

        with LotteryContext(request.lottery_type):
            df_history = data_manager.fetch_draws_from_db()

            if len(df_history) < request.num_draws:
                logger.warning(f"⚠️ Недостаточно данных: доступно {len(df_history)}, запрошено {request.num_draws}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Недостаточно данных. Доступно {len(df_history)} тиражей"
                )

            config = data_manager.get_current_config()
            logger.info(f"🎯 Конфигурация лотереи: {config.get('name', 'Unknown')}")

            # Инициализация банкролл менеджера (ИСПРАВЛЕННАЯ ВЕРСИЯ)
            bankroll_mgr = BankrollManager(
                initial_bankroll=request.initial_bankroll,
                ticket_cost=request.bet_size
            )
            logger.info(f"💰 BankrollManager инициализирован: банкролл={request.initial_bankroll}, цена билета={request.bet_size}")

            # Выбираем стратегию ставок
            if request.strategy in ["martingale", "fibonacci"]:
                betting_strategy = BettingStrategy[request.strategy.upper()]
            else:
                betting_strategy = BettingStrategy.FIXED

            results = []
            wins = 0
            total_spent = 0
            total_won = 0
            consecutive_losses = 0
            consecutive_wins = 0

            # Берём случайную выборку из истории для симуляции
            sample_draws = df_history.sample(n=min(request.num_draws, len(df_history)))

            for idx, (_, draw) in enumerate(sample_draws.iterrows()):
                # Генерируем комбинации согласно стратегии
                combinations = _generate_strategy_combinations(
                    request.strategy,
                    request.combinations_per_draw,
                    df_history,
                    config,
                    db,
                    current_user.id if request.use_favorites else None
                )

                # Рассчитываем размер ставки
                # Для Kelly нужна вероятность и коэффициент
                if betting_strategy == BettingStrategy.KELLY:
                    bet_size = bankroll_mgr.calculate_kelly_bet(
                        win_probability=0.05,
                        odds=100,
                        fraction=0.25  # Используем четверть Келли для безопасности
                    )
                # Для Martingale учитываем серию проигрышей
                elif betting_strategy == BettingStrategy.MARTINGALE:
                    base_bet = request.bet_size
                    bet_size = base_bet * (2 ** consecutive_losses)
                    bet_size = min(bet_size, bankroll_mgr.current_bankroll * 0.5)  # Не более 50% банкролла
                # Для Fibonacci
                elif betting_strategy == BettingStrategy.FIBONACCI:
                    fib_sequence = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
                    fib_index = min(consecutive_losses, len(fib_sequence) - 1)
                    bet_size = request.bet_size * fib_sequence[fib_index]
                    bet_size = min(bet_size, bankroll_mgr.current_bankroll * 0.3)
                # Процент от банкролла
                elif betting_strategy == BettingStrategy.PERCENTAGE:
                    bet_size = bankroll_mgr.current_bankroll * 0.02  # 2% от банкролла
                # Фиксированная ставка
                else:
                    bet_size = request.bet_size

                # Ограничиваем ставку текущим банкроллом
                bet_size = min(bet_size, bankroll_mgr.current_bankroll)

                # Проверяем выигрыш для каждой комбинации
                draw_won = False
                prize = 0

                # Правильно извлекаем числа из draw
                draw_field1 = draw.get('field1_numbers', draw.get('Числа_Поле1_list', []))
                draw_field2 = draw.get('field2_numbers', draw.get('Числа_Поле2_list', []))

                for combo in combinations:
                    is_win = _check_combination_win(
                        combo['field1'],
                        combo['field2'],
                        draw_field1,
                        draw_field2,
                        config
                    )

                    if is_win['won']:
                        draw_won = True
                        prize = _calculate_prize(is_win['match_level'], bet_size)
                        total_won += prize
                        bankroll_mgr.update_bankroll(prize)
                        wins += 1
                        consecutive_wins += 1
                        consecutive_losses = 0
                        break

                if not draw_won:
                    consecutive_losses += 1
                    consecutive_wins = 0

                # Обновляем банкролл
                total_spent += bet_size * request.combinations_per_draw
                bankroll_mgr.update_bankroll(-bet_size * request.combinations_per_draw)

                results.append({
                    "draw": idx + 1,
                    "draw_number": int(draw.get('Тираж', draw.get('draw_number', idx + 1))),
                    "combinations_played": request.combinations_per_draw,
                    "bet_size": round(bet_size, 2),
                    "won": draw_won,
                    "bankroll": round(bankroll_mgr.current_bankroll, 2),
                    "prize": prize
                })

                # Проверка на банкротство
                if bankroll_mgr.current_bankroll <= 0:
                    break

            # Расчёт итоговой статистики
            roi = ((total_won - total_spent) / total_spent) * 100 if total_spent > 0 else 0
            win_rate = (wins / len(results)) * 100 if results else 0

            # Анализ просадок
            bankroll_history = [r['bankroll'] for r in results]
            max_drawdown = _calculate_max_drawdown(bankroll_history)

            return {
                "status": "success",
                "strategy": request.strategy,
                "betting_strategy": betting_strategy.value,
                "simulated_draws": len(results),
                "total_draws_requested": request.num_draws,
                "wins": wins,
                "win_rate": round(win_rate, 2),
                "total_spent": round(total_spent, 2),
                "total_won": round(total_won, 2),
                "roi": round(roi, 2),
                "initial_bankroll": request.initial_bankroll,
                "final_bankroll": round(bankroll_mgr.current_bankroll, 2),
                "max_drawdown": round(max_drawdown, 2),
                "profit_loss": round(bankroll_mgr.current_bankroll - request.initial_bankroll, 2),
                "results_sample": results[:10],  # Первые 10 результатов
                "recommendation": _get_strategy_recommendation(roi, win_rate, max_drawdown),
                "bankrupt": bankroll_mgr.current_bankroll <= 0,
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(f"✅ Результат симуляции: ROI={result['roi']}%, WinRate={result['win_rate']}%")
            logger.info(f"📊 Структура результата: {list(result.keys())}")

    except Exception as e:
        logger.error(f"❌ Ошибка симуляции стратегии: {e}")
        logger.error(f"❌ Тип ошибки: {type(e).__name__}")
        logger.error(f"❌ Трассировка: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка симуляции стратегии: {str(e)}")


@router.post("/roi")
async def calculate_roi(
    request: ROICalculationRequest,
    current_user: User = Depends(get_current_user)
):
    """Продвинутый расчёт ROI с учётом реальной статистики"""
    try:
        logger.info(f"💰 Запуск расчёта ROI: инвестиции={request.investment}, билет={request.ticket_price}")
        with LotteryContext(request.lottery_type):
            df_history = data_manager.fetch_draws_from_db()

            if df_history.empty:
                raise HTTPException(status_code=404, detail="Нет исторических данных")

            logger.info(f"📊 Использование {len(df_history)} тиражей для ROI расчёта")
            # Анализ реальных выигрышей в истории
            config = data_manager.get_current_config()

            # Расчёт базовых параметров
            num_tickets = int(request.investment / request.ticket_price)
            draws_per_week = 2  # Обычно 2 тиража в неделю
            total_draws = (request.duration_days // 7) * draws_per_week

            logger.info(f"🎫 Билетов: {num_tickets}, Тиражей: {total_draws}")

            # Анализируем реальные вероятности на основе истории
            win_probabilities = _calculate_real_win_probabilities(df_history, config)

            # Моделируем различные сценарии на основе реальных данных
            scenarios = {}

            # Пессимистичный сценарий (нижний квартиль)
            scenarios["pessimistic"] = _simulate_roi_scenario(
                num_tickets=num_tickets,
                total_draws=total_draws,
                win_rate=win_probabilities['low'],
                avg_prize=win_probabilities['avg_prize'] * 0.7,
                investment=request.investment
            )

            # Реалистичный сценарий (медиана)
            scenarios["realistic"] = _simulate_roi_scenario(
                num_tickets=num_tickets,
                total_draws=total_draws,
                win_rate=win_probabilities['median'],
                avg_prize=win_probabilities['avg_prize'],
                investment=request.investment
            )

            # Оптимистичный сценарий (верхний квартиль)
            scenarios["optimistic"] = _simulate_roi_scenario(
                num_tickets=num_tickets,
                total_draws=total_draws,
                win_rate=win_probabilities['high'],
                avg_prize=win_probabilities['avg_prize'] * 1.5,
                investment=request.investment
            )

            # Монте-Карло симуляция для более точной оценки
            monte_carlo_results = _monte_carlo_roi_simulation(
                num_tickets=num_tickets,
                total_draws=total_draws,
                investment=request.investment,
                win_probabilities=win_probabilities,
                num_simulations=1000
            )
            logger.info(f"✅ ROI расчёт завершён успешно")

            return {
                "status": "success",
                "investment": request.investment,
                "ticket_price": request.ticket_price,
                "num_tickets": num_tickets,
                "duration_days": request.duration_days,
                "total_draws": total_draws,
                "scenarios": scenarios,
                "monte_carlo": monte_carlo_results,
                "recommendation": _get_roi_recommendation(scenarios, monte_carlo_results),
                "risk_assessment": _assess_risk_level(scenarios, monte_carlo_results),
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
async def compare_methods(
    lottery_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сравнение различных методов генерации комбинаций"""
    try:
        logger.info(f"⚖️ Запуск сравнения методов для {lottery_type}")

        with LotteryContext(lottery_type):
            df_history = data_manager.fetch_draws_from_db()

            if df_history.empty:
                logger.warning(f"⚠️ Нет исторических данных для {lottery_type}")
                raise HTTPException(status_code=404, detail="Нет исторических данных")

            logger.info(f"📊 Доступно {len(df_history)} тиражей для сравнения")
            config = data_manager.get_current_config()

            # Методы для сравнения
            methods = ["random", "hot", "cold", "mixed", "ai"]
            comparison_results = []

            for method in methods:
                try:
                    logger.info(f"🧪 Тестирование метода: {method}")

                    method_result = _test_generation_method(method, df_history, config, 50)
                    comparison_results.append(method_result)
                    logger.info(f"✅ Метод {method} протестирован")

                except Exception as method_error:
                    logger.error(f"❌ Ошибка тестирования метода {method}: {method_error}")
                    continue

            if not comparison_results:
                raise HTTPException(status_code=500, detail="Не удалось протестировать ни один метод")

            # Определяем лучший метод
            best_method = max(comparison_results, key=lambda x: x['avg_score'])
            logger.info(f"🏆 Лучший метод: {best_method['method']}")

            return {
                "status": "success",
                "comparison": comparison_results,
                "best_overall": best_method['method'],
                "summary": f"Протестировано {len(comparison_results)} методов",
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Ошибка сравнения методов: {e}")
        logger.error(f"❌ Тип ошибки: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Ошибка сравнения методов: {str(e)}")
#     lottery_type: str = "4x20",
#     num_simulations: int = 100,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Сравнение различных методов генерации на реальных данных"""
#     try:
#         logger.info(f"⚖️ Запуск сравнения методов для {lottery_type}")
#
#         with LotteryContext(lottery_type):
#             df_history = data_manager.fetch_draws_from_db()
#
#             if len(df_history) < 100:
#                 raise HTTPException(status_code=400, detail="Недостаточно данных для сравнения")
#
#             logger.info(f"📊 Доступно {len(df_history)} тиражей для сравнения")
#
#             config = data_manager.get_current_config()
#             methods = ["random", "hot", "cold", "mixed", "ai", "pattern"]
#             comparison = []
#
#             # Тестируем каждый метод
#             for method in methods:
#                 method_results = _test_generation_method(
#                     method=method,
#                     df_history=df_history,
#                     config=config,
#                     num_simulations=num_simulations
#                 )
#
#                 comparison.append({
#                     "method": method,
#                     "avg_score": round(method_results['avg_score'], 1),
#                     "win_rate": round(method_results['win_rate'], 2),
#                     "roi": round(method_results['roi'], 2),
#                     "consistency": round(method_results['consistency'], 2),
#                     "complexity": _get_method_complexity(method),
#                     "recommended_for": _get_method_recommendation(method, method_results),
#                     "pros": method_results['pros'],
#                     "cons": method_results['cons']
#                 })
#
#             # Сортируем по среднему скору
#             comparison.sort(key=lambda x: x["avg_score"], reverse=True)
#
#             return {
#                 "status": "success",
#                 "lottery_type": lottery_type,
#                 "comparison": comparison,
#                 "best_overall": comparison[0]["method"],
#                 "best_for_beginners": next(m["method"] for m in comparison if "Новички" in m["recommended_for"]),
#                 "best_roi": max(comparison, key=lambda x: x["roi"])["method"],
#                 "most_consistent": max(comparison, key=lambda x: x["consistency"])["method"],
#                 "analysis_based_on": f"{len(df_history)} исторических тиражей",
#                 "timestamp": datetime.utcnow().isoformat()
#             }
#
#     except Exception as e:
#         logger.error(f"❌ Ошибка сравнения методов: {e}")
#         logger.error(f"❌ Тип ошибки: {type(e).__name__}")
#         raise HTTPException(status_code=500, detail=f"Ошибка сравнения методов: {str(e)}")

@router.post("/bankroll")
async def simulate_bankroll_management(
    request: BankrollSimulationRequest,
    current_user: User = Depends(get_current_user)
):
    """Симуляция управления банкроллом с различными стратегиями"""
    try:
        logger.info(f"🏦 Запуск симуляции банкролла: стратегия={request.strategy}")
        logger.info(
            f"📊 Параметры: банкролл={request.initial_bankroll}, симуляций={request.num_simulations}, риск={request.risk_level}")

        with LotteryContext(request.lottery_type):
            df_history = data_manager.fetch_draws_from_db()

            if len(df_history) < request.num_draws:
                logger.warning(f"⚠️ Недостаточно данных: доступно {len(df_history)}, запрошено {request.num_draws}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Недостаточно данных. Доступно {len(df_history)} тиражей"
                )

            config = data_manager.get_current_config()
            logger.info(f"🎯 Конфигурация лотереи: {config.get('name', 'Unknown')}")

            # Инициализация банкролл менеджера (ИСПРАВЛЕННАЯ ВЕРСИЯ)
            bankroll_mgr = BankrollManager(
                initial_bankroll=request.initial_bankroll,
                ticket_cost=request.bet_size if hasattr(request, 'bet_size') else 100
            )
            logger.info(f"💰 BankrollManager инициализирован: банкролл={request.initial_bankroll}, цена билета={request.bet_size}")

            # Выбор стратегии
            strategy = BettingStrategy[request.strategy.upper()]

            # Запуск множественных симуляций
            simulation_results = []

            for sim_idx in range(request.num_simulations):
                sim_bankroll = request.initial_bankroll
                sim_history = []
                consecutive_losses = 0
                consecutive_wins = 0

                for draw_idx in range(request.num_draws):
                    # Расчёт размера ставки
                    bet_size = bankroll_mgr.calculate_bet_size(
                        strategy=strategy,
                        win_probability=0.05,
                        odds=100,
                        current_streak=consecutive_losses if strategy == BettingStrategy.MARTINGALE else 0
                    )

                    # Ограничение ставки текущим банкроллом
                    bet_size = min(bet_size, sim_bankroll * request.risk_level)

                    # Симуляция результата (вероятность выигрыша ~5%)
                    is_win = np.random.random() < 0.05

                    if is_win:
                        prize = bet_size * np.random.choice([5, 10, 20, 50, 100], p=[0.5, 0.3, 0.15, 0.04, 0.01])
                        sim_bankroll += prize - bet_size
                        consecutive_wins += 1
                        consecutive_losses = 0
                    else:
                        sim_bankroll -= bet_size
                        consecutive_losses += 1
                        consecutive_wins = 0

                    sim_history.append(sim_bankroll)

                    # Проверка на банкротство
                    if sim_bankroll <= 0:
                        break

                simulation_results.append({
                    "final_bankroll": sim_bankroll,
                    "survived": sim_bankroll > 0,
                    "max_bankroll": max(sim_history),
                    "min_bankroll": min(sim_history),
                    "draws_played": len(sim_history)
                })

            # Анализ результатов
            survived_count = sum(1 for r in simulation_results if r["survived"])
            survival_rate = (survived_count / request.num_simulations) * 100

            avg_final_bankroll = np.mean([r["final_bankroll"] for r in simulation_results])
            median_final_bankroll = np.median([r["final_bankroll"] for r in simulation_results])

            profitable_count = sum(1 for r in simulation_results if r["final_bankroll"] > request.initial_bankroll)
            profitability_rate = (profitable_count / request.num_simulations) * 100

            # Расчёт рисков
            var_95 = np.percentile([r["final_bankroll"] for r in simulation_results], 5)
            cvar_95 = np.mean([r["final_bankroll"] for r in simulation_results if r["final_bankroll"] <= var_95])

            return {
                "status": "success",
                "strategy": request.strategy,
                "initial_bankroll": request.initial_bankroll,
                "num_simulations": request.num_simulations,
                "num_draws": request.num_draws,
                "results": {
                    "survival_rate": round(survival_rate, 2),
                    "profitability_rate": round(profitability_rate, 2),
                    "avg_final_bankroll": round(avg_final_bankroll, 2),
                    "median_final_bankroll": round(median_final_bankroll, 2),
                    "best_result": round(max(r["final_bankroll"] for r in simulation_results), 2),
                    "worst_result": round(min(r["final_bankroll"] for r in simulation_results), 2),
                    "var_95": round(var_95, 2),
                    "cvar_95": round(cvar_95, 2)
                },
                "recommendation": _get_bankroll_recommendation(
                    strategy, survival_rate, profitability_rate, var_95
                ),
                "risk_assessment": _assess_strategy_risk(survival_rate, profitability_rate, cvar_95),
                "optimal_settings": _suggest_optimal_settings(
                    request.initial_bankroll, survival_rate, profitability_rate
                ),
                "timestamp": datetime.utcnow().isoformat()
            }


    except Exception as e:
        logger.error(f"❌ Ошибка симуляции стратегии: {e}")
        logger.error(f"❌ Тип ошибки: {type(e).__name__}")
        logger.error(f"❌ Трассировка: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка симуляции стратегии: {str(e)}")

# Вспомогательные функции
def _generate_strategy_combinations(strategy, count, df_history, config, db, user_id):
    """Генерация комбинаций согласно стратегии"""
    combinations = []

    if strategy == "random":
        # Случайная генерация
        for _ in range(count):
            f1, f2 = combination_generator.generate_random_combination()
            combinations.append({
                'field1': f1,
                'field2': f2
            })

    elif strategy in ["hot", "cold", "balanced"]:
        # Паттерн-based генерация
        generated = combination_generator.generate_pattern_based_combinations(
            df_history, count, strategy
        )
        for f1, f2, desc in generated:
            combinations.append({
                'field1': f1,
                'field2': f2
            })

    elif strategy == "mixed":
        # Смешанная стратегия - комбинируем hot и cold
        half = count // 2
        hot_combos = combination_generator.generate_pattern_based_combinations(
            df_history, half, 'hot'
        )
        cold_combos = combination_generator.generate_pattern_based_combinations(
            df_history, count - half, 'cold'
        )

        for f1, f2, desc in hot_combos:
            combinations.append({'field1': f1, 'field2': f2})
        for f1, f2, desc in cold_combos:
            combinations.append({'field1': f1, 'field2': f2})

    elif strategy == "ai":
        # ML-based генерация
        generated = combination_generator.generate_ml_based_combinations(
            df_history, count
        )
        for f1, f2, desc in generated:
            combinations.append({
                'field1': f1,
                'field2': f2
            })

    elif strategy in ["martingale", "fibonacci"]:
        # Для стратегий ставок используем RF ranked
        generated = combination_generator.generate_rf_ranked_combinations(
            df_history, count
        )
        for f1, f2, desc in generated:
            combinations.append({
                'field1': f1,
                'field2': f2
            })

    else:  # pattern или любая другая
        # Multi-strategy как fallback
        generated = combination_generator.generate_multi_strategy_combinations(
            df_history, count
        )
        for f1, f2, desc in generated:
            combinations.append({
                'field1': f1,
                'field2': f2
            })

    return combinations

def _check_combination_win(field1, field2, draw_field1, draw_field2, config):
    """Проверка выигрыша комбинации"""
    match_f1 = len(set(field1) & set(draw_field1))
    match_f2 = len(set(field2) & set(draw_field2))

    # Определение уровня выигрыша (упрощённо)
    if match_f1 == config['field1_size'] and match_f2 == config['field2_size']:
        return {"won": True, "match_level": "jackpot"}
    elif match_f1 == config['field1_size'] and match_f2 >= 1:
        return {"won": True, "match_level": "major"}
    elif match_f1 >= 3 and match_f2 >= 1:
        return {"won": True, "match_level": "minor"}
    elif match_f1 >= 2:
        return {"won": True, "match_level": "small"}
    else:
        return {"won": False, "match_level": None}

def _calculate_prize(match_level, bet_size):
    """Расчёт выигрыша"""
    prizes = {
        "jackpot": bet_size * 10000,
        "major": bet_size * 1000,
        "minor": bet_size * 100,
        "small": bet_size * 5
    }
    return prizes.get(match_level, 0)

def _calculate_max_drawdown(bankroll_history):
    """Расчёт максимальной просадки"""
    if not bankroll_history:
        return 0

    max_value = bankroll_history[0]
    max_drawdown = 0

    for value in bankroll_history:
        if value > max_value:
            max_value = value
        drawdown = (max_value - value) / max_value * 100 if max_value > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)

    return max_drawdown

def _get_strategy_recommendation(roi, win_rate, max_drawdown):
    """Рекомендация по стратегии"""
    if roi > 10 and win_rate > 20:
        return "🟢 Хорошая стратегия с положительным ROI"
    elif roi > 0:
        return "🟡 Умеренная стратегия с небольшой прибылью"
    elif roi > -20:
        return "🟠 Убыточная стратегия, но приемлемые потери"
    else:
        return "🔴 Высокий риск потерь, не рекомендуется"

def _calculate_real_win_probabilities(df_history, config):
    """Расчёт реальных вероятностей на основе истории"""
    # Здесь должен быть анализ реальных выигрышных комбинаций
    # Упрощённая версия
    return {
        "low": 0.01,
        "median": 0.05,
        "high": 0.10,
        "avg_prize": 500
    }

def _simulate_roi_scenario(num_tickets, total_draws, win_rate, avg_prize, investment):
    """Симуляция ROI сценария"""
    expected_wins = num_tickets * win_rate
    expected_return = expected_wins * avg_prize
    roi = ((expected_return - investment) / investment) * 100

    return {
        "expected_wins": round(expected_wins, 2),
        "expected_return": round(expected_return, 2),
        "roi_percentage": round(roi, 2),
        "break_even": expected_return >= investment,
        "profit_loss": round(expected_return - investment, 2)
    }

def _monte_carlo_roi_simulation(num_tickets, total_draws, investment, win_probabilities, num_simulations):
    """Монте-Карло симуляция ROI"""
    results = []

    for _ in range(num_simulations):
        total_return = 0
        for _ in range(num_tickets):
            if np.random.random() < win_probabilities['median']:
                # Случайный приз из распределения
                prize = np.random.gamma(2, win_probabilities['avg_prize'] / 2)
                total_return += prize

        roi = ((total_return - investment) / investment) * 100
        results.append(roi)

    return {
        "mean_roi": round(np.mean(results), 2),
        "median_roi": round(np.median(results), 2),
        "std_roi": round(np.std(results), 2),
        "percentile_5": round(np.percentile(results, 5), 2),
        "percentile_95": round(np.percentile(results, 95), 2),
        "probability_profit": round(sum(1 for r in results if r > 0) / num_simulations * 100, 2)
    }

def _get_roi_recommendation(scenarios, monte_carlo):
    """Рекомендация по ROI"""
    if monte_carlo['probability_profit'] > 60:
        return "🎯 Высокая вероятность прибыли"
    elif monte_carlo['probability_profit'] > 30:
        return "⚡ Умеренная вероятность прибыли"
    else:
        return "⚠️ Низкая вероятность прибыли"

def _assess_risk_level(scenarios, monte_carlo):
    """Оценка уровня риска"""
    risk_score = 0

    # Оценка волатильности
    if monte_carlo['std_roi'] > 50:
        risk_score += 3
    elif monte_carlo['std_roi'] > 25:
        risk_score += 2
    else:
        risk_score += 1

    # Оценка худшего сценария
    if monte_carlo['percentile_5'] < -50:
        risk_score += 3
    elif monte_carlo['percentile_5'] < -25:
        risk_score += 2
    else:
        risk_score += 1

    if risk_score >= 5:
        return {"level": "HIGH", "description": "Высокий риск потерь"}
    elif risk_score >= 3:
        return {"level": "MEDIUM", "description": "Умеренный риск"}
    else:
        return {"level": "LOW", "description": "Низкий риск"}


def _test_generation_method(method, df_history, config, num_simulations):
    """Тестирование метода генерации"""
    from backend.app.core import combination_generator
    import numpy as np

    scores = []
    wins = 0

    for _ in range(num_simulations):
        try:
            # Генерируем комбинацию методом
            if method == "random":
                f1, f2 = combination_generator.generate_random_combination()
                combo = {'field1': f1, 'field2': f2}

            elif method == "hot":
                generated = combination_generator.generate_pattern_based_combinations(
                    df_history.tail(50), 1, 'hot'
                )
                if generated:
                    f1, f2, desc = generated[0]
                    combo = {'field1': f1, 'field2': f2}
                else:
                    f1, f2 = combination_generator.generate_random_combination()
                    combo = {'field1': f1, 'field2': f2}

            elif method == "cold":
                generated = combination_generator.generate_pattern_based_combinations(
                    df_history.tail(50), 1, 'cold'
                )
                if generated:
                    f1, f2, desc = generated[0]
                    combo = {'field1': f1, 'field2': f2}
                else:
                    f1, f2 = combination_generator.generate_random_combination()
                    combo = {'field1': f1, 'field2': f2}

            elif method == "mixed":
                generated = combination_generator.generate_pattern_based_combinations(
                    df_history.tail(50), 1, 'balanced'
                )
                if generated:
                    f1, f2, desc = generated[0]
                    combo = {'field1': f1, 'field2': f2}
                else:
                    f1, f2 = combination_generator.generate_random_combination()
                    combo = {'field1': f1, 'field2': f2}

            elif method == "ai":
                generated = combination_generator.generate_rf_ranked_combinations(
                    df_history.tail(50), 1
                )
                if generated:
                    f1, f2, desc = generated[0]
                    combo = {'field1': f1, 'field2': f2}
                else:
                    f1, f2 = combination_generator.generate_random_combination()
                    combo = {'field1': f1, 'field2': f2}

            else:  # pattern или другие
                f1, f2 = combination_generator.generate_random_combination()
                combo = {'field1': f1, 'field2': f2}

            # Оцениваем комбинацию
            score = _evaluate_combination_score(combo, df_history)
            scores.append(score)

            # Проверяем на случайном тираже
            if not df_history.empty:
                random_draw = df_history.sample(1).iloc[0]

                # Извлекаем числа из тиража правильно
                draw_f1 = random_draw.get('field1_numbers', random_draw.get('Числа_Поле1_list', []))
                draw_f2 = random_draw.get('field2_numbers', random_draw.get('Числа_Поле2_list', []))

                if isinstance(draw_f1, list) and isinstance(draw_f2, list):
                    win_check = _check_combination_win(
                        combo['field1'], combo['field2'],
                        draw_f1, draw_f2,
                        config
                    )
                    if win_check.get('won', False):
                        wins += 1

        except Exception as e:
            logger.warning(f"Ошибка тестирования метода {method}: {e}")
            scores.append(50)  # Средний скор при ошибке

    avg_score = round(np.mean(scores) if scores else 50, 2)
    win_rate = round((wins / num_simulations) * 100, 2) if num_simulations > 0 else 0
    roi = round((wins * 500 - num_simulations * 100) / (num_simulations * 100) * 100,
                2) if num_simulations > 0 else -100

    return {
        "method": method,
        "avg_score": avg_score,
        "win_rate": win_rate,
        "roi": roi,
        "complexity": _get_method_complexity(method),
        "consistency": max(0, 100 - (np.std(scores) if scores else 50)),
        "pros": _get_method_pros(method),  # ДОБАВИТЬ
        "cons": _get_method_cons(method)  # ДОБАВИТЬ
    }

# def _evaluate_combination_score(combo, df_history):
#     """Оценка качества комбинации"""
#     score = 50  # Базовый скор
#
#     # Анализ горячих/холодных чисел
#     hot_cold = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
#         df_history.tail(20), window_sizes=[20], top_n=10
#     )
#
#     # Добавляем баллы за горячие числа
#     hot_numbers = hot_cold.get('field1_window_20', {}).get('hot_numbers', [])
#     hot_count = len(set(combo['field1']) & set(hot_numbers))
#     score += hot_count * 5
#
#     return min(100, score)

def _get_method_complexity(method):
    """Определение сложности метода"""
    complexity_map = {
        "random": "Низкая",
        "hot": "Низкая",
        "cold": "Средняя",
        "mixed": "Средняя",
        "ai": "Высокая",
        "pattern": "Высокая"
    }
    return complexity_map.get(method, "Средняя")

def _get_method_recommendation(method, results):
    """Рекомендация для метода"""
    if results['avg_score'] > 70 and results['consistency'] > 70:
        return "Все игроки"
    elif results['consistency'] > 80:
        return "Новички"
    elif results['avg_score'] > 75:
        return "Опытные"
    else:
        return "Экспериментаторы"

def _get_method_pros(method):
    """Преимущества метода"""
    pros_map = {
        "random": ["Простота", "Непредсказуемость"],
        "hot": ["Следование трендам", "Высокая активность"],
        "cold": ["Потенциал возврата", "Контртренд"],
        "mixed": ["Баланс", "Диверсификация"],
        "ai": ["Интеллектуальный анализ", "Адаптивность"],
        "pattern": ["Поиск закономерностей", "Глубокий анализ"]
    }
    return pros_map.get(method, ["Стандартный подход"])

def _get_method_cons(method):
    """Недостатки метода"""
    cons_map = {
        "random": ["Нет стратегии", "Случайность"],
        "hot": ["Следование толпе", "Переоценённость"],
        "cold": ["Долгое ожидание", "Риск"],
        "mixed": ["Компромисс", "Средние результаты"],
        "ai": ["Сложность", "Требует данных"],
        "pattern": ["Переусложнение", "Ложные паттерны"]
    }
    return cons_map.get(method, ["Возможны недостатки"])

def _get_bankroll_recommendation(strategy, survival_rate, profitability_rate, var_95):
    """Рекомендация по управлению банкроллом"""
    if survival_rate > 90 and profitability_rate > 60:
        return f"✅ Стратегия {strategy} показывает отличные результаты"
    elif survival_rate > 70:
        return f"⚡ Стратегия {strategy} приемлема с осторожностью"
    else:
        return f"❌ Стратегия {strategy} слишком рискованна"

def _assess_strategy_risk(survival_rate, profitability_rate, cvar_95):
    """Оценка риска стратегии"""
    if survival_rate < 50:
        return "КРИТИЧЕСКИЙ"
    elif survival_rate < 70:
        return "ВЫСОКИЙ"
    elif survival_rate < 90:
        return "УМЕРЕННЫЙ"
    else:
        return "НИЗКИЙ"

def _suggest_optimal_settings(initial_bankroll, survival_rate, profitability_rate):
    """Предложение оптимальных настроек"""
    if survival_rate < 70:
        suggested_bet = initial_bankroll * 0.01  # 1% банкролла
    elif survival_rate < 90:
        suggested_bet = initial_bankroll * 0.02  # 2% банкролла
    else:
        suggested_bet = initial_bankroll * 0.03  # 3% банкролла

    return {
        "suggested_bet_size": round(suggested_bet, 2),
        "suggested_risk_level": round(suggested_bet / initial_bankroll * 100, 2),
        "suggested_stop_loss": round(initial_bankroll * 0.3, 2),
        "suggested_take_profit": round(initial_bankroll * 1.5, 2)
    }


def _evaluate_combination_score(combo, df_history):
    """Оценка качества комбинации"""
    if df_history.empty:
        return 50

    try:
        from backend.app.core import pattern_analyzer

        score = 50  # Базовый скор

        # Анализ горячих/холодных чисел
        hot_cold = pattern_analyzer.GLOBAL_PATTERN_ANALYZER.analyze_hot_cold_numbers(
            df_history.tail(20), window_sizes=[20], top_n=10
        )

        # Добавляем баллы за горячие числа
        if 'field1_window20' in hot_cold:
            hot_numbers_f1 = [item[0] for item in hot_cold['field1_window20'].get('hot_numbers', [])]
            hot_count_f1 = len(set(combo['field1']) & set(hot_numbers_f1))
            score += hot_count_f1 * 5

        if 'field2_window20' in hot_cold:
            hot_numbers_f2 = [item[0] for item in hot_cold['field2_window20'].get('hot_numbers', [])]
            hot_count_f2 = len(set(combo['field2']) & set(hot_numbers_f2))
            score += hot_count_f2 * 3

        return min(100, max(0, score))

    except Exception as e:
        logger.warning(f"Ошибка при оценке комбинации: {e}")
        return 50