import { useEffect, useState } from 'react';
import StatsCard from '../components/StatsCard';
import { SkeletonCard } from '../components/Skeleton';
// @ts-ignore - JS module
import { getSaaSList } from '../api/saas';
// @ts-ignore - JS module
import { getSubmissionStats, getSubmissions, retrySubmission, deleteSubmission } from '../api/submissions';
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
    processing: 0,
    submitted: 0,
    approved: 0,
    failed: 0,
    successRate: 0,
  });
  const [workflowStatus, setWorkflowStatus] = useState<any>(null);
  const [recentSubmissions, setRecentSubmissions] = useState<any[]>([]);
  const [failedSubmissions, setFailedSubmissions] = useState<any[]>([]);
  const [successfulSubmissions, setSuccessfulSubmissions] = useState<any[]>([]);
  const [saasList, setSaaSList] = useState<any[]>([]);
  const [directories, setDirectories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<any | null>(null);

  useEffect(() => {
    loadDashboardData();
    
    // Start with default polling interval
    let pollInterval = 30000; // Default: 30 seconds
    
    const interval = setInterval(() => {
      loadDashboardData();
    }, pollInterval);
    
    return () => clearInterval(interval);
  }, []);
  
  // Separate effect for faster polling when there are active tasks
  useEffect(() => {
    if (!workflowStatus || workflowStatus.active_tasks === 0) {
      return; // Use default polling from main effect
    }
    
    // When there are active tasks, poll more frequently
    const fastInterval = setInterval(() => {
      loadDashboardData();
    }, 5000); // Poll every 5 seconds when active
    
    return () => clearInterval(fastInterval);
  }, [workflowStatus?.active_tasks]);

  async function loadDashboardData() {
    try {
      const [saas, dirs, submissionStats, workflow, submissions] = await Promise.all([
        getSaaSList().catch(() => []),
        getDirectories().catch(() => []),
        getSubmissionStats().catch(() => ({ total: 0, by_status: {} })),
        getWorkflowStatus().catch(() => null),
        getSubmissions().catch(() => []),
      ]);

      setSaaSList(saas);
      setDirectories(dirs);

      // Get processing count from stats or workflow status
      const processingCount = submissionStats.processing || 
                             (workflow?.active_tasks || 0);
      
      setStats({
        totalSaaS: saas.length || 0,
        totalDirectories: dirs.length || 0,
        totalSubmissions: submissionStats.total || 0,
        pending: (submissionStats.by_status?.pending || 0) + processingCount, // Include processing in pending
        processing: processingCount,
        submitted: submissionStats.by_status?.submitted || 0,
        approved: submissionStats.by_status?.approved || 0,
        failed: submissionStats.by_status?.failed || 0,
        successRate: submissionStats.success_rate || 0,
      });

      // Enrich submissions with SaaS and Directory data
      const enriched = submissions.map((sub: any) => ({
        ...sub,
        saas: saas.find((s: any) => s.id === sub.saas_id),
        directory: dirs.find((d: any) => d.id === sub.directory_id),
      }));

      // Get recent submissions (last 5)
      const recent = enriched
        .sort((a: any, b: any) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        .slice(0, 5);
      setRecentSubmissions(recent);

      // Get failed submissions (for retry section)
      const failed = enriched
        .filter((s: any) => s.status === 'failed')
        .sort((a: any, b: any) => 
          new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime()
        )
        .slice(0, 10);
      setFailedSubmissions(failed);

      // Get successful submissions (submitted + approved)
      const successful = enriched
        .filter((s: any) => s.status === 'submitted' || s.status === 'approved')
        .sort((a: any, b: any) => 
          new Date(b.submitted_at || b.created_at).getTime() - new Date(a.submitted_at || a.created_at).getTime()
        )
        .slice(0, 10);
      setSuccessfulSubmissions(successful);

      setWorkflowStatus(workflow);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setLoading(false);
    }
  }

  async function handleRetry(submissionId: number) {
    if (!confirm('Retry this failed submission?')) return;

    setRetrying(submissionId);
    try {
      await retrySubmission(submissionId);
      await loadDashboardData();
      alert('Submission queued for retry');
    } catch (error: any) {
      alert(error.message || 'Failed to retry submission');
    } finally {
      setRetrying(null);
    }
  }

  /**
   * Delete a failed submission permanently
   * Removes the submission record from the database
   * @param {number} submissionId - ID of the submission to delete
   */
  async function handleDelete(submissionId: number) {
    if (!confirm('Are you sure you want to delete this submission? This action cannot be undone.')) return;

    setDeleting(submissionId);
    try {
      await deleteSubmission(submissionId);
      await loadDashboardData();
      alert('Submission deleted successfully');
    } catch (error: any) {
      alert(error.message || 'Failed to delete submission');
    } finally {
      setDeleting(null);
    }
  }

  function handleViewDetails(submission: any) {
    setSelectedSubmission(submission);
  }

  function closeDetailsModal() {
    setSelectedSubmission(null);
  }

  function parseFormData(formDataString: string | null) {
    if (!formDataString) return null;
    try {
      return JSON.parse(formDataString);
    } catch {
      return null;
    }
  }

  function calculateSuccessRate() {
    // Use successRate from stats if available (calculated on backend excluding pending/processing)
    if (stats.successRate > 0) {
      return stats.successRate;
    }
    // Fallback calculation: exclude pending and processing from denominator
    const { failed, submitted, approved, pending, processing } = stats;
    const completed = submitted + approved + failed;
    if (completed === 0) return 0;
    const successful = submitted + approved;
    return Math.round((successful / completed) * 100);
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatsCard
            title="Success Rate"
            value={`${calculateSuccessRate()}%`}
            icon="📊"
            color={calculateSuccessRate() >= 80 ? 'green' : calculateSuccessRate() >= 50 ? 'yellow' : 'red'}
            delay={700}
          />
          {stats.processing > 0 && (
            <StatsCard
              title="Processing"
              value={stats.processing}
              icon="⚙️"
              color="purple"
              delay={750}
            />
          )}
          <StatsCard
            title="Completed"
            value={`${stats.submitted + stats.approved + stats.failed}`}
            icon="✅"
            color="blue"
            delay={800}
          />
        </div>
      )}

      {/* Failed Submissions with Retry */}
      {!loading && failedSubmissions.length > 0 && (
        <div className="card animate-fade-in delay-900 mb-8 border-red-500/20">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="text-red-400">❌</span>
              Failed Submissions ({failedSubmissions.length})
            </h2>
            <span className="text-sm text-[#8b949e]">Click Retry to resubmit</span>
          </div>
          <div className="space-y-3">
            {failedSubmissions.map((sub: any, index: number) => (
              <div
                key={sub.id}
                className="flex items-center justify-between p-4 rounded-lg border border-red-500/20 bg-red-500/5 hover:border-red-500/40 transition-colors animate-slide-in cursor-pointer"
                style={{ animationDelay: `${900 + index * 50}ms` }}
                onClick={() => handleViewDetails(sub)}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-sm text-[#8b949e] font-mono">#{sub.id}</span>
                    <span className="px-2 py-1 rounded text-xs font-medium bg-red-500/10 text-red-400">
                      FAILED
                    </span>
                    {sub.retry_count > 0 && (
                      <span className="text-xs text-yellow-400" title="Retry attempts">
                        {sub.retry_count} retries
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-white mb-1">
                    <strong>{sub.saas?.name || `SaaS #${sub.saas_id}`}</strong>
                    {' → '}
                    <strong>{sub.directory?.name || `Directory #${sub.directory_id}`}</strong>
                  </div>
                  {sub.error_message && (
                    <p className="text-xs text-red-400 mt-1 line-clamp-2">
                      {sub.error_message}
                    </p>
                  )}
                  <p className="text-xs text-[#8b949e] mt-2">
                    Failed {new Date(sub.updated_at || sub.created_at).toLocaleString()}
                  </p>
                  <p className="text-xs text-[#58a6ff] mt-2 font-medium">
                    Click to view details →
                  </p>
                </div>
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRetry(sub.id);
                    }}
                    disabled={retrying === sub.id || deleting === sub.id}
                    className="btn btn-secondary text-sm px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {retrying === sub.id ? (
                      <span className="flex items-center gap-2">
                        <span className="animate-spin">⏳</span>
                        Retrying...
                      </span>
                    ) : (
                      'Retry'
                    )}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(sub.id);
                    }}
                    disabled={retrying === sub.id || deleting === sub.id}
                    className="btn bg-red-500/20 hover:bg-red-500/30 text-red-400 border-red-500/30 text-sm px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {deleting === sub.id ? (
                      <span className="flex items-center gap-2">
                        <span className="animate-spin">⏳</span>
                        Deleting...
                      </span>
                    ) : (
                      'Delete'
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Successful Submissions */}
      {!loading && successfulSubmissions.length > 0 && (
        <div className="card animate-fade-in delay-950 mb-8 border-green-500/20">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="text-green-400">✅</span>
              Successful Submissions ({successfulSubmissions.length})
            </h2>
          </div>
          <div className="space-y-3">
            {successfulSubmissions.map((sub: any, index: number) => (
              <div
                key={sub.id}
                className="flex items-center justify-between p-4 rounded-lg border border-green-500/20 bg-green-500/5 hover:border-green-500/40 transition-colors animate-slide-in"
                style={{ animationDelay: `${950 + index * 50}ms` }}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-sm text-[#8b949e] font-mono">#{sub.id}</span>
                    {(() => {
                      // Check if this submission is currently being processed
                      const isProcessing = workflowStatus?.active_submission_ids?.includes(sub.id) || false;
                      const displayStatus = isProcessing ? 'processing' : sub.status;
                      
                      return (
                        <span className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 ${
                          displayStatus === 'approved' 
                            ? 'bg-green-500/10 text-green-400' 
                            : displayStatus === 'processing'
                            ? 'bg-purple-500/10 text-purple-400'
                            : 'bg-blue-500/10 text-blue-400'
                        }`}>
                          {isProcessing && <span className="animate-spin">⏳</span>}
                          {displayStatus.toUpperCase()}
                        </span>
                      );
                    })()}
                  </div>
                  <div className="text-sm text-white mb-1">
                    <strong>{sub.saas?.name || `SaaS #${sub.saas_id}`}</strong>
                    {' → '}
                    <strong>{sub.directory?.name || `Directory #${sub.directory_id}`}</strong>
                  </div>
                  {sub.submitted_at && (
                    <p className="text-xs text-[#8b949e] mt-2">
                      Submitted {new Date(sub.submitted_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedSubmission(sub);
                    }}
                    className="btn btn-secondary text-sm px-4 py-2"
                  >
                    View Logs
                  </button>
                  {sub.directory?.url && (
                    <a
                      href={sub.directory.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary text-sm px-4 py-2"
                    >
                      View
                    </a>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(sub.id);
                    }}
                    disabled={deleting === sub.id}
                    className="btn bg-red-500/20 hover:bg-red-500/30 text-red-400 border-red-500/30 text-sm px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {deleting === sub.id ? (
                      <span className="flex items-center gap-2">
                        <span className="animate-spin">⏳</span>
                        Deleting...
                      </span>
                    ) : (
                      'Delete'
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Submissions */}
      {!loading && recentSubmissions.length > 0 && (
        <div className="card animate-fade-in delay-1000 mb-8">
          <h2 className="text-xl font-semibold text-white mb-4">Recent Submissions</h2>
          <div className="space-y-3">
            {recentSubmissions.map((sub: any, index: number) => (
              <div
                key={sub.id}
                className="flex items-center justify-between p-3 rounded-lg border border-[#30363d] hover:border-[#58a6ff] transition-colors animate-slide-in"
                style={{ animationDelay: `${1000 + index * 50}ms` }}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-[#8b949e] font-mono">#{sub.id}</span>
                    {(() => {
                      // Check if this submission is currently being processed
                      const isProcessing = workflowStatus?.active_submission_ids?.includes(sub.id) || false;
                      const displayStatus = isProcessing ? 'processing' : sub.status;
                      
                      return (
                        <span className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 ${
                          displayStatus === 'approved' ? 'bg-green-500/10 text-green-400' :
                          displayStatus === 'submitted' ? 'bg-blue-500/10 text-blue-400' :
                          displayStatus === 'processing' ? 'bg-purple-500/10 text-purple-400' :
                          displayStatus === 'pending' ? 'bg-yellow-500/10 text-yellow-400' :
                          'bg-red-500/10 text-red-400'
                        }`}>
                          {isProcessing && <span className="animate-spin">⏳</span>}
                          {displayStatus.toUpperCase()}
                        </span>
                      );
                    })()}
                  </div>
                  <div className="text-sm text-white mt-1">
                    {sub.saas?.name || `SaaS #${sub.saas_id}`} → {sub.directory?.name || `Directory #${sub.directory_id}`}
                  </div>
                  <p className="text-sm text-[#8b949e] mt-1">
                    Created {new Date(sub.created_at).toLocaleString()}
                  </p>
                  {(() => {
                    const isProcessing = workflowStatus?.active_submission_ids?.includes(sub.id) || false;
                    if (isProcessing) {
                      const progress = workflowStatus?.active_submissions?.find((a: any) => a.submission_id === sub.id);
                      if (progress) {
                        return (
                          <div className="mt-2 flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-[#30363d] rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-purple-500 transition-all duration-300"
                                style={{ width: `${progress.progress || 0}%` }}
                              />
                            </div>
                            <span className="text-xs text-purple-400">{progress.progress || 0}%</span>
                          </div>
                        );
                      }
                    }
                    return null;
                  })()}
                </div>
                {sub.retry_count > 0 && !workflowStatus?.active_submission_ids?.includes(sub.id) && (
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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="animate-slide-in delay-1100">
              <p className="text-sm text-[#8b949e] mb-1">Status</p>
              <p className={`text-lg font-semibold ${workflowStatus.is_running ? 'text-green-400' : 'text-red-400'}`}>
                {workflowStatus.is_running ? 'Running' : 'Stopped'}
              </p>
            </div>
            <div className="animate-slide-in delay-1200">
              <p className="text-sm text-[#8b949e] mb-1">Active Tasks</p>
              <p className="text-lg font-semibold text-purple-400">{workflowStatus.active_tasks || 0}</p>
            </div>
            <div className="animate-slide-in delay-1300">
              <p className="text-sm text-[#8b949e] mb-1">Queue Length</p>
              <p className="text-lg font-semibold text-yellow-400">{workflowStatus.queue_length || 0}</p>
            </div>
            <div className="animate-slide-in delay-1400">
              <p className="text-sm text-[#8b949e] mb-1">Max Concurrent</p>
              <p className="text-lg font-semibold text-white">{workflowStatus.max_concurrent || 0}</p>
            </div>
          </div>
          
          {/* Active Submissions List */}
          {workflowStatus.active_submissions && workflowStatus.active_submissions.length > 0 && (
            <div className="mt-4 p-4 bg-[#161b22] rounded-lg border border-[#30363d]">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <span className="animate-spin">⚙️</span>
                Active Submissions ({workflowStatus.active_submissions.length})
              </h3>
              <div className="space-y-2">
                {workflowStatus.active_submissions.map((active: any) => (
                  <div key={active.submission_id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-[#8b949e] font-mono">#{active.submission_id}</span>
                      <span className="text-purple-400">{active.message || 'Processing...'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-[#30363d] rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-purple-500 transition-all duration-300"
                          style={{ width: `${active.progress || 0}%` }}
                        />
                      </div>
                      <span className="text-xs text-[#8b949e] w-10 text-right">{active.progress || 0}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : null}

      {/* Submission Details Modal */}
      {selectedSubmission && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 animate-fade-in"
          onClick={closeDetailsModal}
        >
          <div
            className="card max-w-4xl w-full max-h-[90vh] overflow-y-auto animate-slide-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white">
                Submission Details #{selectedSubmission.id}
              </h2>
              <button
                onClick={closeDetailsModal}
                className="text-[#8b949e] hover:text-white text-2xl"
              >
                ×
              </button>
            </div>

            {/* Basic Info */}
            <div className="mb-6 p-4 bg-[#161b22] rounded-lg border border-[#30363d]">
              <h3 className="text-lg font-semibold text-white mb-3">Submission Information</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-[#8b949e]">SaaS Product:</span>
                  <p className="text-white font-medium">
                    {selectedSubmission.saas?.name || `SaaS #${selectedSubmission.saas_id}`}
                  </p>
                </div>
                <div>
                  <span className="text-[#8b949e]">Directory:</span>
                  <p className="text-white font-medium">
                    {selectedSubmission.directory?.name || `Directory #${selectedSubmission.directory_id}`}
                  </p>
                </div>
                <div>
                  <span className="text-[#8b949e]">Status:</span>
                  <p className="text-red-400 font-medium">FAILED</p>
                </div>
                <div>
                  <span className="text-[#8b949e]">Retry Count:</span>
                  <p className="text-white font-medium">{selectedSubmission.retry_count || 0}</p>
                </div>
                <div>
                  <span className="text-[#8b949e]">Failed At:</span>
                  <p className="text-white">
                    {new Date(selectedSubmission.updated_at || selectedSubmission.created_at).toLocaleString()}
                  </p>
                </div>
                {selectedSubmission.directory?.url && (
                  <div>
                    <span className="text-[#8b949e]">Directory URL:</span>
                    <a
                      href={selectedSubmission.directory.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#58a6ff] hover:underline block"
                    >
                      {selectedSubmission.directory.url}
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Workflow Execution Log - Prominent Section */}
            {(() => {
              const formData = parseFormData(selectedSubmission.form_data);
              const errorMsg = selectedSubmission.error_message || '';
              // Check if submission is currently being processed
              const isProcessing = workflowStatus?.active_submission_ids?.includes(selectedSubmission.id) || false;
              const submissionStatus = isProcessing ? 'processing' : (selectedSubmission.status || 'pending');
              const isSuccessful = submissionStatus === 'submitted' || submissionStatus === 'approved';
              
              // Reconstruct workflow steps from available data
              const workflowSteps = [];
              
              // Step 1: Navigation
              // Check if navigation failed by looking at error message
              const navFailed = errorMsg.toLowerCase().includes('failed to navigate') || 
                               errorMsg.toLowerCase().includes('navigation failed') ||
                               errorMsg.toLowerCase().includes('navigation timeout');
              
              workflowSteps.push({
                step: 1,
                name: 'Navigate to Directory',
                status: navFailed ? 'failed' : 'success',
                message: navFailed 
                  ? errorMsg.includes('Failed to navigate') 
                    ? errorMsg 
                    : `Failed to navigate to ${selectedSubmission.directory?.url || 'directory URL'}`
                  : `Navigated to ${selectedSubmission.directory?.url || 'directory URL'}`,
                timestamp: selectedSubmission.created_at,
                duration: null
              });
              
              // Step 2: Form Detection
              // Skip if navigation failed
              if (navFailed) {
                workflowSteps.push({
                  step: 2,
                  name: 'Detect Submission Form',
                  status: 'failed',
                  message: 'Skipped - navigation failed',
                  timestamp: null
                });
              } else if (formData && formData.form_structure) {
                const fieldCount = formData.total_fields || 0;
                workflowSteps.push({
                  step: 2,
                  name: 'Detect Submission Form',
                  status: fieldCount > 0 ? 'success' : 'warning',
                  message: fieldCount > 0 
                    ? `Form detected with ${fieldCount} fields`
                    : 'Form detected but no fields found (form may be empty or not fully loaded)',
                  timestamp: null
                });
              } else {
                workflowSteps.push({
                  step: 2,
                  name: 'Detect Submission Form',
                  status: 'warning',
                  message: 'Form detection status unknown',
                  timestamp: null
                });
              }
              
              // Step 3: Form Analysis
              // Skip if navigation failed
              if (navFailed) {
                workflowSteps.push({
                  step: 3,
                  name: 'Analyze Form Structure',
                  status: 'failed',
                  message: 'Skipped - navigation failed',
                  timestamp: null
                });
              } else if (formData) {
                const analysisMethod = formData.analysis_method || 'unknown';
                const methodLabel = analysisMethod === 'ai' ? 'AI (Ollama)' : analysisMethod === 'dom' ? 'DOM Extraction' : 'Unknown';
                workflowSteps.push({
                  step: 3,
                  name: 'Analyze Form Structure',
                  status: formData.form_structure && formData.form_structure.fields ? 'success' : 'failed',
                  message: `Analysis method: ${methodLabel}. Detected ${formData.total_fields || 0} fields.`,
                  timestamp: null
                });
              } else {
                workflowSteps.push({
                  step: 3,
                  name: 'Analyze Form Structure',
                  status: 'failed',
                  message: 'Form analysis failed - no form structure data available',
                  timestamp: null
                });
              }
              
              // Step 4: Field Mapping
              // Skip if navigation failed
              if (navFailed) {
                workflowSteps.push({
                  step: 4,
                  name: 'Map SaaS Data to Form Fields',
                  status: 'failed',
                  message: 'Skipped - navigation failed',
                  timestamp: null
                });
              } else if (formData && formData.form_structure && formData.form_structure.fields) {
                const mappedCount = formData.fields_filled || 0;
                const totalFields = formData.total_fields || 0;
                workflowSteps.push({
                  step: 4,
                  name: 'Map SaaS Data to Form Fields',
                  status: mappedCount > 0 ? 'success' : 'failed',
                  message: `Mapped ${mappedCount} out of ${totalFields} fields`,
                  timestamp: null
                });
              } else {
                workflowSteps.push({
                  step: 4,
                  name: 'Map SaaS Data to Form Fields',
                  status: 'failed',
                  message: 'Field mapping failed - no form structure available',
                  timestamp: null
                });
              }
              
              // Step 5: Fill Form Fields
              if (formData) {
                const filledCount = formData.fields_filled || 0;
                const totalFields = formData.total_fields || 0;
                const fillErrors = formData.fill_errors || [];
                
                if (filledCount === 0) {
                  workflowSteps.push({
                    step: 5,
                    name: 'Fill Form Fields',
                    status: 'failed',
                    message: `Failed to fill any fields. ${fillErrors.length} errors occurred.`,
                    errors: fillErrors,
                    timestamp: null
                  });
                } else if (fillErrors.length > 0) {
                  workflowSteps.push({
                    step: 5,
                    name: 'Fill Form Fields',
                    status: 'partial',
                    message: `Filled ${filledCount} out of ${totalFields} fields. ${fillErrors.length} fields failed.`,
                    errors: fillErrors,
                    timestamp: null
                  });
                } else {
                  workflowSteps.push({
                    step: 5,
                    name: 'Fill Form Fields',
                    status: 'success',
                    message: `Successfully filled ${filledCount} out of ${totalFields} fields`,
                    timestamp: null
                  });
                }
              } else {
                workflowSteps.push({
                  step: 5,
                  name: 'Fill Form Fields',
                  status: 'failed',
                  message: 'Field filling failed - no form data available',
                  timestamp: null
                });
              }
              
              // Step 6: Submit Form
              // Check if submission was successful based on status and form data
              const submitSuccess = isSuccessful || (formData && formData.fields_filled > 0 && !errorMsg);
              const submitFailed = errorMsg.toLowerCase().includes('submit') || 
                                   (formData && formData.fields_filled === 0) ||
                                   (!isSuccessful && !isProcessing && errorMsg);
              
              if (submitFailed && !isSuccessful) {
                // Only show as failed if there's an actual error and not successful
                workflowSteps.push({
                  step: 6,
                  name: 'Submit Form',
                  status: 'failed',
                  message: errorMsg.toLowerCase().includes('submit') 
                    ? errorMsg 
                    : formData && formData.fields_filled === 0
                    ? 'Form submission failed - no fields were filled'
                    : 'Form submission failed - could not complete submission',
                  timestamp: selectedSubmission.updated_at
                });
              } else if (submitSuccess || isSuccessful) {
                // Show as success if submission status is submitted/approved or form was filled successfully
                workflowSteps.push({
                  step: 6,
                  name: 'Submit Form',
                  status: 'success',
                  message: isSuccessful 
                    ? 'Form submitted successfully' 
                    : formData && formData.fields_filled > 0
                    ? `Form submitted successfully - ${formData.fields_filled} fields filled`
                    : 'Form submission completed',
                  timestamp: selectedSubmission.submitted_at || selectedSubmission.updated_at
                });
              } else {
                // Default to pending if still processing
                workflowSteps.push({
                  step: 6,
                  name: 'Submit Form',
                  status: isProcessing ? 'pending' : 'failed',
                  message: isProcessing 
                    ? 'Submitting form...' 
                    : 'Form submission status unclear',
                  timestamp: selectedSubmission.updated_at
                });
              }
              
              // Step 7: Verify Submission
              // Check if submission was verified as successful
              if (isSuccessful) {
                workflowSteps.push({
                  step: 7,
                  name: 'Verify Submission',
                  status: 'success',
                  message: submissionStatus === 'approved' 
                    ? 'Submission verified and approved' 
                    : 'Submission verified successfully',
                  timestamp: selectedSubmission.submitted_at || selectedSubmission.updated_at
                });
              } else if (submitFailed && !isProcessing) {
                workflowSteps.push({
                  step: 7,
                  name: 'Verify Submission',
                  status: 'failed',
                  message: errorMsg || 'Submission verification failed - submission was not successful',
                  timestamp: selectedSubmission.updated_at
                });
              } else {
                // Still processing or status unclear
                workflowSteps.push({
                  step: 7,
                  name: 'Verify Submission',
                  status: isProcessing ? 'pending' : 'failed',
                  message: isProcessing 
                    ? 'Verifying submission...' 
                    : 'Submission verification status unclear',
                  timestamp: selectedSubmission.updated_at
                });
              }
              
              return (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                      <span>📋</span>
                      Workflow Execution Log
                    </h3>
                    {isProcessing ? (
                      <span className="px-3 py-1 rounded-full text-sm font-medium border bg-purple-500/20 text-purple-400 border-purple-500/30 flex items-center gap-2">
                        <span className="animate-spin">⏳</span>
                        PROCESSING
                      </span>
                    ) : isSuccessful ? (
                      <span className={`px-3 py-1 rounded-full text-sm font-medium border ${
                        submissionStatus === 'approved' 
                          ? 'bg-green-500/20 text-green-400 border-green-500/30'
                          : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                      }`}>
                        {submissionStatus === 'approved' ? 'APPROVED' : 'SUBMITTED'}
                      </span>
                    ) : errorMsg ? (
                      <span className="px-3 py-1 rounded-full text-sm font-medium bg-red-500/20 text-red-400 border border-red-500/30">
                        FAILED
                      </span>
                    ) : (
                      <span className="px-3 py-1 rounded-full text-sm font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                        PENDING
                      </span>
                    )}
                  </div>
                  
                  {/* Processing Indicator - Show when submission is being processed */}
                  {isProcessing && (
                    <div className="mb-4 p-4 bg-purple-500/10 border-2 border-purple-500/30 rounded-lg">
                      <h4 className="font-bold text-purple-400 mb-2 flex items-center gap-2">
                        <span className="animate-spin">⚙️</span>
                        Processing Submission...
                      </h4>
                      <div className="space-y-2 font-medium text-purple-300">
                        {(() => {
                          const progress = workflowStatus?.active_submissions?.find((a: any) => a.submission_id === selectedSubmission.id);
                          if (progress) {
                            return (
                              <>
                                <p>{progress.message || 'Processing submission...'}</p>
                                <div className="mt-2">
                                  <div className="flex items-center justify-between text-sm mb-1">
                                    <span>Progress</span>
                                    <span>{progress.progress || 0}%</span>
                                  </div>
                                  <div className="w-full h-2 bg-[#30363d] rounded-full overflow-hidden">
                                    <div 
                                      className="h-full bg-purple-500 transition-all duration-300"
                                      style={{ width: `${progress.progress || 0}%` }}
                                    />
                                  </div>
                                </div>
                                {progress.started_at && (
                                  <p className="text-sm opacity-75 mt-2">
                                    Started: {new Date(progress.started_at).toLocaleString()}
                                  </p>
                                )}
                              </>
                            );
                          }
                          return <p>Submission is being processed...</p>;
                        })()}
                      </div>
                    </div>
                  )}
                  
                  {/* Success Summary - Show at top for successful submissions */}
                  {!isProcessing && isSuccessful && (
                    <div className={`mb-4 p-4 border-2 rounded-lg ${
                      submissionStatus === 'approved'
                        ? 'bg-green-500/10 border-green-500/30'
                        : 'bg-blue-500/10 border-blue-500/30'
                    }`}>
                      <h4 className={`font-bold mb-2 flex items-center gap-2 ${
                        submissionStatus === 'approved' ? 'text-green-400' : 'text-blue-400'
                      }`}>
                        <span>{submissionStatus === 'approved' ? '✅' : '✓'}</span>
                        {submissionStatus === 'approved' ? 'Submission Approved!' : 'Submission Successful!'}
                      </h4>
                      <div className={`space-y-2 font-medium ${
                        submissionStatus === 'approved' ? 'text-green-300' : 'text-blue-300'
                      }`}>
                        <p>
                          {submissionStatus === 'approved'
                            ? 'Your product has been successfully submitted and approved by the directory. Congratulations!'
                            : `Your product has been successfully submitted to ${selectedSubmission.directory?.name || 'the directory'}. It is now pending approval.`}
                        </p>
                        {formData && formData.fields_filled > 0 && (
                          <p className="text-sm opacity-90">
                            ✓ Successfully filled {formData.fields_filled} out of {formData.total_fields || formData.fields_filled} form fields
                          </p>
                        )}
                        {formData && formData.analysis_method && (
                          <p className="text-sm opacity-90">
                            ✓ Form analyzed using {formData.analysis_method === 'ai' ? 'AI (Ollama)' : formData.analysis_method === 'dom' ? 'DOM Extraction' : formData.analysis_method}
                          </p>
                        )}
                        {selectedSubmission.submitted_at && (
                          <p className="text-sm opacity-75 mt-2">
                            Submitted at: {new Date(selectedSubmission.submitted_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Failure Summary - Show at top for failed submissions */}
                  {!isSuccessful && errorMsg && (
                    <div className="mb-4 p-4 bg-red-500/10 border-2 border-red-500/30 rounded-lg">
                      <h4 className="font-bold text-red-400 mb-2 flex items-center gap-2">
                        <span>⚠️</span>
                        Failure Reason
                      </h4>
                      <p className="text-red-300 whitespace-pre-wrap font-medium">{errorMsg}</p>
                    </div>
                  )}
                  
                  <div className="space-y-3">
                    {workflowSteps.map((step, idx) => {
                      const isLast = idx === workflowSteps.length - 1;
                      const statusColors = {
                        success: 'bg-green-500/10 border-green-500/20 text-green-400',
                        partial: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400',
                        failed: 'bg-red-500/10 border-red-500/20 text-red-400',
                        warning: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
                      };
                      
                      return (
                        <div key={idx} className="relative">
                          {/* Connection Line */}
                          {!isLast && (
                            <div className="absolute left-4 top-12 bottom-0 w-0.5 bg-[#30363d]"></div>
                          )}
                          
                          <div className={`p-4 rounded-lg border ${statusColors[step.status as keyof typeof statusColors]}`}>
                            <div className="flex items-start gap-3">
                              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                                step.status === 'success' ? 'bg-green-500/20 text-green-400' :
                                step.status === 'partial' ? 'bg-yellow-500/20 text-yellow-400' :
                                step.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                                'bg-yellow-500/20 text-yellow-400'
                              }`}>
                                {step.status === 'success' ? '✓' :
                                 step.status === 'partial' ? '⚠' :
                                 step.status === 'failed' ? '✗' : '○'}
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <h4 className="font-semibold text-white">
                                    Step {step.step}: {step.name}
                                  </h4>
                                  <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                                    step.status === 'success' ? 'bg-green-500/20 text-green-400' :
                                    step.status === 'partial' ? 'bg-yellow-500/20 text-yellow-400' :
                                    step.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                                    'bg-yellow-500/20 text-yellow-400'
                                  }`}>
                                    {step.status.toUpperCase()}
                                  </span>
                                </div>
                                <p className="text-sm text-[#8b949e] mb-2">{step.message}</p>
                                
                                {/* Show errors for this step */}
                                {step.errors && step.errors.length > 0 && (
                                  <div className="mt-2 p-2 bg-red-500/5 border border-red-500/20 rounded">
                                    <p className="text-xs font-semibold text-red-400 mb-1">Field Errors:</p>
                                    <ul className="list-disc list-inside space-y-1">
                                      {step.errors.slice(0, 5).map((error: any, errIdx: number) => (
                                        <li key={errIdx} className="text-xs text-red-300">
                                          {typeof error === 'string' ? error : error.message || JSON.stringify(error)}
                                        </li>
                                      ))}
                                      {step.errors.length > 5 && (
                                        <li className="text-xs text-[#8b949e]">
                                          ... and {step.errors.length - 5} more errors
                                        </li>
                                      )}
                                    </ul>
                                  </div>
                                )}
                                
                                {/* Timestamp with duration calculation */}
                                <div className="mt-2 flex items-center gap-2">
                                  {step.timestamp && (
                                    <p className="text-xs text-[#8b949e]">
                                      <span className="font-mono">
                                        {new Date(step.timestamp).toLocaleString()}
                                      </span>
                                    </p>
                                  )}
                                  {idx > 0 && workflowSteps[idx - 1].timestamp && step.timestamp && (
                                    <span className="text-xs text-[#58a6ff]">
                                      (Duration: {Math.round((new Date(step.timestamp).getTime() - new Date(workflowSteps[idx - 1].timestamp).getTime()) / 1000)}s)
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  
                  {/* Detailed Timeline View */}
                  <div className="mt-6 p-4 bg-[#161b22] rounded-lg border border-[#30363d]">
                    <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                      <span>⏱️</span>
                      Process Timeline
                    </h4>
                    <div className="space-y-2">
                      {workflowSteps.map((step, idx) => {
                        const stepTime = step.timestamp ? new Date(step.timestamp) : null;
                        const prevStepTime = idx > 0 && workflowSteps[idx - 1].timestamp 
                          ? new Date(workflowSteps[idx - 1].timestamp) 
                          : null;
                        const duration = stepTime && prevStepTime 
                          ? Math.round((stepTime.getTime() - prevStepTime.getTime()) / 1000)
                          : null;
                        
                        return (
                          <div key={idx} className="flex items-start gap-3 text-sm">
                            <div className={`flex-shrink-0 w-2 h-2 rounded-full mt-2 ${
                              step.status === 'success' ? 'bg-green-400' :
                              step.status === 'partial' ? 'bg-yellow-400' :
                              step.status === 'failed' ? 'bg-red-400' :
                              'bg-gray-400'
                            }`}></div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-white font-medium">{step.name}</span>
                                <span className={`px-2 py-0.5 text-xs rounded ${
                                  step.status === 'success' ? 'bg-green-500/20 text-green-400' :
                                  step.status === 'partial' ? 'bg-yellow-500/20 text-yellow-400' :
                                  step.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                                  'bg-gray-500/20 text-gray-400'
                                }`}>
                                  {step.status.toUpperCase()}
                                </span>
                                {duration !== null && (
                                  <span className="text-xs text-[#58a6ff]">
                                    ({duration}s)
                                  </span>
                                )}
                              </div>
                              {stepTime && (
                                <p className="text-xs text-[#8b949e] mt-1 font-mono">
                                  {stepTime.toLocaleString()}
                                </p>
                              )}
                              <p className="text-xs text-[#8b949e] mt-1">{step.message}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Form Analysis Details */}
            {(() => {
              const formData = parseFormData(selectedSubmission.form_data);
              if (!formData) {
                return null;
              }

              const formStructure = formData.form_structure || {};
              const fields = formStructure.fields || [];
              const fieldsFilled = formData.fields_filled || 0;
              const totalFields = formData.total_fields || 0;
              const fillErrors = formData.fill_errors || [];
              const analysisMethod = formData.analysis_method || 'unknown';

              // Determine which fields were successfully filled
              const filledFields = new Set<string>();
              const errorFields = new Map<string, string>();

              // Parse fill errors to identify which fields failed
              fillErrors.forEach((error: any) => {
                if (typeof error === 'string') {
                  // Try to extract selector from error message
                  const match = error.match(/selector[:\s]+([^\s,]+)/i);
                  if (match) {
                    errorFields.set(match[1], error);
                  }
                } else if (error.selector) {
                  errorFields.set(error.selector, error.message || JSON.stringify(error));
                }
              });

              // Fields that were filled successfully (not in error list)
              fields.forEach((field: any) => {
                const selector = field.selector;
                if (selector && !errorFields.has(selector)) {
                  filledFields.add(selector);
                }
              });

              return (
                <>
                  {/* Summary */}
                  <div className="mb-6 p-4 bg-[#161b22] rounded-lg border border-[#30363d]">
                    <h3 className="text-lg font-semibold text-white mb-3">Form Analysis Summary</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <span className="text-[#8b949e] text-sm">Analysis Method:</span>
                        <p className="text-white font-medium">
                          {analysisMethod === 'ai' ? 'AI (Ollama)' : analysisMethod === 'dom' ? 'DOM Extraction' : 'Unknown'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[#8b949e] text-sm">Total Fields:</span>
                        <p className="text-white font-medium">{totalFields}</p>
                      </div>
                      <div>
                        <span className="text-[#8b949e] text-sm">Fields Filled:</span>
                        <p className="text-green-400 font-medium">{fieldsFilled}</p>
                      </div>
                      <div>
                        <span className="text-[#8b949e] text-sm">Fields Failed:</span>
                        <p className="text-red-400 font-medium">{fillErrors.length}</p>
                      </div>
                    </div>
                  </div>

                  {/* Successfully Filled Fields */}
                  {filledFields.size > 0 && (
                    <div className="mb-6">
                      <h3 className="text-lg font-semibold text-green-400 mb-3 flex items-center gap-2">
                        <span>✅</span>
                        Successfully Filled Fields ({filledFields.size})
                      </h3>
                      <div className="space-y-2">
                        {fields
                          .filter((field: any) => filledFields.has(field.selector))
                          .map((field: any, idx: number) => (
                            <div
                              key={idx}
                              className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg"
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-mono text-green-300">{field.selector}</span>
                                    {field.purpose && (
                                      <span className="px-2 py-0.5 text-xs rounded bg-green-500/20 text-green-300">
                                        {field.purpose}
                                      </span>
                                    )}
                                  </div>
                                  {field.label && (
                                    <p className="text-sm text-[#8b949e]">Label: {field.label}</p>
                                  )}
                                  {field.name && (
                                    <p className="text-sm text-[#8b949e]">Name: {field.name}</p>
                                  )}
                                  {field.type && (
                                    <p className="text-sm text-[#8b949e]">Type: {field.type}</p>
                                  )}
                                </div>
                                <span className="text-green-400 text-xl">✓</span>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Failed Fields */}
                  {fillErrors.length > 0 && (
                    <div className="mb-6">
                      <h3 className="text-lg font-semibold text-red-400 mb-3 flex items-center gap-2">
                        <span>❌</span>
                        Failed Fields ({fillErrors.length})
                      </h3>
                      <div className="space-y-2">
                        {fillErrors.map((error: any, idx: number) => {
                          const errorMsg = typeof error === 'string' ? error : error.message || JSON.stringify(error);
                          const errorSelector = typeof error === 'object' && error.selector ? error.selector : null;
                          
                          // Try to find the field in form structure
                          const field = errorSelector
                            ? fields.find((f: any) => f.selector === errorSelector)
                            : null;

                          return (
                            <div
                              key={idx}
                              className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg"
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  {field ? (
                                    <>
                                      <div className="flex items-center gap-2 mb-1">
                                        <span className="text-sm font-mono text-red-300">{field.selector}</span>
                                        {field.purpose && (
                                          <span className="px-2 py-0.5 text-xs rounded bg-red-500/20 text-red-300">
                                            {field.purpose}
                                          </span>
                                        )}
                                      </div>
                                      {field.label && (
                                        <p className="text-sm text-[#8b949e]">Label: {field.label}</p>
                                      )}
                                      {field.name && (
                                        <p className="text-sm text-[#8b949e]">Name: {field.name}</p>
                                      )}
                                      {field.type && (
                                        <p className="text-sm text-[#8b949e]">Type: {field.type}</p>
                                      )}
                                    </>
                                  ) : errorSelector ? (
                                    <span className="text-sm font-mono text-red-300">{errorSelector}</span>
                                  ) : null}
                                  <p className="text-sm text-red-300 mt-2 whitespace-pre-wrap">{errorMsg}</p>
                                </div>
                                <span className="text-red-400 text-xl">✗</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* All Detected Fields */}
                  {fields.length > 0 && (
                    <div className="mb-6">
                      <h3 className="text-lg font-semibold text-white mb-3">All Detected Fields ({fields.length})</h3>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {fields.map((field: any, idx: number) => {
                          const wasFilled = filledFields.has(field.selector);
                          const hasError = errorFields.has(field.selector);
                          
                          return (
                            <div
                              key={idx}
                              className={`p-3 rounded-lg border ${
                                wasFilled
                                  ? 'bg-green-500/5 border-green-500/20'
                                  : hasError
                                  ? 'bg-red-500/5 border-red-500/20'
                                  : 'bg-[#161b22] border-[#30363d]'
                              }`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-sm font-mono text-[#8b949e]">{field.selector || 'N/A'}</span>
                                {wasFilled && <span className="text-green-400 text-xs">✓ Filled</span>}
                                {hasError && <span className="text-red-400 text-xs">✗ Error</span>}
                                {!wasFilled && !hasError && <span className="text-yellow-400 text-xs">○ Not filled</span>}
                                {field.purpose && (
                                  <span className="px-2 py-0.5 text-xs rounded bg-[#30363d] text-[#8b949e]">
                                    {field.purpose}
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-[#8b949e] space-y-1">
                                {field.label && <p>Label: {field.label}</p>}
                                {field.name && <p>Name: {field.name}</p>}
                                {field.type && <p>Type: {field.type}</p>}
                                {field.placeholder && <p>Placeholder: {field.placeholder}</p>}
                                {field.required !== undefined && (
                                  <p>Required: {field.required ? 'Yes' : 'No'}</p>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              );
            })()}

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              {(() => {
                const isCurrentlyProcessing = workflowStatus?.active_submission_ids?.includes(selectedSubmission.id) || false;
                const displayStatus = isCurrentlyProcessing ? 'processing' : selectedSubmission.status;
                
                if (isCurrentlyProcessing) {
                  return (
                    <div className="flex-1 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                      <p className="text-purple-400 text-sm flex items-center gap-2">
                        <span className="animate-spin">⏳</span>
                        Submission is currently being processed. Please wait...
                      </p>
                    </div>
                  );
                }
                
                return (
                  <>
                    {displayStatus === 'failed' && (
                      <button
                        onClick={() => {
                          handleRetry(selectedSubmission.id);
                          closeDetailsModal();
                        }}
                        disabled={retrying === selectedSubmission.id || deleting === selectedSubmission.id}
                        className="btn btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {retrying === selectedSubmission.id ? (
                          <span className="flex items-center justify-center gap-2">
                            <span className="animate-spin">⏳</span>
                            Retrying...
                          </span>
                        ) : (
                          'Retry Submission'
                        )}
                      </button>
                    )}
                    <button
                      onClick={() => {
                        handleDelete(selectedSubmission.id);
                        closeDetailsModal();
                      }}
                      disabled={retrying === selectedSubmission.id || deleting === selectedSubmission.id}
                      className="btn bg-red-500/20 hover:bg-red-500/30 text-red-400 border-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {deleting === selectedSubmission.id ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="animate-spin">⏳</span>
                          Deleting...
                        </span>
                      ) : (
                        'Delete'
                      )}
                    </button>
                  </>
                );
              })()}
              <button
                onClick={closeDetailsModal}
                className="btn btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
