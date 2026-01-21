import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
// @ts-ignore - JS module
import { getSaaSById, createSaaS, updateSaaS } from '../api/saas';
// @ts-ignore - JS module
import { getDirectories } from '../api/directories';
// @ts-ignore - JS module
import { startSubmissionJob } from '../api/jobs';

export default function SaaSForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = !!id;

  const [formData, setFormData] = useState({
    name: '',
    url: '',
    description: '',
    category: '',
    contact_email: '',
    logo_path: '',
  });

  const [directories, setDirectories] = useState([]);
  const [selectedDirectories, setSelectedDirectories] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      await loadDirectories();
      if (isEditing) {
        await loadSaaS();
      } else {
        setLoading(false);
      }
    }
    init();
  }, [id]);

  async function loadSaaS() {
    try {
      setLoading(true);
      setError(null);
      const data = await getSaaSById(id!);
      setFormData({
        name: data.name || '',
        url: data.url || '',
        description: data.description || '',
        category: data.category || '',
        contact_email: data.contact_email || '',
        logo_path: data.logo_path || '',
      });
    } catch (error: any) {
      console.error('Failed to load SaaS:', error);
      setError(error.message || 'Failed to load SaaS product');
    } finally {
      setLoading(false);
    }
  }

  async function loadDirectories() {
    try {
      const data = await getDirectories();
      setDirectories(data || []);
    } catch (error: any) {
      console.error('Failed to load directories:', error);
      setError('Failed to load directories');
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  }

  function handleDirectoryToggle(directoryId: number) {
    setSelectedDirectories(prev =>
      prev.includes(directoryId)
        ? prev.filter(id => id !== directoryId)
        : [...prev, directoryId]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      // Validate required fields
      if (!formData.name.trim()) {
        setError('Product name is required');
        setSubmitting(false);
        return;
      }
      if (!formData.url.trim()) {
        setError('Website URL is required');
        setSubmitting(false);
        return;
      }
      if (!formData.contact_email.trim()) {
        setError('Contact email is required');
        setSubmitting(false);
        return;
      }

      // Validate URL format
      try {
        new URL(formData.url);
      } catch {
        setError('Please enter a valid URL (e.g., https://example.com)');
        setSubmitting(false);
        return;
      }

      // Validate email format
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.contact_email)) {
        setError('Please enter a valid email address');
        setSubmitting(false);
        return;
      }

      let saasId;
      if (isEditing) {
        const updated = await updateSaaS(id!, formData);
        saasId = updated.id;
      } else {
        const newSaaS = await createSaaS(formData);
        saasId = newSaaS.id;
      }

      // If directories are selected, start submission job
      if (selectedDirectories.length > 0) {
        try {
          await (startSubmissionJob as any)(saasId, selectedDirectories);
          alert('SaaS product saved and submission job started!');
        } catch (jobError: any) {
          console.error('Failed to start submission job:', jobError);
          alert('SaaS product saved, but failed to start submission job: ' + (jobError.message || 'Unknown error'));
        }
      } else {
        alert('SaaS product saved successfully!');
      }

      navigate('/saas');
    } catch (error: any) {
      console.error('Failed to save SaaS:', error);
      setError(error.message || 'Failed to save SaaS product. Please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading && isEditing) {
    return (
      <div className="animate-fade-in">
        <div className="mb-8 animate-slide-in">
          <h1 className="text-4xl font-bold text-white mb-2">Loading...</h1>
        </div>
        <div className="card max-w-3xl">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-[#30363d] rounded w-3/4"></div>
            <div className="h-10 bg-[#30363d] rounded"></div>
            <div className="h-4 bg-[#30363d] rounded w-1/2"></div>
            <div className="h-10 bg-[#30363d] rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8 animate-slide-in">
        <h1 className="text-4xl font-bold text-white mb-2">
          {isEditing ? 'Edit SaaS Product' : 'Add New SaaS Product'}
        </h1>
        <p className="text-[#8b949e]">
          {isEditing ? 'Update your SaaS product information' : 'Add a new SaaS product to submit to directories'}
        </p>
      </div>

      {error && (
        <div className="card max-w-3xl mb-6 bg-red-500/10 border-red-500/20 animate-fade-in">
          <div className="flex items-center gap-3">
            <span className="text-red-400 text-xl">⚠️</span>
            <p className="text-red-400">{error}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="card max-w-3xl animate-fade-in delay-100">
        <div className="space-y-6">
          {/* Name */}
          <div>
            <label htmlFor="name" className="label">
              Product Name *
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              className="input"
              required
              placeholder="My Awesome SaaS"
            />
          </div>

          {/* URL */}
          <div>
            <label htmlFor="url" className="label">
              Website URL *
            </label>
            <input
              type="url"
              id="url"
              name="url"
              value={formData.url}
              onChange={handleChange}
              className="input"
              required
              placeholder="https://example.com"
            />
          </div>

          {/* Contact Email */}
          <div>
            <label htmlFor="contact_email" className="label">
              Contact Email *
            </label>
            <input
              type="email"
              id="contact_email"
              name="contact_email"
              value={formData.contact_email}
              onChange={handleChange}
              className="input"
              required
              placeholder="contact@example.com"
            />
          </div>

          {/* Category */}
          <div>
            <label htmlFor="category" className="label">
              Category
            </label>
            <input
              type="text"
              id="category"
              name="category"
              value={formData.category}
              onChange={handleChange}
              className="input"
              placeholder="Productivity, Marketing, etc."
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="label">
              Description
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              className="input min-h-[120px] resize-y"
              placeholder="Describe your SaaS product..."
              rows={5}
            />
          </div>

          {/* Logo Path */}
          <div>
            <label htmlFor="logo_path" className="label">
              Logo Path
            </label>
            <input
              type="text"
              id="logo_path"
              name="logo_path"
              value={formData.logo_path}
              onChange={handleChange}
              className="input"
              placeholder="/path/to/logo.png"
            />
          </div>

          {/* Directory Selection (only for new SaaS) */}
          {!isEditing && (
            <div>
              <label className="label">
                Submit to Directories (optional)
              </label>
              <p className="text-sm text-[#8b949e] mb-3">
                Select directories to automatically submit this SaaS product to
              </p>
              {directories.length === 0 ? (
                <div className="border border-[#30363d] rounded-lg p-6 bg-[#0d1117] text-center">
                  <p className="text-[#8b949e] mb-2">No directories available</p>
                  <p className="text-xs text-[#8b949e]">
                    Add directories first to enable automatic submissions
                  </p>
                </div>
              ) : (
                <>
                  <div className="space-y-2 max-h-48 overflow-y-auto border border-[#30363d] rounded-lg p-4 bg-[#0d1117]">
                    {directories.map((dir: any) => (
                      <label
                        key={dir.id}
                        className="flex items-center gap-3 p-3 rounded-lg hover:bg-[#30363d]/50 cursor-pointer transition-colors border border-transparent hover:border-[#30363d]"
                      >
                        <input
                          type="checkbox"
                          checked={selectedDirectories.includes(dir.id)}
                          onChange={() => handleDirectoryToggle(dir.id)}
                          className="w-4 h-4 text-[#58a6ff] bg-[#0d1117] border-[#30363d] rounded focus:ring-2 focus:ring-[#58a6ff] focus:ring-offset-0 focus:ring-offset-[#0d1117] cursor-pointer"
                        />
                        <div className="flex-1">
                          <p className="text-white font-medium">{dir.name}</p>
                          <p className="text-sm text-[#8b949e]">{dir.url}</p>
                          {dir.description && (
                            <p className="text-xs text-[#8b949e] mt-1 line-clamp-1">{dir.description}</p>
                          )}
                        </div>
                      </label>
                    ))}
                  </div>
                  {selectedDirectories.length > 0 && (
                    <p className="text-sm text-[#58a6ff] mt-2">
                      {selectedDirectories.length} director{selectedDirectories.length === 1 ? 'y' : 'ies'} selected
                    </p>
                  )}
                </>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              className="btn btn-primary flex-1"
              disabled={submitting}
            >
              {submitting ? 'Saving...' : isEditing ? 'Update Product' : 'Create Product'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/saas')}
              className="btn btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
