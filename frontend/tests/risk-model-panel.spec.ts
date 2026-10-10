import '@angular/compiler';
import { DestroyRef, Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { RiskModelPage } from '../src/app/features/ai/risk-model.page';
import { ModelStatus, RiskModelService } from '../src/app/features/ai/risk-model.service';

class Page extends RiskModelPage {
  acknowledge() { this.ack = true; this.reason = 'Synthetic experimental review'; }
  trainNow() { this.train(); }
  activateNow() { this.activate('model'); }
  failed() { return this.error(); }
  state() { return this.status(); }
}
function setup(role = 'admin') {
  vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ role }) });
  const state: ModelStatus = { mode: 'demonstration', institutional_status: 'inactive', active_run_id: null, deployment_version: 3, autorun: false, runs: [] };
  const status = vi.fn(() => of(state)); const train = vi.fn(() => of({})); const activate = vi.fn(() => of({}));
  const injector = Injector.create({ providers: [
    { provide: RiskModelService, useValue: { status, train, activate } },
    { provide: DestroyRef, useValue: { onDestroy: () => {} } },
  ] });
  return { page: runInInjectionContext(injector, () => new Page()), status, train, activate };
}
afterEach(() => vi.unstubAllGlobals());
describe('experimental model panel', () => {
  it('requires explicit synthetic acknowledgement to request training', () => {
    const { page, train } = setup(); page.trainNow(); expect(train).not.toHaveBeenCalled();
    page.acknowledge(); page.trainNow(); expect(train).toHaveBeenCalledWith(42, 80, 10.4);
  });
  it('does not offer training or activation to a teacher', () => {
    const { page, train, activate } = setup('teacher'); page.acknowledge(); page.trainNow(); page.activateNow();
    expect(train).not.toHaveBeenCalled(); expect(activate).not.toHaveBeenCalled();
  });
  it('sends the observed deployment version and keeps failed requests visible', () => {
    const { page, activate } = setup(); page.acknowledge();
    activate.mockReturnValueOnce(throwError(() => ({ error: { detail: 'Recarga versión' } })));
    page.activateNow(); expect(activate).toHaveBeenCalledWith('model', 3, 'Synthetic experimental review');
    expect(page.failed()).toBe('Recarga versión');
  });
  it('does not fabricate model availability when the status endpoint fails', () => {
    const { page, status } = setup();
    expect(page.state()?.active_run_id).toBeNull();
    status.mockReturnValueOnce(throwError(() => ({})));
    (page as unknown as { load(): void }).load(); expect(page.failed()).toContain('No se pudo');
  });
});
