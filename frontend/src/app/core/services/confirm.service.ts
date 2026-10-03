import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ConfirmService {
  readonly prompt = signal<string | null>(null);
  private resolveCurrent: ((confirmed: boolean) => void) | null = null;

  ask(message: string): Promise<boolean> {
    if (this.resolveCurrent) {
      this.resolveCurrent(false);
    }
    this.prompt.set(message);
    return new Promise((resolve) => {
      this.resolveCurrent = resolve;
    });
  }

  answer(confirmed: boolean): void {
    this.resolveCurrent?.(confirmed);
    this.resolveCurrent = null;
    this.prompt.set(null);
  }
}
