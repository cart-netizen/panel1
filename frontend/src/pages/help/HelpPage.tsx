import React, { useState } from 'react';
import { HELP_SECTIONS } from '../../constants';
import { Button, SecondaryButton } from '../../components/common/Button';
import { SearchInput } from '../../components/common/Input';
import { cn } from '../../utils';

export const HelpPage: React.FC = () => {
  const [activeSection, setActiveSection] = useState<string>('gettingStarted');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredSections = Object.entries(HELP_SECTIONS).filter(([key, section]) => {
    if (!searchQuery) return true;
    const searchLower = searchQuery.toLowerCase();
    return (
      section.title.toLowerCase().includes(searchLower) ||
      section.items.some(item => item.toLowerCase().includes(searchLower))
    );
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Заголовок */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            ❓ Центр поддержки
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
            Найдите ответы на часто задаваемые вопросы или обратитесь в службу поддержки
          </p>

          {/* Поиск */}
          <div className="max-w-md mx-auto">
            <SearchInput
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск по справке..."
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Боковая навигация */}
          <div className="lg:col-span-1">
            <div className="card sticky top-8">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900">
                  📋 Разделы справки
                </h2>
              </div>
              <div className="card-body p-0">
                <nav className="space-y-1">
                  {filteredSections.map(([key, section]) => (
                    <button
                      key={key}
                      onClick={() => setActiveSection(key)}
                      className={cn(
                        'w-full flex items-center space-x-3 px-4 py-3 text-left transition-colors',
                        activeSection === key
                          ? 'bg-primary-50 border-r-2 border-primary-500 text-primary-700'
                          : 'hover:bg-gray-50 text-gray-700'
                      )}
                    >
                      <span className="text-xl">{section.icon}</span>
                      <span className="font-medium">{section.title}</span>
                    </button>
                  ))}
                </nav>
              </div>
            </div>

            {/* Контакты поддержки */}
            <div className="card mt-6">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900">
                  💬 Связаться с нами
                </h2>
              </div>
              <div className="card-body space-y-4">
                <Button
                  fullWidth
                  icon="📧"
                  variant="secondary"
                  onClick={() => {
                    window.open(`mailto:${process.env.REACT_APP_SUPPORT_EMAIL}`, '_blank');
                  }}
                >
                  Email поддержка
                </Button>

                <Button
                  fullWidth
                  icon="💬"
                  variant="secondary"
                  onClick={() => {
                    window.open(process.env.REACT_APP_TELEGRAM_BOT, '_blank');
                  }}
                >
                  Telegram бот
                </Button>
              </div>
            </div>
          </div>

          {/* Основной контент */}
          <div className="lg:col-span-3">
            {filteredSections.length === 0 ? (
              <div className="card text-center py-12">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Ничего не найдено
                </h3>
                <p className="text-gray-600">
                  Попробуйте изменить поисковый запрос или выберите раздел из меню
                </p>
              </div>
            ) : (
              <div className="space-y-8">
                {/* Активный раздел */}
                {filteredSections.map(([key, section]) => {
                  if (key !== activeSection && !searchQuery) return null;

                  return (
                    <HelpSection
                      key={key}
                      sectionKey={key}
                      section={section}
                      isExpanded={key === activeSection || !!searchQuery}
                    />
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Дополнительные ресурсы */}
        <div className="mt-16 card">
          <div className="card-header">
            <h2 className="text-2xl font-semibold text-gray-900">
              📚 Дополнительные ресурсы
            </h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-6 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-4xl mb-3">🎥</div>
                <h3 className="text-lg font-semibold text-blue-800 mb-2">
                  Видеоуроки
                </h3>
                <p className="text-blue-700 text-sm mb-4">
                  Пошаговые инструкции по использованию всех функций платформы
                </p>
                <SecondaryButton
                  size="sm"
                  onClick={() => {
                    console.log('Video tutorials coming soon');
                  }}
                >
                  Смотреть видео
                </SecondaryButton>
              </div>

              <div className="text-center p-6 bg-green-50 rounded-lg border border-green-200">
                <div className="text-4xl mb-3">📖</div>
                <h3 className="text-lg font-semibold text-green-800 mb-2">
                  База знаний
                </h3>
                <p className="text-green-700 text-sm mb-4">
                  Подробные статьи о стратегиях игры и анализе трендов
                </p>
                <SecondaryButton
                  size="sm"
                  onClick={() => {
                    console.log('Knowledge base coming soon');
                  }}
                >
                  Читать статьи
                </SecondaryButton>
              </div>

              <div className="text-center p-6 bg-purple-50 rounded-lg border border-purple-200">
                <div className="text-4xl mb-3">👥</div>
                <h3 className="text-lg font-semibold text-purple-800 mb-2">
                  Сообщество
                </h3>
                <p className="text-purple-700 text-sm mb-4">
                  Общайтесь с другими пользователями и делитесь опытом
                </p>
                <SecondaryButton
                  size="sm"
                  onClick={() => {
                    console.log('Community coming soon');
                  }}
                >
                  Присоединиться
                </SecondaryButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Компонент раздела справки
interface HelpSectionProps {
  sectionKey: string;
  section: {
    title: string;
    icon: string;
    items: readonly string[];
  };
  isExpanded: boolean;
}


const HelpSection: React.FC<HelpSectionProps> = ({ sectionKey, section, isExpanded }) => {
  if (!isExpanded) return null;

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">{section.icon}</span>
          <h2 className="text-xl font-semibold text-gray-900">
            {section.title}
          </h2>
        </div>
      </div>
      <div className="card-body">
        <div className="space-y-6">
          {section.items.map((item, index) => (
            <HelpItem
              key={index}
              title={item}
              sectionKey={sectionKey}
              itemIndex={index}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

// Компонент элемента справки
interface HelpItemProps {
  title: string;
  sectionKey: string;
  itemIndex: number;
}

const HelpItem: React.FC<HelpItemProps> = ({ title, sectionKey, itemIndex }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Получаем контент для каждого элемента
  const getContent = () => {
    const contentMap: Record<string, Record<number, { description: string; steps?: string[] }>> = {
      gettingStarted: {
        0: {
          description: "Как зарегистрироваться и начать пользоваться платформой",
          steps: [
            "Перейдите на страницу регистрации, нажав 'Зарегистрироваться'",
            "Введите email и пароль (минимум 6 символов)",
            "Укажите ваше полное имя для персонализации",
            "Войдите в систему и изучите главную панель управления"
          ]
        },
        1: {
          description: "Выбор подходящей лотереи для анализа",
          steps: [
            "В левом верхнем углу найдите селектор лотереи",
            "Доступны: Спортлото 4x20 и 5 из 36 плюс",
            "Выберите лотерею с наибольшим количеством исторических данных",
            "Система автоматически переключится на выбранную лотерею"
          ]
        },
        2: {
          description: "Создание первых комбинаций с помощью AI",
          steps: [
            "Перейдите в раздел 'Генерация' через боковое меню",
            "Выберите тип генератора: RF Ranked для лучших результатов",
            "Укажите количество комбинаций (рекомендуется начать с 3)",
            "Нажмите 'Сгенерировать' и дождитесь результата"
          ]
        },
        3: {
          description: "Как интерпретировать результаты генерации",
          steps: [
            "Изучите описание каждой комбинации и её оценку",
            "Обратите внимание на RF прогноз (помечен приоритетом)",
            "Сравните числа с текущими трендами в правой панели",
            "Добавьте лучшие комбинации в избранное для быстрого доступа"
          ]
        }
      },
      generation: {
        0: {
          description: "Различные алгоритмы генерации комбинаций",
          steps: [
            "RF Ranked - машинное обучение Random Forest (лучший выбор)",
            "Multi Strategy - комбинация нескольких алгоритмов",
            "Hot/Cold - генерация на основе частоты выпадения чисел",
            "Balanced - сбалансированное сочетание горячих и холодных чисел"
          ]
        },
        1: {
          description: "Настройка параметров для оптимальных результатов",
          steps: [
            "Количество комбинаций: 1-3 для начинающих, до 10 для опытных",
            "Тип генератора: RF Ranked для максимальной точности",
            "Изучайте превью трендов в левой панели",
            "Экспериментируйте с разными настройками для разных стратегий"
          ]
        },
        2: {
          description: "Анализ качества сгенерированных комбинаций",
          steps: [
            "RF оценка показывает качество от -∞ до +∞ (выше = лучше)",
            "Описание комбинации содержит информацию об алгоритме",
            "Используйте кнопку 'Оценить' для детального анализа",
            "Отслеживайте успешность ваших стратегий в статистике"
          ]
        },
        3: {
          description: "Управление избранными комбинациями",
          steps: [
            "Нажмите 'В избранное' под любой комбинацией",
            "Просматривайте сохраненные комбинации в профиле",
            "Копируйте комбинации в буфер обмена кнопкой 'Копировать'",
            "Регулярно очищайте старые комбинации"
          ]
        }
      },
      trends: {
        0: {
          description: "Понимание горячих и холодных чисел",
          steps: [
            "🔥 Горячие числа - часто выпадают в последних 10-20 тиражах",
            "❄️ Холодные числа - долго не выпадали, готовы к выходу",
            "Анализ охватывает разные временные периоды",
            "Учитывайте цикличность и не полагайтесь только на температуру"
          ]
        },
        1: {
          description: "Выявление повторяющихся паттернов",
          steps: [
            "Изучайте графики частот в разделе 'Тренды'",
            "Ищите сезонные и циклические изменения",
            "Анализируйте связи между числами разных полей",
            "Отслеживайте изменения силы трендов со временем"
          ]
        },
        2: {
          description: "Использование импульса чисел в прогнозах",
          steps: [
            "⚡ Импульс показывает ускорение частоты выпадения",
            "Комбинируйте импульсные числа с горячими и холодными",
            "Не используйте только импульс - это лишь один фактор",
            "Отслеживайте изменение силы тренда (0-1, где 1 максимум)"
          ]
        },
        3: {
          description: "Создание прогнозов на основе трендов",
          steps: [
            "Регулярно проверяйте актуальные тренды перед игрой",
            "Учитывайте уверенность системы в трендах (confidence)",
            "Комбинируйте анализ трендов с RF генерацией",
            "Ведите статистику успешности ваших прогнозов"
          ]
        }
      },
      subscription: {
        0: {
          description: "Сравнение доступных планов подписки",
          steps: [
            "🆓 Базовый: 20 генераций/день, история 6 месяцев",
            "⭐ Премиум: 100 генераций/день, полная история, кластерный анализ",
            "🚀 Профессиональный: безлимит, все функции, API доступ",
            "Все планы включают AI модели и анализ трендов"
          ]
        },
        1: {
          description: "Ограничения для каждого плана",
          steps: [
            "Генерации в день: базовый - 20, премиум - 100, про - безлимит",
            "Исторические данные: базовый - 180 дней, остальные - полная база",
            "Симуляции стратегий: базовый - 5, премиум - 25, про - безлимит",
            "Поддержка: email для всех, приоритетная для премиум и про"
          ]
        },
        2: {
          description: "Процесс активации подписки (демо-режим)",
          steps: [
            "Перейдите в раздел 'Подписки' через меню",
            "Выберите подходящий план из трех доступных",
            "Нажмите 'Выбрать план' или 'Демо-активация'",
            "Подтвердите активацию в появившемся диалоге"
          ]
        },
        3: {
          description: "Управление подпиской",
          steps: [
            "Текущий статус отображается в левом меню и профиле",
            "Меняйте планы в любое время через страницу подписок",
            "Отслеживайте использование лимитов в статистике",
            "Обращайтесь в поддержку при проблемах с подпиской"
          ]
        }
      }
    };

    return contentMap[sectionKey]?.[itemIndex] || {
      description: "Подробная информация по этому разделу находится в разработке.",
      steps: [
        "Обратитесь в службу поддержки для получения дополнительной информации",
        "Проверьте обновления - новый контент добавляется регулярно",
        "Изучите другие разделы справки для получения общего понимания системы"
      ]
    };
  };

  const content = getContent();

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
      >
        <span className="font-medium text-gray-900">{title}</span>
        <span className={cn(
          'transition-transform duration-200',
          isExpanded ? 'rotate-180' : 'rotate-0'
        )}>
          ▼
        </span>
      </button>

      {isExpanded && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <p className="text-gray-700 mb-4">{content.description}</p>

          {content.steps && (
            <div>
              <h4 className="font-medium text-gray-900 mb-3">📝 Пошаговая инструкция:</h4>
              <ol className="space-y-2">
                {content.steps.map((step, index) => (
                  <li key={index} className="flex items-start space-x-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-primary-100 text-primary-700 rounded-full text-sm font-medium flex items-center justify-center mt-0.5">
                      {index + 1}
                    </span>
                    <span className="text-gray-700 text-sm leading-relaxed">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div className="mt-6 pt-4 border-t border-gray-200 bg-blue-50 rounded-lg p-3">
            <div className="flex items-start space-x-2">
              <span className="text-blue-500 mt-0.5">💡</span>
              <div className="text-sm">
                <p className="text-blue-700 font-medium mb-1">Нужна дополнительная помощь?</p>
                <p className="text-blue-600">
                  Не нашли ответ на ваш вопрос? {' '}
                  <button
                    onClick={() => {
                      const subject = encodeURIComponent(`Вопрос по разделу: ${title}`);
                      const body = encodeURIComponent(`Здравствуйте!\n\nУ меня возник вопрос по разделу "${title}":\n\n[Опишите ваш вопрос здесь]\n\nС уважением`);
                      window.open(`mailto:${process.env.REACT_APP_SUPPORT_EMAIL}?subject=${subject}&body=${body}`, '_blank');
                    }}
                    className="text-primary-600 hover:underline font-medium"
                  >
                    Напишите нам
                  </button>
                  {' '}и мы поможем в течение 24 часов.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};