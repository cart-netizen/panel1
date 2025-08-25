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
  List,
  ListItem,
  ListItemText,
  Paper,
  Tab,
  Tabs,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress
} from '@mui/material';
import {
  TrendingUp,
  Timeline,
  ShowChart,
  Analytics,
  ExpandMore,
  Insights,
  Schedule,
  Functions
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
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useAuth, useSelectedLottery } from '../../store';

interface TimeSeriesAnalysisProps {
  lotteryType: string;
}

interface AnalysisSummary {
  total_fields_analyzed: number;
  seasonality_detected: Array<{ field: string; period: number }>;
  trends_detected: Array<{ field: string; direction: string }>;
  stationary_fields: string[];
  recommended_arima_params: Record<string, [number, number, number]>;
}

interface Combination {
  field1: number[];
  field2: number[];
  confidence: number;
  method: string;
  analysis_details?: {
    arima_params: [number, number, number];
    seasonality_period: number;
    trend_strength: number;
    forecast_horizon: number;
  };
}

interface ForecastData {
  period: string;
  historical: number;
  forecast: number;
  confidence_lower: number;
  confidence_upper: number;
  trend: number;
  seasonal: number;
}

interface SeasonalityAnalysis {
  field: string;
  period: number;
  strength: number;
  components: Array<{
    period: number;
    amplitude: number;
    phase: number;
  }>;
}

interface TrendAnalysis {
  field: string;
  direction: 'increasing' | 'decreasing' | 'stable';
  strength: number;
  slope: number;
  r_squared: number;
  forecast_trend: number[];
}

interface ModelDiagnostics {
  model_type: string;
  aic: number;
  bic: number;
  residual_stats: {
    mean: number;
    std: number;
    skewness: number;
    kurtosis: number;
  };
  ljung_box_p_value: number;
  jarque_bera_p_value: number;
  durbin_watson: number;
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
      id={`timeseries-tabpanel-${index}`}
      aria-labelledby={`timeseries-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const TimeSeriesAnalysis: React.FC<TimeSeriesAnalysisProps> = ({ lotteryType }) => {
  const { user } = useAuth();
  const selectedLottery = useSelectedLottery();
  const [tabValue, setTabValue] = useState(0);
  const [analysisType, setAnalysisType] = useState<'arima' | 'sarima' | 'auto'>('auto');
  const [forecastHorizon, setForecastHorizon] = useState(10);
  const [seasonalityPeriod, setSeasonalityPeriod] = useState(7);
  const [numCombinations, setNumCombinations] = useState(5);

  // Проверка премиум подписки
  const isPremium = user?.subscription_status === 'active';

  // Запрос анализа временных рядов
  const { data: analysisData, isLoading: analysisLoading, refetch: refetchAnalysis } = useQuery({
    queryKey: ['timeseries-analysis', selectedLottery, analysisType],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/timeseries/analyze`, {
        params: {
          method: analysisType,
          forecast_horizon: forecastHorizon,
          seasonality_period: seasonalityPeriod
        }
      });
      return response.data;
    },
    enabled: isPremium,
    refetchInterval: 60000,
  });

  // Мутация для генерации прогнозов
  const forecastMutation = useMutation({
    mutationFn: async (params: {
      method: string;
      horizon: number;
      confidence_level: number;
    }) => {
      const response = await apiClient.post(`/${selectedLottery}/timeseries/forecast`, params);
      return response.data;
    },
  });

  // Мутация для генерации комбинаций
  const generateMutation = useMutation({
    mutationFn: async (params: {
      num_combinations: number;
      method: string;
      use_seasonality: boolean;
    }) => {
      const response = await apiClient.post(`/${selectedLottery}/timeseries/generate`, params);
      return response.data;
    },
  });

  // Запрос диагностики моделей
  const { data: diagnostics, isLoading: diagnosticsLoading } = useQuery({
    queryKey: ['timeseries-diagnostics', selectedLottery],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/timeseries/diagnostics`);
      return response.data;
    },
    enabled: isPremium && tabValue === 3,
  });

  // Обработчики
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleForecast = () => {
    forecastMutation.mutate({
      method: analysisType,
      horizon: forecastHorizon,
      confidence_level: 0.95
    });
  };

  const handleGenerate = () => {
    generateMutation.mutate({
      num_combinations: numCombinations,
      method: analysisType,
      use_seasonality: seasonalityPeriod > 0
    });
  };

  // Рендер графика прогноза
  const renderForecastChart = (data: ForecastData[]) => {
    return (
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="historical"
            stroke="#8884d8"
            strokeWidth={2}
            name="Исторические данные"
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#82ca9d"
            strokeWidth={2}
            strokeDasharray="5 5"
            name="Прогноз"
          />
          <Area
            type="monotone"
            dataKey="confidence_upper"
            stackId="1"
            stroke="transparent"
            fill="#82ca9d"
            fillOpacity={0.2}
            name="Доверительный интервал"
          />
          <Area
            type="monotone"
            dataKey="confidence_lower"
            stackId="1"
            stroke="transparent"
            fill="#ffffff"
            name=""
          />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  // Рендер сезонной декомпозиции
  const renderSeasonalDecomposition = (data: any) => {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="trend" stroke="#8884d8" name="Тренд" />
          <Line type="monotone" dataKey="seasonal" stroke="#82ca9d" name="Сезонная компонента" />
          <Line type="monotone" dataKey="residual" stroke="#ffc658" name="Остатки" />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  if (!isPremium) {
    return (
      <Box p={3}>
        <Alert severity="warning">
          <Typography variant="h6" gutterBottom>
            🔒 Анализ временных рядов - Премиум функция
          </Typography>
          <Typography>
            Для доступа к анализу временных рядов ARIMA/SARIMA необходима премиум подписка.
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
          📈 Анализ временных рядов
        </Typography>
        <Typography variant="body2" color="text.secondary">
          ARIMA/SARIMA моделирование для прогнозирования трендов лотерейных чисел
        </Typography>
      </Box>

      {/* Панель управления */}
      <Box p={3}>
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>⚙️ Настройки анализа</Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Метод анализа</InputLabel>
                  <Select
                    value={analysisType}
                    label="Метод анализа"
                    onChange={(e) => setAnalysisType(e.target.value as any)}
                  >
                    <MenuItem value="arima">ARIMA</MenuItem>
                    <MenuItem value="sarima">SARIMA (с сезонностью)</MenuItem>
                    <MenuItem value="auto">Автовыбор (рекомендуется)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={4}>
                <Typography variant="subtitle2" gutterBottom>
                  Горизонт прогноза: {forecastHorizon} периодов
                </Typography>
                <Slider
                  value={forecastHorizon}
                  onChange={(_, value) => setForecastHorizon(value as number)}
                  min={5}
                  max={30}
                  step={1}
                  marks={[
                    { value: 5, label: '5' },
                    { value: 10, label: '10' },
                    { value: 20, label: '20' },
                    { value: 30, label: '30' }
                  ]}
                />
              </Grid>

              <Grid item xs={12} md={4}>
                <Typography variant="subtitle2" gutterBottom>
                  Период сезонности: {seasonalityPeriod}
                </Typography>
                <Slider
                  value={seasonalityPeriod}
                  onChange={(_, value) => setSeasonalityPeriod(value as number)}
                  min={0}
                  max={14}
                  step={1}
                  marks={[
                    { value: 0, label: 'Нет' },
                    { value: 7, label: '7' },
                    { value: 14, label: '14' }
                  ]}
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="contained"
                  startIcon={<Analytics />}
                  onClick={() => refetchAnalysis()}
                  disabled={analysisLoading}
                  sx={{ mr: 2 }}
                >
                  {analysisLoading ? 'Анализ...' : 'Запустить анализ'}
                </Button>

                <Button
                  variant="outlined"
                  startIcon={<ShowChart />}
                  onClick={handleForecast}
                  disabled={forecastMutation.isPending || !analysisData}
                >
                  {forecastMutation.isPending ? 'Прогноз...' : 'Создать прогноз'}
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Box>

      {/* Вкладки */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="timeseries analysis tabs">
          <Tab label="📊 Обзор" />
          <Tab label="📈 Прогнозы" />
          <Tab label="🎯 Генерация" />
          <Tab label="🔍 Диагностика" />
        </Tabs>
      </Box>

      {/* Вкладка 1: Обзор анализа */}
      <TabPanel value={tabValue} index={0}>
        {analysisLoading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
          </Box>
        ) : analysisData ? (
          <Grid container spacing={3}>
            {/* Сводка анализа */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3, bgcolor: 'primary.light' }}>
                <Typography variant="h6" gutterBottom color="primary.contrastText">
                  📋 Сводка анализа временных рядов
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" display="block" color="primary.contrastText">
                      Проанализированных полей
                    </Typography>
                    <Typography variant="h4" color="primary.contrastText">
                      {analysisData.summary?.total_fields_analyzed || 0}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" display="block" color="primary.contrastText">
                      Обнаружена сезонность
                    </Typography>
                    <Typography variant="h4" color="primary.contrastText">
                      {analysisData.summary?.seasonality_detected?.length || 0}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" display="block" color="primary.contrastText">
                      Трендов выявлено
                    </Typography>
                    <Typography variant="h4" color="primary.contrastText">
                      {analysisData.summary?.trends_detected?.length || 0}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" display="block" color="primary.contrastText">
                      Стационарных рядов
                    </Typography>
                    <Typography variant="h4" color="primary.contrastText">
                      {analysisData.summary?.stationary_fields?.length || 0}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>

            {/* Детальная информация по полям */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>🔄 Сезонность</Typography>
                  {analysisData.seasonality_analysis?.length > 0 ? (
                    <List dense>
                      {analysisData.seasonality_analysis.map((item: SeasonalityAnalysis, index: number) => (
                        <ListItem key={index} sx={{ px: 0 }}>
                          <ListItemText
                            primary={`${item.field} (период: ${item.period})`}
                            secondary={
                              <Box>
                                <LinearProgress
                                  variant="determinate"
                                  value={item.strength * 100}
                                  sx={{ mt: 1, mb: 1 }}
                                />
                                <Typography variant="caption">
                                  Сила сезонности: {(item.strength * 100).toFixed(1)}%
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Сезонность не обнаружена
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>📈 Тренды</Typography>
                  {analysisData.trend_analysis?.length > 0 ? (
                    <List dense>
                      {analysisData.trend_analysis.map((item: TrendAnalysis, index: number) => (
                        <ListItem key={index} sx={{ px: 0 }}>
                          <ListItemText
                            primary={item.field}
                            secondary={
                              <Box>
                                <Chip
                                  label={item.direction}
                                  size="small"
                                  color={
                                    item.direction === 'increasing' ? 'success' :
                                    item.direction === 'decreasing' ? 'error' : 'default'
                                  }
                                  sx={{ mb: 1 }}
                                />
                                <Typography variant="caption" display="block">
                                  Сила тренда: {(item.strength * 100).toFixed(1)}%
                                </Typography>
                                <Typography variant="caption" display="block">
                                  R²: {item.r_squared?.toFixed(3)}
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Значимые тренды не обнаружены
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Рекомендуемые параметры ARIMA */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>⚙️ Рекомендуемые параметры ARIMA</Typography>
                  {analysisData.summary?.recommended_arima_params ? (
                    <Grid container spacing={2}>
                      {Object.entries(analysisData.summary.recommended_arima_params).map(([field, params]: [string, any], index) => (
                        <Grid item xs={12} md={6} key={index}>
                          <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                            <Typography variant="subtitle2" gutterBottom>{field}</Typography>
                            <Box display="flex" gap={1}>
                              <Chip label={`p=${params[0]}`} size="small" color="primary" />
                              <Chip label={`d=${params[1]}`} size="small" color="secondary" />
                              <Chip label={`q=${params[2]}`} size="small" color="success" />
                            </Box>
                            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                              ARIMA({params[0]}, {params[1]}, {params[2]})
                            </Typography>
                          </Paper>
                        </Grid>
                      ))}
                    </Grid>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Параметры ARIMA будут определены после анализа
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ) : (
          <Alert severity="info">
            Запустите анализ временных рядов для просмотра детальной статистики
          </Alert>
        )}
      </TabPanel>

      {/* Вкладка 2: Прогнозы */}
      <TabPanel value={tabValue} index={1}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📈 Прогнозирование временных рядов
            </Typography>

            {forecastMutation.data ? (
              <Grid container spacing={3}>
                {/* График прогноза для поля 1 */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Прогноз для поля 1
                    </Typography>
                    {renderForecastChart(forecastMutation.data.field1_forecast)}
                  </Paper>
                </Grid>

                {/* График прогноза для поля 2 */}
                <Grid item xs={12}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Прогноз для поля 2
                    </Typography>
                    {renderForecastChart(forecastMutation.data.field2_forecast)}
                  </Paper>
                </Grid>

                {/* Метрики точности */}
                {forecastMutation.data.accuracy_metrics && (
                  <Grid item xs={12}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle1" gutterBottom>📊 Метрики точности</Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" display="block">MAE (Средняя абсолютная ошибка)</Typography>
                          <Typography variant="h6">
                            {forecastMutation.data.accuracy_metrics.mae?.toFixed(3)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" display="block">RMSE (Среднеквадратичная ошибка)</Typography>
                          <Typography variant="h6">
                            {forecastMutation.data.accuracy_metrics.rmse?.toFixed(3)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" display="block">MAPE (%)</Typography>
                          <Typography variant="h6">
                            {(forecastMutation.data.accuracy_metrics.mape * 100)?.toFixed(1)}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" display="block">R²</Typography>
                          <Typography variant="h6">
                            {forecastMutation.data.accuracy_metrics.r_squared?.toFixed(3)}
                          </Typography>
                        </Grid>
                      </Grid>
                    </Paper>
                  </Grid>
                )}
              </Grid>
            ) : (
              <Alert severity="info">
                Нажмите "Создать прогноз" для генерации временных рядов
              </Alert>
            )}

            {forecastMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                Ошибка прогнозирования: {(forecastMutation.error as Error)?.message}
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      {/* Вкладка 3: Генерация комбинаций */}
      <TabPanel value={tabValue} index={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🎯 Генерация комбинаций на основе временных рядов
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
                max={15}
                marks
                step={1}
                sx={{ mb: 2 }}
              />
            </Box>

            <Button
              variant="contained"
              size="large"
              startIcon={<TrendingUp />}
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !analysisData}
              fullWidth
            >
              {generateMutation.isPending ? 'Генерация...' : 'Сгенерировать комбинации'}
            </Button>

            {/* Результаты генерации */}
            {generateMutation.data?.combinations && (
              <Box mt={3}>
                <Typography variant="h6" gutterBottom>📋 Результаты на основе временных рядов</Typography>
                <Grid container spacing={2}>
                  {generateMutation.data.combinations.map((combo: Combination, index: number) => (
                    <Grid item xs={12} key={index}>
                      <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                          <Typography variant="subtitle1">
                            Комбинация #{index + 1}
                          </Typography>
                          <Chip
                            label={`${(combo.confidence * 100).toFixed(1)}% точности`}
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

                        {combo.analysis_details && (
                          <Accordion>
                            <AccordionSummary expandIcon={<ExpandMore />}>
                              <Typography variant="caption">Детали анализа</Typography>
                            </AccordionSummary>
                            <AccordionDetails>
                              <Grid container spacing={2}>
                                <Grid item xs={6}>
                                  <Typography variant="caption" display="block">ARIMA параметры</Typography>
                                  <Typography variant="body2">
                                    ({combo.analysis_details.arima_params?.join(', ')})
                                  </Typography>
                                </Grid>
                                <Grid item xs={6}>
                                  <Typography variant="caption" display="block">Период сезонности</Typography>
                                  <Typography variant="body2">
                                    {combo.analysis_details.seasonality_period || 'Не обнаружена'}
                                  </Typography>
                                </Grid>
                                <Grid item xs={6}>
                                  <Typography variant="caption" display="block">Сила тренда</Typography>
                                  <Typography variant="body2">
                                    {combo.analysis_details.trend_strength?.toFixed(3)}
                                  </Typography>
                                </Grid>
                                <Grid item xs={6}>
                                  <Typography variant="caption" display="block">Горизонт прогноза</Typography>
                                  <Typography variant="body2">
                                    {combo.analysis_details.forecast_horizon} периодов
                                  </Typography>
                                </Grid>
                              </Grid>
                            </AccordionDetails>
                          </Accordion>
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

      {/* Вкладка 4: Диагностика моделей */}
      <TabPanel value={tabValue} index={3}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🔍 Диагностика моделей временных рядов
            </Typography>

            {diagnosticsLoading ? (
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
              </Box>
            ) : diagnostics ? (
              <Grid container spacing={3}>
                {diagnostics.models?.map((model: ModelDiagnostics, index: number) => (
                  <Grid item xs={12} md={6} key={index}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle1" gutterBottom>
                        📊 {model.model_type} модель
                      </Typography>

                      {/* Информационные критерии */}
                      <Box mb={2}>
                        <Typography variant="caption" display="block">Информационные критерии</Typography>
                        <Grid container spacing={1}>
                          <Grid item xs={6}>
                            <Typography variant="body2">AIC: {model.aic?.toFixed(2)}</Typography>
                          </Grid>
                          <Grid item xs={6}>
                            <Typography variant="body2">BIC: {model.bic?.toFixed(2)}</Typography>
                          </Grid>
                        </Grid>
                      </Box>

                      {/* Статистика остатков */}
                      <Box mb={2}>
                        <Typography variant="caption" display="block">Статистика остатков</Typography>
                        <Grid container spacing={1}>
                          <Grid item xs={6}>
                            <Typography variant="body2">
                              Среднее: {model.residual_stats?.mean?.toFixed(4)}
                            </Typography>
                          </Grid>
                          <Grid item xs={6}>
                            <Typography variant="body2">
                              Ст. откл.: {model.residual_stats?.std?.toFixed(4)}
                            </Typography>
                          </Grid>
                          <Grid item xs={6}>
                            <Typography variant="body2">
                              Асимметрия: {model.residual_stats?.skewness?.toFixed(3)}
                            </Typography>
                          </Grid>
                          <Grid item xs={6}>
                            <Typography variant="body2">
                              Эксцесс: {model.residual_stats?.kurtosis?.toFixed(3)}
                            </Typography>
                          </Grid>
                        </Grid>
                      </Box>

                      {/* Тесты */}
                      <Box>
                        <Typography variant="caption" display="block">Диагностические тесты</Typography>
                        <List dense>
                          <ListItem sx={{ px: 0 }}>
                            <ListItemText
                              primary="Льюнг-Бокс тест"
                              secondary={`p-value: ${model.ljung_box_p_value?.toFixed(4)}`}
                            />
                            <Chip
                              label={model.ljung_box_p_value > 0.05 ? 'OK' : 'Предупреждение'}
                              size="small"
                              color={model.ljung_box_p_value > 0.05 ? 'success' : 'warning'}
                            />
                          </ListItem>
                          <ListItem sx={{ px: 0 }}>
                            <ListItemText
                              primary="Jarque-Bera тест"
                              secondary={`p-value: ${model.jarque_bera_p_value?.toFixed(4)}`}
                            />
                            <Chip
                              label={model.jarque_bera_p_value > 0.05 ? 'OK' : 'Предупреждение'}
                              size="small"
                              color={model.jarque_bera_p_value > 0.05 ? 'success' : 'warning'}
                            />
                          </ListItem>
                          <ListItem sx={{ px: 0 }}>
                            <ListItemText
                              primary="Дарбин-Уотсон"
                              secondary={`Статистика: ${model.durbin_watson?.toFixed(3)}`}
                            />
                            <Chip
                              label={Math.abs(model.durbin_watson - 2) < 0.5 ? 'OK' : 'Предупреждение'}
                              size="small"
                              color={Math.abs(model.durbin_watson - 2) < 0.5 ? 'success' : 'warning'}
                            />
                          </ListItem>
                        </List>
                      </Box>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Alert severity="info">
                Диагностика моделей будет доступна после завершения анализа
              </Alert>
            )}
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  );
};

export default TimeSeriesAnalysis;