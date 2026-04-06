import { useState, useRef } from 'react';

interface UploadResult {
  nct_id: string;
  brief_title: string;
  inclusion_count: number;
  exclusion_count: number;
  extraction_method: string;
  confidence: string;
  source_format: string;
  warnings: string[];
}

interface Props {
  onUpload: (result: UploadResult) => void;
}

export function TrialUpload({ onUpload }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [tab, setTab] = useState<'file' | 'paste' | 'nct'>('file');
  const [nctId, setNctId] = useState('');
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<UploadResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    if (title.trim()) formData.append('title', title.trim());

    try {
      const resp = await fetch('/api/v1/ingest/trial', { method: 'POST', body: formData });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      const data: UploadResult = await resp.json();
      setResult(data);
      onUpload(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleText = async () => {
    if (!text.trim()) return;
    setUploading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('text', text.trim());
    if (title.trim()) formData.append('title', title.trim());

    try {
      const resp = await fetch('/api/v1/ingest/trial', { method: 'POST', body: formData });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      const data: UploadResult = await resp.json();
      setResult(data);
      onUpload(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleNct = async () => {
    const id = nctId.trim();
    if (!id) return;
    setUploading(true);
    setError('');
    setResult(null);

    try {
      const resp = await fetch(`/api/v1/ingest/ctgov/${encodeURIComponent(id)}`, { method: 'POST' });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Import failed' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      const uploadResult: UploadResult = {
        nct_id: data.nct_id,
        brief_title: data.brief_title,
        inclusion_count: data.inclusion_count,
        exclusion_count: data.exclusion_count,
        extraction_method: 'ctgov',
        confidence: 'high',
        source_format: 'ctgov',
        warnings: data.already_loaded ? ['Trial was already loaded'] : [],
      };
      setResult(uploadResult);
      onUpload(uploadResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setUploading(false);
    }
  };

  if (!expanded) {
    return (
      <button onClick={() => setExpanded(true)}
        className="w-full py-3 border-2 border-dashed border-blue-200 rounded-lg text-sm text-blue-600 hover:bg-blue-50 hover:border-blue-300 transition-colors">
        + Upload a Protocol to Match Against
      </button>
    );
  }

  return (
    <div className="border border-blue-200 rounded-lg p-4 bg-blue-50/30">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-900">Upload a Protocol</h3>
        <button onClick={() => setExpanded(false)} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
      </div>

      {/* Title field */}
      <input type="text" value={title} onChange={e => setTitle(e.target.value)}
        placeholder="Protocol title (optional)"
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-3" />

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-3">
        <button onClick={() => setTab('file')}
          className={`px-3 py-1.5 text-sm font-medium border-b-2 transition-colors
            ${tab === 'file' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'}`}>
          Upload File
        </button>
        <button onClick={() => setTab('paste')}
          className={`px-3 py-1.5 text-sm font-medium border-b-2 transition-colors
            ${tab === 'paste' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'}`}>
          Paste Text
        </button>
        <button onClick={() => setTab('nct')}
          className={`px-3 py-1.5 text-sm font-medium border-b-2 transition-colors
            ${tab === 'nct' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'}`}>
          NCT ID
        </button>
      </div>

      {tab === 'file' && (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.json,.csv"
            onChange={handleFile} className="hidden" />
          <button onClick={() => fileRef.current?.click()} disabled={uploading}
            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">
            {uploading ? 'Extracting criteria...' : 'Choose Protocol File'}
          </button>
          <p className="text-xs text-gray-500 mt-2">PDF, DOCX, TXT, JSON, CSV</p>
        </div>
      )}

      {tab === 'paste' && (
        <div>
          <textarea value={text} onChange={e => setText(e.target.value)}
            placeholder="Paste the eligibility criteria section from your protocol here..."
            rows={6}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-y" />
          <button onClick={handleText} disabled={uploading || !text.trim()}
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
            {uploading ? 'Extracting...' : 'Extract Criteria'}
          </button>
        </div>
      )}

      {tab === 'nct' && (
        <div>
          <div className="flex gap-2">
            <input type="text" value={nctId} onChange={e => setNctId(e.target.value)}
              placeholder="NCT number (e.g. NCT04567890)"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
              onKeyDown={e => e.key === 'Enter' && handleNct()} />
            <button onClick={handleNct} disabled={uploading || !nctId.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
              {uploading ? 'Importing...' : 'Import'}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">Import a trial directly from ClinicalTrials.gov with full eligibility criteria and site locations</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
      )}

      {/* Success result */}
      {result && (
        <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-green-700 font-medium text-sm">Protocol uploaded</span>
            <span className={`px-1.5 py-0.5 rounded text-xs ${
              result.confidence === 'high' ? 'bg-green-100 text-green-700' :
              result.confidence === 'medium' ? 'bg-yellow-100 text-yellow-700' :
              'bg-red-100 text-red-700'
            }`}>
              {result.confidence} confidence
            </span>
          </div>
          <p className="text-sm text-gray-700">{result.brief_title}</p>
          <p className="text-xs text-gray-500 mt-1">
            {result.inclusion_count} inclusion + {result.exclusion_count} exclusion criteria extracted
          </p>
          {result.warnings.length > 0 && (
            <div className="mt-2 text-xs text-amber-700">
              {result.warnings.map((w, i) => <p key={i}>Note: {w}</p>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
