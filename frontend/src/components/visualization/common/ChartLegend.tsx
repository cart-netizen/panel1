import React from 'react';

interface ChartLegendProps {
  data: Array<{
    value: string;
    color: string;
    label?: string;
  }>;
  className?: string;
}

const ChartLegend: React.FC<ChartLegendProps> = ({ data, className = '' }) => {
  return (
    <div className={`flex flex-wrap justify-center gap-4 ${className}`}>
      {data.map((item, index) => (
        <div key={index} className="flex items-center space-x-2">
          <div
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: item.color }}
          ></div>
          <span className="text-sm font-medium">{item.label || item.value}</span>
        </div>
      ))}
    </div>
  );
};

export default ChartLegend;