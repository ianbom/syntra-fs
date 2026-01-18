import React from 'react';
import { AmbientBackground } from '../common/AmbientBackground';

interface AuthLayoutProps {
    children: React.ReactNode;
    footerContent?: React.ReactNode;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children, footerContent }) => {
    return (
        <div className="relative flex min-h-screen w-full flex-col overflow-hidden text-white bg-background-dark selection:bg-primary selection:text-black">
            {/* Ambient Background Effects */}
            <AmbientBackground variant="auth" />

            {/* Main Content */}
            <div className="relative z-10 flex h-full grow flex-col items-center justify-center p-4">
                {children}

                {/* Bottom Page Footer */}
                {footerContent && (
                    <div
                        className="animate-fade-in-delay mt-8 flex flex-col items-center gap-4 text-center opacity-0"
                        style={{ animationFillMode: 'forwards' }}
                    >
                        {footerContent}
                    </div>
                )}
            </div>
        </div>
    );
};
