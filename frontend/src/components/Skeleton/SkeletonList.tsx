import './Skeleton.css';

interface SkeletonListProps {
  items?: number;
}

export default function SkeletonList({ items = 3 }: SkeletonListProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: items }).map((_, index) => (
        <div
          key={index}
          className="skeleton-card bg-[#161b22] border border-[#30363d] rounded-xl p-6"
          style={{ animationDelay: `${index * 100}ms` }}
        >
          <div className="skeleton h-6 w-3/4 mb-4 rounded"></div>
          <div className="skeleton h-4 w-full mb-2 rounded"></div>
          <div className="skeleton h-4 w-5/6 mb-4 rounded"></div>
          <div className="flex gap-2 mb-4">
            <div className="skeleton h-6 w-16 rounded"></div>
            <div className="skeleton h-6 w-20 rounded"></div>
          </div>
          <div className="flex gap-2">
            <div className="skeleton h-10 flex-1 rounded-lg"></div>
            <div className="skeleton h-10 w-20 rounded-lg"></div>
          </div>
        </div>
      ))}
    </div>
  );
}
