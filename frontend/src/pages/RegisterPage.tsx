import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useState } from 'react';
import { Zap, Mail, Lock, User, Eye, EyeOff, ArrowRight, CheckCircle } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import clsx from 'clsx';

const schema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
    .regex(/[0-9]/, 'Must contain at least one number'),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
});

type RegisterForm = z.infer<typeof schema>;

const perks = [
  'AI resume match scoring',
  'Cover letter generator',
  'Career coach AI',
  'Application tracker',
];

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const { register, handleSubmit, formState: { errors } } = useForm<RegisterForm>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    setServerError('');
    try {
      const response = await api.post('/auth/register', {
        full_name: data.full_name,
        email: data.email,
        password: data.password,
      });
      const { access_token, refresh_token, user_id, email, full_name, role } = response.data;
      setAuth({ id: user_id, email, full_name, role }, access_token, refresh_token);
      navigate('/dashboard');
    } catch (error: any) {
      setServerError(error.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4 relative">
      <div className="absolute inset-0 bg-gradient-mesh opacity-20 pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-4xl grid md:grid-cols-2 gap-8 relative"
      >
        {/* Left — perks */}
        <div className="hidden md:flex flex-col justify-center">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-10 h-10 bg-gradient-brand rounded-xl flex items-center justify-center shadow-glow">
              <Zap size={18} className="text-white" />
            </div>
            <span className="font-bold text-white text-xl">ResuMesh</span>
          </div>
          <h2 className="text-3xl font-bold text-white mb-3 leading-tight">
            Land your dream job<br />
            <span className="gradient-text">10x faster</span>
          </h2>
          <p className="text-slate-400 mb-8 text-sm leading-relaxed">
            Join thousands of professionals who use ResuMesh to optimize their job applications with AI.
          </p>
          <div className="space-y-3">
            {perks.map((perk) => (
              <div key={perk} className="flex items-center gap-3">
                <CheckCircle size={16} className="text-brand-400 flex-shrink-0" />
                <span className="text-slate-300 text-sm">{perk}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right — form */}
        <div className="card p-8">
          <div className="text-center mb-6 md:hidden">
            <div className="w-10 h-10 bg-gradient-brand rounded-xl flex items-center justify-center shadow-glow mx-auto mb-2">
              <Zap size={18} className="text-white" />
            </div>
          </div>
          <h1 className="text-xl font-semibold text-white mb-1">Create your account</h1>
          <p className="text-slate-400 text-sm mb-6">Free forever · No credit card needed</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Full Name</label>
              <div className="relative">
                <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text" placeholder="Aryan Singh"
                  {...register('full_name')}
                  className={clsx('input pl-10', errors.full_name && 'input-error')}
                />
              </div>
              {errors.full_name && <p className="text-red-400 text-xs mt-1">{errors.full_name.message}</p>}
            </div>

            <div>
              <label className="label">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="email" placeholder="you@example.com"
                  {...register('email')}
                  className={clsx('input pl-10', errors.email && 'input-error')}
                />
              </div>
              {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>}
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showPassword ? 'text' : 'password'} placeholder="Min. 8 characters"
                  {...register('password')}
                  className={clsx('input pl-10 pr-10', errors.password && 'input-error')}
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>}
            </div>

            <div>
              <label className="label">Confirm Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="password" placeholder="Repeat password"
                  {...register('confirm_password')}
                  className={clsx('input pl-10', errors.confirm_password && 'input-error')}
                />
              </div>
              {errors.confirm_password && <p className="text-red-400 text-xs mt-1">{errors.confirm_password.message}</p>}
            </div>

            {serverError && (
              <div className="bg-red-900/30 border border-red-800/50 rounded-lg p-3">
                <p className="text-red-400 text-sm">{serverError}</p>
              </div>
            )}

            <button type="submit" disabled={isLoading} className="btn-primary w-full justify-center py-3 mt-2">
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Creating account...
                </span>
              ) : (
                <span className="flex items-center gap-2">Create Account <ArrowRight size={16} /></span>
              )}
            </button>
          </form>

          <p className="text-center text-slate-400 text-sm mt-5">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
