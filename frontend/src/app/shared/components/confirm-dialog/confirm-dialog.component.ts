import { Component, input } from '@angular/core';

@Component({ selector: 'app-confirm-dialog', standalone: true, template: '<section><strong>{{ title() }}</strong><p>{{ message() }}</p></section>' })
export class ConfirmDialogComponent { title = input('Confirmar'); message = input('Esta accion requiere confirmacion.'); }
