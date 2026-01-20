import './StatsCard.css';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color?: 'blue' | 'green' | 'yellow' | 'red';
  delay?: number;
}

export default function StatsCard({ title, value, icon, trend, color = 'blue', delay = 0 }: StatsCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
  };

  return (
    <div 
      className="stats-card bg-[#161b22] border border-[#30363d] rounded-xl p-6 transition-all duration-300 hover:border-[#58a6ff] hover:shadow-lg hover:shadow-blue-500/10"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-[#8b949e] mb-1">{title}</p>
          <p className="text-3xl font-bold text-white mb-1">{value}</p>
          {trend && (
            <p className={`text-sm mt-2 flex items-center gap-1 ${trend.isPositive ? 'text-green-400' : 'text-red-400'}`}>
              <span>{trend.isPositive ? '↑' : '↓'}</span>
              <span>{Math.abs(trend.value)}%</span>
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg border ${colorClasses[color]} icon-container`}>
          <span className="text-2xl">{icon}</span>
        </div>
      </div>
    </div>
  );
}
