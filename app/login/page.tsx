import { Suspense } from "react";
import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-mist" />}>
      <LoginForm />
    </Suspense>
  );
}
