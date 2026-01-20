import './Skeleton.css';

interface SkeletonTableProps {
  rows?: number;
  columns?: number;
}

export default function SkeletonTable({ rows = 5, columns = 7 }: SkeletonTableProps) {
  return (
    <div className="skeleton-table bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
      <div className="p-4 border-b border-[#30363d]">
        <div className="skeleton h-4 w-32 rounded"></div>
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-[#30363d]">
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i} className="p-4 text-left">
                <div className="skeleton h-3 w-20 rounded"></div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex} className="border-b border-[#30363d]">
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="p-4">
                  <div className={`skeleton h-4 rounded ${colIndex === 0 ? 'w-32' : colIndex === 1 ? 'w-24' : 'w-20'}`}></div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
