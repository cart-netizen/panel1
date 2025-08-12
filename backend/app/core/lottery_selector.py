# core/lottery_selector.py
"""
Модуль для выбора типа лотереи и управления конфигурацией
"""

import dash_bootstrap_components as dbc
from dash import html
from backend.app.core.data_manager import LOTTERY_CONFIGS


# def create_lottery_selector_layout():
#   """Создает layout для выбора лотереи"""
#
#   lottery_cards = []
#   for lottery_key, config in LOTTERY_CONFIGS.items():
#
#     # Определяем описание лотереи
#     if lottery_key == '4x20':
#       title = "Спортлото 4 из 20"
#       description = "Классическая лотерея: 4 числа из 20 в двух полях"
#       icon = "🎯"
#     elif lottery_key == '5x36plus':
#       title = "5 из 36 плюс"
#       description = "5 чисел из 36 + 1 число из 4"
#       icon = "🎲"
#     else:
#       title = lottery_key
#       description = "Описание недоступно"
#       icon = "🎪"
#
#     card = dbc.Card([
#       dbc.CardBody([
#         html.H2(icon, className="text-center mb-3", style={"font-size": "4rem"}),
#         html.H4(title, className="card-title text-center"),
#         html.P(description, className="card-text text-center text-muted"),
#         dbc.Button(
#           "Выбрать лотерею",
#           id=f"select-lottery-{lottery_key}",
#           color="primary",
#           size="lg",
#           className="w-100"
#         )
#       ])
#     ], className="h-100")
#
#     lottery_cards.append(
#       dbc.Col(card, width=12, md=6, lg=4, className="mb-4")
#     )
#
#   return dbc.Container([
#     dbc.Row([
#       dbc.Col([
#         html.H1("🎲 Аналитическая панель лотерей", className="text-center mb-2"),
#         html.P("Выберите лотерею для анализа", className="text-center text-muted mb-5")
#       ], width=12)
#     ]),
#     dbc.Row(lottery_cards, justify="center"),
#     dbc.Row([
#       dbc.Col([
#         html.Hr(),
#         html.P("💡 Совет: Каждая лотерея имеет свою базу данных и настройки анализа",
#                className="text-center text-muted small")
#       ], width=12)
#     ])
#   ], fluid=True, className="py-5")
#
def create_lottery_selector_layout():
    """Создает layout для выбора типа лотереи"""
    return dbc.Container(fluid=True, className="vh-100 d-flex align-items-center justify-content-center", children=[
      dbc.Row([
        dbc.Col([
          html.H1("🎲 Выберите лотерею", className="text-center mb-5 display-4"),
          dbc.Row([
            dbc.Col([
              dbc.Card([
                dbc.CardImg(src="/assets/4x20-logo.png", top=True,
                            style={"height": "200px", "object-fit": "cover"}) if False else None,
                dbc.CardBody([
                  html.H4("Спортлото 4 из 20", className="card-title text-center"),
                  html.P("Классическая лотерея с двумя полями по 4 числа",
                         className="card-text text-center text-muted"),
                  dbc.Button(
                    "Перейти к анализу",
                    id="select-lottery-4x20",
                    color="primary",
                    size="lg",
                    className="w-100"
                  )
                ])
              ], className="h-100 shadow-sm lottery-card")
            ], width=12, md=6, className="mb-4"),

            dbc.Col([
              dbc.Card([
                dbc.CardImg(src="/assets/5x36-logo.png", top=True,
                            style={"height": "200px", "object-fit": "cover"}) if False else None,
                dbc.CardBody([
                  html.H4("5 из 36 плюс", className="card-title text-center"),
                  html.P("Лотерея с полем из 5 чисел плюс дополнительное число",
                         className="card-text text-center text-muted"),
                  dbc.Button(
                    "Перейти к анализу",
                    id="select-lottery-5x36plus",
                    color="success",
                    size="lg",
                    className="w-100"
                  )
                ])
              ], className="h-100 shadow-sm lottery-card")
            ], width=12, md=6, className="mb-4")
          ], justify="center")
        ], width=12, lg=8)
      ], justify="center")
    ])




def get_lottery_callbacks():
  """Возвращает список callback-ов для выбора лотереи"""
  callbacks = []
  for lottery_key in LOTTERY_CONFIGS.keys():
    callbacks.append({
      'output_id': 'url',
      'output_property': 'pathname',
      'input_id': f'select-lottery-{lottery_key}',
      'input_property': 'n_clicks',
      'lottery_type': lottery_key
    })
  return callbacks
#
# def get_lottery_callbacks():
#     """Возвращает коллбэки для выбора лотереи (пустая функция для совместимости)"""
#     pass