import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({ standalone: true, imports: [PageHeaderComponent], template: '<app-page-header [title]="title" description="Estructura preparada para cursos, grados, secciones y evaluaciones." />' })
export class PlaceholderPage {
	private readonly route = inject(ActivatedRoute);
	title = this.route.snapshot.data['title'] ?? 'Gestion academica';
}
