import { Component } from '@angular/core';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({ standalone: true, imports: [PageHeaderComponent], template: '<app-page-header title="Usuarios" description="Base preparada para usuarios, roles y accesos." />' })
export class PlaceholderPage {}
