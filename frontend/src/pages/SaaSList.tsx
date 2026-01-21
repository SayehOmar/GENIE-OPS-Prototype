import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
// @ts-ignore - JS module
import { getSaaSList, deleteSaaS } from '../api/saas';
// @ts-ignore - JS module
import { startSubmissionJob } from '../api/jobs';
// @ts-ignore - JS module
import { getDirectories } from '../api/directories';
import { SkeletonList } from '../components/Skeleton';

export default function SaaSList() {
  const navigate = useNavigate();
  const [saasList, setSaaSList] = useState<any[]>([]);
  const [directories, setDirectories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSaaS, setSelectedSaaS] = useState<number | null>(null);
  const [selectedDirectories, setSelectedDirectories] = useState<number[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [saas, dirs] = await Promise.all([
        getSaaSList(),
        getDirectories(),
      ]);
      setSaaSList(saas);
      setDirectories(dirs);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Are you sure you want to delete this SaaS product?')) return;

    try {
      await deleteSaaS(id);
      await loadData();
      alert('SaaS product deleted');
    } catch (error: any) {
      alert(error.message || 'Failed to delete SaaS product');
    }
  }

  async function handleStartJob(saasId: number) {
    if (selectedDirectories.length === 0) {
      alert('Please select at least one directory');
      return;
    }

    try {
      await (startSubmissionJob as any)(saasId, selectedDirectories);
      alert('Submission job started!');
      setSelectedSaaS(null);
      setSelectedDirectories([]);
    } catch (error: any) {
      alert(error.message || 'Failed to start submission job');
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8 flex items-center justify-between animate-slide-in">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">SaaS Products</h1>
          <p className="text-[#8b949e]">Manage your SaaS products and start submissions</p>
        </div>
        <button
          onClick={() => navigate('/saas/new')}
          className="btn btn-primary"
        >
          + Add New SaaS
        </button>
      </div>

      {loading ? (
        <SkeletonList items={6} />
      ) : saasList.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-dark-text-muted mb-4">No SaaS products yet</p>
          <button
            onClick={() => navigate('/saas/new')}
            className="btn btn-primary"
          >
            Create Your First SaaS Product
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {saasList.map((saas: any, index: number) => (
            <div 
              key={saas.id} 
              className="card"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-white mb-1">{saas.name}</h3>
                  <a
                    href={saas.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-dark-accent hover:underline"
                  >
                    {saas.url}
                  </a>
                </div>
              </div>

              {saas.description && (
                <p className="text-sm text-dark-text-muted mb-4 line-clamp-2">
                  {saas.description}
                </p>
              )}

              <div className="flex flex-wrap gap-2 mb-4">
                {saas.category && (
                  <span className="px-2 py-1 bg-dark-border rounded text-xs text-dark-text-muted">
                    {saas.category}
                  </span>
                )}
                <span className="px-2 py-1 bg-dark-border rounded text-xs text-dark-text-muted">
                  {saas.contact_email}
                </span>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => navigate(`/saas/${saas.id}/edit`)}
                  className="btn btn-secondary flex-1 text-sm"
                >
                  Edit
                </button>
                <button
                  onClick={() => {
                    setSelectedSaaS(saas.id);
                    setSelectedDirectories([]);
                  }}
                  className="btn btn-primary flex-1 text-sm"
                >
                  Submit
                </button>
                <button
                  onClick={() => handleDelete(saas.id)}
                  className="btn btn-danger text-sm px-3"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Submission Modal */}
      {selectedSaaS && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="card max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <h2 className="text-2xl font-bold text-white mb-4">
              Start Submission Job
            </h2>
            <p className="text-dark-text-muted mb-6">
              Select directories to submit to:
            </p>

            <div className="space-y-2 mb-6 max-h-64 overflow-y-auto">
              {directories.map((dir: any) => (
                <label
                  key={dir.id}
                  className="flex items-center gap-3 p-3 rounded-lg border border-dark-border hover:bg-dark-border cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedDirectories.includes(dir.id)}
                    onChange={() =>
                      setSelectedDirectories(prev =>
                        prev.includes(dir.id)
                          ? prev.filter(id => id !== dir.id)
                          : [...prev, dir.id]
                      )
                    }
                    className="w-4 h-4 text-dark-accent bg-dark-bg border-dark-border rounded focus:ring-dark-accent"
                  />
                  <div className="flex-1">
                    <p className="text-white font-medium">{dir.name}</p>
                    <p className="text-sm text-dark-text-muted">{dir.url}</p>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => handleStartJob(selectedSaaS)}
                className="btn btn-primary flex-1"
                disabled={selectedDirectories.length === 0}
              >
                Start Submission
              </button>
              <button
                onClick={() => {
                  setSelectedSaaS(null);
                  setSelectedDirectories([]);
                }}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
