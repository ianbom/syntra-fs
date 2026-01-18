import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthLayout } from '../../components/layouts';
import { GlassCard } from '../../components/ui';
import { useMutation } from '@tanstack/react-query';
import { useAuthStore } from '../../store/authStore';
import { AuthService } from '../../services/authService';
import {
    AuthHeader,
    LoginForm,
    StatusIndicator,
    AuthFooter,
} from '../../features/auth/components';

const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const { setAuth } = useAuthStore();
    const [error, setError] = React.useState<string | null>(null);

    const loginMutation = useMutation({
        mutationFn: AuthService.login,
        onSuccess: (data) => {
            setAuth(data.user, data.accessToken, data.refreshToken);
            navigate('/admin/dashboard');
        },
        onError: (err: any) => {
            console.error('Login failed', err);
            setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
        },
    });

    const handleLogin = (email: string, password: string, rememberMe: boolean) => {
        setError(null);
        loginMutation.mutate({ email, password, rememberMe });
    };


    const handleForgotPassword = () => {
        console.log('Forgot password clicked');
        // TODO: Navigate to forgot password page
        navigate('/forgot-password');
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

                {error && (
                    <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-200 text-sm text-center">
                        {error}
                    </div>
                )}

                <LoginForm
                    onSubmit={handleLogin}
                   
                    onForgotPassword={handleForgotPassword}
                    isLoading={loginMutation.isPending}
                />
            </GlassCard>
        </AuthLayout>
    );
};

export default LoginPage;
