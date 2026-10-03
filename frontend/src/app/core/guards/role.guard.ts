import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';

function currentRole(): string {
  try {
    return JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role ?? '';
  } catch {
    return '';
  }
}

export const roleGuard: CanActivateFn = (route) => {
  const router = inject(Router);
  const allowedRoles = route.data['roles'] as string[] | undefined;
  const role = currentRole();

  if (allowedRoles?.includes(role)) return true;
  if (role === 'student' || role === 'parent') return router.createUrlTree(['/mi-avance']);
  return router.createUrlTree([role ? '/dashboard' : '/login']);
};
