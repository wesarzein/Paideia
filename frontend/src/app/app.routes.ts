import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login.page').then((m) => m.LoginPage) },
  {
    path: '',
    canActivateChild: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: 'dashboard', loadComponent: () => import('./features/dashboard/dashboard.page').then((m) => m.DashboardPage), data: { title: 'Dashboard' } },
      { path: 'usuarios', loadComponent: () => import('./features/users/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Usuarios' } },
      { path: 'estudiantes', loadComponent: () => import('./features/students/students.page').then((m) => m.StudentsPage), data: { title: 'Estudiantes' } },
      { path: 'cursos', loadComponent: () => import('./features/academic/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Cursos y gestion academica' } },
      { path: 'evaluaciones', loadComponent: () => import('./features/academic/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Evaluaciones' } },
      { path: 'calificaciones', loadComponent: () => import('./features/grades/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Calificaciones' } },
      { path: 'asistencia', loadComponent: () => import('./features/attendance/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Asistencia' } },
      { path: 'seguimiento', loadComponent: () => import('./features/follow-up/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Seguimiento academico' } },
      { path: 'analitica', loadComponent: () => import('./features/analytics/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Analitica' } },
      { path: 'ia', loadComponent: () => import('./features/ai/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'IA' } },
      { path: 'reportes', loadComponent: () => import('./features/reports/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Reportes' } },
      { path: 'importacion', loadComponent: () => import('./features/imports/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Importacion' } }
    ],
  },
];
