import React from 'react';

interface ChartTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
  className?: string;
}

const ChartTooltip: React.FC<ChartTooltipProps> = ({ active, payload, label, className = '' }) => {
  if (!active || !payload || !payload.length) {
    return null;
  }

  return (
    <div className={`bg-gray-800 text-white p-3 rounded-lg shadow-xl border border-gray-600 ${className}`}>
      {label && <div className="font-bold mb-2">{label}</div>}
      <div className="space-y-1">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between space-x-4">
            <div className="flex items-center">
              <div
                className="w-3 h-3 rounded-full mr-2"
                style={{ backgroundColor: entry.color }}
              ></div>
              <span>{entry.name}</span>
            </div>
            <span className="font-semibold">{entry.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChartTooltip;