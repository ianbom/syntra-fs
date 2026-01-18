import React from 'react';
import { Button } from '../../../components/ui';

interface SocialLoginButtonProps {
    provider: 'google';
    onClick?: () => void;
    isLoading?: boolean;
}

export const SocialLoginButton: React.FC<SocialLoginButtonProps> = ({
    provider,
    onClick,
    isLoading = false,
}) => {
    const providerConfig = {
        google: {
            label: 'Continue with Google',
            // Using grayscale Google logo for monochrome design
            icon: (
                <img
                    alt="Google Logo"
                    className="h-5 w-5 grayscale opacity-80 group-hover:opacity-100 transition-opacity"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuBFAJ4IlUJogfeVTqxiTQH8YbCP1n9SajF1Vm5iK6ie1JV-D4N0rqIi25bA4czncFpyTsNKiea4MBdfQTlE3okN3hBn4qsXGbMKcydY4BOb_Zi0uy_7KJO-MlLHSp8O3c40LTH-NnV_RSm599DOH6GEKgXG_-kzAfldteh7Tqznof0mj1NpPFCHTDXvGMELQRDCGW9I6niVuBHpq7m2HGNsyxb96pTF9nMmBhj3eFdOqJqWrkI6-hhartHcIQ24fLutguKEZh49wM8"
                />
            ),
        },
    };

    const config = providerConfig[provider];

    return (
        <Button
            variant="secondary"
            onClick={onClick}
            disabled={isLoading}
            className="gap-3 group"
        >
            {config.icon}
            <span>{config.label}</span>
        </Button>
    );
};
