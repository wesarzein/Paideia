import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ConfirmService } from './core/services/confirm.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <router-outlet />
    @if (confirm.prompt(); as prompt) {
      <div class="confirm-backdrop" (click)="confirm.answer(false)">
        <section class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title" (click)="$event.stopPropagation()">
          <h2 id="confirm-title">Confirmar acción</h2>
          <p>{{ prompt }}</p>
          <div class="confirm-actions">
            <button type="button" class="secondary" (click)="confirm.answer(false)">Cancelar</button>
            <button type="button" class="primary" (click)="confirm.answer(true)">Confirmar</button>
          </div>
        </section>
      </div>
    }
  `,
  styles: [`
    .confirm-backdrop{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:20px;background:#0f172a66}
    .confirm-dialog{width:min(100%,440px);padding:24px;border:1px solid var(--color-border);border-radius:12px;background:var(--color-surface);box-shadow:0 20px 60px #0f172a33}
    .confirm-dialog h2{margin:0 0 10px;font-size:1.1rem}.confirm-dialog p{color:var(--color-muted-text);line-height:1.5}
    .confirm-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:22px}
    .confirm-actions button{padding:9px 14px;border:1px solid var(--color-border);border-radius:7px;background:var(--color-surface);color:var(--color-text);font:inherit;cursor:pointer}
    .confirm-actions .primary{border-color:var(--color-primary);background:var(--color-primary);color:#fff}
  `],
})
export class AppComponent {
  protected readonly confirm = inject(ConfirmService);
}
