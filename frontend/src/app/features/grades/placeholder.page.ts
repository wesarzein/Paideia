import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({ standalone: true, imports: [PageHeaderComponent], template: '<app-page-header title="Calificaciones" description="Base preparada para registro y analisis de notas." />' })
export class PlaceholderPage {}
