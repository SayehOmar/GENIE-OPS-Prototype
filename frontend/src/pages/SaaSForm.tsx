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

  useEffect(() => {
    loadDirectories();
    if (isEditing) {
      loadSaaS();
    }
  }, [id]);

  async function loadSaaS() {
    try {
      const data = await getSaaSById(id!);
      setFormData({
        name: data.name || '',
        url: data.url || '',
        description: data.description || '',
        category: data.category || '',
        contact_email: data.contact_email || '',
        logo_path: data.logo_path || '',
      });
    } catch (error) {
      console.error('Failed to load SaaS:', error);
      alert('Failed to load SaaS product');
    }
  }

  async function loadDirectories() {
    try {
      const data = await getDirectories();
      setDirectories(data);
    } catch (error) {
      console.error('Failed to load directories:', error);
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

    try {
      let saasId;
      if (isEditing) {
        await updateSaaS(id!, formData);
        saasId = parseInt(id!);
      } else {
        const newSaaS = await createSaaS(formData);
        saasId = newSaaS.id;
      }

      // If directories are selected, start submission job
      if (selectedDirectories.length > 0) {
        await startSubmissionJob(saasId, selectedDirectories);
        alert('SaaS product saved and submission job started!');
      } else {
        alert('SaaS product saved successfully!');
      }

      navigate('/saas');
    } catch (error: any) {
      console.error('Failed to save SaaS:', error);
      alert(error.message || 'Failed to save SaaS product');
    } finally {
      setSubmitting(false);
    }
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
          {!isEditing && directories.length > 0 && (
            <div>
              <label className="label">
                Submit to Directories (optional)
              </label>
              <div className="space-y-2 max-h-48 overflow-y-auto border border-dark-border rounded-lg p-4">
                {directories.map((dir: any) => (
                  <label
                    key={dir.id}
                    className="flex items-center gap-3 p-2 rounded hover:bg-dark-border cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDirectories.includes(dir.id)}
                      onChange={() => handleDirectoryToggle(dir.id)}
                      className="w-4 h-4 text-dark-accent bg-dark-bg border-dark-border rounded focus:ring-dark-accent"
                    />
                    <div className="flex-1">
                      <p className="text-white font-medium">{dir.name}</p>
                      <p className="text-sm text-dark-text-muted">{dir.url}</p>
                    </div>
                  </label>
                ))}
              </div>
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
