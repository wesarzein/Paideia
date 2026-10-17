import { moduleRoles } from './core/module-access';
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
      { path: 'dashboard', canActivate: [roleGuard], loadComponent: () => import('./features/dashboard/dashboard.page').then((m) => m.DashboardPage), data: { title: 'Inicio', roles: moduleRoles['dashboard'] } },
      { path: 'usuarios', canActivate: [roleGuard], loadComponent: () => import('./features/users/users.page').then((m) => m.UsersPage), data: { title: 'Usuarios', roles: moduleRoles['usuarios'] } },
      { path: 'grados-secciones', canActivate: [roleGuard], loadComponent: () => import('./features/courses/cohorts.page').then((m) => m.CohortsPage), data: { title: 'Grados y secciones', roles: moduleRoles['grados-secciones'] } },
      { path: 'estudiantes', canActivate: [roleGuard], loadComponent: () => import('./features/students/students.page').then((m) => m.StudentsPage), data: { title: 'Estudiantes', roles: moduleRoles['estudiantes'] } },
      { path: 'cursos', canActivate: [roleGuard], loadComponent: () => import('./features/courses/courses.page').then((m) => m.CoursesPage), data: { title: 'Cursos', roles: moduleRoles['cursos'] } },
      { path: 'calificaciones', canActivate: [roleGuard], loadComponent: () => import('./features/grades/grades.page').then((m) => m.GradesPage), data: { title: 'Calificaciones', roles: moduleRoles['calificaciones'] } },
      { path: 'asistencia', canActivate: [roleGuard], loadComponent: () => import('./features/attendance/attendance.page').then((m) => m.AttendancePage), data: { title: 'Asistencia', roles: moduleRoles['asistencia'] } },
      { path: 'seguimiento', canActivate: [roleGuard], loadComponent: () => import('./features/follow-up/placeholder.page').then((m) => m.PlaceholderPage), data: { title: 'Seguimiento academico', roles: moduleRoles['seguimiento'] } },
      { path: 'analitica', canActivate: [roleGuard], loadComponent: () => import('./features/analytics/analytics.page').then((m) => m.AnalyticsPage), data: { title: 'Analitica', roles: moduleRoles['analitica'] } },
      { path: 'ia', canActivate: [roleGuard], loadComponent: () => import('./features/ai/academic-ai.page').then((m) => m.AcademicAiPage), data: { title: 'IA', roles: moduleRoles['ia'] } },
      { path: 'reportes', canActivate: [roleGuard], loadComponent: () => import('./features/reports/reports.page').then((m) => m.ReportsPage), data: { title: 'Reportes', roles: moduleRoles['reportes'] } },
      { path: 'importacion', canActivate: [roleGuard], loadComponent: () => import('./features/imports/imports.page').then((m) => m.ImportsPage), data: { title: 'Importacion', roles: moduleRoles['importacion'] } }
    ],
  },
];
