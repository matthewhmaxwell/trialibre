import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { InputTab } from '../types/api';

interface Props {
  onSubmit: (text: string) => void;
  disabled: boolean;
}

export function PatientInput({ onSubmit, disabled }: Props) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<InputTab>('type');
  const [text, setText] = useState('');
  const [fileName, setFileName] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);

    const formData = new FormData();
    formData.append('file', file);
    try {
      const resp = await fetch('/api/v1/ingest/file', { method: 'POST', body: formData });
      const data = await resp.json();
      setText(data.extracted_text || '');
      setTab('type');
    } catch {
      setText('');
    }
  };

  const handlePhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);

    const formData = new FormData();
    formData.append('file', file);
    try {
      const resp = await fetch('/api/v1/ingest/file', { method: 'POST', body: formData });
      const data = await resp.json();
      setText(data.extracted_text || '');
      setTab('type');
    } catch {
      setText('');
    }
  };

  const tabs: { key: InputTab; label: string }[] = [
    { key: 'type', label: t('match.type_tab') },
    { key: 'upload', label: t('match.upload_tab') },
    { key: 'photo', label: t('match.photo_tab') },
  ];

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Tab bar */}
      <div className="flex border-b border-gray-200 mb-4">
        {tabs.map(tb => (
          <button key={tb.key} onClick={() => setTab(tb.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors
              ${tab === tb.key ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {tb.label}
          </button>
        ))}
      </div>

      {/* Type tab */}
      {tab === 'type' && (
        <div>
          <textarea value={text} onChange={e => setText(e.target.value)}
            placeholder={t('match.placeholder')}
            rows={6}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y" />
          {fileName && <p className="text-xs text-gray-500 mt-1">Loaded from: {fileName}</p>}
        </div>
      )}

      {/* Upload tab */}
      {tab === 'upload' && (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <input ref={fileRef} type="file" accept=".pdf,.docx,.csv,.txt,.json,.xml"
            onChange={handleFile} className="hidden" />
          <button onClick={() => fileRef.current?.click()}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">
            Choose file
          </button>
          <p className="text-xs text-gray-500 mt-2">PDF, DOCX, CSV, TXT, FHIR JSON, HL7</p>
        </div>
      )}

      {/* Photo tab */}
      {tab === 'photo' && (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <input type="file" accept="image/*" capture="environment"
            onChange={handlePhoto} className="hidden" id="camera-input" />
          <label htmlFor="camera-input"
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 cursor-pointer inline-block">
            Take Photo
          </label>
          <p className="text-xs text-gray-500 mt-2">Take a photo of a patient record or lab report</p>
        </div>
      )}

      {/* Submit */}
      <button onClick={() => text.trim() && onSubmit(text.trim())}
        disabled={disabled || !text.trim()}
        className="mt-4 w-full py-3 bg-blue-600 text-white rounded-lg font-medium text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
        {t('match.find_trials')}
      </button>
    </div>
  );
}
