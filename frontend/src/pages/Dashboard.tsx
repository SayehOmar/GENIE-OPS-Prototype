import { useEffect, useState } from 'react';
import StatsCard from '../components/StatsCard';
import { SkeletonCard } from '../components/Skeleton';
import { getSaaSList } from '../api/saas';
import { getSubmissionStats } from '../api/submissions';
import { getDirectories } from '../api/directories';
import { getWorkflowStatus } from '../api/jobs';

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalSaaS: 0,
    totalDirectories: 0,
    totalSubmissions: 0,
    pending: 0,
    submitted: 0,
    approved: 0,
    failed: 0,
  });
  const [workflowStatus, setWorkflowStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  async function loadDashboardData() {
    try {
      const [saasList, directories, submissionStats, workflow] = await Promise.all([
        getSaaSList().catch(() => []),
        getDirectories().catch(() => []),
        getSubmissionStats().catch(() => ({ total: 0, by_status: {} })),
        getWorkflowStatus().catch(() => null),
      ]);

      setStats({
        totalSaaS: saasList.length || 0,
        totalDirectories: directories.length || 0,
        totalSubmissions: submissionStats.total || 0,
        pending: submissionStats.by_status?.pending || 0,
        submitted: submissionStats.by_status?.submitted || 0,
        approved: submissionStats.by_status?.approved || 0,
        failed: submissionStats.by_status?.failed || 0,
      });

      setWorkflowStatus(workflow);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8 animate-slide-in">
        <h1 className="text-4xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-[#8b949e]">Overview of your submissions and workflow</p>
      </div>

      {/* Stats Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} className="delay-100" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Total SaaS Products"
            value={stats.totalSaaS}
            icon="🚀"
            color="blue"
            delay={0}
          />
          <StatsCard
            title="Directories"
            value={stats.totalDirectories}
            icon="📁"
            color="green"
            delay={100}
          />
          <StatsCard
            title="Total Submissions"
            value={stats.totalSubmissions}
            icon="📝"
            color="yellow"
            delay={200}
          />
          <StatsCard
            title="Pending"
            value={stats.pending}
            icon="⏳"
            color="yellow"
            delay={300}
          />
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatsCard
            title="Submitted"
            value={stats.submitted}
            icon="✅"
            color="green"
            delay={400}
          />
          <StatsCard
            title="Approved"
            value={stats.approved}
            icon="🎉"
            color="green"
            delay={500}
          />
          <StatsCard
            title="Failed"
            value={stats.failed}
            icon="❌"
            color="red"
            delay={600}
          />
        </div>
      )}

      {/* Workflow Status */}
      {loading ? (
        <SkeletonCard />
      ) : workflowStatus ? (
        <div className="card animate-fade-in delay-700">
          <h2 className="text-xl font-semibold text-white mb-4">Workflow Manager Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="animate-slide-in delay-800">
              <p className="text-sm text-[#8b949e] mb-1">Status</p>
              <p className={`text-lg font-semibold ${workflowStatus.is_running ? 'text-green-400' : 'text-red-400'}`}>
                {workflowStatus.is_running ? 'Running' : 'Stopped'}
              </p>
            </div>
            <div className="animate-slide-in delay-900">
              <p className="text-sm text-[#8b949e] mb-1">Active Tasks</p>
              <p className="text-lg font-semibold text-white">{workflowStatus.active_tasks || 0}</p>
            </div>
            <div className="animate-slide-in delay-1000">
              <p className="text-sm text-[#8b949e] mb-1">Max Concurrent</p>
              <p className="text-lg font-semibold text-white">{workflowStatus.max_concurrent || 0}</p>
            </div>
            <div className="animate-slide-in delay-1100">
              <p className="text-sm text-[#8b949e] mb-1">Processing Interval</p>
              <p className="text-lg font-semibold text-white">{workflowStatus.processing_interval || 0}s</p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
