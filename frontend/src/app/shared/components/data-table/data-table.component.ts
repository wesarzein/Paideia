import { Component, input } from '@angular/core';

@Component({ selector: 'app-data-table', standalone: true, template: '<div class="table-shell"><ng-content /></div>', styles: ['.table-shell{overflow:auto;border:1px solid var(--color-border);border-radius:8px;background:white}'] })
export class DataTableComponent { caption = input('Tabla de datos'); }
