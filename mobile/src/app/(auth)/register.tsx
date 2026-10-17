import { AuthForm } from '@/components/AuthForm';
import { useAuth } from '@/lib/auth';

export default function RegisterScreen() {
  const { signUp } = useAuth();
  return (
    <AuthForm
      title="Create your account"
      subtitle="Diagnose plant diseases and get treatment advice."
      fields={[
        { key: 'name', label: 'Name' },
        { key: 'email', label: 'Email', email: true },
        { key: 'password', label: 'Password (8+ characters)', secure: true },
      ]}
      submitLabel="Create account"
      onSubmit={({ name = '', email = '', password = '' }) => signUp(email.trim(), name.trim(), password)}
      footerText="Already have an account?"
      footerLink={{ href: '/login', label: 'Sign in' }}
    />
  );
}
