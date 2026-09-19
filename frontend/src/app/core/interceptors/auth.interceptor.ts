import { HttpInterceptorFn } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { inject } from '@angular/core';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const router = inject(Router);
  const token = localStorage.getItem('paideia_access_token');
  const authRequest = token
    ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : request;
  return next(authRequest).pipe(catchError((error: { status?: number }) => {
    if (error.status === 401 && !request.url.includes('/auth/login')) {
      localStorage.removeItem('paideia_access_token');
      localStorage.removeItem('paideia_user');
      void router.navigateByUrl('/login');
    }
    return throwError(() => error);
  }));
};
