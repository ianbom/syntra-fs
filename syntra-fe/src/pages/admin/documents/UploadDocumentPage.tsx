import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { AdminHeader } from '../../../features/admin/components';
import { Button, Checkbox } from '../../../components/ui';
import { DocumentService } from '../../../services/documentService';

interface UploadFormData {
    file: File | null;
    type: string;
    isPrivate: boolean;
}

const documentTypes = [
    { value: 'journal', label: 'Journal' },
    { value: 'article', label: 'Article' },
    { value: 'thesis', label: 'Thesis' },
    { value: 'report', label: 'Report' },
    { value: 'manual', label: 'Manual' },
    { value: 'other', label: 'Other' },
];

const UploadDocumentPage: React.FC = () => {
    const navigate = useNavigate();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [formData, setFormData] = useState<UploadFormData>({
        file: null,
        type: '',
        isPrivate: false,
    });
    const [isDragging, setIsDragging] = useState(false);

    const handleFileSelect = (file: File | null) => {
        if (file) {
            setFormData(prev => ({ ...prev, file }));
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        handleFileSelect(file);
    };

    const [error, setError] = useState<string | null>(null);

    const uploadMutation = useMutation({
        mutationFn: DocumentService.uploadDocument,
        onSuccess: () => {
            navigate('/admin/documents');
        },
        onError: (err: any) => {
            console.error('Upload failed', err);
            setError(err.response?.data?.detail || 'Upload failed. Please try again.');
        },
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!formData.file || !formData.type) {
            alert('Please select a file and document type');
            return;
        }

        uploadMutation.mutate({
            file: formData.file,
            type: formData.type,
            isPrivate: formData.isPrivate,
        });
    };

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <div>
            <AdminHeader
                title="Upload Document"
                subtitle="Add a new document to the knowledge base"
            />

            <div className="max-w-2xl">
                {error && (
                    <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-200 text-sm">
                        {error}
                    </div>
                )}
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* File Upload Area */}
                    <div className="space-y-2">
                        <label className="block text-sm font-medium text-white/70">
                            Document File
                        </label>
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            className={`
                                relative cursor-pointer rounded-xl border-2 border-dashed p-8
                                transition-all duration-200
                                ${isDragging
                                    ? 'border-white bg-white/5'
                                    : formData.file
                                        ? 'border-green-500/50 bg-green-500/5'
                                        : 'border-white/20 hover:border-white/40 hover:bg-white/[0.02]'
                                }
                            `}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf,.doc,.docx,.txt,.md"
                                onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
                                className="hidden"
                            />

                            <div className="flex flex-col items-center text-center">
                                {formData.file ? (
                                    <>
                                        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-green-500/10 border border-green-500/20 mb-4">
                                            <span className="material-symbols-outlined text-green-400" style={{ fontSize: '28px' }}>
                                                check_circle
                                            </span>
                                        </div>
                                        <p className="text-sm font-medium text-white mb-1">
                                            {formData.file.name}
                                        </p>
                                        <p className="text-xs text-white/50">
                                            {formatFileSize(formData.file.size)}
                                        </p>
                                        <button
                                            type="button"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setFormData(prev => ({ ...prev, file: null }));
                                            }}
                                            className="mt-3 text-xs text-red-400 hover:text-red-300 transition-colors"
                                        >
                                            Remove file
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-white/5 border border-white/10 mb-4">
                                            <span className="material-symbols-outlined text-white/50" style={{ fontSize: '28px' }}>
                                                cloud_upload
                                            </span>
                                        </div>
                                        <p className="text-sm font-medium text-white mb-1">
                                            Drop your file here or click to browse
                                        </p>
                                        <p className="text-xs text-white/40">
                                            Supports PDF, DOC, DOCX, TXT, MD
                                        </p>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Document Type */}
                    <div className="space-y-2">
                        <label className="block text-sm font-medium text-white/70">
                            Document Type
                        </label>
                        <div className="relative">
                            <span
                                className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-white/30"
                                style={{ fontSize: '20px' }}
                            >
                                category
                            </span>
                            <select
                                value={formData.type}
                                onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
                                className="h-12 w-full appearance-none rounded-lg border border-white/10 bg-black/40 pl-11 pr-10 text-sm text-white transition-all focus:border-white/40 focus:bg-black/60 focus:outline-none focus:ring-1 focus:ring-white/20"
                                required
                            >
                                <option value="" disabled className="bg-black text-white/50">
                                    Select document type
                                </option>
                                {documentTypes.map((type) => (
                                    <option key={type.value} value={type.value} className="bg-black text-white">
                                        {type.label}
                                    </option>
                                ))}
                            </select>
                            <span
                                className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none"
                                style={{ fontSize: '20px' }}
                            >
                                expand_more
                            </span>
                        </div>
                    </div>

                    {/* Privacy Toggle */}
                    <div className="space-y-2">
                        <label className="block text-sm font-medium text-white/70">
                            Privacy Setting
                        </label>
                        <div className="flex items-center gap-4 rounded-lg border border-white/10 bg-black/40 p-4">
                            <Checkbox
                                checked={formData.isPrivate}
                                onChange={(e) => setFormData(prev => ({ ...prev, isPrivate: e.target.checked }))}
                            />
                            <div>
                                <p className="text-sm font-medium text-white">Private Document</p>
                                <p className="text-xs text-white/40">
                                    Only admins will be able to access this document
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-4">
                        <Button
                            type="button"
                            variant="secondary"
                            onClick={() => navigate('/admin/documents')}
                            className="flex-1"
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            variant="primary"
                            icon="upload"
                            iconPosition="left"
                            isLoading={uploadMutation.isPending}
                            className="flex-1"
                        >
                            {uploadMutation.isPending ? 'Uploading...' : 'Upload Document'}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default UploadDocumentPage;
