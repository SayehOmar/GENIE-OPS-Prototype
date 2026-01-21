import { useEffect, useState } from 'react';
import StatsCard from '../components/StatsCard';
import { SkeletonCard } from '../components/Skeleton';
// @ts-ignore - JS module
import { getSaaSList } from '../api/saas';
// @ts-ignore - JS module
import { getSubmissionStats, getSubmissions } from '../api/submissions';
// @ts-ignore - JS module
import { getDirectories } from '../api/directories';
// @ts-ignore - JS module
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
  const [recentSubmissions, setRecentSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  async function loadDashboardData() {
    try {
      const [saasList, directories, submissionStats, workflow, submissions] = await Promise.all([
        getSaaSList().catch(() => []),
        getDirectories().catch(() => []),
        getSubmissionStats().catch(() => ({ total: 0, by_status: {} })),
        getWorkflowStatus().catch(() => null),
        getSubmissions().catch(() => []),
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

      // Get recent submissions (last 5)
      const recent = submissions
        .sort((a: any, b: any) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        .slice(0, 5);
      setRecentSubmissions(recent);

      setWorkflowStatus(workflow);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setLoading(false);
    }
  }

  function calculateSuccessRate() {
    const { totalSubmissions, failed } = stats;
    if (totalSubmissions === 0) return 0;
    const successful = totalSubmissions - failed;
    return Math.round((successful / totalSubmissions) * 100);
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

      {/* Success Rate & Additional Stats */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <StatsCard
            title="Success Rate"
            value={`${calculateSuccessRate()}%`}
            icon="📊"
            color={calculateSuccessRate() >= 80 ? 'green' : calculateSuccessRate() >= 50 ? 'yellow' : 'red'}
            delay={700}
          />
          <StatsCard
            title="Processing Rate"
            value={`${stats.submitted + stats.approved}/${stats.totalSubmissions || 1}`}
            icon="⚡"
            color="blue"
            delay={800}
          />
        </div>
      )}

      {/* Recent Submissions */}
      {!loading && recentSubmissions.length > 0 && (
        <div className="card animate-fade-in delay-900 mb-8">
          <h2 className="text-xl font-semibold text-white mb-4">Recent Submissions</h2>
          <div className="space-y-3">
            {recentSubmissions.map((sub: any, index: number) => (
              <div
                key={sub.id}
                className="flex items-center justify-between p-3 rounded-lg border border-[#30363d] hover:border-[#58a6ff] transition-colors animate-slide-in"
                style={{ animationDelay: `${900 + index * 50}ms` }}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-[#8b949e] font-mono">#{sub.id}</span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      sub.status === 'approved' ? 'bg-green-500/10 text-green-400' :
                      sub.status === 'submitted' ? 'bg-blue-500/10 text-blue-400' :
                      sub.status === 'pending' ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>
                      {sub.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-[#8b949e] mt-1">
                    Created {new Date(sub.created_at).toLocaleString()}
                  </p>
                </div>
                {sub.retry_count > 0 && (
                  <span className="text-xs text-yellow-400" title="Retry attempts">
                    {sub.retry_count} retries
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Workflow Status */}
      {loading ? (
        <SkeletonCard />
      ) : workflowStatus ? (
        <div className="card animate-fade-in delay-1000">
          <h2 className="text-xl font-semibold text-white mb-4">Workflow Manager Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="animate-slide-in delay-1100">
              <p className="text-sm text-[#8b949e] mb-1">Status</p>
              <p className={`text-lg font-semibold ${workflowStatus.is_running ? 'text-green-400' : 'text-red-400'}`}>
                {workflowStatus.is_running ? 'Running' : 'Stopped'}
              </p>
            </div>
            <div className="animate-slide-in delay-1200">
              <p className="text-sm text-[#8b949e] mb-1">Active Tasks</p>
              <p className="text-lg font-semibold text-white">{workflowStatus.active_tasks || 0}</p>
            </div>
            <div className="animate-slide-in delay-1300">
              <p className="text-sm text-[#8b949e] mb-1">Max Concurrent</p>
              <p className="text-lg font-semibold text-white">{workflowStatus.max_concurrent || 0}</p>
            </div>
            <div className="animate-slide-in delay-1400">
              <p className="text-sm text-[#8b949e] mb-1">Processing Interval</p>
              <p className="text-lg font-semibold text-white">{workflowStatus.processing_interval || 0}s</p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
