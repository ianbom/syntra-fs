import React from 'react';
import { DocumentService } from '../../../services/documentService';

interface MessageReference {
    document_title: string;
    page_number?: number;
    quote: string;
    file_path?: string;
    document_id: number;
}

export interface MessageProps {
    role: 'user' | 'bot';
    content: string;
    timestamp: string;
    references?: MessageReference[];
}

export const MessageItem: React.FC<MessageProps> = ({ role, content, timestamp, references }) => {
    const isBot = role === 'bot';

    return (
        <div className={`flex ${isBot ? 'items-start' : 'flex-row-reverse items-start'} gap-4 max-w-4xl mx-auto`}>
            {isBot ? (
                <div className="flex-shrink-0 size-9 rounded-full bg-gradient-to-tr from-gray-800 to-black border border-white/20 flex items-center justify-center shadow-lg">
                    <div className="size-3 rounded-sm bg-white transform rotate-45 shadow-[0_0_8px_rgba(255,255,255,0.15)]"></div>
                </div>
            ) : (
                <div className="flex-shrink-0 size-9 rounded-full bg-gray-700 border border-white/20 shadow-lg flex items-center justify-center text-white text-xs">
                    U
                </div>
            )}

            <div className={`flex flex-col gap-2 flex-1 min-w-0 ${isBot ? 'animate-[fadeIn_0.5s_ease-out]' : 'items-end animate-[fadeIn_0.5s_ease-out_0.1s_both]'}`}>
                <div className="flex items-baseline gap-2">
                    {isBot ? (
                        <>
                            <span className="text-white font-medium text-xs">Syntra AI</span>
                            <span className="text-gray-500 text-[10px]">{timestamp}</span>
                        </>
                    ) : (
                        <>
                            <span className="text-gray-500 text-[10px]">{timestamp}</span>
                            <span className="text-white font-medium text-xs">You</span>
                        </>
                    )}
                </div>

                <div className={`${isBot ? 'glass-card-assistant rounded-tl-sm text-gray-200' : 'glass-card-user rounded-tr-sm text-white'} p-5 rounded-2xl leading-relaxed text-[15px]`}>
                    <div className="whitespace-pre-wrap">{content}</div>

                    {references && references.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-white/10">
                            <div className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wider">References:</div>
                            <div className="flex flex-col gap-2">
                                {references.map((ref, idx) => (
                                    <div key={idx} className="bg-white/5 border border-white/10 p-2 rounded text-xs text-gray-300">
                                        <div className="flex justify-between items-start gap-2">
                                            <div className="font-semibold text-white">{ref.document_title} {ref.page_number && `(Page ${ref.page_number})`}</div>
                                            {/* Assuming file_path is relative to public or handle via API download endpoint later. For now just displaying it or linking if it's a URL */}
                                            {/*  Ideally this should be a proper download link from backend. For now we just mock the href or use the path if it's a public URL */}
                                            {/* We will assume it's not directly accessible yet without a presigned URL, so just showing a placeholder action or if it's a local static path */}
                                            {/* If the user wants to "open" it, we likely need a download endpoint. */}
                                            {/* For now, let's just make it a non-functional link or specific endpoint if we knew it. */}
                                            {/* User asked to "bisa membuka file tersebut", implying a working link. */}
                                            {/* We'll assume a route /api/documents/download/{id} or similar exists or just use the path if it's served statically. */}
                                            {/* Let's render a button/link. */}
                                        </div>
                                        <div className="mt-1 italic opacity-80 line-clamp-2">"{ref.quote}"</div>
                                        {/* Adding a File Open Link */}
                                        <div className="mt-2 pt-2 border-t border-white/5">
                                            <a
                                                href="#"
                                                onClick={async (e) => {
                                                    e.preventDefault();
                                                    try {
                                                        const response = await DocumentService.getDownloadUrl(ref.document_id);
                                                        if (response.download_url) {
                                                            window.open(response.download_url, '_blank');
                                                        } else {
                                                            alert("Download URL not found");
                                                        }
                                                    } catch (err) {
                                                        console.error("Error opening document:", err);
                                                        alert("Failed to open document");
                                                    }
                                                }}
                                                className="flex items-center gap-1 text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
                                            >
                                                <span className="material-symbols-outlined text-[10px]">open_in_new</span>
                                                Open Document
                                            </a>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
