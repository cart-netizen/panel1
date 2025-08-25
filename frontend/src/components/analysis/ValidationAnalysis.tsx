import React, { useState, useCallback, useEffect } from 'react';
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
  Slider,
  FormControlLabel,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
} from '@mui/material';
import {
  Science,
  PlayArrow,
  Compare,
  Timeline,
  CheckCircle,
  Error,
  Info,
  ExpandMore,
  ExpandLess,
  Refresh,
  Download,
  Assessment,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { useSelectedLottery, useAuth } from '../../store';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

interface ValidationTask {
  task_id: string;
  status: 'started' | 'running' | 'completed' | 'error';
  message?: string;
  progress?: number;
  summary?: any;
  average_metrics?: any;
  window_details?: any[];
}

interface ComparisonResult {
  model: string;
  avg_accuracy: number;
  avg_f1: number;
  avg_roc_auc: number;
  avg_precision: number;
  avg_recall: number;
  stability: number;
  training_time: number;
  prediction_time: number;
}

interface ValidationParams {
  models: string[];
  initial_train_size: number;
  test_size: number;
  step_size: number;
  expanding_window: boolean;
  purged_window: number;
  embargo_window: number;
}

interface CrossValidationParams {
  models: string[];
  cv_folds: number;
  stratified: boolean;
  shuffle: boolean;
  random_state: number;
}

interface ValidationAnalysisProps {
  lotteryType: string;
}

const ValidationAnalysis: React.FC<ValidationAnalysisProps> = ({ lotteryType }) => {
  const selectedLottery = useSelectedLottery();
  const { user } = useAuth();
  const [validationParams, setValidationParams] = useState<ValidationParams>({
    models: ['rf', 'lstm', 'xgboost'],
    initial_train_size: 100,
    test_size: 20,
    step_size: 10,
    expanding_window: true,
    purged_window: 0,
    embargo_window: 0,
  });

  const [crossValidationParams, setCrossValidationParams] = useState<CrossValidationParams>({
    models: ['rf', 'lstm'],
    cv_folds: 5,
    stratified: true,
    shuffle: true,
    random_state: 42,
  });

  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState<string | null>(null);
  const [detailsDialog, setDetailsDialog] = useState(false);
  const [selectedValidation, setSelectedValidation] = useState<'walk_forward' | 'cross_validation'>('walk_forward');

  // Проверка премиум подписки
  const isPremium = user?.subscription_status === 'active';

  const availableModels = [
    { value: 'rf', label: 'Random Forest' },
    { value: 'lstm', label: 'LSTM' },
    { value: 'xgboost', label: 'XGBoost' },
    { value: 'genetic', label: 'Генетический алгоритм' },
    { value: 'rl', label: 'Reinforcement Learning' },
    { value: 'bayesian', label: 'Байесовский' },
    { value: 'timeseries', label: 'Временные ряды' },
  ];

  // Мутация для запуска walk-forward валидации
  const walkForwardMutation = useMutation({
    mutationFn: async (data: ValidationParams) => {
      const response = await apiClient.post(`/${selectedLottery}/validation/walk-forward`, data);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.task_id) {
        setCurrentTaskId(data.task_id);
      }
    },
  });

  // Мутация для запуска кросс-валидации
  const crossValidationMutation = useMutation({
    mutationFn: async (data: CrossValidationParams) => {
      const response = await apiClient.post(`/${selectedLottery}/validation/cross-validation`, data);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.task_id) {
        setCurrentTaskId(data.task_id);
      }
    },
  });

  // Мутация для сравнения моделей
  const comparisonMutation = useMutation({
    mutationFn: async (data: { method: string; models: string[] }) => {
      const response = await apiClient.post(`/${selectedLottery}/validation/compare-models`, data);
      return response.data;
    },
  });

  // Состояние для контроля polling
  const [isPolling, setIsPolling] = useState(false);

  // Запрос статуса валидации
  const { data: taskStatus, isLoading: taskLoading } = useQuery({
    queryKey: ['validation-task-status', currentTaskId],
    queryFn: async () => {
      if (!currentTaskId) return null;
      const response = await apiClient.get(`/${selectedLottery}/validation/status/${currentTaskId}`);
      return response.data;
    },
    enabled: !!currentTaskId,
    refetchInterval: isPolling ? 2000 : false,
  });

  // Запрос истории валидаций
  const { data: validationHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['validation-history', selectedLottery],
    queryFn: async () => {
      const response = await apiClient.get(`/${selectedLottery}/validation/history`);
      return response.data;
    },
    refetchInterval: 60000,
  });

  // Эффект для отслеживания завершения задачи
  useEffect(() => {
    if (taskStatus?.status === 'completed' || taskStatus?.status === 'error') {
      setTimeout(() => {
        setCurrentTaskId(null);
      }, 5000);
    }
  }, [taskStatus]);

  // Обработчики
  const handleStartWalkForward = () => {
    walkForwardMutation.mutate(validationParams);
  };

  const handleStartCrossValidation = () => {
    crossValidationMutation.mutate(crossValidationParams);
  };

  const handleCompareModels = () => {
    comparisonMutation.mutate({
      method: selectedValidation,
      models: selectedValidation === 'walk_forward' ? validationParams.models : crossValidationParams.models
    });
  };

  const handleParamChange = (param: keyof ValidationParams, value: any) => {
    setValidationParams(prev => ({
      ...prev,
      [param]: value
    }));
  };

  const handleCVParamChange = (param: keyof CrossValidationParams, value: any) => {
    setCrossValidationParams(prev => ({
      ...prev,
      [param]: value
    }));
  };

  // Рендер графика метрик
  const renderMetricsChart = (data: any[]) => {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="window" />
          <YAxis />
          <RechartsTooltip />
          <Legend />
          <Line type="monotone" dataKey="accuracy" stroke="#8884d8" strokeWidth={2} name="Точность" />
          <Line type="monotone" dataKey="f1_score" stroke="#82ca9d" strokeWidth={2} name="F1-Score" />
          <Line type="monotone" dataKey="precision" stroke="#ffc658" strokeWidth={2} name="Precision" />
          <Line type="monotone" dataKey="recall" stroke="#ff7300" strokeWidth={2} name="Recall" />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  // Рендер сравнения моделей
  const renderModelComparison = (data: ComparisonResult[]) => {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="model" />
          <YAxis />
          <RechartsTooltip />
          <Legend />
          <Bar dataKey="avg_accuracy" fill="#8884d8" name="Точность" />
          <Bar dataKey="avg_f1" fill="#82ca9d" name="F1-Score" />
          <Bar dataKey="stability" fill="#ffc658" name="Стабильность" />
        </BarChart>
      </ResponsiveContainer>
    );
  };

  if (!isPremium) {
    return (
      <Box p={3}>
        <Alert severity="warning">
          <Typography variant="h6" gutterBottom>
            🔒 Walk-forward валидация - Премиум функция
          </Typography>
          <Typography>
            Для доступа к продвинутой валидации моделей необходима премиум подписка.
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
          🧪 Валидация моделей
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Walk-forward и кросс-валидация для объективной оценки производительности моделей
        </Typography>
      </Box>

      {/* Статус текущей валидации */}
      {currentTaskId && taskStatus && (
        <Box p={3}>
          <Alert
            severity={
              taskStatus.status === 'completed' ? 'success' :
              taskStatus.status === 'error' ? 'error' : 'info'
            }
          >
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                {taskStatus.status === 'completed' ? '✅ Валидация завершена' :
                 taskStatus.status === 'error' ? '❌ Ошибка валидации' :
                 taskStatus.status === 'running' ? '🔄 Валидация в процессе...' : '🚀 Валидация запущена'}
              </Typography>

              {taskStatus.message && (
                <Typography variant="body2" gutterBottom>
                  {taskStatus.message}
                </Typography>
              )}

              {taskStatus.status === 'running' && taskStatus.progress !== undefined && (
                <Box>
                  <Typography variant="caption" display="block">
                    Прогресс: {Math.round(taskStatus.progress)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={taskStatus.progress}
                    sx={{ mt: 1 }}
                  />
                </Box>
              )}
            </Box>
          </Alert>
        </Box>
      )}

      <Box p={3}>
        <Grid container spacing={3}>
          {/* Выбор типа валидации */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>⚙️ Тип валидации</Typography>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Метод валидации</InputLabel>
                  <Select
                    value={selectedValidation}
                    label="Метод валидации"
                    onChange={(e) => setSelectedValidation(e.target.value as any)}
                  >
                    <MenuItem value="walk_forward">Walk-Forward валидация</MenuItem>
                    <MenuItem value="cross_validation">Кросс-валидация</MenuItem>
                  </Select>
                </FormControl>
              </CardContent>
            </Card>
          </Grid>

          {/* Настройки Walk-Forward валидации */}
          {selectedValidation === 'walk_forward' && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>📈 Walk-Forward валидация</Typography>

                  {/* Выбор моделей */}
                  <FormControl fullWidth sx={{ mb: 3 }}>
                    <InputLabel>Модели для валидации</InputLabel>
                    <Select
                      multiple
                      value={validationParams.models}
                      label="Модели для валидации"
                      onChange={(e) => handleParamChange('models', e.target.value)}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {(selected as string[]).map((value) => (
                            <Chip
                              key={value}
                              label={availableModels.find(m => m.value === value)?.label || value}
                              size="small"
                            />
                          ))}
                        </Box>
                      )}
                    >
                      {availableModels.map((model) => (
                        <MenuItem key={model.value} value={model.value}>
                          <Checkbox checked={validationParams.models.indexOf(model.value) > -1} />
                          <ListItemText primary={model.label} />
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" gutterBottom>
                        Начальный размер обучающей выборки: {validationParams.initial_train_size}
                      </Typography>
                      <Slider
                        value={validationParams.initial_train_size}
                        onChange={(_, value) => handleParamChange('initial_train_size', value)}
                        min={50}
                        max={200}
                        step={10}
                        marks={[
                          { value: 50, label: '50' },
                          { value: 100, label: '100' },
                          { value: 150, label: '150' },
                          { value: 200, label: '200' }
                        ]}
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" gutterBottom>
                        Размер тестовой выборки: {validationParams.test_size}
                      </Typography>
                      <Slider
                        value={validationParams.test_size}
                        onChange={(_, value) => handleParamChange('test_size', value)}
                        min={10}
                        max={50}
                        step={5}
                        marks={[
                          { value: 10, label: '10' },
                          { value: 20, label: '20' },
                          { value: 30, label: '30' },
                          { value: 50, label: '50' }
                        ]}
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" gutterBottom>
                        Размер шага: {validationParams.step_size}
                      </Typography>
                      <Slider
                        value={validationParams.step_size}
                        onChange={(_, value) => handleParamChange('step_size', value)}
                        min={1}
                        max={20}
                        step={1}
                        marks={[
                          { value: 1, label: '1' },
                          { value: 5, label: '5' },
                          { value: 10, label: '10' },
                          { value: 20, label: '20' }
                        ]}
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={validationParams.expanding_window}
                            onChange={(e) => handleParamChange('expanding_window', e.target.checked)}
                          />
                        }
                        label="Расширяющееся окно"
                      />
                      <Typography variant="caption" display="block" color="text.secondary">
                        Если включено, обучающая выборка будет постоянно расширяться
                      </Typography>
                    </Grid>
                  </Grid>

                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<Science />}
                    onClick={handleStartWalkForward}
                    disabled={walkForwardMutation.isPending || !!currentTaskId}
                    fullWidth
                    sx={{ mt: 3 }}
                  >
                    {walkForwardMutation.isPending ? 'Запуск валидации...' : 'Запустить Walk-Forward валидацию'}
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Настройки кросс-валидации */}
          {selectedValidation === 'cross_validation' && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>🔄
                    Кросс-валидация
                  </Typography>

                  {/* Выбор моделей */}
                  <FormControl fullWidth sx={{ mb: 3 }}>
                    <InputLabel>Модели для валидации</InputLabel>
                    <Select
                      multiple
                      value={crossValidationParams.models}
                      label="Модели для валидации"
                      onChange={(e) => handleCVParamChange('models', e.target.value)}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {(selected as string[]).map((value) => (
                            <Chip
                              key={value}
                              label={availableModels.find(m => m.value === value)?.label || value}
                              size="small"
                            />
                          ))}
                        </Box>
                      )}
                    >
                      {availableModels.map((model) => (
                        <MenuItem key={model.value} value={model.value}>
                          <Checkbox checked={crossValidationParams.models.indexOf(model.value) > -1} />
                          <ListItemText primary={model.label} />
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" gutterBottom>
                        Количество фолдов: {crossValidationParams.cv_folds}
                      </Typography>
                      <Slider
                        value={crossValidationParams.cv_folds}
                        onChange={(_, value) => handleCVParamChange('cv_folds', value)}
                        min={3}
                        max={10}
                        step={1}
                        marks={[
                          { value: 3, label: '3' },
                          { value: 5, label: '5' },
                          { value: 7, label: '7' },
                          { value: 10, label: '10' }
                        ]}
                      />
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={crossValidationParams.stratified}
                            onChange={(e) => handleCVParamChange('stratified', e.target.checked)}
                          />
                        }
                        label="Стратифицированная выборка"
                      />
                      <FormControlLabel
                        control={
                          <Switch
                            checked={crossValidationParams.shuffle}
                            onChange={(e) => handleCVParamChange('shuffle', e.target.checked)}
                          />
                        }
                        label="Перемешивание данных"
                      />
                    </Grid>
                  </Grid>

                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<Science />}
                    onClick={handleStartCrossValidation}
                    disabled={crossValidationMutation.isPending || !!currentTaskId}
                    fullWidth
                    sx={{ mt: 3 }}
                  >
                    {crossValidationMutation.isPending ? 'Запуск валидации...' : 'Запустить кросс-валидацию'}
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Результаты валидации */}
          {taskStatus?.summary && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>📊 Результаты валидации</Typography>

                  {/* Сводная таблица */}
                  <TableContainer component={Paper} sx={{ mb: 3 }}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Модель</TableCell>
                          <TableCell align="right">Точность</TableCell>
                          <TableCell align="right">F1-Score</TableCell>
                          <TableCell align="right">Precision</TableCell>
                          <TableCell align="right">Recall</TableCell>
                          <TableCell align="right">Стабильность</TableCell>
                          <TableCell align="center">Действия</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(taskStatus.summary.model_results || {}).map(([model, results]: [string, any]) => (
                          <TableRow key={model}>
                            <TableCell component="th" scope="row">
                              <Chip
                                label={availableModels.find(m => m.value === model)?.label || model}
                                color="primary"
                                size="small"
                              />
                            </TableCell>
                            <TableCell align="right">{(results.avg_accuracy * 100).toFixed(1)}%</TableCell>
                            <TableCell align="right">{(results.avg_f1 * 100).toFixed(1)}%</TableCell>
                            <TableCell align="right">{(results.avg_precision * 100).toFixed(1)}%</TableCell>
                            <TableCell align="right">{(results.avg_recall * 100).toFixed(1)}%</TableCell>
                            <TableCell align="right">{(results.stability * 100).toFixed(1)}%</TableCell>
                            <TableCell align="center">
                              <IconButton
                                size="small"
                                onClick={() => setShowDetails(showDetails === model ? null : model)}
                              >
                                {showDetails === model ? <ExpandLess /> : <ExpandMore />}
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {/* Детальная информация */}
                  {showDetails && taskStatus.window_details && (
                    <Collapse in={!!showDetails}>
                      <Paper sx={{ p: 2, mb: 2 }}>
                        <Typography variant="subtitle1" gutterBottom>
                          Детали для модели: {availableModels.find(m => m.value === showDetails)?.label || showDetails}
                        </Typography>
                        {renderMetricsChart(
                          taskStatus.window_details.filter((w: any) => w.model === showDetails)
                        )}
                      </Paper>
                    </Collapse>
                  )}

                  {/* График сравнения */}
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>📈 Сравнение моделей</Typography>
                    {renderModelComparison(
                      Object.entries(taskStatus.summary.model_results || {}).map(([model, results]: [string, any]) => ({
                        model: availableModels.find(m => m.value === model)?.label || model,
                        ...results
                      }))
                    )}
                  </Paper>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Кнопка сравнения моделей */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>🏆 Сравнение моделей</Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Комплексное сравнение всех моделей по различным метрикам
                </Typography>

                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<Compare />}
                  onClick={handleCompareModels}
                  disabled={comparisonMutation.isPending}
                  fullWidth
                >
                  {comparisonMutation.isPending ? 'Сравнение...' : 'Сравнить все модели'}
                </Button>

                {/* Результаты сравнения */}
                {comparisonMutation.data && (
                  <Box mt={3}>
                    <Typography variant="h6" gutterBottom>🏅 Результаты сравнения</Typography>
                    <Grid container spacing={2}>
                      {comparisonMutation.data.ranking?.map((item: any, index: number) => (
                        <Grid item xs={12} md={6} key={index}>
                          <Paper
                            sx={{
                              p: 2,
                              bgcolor: index === 0 ? 'success.light' : 'background.default',
                              border: index === 0 ? 2 : 0,
                              borderColor: 'success.main'
                            }}
                          >
                            <Box display="flex" alignItems="center" justifyContent="space-between">
                              <Typography variant="h6">
                                {index + 1}. {availableModels.find(m => m.value === item.model)?.label || item.model}
                              </Typography>
                              {index === 0 && <Typography variant="h4">🏆</Typography>}
                              {index === 1 && <Typography variant="h4">🥈</Typography>}
                              {index === 2 && <Typography variant="h4">🥉</Typography>}
                            </Box>
                            <Typography variant="body2" color="text.secondary">
                              Общий балл: {item.overall_score?.toFixed(3)}
                            </Typography>
                            <Typography variant="caption" display="block">
                              Лучшие метрики: {item.best_metrics?.join(', ')}
                            </Typography>
                          </Paper>
                        </Grid>
                      ))}
                    </Grid>

                    {comparisonMutation.data.recommendation && (
                      <Paper sx={{ p: 2, mt: 2, bgcolor: 'info.light' }}>
                        <Typography variant="h6" color="info.contrastText" gutterBottom>
                          💡 Рекомендация
                        </Typography>
                        <Typography variant="body2" color="info.contrastText">
                          {comparisonMutation.data.recommendation}
                        </Typography>
                      </Paper>
                    )}
                  </Box>
                )}

                {comparisonMutation.isError && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    Ошибка сравнения: {(comparisonMutation.error as Error)?.message}
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* История валидаций */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">📚 История валидаций</Typography>
                  <Button
                    startIcon={<Refresh />}
                    size="small"
                    onClick={() => {/* refetch history */}}
                    disabled={historyLoading}
                  >
                    Обновить
                  </Button>
                </Box>

                {historyLoading ? (
                  <Box display="flex" justifyContent="center" p={2}>
                    <CircularProgress />
                  </Box>
                ) : validationHistory?.length > 0 ? (
                  <TableContainer component={Paper}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Дата</TableCell>
                          <TableCell>Тип</TableCell>
                          <TableCell>Модели</TableCell>
                          <TableCell>Лучшая модель</TableCell>
                          <TableCell align="right">Лучший результат</TableCell>
                          <TableCell align="center">Статус</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {validationHistory.slice(0, 10).map((validation: any, index: number) => (
                          <TableRow key={index}>
                            <TableCell>
                              {new Date(validation.created_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={validation.validation_type}
                                size="small"
                                color="primary"
                              />
                            </TableCell>
                            <TableCell>
                              <Box display="flex" gap={0.5} flexWrap="wrap">
                                {validation.models?.slice(0, 3).map((model: string) => (
                                  <Chip
                                    key={model}
                                    label={availableModels.find(m => m.value === model)?.label || model}
                                    size="small"
                                    variant="outlined"
                                  />
                                ))}
                                {validation.models?.length > 3 && (
                                  <Chip label={`+${validation.models.length - 3}`} size="small" />
                                )}
                              </Box>
                            </TableCell>
                            <TableCell>
                              {validation.best_model && (
                                <Chip
                                  label={availableModels.find(m => m.value === validation.best_model)?.label || validation.best_model}
                                  size="small"
                                  color="success"
                                />
                              )}
                            </TableCell>
                            <TableCell align="right">
                              {validation.best_score ? `${(validation.best_score * 100).toFixed(1)}%` : 'N/A'}
                            </TableCell>
                            <TableCell align="center">
                              <Chip
                                icon={
                                  validation.status === 'completed' ? <CheckCircle /> :
                                  validation.status === 'error' ? <Error /> : <Info />
                                }
                                label={validation.status}
                                size="small"
                                color={
                                  validation.status === 'completed' ? 'success' :
                                  validation.status === 'error' ? 'error' : 'default'
                                }
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Alert severity="info">
                    История валидаций пока отсутствует. Запустите первую валидацию.
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default ValidationAnalysis;