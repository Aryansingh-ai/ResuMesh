import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useState } from 'react';
import { Zap, Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import clsx from 'clsx';

const schema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginForm = z.infer<typeof schema>;

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    setServerError('');
    try {
      const response = await api.post('/auth/login', data);
      const { access_token, refresh_token, user_id, email, full_name, role } = response.data;
      setAuth({ id: user_id, email, full_name, role }, access_token, refresh_token);
      navigate('/dashboard');
    } catch (error: any) {
      setServerError(error.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4 relative">
      <div className="absolute inset-0 bg-gradient-mesh opacity-20 pointer-events-none" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[400px] h-[400px] bg-brand-600/10 rounded-full blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md relative"
      >
        <div className="card p-8">
          {/* Logo */}
          <div className="text-center mb-8">
            <Link to="/" className="inline-flex flex-col items-center gap-2">
              <div className="w-12 h-12 bg-gradient-brand rounded-xl flex items-center justify-center shadow-glow">
                <Zap size={22} className="text-white" />
              </div>
              <span className="font-bold text-white text-xl">ResuMesh</span>
            </Link>
            <h1 className="text-xl font-semibold text-white mt-4">Welcome back</h1>
            <p className="text-slate-400 text-sm mt-1">Sign in to your account</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Email */}
            <div>
              <label htmlFor="email" className="label">Email address</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  {...register('email')}
                  className={clsx('input pl-10', errors.email && 'input-error')}
                />
              </div>
              {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>}
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="label">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  {...register('password')}
                  className={clsx('input pl-10 pr-10', errors.password && 'input-error')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>}
            </div>

            {/* Server error */}
            {serverError && (
              <div className="bg-red-900/30 border border-red-800/50 rounded-lg p-3">
                <p className="text-red-400 text-sm">{serverError}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full justify-center py-3"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  Sign In <ArrowRight size={16} />
                </span>
              )}
            </button>
          </form>

          <p className="text-center text-slate-400 text-sm mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-brand-400 hover:text-brand-300 font-medium transition-colors">
              Create one free
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
