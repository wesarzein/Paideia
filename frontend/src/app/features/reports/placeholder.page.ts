import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({ standalone: true, imports: [PageHeaderComponent], template: '<app-page-header title="Reportes" description="Base preparada para reportes individuales y grupales." />' })
export class PlaceholderPage {}
