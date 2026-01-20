import { useState, useEffect } from 'react';
import { getSubmissions, retrySubmission } from '../api/submissions';
import { getSaaSList } from '../api/saas';
import { getDirectories } from '../api/directories';
import { processSubmission } from '../api/jobs';
import { SkeletonTable } from '../components/Skeleton';

interface Submission {
  id: number;
  saas_id: number;
  directory_id: number;
  status: string;
  submitted_at: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  saas?: { name: string };
  directory?: { name: string; url: string };
}

export default function Submissions() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [saasList, setSaaSList] = useState<any[]>([]);
  const [directories, setDirectories] = useState<any[]>([]);
  const [filter, setFilter] = useState({ saasId: '', status: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [filter]);

  async function loadData() {
    try {
      const [subs, saas, dirs] = await Promise.all([
        getSubmissions(
          filter.saasId ? parseInt(filter.saasId) : null,
          null
        ),
        getSaaSList(),
        getDirectories(),
      ]);

      // Enrich submissions with SaaS and Directory data
      const enriched = subs.map((sub: Submission) => ({
        ...sub,
        saas: saas.find((s: any) => s.id === sub.saas_id),
        directory: dirs.find((d: any) => d.id === sub.directory_id),
      }));

      // Apply status filter
      const filtered = filter.status
        ? enriched.filter((s: Submission) => s.status === filter.status)
        : enriched;

      setSubmissions(filtered);
      setSaaSList(saas);
      setDirectories(dirs);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load submissions:', error);
      setLoading(false);
    }
  }

  async function handleRetry(submissionId: number) {
    if (!confirm('Retry this submission?')) return;

    try {
      await retrySubmission(submissionId);
      await loadData();
      alert('Submission queued for retry');
    } catch (error: any) {
      alert(error.message || 'Failed to retry submission');
    }
  }

  async function handleProcess(submissionId: number) {
    if (!confirm('Process this submission now?')) return;

    try {
      await processSubmission(submissionId);
      await loadData();
      alert('Submission queued for processing');
    } catch (error: any) {
      alert(error.message || 'Failed to process submission');
    }
  }

  function getStatusBadge(status: string) {
    const styles = {
      pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
      submitted: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      approved: 'bg-green-500/10 text-green-400 border-green-500/20',
      failed: 'bg-red-500/10 text-red-400 border-red-500/20',
    };

    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${styles[status as keyof typeof styles] || styles.pending}`}>
        {status.toUpperCase()}
      </span>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8 flex items-center justify-between animate-slide-in">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Submissions</h1>
          <p className="text-[#8b949e]">Monitor and manage your directory submissions</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card mb-6 animate-fade-in delay-100">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Filter by SaaS</label>
            <select
              value={filter.saasId}
              onChange={(e) => setFilter({ ...filter, saasId: e.target.value })}
              className="input"
            >
              <option value="">All SaaS Products</option>
              {saasList.map((saas: any) => (
                <option key={saas.id} value={saas.id}>
                  {saas.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Filter by Status</label>
            <select
              value={filter.status}
              onChange={(e) => setFilter({ ...filter, status: e.target.value })}
              className="input"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="submitted">Submitted</option>
              <option value="approved">Approved</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setFilter({ saasId: '', status: '' })}
              className="btn btn-secondary w-full"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Submissions Table */}
      {loading ? (
        <SkeletonTable rows={5} columns={7} />
      ) : (
        <div className="card overflow-x-auto animate-fade-in delay-200">
        <table className="w-full">
          <thead>
            <tr className="border-b border-dark-border">
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">SaaS Product</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Directory</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Status</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Retries</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Submitted At</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Error</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Actions</th>
            </tr>
          </thead>
          <tbody>
            {submissions.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-dark-text-muted">
                  No submissions found
                </td>
              </tr>
            ) : (
              submissions.map((submission) => (
                <tr
                  key={submission.id}
                  className="border-b border-dark-border hover:bg-dark-border/50 transition-colors"
                >
                  <td className="py-3 px-4">
                    <div className="font-medium text-white">
                      {submission.saas?.name || `SaaS #${submission.saas_id}`}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <div>
                      <div className="font-medium text-white">
                        {submission.directory?.name || `Directory #${submission.directory_id}`}
                      </div>
                      {submission.directory?.url && (
                        <a
                          href={submission.directory.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-dark-accent hover:underline"
                        >
                          {submission.directory.url}
                        </a>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    {getStatusBadge(submission.status)}
                  </td>
                  <td className="py-3 px-4 text-dark-text-muted">
                    {submission.retry_count}
                  </td>
                  <td className="py-3 px-4 text-dark-text-muted text-sm">
                    {submission.submitted_at
                      ? new Date(submission.submitted_at).toLocaleString()
                      : '-'}
                  </td>
                  <td className="py-3 px-4">
                    {submission.error_message ? (
                      <span className="text-sm text-red-400" title={submission.error_message}>
                        {submission.error_message.length > 50
                          ? submission.error_message.substring(0, 50) + '...'
                          : submission.error_message}
                      </span>
                    ) : (
                      <span className="text-dark-text-muted">-</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex gap-2">
                      {submission.status === 'pending' && (
                        <button
                          onClick={() => handleProcess(submission.id)}
                          className="btn btn-primary text-xs px-3 py-1"
                        >
                          Process
                        </button>
                      )}
                      {submission.status === 'failed' && (
                        <button
                          onClick={() => handleRetry(submission.id)}
                          className="btn btn-secondary text-xs px-3 py-1"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      )}
    </div>
  );
}
