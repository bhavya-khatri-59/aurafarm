import { AuthForm } from '@/components/AuthForm';
import { useAuth } from '@/lib/auth';

export default function LoginScreen() {
  const { signIn } = useAuth();
  return (
    <AuthForm
      title="Welcome back"
      subtitle="Sign in to continue caring for your crops."
      fields={[
        { key: 'email', label: 'Email', email: true },
        { key: 'password', label: 'Password', secure: true },
      ]}
      submitLabel="Sign in"
      onSubmit={({ email = '', password = '' }) => signIn(email.trim(), password)}
      footerText="New to AuraFarm?"
      footerLink={{ href: '/register', label: 'Create an account' }}
    />
  );
}
