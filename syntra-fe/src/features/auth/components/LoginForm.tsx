import React, { useState } from 'react';
import { Input, Button, Checkbox, Divider } from '../../../components/ui';
import { SocialLoginButton } from './SocialLoginButton';

interface LoginFormProps {
    onSubmit: (email: string, password: string, rememberMe: boolean) => void;
    onGoogleLogin?: () => void;
    onForgotPassword?: () => void;
    isLoading?: boolean;
}

export const LoginForm: React.FC<LoginFormProps> = ({
    onSubmit,
    onGoogleLogin,
    onForgotPassword,
    isLoading = false,
}) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit(email, password, rememberMe);
    };

    return (
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
            {/* Email Input */}
            <Input
                type="email"
                icon="mail"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
            />

            {/* Password Input */}
            <Input
                type="password"
                icon="lock"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                showPasswordToggle
                required
                autoComplete="current-password"
            />

            {/* Row: Remember Me & Forgot Password */}
            <div className="flex items-center justify-between text-xs">
                <Checkbox
                    label="Remember me"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                />
                <button
                    type="button"
                    onClick={onForgotPassword}
                    className="font-medium text-white/70 hover:text-white hover:underline decoration-white/30 underline-offset-4 transition-all"
                >
                    Forgot password?
                </button>
            </div>

            {/* Submit Button */}
            <Button
                type="submit"
                variant="primary"
                icon="arrow_forward"
                isLoading={isLoading}
                className="group mt-2"
            >
                Sign In
            </Button>

            {/* Divider */}
            {/* <Divider text="Or" /> */}

            {/* Google Button */}
            {/* <SocialLoginButton
                provider="google"
                onClick={onGoogleLogin}
                isLoading={isLoading}
            /> */}
        </form>
    );
};
