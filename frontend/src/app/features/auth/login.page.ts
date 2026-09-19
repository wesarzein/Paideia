import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { ApiService } from '../../core/services/api.service';

@Component({
  standalone: true,
  imports: [FormsModule],
  template: `
    <section class="login">
      <img class="logo" src="assets/logo.png" alt="Logo del colegio" />
      <h1>Paideia</h1>
      <p>Acceso institucional para el equipo académico del colegio.</p>
      <form (ngSubmit)="login()">
        <label>Email
          <input type="email" name="email" [(ngModel)]="email" required />
        </label>
        <label>Contraseña
          <input type="password" name="password" [(ngModel)]="password" required />
        </label>
        @if (error()) {
          <p class="error">{{ error() }}</p>
        }
        <button type="submit">Iniciar sesión</button>
      </form>
    </section>
  `,
  styles: [`
    .login { max-width: 420px; margin: 12vh auto; background: white; border: 1px solid var(--color-border); border-radius: 8px; padding: 28px; }
    h1 { margin-top: 0; }
    .logo { width: 78px; height: 78px; object-fit: contain; }
    form { display: grid; gap: 16px; }
    label { display: grid; gap: 8px; color: var(--color-muted-text); }
    input { border: 1px solid var(--color-border); border-radius: 6px; padding: 10px 12px; font: inherit; }
    button { background: var(--color-primary); border: 0; border-radius: 8px; color: white; padding: 10px 14px; cursor: pointer; }
    .error { color: #a33a32; margin: 0; }
  `],
})
export class LoginPage {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  protected email = 'admin@paideia.local';
  protected password = 'Admin123!';
  protected readonly error = signal('');

  protected login(): void {
    this.error.set('');
    this.api.login({ email: this.email, password: this.password }).subscribe({
      next: (response) => {
        localStorage.setItem('paideia_access_token', response.access_token);
        localStorage.setItem('paideia_user', JSON.stringify(response.user));
        void this.router.navigateByUrl('/dashboard');
      },
      error: () => this.error.set('Credenciales inválidas.'),
    });
  }
}
