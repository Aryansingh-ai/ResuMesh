import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, FileText, Trash2, Star, Eye, CheckCircle,
  AlertCircle, Clock, Plus, X,
} from 'lucide-react';
import api from '@/lib/api';
import clsx from 'clsx';

const FileCard = ({ resume, onDelete, onSetPrimary }: any) => (
  <motion.div
    layout
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    exit={{ opacity: 0, scale: 0.95 }}
    className={clsx(
      'card p-5 transition-all duration-200',
      resume.is_primary && 'border-brand-600/50'
    )}
  >
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-start gap-3 flex-1 min-w-0">
        <div className={clsx(
          'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
          resume.file_type === 'pdf' ? 'bg-red-900/30' : 'bg-blue-900/30'
        )}>
          <FileText size={18} className={resume.file_type === 'pdf' ? 'text-red-400' : 'text-blue-400'} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-white text-sm truncate">{resume.title}</h3>
            {resume.is_primary && (
              <span className="badge-purple text-[10px]">
                <Star size={9} className="mr-1" /> Primary
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5 truncate">{resume.file_name}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-[10px] text-slate-500 uppercase">{resume.file_type}</span>
            <span className="text-[10px] text-slate-500">·</span>
            <span className="text-[10px] text-slate-500">{(resume.file_size_bytes / 1024).toFixed(0)} KB</span>
            <span className="text-[10px] text-slate-500">·</span>
            {resume.is_parsed ? (
              <span className="flex items-center gap-1 text-[10px] text-green-400">
                <CheckCircle size={10} /> Parsed
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[10px] text-yellow-400">
                <Clock size={10} /> Parsing...
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {!resume.is_primary && (
          <button
            onClick={() => onSetPrimary(resume.id)}
            className="btn-ghost p-1.5 text-xs"
            title="Set as primary"
          >
            <Star size={14} />
          </button>
        )}
        <button
          onClick={() => onDelete(resume.id)}
          className="btn-ghost p-1.5 text-red-400 hover:text-red-300 hover:bg-red-900/20"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  </motion.div>
);

export default function ResumeManagerPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadTitle, setUploadTitle] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => api.get('/resumes/').then((r) => r.data),
    refetchInterval: (query) => {
      const items = query?.state?.data?.items || [];
      const hasUnparsed = items.some((r: any) => !r.is_parsed);
      return hasUnparsed ? 2000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ file, title }: { file: File; title: string }) => {
      const form = new FormData();
      form.append('file', file);
      form.append('title', title);
      form.append('is_primary', data?.items?.length === 0 ? 'true' : 'false');
      return api.post('/resumes/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      setSelectedFile(null);
      setUploadTitle('');
      setUploadError('');
    },
    onError: (error: any) => {
      setUploadError(error.response?.data?.detail || 'Upload failed');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/resumes/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resumes'] }),
  });

  const handleFileSelect = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx'].includes(ext || '')) {
      setUploadError('Only PDF and DOCX files are allowed');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File must be under 10MB');
      return;
    }
    setSelectedFile(file);
    setUploadTitle(file.name.replace(/\.(pdf|docx)$/i, ''));
    setUploadError('');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleUpload = () => {
    if (!selectedFile || !uploadTitle.trim()) return;
    uploadMutation.mutate({ file: selectedFile, title: uploadTitle });
  };

  const resumes = data?.items || [];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Resume Manager</h1>
        <p className="page-subtitle">Upload and manage your resumes. Mark one as primary for auto-matching.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Panel */}
        <div className="lg:col-span-1">
          <div className="card p-5 sticky top-4">
            <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
              <Plus size={16} className="text-brand-400" /> Upload Resume
            </h2>

            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => !selectedFile && fileInputRef.current?.click()}
              className={clsx(
                'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200 mb-4',
                isDragging ? 'border-brand-500 bg-brand-900/20' : 'border-dark-400 hover:border-brand-600/50 hover:bg-dark-800/50'
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              />
              {selectedFile ? (
                <div>
                  <CheckCircle size={28} className="text-green-400 mx-auto mb-2" />
                  <div className="text-sm text-white font-medium truncate">{selectedFile.name}</div>
                  <div className="text-xs text-slate-400 mt-1">{(selectedFile.size / 1024).toFixed(0)} KB</div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                    className="text-xs text-red-400 hover:text-red-300 mt-2 flex items-center gap-1 mx-auto"
                  >
                    <X size={12} /> Remove
                  </button>
                </div>
              ) : (
                <div>
                  <Upload size={28} className="text-slate-500 mx-auto mb-2" />
                  <div className="text-sm text-slate-300 font-medium">Drop file or click to browse</div>
                  <div className="text-xs text-slate-500 mt-1">PDF, DOCX · Max 10MB</div>
                </div>
              )}
            </div>

            {selectedFile && (
              <div className="mb-4">
                <label className="label">Resume Title</label>
                <input
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="e.g. Software Engineer Resume"
                  className="input"
                />
              </div>
            )}

            {uploadError && (
              <div className="flex items-center gap-2 text-red-400 text-xs mb-3">
                <AlertCircle size={12} /> {uploadError}
              </div>
            )}

            <button
              onClick={handleUpload}
              disabled={!selectedFile || !uploadTitle.trim() || uploadMutation.isPending}
              className="btn-primary w-full justify-center"
            >
              {uploadMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Uploading...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Upload size={15} /> Upload Resume
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Resume List */}
        <div className="lg:col-span-2">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="card p-5 shimmer h-20 rounded-xl" />
              ))}
            </div>
          ) : resumes.length === 0 ? (
            <div className="card p-12 text-center">
              <FileText size={40} className="text-slate-600 mx-auto mb-4" />
              <h3 className="text-white font-medium mb-2">No resumes yet</h3>
              <p className="text-slate-400 text-sm">Upload your first resume to start analyzing jobs.</p>
            </div>
          ) : (
            <AnimatePresence>
              <div className="space-y-3">
                {resumes.map((resume: any) => (
                  <FileCard
                    key={resume.id}
                    resume={resume}
                    onDelete={(id: string) => deleteMutation.mutate(id)}
                    onSetPrimary={() => {}} // Could implement PATCH /resumes/{id}
                  />
                ))}
              </div>
            </AnimatePresence>
          )}

          {resumes.length > 0 && (
            <p className="text-slate-500 text-xs mt-4 text-center">
              {resumes.length} resume{resumes.length > 1 ? 's' : ''} · Your primary resume is used for auto-matching
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
