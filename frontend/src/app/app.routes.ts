import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login.page').then((m) => m.LoginPage) },
  {
    path: '',
    component: ShellComponent,
    canActivateChild: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: 'dashboard', canActivate: [roleGuard], loadComponent: () => import('./features/dashboard/dashboard.page').then((m) => m.DashboardPage), data: { title: 'Dashboard', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'mi-avance', canActivate: [roleGuard], loadComponent: () => import('./features/portal/my-academic.page').then((m) => m.MyAcademicPage), data: { title: 'Mi avance académico', roles: ['student', 'parent'] } },
      { path: 'usuarios', canActivate: [roleGuard], loadComponent: () => import('./features/users/users.page').then((m) => m.UsersPage), data: { title: 'Usuarios', roles: ['admin'] } },
      { path: 'estudiantes', canActivate: [roleGuard], loadComponent: () => import('./features/students/students.page').then((m) => m.StudentsPage), data: { title: 'Estudiantes', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'cursos', canActivate: [roleGuard], loadComponent: () => import('./features/courses/courses.page').then((m) => m.CoursesPage), data: { title: 'Cursos y gestion academica', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'calificaciones', canActivate: [roleGuard], loadComponent: () => import('./features/grades/grades.page').then((m) => m.GradesPage), data: { title: 'Calificaciones', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'asistencia', canActivate: [roleGuard], loadComponent: () => import('./features/attendance/attendance.page').then((m) => m.AttendancePage), data: { title: 'Asistencia', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'seguimiento', canActivate: [roleGuard], loadComponent: () => import('./features/follow-up/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Seguimiento academico', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'analitica', canActivate: [roleGuard], loadComponent: () => import('./features/analytics/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Analitica', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'ia', canActivate: [roleGuard], loadComponent: () => import('./features/ai/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'IA', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'reportes', canActivate: [roleGuard], loadComponent: () => import('./features/reports/reports.page').then((m) => m.ReportsPage), data: { title: 'Reportes', roles: ['admin', 'teacher', 'coordinator', 'director'] } },
      { path: 'importacion', canActivate: [roleGuard], loadComponent: () => import('./features/imports/imports.page').then((m) => m.ImportsPage), data: { title: 'Importacion', roles: ['admin', 'teacher'] } }
    ],
  },
];
