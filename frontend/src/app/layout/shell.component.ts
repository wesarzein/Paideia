import { Component } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { inject } from '@angular/core';

import { ApiService } from '../core/services/api.service';

const links = [
  ['Dashboard', '/dashboard'],
  ['Usuarios', '/usuarios'],
  ['Estudiantes', '/estudiantes'],
  ['Cursos', '/cursos'],
  ['Evaluaciones', '/evaluaciones'],
  ['Calificaciones', '/calificaciones'],
  ['Asistencia', '/asistencia'],
  ['Seguimiento', '/seguimiento'],
  ['Analitica', '/analitica'],
  ['IA', '/ia'],
  ['Reportes', '/reportes'],
  ['Importacion', '/importacion'],
];

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <aside>
      <div class="brand"><img src="assets/logo.png" alt="Logo del colegio" /><strong>Paideia</strong></div>
      <nav>
        @for (link of links; track link[1]) {
          <a [routerLink]="link[1]" routerLinkActive="active">{{ link[0] }}</a>
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
    :host { display: grid; grid-template-columns: 260px 1fr; min-height: 100vh; background: var(--color-muted); }
    aside { background: var(--color-primary); color: white; padding: 24px 18px; }
    strong { display: block; font-size: 1.35rem; margin-bottom: 22px; }
    .brand { display: flex; align-items: center; gap: 10px; margin-bottom: 22px; } .brand strong { margin: 0; } .brand img { width: 42px; height: 42px; object-fit: contain; border-radius: 6px; background: white; }
    nav { display: grid; gap: 4px; }
    a { border-radius: 8px; color: #d9e2ec; padding: 10px 12px; }
    a.active, a:hover { background: var(--color-primary-dark); color: white; }
    main { padding: 20px 28px 28px; min-width: 0; }
    .topbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 22px; color: var(--color-muted-text); }
    button { border: 1px solid var(--color-primary); border-radius: 6px; padding: 9px 13px; color: var(--color-primary); background: white; cursor: pointer; font: inherit; }
    @media (max-width: 820px) { :host { grid-template-columns: 1fr; } aside { position: static; } nav { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); } }
  `],
})
export class ShellComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  protected readonly links = links;

  protected logout(): void {
    this.api.logout().subscribe({ complete: () => this.finishLogout(), error: () => this.finishLogout() });
  }

  private finishLogout(): void {
    localStorage.removeItem('paideia_access_token');
    localStorage.removeItem('paideia_user');
    void this.router.navigateByUrl('/login');
  }
}
