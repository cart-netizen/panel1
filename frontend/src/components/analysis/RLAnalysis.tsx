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
  Slider,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Psychology,
  Speed,
  TrendingUp,
  PlayArrow,
  Refresh,
  Assessment,
  School,
  Info,
  CheckCircle,
  Error,
  Timeline,
  BarChart
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart as RechartsBarChart,
  Bar,
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
  Radar
} from 'recharts';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useAuth, useSelectedLottery } from '../../store';

interface RLAnalysisProps {
  lotteryType: string;
}

interface RLParameters {
  q_episodes: number;
  dqn_episodes: number;
  window_size: number;
  learning_rate: number;
  discount_factor: number;
  epsilon: number;
  batch_size: number;
}

interface AgentStatus {
  q_agent: {
    trained: boolean;
    episodes: number;
    win_rate: number;
    avg_reward: number;
    q_table_size: number;
    memory_usage: number;
  };
  dqn_agent: {
    trained: boolean;
    episodes: number;
    win_rate: number;
    avg_reward: number;
    network_layers: number;
    total_parameters: number;
  };
  environment: {
    state_size: number;
    action_size: number;
    reward_scheme: string;
    last_updated: string;
  };
}

interface RLCombination {
  field1: number[];
  field2: number[];
  confidence: number;
  method: string;
  rl_info?: {
    q_value: number;
    state_features: number[];
    action_probability: number;
    exploration_factor: number;
  };
}

interface EvaluationMetrics {
  q_learning: {
    win_rate: number;
    avg_reward: number;
    roi: number;
    stability: number;
    exploration_rate: number;
  };
  dqn: {
    win_rate: number;
    avg_reward: number;
    roi: number;
    stability: number;
    network_confidence: number;
  };
  comparison: {
    better_agent: string;
    performance_difference: number;
    recommendation: string;
  };
}

interface TrainingProgress {
  episode: number;
  reward: number;
  cumulative_reward: number;
  epsilon: number;
  loss?: number;
  q_values_avg?: number;
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
      id={`rl-tabpanel-${index}`}
      aria-labelledby={`rl-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const RLAnalysis: React.FC<RLAnalysisProps> = ({ lotteryType }) => {
  const { user } = useAuth();
  const selectedLottery = useSelectedLottery();
  const [tabValue, setTabValue] = useState(0);
  const [strategy, setStrategy] = useState<'q_learning' | 'dqn' | 'ensemble'>('ensemble');
  const [numCombinations, setNumCombinations] = useState(5);
  const [rlParams, setRLParams] = useState<RLParameters>({
    q_episodes: 500,
    dqn_episodes: 300,
    window_size: 50,
    learning_rate: 0.001,
    discount_factor: 0.95,
    epsilon: 1.0,
    batch_size: 32
  });

  // Проверка премиум подписки
  const isPremium = user?.subscription_status === 'active';

  // Форматирование чисел
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  // Запрос статуса агентов
  const { data: agentStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['rl-status', selectedLottery],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/rl/status`);
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Мутация для обучения агентов
  const trainMutation = useMutation({
    mutationFn: async (params: RLParameters) => {
      const response = await apiClient.post(`/${selectedLottery}/rl/train`, params);
      return response.data;
    },
    onSuccess: () => {
      refetchStatus();
    },
  });

  // Мутация для генерации комбинаций
  const generateMutation = useMutation({
    mutationFn: async (params: {
      count: number;
      strategy: string;
    }) => {
      const response = await apiClient.get(`/${selectedLottery}/rl/generate`, {
        params
      });
      return response.data;
    },
  });

  // Мутация для оценки производительности
  const evaluateMutation = useMutation({
    mutationFn: async (params: { test_size: number }) => {
      const response = await apiClient.post(`/${selectedLottery}/rl/evaluate`, params);
      return response.data;
    },
  });

  // Обработчики
  const handleTrain = () => {
    trainMutation.mutate(rlParams);
  };

  const handleGenerate = () => {
    generateMutation.mutate({
      count: numCombinations,
      strategy: strategy
    });
  };

  const handleEvaluate = () => {
    evaluateMutation.mutate({ test_size: 100 });
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleParamChange = (param: keyof RLParameters, value: number) => {
    setRLParams(prev => ({
      ...prev,
      [param]: value
    }));
  };

  // Рендер графика обучения
  const renderTrainingChart = (data: TrainingProgress[]) => {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="episode" />
          <YAxis />
          <RechartsTooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="cumulative_reward"
            stroke="#8884d8"
            strokeWidth={2}
            name="Кумулятивная награда"
          />
          <Line
            type="monotone"
            dataKey="epsilon"
            stroke="#82ca9d"
            strokeWidth={2}
            name="Epsilon (исследование)"
          />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  // Рендер метрик агентов
  const renderAgentMetrics = (agentData: any, agentName: string) => {
    const metrics = [
      { name: 'Win Rate', value: agentData.win_rate * 100, max: 100, unit: '%' },
      { name: 'Avg Reward', value: agentData.avg_reward, max: 1, unit: '' },
      { name: 'ROI', value: agentData.roi || 0, max: 100, unit: '%' },
    ];

    return (
      <ResponsiveContainer width="100%" height={250}>
        <RadarChart data={metrics}>
          <PolarGrid />
          <PolarAngleAxis dataKey="name" />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={false}
          />
          <Radar
            name={agentName}
            dataKey="value"
            stroke="#8884d8"
            fill="#8884d8"
            fillOpacity={0.3}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    );
  };

  if (!isPremium) {
    return (
      <Box p={3}>
        <Alert severity="warning">
          <Typography variant="h6" gutterBottom>
            🔒 Reinforcement Learning - Премиум функция
          </Typography>
          <Typography>
            Для доступа к обучению с подкреплением необходима премиум подписка.
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
          🤖 Reinforcement Learning
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Обучение с подкреплением: Q-Learning и Deep Q-Network для оптимизации стратегий
        </Typography>
      </Box>

      {/* Статус агентов */}
      <Box p={3}>
        <Card variant="outlined">
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
              <Typography variant="h6">🤖 Статус агентов</Typography>
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
            ) : agentStatus ? (
              <Grid container spacing={3}>
                {/* Q-Learning агент */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Box display="flex" alignItems="center" mb={2}>
                      <Psychology color="primary" sx={{ mr: 1 }} />
                      <Typography variant="subtitle1">Q-Learning агент</Typography>
                      <Chip
                        icon={agentStatus.q_agent?.trained ? <CheckCircle /> : <Error />}
                        label={agentStatus.q_agent?.trained ? 'Обучен' : 'Не обучен'}
                        color={agentStatus.q_agent?.trained ? 'success' : 'error'}
                        size="small"
                        sx={{ ml: 'auto' }}
                      />
                    </Box>

                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Эпизоды</Typography>
                        <Typography variant="body2">{agentStatus.q_agent?.episodes || 0}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Процент побед</Typography>
                        <Typography variant="body2">{((agentStatus.q_agent?.win_rate || 0) * 100).toFixed(1)}%</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Средняя награда</Typography>
                        <Typography variant="body2">{(agentStatus.q_agent?.avg_reward || 0).toFixed(3)}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Размер Q-таблицы</Typography>
                        <Typography variant="body2">{formatNumber(agentStatus.q_agent?.q_table_size || 0)}</Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>

                {/* DQN агент */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                    <Box display="flex" alignItems="center" mb={2}>
                      <Speed color="secondary" sx={{ mr: 1 }} />
                      <Typography variant="subtitle1">DQN агент</Typography>
                      <Chip
                        icon={agentStatus.dqn_agent?.trained ? <CheckCircle /> : <Error />}
                        label={agentStatus.dqn_agent?.trained ? 'Обучен' : 'Не обучен'}
                        color={agentStatus.dqn_agent?.trained ? 'success' : 'error'}
                        size="small"
                        sx={{ ml: 'auto' }}
                      />
                    </Box>

                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Эпизоды</Typography>
                        <Typography variant="body2">{agentStatus.dqn_agent?.episodes || 0}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Процент побед</Typography>
                        <Typography variant="body2">{((agentStatus.dqn_agent?.win_rate || 0) * 100).toFixed(1)}%</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Средняя награда</Typography>
                        <Typography variant="body2">{(agentStatus.dqn_agent?.avg_reward || 0).toFixed(3)}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" display="block">Параметры сети</Typography>
                        <Typography variant="body2">{formatNumber(agentStatus.dqn_agent?.total_parameters || 0)}</Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>

                {/* Среда обучения */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 2, bgcolor: 'info.light' }}>
                    <Typography variant="subtitle1" gutterBottom color="info.contrastText">
                      🎯 Среда обучения
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={3}>
                        <Typography variant="caption" display="block" color="info.contrastText">
                          Размер состояния
                        </Typography>
                        <Typography variant="body2" color="info.contrastText">
                          {agentStatus.environment?.state_size || 0}
                        </Typography>
                      </Grid>
                      <Grid item xs={3}>
                        <Typography variant="caption" display="block" color="info.contrastText">
                          Размер действия
                        </Typography>
                        <Typography variant="body2" color="info.contrastText">
                          {agentStatus.environment?.action_size || 0}
                        </Typography>
                      </Grid>
                      <Grid item xs={3}>
                        <Typography variant="caption" display="block" color="info.contrastText">
                          Схема наград
                        </Typography>
                        <Typography variant="body2" color="info.contrastText">
                          {agentStatus.environment?.reward_scheme || 'Standard'}
                        </Typography>
                      </Grid>
                      <Grid item xs={3}>
                        <Typography variant="caption" display="block" color="info.contrastText">
                          Обновлено
                        </Typography>
                        <Typography variant="body2" color="info.contrastText">
                          {agentStatus.environment?.last_updated ?
                            new Date(agentStatus.environment.last_updated).toLocaleDateString() : 'N/A'}
                        </Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="error">Ошибка загрузки статуса агентов</Alert>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* Вкладки */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="rl analysis tabs">
          <Tab label="🎯 Генерация" />
          <Tab label="🏫 Обучение" />
          <Tab label="📊 Оценка" />
          <Tab label="⚙️ Настройки" />
        </Tabs>
      </Box>

      {/* Вкладка 1: Генерация комбинаций */}
      <TabPanel value={tabValue} index={0}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🎯 Генерация комбинаций с RL
            </Typography>

            {/* Настройки генерации */}
            <Grid container spacing={3} mb={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Стратегия</InputLabel>
                  <Select
                    value={strategy}
                    label="Стратегия"
                    onChange={(e) => setStrategy(e.target.value as any)}
                  >
                    <MenuItem value="q_learning">Q-Learning</MenuItem>
                    <MenuItem value="dqn">Deep Q-Network</MenuItem>
                    <MenuItem value="ensemble">Ансамбль (рекомендуется)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
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
                />
              </Grid>
            </Grid>

            <Button
              variant="contained"
              size="large"
              startIcon={<PlayArrow />}
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !agentStatus?.q_agent?.trained}
              fullWidth
            >
              {generateMutation.isPending ? 'Генерация...' : 'Сгенерировать комбинации'}
            </Button>

            {/* Результаты генерации */}
            {generateMutation.data?.combinations && (
              <Box mt={3}>
                <Typography variant="h6" gutterBottom>📋 Результаты RL генерации</Typography>
                <Grid container spacing={2}>
                  {generateMutation.data.combinations.map((combo: RLCombination, index: number) => (
                    <Grid item xs={12} key={index}>
                      <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                          <Typography variant="subtitle1">
                            Комбинация #{index + 1}
                          </Typography>
                          <Box display="flex" gap={1}>
                            <Chip
                              label={combo.method}
                              size="small"
                              color={
                                combo.method === 'q_learning' ? 'primary' :
                                combo.method === 'dqn' ? 'secondary' : 'success'
                              }
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

                        {combo.rl_info && (
                          <Box mt={1}>
                            <Typography variant="caption" display="block">
                              Q-значение: {combo.rl_info.q_value?.toFixed(4)}
                            </Typography>
                            <Typography variant="caption" display="block">
                              Вероятность действия: {(combo.rl_info.action_probability * 100)?.toFixed(1)}%
                            </Typography>
                            <Typography variant="caption" display="block">
                              Фактор исследования: {combo.rl_info.exploration_factor?.toFixed(3)}
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

      {/* Вкладка 2: Обучение */}
      <TabPanel value={tabValue} index={1}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🏫 Обучение RL агентов
            </Typography>

            {/* Параметры обучения */}
            <Grid container spacing={3} mb={4}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Q-Learning эпизоды: {rlParams.q_episodes}
                </Typography>
                <Slider
                  value={rlParams.q_episodes}
                  onChange={(_, value) => handleParamChange('q_episodes', value as number)}
                  min={100}
                  max={1000}
                  step={50}
                  marks={[
                    { value: 100, label: '100' },
                    { value: 500, label: '500' },
                    { value: 1000, label: '1000' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  DQN эпизоды: {rlParams.dqn_episodes}
                </Typography>
                <Slider
                  value={rlParams.dqn_episodes}
                  onChange={(_, value) => handleParamChange('dqn_episodes', value as number)}
                  min={100}
                  max={500}
                  step={25}
                  marks={[
                    { value: 100, label: '100' },
                    { value: 300, label: '300' },
                    { value: 500, label: '500' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Размер окна: {rlParams.window_size}
                </Typography>
                <Slider
                  value={rlParams.window_size}
                  onChange={(_, value) => handleParamChange('window_size', value as number)}
                  min={20}
                  max={100}
                  step={10}
                  marks={[
                    { value: 20, label: '20' },
                    { value: 50, label: '50' },
                    { value: 100, label: '100' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Скорость обучения: {rlParams.learning_rate}
                </Typography>
                <Slider
                  value={rlParams.learning_rate}
                  onChange={(_, value) => handleParamChange('learning_rate', value as number)}
                  min={0.0001}
                  max={0.01}
                  step={0.0001}
                  marks={[
                    { value: 0.0001, label: '0.0001' },
                    { value: 0.001, label: '0.001' },
                    { value: 0.01, label: '0.01' }
                  ]}
                />
              </Grid>
            </Grid>

            <Button
              variant="contained"
              size="large"
              startIcon={<School />}
              onClick={handleTrain}
              disabled={trainMutation.isPending}
              fullWidth
            >
              {trainMutation.isPending ? 'Обучение в процессе...' : 'Запустить обучение агентов'}
            </Button>

            {trainMutation.isPending && (
              <Box mt={2}>
                <Typography variant="body2" gutterBottom>Прогресс обучения:</Typography>
                <LinearProgress />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Обучение может занять несколько минут в зависимости от количества эпизодов
                </Typography>
              </Box>
            )}

            {/* Результаты обучения */}
            {trainMutation.data && (
              <Box mt={3}>
                <Typography variant="h6" gutterBottom>📈 Результаты обучения</Typography>

                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle1" gutterBottom>Q-Learning</Typography>
                      <Grid container spacing={1}>
                        <Grid item xs={6}>
                          <Typography variant="caption" display="block">Процент побед</Typography>
                          <Typography variant="h6" color="primary">
                            {(trainMutation.data.q_learning?.win_rate * 100)?.toFixed(1)}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="caption" display="block">Средняя награда</Typography>
                          <Typography variant="h6" color="primary">
                            {trainMutation.data.q_learning?.avg_reward?.toFixed(3)}
                          </Typography>
                        </Grid>
                      </Grid>
                    </Paper>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle1" gutterBottom>DQN</Typography>
                      <Grid container spacing={1}>
                        <Grid item xs={6}>
                          <Typography variant="caption" display="block">Процент побед</Typography>
                          <Typography variant="h6" color="secondary">
                            {(trainMutation.data.dqn?.win_rate * 100)?.toFixed(1)}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="caption" display="block">Средняя награда</Typography>
                          <Typography variant="h6" color="secondary">
                            {trainMutation.data.dqn?.avg_reward?.toFixed(3)}
                          </Typography>
                        </Grid>
                      </Grid>
                    </Paper>
                  </Grid>
                </Grid>

                {/* График обучения */}
                {trainMutation.data.training_history && (
                  <Paper sx={{ p: 2, mt: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>📊 История обучения</Typography>
                    {renderTrainingChart(trainMutation.data.training_history)}
                  </Paper>
                )}
              </Box>
            )}

            {trainMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                Ошибка обучения: {(trainMutation.error as Error)?.message}
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 3: Оценка производительности */}
      <TabPanel value={tabValue} index={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📊 Оценка производительности агентов
            </Typography>

            <Button
              variant="contained"
              startIcon={<Assessment />}
              onClick={handleEvaluate}
              disabled={evaluateMutation.isPending || !agentStatus?.q_agent?.trained}
              sx={{ mb: 3 }}
            >
              {evaluateMutation.isPending ? 'Оценка...' : 'Запустить оценку'}
            </Button>

            {/* Результаты оценки */}
            {evaluateMutation.data && (
              <Box>
                <Typography variant="h6" gutterBottom>🏆 Результаты сравнения</Typography>

                <Grid container spacing={3}>
                  {/* Метрики Q-Learning */}
                  <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle1" gutterBottom>Q-Learning метрики</Typography>
                      {renderAgentMetrics(evaluateMutation.data.q_learning, 'Q-Learning')}
                    </Paper>
                  </Grid>

                  {/* Метрики DQN */}
                  <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle1" gutterBottom>DQN метрики</Typography>
                      {renderAgentMetrics(evaluateMutation.data.dqn, 'DQN')}
                    </Paper>
                  </Grid>

                  {/* Сравнение */}
                  <Grid item xs={12}>
                    <Paper sx={{ p: 2, bgcolor: 'success.light' }}>
                      <Typography variant="subtitle1" gutterBottom color="success.contrastText">
                        🎯 Рекомендация
                      </Typography>
                      <Typography variant="h6" color="success.contrastText" gutterBottom>
                        Лучший агент: {evaluateMutation.data.comparison?.better_agent}
                      </Typography>
                      <Typography variant="body2" color="success.contrastText" gutterBottom>
                        Разница в производительности: {evaluateMutation.data.comparison?.performance_difference?.toFixed(1)}%
                      </Typography>
                      <Typography variant="body2" color="success.contrastText">
                        {evaluateMutation.data.comparison?.recommendation}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>
            )}

            {evaluateMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                Ошибка оценки: {(evaluateMutation.error as Error)?.message}
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 4: Настройки */}
      <TabPanel value={tabValue} index={3}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              ⚙️ Продвинутые настройки RL
            </Typography>

            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="body2">
                Настройка гиперпараметров для тонкой настройки производительности агентов
              </Typography>
            </Alert>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Фактор дисконтирования: {rlParams.discount_factor}
                </Typography>
                <Slider
                  value={rlParams.discount_factor}
                  onChange={(_, value) => handleParamChange('discount_factor', value as number)}
                  min={0.8}
                  max={0.99}
                  step={0.01}
                  marks={[
                    { value: 0.8, label: '0.8' },
                    { value: 0.9, label: '0.9' },
                    { value: 0.95, label: '0.95' },
                    { value: 0.99, label: '0.99' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Начальный epsilon: {rlParams.epsilon}
                </Typography>
                <Slider
                  value={rlParams.epsilon}
                  onChange={(_, value) => handleParamChange('epsilon', value as number)}
                  min={0.1}
                  max={1.0}
                  step={0.1}
                  marks={[
                    { value: 0.1, label: '0.1' },
                    { value: 0.5, label: '0.5' },
                    { value: 1.0, label: '1.0' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Размер батча (DQN): {rlParams.batch_size}
                </Typography>
                <Slider
                  value={rlParams.batch_size}
                  onChange={(_, value) => handleParamChange('batch_size', value as number)}
                  min={16}
                  max={128}
                  step={16}
                  marks={[
                    { value: 16, label: '16' },
                    { value: 32, label: '32' },
                    { value: 64, label: '64' },
                    { value: 128, label: '128' }
                  ]}
                />
              </Grid>
            </Grid>

            <Box mt={4}>
              <Typography variant="subtitle1" gutterBottom>
                📚 Справка по параметрам
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon><Info color="primary" /></ListItemIcon>
                  <ListItemText
                    primary="Фактор дисконтирования (γ)"
                    secondary="Определяет важность будущих наград. Чем выше, тем больше агент учитывает долгосрочные результаты."
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon><Info color="primary" /></ListItemIcon>
                  <ListItemText
                    primary="Epsilon (ε)"
                    secondary="Начальная вероятность случайного действия для исследования среды."
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon><Info color="primary" /></ListItemIcon>
                  <ListItemText
                    primary="Размер батча"
                    secondary="Количество образцов для обучения DQN за одну итерацию."
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon><Info color="primary" /></ListItemIcon>
                  <ListItemText
                    primary="Размер окна"
                    secondary="Количество последних тиражей для формирования состояния среды."
                  />
                </ListItem>
              </List>
            </Box>
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  );
};

export default RLAnalysis;