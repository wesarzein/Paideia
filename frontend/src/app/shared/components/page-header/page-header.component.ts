import { Component, input } from '@angular/core';

@Component({
  selector: 'app-page-header',
  standalone: true,
  template: '<header><h1>{{ title() }}</h1><p>{{ description() }}</p></header>',
  styles: ['header{margin-bottom:22px} h1{margin:0 0 6px;font-size:1.8rem} p{margin:0;color:#52606d}'],
})
export class PageHeaderComponent {
  title = input.required<string>();
  description = input<string>('');
}
