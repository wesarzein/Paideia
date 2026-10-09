import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { ApiService, AuthUser } from '../src/app/core/services/api.service';
import { ConfirmService } from '../src/app/core/services/confirm.service';
import { UsersPage } from '../src/app/features/users/users.page';

class Accounts extends UsersPage {
  changeStatus(user: AuthUser) { return this.toggleStatus(user); }
  errorMessage() { return this.error(); }
}

function setup(confirmed = true, fail = false) {
  const updateUser = vi.fn(() => fail
    ? throwError(() => ({ error: { detail: 'Debe conservarse un administrador activo' } }))
    : of({}));
  const injector = Injector.create({ providers: [
    { provide: ApiService, useValue: {
      updateUser, listUsers: () => of([]), getStudents: () => of([]),
      getAcademicCatalog: () => of({ grades: [], sections: [], courses: [], periods: [], students: [], literal_scale: [] }),
    } },
    { provide: ConfirmService, useValue: { ask: async () => confirmed } },
  ] });
  return { page: runInInjectionContext(injector, () => new Accounts()), updateUser };
}

describe('account status', () => {
  it.each([true, false])('changes status %s using PATCH without changing links', async (active) => {
    const { page, updateUser } = setup();
    await page.changeStatus({ id: 'synthetic', is_active: active } as AuthUser);
    expect(updateUser).toHaveBeenCalledWith('synthetic', { is_active: !active });
  });

  it('leaves the account untouched if confirmation is cancelled', async () => {
    const { page, updateUser } = setup(false);
    await page.changeStatus({ id: 'synthetic', is_active: true } as AuthUser);
    expect(updateUser).not.toHaveBeenCalled();
  });

  it('shows the actionable API rejection', async () => {
    const { page } = setup(true, true);
    await page.changeStatus({ id: 'synthetic', is_active: true } as AuthUser);
    expect(page.errorMessage()).toBe('Debe conservarse un administrador activo');
  });
});
