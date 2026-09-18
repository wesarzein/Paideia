import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  standalone: true,
  template: `
    <section class="login">
      <h1>Paideia</h1>
      <p>Acceso preparado para JWT y RBAC.</p>
      <button type="button" (click)="enterDemo()">Entrar a base inicial</button>
    </section>
  `,
  styles: [`
    .login { max-width: 420px; margin: 12vh auto; background: white; border: 1px solid var(--color-border); border-radius: 8px; padding: 28px; }
    h1 { margin-top: 0; }
    button { background: var(--color-primary); border: 0; border-radius: 8px; color: white; padding: 10px 14px; }
  `],
})
export class LoginPage {
  constructor(private readonly router: Router) {}

  enterDemo(): void {
    localStorage.setItem('paideia_access_token', 'demo-placeholder-token');
    void this.router.navigateByUrl('/dashboard');
  }
}
