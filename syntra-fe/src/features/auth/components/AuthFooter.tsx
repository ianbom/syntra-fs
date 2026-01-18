import React from 'react';
import { Link } from 'react-router-dom';

interface AuthFooterProps {
    text: string;
    linkText: string;
    linkTo: string;
}

export const AuthFooter: React.FC<AuthFooterProps> = ({ text, linkText, linkTo }) => {
    return (
        <>
            <p className="text-sm text-white/40">
                {text}
                <Link
                    to={linkTo}
                    className="font-medium text-white hover:underline underline-offset-4 transition-colors ml-1"
                >
                    {linkText}
                </Link>
            </p>
            <div className="flex gap-6 text-xs text-white/20">
                <a href="#" className="hover:text-white/40 transition-colors">
                    Privacy
                </a>
                <a href="#" className="hover:text-white/40 transition-colors">
                    Terms
                </a>
                <a href="#" className="hover:text-white/40 transition-colors">
                    Help
                </a>
            </div>
        </>
    );
};
