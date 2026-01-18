import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthLayout } from '../../components/layouts';
import { GlassCard } from '../../components/ui';
import {
    AuthHeader,
    LoginForm,
    StatusIndicator,
    AuthFooter,
} from '../../features/auth/components';

const LoginPage: React.FC = () => {
    const navigate = useNavigate();

    const handleLogin = (email: string, password: string, rememberMe: boolean) => {
        console.log('Login attempt:', { email, password, rememberMe });
        // TODO: Implement actual login logic with TanStack Query mutation
        // For now, simulate login and redirect to dashboard
        navigate('/admin/dashboard');
    };

    const handleGoogleLogin = () => {
        console.log('Google login clicked');
        // TODO: Implement Google OAuth
    };

    const handleForgotPassword = () => {
        console.log('Forgot password clicked');
        // TODO: Navigate to forgot password page
    };

    return (
        <AuthLayout
            footerContent={
                <AuthFooter
                    text="Don't have an account?"
                    linkText="Request Access"
                    linkTo="/register"
                />
            }
        >
            <GlassCard
                footer={<StatusIndicator status="operational" version="2.0.4" />}
            >
                <AuthHeader
                    icon="blur_on"
                    title="Welcome Back"
                    subtitle="Enter the knowledge matrix"
                />
                <LoginForm
                    onSubmit={handleLogin}
                    onGoogleLogin={handleGoogleLogin}
                    onForgotPassword={handleForgotPassword}
                />
            </GlassCard>
        </AuthLayout>
    );
};

export default LoginPage;
