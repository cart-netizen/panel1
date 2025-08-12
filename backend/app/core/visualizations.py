import plotly.express as px
import pandas as pd
from collections import Counter


def create_number_frequency_heatmap(df, field_name='Числа_Поле1_list', title_suffix=""):
  """
    Creates a heatmap of number frequencies for a given field (e.g., 'Числа_Поле1_list').

    Args:
        df (pd.DataFrame): DataFrame containing historical draw data.
        field_name (str): The column name of the field list (e.g., 'Числа_Поле1_list').
        title_suffix (str): Suffix for the plot title, usually field identifier.

    Returns:
        plotly.graph_objects.Figure: A Plotly heatmap figure.
    """
  if df.empty or field_name not in df.columns:
    return px.imshow([[0]], title=f"Нет данных для тепловой карты {title_suffix}")

  all_numbers_in_field = [num for sublist in df[field_name].dropna() if isinstance(sublist, list) for num in sublist]
  if not all_numbers_in_field:
    return px.imshow([[0]], title=f"Не найдено чисел для тепловой карты {title_suffix}")

  counts = Counter(all_numbers_in_field)
  # Create a matrix for numbers 1-20
  freq_matrix_data = [[counts.get(i, 0)] for i in range(1, 21)]

  fig = px.imshow(freq_matrix_data,
                  labels=dict(x="Частота", y="Число", color="Частота выпадения"),
                  y=[str(i) for i in range(1, 21)],  # Number labels for y-axis
                  x=[''],  # Single column, no meaningful x-axis label needed beyond legend
                  title=f'Тепловая карта частот чисел {title_suffix}',
                  color_continuous_scale="Viridis", text_auto=True)
  fig.update_layout(yaxis_nticks=20, yaxis_title="Число", xaxis_title="",
                    coloraxis_colorbar_title="Частота")
  fig.update_xaxes(showticklabels=False)  # Hide x-axis ticks and labels
  return fig


def create_positional_histogram(df, field_name='Числа_Поле1_list', title_suffix=""):
  """
    Creates histograms for number occurrences by their position within a field.
    Assumes each list in field_name contains 4 sorted numbers.

    Args:
        df (pd.DataFrame): DataFrame with historical draw data.
        field_name (str): The column name of the field list.
        title_suffix (str): Suffix for the plot title.

    Returns:
        plotly.graph_objects.Figure: A Plotly bar chart figure.
    """
  if df.empty or field_name not in df.columns:
    return px.bar(title=f"Нет данных для позиционной гистограммы {title_suffix}")

  # Data for 4 positions
  positional_data_for_df = []
  for numbers_list in df[field_name].dropna():
    if isinstance(numbers_list, list) and len(numbers_list) == 4:
      # Assuming numbers_list is already sorted as per lottery rules for positions
      for i in range(4):  # 0, 1, 2, 3 for Pos 1, 2, 3, 4
        positional_data_for_df.append({'Число': numbers_list[i], 'Позиция': f'Поз. {i + 1}', 'Счетчик': 1})

  if not positional_data_for_df:
    return px.bar(title=f"Недостаточно валидных данных для позиционной гистограммы {title_suffix}")

  plot_df = pd.DataFrame(positional_data_for_df)
  # Aggregate counts
  plot_df_grouped = plot_df.groupby(['Число', 'Позиция']).size().reset_index(name='Частота')

  fig = px.bar(plot_df_grouped, x='Число', y='Частота', color='Позиция',
               barmode='group',
               title=f'Частота чисел по позициям {title_suffix}',
               labels={'Число': 'Число (1-20)', 'Частота': 'Частота выпадения'},
               category_orders={"Позиция": [f'Поз. {i + 1}' for i in range(4)]}  # Ensure correct order
               )
  fig.update_layout(xaxis_dtick=1, legend_title_text="Позиция в поле")
  return fig


def create_sum_histogram(df, field_name='Числа_Поле1_list', title_suffix=""):
  """
    Creates a histogram of the sum of numbers in combinations for a specific field.

    Args:
        df (pd.DataFrame): DataFrame with historical draw data.
        field_name (str): The column name of the field list.
        title_suffix (str): Suffix for the plot title.

    Returns:
        plotly.graph_objects.Figure: A Plotly histogram figure.
    """
  if df.empty or field_name not in df.columns:
    return px.histogram(title=f"Нет данных для гистограммы сумм {title_suffix}")

  sums_of_numbers = df[field_name].dropna().apply(
    lambda x: sum(x) if isinstance(x, list) and all(isinstance(n, int) for n in x) else None
  ).dropna()

  if sums_of_numbers.empty:
    return px.histogram(title=f"Нет валидных сумм для гистограммы {title_suffix}")

  # Min sum for 4 unique numbers from 1-20 is 1+2+3+4=10. Max is 17+18+19+20=74.
  nbins = max(10, min(25, int(sums_of_numbers.nunique() / 2)))  # Dynamic binning
  fig = px.histogram(sums_of_numbers, nbins=nbins,
                     title=f'Гистограмма сумм комбинаций {title_suffix}',
                     labels={'value': 'Сумма 4-х чисел'})
  fig.update_layout(yaxis_title="Количество комбинаций")
  return fig


def create_animated_frequency_timeline(df, field_name='Числа_Поле1_list', title_suffix=""):
  """
    Creates an animated bar chart showing how number frequencies change over draw numbers (time).
    Animates over a sample of recent draws for performance.

    Args:
        df (pd.DataFrame): DataFrame with historical draw data. Must include 'Тираж'.
        field_name (str): The column name of the field list.
        title_suffix (str): Suffix for the plot title.

    Returns:
        plotly.graph_objects.Figure: An animated Plotly bar chart.
    """
  if df.empty or 'Тираж' not in df.columns or field_name not in df.columns or df[field_name].dropna().empty:
    return px.bar(title=f"Нет данных для анимированной временной шкалы {title_suffix}")

  df_sorted_by_draw = df.sort_values(by="Тираж")

  # For performance, animate only a subset of draws (e.g., last 100 or a sample)
  sample_size = 100
  if len(df_sorted_by_draw) > sample_size:
    anim_df_source = df_sorted_by_draw.tail(sample_size)
  else:
    anim_df_source = df_sorted_by_draw

  if anim_df_source.empty:
    return px.bar(title=f"Недостаточно данных для анимации {title_suffix}")

  animation_frames_data = []
  cumulative_counts = Counter()  # To show evolving frequency over the animation period

  # Iterate through the sampled draws to build frames for animation
  # This animation will show the frequency of numbers *within the animated period only*
  for _, row in anim_df_source.iterrows():
    draw_number = row['Тираж']
    numbers_in_draw = row[field_name]
    if isinstance(numbers_in_draw, list):
      current_draw_counts = Counter(numbers_in_draw)
      for num, count in current_draw_counts.items():
        animation_frames_data.append({
          'Тираж': draw_number,
          'Число': str(num),  # Number as string for categorical axis
          'Частота в тираже': count  # How many times this number appeared in this specific draw (usually 1)
          # If we want cumulative frequency, logic needs change
        })

  if not animation_frames_data:
    return px.bar(title=f"Нет валидных числовых данных для анимации {title_suffix}")

  anim_df = pd.DataFrame(animation_frames_data)
  # We want to show the state of frequencies AT each draw.
  # For a bar chart animating over draws, each frame shows counts for that draw or up to that draw.
  # The current setup shows counts *per draw*. If cumulative is desired, need more complex aggregation.
  # Let's make it simpler: animate frequency of numbers appearing in each draw.

  # Get all unique numbers in the animation sample to define the y-axis range correctly for numbers
  all_numbers_in_sample = sorted(list(set(anim_df['Число'].astype(int))))

  fig = px.bar(anim_df, x='Частота в тираже', y='Число', animation_frame='Тираж',
               # animation_group='Число', # Use if bars are meant to represent the same entity across frames
               orientation='h',  # Horizontal bar chart might look better for number list
               color='Число',  # Color by number
               range_x=[0, anim_df['Частота в тираже'].max() if not anim_df.empty else 1],
               category_orders={'Число': [str(n) for n in all_numbers_in_sample]},
               # Ensure consistent order of numbers on y-axis
               title=f'Анимированная частота чисел по тиражам {title_suffix}')

  fig.update_layout(
    yaxis_title="Число",
    xaxis_title="Частота в данном тираже",
    legend_title_text="Число"
  )
  # Ensure animation iterates draw by draw correctly
  if 'Тираж' in anim_df:
    fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 1000  # Animation speed (ms per frame)
    fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 300  # Transition speed

  return fig