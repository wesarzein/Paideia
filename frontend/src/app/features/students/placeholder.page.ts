import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({ standalone: true, imports: [PageHeaderComponent], template: '<app-page-header title="Estudiantes" description="Base preparada para centralizar informacion academica." />' })
export class PlaceholderPage {}
