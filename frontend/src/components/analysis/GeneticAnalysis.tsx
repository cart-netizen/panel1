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
  Badge,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Psychology,
  Timeline,
  PlayArrow,
  Stop,
  Refresh,
  Assessment,
  TrendingUp,
  Speed,
  School,
  Info,
  CheckCircle,
  Error,
  Warning
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart
} from 'recharts';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useAuth, useSelectedLottery } from '../../store';

interface GeneticAnalysisProps {
  lotteryType: string;
}

interface GeneticParams {
  population_size: number;
  generations: number;
  elite_size: number;
  mutation_rate: number;
  crossover_rate: number;
  tournament_size: number;
  diversity_threshold: number;
}

interface EvolutionTask {
  task_id: string;
  status: 'started' | 'running' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  current_generation?: number;
  best_fitness?: number;
  results?: {
    best_combinations: Array<{
      field1: number[];
      field2: number[];
      fitness: number;
      generation: number;
    }>;
    evolution_history: Array<{
      generation: number;
      best_fitness: number;
      avg_fitness: number;
      diversity: number;
    }>;
    final_statistics: {
      total_generations: number;
      convergence_generation: number;
      improvement_rate: number;
      diversity_maintained: boolean;
    };
  };
}

interface EvolutionStatistics {
  last_evolution: {
    timestamp: string;
    total_generations: number;
    best_fitness: number;
    convergence_generation: number;
    population_diversity: number;
  };
  historical_performance: Array<{
    run_id: string;
    timestamp: string;
    best_fitness: number;
    generations: number;
  }>;
  parameter_optimization: {
    optimal_population_size: number;
    optimal_mutation_rate: number;
    optimal_crossover_rate: number;
  };
}

interface Combination {
  field1: number[];
  field2: number[];
  fitness: number;
  confidence: number;
  method: string;
  genetic_info?: {
    generation: number;
    parent_fitness: number[];
    mutation_applied: boolean;
    crossover_applied: boolean;
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
      id={`genetic-tabpanel-${index}`}
      aria-labelledby={`genetic-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const GeneticAnalysis: React.FC<GeneticAnalysisProps> = ({ lotteryType }) => {
  const { user } = useAuth();
  const selectedLottery = useSelectedLottery();
  const [tabValue, setTabValue] = useState(0);
  const [currentTask, setCurrentTask] = useState<string | null>(null);
  const [geneticParams, setGeneticParams] = useState<GeneticParams>({
    population_size: 50,
    generations: 30,
    elite_size: 10,
    mutation_rate: 0.1,
    crossover_rate: 0.8,
    tournament_size: 5,
    diversity_threshold: 0.7
  });


  // Проверка премиум подписки
  const isPremium = user?.subscription_status === 'active';

  // Запрос статистики генетического алгоритма
  const { data: statistics, isLoading: statisticsLoading, refetch: refetchStatistics } = useQuery({
    queryKey: ['genetic-statistics', selectedLottery],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/genetic/statistics`);
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Мутация для быстрой генерации
  const generateMutation = useMutation({
    mutationFn: async (params: { num_combinations: number }) => {
      const response = await apiClient.post(`/${selectedLottery}/genetic/generate`, params);
      return response.data;
    },
  });

  // Мутация для запуска эволюции
  const evolveMutation = useMutation({
    mutationFn: async (params: GeneticParams) => {
      const response = await apiClient.post(`/${selectedLottery}/genetic/evolve`, params);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.task_id) {
        setCurrentTask(data.task_id);
      }
    },
  });

  // Мутация для предсказания
  const predictMutation = useMutation({
    mutationFn: async (combination: { field1: number[]; field2: number[] }) => {
      const response = await apiClient.post(`/${selectedLottery}/genetic/predict`, combination);
      return response.data;
    },
  });

  // Состояние для контроля polling
  const [isPolling, setIsPolling] = useState(false);

  // Запрос статуса эволюции
  const { data: taskStatus, isLoading: taskLoading } = useQuery({
    queryKey: ['genetic-task-status', currentTask],
    queryFn: async () => {
      if (!currentTask) return null;
      const response = await apiClient.get(`/${selectedLottery}/genetic/evolution/status/${currentTask}`);
      return response.data;
    },
    enabled: !!currentTask,
    refetchInterval: isPolling ? 2000 : false,
  });

  // Эффект для отслеживания завершения задачи
  useEffect(() => {
    if (taskStatus?.status === 'completed' || taskStatus?.status === 'failed') {
      refetchStatistics();
      if (taskStatus?.status === 'completed') {
        // Сбрасываем текущую задачу через некоторое время для показа результатов
        setTimeout(() => {
          setCurrentTask(null);
        }, 5000);
      }
    }
  }, [taskStatus, refetchStatistics]);

  // Обработчики
  const handleGenerate = (numCombinations: number = 5) => {
    generateMutation.mutate({ num_combinations: numCombinations });
  };

  const handleEvolve = () => {
    evolveMutation.mutate(geneticParams);
  };

  const handlePredict = (combination: { field1: number[]; field2: number[] }) => {
    predictMutation.mutate(combination);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleParamChange = (param: keyof GeneticParams, value: number) => {
    setGeneticParams(prev => ({
      ...prev,
      [param]: value
    }));
  };

  // Рендер графика эволюции
  const renderEvolutionChart = (history: any[]) => {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={history}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="generation" />
          <YAxis />
          <RechartsTooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="best_fitness"
            stroke="#8884d8"
            strokeWidth={2}
            name="Лучший фитнес"
          />
          <Line
            type="monotone"
            dataKey="avg_fitness"
            stroke="#82ca9d"
            strokeWidth={2}
            name="Средний фитнес"
          />
          <Line
            type="monotone"
            dataKey="diversity"
            stroke="#ffc658"
            strokeWidth={2}
            name="Разнообразие"
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
            🔒 Генетический алгоритм - Премиум функция
          </Typography>
          <Typography>
            Для доступа к генетической оптимизации комбинаций необходима премиум подписка.
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
          🧬 Генетический алгоритм
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Эволюционная оптимизация комбинаций с адаптивными параметрами
        </Typography>
      </Box>

      {/* Статус текущей эволюции */}
      {currentTask && (
        <Box p={3}>
          <Alert
            severity={
              taskStatus?.status === 'completed' ? 'success' :
              taskStatus?.status === 'failed' ? 'error' : 'info'
            }
            action={
              taskStatus?.status === 'running' && (
                <IconButton
                  aria-label="close"
                  color="inherit"
                  size="small"
                  onClick={() => setCurrentTask(null)}
                >
                  <Stop />
                </IconButton>
              )
            }
          >
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                {taskStatus?.status === 'completed' ? '✅ Эволюция завершена' :
                 taskStatus?.status === 'failed' ? '❌ Ошибка эволюции' :
                 taskStatus?.status === 'running' ? '🧬 Эволюция в процессе...' : '🚀 Эволюция запущена'}
              </Typography>

              {taskStatus?.message && (
                <Typography variant="body2" gutterBottom>
                  {taskStatus.message}
                </Typography>
              )}

              {taskStatus?.status === 'running' && (
                <Box>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="caption">
                      Поколение: {taskStatus.current_generation || 0} / {geneticParams.generations}
                    </Typography>
                    <Typography variant="caption">
                      Лучший фитнес: {taskStatus.best_fitness?.toFixed(4) || 'N/A'}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={((taskStatus.current_generation || 0) / geneticParams.generations) * 100}
                  />
                </Box>
              )}
            </Box>
          </Alert>
        </Box>
      )}

      {/* Вкладки */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="genetic analysis tabs">
          <Tab label="🎯 Генерация" />
          <Tab label="⚙️ Эволюция" />
          <Tab label="🔮 Предсказание" />
          <Tab label="📊 Статистика" />
        </Tabs>
      </Box>

      {/* Вкладка 1: Быстрая генерация */}
      <TabPanel value={tabValue} index={0}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🎯 Быстрая генерация комбинаций
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Генерация комбинаций на основе последней обученной популяции
            </Typography>

            <Box display="flex" gap={2} mb={3}>
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={() => handleGenerate(3)}
                disabled={generateMutation.isPending}
              >
                3 комбинации
              </Button>
              <Button
                variant="outlined"
                startIcon={<PlayArrow />}
                onClick={() => handleGenerate(5)}
                disabled={generateMutation.isPending}
              >
                5 комбинаций
              </Button>
              <Button
                variant="outlined"
                startIcon={<PlayArrow />}
                onClick={() => handleGenerate(10)}
                disabled={generateMutation.isPending}
              >
                10 комбинаций
              </Button>
            </Box>

            {generateMutation.isPending && (
              <Box display="flex" alignItems="center" mb={2}>
                <CircularProgress size={20} sx={{ mr: 2 }} />
                <Typography variant="body2">Генерация комбинаций...</Typography>
              </Box>
            )}

            {/* Результаты генерации */}
            {generateMutation.data?.combinations && (
              <Box mt={3}>
                <Typography variant="h6" gutterBottom>📋 Сгенерированные комбинации</Typography>
                <Grid container spacing={2}>
                  {generateMutation.data.combinations.map((combo: Combination, index: number) => (
                    <Grid item xs={12} key={index}>
                      <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                          <Typography variant="subtitle1">
                            Комбинация #{index + 1}
                          </Typography>
                          <Box display="flex" gap={1}>
                            <Chip
                              label={`Фитнес: ${combo.fitness?.toFixed(4)}`}
                              size="small"
                              color="primary"
                            />
                            <Chip
                              label={`${(combo.confidence * 100).toFixed(1)}%`}
                              size="small"
                              color={combo.confidence > 0.7 ? 'success' : 'warning'}
                            />
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

                        {combo.genetic_info && (
                          <Box mt={1}>
                            <Typography variant="caption" display="block">
                              Поколение: {combo.genetic_info.generation}
                            </Typography>
                            <Typography variant="caption" display="block">
                              Мутация: {combo.genetic_info.mutation_applied ? 'Да' : 'Нет'},
                              Кроссовер: {combo.genetic_info.crossover_applied ? 'Да' : 'Нет'}
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

      {/* Вкладка 2: Настройка эволюции */}
      <TabPanel value={tabValue} index={1}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              ⚙️ Настройка и запуск эволюции
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Настройте параметры генетического алгоритма для оптимальной эволюции
            </Typography>

            {/* Параметры эволюции */}
            <Grid container spacing={3} mb={4}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Размер популяции: {geneticParams.population_size}
                </Typography>
                <Slider
                  value={geneticParams.population_size}
                  onChange={(_, value) => handleParamChange('population_size', value as number)}
                  min={20}
                  max={200}
                  step={10}
                  marks={[
                    { value: 20, label: '20' },
                    { value: 50, label: '50' },
                    { value: 100, label: '100' },
                    { value: 200, label: '200' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Количество поколений: {geneticParams.generations}
                </Typography>
                <Slider
                  value={geneticParams.generations}
                  onChange={(_, value) => handleParamChange('generations', value as number)}
                  min={10}
                  max={100}
                  step={5}
                  marks={[
                    { value: 10, label: '10' },
                    { value: 30, label: '30' },
                    { value: 50, label: '50' },
                    { value: 100, label: '100' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Коэффициент мутации: {geneticParams.mutation_rate.toFixed(2)}
                </Typography>
                <Slider
                  value={geneticParams.mutation_rate}
                  onChange={(_, value) => handleParamChange('mutation_rate', value as number)}
                  min={0.01}
                  max={0.5}
                  step={0.01}
                  marks={[
                    { value: 0.01, label: '1%' },
                    { value: 0.1, label: '10%' },
                    { value: 0.25, label: '25%' },
                    { value: 0.5, label: '50%' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Коэффициент кроссовера: {geneticParams.crossover_rate.toFixed(2)}
                </Typography>
                <Slider
                  value={geneticParams.crossover_rate}
                  onChange={(_, value) => handleParamChange('crossover_rate', value as number)}
                  min={0.5}
                  max={1.0}
                  step={0.05}
                  marks={[
                    { value: 0.5, label: '50%' },
                    { value: 0.7, label: '70%' },
                    { value: 0.8, label: '80%' },
                    { value: 1.0, label: '100%' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Размер элиты: {geneticParams.elite_size}
                </Typography>
                <Slider
                  value={geneticParams.elite_size}
                  onChange={(_, value) => handleParamChange('elite_size', value as number)}
                  min={2}
                  max={50}
                  step={2}
                  marks={[
                    { value: 2, label: '2' },
                    { value: 10, label: '10' },
                    { value: 25, label: '25' },
                    { value: 50, label: '50' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Порог разнообразия: {geneticParams.diversity_threshold.toFixed(2)}
                </Typography>
                <Slider
                  value={geneticParams.diversity_threshold}
                  onChange={(_, value) => handleParamChange('diversity_threshold', value as number)}
                  min={0.3}
                  max={0.9}
                  step={0.05}
                  marks={[
                    { value: 0.3, label: '30%' },
                    { value: 0.5, label: '50%' },
                    { value: 0.7, label: '70%' },
                    { value: 0.9, label: '90%' }
                  ]}
                />
              </Grid>
            </Grid>

            {/* Кнопка запуска */}
            <Button
              variant="contained"
              size="large"
              startIcon={<Psychology />}
              onClick={handleEvolve}
              disabled={evolveMutation.isPending || !!currentTask}
              fullWidth
            >
              {evolveMutation.isPending ? 'Запуск эволюции...' : 'Запустить эволюцию'}
            </Button>

            {/* Результаты эволюции */}
            {taskStatus?.results && (
              <Box mt={4}>
                <Typography variant="h6" gutterBottom>🏆 Результаты эволюции</Typography>

                {/* Лучшие комбинации */}
                <Paper sx={{ p: 2, mb: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>🥇 Лучшие комбинации</Typography>
                  <Grid container spacing={2}>
                    {taskStatus.results.best_combinations?.slice(0, 5).map((combo: any, index: number) => (
                      <Grid item xs={12} key={index}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" p={1}
                             bgcolor={index === 0 ? 'success.light' : 'background.default'}
                             borderRadius={1}>
                          <Box display="flex" alignItems="center" gap={2}>
                            <Box>
                              <Typography variant="caption" display="block">Поле 1:</Typography>
                              <Box display="flex" gap={0.5}>
                                {combo.field1?.map((num: number) => (
                                  <Chip key={num} label={num} size="small" color="primary" />
                                ))}
                              </Box>
                            </Box>
                            <Typography>+</Typography>
                            <Box>
                              <Typography variant="caption" display="block">Поле 2:</Typography>
                              <Box display="flex" gap={0.5}>
                                {combo.field2?.map((num: number) => (
                                  <Chip key={num} label={num} size="small" color="secondary" />
                                ))}
                              </Box>
                            </Box>
                          </Box>
                          <Box textAlign="right">
                            <Typography variant="caption" display="block">
                              Фитнес: {combo.fitness?.toFixed(4)}
                            </Typography>
                            <Typography variant="caption" display="block">
                              Поколение: {combo.generation}
                            </Typography>
                          </Box>
                        </Box>
                      </Grid>
                    ))}
                  </Grid>
                </Paper>

                {/* График эволюции */}
                {taskStatus.results.evolution_history && (
                  <Paper sx={{ p: 2, mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>📈 История эволюции</Typography>
                    {renderEvolutionChart(taskStatus.results.evolution_history)}
                  </Paper>
                )}

                {/* Финальная статистика */}
                {taskStatus.results.final_statistics && (
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>📊 Финальная статистика</Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" display="block">Всего поколений</Typography>
                        <Typography variant="h6">{taskStatus.results.final_statistics.total_generations}</Typography>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" display="block">Сходимость на поколении</Typography>
                        <Typography variant="h6">{taskStatus.results.final_statistics.convergence_generation}</Typography>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" display="block">Скорость улучшения</Typography>
                        <Typography variant="h6">{(taskStatus.results.final_statistics.improvement_rate * 100).toFixed(1)}%</Typography>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="caption" display="block">Разнообразие сохранено</Typography>
                        <Typography variant="h6">
                          {taskStatus.results.final_statistics.diversity_maintained ? '✅' : '❌'}
                        </Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                )}
              </Box>
            )}

            {evolveMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                Ошибка запуска эволюции: {(evolveMutation.error as Error)?.message}
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 3: Предсказание фитнеса */}
      <TabPanel value={tabValue} index={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🔮 Предсказание фитнеса комбинации
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Оцените качество любой комбинации с помощью обученной модели
            </Typography>

            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="body2">
                Введите комбинацию чисел для получения оценки фитнеса от генетического алгоритма
              </Typography>
            </Alert>

            {/* Форма ввода комбинации - здесь можно добавить поля ввода */}
            <Typography variant="body2" color="text.secondary">
              Форма ввода комбинации будет добавлена в следующем обновлении
            </Typography>

            {/* Результат предсказания */}
            {predictMutation.data && (
              <Paper sx={{ p: 2, mt: 2, bgcolor: 'success.light' }}>
                <Typography variant="subtitle1" gutterBottom>🎯 Результат оценки</Typography>
                <Typography variant="h4" color="success.contrastText">
                  Фитнес: {predictMutation.data.fitness?.toFixed(4)}
                </Typography>
                <Typography variant="body2" color="success.contrastText">
                  {predictMutation.data.interpretation}
                </Typography>
              </Paper>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 4: Статистика */}
      <TabPanel value={tabValue} index={3}>
        <Card>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
              <Typography variant="h6">
                📊 Статистика генетического алгоритма
              </Typography>
              <Button
                startIcon={<Refresh />}
                onClick={() => refetchStatistics()}
                disabled={statisticsLoading}
                size="small"
              >
                Обновить
              </Button>
            </Box>

            {statisticsLoading ? (
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
              </Box>
            ) : statistics ? (
              <Grid container spacing={3}>
                {/* Последняя эволюция */}
                {statistics.last_evolution && (
                  <Grid item xs={12}>
                    <Paper sx={{ p: 2, bgcolor: 'primary.light' }}>
                      <Typography variant="subtitle1" gutterBottom color="primary.contrastText">
                        🕒 Последняя эволюция
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" display="block" color="primary.contrastText">
                            Дата
                          </Typography>
                          <Typography variant="body2" color="primary.contrastText">
                            {new Date(statistics.last_evolution.timestamp).toLocaleString()}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" display="block" color="primary.contrastText">
                            Поколений
                          </Typography>
                          <Typography variant="body2" color="primary.contrastText">
                            {statistics.last_evolution.total_generations}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" display="block" color="primary.contrastText">
                            Лучший фитнес
                          </Typography>
                          <Typography variant="body2" color="primary.contrastText">
                            {statistics.last_evolution.best_fitness?.toFixed(4)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" display="block" color="primary.contrastText">
                            Разнообразие
                          </Typography>
                          <Typography variant="body2" color="primary.contrastText">
                            {(statistics.last_evolution.population_diversity * 100)?.toFixed(1)}%
                          </Typography>
                        </Grid>
                      </Grid>
                    </Paper>
                  </Grid>
                )}

                {/* Оптимальные параметры */}
                {statistics.parameter_optimization && (
                  <Grid item xs={12}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle1" gutterBottom>⚙️ Рекомендуемые параметры</Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={4}>
                          <Typography variant="caption" display="block">Размер популяции</Typography>
                          <Typography variant="h6">{statistics.parameter_optimization.optimal_population_size}</Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" display="block">Коэффициент мутации</Typography>
                          <Typography variant="h6">{(statistics.parameter_optimization.optimal_mutation_rate * 100).toFixed(1)}%</Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" display="block">Коэффициент кроссовера</Typography>
                          <Typography variant="h6">{(statistics.parameter_optimization.optimal_crossover_rate * 100).toFixed(1)}%</Typography>
                        </Grid>
                      </Grid>
                    </Paper>
                  </Grid>
                )}

                {/* История производительности */}
                {statistics.historical_performance && (
                  <Grid item xs={12}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle1" gutterBottom>📈 История производительности</Typography>
                      {statistics.historical_performance.length > 0 ? (
                        <List dense>
                          {statistics.historical_performance.slice(-10).map((run: any, index: number) => (
                            <ListItem key={index} sx={{ px: 0 }}>
                              <ListItemIcon>
                                <Assessment color="primary" />
                              </ListItemIcon>
                              <ListItemText
                                primary={`Фитнес: ${run.best_fitness?.toFixed(4)}`}
                                secondary={`${new Date(run.timestamp).toLocaleDateString()} - ${run.generations} поколений`}
                              />
                            </ListItem>
                          ))}
                        </List>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          История эволюций пока отсутствует
                        </Typography>
                      )}
                    </Paper>
                  </Grid>
                )}
              </Grid>
            ) : (
              <Alert severity="info">
                Статистика генетического алгоритма будет доступна после первого запуска эволюции
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  );
};

export default GeneticAnalysis;