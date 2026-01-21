import { useState, useEffect } from 'react';
// @ts-ignore - JS module
import { getSubmissions, retrySubmission } from '../api/submissions';
// @ts-ignore - JS module
import { getSaaSList } from '../api/saas';
// @ts-ignore - JS module
import { getDirectories } from '../api/directories';
// @ts-ignore - JS module
import { processSubmission } from '../api/jobs';
import { SkeletonTable } from '../components/Skeleton';

interface Submission {
  id: number;
  saas_id: number;
  directory_id: number;
  status: string;
  submitted_at: string | null;
  error_message: string | null;
  form_data: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string | null;
  saas?: { name: string; url: string; category: string };
  directory?: { name: string; url: string; description: string };
}

export default function Submissions() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [saasList, setSaaSList] = useState<any[]>([]);
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
        (getSubmissions as any)(
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
        <SkeletonTable rows={5} columns={10} />
      ) : (
        <div className="card overflow-x-auto animate-fade-in delay-200">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#30363d]">
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">ID</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">SaaS Product</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">Directory</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">Status</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">Retries</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">Created At</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">Submitted At</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">Last Updated</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">Error</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-[#8b949e]">Actions</th>
            </tr>
          </thead>
          <tbody>
            {submissions.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-8 text-center text-[#8b949e]">
                  No submissions found
                </td>
              </tr>
            ) : (
              submissions.map((submission) => (
                <tr
                  key={submission.id}
                  className="border-b border-[#30363d] hover:bg-[#30363d]/50 transition-colors"
                >
                  <td className="py-3 px-4">
                    <span className="text-sm text-[#8b949e] font-mono">#{submission.id}</span>
                  </td>
                  <td className="py-3 px-4">
                    <div>
                      <div className="font-medium text-white">
                        {submission.saas?.name || `SaaS #${submission.saas_id}`}
                      </div>
                      {submission.saas?.category && (
                        <span className="text-xs text-[#8b949e]">{submission.saas.category}</span>
                      )}
                      {submission.saas?.url && (
                        <a
                          href={submission.saas.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-[#58a6ff] hover:underline block mt-1"
                        >
                          {submission.saas.url}
                        </a>
                      )}
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
                          className="text-sm text-[#58a6ff] hover:underline block"
                        >
                          {submission.directory.url}
                        </a>
                      )}
                      {submission.directory?.description && (
                        <p className="text-xs text-[#8b949e] mt-1 line-clamp-1">
                          {submission.directory.description}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    {getStatusBadge(submission.status)}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1">
                      <span className="text-[#8b949e]">{submission.retry_count}</span>
                      {submission.retry_count > 0 && (
                        <span className="text-xs text-yellow-400" title="Retry attempts">⚠️</span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-[#8b949e] text-sm">
                    {submission.created_at
                      ? new Date(submission.created_at).toLocaleDateString()
                      : '-'}
                    <br />
                    <span className="text-xs">
                      {submission.created_at
                        ? new Date(submission.created_at).toLocaleTimeString()
                        : ''}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-[#8b949e] text-sm">
                    {submission.submitted_at
                      ? (
                          <>
                            {new Date(submission.submitted_at).toLocaleDateString()}
                            <br />
                            <span className="text-xs">
                              {new Date(submission.submitted_at).toLocaleTimeString()}
                            </span>
                          </>
                        )
                      : '-'}
                  </td>
                  <td className="py-3 px-4 text-[#8b949e] text-sm">
                    {submission.updated_at
                      ? (
                          <>
                            {new Date(submission.updated_at).toLocaleDateString()}
                            <br />
                            <span className="text-xs">
                              {new Date(submission.updated_at).toLocaleTimeString()}
                            </span>
                          </>
                        )
                      : '-'}
                  </td>
                  <td className="py-3 px-4">
                    {submission.error_message ? (
                      <div className="group relative">
                        <span className="text-sm text-red-400 cursor-help">
                          {submission.error_message.length > 30
                            ? submission.error_message.substring(0, 30) + '...'
                            : submission.error_message}
                        </span>
                        <div className="absolute left-0 top-full mt-2 hidden group-hover:block z-10 bg-[#161b22] border border-[#30363d] rounded-lg p-3 shadow-lg max-w-xs">
                          <p className="text-sm text-red-400 whitespace-pre-wrap">
                            {submission.error_message}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <span className="text-[#8b949e]">-</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex gap-2">
                      {submission.status === 'pending' && (
                        <button
                          onClick={() => handleProcess(submission.id)}
                          className="btn btn-primary text-xs px-3 py-1"
                          title="Process this submission now"
                        >
                          Process
                        </button>
                      )}
                      {submission.status === 'failed' && (
                        <button
                          onClick={() => handleRetry(submission.id)}
                          className="btn btn-secondary text-xs px-3 py-1"
                          title="Retry this submission"
                        >
                          Retry
                        </button>
                      )}
                      {submission.form_data && (
                        <button
                          onClick={() => {
                            try {
                              const formData = JSON.parse(submission.form_data || '{}');
                              alert('Form Data:\n' + JSON.stringify(formData, null, 2));
                            } catch (e) {
                              alert('Form Data:\n' + submission.form_data);
                            }
                          }}
                          className="btn btn-secondary text-xs px-2 py-1"
                          title="View form data"
                        >
                          📋
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
