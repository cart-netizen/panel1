import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  CircularProgress,
  Alert,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Divider,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  LinearProgress,
  Tooltip,
  IconButton,
  Tabs,
  Tab,
  Badge
} from '@mui/material';
import {
  Casino,
  TrendingUp,
  TrendingDown,
  Assessment,
  Psychology,
  Info,
  Refresh,
  BarChart,
  PieChart,
  BubbleChart,
  Whatshot,
  AcUnit,
  CheckCircle,
  Error,
  PlayArrow
} from '@mui/icons-material';
import {
  BarChart as RechartsBarChart,
  Bar,
  LineChart,
  Line,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Scatter,
  ScatterChart,
  ZAxis
} from 'recharts';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useAuth, useSelectedLottery } from '../../store';

interface BayesianAnalysisProps {
  lotteryType: string;
}

interface Combination {
  field1: number[];
  field2: number[];
  confidence: number;
  method: string;
  strategy?: string;
  bayesian_info?: {
    posterior_strength: number;
    confidence_interval: [number, number];
    convergence_score: number;
  };
}

interface PosteriorData {
  number: number;
  posterior: number;
  cdm: number;
  combined: number;
  ci_lower: number;
  ci_upper: number;
}

interface HotColdAnalysis {
  hot_numbers: Array<{
    number: number;
    field: string;
    posterior_prob: number;
    frequency: number;
    bayesian_score: number;
  }>;
  cold_numbers: Array<{
    number: number;
    field: string;
    posterior_prob: number;
    frequency: number;
    bayesian_score: number;
  }>;
  analysis_summary: {
    hot_threshold: number;
    cold_threshold: number;
    analysis_period: number;
    confidence_level: number;
  };
}

interface SimulationResult {
  roi: number;
  total_cost: number;
  total_winnings: number;
  win_rate: number;
  simulated_draws: number;
  profit_distribution: Array<{
    draw: number;
    profit: number;
    cumulative_profit: number;
  }>;
  metrics: {
    sharpe_ratio: number;
    max_drawdown: number;
    volatility: number;
  };
}

interface ProbabilityAnalysis {
  field1_analysis: PosteriorData[];
  field2_analysis: PosteriorData[];
  convergence_metrics: {
    iterations: number;
    convergence_score: number;
    stability_index: number;
  };
  summary: {
    most_probable_field1: number[];
    most_probable_field2: number[];
    uncertainty_measure: number;
  };
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
      id={`bayesian-tabpanel-${index}`}
      aria-labelledby={`bayesian-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const BayesianAnalysis: React.FC<BayesianAnalysisProps> = ({ lotteryType }) => {
  const { user } = useAuth();
  const selectedLottery = useSelectedLottery();
  const [tabValue, setTabValue] = useState(0);
  const [numCombinations, setNumCombinations] = useState(5);
  const [simulationDraws, setSimulationDraws] = useState(100);
  const [analysisDepth, setAnalysisDepth] = useState(50);

  // Проверка премиум подписки
  const isPremium = user?.subscription_status === 'active';

  // Запрос состояния модели CDM
  const { data: modelStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['bayesian-status', selectedLottery],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/bayesian/status`);
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Мутация для обучения модели
  const trainMutation = useMutation({
    mutationFn: async (force: boolean = false) => {
      const response = await apiClient.post(
        `/${selectedLottery}/bayesian/train`,
        null,
        { params: { force } }
      );
      return response.data;
    },
    onSuccess: () => {
      refetchStatus();
    },
  });

  // Мутация для генерации комбинаций
  const generateMutation = useMutation({
    mutationFn: async (params: {
      num_combinations: number;
      strategy?: string;
    }) => {
      const response = await apiClient.get(`/${selectedLottery}/bayesian/generate`, {
        params
      });
      return response.data;
    },
  });

  // Запрос анализа вероятностей
  const { data: probabilityAnalysis, isLoading: probabilityLoading, refetch: refetchProbability } = useQuery({
    queryKey: ['bayesian-probability', selectedLottery, analysisDepth],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/bayesian/probability-analysis`, {
        params: { depth: analysisDepth }
      });
      return response.data;
    },
    enabled: isPremium && tabValue === 1,
    refetchInterval: 60000,
  });

  // Запрос анализа горячих/холодных чисел
  const { data: hotColdAnalysis, isLoading: hotColdLoading } = useQuery({
    queryKey: ['bayesian-hot-cold', selectedLottery],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/bayesian/hot-cold-analysis`);
      return response.data;
    },
    enabled: isPremium && tabValue === 2,
    refetchInterval: 60000,
  });

  // Мутация для симуляции
  const simulationMutation = useMutation({
    mutationFn: async (params: {
      num_draws: number;
      strategy: string;
      investment_per_draw: number;
    }) => {
      const response = await apiClient.post(`/${selectedLottery}/bayesian/simulate`, params);
      return response.data;
    },
  });

  // Обработчики
  const handleTrain = (force: boolean = false) => {
    trainMutation.mutate(force);
  };

  const handleGenerate = () => {
    generateMutation.mutate({
      num_combinations: numCombinations,
      strategy: 'bayesian_optimal'
    });
  };

  const handleSimulate = () => {
    simulationMutation.mutate({
      num_draws: simulationDraws,
      strategy: 'bayesian_optimal',
      investment_per_draw: 100, // Стандартная ставка
    });
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // Рендер постериорного распределения
  const renderPosteriorChart = (data: PosteriorData[]) => {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="number" />
          <YAxis />
          <RechartsTooltip
            formatter={(value: number, name: string) => [
              value.toFixed(4),
              name === 'posterior' ? 'Байесовская вероятность' :
              name === 'cdm' ? 'CDM оценка' : 'Комбинированная оценка'
            ]}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="posterior"
            stroke="#8884d8"
            strokeWidth={2}
            name="Байесовская вероятность"
          />
          <Line
            type="monotone"
            dataKey="cdm"
            stroke="#82ca9d"
            strokeWidth={2}
            name="CDM оценка"
          />
          <Line
            type="monotone"
            dataKey="combined"
            stroke="#ffc658"
            strokeWidth={2}
            name="Комбинированная"
          />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  if (!isPremium) {
    return (
      <Box p={3}>
        <Alert severity="warning">
          <Typography variant="h6" gutterBottom>
            🔒 Байесовский анализ - Премиум функция
          </Typography>
          <Typography>
            Для доступа к байесовскому анализу комбинаций и CDM модели необходима премиум подписка.
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
          🧠 Байесовский анализ (CDM модель)
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Продвинутый анализ с использованием сопряженной модели Дирихле-Мультиномиального распределения
        </Typography>
      </Box>

      {/* Статус модели */}
      <Box p={3}>
        <Card variant="outlined">
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
              <Typography variant="h6">📊 Статус CDM модели</Typography>
              <Button
                startIcon={<Refresh />}
                onClick={() => refetchStatus()}
                disabled={statusLoading}
                size="small"
              >
                Обновить
              </Button>
            </Box>

            {statusLoading ? (
              <Box display="flex" alignItems="center">
                <CircularProgress size={20} sx={{ mr: 2 }} />
                <Typography>Загрузка статуса...</Typography>
              </Box>
            ) : modelStatus ? (
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Typography variant="subtitle2" gutterBottom>Состояние обучения</Typography>
                    <Chip
                      icon={modelStatus.is_trained ? <CheckCircle /> : <Error />}
                      label={modelStatus.is_trained ? 'Обучена' : 'Не обучена'}
                      color={modelStatus.is_trained ? 'success' : 'error'}
                      size="small"
                    />
                    <Box mt={1}>
                      <Typography variant="caption" display="block">
                        Количество тиражей: {modelStatus.training_samples || 0}
                      </Typography>
                      <Typography variant="caption" display="block">
                        Последнее обновление: {modelStatus.last_updated ?
                          new Date(modelStatus.last_updated).toLocaleString() : 'Никогда'}
                      </Typography>
                    </Box>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Typography variant="subtitle2" gutterBottom>Качество модели</Typography>
                    <Box display="flex" alignItems="center" mb={1}>
                      <Typography variant="body2" sx={{ mr: 1 }}>
                        Сходимость: {((modelStatus.convergence_score || 0) * 100).toFixed(1)}%
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={(modelStatus.convergence_score || 0) * 100}
                        sx={{ flex: 1, ml: 1 }}
                      />
                    </Box>
                    <Typography variant="caption" display="block">
                      α-параметры: {modelStatus.alpha_sum?.toFixed(2) || 'N/A'}
                    </Typography>
                  </Paper>
                </Grid>

                <Grid item xs={12}>
                  <Box display="flex" gap={2}>
                    <Button
                      variant="contained"
                      startIcon={<PlayArrow />}
                      onClick={() => handleTrain(false)}
                      disabled={trainMutation.isPending}
                    >
                      {trainMutation.isPending ? 'Обучение...' : 'Обучить модель'}
                    </Button>

                    {modelStatus.is_trained && (
                      <Button
                        variant="outlined"
                        startIcon={<Refresh />}
                        onClick={() => handleTrain(true)}
                        disabled={trainMutation.isPending}
                      >
                        Переобучить
                      </Button>
                    )}
                  </Box>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="error">Ошибка загрузки статуса модели</Alert>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* Вкладки */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="bayesian analysis tabs">
          <Tab label="🎯 Генерация" />
          <Tab label="📈 Анализ вероятностей" />
          <Tab label="🔥 Горячие/Холодные" />
          <Tab label="🎲 Симуляция" />
        </Tabs>
      </Box>

      {/* Вкладка 1: Генерация комбинаций */}
      <TabPanel value={tabValue} index={0}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🎯 Генерация оптимальных комбинаций
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
            </Box>

            <Button
              variant="contained"
              size="large"
              startIcon={<Casino />}
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !modelStatus?.is_trained}
              fullWidth
            >
              {generateMutation.isPending ? 'Генерация...' : 'Сгенерировать комбинации'}
            </Button>

            {/* Результаты генерации */}
            {generateMutation.data && (
              <Box mt={3}>
                <Typography variant="h6" gutterBottom>📋 Результаты</Typography>
                <Grid container spacing={2}>
                  {generateMutation.data.combinations?.map((combo: Combination, index: number) => (
                    <Grid item xs={12} key={index}>
                      <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                          <Typography variant="subtitle1">
                            Комбинация #{index + 1}
                          </Typography>
                          <Chip
                            label={`${(combo.confidence * 100).toFixed(1)}% уверенности`}
                            color={combo.confidence > 0.7 ? 'success' : combo.confidence > 0.5 ? 'warning' : 'default'}
                            size="small"
                          />
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

                        {combo.bayesian_info && (
                          <Box mt={1}>
                            <Typography variant="caption" display="block">
                              Постериорная сила: {combo.bayesian_info.posterior_strength?.toFixed(3)}
                            </Typography>
                            <Typography variant="caption" display="block">
                              Доверительный интервал: [{combo.bayesian_info.confidence_interval?.[0]?.toFixed(3)}, {combo.bayesian_info.confidence_interval?.[1]?.toFixed(3)}]
                            </Typography>
                          </Box>
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

      {/* Вкладка 2: Анализ вероятностей */}
      <TabPanel value={tabValue} index={1}>
        <Card>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
              <Typography variant="h6">
                📈 Байесовский анализ вероятностей
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Typography variant="body2">Глубина анализа:</Typography>
                <Slider
                  value={analysisDepth}
                  onChange={(_, value) => setAnalysisDepth(value as number)}
                  min={20}
                  max={100}
                  step={10}
                  marks
                  sx={{ width: 150 }}
                />
                <Button
                  size="small"
                  startIcon={<Refresh />}
                  onClick={() => refetchProbability()}
                  disabled={probabilityLoading}
                >
                  Обновить
                </Button>
              </Box>
            </Box>

            {probabilityLoading ? (
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
              </Box>
            ) : probabilityAnalysis ? (
              <Grid container spacing={3}>
                {/* Сводка анализа */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
                    <Typography variant="subtitle1" gutterBottom>🎯 Рекомендуемые числа</Typography>
                    <Box display="flex" gap={2} mb={2}>
                      <Box>
                        <Typography variant="caption" display="block">Поле 1:</Typography>
                        <Box display="flex" gap={0.5}>
                          {probabilityAnalysis.summary?.most_probable_field1?.map((num: number) => (
                            <Chip key={num} label={num} size="small" color="primary" />
                          ))}
                        </Box>
                      </Box>
                      <Box>
                        <Typography variant="caption" display="block">Поле 2:</Typography>
                        <Box display="flex" gap={0.5}>
                          {probabilityAnalysis.summary?.most_probable_field2?.map((num: number) => (
                            <Chip key={num} label={num} size="small" color="secondary" />
                          ))}
                        </Box>
                      </Box>
                    </Box>
                    <Typography variant="caption">
                      Мера неопределенности: {probabilityAnalysis.summary?.uncertainty_measure?.toFixed(4)}
                    </Typography>
                  </Paper>
                </Grid>

                {/* График поля 1 */}
                <Grid item xs={12} lg={6}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>Поле 1 - Постериорное распределение</Typography>
                    {renderPosteriorChart(probabilityAnalysis.field1_analysis)}
                  </Paper>
                </Grid>

                {/* График поля 2 */}
                <Grid item xs={12} lg={6}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>Поле 2 - Постериорное распределение</Typography>
                    {renderPosteriorChart(probabilityAnalysis.field2_analysis)}
                  </Paper>
                </Grid>

                {/* Метрики сходимости */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>🔬 Метрики сходимости</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={4}>
                        <Box textAlign="center">
                          <Typography variant="h4" color="primary">
                            {probabilityAnalysis.convergence_metrics?.iterations}
                          </Typography>
                          <Typography variant="caption">Итераций</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <Box textAlign="center">
                          <Typography variant="h4" color="success.main">
                            {(probabilityAnalysis.convergence_metrics?.convergence_score * 100)?.toFixed(1)}%
                          </Typography>
                          <Typography variant="caption">Сходимость</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <Box textAlign="center">
                          <Typography variant="h4" color="warning.main">
                            {probabilityAnalysis.convergence_metrics?.stability_index?.toFixed(3)}
                          </Typography>
                          <Typography variant="caption">Стабильность</Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">
                Запустите анализ вероятностей для просмотра детальной статистики
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 3: Горячие/Холодные числа */}
      <TabPanel value={tabValue} index={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🔥 Байесовский анализ горячих и холодных чисел
            </Typography>

            {hotColdLoading ? (
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
              </Box>
            ) : hotColdAnalysis ? (
              <Grid container spacing={3}>
                {/* Сводка анализа */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Typography variant="subtitle1" gutterBottom>📊 Параметры анализа</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" display="block">Порог "горячих"</Typography>
                        <Typography variant="body2">{hotColdAnalysis.analysis_summary?.hot_threshold?.toFixed(3)}</Typography>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" display="block">Порог "холодных"</Typography>
                        <Typography variant="body2">{hotColdAnalysis.analysis_summary?.cold_threshold?.toFixed(3)}</Typography>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" display="block">Период анализа</Typography>
                        <Typography variant="body2">{hotColdAnalysis.analysis_summary?.analysis_period} тиражей</Typography>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" display="block">Уровень доверия</Typography>
                        <Typography variant="body2">{(hotColdAnalysis.analysis_summary?.confidence_level * 100)?.toFixed(1)}%</Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>

                {/* Горячие числа */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2 }}>
                    <Box display="flex" alignItems="center" mb={2}>
                      <Whatshot color="error" sx={{ mr: 1 }} />
                      <Typography variant="subtitle1">Горячие числа</Typography>
                    </Box>
                    <List dense>
                      {hotColdAnalysis.hot_numbers?.slice(0, 10).map((item: any, index: number) => (
                        <ListItem key={index} sx={{ px: 0 }}>
                          <ListItemIcon>
                            <Chip
                              label={item.number}
                              size="small"
                              color="error"
                              variant={item.field === 'field1' ? 'filled' : 'outlined'}
                            />
                          </ListItemIcon>
                          <ListItemText
                            primary={`Поле ${item.field === 'field1' ? '1' : '2'}`}
                            secondary={
                              <Box>
                                <Typography variant="caption" display="block">
                                  Байесовская оценка: {item.bayesian_score?.toFixed(3)}
                                </Typography>
                                <Typography variant="caption" display="block">
                                  Частота: {item.frequency} ({(item.posterior_prob * 100)?.toFixed(1)}%)
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Paper>
                </Grid>

                {/* Холодные числа */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2 }}>
                    <Box display="flex" alignItems="center" mb={2}>
                      <AcUnit color="info" sx={{ mr: 1 }} />
                      <Typography variant="subtitle1">Холодные числа</Typography>
                    </Box>
                    <List dense>
                      {hotColdAnalysis.cold_numbers?.slice(0, 10).map((item: any, index: number) => (
                        <ListItem key={index} sx={{ px: 0 }}>
                          <ListItemIcon>
                            <Chip
                              label={item.number}
                              size="small"
                              color="info"
                              variant={item.field === 'field1' ? 'filled' : 'outlined'}
                            />
                          </ListItemIcon>
                          <ListItemText
                            primary={`Поле ${item.field === 'field1' ? '1' : '2'}`}
                            secondary={
                              <Box>
                                <Typography variant="caption" display="block">
                                  Байесовская оценка: {item.bayesian_score?.toFixed(3)}
                                </Typography>
                                <Typography variant="caption" display="block">
                                  Частота: {item.frequency} ({(item.posterior_prob * 100)?.toFixed(1)}%)
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Paper>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">
                Загрузка анализа горячих и холодных чисел...
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 4: Симуляция */}
      <TabPanel value={tabValue} index={3}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🎲 Симуляция производительности стратегии
            </Typography>

            {/* Настройки симуляции */}
            <Box mb={3}>
              <Typography variant="subtitle2" gutterBottom>
                Количество тиражей для симуляции: {simulationDraws}
              </Typography>
              <Slider
                value={simulationDraws}
                onChange={(_, value) => setSimulationDraws(value as number)}
                min={50}
                max={500}
                step={50}
                marks
                sx={{ mb: 3 }}
              />

              <Button
                variant="contained"
                size="large"
                startIcon={<Assessment />}
                onClick={handleSimulate}
                disabled={simulationMutation.isPending || !modelStatus?.is_trained}
                fullWidth
              >
                {simulationMutation.isPending ? 'Выполнение симуляции...' : 'Запустить симуляцию'}
              </Button>
            </Box>

            {/* Результаты симуляции */}
            {simulationMutation.data && (
              <Box mt={3}>
                <Typography variant="h6" gutterBottom>📈 Результаты симуляции</Typography>

                {/* Основные метрики */}
                <Grid container spacing={2} mb={3}>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.light' }}>
                      <Typography variant="h4" color="success.contrastText">
                        {simulationMutation.data.roi?.toFixed(1)}%
                      </Typography>
                      <Typography variant="caption" color="success.contrastText">ROI</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'info.light' }}>
                      <Typography variant="h4" color="info.contrastText">
                        {simulationMutation.data.win_rate?.toFixed(1)}%
                      </Typography>
                      <Typography variant="caption" color="info.contrastText">Процент побед</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'warning.light' }}>
                      <Typography variant="h4" color="warning.contrastText">
                        {simulationMutation.data.total_winnings?.toLocaleString()}
                      </Typography>
                      <Typography variant="caption" color="warning.contrastText">Выигрыши</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'error.light' }}>
                      <Typography variant="h4" color="error.contrastText">
                        {simulationMutation.data.total_cost?.toLocaleString()}
                      </Typography>
                      <Typography variant="caption" color="error.contrastText">Затраты</Typography>
                    </Paper>
                  </Grid>
                </Grid>

                {/* График кумулятивной прибыли */}
                {simulationMutation.data.profit_distribution && (
                  <Paper sx={{ p: 2, mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>💰 Кумулятивная прибыль</Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={simulationMutation.data.profit_distribution}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="draw" />
                        <YAxis />
                        <RechartsTooltip />
                        <Line
                          type="monotone"
                          dataKey="cumulative_profit"
                          stroke="#8884d8"
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </Paper>
                )}

                {/* Дополнительные метрики */}
                {simulationMutation.data.metrics && (
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>📊 Дополнительные метрики</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={4}>
                        <Typography variant="caption" display="block">Коэффициент Шарпа</Typography>
                        <Typography variant="h6">{simulationMutation.data.metrics.sharpe_ratio?.toFixed(3)}</Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="caption" display="block">Максимальная просадка</Typography>
                        <Typography variant="h6" color="error">{simulationMutation.data.metrics.max_drawdown?.toFixed(1)}%</Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="caption" display="block">Волатильность</Typography>
                        <Typography variant="h6">{simulationMutation.data.metrics.volatility?.toFixed(3)}</Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                )}
              </Box>
            )}

            {simulationMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                Ошибка симуляции: {(simulationMutation.error as Error)?.message}
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  );
};

export default BayesianAnalysis;