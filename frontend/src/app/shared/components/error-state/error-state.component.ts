import { Component, input } from '@angular/core';

@Component({ selector: 'app-error-state', standalone: true, template: '<p class="error">{{ message() }}</p>', styles: ['.error{color:#b42318}'] })
export class ErrorStateComponent { message = input('No se pudo cargar la informacion.'); }
