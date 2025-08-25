import React, { useState, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Alert,
  LinearProgress,
  Chip,
  Paper,
  Tooltip,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemText,
  Divider,
  Tab,
  Tabs,
  CircularProgress,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  TrendingUp,
  Psychology,
  Insights,
  Speed,
  Info,
  ExpandMore,
  ExpandLess,
  AutoFixHigh,
  Timeline,
  School,
  Assessment,
  CheckCircle,
  Error,
  Warning
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useSelectedLottery, useAuth } from '../../store';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';

interface XGBoostPrediction {
  field1: number[];
  field2: number[];
  description: string;
}

interface SHAPExplanation {
  combination: {
    field1: number[];
    field2: number[];
  };
  score: number;
  explanations: {
    field1: any[];
    field2: any[];
  };
  top_factors: Array<{
    name: string;
    value: number;
    shap_value: number;
  }>;
  interpretation: string;
}

interface FeatureImportance {
  name: string;
  importance: number;
  description: string;
}

interface XGBoostMetrics {
  model_performance: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    auc_roc: number;
  };
  feature_importance: FeatureImportance[];
  model_info: {
    n_estimators: number;
    max_depth: number;
    learning_rate: number;
    last_trained: string;
    training_samples: number;
  };
  prediction_confidence: {
    avg_confidence: number;
    confidence_distribution: Array<{
      range: string;
      count: number;
    }>;
  };
}

interface HyperparameterTuning {
  best_params: {
    n_estimators: number;
    max_depth: number;
    learning_rate: number;
    subsample: number;
    colsample_bytree: number;
  };
  best_score: number;
  cv_results: Array<{
    params: any;
    mean_score: number;
    std_score: number;
  }>;
  tuning_time: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`xgboost-tabpanel-${index}`}
      aria-labelledby={`xgboost-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const XGBoostAnalysis: React.FC = () => {
  const selectedLottery = useSelectedLottery();
  const { user } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [selectedField, setSelectedField] = useState('field1');
  const [selectedNumber, setSelectedNumber] = useState(1);
  const [analyzedCombination, setAnalyzedCombination] = useState<{
    field1: number[];
    field2: number[];
  } | null>(null);
  const [numCombinations, setNumCombinations] = useState(5);
  const [autoTune, setAutoTune] = useState(false);

  // Проверка премиум подписки
  const isPremium = user?.subscription_status === 'active';

  // Запрос метрик XGBoost
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['xgboost-metrics', selectedLottery],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/xgboost/metrics`);
      return response.data;
    },
    refetchInterval: 60000,
  });

  // Мутация для генерации XGBoost комбинаций
  const generateMutation = useMutation({
    mutationFn: async (params: {
      num_combinations: number;
      num_candidates: number;
    }) => {
      const response = await apiClient.post(`/${selectedLottery}/xgboost/generate`, params);
      return response.data;
    },
  });

  // Мутация для объяснения комбинации
  const explainMutation = useMutation({
    mutationFn: async (combination: { field1: number[]; field2: number[] }) => {
      const response = await apiClient.post(`/${selectedLottery}/xgboost/explain`, combination);
      return response.data;
    },
  });

  // Мутация для обучения модели
  const trainMutation = useMutation({
    mutationFn: async (force: boolean) => {
      const response = await apiClient.post(
        `/${selectedLottery}/xgboost/train`,
        null,
        { params: { force } }
      );
      return response.data;
    },
  });

  // Мутация для тюнинга гиперпараметров
  const tuneMutation = useMutation({
    mutationFn: async (params: {
      cv_folds: number;
      n_iter: number;
      scoring: string;
    }) => {
      const response = await apiClient.post(`/${selectedLottery}/xgboost/tune`, params);
      return response.data;
    },
  });

  // Обработчики
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleGenerate = () => {
    generateMutation.mutate({
      num_combinations: numCombinations,
      num_candidates: numCombinations * 10
    });
  };

  const handleExplain = (combination: { field1: number[]; field2: number[] }) => {
    explainMutation.mutate(combination);
    setAnalyzedCombination(combination);
  };

  const handleTrain = (force: boolean = false) => {
    trainMutation.mutate(force);
  };

  const handleTune = () => {
    tuneMutation.mutate({
      cv_folds: 5,
      n_iter: 50,
      scoring: 'accuracy'
    });
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  // Форматирование чисел
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num?.toString() || '0';
  };

  // Рендер важности признаков
  const renderFeatureImportance = (features: FeatureImportance[]) => {
    const chartData = features?.slice(0, 15).map(f => ({
      name: f.name.length > 20 ? f.name.substring(0, 20) + '...' : f.name,
      importance: f.importance,
      fullName: f.name,
      description: f.description
    }));

    return (
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={chartData}
          layout="horizontal"
          margin={{ top: 20, right: 30, left: 100, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis dataKey="name" type="category" width={100} />
          <RechartsTooltip
            formatter={(value: number, name: string, props: any) => [
              value.toFixed(4),
              'Важность',
              props.payload.description
            ]}
            labelFormatter={(label: string, payload: any) =>
              payload?.[0]?.payload?.fullName || label
            }
          />
          <Bar dataKey="importance" fill="#8884d8" />
        </BarChart>
      </ResponsiveContainer>
    );
  };

  // Рендер SHAP объяснений
  const renderSHAPExplanation = (explanation: SHAPExplanation) => {
    return (
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 2, bgcolor: 'primary.light' }}>
            <Typography variant="h6" color="primary.contrastText" gutterBottom>
              🎯 Анализируемая комбинация
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              <Box>
                <Typography variant="caption" color="primary.contrastText">Поле 1:</Typography>
                <Box display="flex" gap={0.5} mt={0.5}>
                  {explanation.combination.field1?.map((num: number) => (
                    <Chip key={num} label={num} size="small" color="secondary" />
                  ))}
                </Box>
              </Box>
              <Typography variant="h6" color="primary.contrastText">+</Typography>
              <Box>
                <Typography variant="caption" color="primary.contrastText">Поле 2:</Typography>
                <Box display="flex" gap={0.5} mt={0.5}>
                  {explanation.combination.field2?.map((num: number) => (
                    <Chip key={num} label={num} size="small" color="secondary" />
                  ))}
                </Box>
              </Box>
            </Box>
            <Typography variant="h4" color="primary.contrastText" sx={{ mt: 2 }}>
              Оценка: {explanation.score?.toFixed(2)}/100
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>🔍 Топ факторы влияния</Typography>
            <List>
              {explanation.top_factors?.slice(0, 10).map((factor, index) => (
                <ListItem key={index} sx={{ px: 0 }}>
                  <ListItemText
                    primary={factor.name}
                    secondary={
                      <Box>
                        <Typography variant="caption" display="block">
                          Значение: {factor.value?.toFixed(3)}
                        </Typography>
                        <Typography variant="caption" display="block">
                          SHAP вклад: {factor.shap_value?.toFixed(4)}
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={Math.abs(factor.shap_value) * 100}
                          color={factor.shap_value > 0 ? 'success' : 'error'}
                          sx={{ mt: 1 }}
                        />
                      </Box>
                    }
                  />
                  <Chip
                    label={factor.shap_value > 0 ? '+' : '-'}
                    size="small"
                    color={factor.shap_value > 0 ? 'success' : 'error'}
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 2, bgcolor: 'info.light' }}>
            <Typography variant="h6" color="info.contrastText" gutterBottom>
              💡 Интерпретация
            </Typography>
            <Typography variant="body2" color="info.contrastText">
              {explanation.interpretation}
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    );
  };

  if (!isPremium) {
    return (
      <Box p={3}>
        <Alert severity="warning">
          <Typography variant="h6" gutterBottom>
            🔒 XGBoost анализ - Премиум функция
          </Typography>
          <Typography>
            Для доступа к XGBoost моделированию и SHAP объяснениям необходима премиум подписка.
          </Typography>
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Заголовок */}
      <Box p={3} borderBottom={1} borderColor="divider">
        <Typography variant="h5" gutterBottom>
          🚀 XGBoost с SHAP интерпретируемостью
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Продвинутое машинное обучение с объяснимыми предсказаниями
        </Typography>
      </Box>

      {/* Статус модели */}
      <Box p={3}>
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>📊 Статус XGBoost модели</Typography>

            {metricsLoading ? (
              <Box display="flex" alignItems="center">
                <CircularProgress size={20} sx={{ mr: 2 }} />
                <Typography>Загрузка метрик...</Typography>
              </Box>
            ) : metrics ? (
              <Grid container spacing={3}>
                {/* Производительность модели */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Typography variant="subtitle2" gutterBottom>🎯 Производительность</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Точность</Typography>
                        <Typography variant="h6">{(metrics.model_performance?.accuracy * 100)?.toFixed(1)}%</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">F1-Score</Typography>
                        <Typography variant="h6">{(metrics.model_performance?.f1_score * 100)?.toFixed(1)}%</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Precision</Typography>
                        <Typography variant="h6">{(metrics.model_performance?.precision * 100)?.toFixed(1)}%</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">AUC-ROC</Typography>
                        <Typography variant="h6">{metrics.model_performance?.auc_roc?.toFixed(3)}</Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>

                {/* Информация о модели */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Typography variant="subtitle2" gutterBottom>⚙️ Параметры модели</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Деревья</Typography>
                        <Typography variant="h6">{metrics.model_info?.n_estimators}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Глубина</Typography>
                        <Typography variant="h6">{metrics.model_info?.max_depth}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Learning Rate</Typography>
                        <Typography variant="h6">{metrics.model_info?.learning_rate}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Выборка</Typography>
                        <Typography variant="h6">{formatNumber(metrics.model_info?.training_samples)}</Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>

                {/* Уверенность предсказаний */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 2, bgcolor: 'success.light' }}>
                    <Typography variant="subtitle2" gutterBottom color="success.contrastText">
                      📈 Уверенность предсказаний
                    </Typography>
                    <Typography variant="h4" color="success.contrastText">
                      {(metrics.prediction_confidence?.avg_confidence * 100)?.toFixed(1)}%
                    </Typography>
                    <Typography variant="caption" color="success.contrastText">
                      Средняя уверенность модели в своих предсказаниях
                    </Typography>
                  </Paper>
                </Grid>

                {/* Кнопки управления */}
                <Grid item xs={12}>
                  <Box display="flex" gap={2}>
                    <Button
                      variant="contained"
                      startIcon={<School />}
                      onClick={() => handleTrain(false)}
                      disabled={trainMutation.isPending}
                    >
                      {trainMutation.isPending ? 'Обучение...' : 'Обучить модель'}
                    </Button>

                    <Button
                      variant="outlined"
                      startIcon={<AutoFixHigh />}
                      onClick={handleTune}
                      disabled={tuneMutation.isPending}
                    >
                      {tuneMutation.isPending ? 'Тюнинг...' : 'Тюнинг параметров'}
                    </Button>

                    <Button
                      variant="outlined"
                      startIcon={<School />}
                      onClick={() => handleTrain(true)}
                      disabled={trainMutation.isPending}
                    >
                      Переобучить
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="warning">
                Модель XGBoost не обучена. Запустите обучение для начала работы.
              </Alert>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* Вкладки */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="xgboost analysis tabs">
          <Tab label="🎯 Генерация" />
          <Tab label="🔍 Интерпретируемость" />
          <Tab label="📊 Важность признаков" />
          <Tab label="⚙️ Тюнинг" />
        </Tabs>
      </Box>

      {/* Вкладка 1: Генерация комбинаций */}
      <TabPanel value={tabValue} index={0}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🎯 Генерация комбинаций с XGBoost
            </Typography>

            {/* Настройки генерации */}
            <Box mb={3}>
              <Typography variant="subtitle2" gutterBottom>
                Количество комбинаций: {numCombinations}
              </Typography>
              <Slider
                value={numCombinations}
                onChange={(_, value) => setNumCombinations(value as number)}
                min={1}
                max={20}
                marks
                step={1}
                sx={{ mb: 2 }}
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={autoTune}
                    onChange={(e) => setAutoTune(e.target.checked)}
                  />
                }
                label="Автоматический тюнинг параметров"
              />
            </Box>

            <Button
              variant="contained"
              size="large"
              startIcon={<TrendingUp />}
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !metrics?.model_info}
              fullWidth
            >
              {generateMutation.isPending ? 'Генерация...' : 'Сгенерировать комбинации'}
            </Button>

            {/* Результаты генерации */}
            {generateMutation.data?.combinations && (
              <Box mt={3}>
                <Typography variant="h6" gutterBottom>📋 XGBoost комбинации</Typography>
                <Grid container spacing={2}>
                  {generateMutation.data.combinations.map((combo: any, index: number) => (
                    <Grid item xs={12} key={index}>
                      <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                          <Typography variant="subtitle1">
                            Комбинация #{index + 1}
                          </Typography>
                          <Box display="flex" gap={1}>
                            <Chip
                              label={`Оценка: ${combo.score?.toFixed(1)}`}
                              color={combo.score > 80 ? 'success' : combo.score > 60 ? 'warning' : 'default'}
                              size="small"
                            />
                            <Button
                              size="small"
                              startIcon={<Psychology />}
                              onClick={() => handleExplain(combo)}
                              disabled={explainMutation.isPending}
                            >
                              Объяснить
                            </Button>
                          </Box>
                        </Box>

                        <Box display="flex" alignItems="center" gap={2} mb={1}>
                          <Box>
                            <Typography variant="caption" display="block">Поле 1:</Typography>
                            <Box display="flex" gap={0.5}>
                              {combo.field1?.map((num: number) => (
                                <Chip
                                  key={num}
                                  label={num}
                                  size="small"
                                  color="primary"
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </Box>

                          <Typography variant="h6">+</Typography>

                          <Box>
                            <Typography variant="caption" display="block">Поле 2:</Typography>
                            <Box display="flex" gap={0.5}>
                              {combo.field2?.map((num: number) => (
                                <Chip
                                  key={num}
                                  label={num}
                                  size="small"
                                  color="secondary"
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </Box>
                        </Box>

                        {combo.description && (
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            {combo.description}
                          </Typography>
                        )}
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            )}

            {generateMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                Ошибка генерации: {(generateMutation.error as Error)?.message}
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 2: SHAP объяснения */}
      <TabPanel value={tabValue} index={1}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🔍 SHAP интерпретируемость
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Детальное объяснение того, как модель принимает решения
            </Typography>

            {explainMutation.data ? (
              renderSHAPExplanation(explainMutation.data)
            ) : (
              <Alert severity="info">
                Выберите комбинацию на вкладке "Генерация" и нажмите "Объяснить" для получения SHAP анализа
              </Alert>
            )}

            {explainMutation.isPending && (
              <Box display="flex" alignItems="center" justifyContent="center" p={4}>
                <CircularProgress sx={{ mr: 2 }} />
                <Typography>Анализ SHAP значений...</Typography>
              </Box>
            )}

            {explainMutation.isError && (
              <Alert severity="error">
                Ошибка объяснения: {(explainMutation.error as Error)?.message}
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 3: Важность признаков */}
      <TabPanel value={tabValue} index={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📊 Важность признаков
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Анализ того, какие признаки наиболее важны для модели XGBoost
            </Typography>

            {metrics?.feature_importance ? (
              <Box>
                <Paper sx={{ p: 2, mb: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    🎯 Топ-15 наиболее важных признаков
                  </Typography>
                  {renderFeatureImportance(metrics.feature_importance)}
                </Paper>

                {/* Детальная таблица */}
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    📋 Детальная информация
                  </Typography>
                  <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
                    <List>
                      {metrics.feature_importance.slice(0, 20).map((feature: FeatureImportance, index: number) => (
                        <ListItem key={index} sx={{ px: 0 }}>
                          <ListItemText
                            primary={feature.name}
                            secondary={
                              <Box>
                                <Typography variant="caption" display="block">
                                  Важность: {feature.importance?.toFixed(4)}
                                </Typography>
                                <Typography variant="caption" display="block" color="text.secondary">
                                  {feature.description}
                                </Typography>
                                <LinearProgress
                                  variant="determinate"
                                  value={(feature.importance / metrics.feature_importance[0].importance) * 100}
                                  sx={{ mt: 1 }}
                                />
                              </Box>
                            }
                          />
                          <Chip
                            label={`#${index + 1}`}
                            size="small"
                            color={index < 5 ? 'primary' : index < 10 ? 'secondary' : 'default'}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                </Paper>
              </Box>
            ) : (
              <Alert severity="info">
                Важность признаков будет доступна после обучения модели XGBoost
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 4: Тюнинг гиперпараметров */}
      <TabPanel value={tabValue} index={3}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              ⚙️ Тюнинг гиперпараметров
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Автоматический поиск оптимальных параметров для максимальной производительности
            </Typography>

            {/* Кнопка запуска тюнинга */}
            <Button
              variant="contained"
              size="large"
              startIcon={<AutoFixHigh />}
              onClick={handleTune}
              disabled={tuneMutation.isPending}
              fullWidth
              sx={{ mb: 3 }}
            >
              {tuneMutation.isPending ? 'Выполнение тюнинга...' : 'Запустить автоматический тюнинг'}
            </Button>

            {tuneMutation.isPending && (
              <Box>
                <Typography variant="body2" gutterBottom>Поиск оптимальных параметров...</Typography>
                <LinearProgress />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Это может занять несколько минут
                </Typography>
              </Box>
            )}

            {/* Результаты тюнинга */}
            {tuneMutation.data && (
              <Box mt={3}>
                <Typography variant="h6" gutterBottom>🏆 Результаты тюнинга</Typography>

                {/* Лучшие параметры */}
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'success.light' }}>
                  <Typography variant="subtitle1" gutterBottom color="success.contrastText">
                    🎯 Оптимальные параметры
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="success.contrastText">N Estimators</Typography>
                      <Typography variant="h6" color="success.contrastText">
                        {tuneMutation.data.best_params?.n_estimators}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="success.contrastText">Max Depth</Typography>
                      <Typography variant="h6" color="success.contrastText">
                        {tuneMutation.data.best_params?.max_depth}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="success.contrastText">Learning Rate</Typography>
                      <Typography variant="h6" color="success.contrastText">
                        {tuneMutation.data.best_params?.learning_rate?.toFixed(3)}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="caption" color="success.contrastText">Лучший результат</Typography>
                      <Typography variant="h6" color="success.contrastText">
                        {(tuneMutation.data.best_score * 100)?.toFixed(1)}%
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>

                {/* История поиска */}
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>📈 История поиска</Typography>
                  <Typography variant="caption" display="block" sx={{ mb: 2 }}>
                    Время тюнинга: {tuneMutation.data.tuning_time?.toFixed(1)} секунд
                  </Typography>

                  {tuneMutation.data.cv_results?.length > 0 && (
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      <List dense>
                        {tuneMutation.data.cv_results
                          .sort((a: any, b: any) => b.mean_score - a.mean_score)
                          .slice(0, 10)
                          .map((result: any, index: number) => (
                          <ListItem key={index} sx={{ px: 0 }}>
                            <ListItemText
                              primary={`Конфигурация #${index + 1}`}
                              secondary={
                                <Box>
                                  <Typography variant="caption" display="block">
                                    Оценка: {(result.mean_score * 100).toFixed(2)}% (±{(result.std_score * 100).toFixed(2)}%)
                                  </Typography>
                                  <Typography variant="caption" display="block" color="text.secondary">
                                    {Object.entries(result.params).map(([key, value]: [string, any]) =>
                                      `${key}: ${value}`
                                    ).join(', ')}
                                  </Typography>
                                </Box>
                              }
                            />
                            {index === 0 && <Chip label="Лучший" size="small" color="success" />}
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  )}
                </Paper>
              </Box>
            )}

            {tuneMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                Ошибка тюнинга: {(tuneMutation.error as Error)?.message}
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Результаты обучения */}
      {trainMutation.data && (
        <Box p={3}>
          <Alert severity="success">
            <Typography variant="subtitle2" gutterBottom>
              ✅ Модель успешно обучена!
            </Typography>
            <Typography variant="body2">
              Новые метрики: Точность {(trainMutation.data.accuracy * 100).toFixed(1)}%,
              F1-Score {(trainMutation.data.f1_score * 100).toFixed(1)}%
            </Typography>
          </Alert>
        </Box>
      )}

      {trainMutation.isError && (
        <Box p={3}>
          <Alert severity="error">
            Ошибка обучения: {(trainMutation.error as Error)?.message}
          </Alert>
        </Box>
      )}
    </Box>
  );
};

export default XGBoostAnalysis;