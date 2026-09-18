import { Component, input } from '@angular/core';

@Component({ selector: 'app-kpi-card', standalone: true, template: '<article><span>{{ label() }}</span><strong>{{ value() }}</strong></article>', styles: ['article{background:white;border:1px solid var(--color-border);border-radius:8px;padding:16px} span{color:#52606d} strong{display:block;font-size:1.7rem;margin-top:8px}'] })
export class KpiCardComponent { label = input.required<string>(); value = input.required<string>(); }
