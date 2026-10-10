import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { CohortManagerComponent } from './cohort-manager.component';

@Component({
  standalone: true,
  imports: [PageHeaderComponent, CohortManagerComponent],
  template: `
    <app-page-header title="Grados y secciones" [description]="isAdmin ? 'Crea grados de Primaria o Secundaria y agrega las secciones de cada grado.' : 'Consulta los grados y secciones disponibles para tus cursos asignados.'" />
    @if (isAdmin) { <p>Primero crea el grado y selecciona su nivel. Luego crea sus secciones y asigna el curso a la cuenta del docente desde Cursos.</p> }
    <app-cohort-manager [expanded]="true" [canManage]="isAdmin" />
  `,
})
export class CohortsPage {
  protected readonly isAdmin = (() => { try { return JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role === 'admin'; } catch { return false; } })();
}
