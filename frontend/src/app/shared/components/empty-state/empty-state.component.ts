import { Component, input } from '@angular/core';

@Component({ selector: 'app-empty-state', standalone: true, template: '<p>{{ message() }}</p>' })
export class EmptyStateComponent { message = input('Sin informacion para mostrar.'); }
