import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';

interface BatchStatus {
  batch_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total: number;
  completed: number;
  failed: number;
  download_url: string | null;
}

export function BatchPage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<BatchStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const resp = await fetch('/api/v1/batch', { method: 'POST', body: formData });
      const data = await resp.json();
      setStatus(data);
      if (data.batch_id) pollStatus(data.batch_id);
    } catch {
      setUploading(false);
    }
  };

  const pollStatus = async (batchId: string) => {
    const poll = async () => {
      try {
        const resp = await fetch(`/api/v1/batch/${batchId}`);
        const data = await resp.json();
        setStatus(data);
        if (data.status === 'running' || data.status === 'pending') {
          setTimeout(poll, 3000);
        } else {
          setUploading(false);
        }
      } catch {
        setUploading(false);
      }
    };
    poll();
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <h1 className="text-xl font-bold text-gray-900 mb-2">{t('nav.batch')}</h1>
      <p className="text-sm text-gray-500 mb-6">Upload a CSV of patients to match against all loaded trials at once.</p>

      {/* Upload area */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-6">
        <input ref={fileRef} type="file" accept=".csv" onChange={handleUpload} className="hidden" />
        <button onClick={() => fileRef.current?.click()} disabled={uploading}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {uploading ? 'Processing...' : 'Upload Patient CSV'}
        </button>
        <p className="text-xs text-gray-500 mt-2">CSV with columns: patient_id, clinical_text</p>
      </div>

      {/* Progress */}
      {status && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-900">Batch {status.batch_id}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium
              ${status.status === 'completed' ? 'bg-green-100 text-green-700' :
                status.status === 'running' ? 'bg-blue-100 text-blue-700' :
                status.status === 'failed' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'}`}>
              {status.status}
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
            <div className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${status.total ? (status.completed / status.total) * 100 : 0}%` }} />
          </div>
          <p className="text-xs text-gray-500">{status.completed} / {status.total} patients processed</p>
          {status.failed > 0 && <p className="text-xs text-red-600 mt-1">{status.failed} failed</p>}

          {status.download_url && (
            <a href={status.download_url} download
              className="inline-block mt-3 px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">
              Download Results
            </a>
          )}
        </div>
      )}
    </div>
  );
}
