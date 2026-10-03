import { Component } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { inject } from '@angular/core';

import { ApiService } from '../core/services/api.service';

const links = [
  { label: 'Dashboard', path: '/dashboard', icon: 'M3 13h8V3H3v10Zm10 8h8V11h-8v10ZM3 21h8v-6H3v6Zm10-12h8V3h-8v6Z' },
  { label: 'Usuarios', path: '/usuarios', icon: 'M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m6-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm6-7.8a4 4 0 0 1 0 7.6M20 21v-2a4 4 0 0 0-3-3.87' },
  { label: 'Estudiantes', path: '/estudiantes', icon: 'M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m6-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z' },
  { label: 'Cursos', path: '/cursos', icon: 'M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5v-17Zm0 0V20' },
  { label: 'Calificaciones', path: '/calificaciones', icon: 'm4 12 5 5L20 6' },
  { label: 'Asistencia', path: '/asistencia', icon: 'M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z' },
  { label: 'Seguimiento', path: '/seguimiento', icon: 'M4 4h16v16H4zM8 8h8M8 12h8m-8 4h5' },
  { label: 'Analítica', path: '/analitica', icon: 'M4 19V5m0 14h17M8 15l3-4 3 2 5-7' },
  { label: 'IA', path: '/ia', icon: 'M12 3v2m0 14v2m9-9h-2M5 12H3m13-5a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm2 10H7' },
  { label: 'Reportes', path: '/reportes', icon: 'M6 2h9l5 5v15H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm8 1v5h5M8 13h8m-8 4h8' },
  { label: 'Importación', path: '/importacion', icon: 'M12 16V4m-4 4 4-4 4 4M4 16v4h16v-4' },
];

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <aside>
      <div class="brand"><img src="assets/logo.png" alt="IE Paideia Newton" /></div>
      <nav>
        @for (link of links; track link.path) {
          <a [routerLink]="link.path" routerLinkActive="active"><svg viewBox="0 0 24 24" aria-hidden="true"><path [attr.d]="link.icon" /></svg><span>{{ link.label }}</span></a>
        }
      </nav>
    </aside>
    <main>
      <header class="topbar">
        <span>Panel institucional</span>
        <button type="button" (click)="logout()">Cerrar sesión</button>
      </header>
      <router-outlet />
    </main>
  `,
  styles: [`
    :host { display: grid; grid-template-columns: 248px 1fr; min-height: 100vh; background: var(--color-muted); }
    aside { background: #fff; color: var(--color-text); padding: 20px 14px; border-right: 1px solid var(--color-border); }
    .brand { display: flex; align-items: center; margin-bottom: 22px; padding: 0 8px; } .brand img { width: 148px; max-width: 100%; height: 58px; object-fit: contain; object-position: left center; }
    nav { display: grid; gap: 3px; }
    a { display:flex; align-items:center; gap:11px; border-radius: 7px; color: var(--color-muted-text); padding: 10px 12px; font-size:.91rem; transition:background .15s,color .15s; }
    a svg { width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;flex:none; }
    a.active { background: #fff5e7; color: #995c13; font-weight:600; box-shadow:inset 2px 0 var(--color-accent); }
    a:hover:not(.active) { background: var(--color-muted); color: var(--color-text); }
    main { padding: 22px 28px 32px; min-width: 0; }
    .topbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 22px; color: var(--color-muted-text); }
    button { border: 1px solid var(--color-border); border-radius: 7px; padding: 9px 13px; color: var(--color-text); background: white; cursor: pointer; font: inherit; }
    button:hover{border-color:var(--color-accent);color:#995c13}
    @media (max-width: 820px) { :host { grid-template-columns: 1fr; } aside { position: static; padding:12px; } .brand{margin-bottom:10px}.brand img{height:44px} nav { display:flex;overflow-x:auto;padding-bottom:4px } nav a{white-space:nowrap } main{padding:16px} }
  `],
})
export class ShellComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  protected readonly links = this.visibleLinks();

  private visibleLinks() {
    let role = '';
    try {
      role = JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role ?? '';
    } catch {
      role = '';
    }
    if (role === 'student' || role === 'parent') {
      return [{ label: 'Mi avance académico', path: '/mi-avance', icon: 'M4 19V5m0 14h17M8 15l3-4 3 2 5-7' }];
    }
    const teacherLinks = new Set(['/dashboard', '/estudiantes', '/cursos', '/calificaciones', '/asistencia', '/seguimiento', '/analitica', '/ia', '/reportes', '/importacion']);
    if (role === 'teacher') return links.filter((link) => teacherLinks.has(link.path));
    if (role === 'coordinator' || role === 'director') {
      return links.filter((link) => link.path !== '/usuarios' && link.path !== '/importacion');
    }
    return role === 'admin' ? links : [];
  }

  protected logout(): void {
    this.api.logout().subscribe({ complete: () => this.finishLogout(), error: () => this.finishLogout() });
  }

  private finishLogout(): void {
    localStorage.removeItem('paideia_access_token');
    localStorage.removeItem('paideia_user');
    void this.router.navigateByUrl('/login');
  }
}
