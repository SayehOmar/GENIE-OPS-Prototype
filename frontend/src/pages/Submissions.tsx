import { useState, useEffect } from 'react';
// @ts-ignore - JS module
import { getSaaSList } from '../api/saas';
// @ts-ignore - JS module
import { getDirectories, createDirectory } from '../api/directories';
// @ts-ignore - JS module
import { startSubmissionJob, processAllPending } from '../api/jobs';
import { SkeletonList } from '../components/Skeleton';

interface SaaS {
  id: number;
  name: string;
  url: string;
  description: string | null;
  category: string | null;
  contact_email: string;
  logo_path: string | null;
}

interface Directory {
  id: number;
  name: string;
  url: string;
  description: string | null;
}

export default function Submissions() {
  const [saasList, setSaaSList] = useState<SaaS[]>([]);
  const [directories, setDirectories] = useState<Directory[]>([]);
  const [selectedSaaS, setSelectedSaaS] = useState<number | null>(null);
  const [selectedDirectories, setSelectedDirectories] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showDirectoryForm, setShowDirectoryForm] = useState(false);
  const [creatingDirectory, setCreatingDirectory] = useState(false);
  const [directoryForm, setDirectoryForm] = useState({
    name: '',
    url: '',
    description: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      const [saas, dirs] = await Promise.all([
        getSaaSList(),
        getDirectories(),
      ]);
      setSaaSList(saas);
      setDirectories(dirs);
      setLoading(false);
    } catch (error: any) {
      console.error('Failed to load data:', error);
      setError(error.message || 'Failed to load data');
      setLoading(false);
    }
  }

  function handleSaaSSelect(saasId: number) {
    setSelectedSaaS(saasId);
    setError(null);
    setSuccess(null);
  }

  function handleDirectoryToggle(directoryId: number) {
    setSelectedDirectories((prev) => {
      if (prev.includes(directoryId)) {
        return prev.filter((id) => id !== directoryId);
      } else {
        return [...prev, directoryId];
      }
    });
    setError(null);
    setSuccess(null);
  }

  function handleSelectAllDirectories() {
    if (selectedDirectories.length === directories.length) {
      setSelectedDirectories([]);
    } else {
      setSelectedDirectories(directories.map((d) => d.id));
    }
    setError(null);
    setSuccess(null);
  }

  async function handleCreateDirectory(e: React.FormEvent) {
    e.preventDefault();
    
    if (!directoryForm.name.trim()) {
      setError('Directory name is required');
      return;
    }
    
    if (!directoryForm.url.trim()) {
      setError('Directory URL is required');
      return;
    }
    
    // Validate URL format
    try {
      new URL(directoryForm.url);
    } catch {
      setError('Please enter a valid URL (e.g., https://example.com/submit)');
      return;
    }
    
    setCreatingDirectory(true);
    setError(null);
    
    try {
      const newDirectory = await createDirectory({
        name: directoryForm.name.trim(),
        url: directoryForm.url.trim(),
        description: directoryForm.description.trim() || null,
      });
      
      // Reload directories list
      await loadData();
      
      // Select the newly created directory
      setSelectedDirectories((prev) => [...prev, newDirectory.id]);
      
      // Reset form and close
      setDirectoryForm({ name: '', url: '', description: '' });
      setShowDirectoryForm(false);
      setSuccess(`Directory "${newDirectory.name}" created successfully!`);
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (error: any) {
      console.error('Failed to create directory:', error);
      setError(error.message || 'Failed to create directory');
    } finally {
      setCreatingDirectory(false);
    }
  }
  
  async function handleSubmit() {
    if (!selectedSaaS) {
      setError('Please select a SaaS product');
      return;
    }

    if (selectedDirectories.length === 0) {
      setError('Please select at least one directory');
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      // Step 1: Create submission job (creates submission records)
      const jobResult = await (startSubmissionJob as any)(
        selectedSaaS,
        selectedDirectories
      );

      if (jobResult.submissions_created === 0) {
        setError('No new submissions created. They may already exist.');
        setSubmitting(false);
        return;
      }

      setSuccess(
        `Created ${jobResult.submissions_created} submission(s). Processing now...`
      );

      // Step 2: Process each submission immediately
      try {
        const processResult = await (processAllPending as any)();
        setSuccess(
          `Successfully created and queued ${processResult.count || jobResult.submissions_created} submission(s) for processing!`
        );
      } catch (processError) {
        // Submissions are created, they'll be processed by workflow manager
        setSuccess(
          `Created ${jobResult.submissions_created} submission(s). They will be processed automatically.`
        );
      }

      // Reset selections after successful submission
      setTimeout(() => {
        setSelectedSaaS(null);
        setSelectedDirectories([]);
        setSuccess(null);
      }, 3000);
    } catch (error: any) {
      console.error('Submission error:', error);
      setError(error.message || 'Failed to create submission job');
    } finally {
      setSubmitting(false);
    }
  }

  const selectedSaaSData = saasList.find((s) => s.id === selectedSaaS);

  return (
    <div className="animate-fade-in">
      <div className="mb-8 animate-slide-in">
        <h1 className="text-4xl font-bold text-white mb-2">Submit to Directories</h1>
        <p className="text-[#8b949e]">
          Select a SaaS product and directories, then submit to start the automation process
        </p>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="card mb-6 bg-red-500/10 border-red-500/20 animate-fade-in">
          <div className="flex items-center gap-2">
            <span className="text-red-400">❌</span>
            <p className="text-red-400">{error}</p>
          </div>
        </div>
      )}

      {success && (
        <div className="card mb-6 bg-green-500/10 border-green-500/20 animate-fade-in">
          <div className="flex items-center gap-2">
            <span className="text-green-400">✅</span>
            <p className="text-green-400">{success}</p>
          </div>
        </div>
      )}

      {loading ? (
        <SkeletonList items={3} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* SaaS Selection */}
          <div className="card animate-fade-in delay-100">
            <h2 className="text-2xl font-bold text-white mb-4">Select SaaS Product</h2>
            {saasList.length === 0 ? (
              <p className="text-[#8b949e]">No SaaS products available. Create one first.</p>
            ) : (
              <div className="space-y-3">
                {saasList.map((saas) => (
                  <div
                    key={saas.id}
                    onClick={() => handleSaaSSelect(saas.id)}
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                      selectedSaaS === saas.id
                        ? 'border-[#58a6ff] bg-[#58a6ff]/10'
                        : 'border-[#30363d] hover:border-[#58a6ff]/50 hover:bg-[#30363d]/50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-white mb-1">
                          {saas.name}
                        </h3>
                        {saas.category && (
                          <span className="inline-block px-2 py-1 text-xs rounded bg-[#30363d] text-[#8b949e] mb-2">
                            {saas.category}
                          </span>
                        )}
                        {saas.url && (
                          <a
                            href={saas.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-[#58a6ff] hover:underline block mt-2"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {saas.url}
                          </a>
                        )}
                        {saas.description && (
                          <p className="text-sm text-[#8b949e] mt-2 line-clamp-2">
                            {saas.description}
                          </p>
                        )}
                      </div>
                      {selectedSaaS === saas.id && (
                        <div className="ml-4 text-[#58a6ff] text-2xl">✓</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Directory Selection */}
          <div className="card animate-fade-in delay-200">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-white">Select Directories</h2>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowDirectoryForm(!showDirectoryForm);
                    setError(null);
                    setDirectoryForm({ name: '', url: '', description: '' });
                  }}
                  className="btn btn-secondary text-sm"
                >
                  {showDirectoryForm ? '✕ Cancel' : '+ Add Directory'}
                </button>
                {directories.length > 0 && (
                  <button
                    onClick={handleSelectAllDirectories}
                    className="btn btn-secondary text-sm"
                  >
                    {selectedDirectories.length === directories.length
                      ? 'Deselect All'
                      : 'Select All'}
                  </button>
                )}
              </div>
            </div>
            
            {/* Add Directory Form */}
            {showDirectoryForm && (
              <div className="mb-6 p-4 bg-[#161b22] border border-[#30363d] rounded-lg animate-fade-in">
                <h3 className="text-lg font-semibold text-white mb-4">Create New Directory</h3>
                <form onSubmit={handleCreateDirectory} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-[#8b949e] mb-2">
                      Directory Name <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={directoryForm.name}
                      onChange={(e) => setDirectoryForm({ ...directoryForm, name: e.target.value })}
                      placeholder="e.g., Product Hunt"
                      className="w-full px-4 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-white placeholder-[#6e7681] focus:outline-none focus:border-[#58a6ff]"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#8b949e] mb-2">
                      Submission URL <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="url"
                      value={directoryForm.url}
                      onChange={(e) => setDirectoryForm({ ...directoryForm, url: e.target.value })}
                      placeholder="https://example.com/submit"
                      className="w-full px-4 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-white placeholder-[#6e7681] focus:outline-none focus:border-[#58a6ff]"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#8b949e] mb-2">
                      Description (Optional)
                    </label>
                    <textarea
                      value={directoryForm.description}
                      onChange={(e) => setDirectoryForm({ ...directoryForm, description: e.target.value })}
                      placeholder="Brief description of the directory..."
                      rows={3}
                      className="w-full px-4 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-white placeholder-[#6e7681] focus:outline-none focus:border-[#58a6ff] resize-none"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={creatingDirectory}
                      className="btn btn-primary text-sm px-6 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {creatingDirectory ? (
                        <span className="flex items-center gap-2">
                          <span className="animate-spin">⏳</span>
                          Creating...
                        </span>
                      ) : (
                        'Create Directory'
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowDirectoryForm(false);
                        setDirectoryForm({ name: '', url: '', description: '' });
                        setError(null);
                      }}
                      className="btn btn-secondary text-sm px-6 py-2"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            )}
            {directories.length === 0 ? (
              <p className="text-[#8b949e]">
                No directories available. Add directories to submit to.
              </p>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {directories.map((directory) => (
                  <div
                    key={directory.id}
                    onClick={() => handleDirectoryToggle(directory.id)}
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                      selectedDirectories.includes(directory.id)
                        ? 'border-[#58a6ff] bg-[#58a6ff]/10'
                        : 'border-[#30363d] hover:border-[#58a6ff]/50 hover:bg-[#30363d]/50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-white mb-1">
                          {directory.name}
                        </h3>
                        {directory.url && (
                          <a
                            href={directory.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-[#58a6ff] hover:underline block mt-2"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {directory.url}
                          </a>
                        )}
                        {directory.description && (
                          <p className="text-sm text-[#8b949e] mt-2 line-clamp-2">
                            {directory.description}
                          </p>
                        )}
                      </div>
                      {selectedDirectories.includes(directory.id) && (
                        <div className="ml-4 text-[#58a6ff] text-2xl">✓</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Submit Button */}
      <div className="mt-6 animate-fade-in delay-300">
        <div className="card bg-[#1f6feb]/10 border-[#1f6feb]/20">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white mb-1">Ready to Submit</h3>
              <p className="text-sm text-[#8b949e]">
                {selectedSaaSData && (
                  <>
                    <strong>{selectedSaaSData.name}</strong>
                    {selectedDirectories.length > 0 && (
                      <> → {selectedDirectories.length} directory(ies)</>
                    )}
                  </>
                )}
                {!selectedSaaSData && 'Select a SaaS product and directories to continue'}
              </p>
            </div>
            <button
              onClick={handleSubmit}
              disabled={
                !selectedSaaS ||
                selectedDirectories.length === 0 ||
                submitting ||
                loading
              }
              className="btn btn-primary px-8 py-3 text-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin">⏳</span>
                  Submitting...
                </span>
              ) : (
                'Submit'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
