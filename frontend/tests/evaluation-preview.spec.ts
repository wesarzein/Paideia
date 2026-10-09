import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { ApiService, EvaluationConfiguration } from '../src/app/core/services/api.service';
import { ConfirmService } from '../src/app/core/services/confirm.service';
import { EvaluationConfiguratorComponent } from '../src/app/features/courses/evaluation-configurator.component';

class Editor extends EvaluationConfiguratorComponent {
  previewExample(configuration: EvaluationConfiguration) {
    this.configuration = configuration;
    this.sampleScores = { active: 0, inactive: null };
    this.preview();
  }
}

describe('evaluation editor samples', () => {
  it('previews an explicit zero while omitting a deactivated criterion', () => {
    const previewEvaluation = vi.fn(() => of({ formula_results: {}, warnings: [], literal: null }));
    const injector = Injector.create({ providers: [
      { provide: ApiService, useValue: { previewEvaluation } },
      { provide: ConfirmService, useValue: {} },
    ] });
    const editor = runInInjectionContext(injector, () => new Editor());
    const configuration = {
      criteria: [{ key: 'active', is_active: true }, { key: 'inactive', is_active: false }],
    } as EvaluationConfiguration;
    editor.previewExample(configuration);
    expect(previewEvaluation).toHaveBeenCalledWith('', configuration, { active: 0 });
  });
});
