// frontend/src/utils/chart-utils.ts
export const generateChartColors = (count: number): string[] => {
  const colors = [
    '#3B82F6', '#EF4444', '#10B981', '#F59E0B',
    '#8B5CF6', '#F97316', '#06B6D4', '#84CC16'
  ];
  return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
};

export const formatChartData = (data: any[], xKey: string, yKey: string) => {
  return data.map(item => ({
    x: item[xKey],
    y: item[yKey],
  }));
};

export const getChartOptions = (title: string) => ({
  responsive: true,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: true,
      text: title,
    },
  },
});