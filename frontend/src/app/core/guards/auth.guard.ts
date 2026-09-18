import { CanActivateChildFn, Router } from '@angular/router';
import { inject } from '@angular/core';

export const authGuard: CanActivateChildFn = () => {
  const router = inject(Router);
  const token = localStorage.getItem('paideia_access_token');
  return token ? true : router.createUrlTree(['/login']);
};
