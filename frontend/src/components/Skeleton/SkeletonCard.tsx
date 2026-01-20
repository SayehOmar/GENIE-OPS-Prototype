import './Skeleton.css';

interface SkeletonCardProps {
  className?: string;
}

export default function SkeletonCard({ className = '' }: SkeletonCardProps) {
  return (
    <div className={`skeleton-card bg-[#161b22] border border-[#30363d] rounded-xl p-6 ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="skeleton h-4 w-24 mb-3 rounded"></div>
          <div className="skeleton h-8 w-32 mb-2 rounded"></div>
          <div className="skeleton h-3 w-16 rounded"></div>
        </div>
        <div className="skeleton w-12 h-12 rounded-lg"></div>
      </div>
    </div>
  );
}
