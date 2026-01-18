export interface Document {
    id: number;
    title: string;
    creator: string;
    keywords: string | null;
    description: string | null;
    publisher: string | null;
    contributor: string | null;
    publication_date: string | null; // Date string
    type: string;
    format: string | null;
    identifier: string | null;
    source: string | null;
    language: string | null;
    relation: string | null;
    coverage: string | null;
    rights: string | null;
    doi: string | null;
    abstract: string | null;
    citation_count: number;
    file_path: string | null;
    is_private: boolean;
    is_metadata_complete: boolean;
    created_at: string;
    updated_at: string;
    chunk_count: number;
}

export interface DocumentUploadResponse extends Document { }

export interface UploadDocumentParams {
    file: File;
    type: string;
    isPrivate: boolean;
}
