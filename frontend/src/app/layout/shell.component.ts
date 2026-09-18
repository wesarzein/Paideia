import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

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
  imports: [RouterLink, RouterLinkActive],
  template: `
    <aside>
      <strong>Paideia</strong>
      <nav>
        @for (link of links; track link[1]) {
          <a [routerLink]="link[1]" routerLinkActive="active">{{ link[0] }}</a>
        }
      </nav>
    </aside>
    <main><ng-content /></main>
  `,
  styles: [`
    :host { display: grid; grid-template-columns: 260px 1fr; min-height: 100vh; }
    aside { background: #102a43; color: white; padding: 24px 18px; }
    strong { display: block; font-size: 1.35rem; margin-bottom: 22px; }
    nav { display: grid; gap: 4px; }
    a { border-radius: 8px; color: #d9e2ec; padding: 10px 12px; }
    a.active, a:hover { background: #1f4e79; color: white; }
    main { padding: 28px; min-width: 0; }
    @media (max-width: 820px) { :host { grid-template-columns: 1fr; } aside { position: static; } nav { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); } }
  `],
})
export class ShellComponent {
  protected readonly links = links;
}
