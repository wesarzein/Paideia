import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login.page').then((m) => m.LoginPage) },
  {
    path: '',
    component: ShellComponent,
    canActivateChild: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: 'dashboard', loadComponent: () => import('./features/dashboard/dashboard.page').then((m) => m.DashboardPage), data: { title: 'Dashboard' } },
      { path: 'usuarios', loadComponent: () => import('./features/users/users.page').then((m) => m.UsersPage), data: { title: 'Usuarios' } },
      { path: 'estudiantes', loadComponent: () => import('./features/students/students.page').then((m) => m.StudentsPage), data: { title: 'Estudiantes' } },
      { path: 'cursos', loadComponent: () => import('./features/courses/courses.page').then((m) => m.CoursesPage), data: { title: 'Cursos y gestion academica' } },
      { path: 'evaluaciones', loadComponent: () => import('./features/academic/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Evaluaciones' } },
      { path: 'calificaciones', loadComponent: () => import('./features/grades/grades.page').then((m) => m.GradesPage), data: { title: 'Calificaciones' } },
      { path: 'asistencia', loadComponent: () => import('./features/attendance/attendance.page').then((m) => m.AttendancePage), data: { title: 'Asistencia' } },
      { path: 'seguimiento', loadComponent: () => import('./features/follow-up/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Seguimiento academico' } },
      { path: 'analitica', loadComponent: () => import('./features/analytics/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Analitica' } },
      { path: 'ia', loadComponent: () => import('./features/ai/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'IA' } },
      { path: 'reportes', loadComponent: () => import('./features/reports/reports.page').then((m) => m.ReportsPage), data: { title: 'Reportes' } },
      { path: 'importacion', loadComponent: () => import('./features/imports/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Importacion' } }
    ],
  },
];
