import '@angular/compiler';
import { Injector, runInInjectionContext } from '@angular/core';
import { of } from 'rxjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiService, EvaluationRevision } from '../src/app/core/services/api.service';
import { ConfirmService } from '../src/app/core/services/confirm.service';
import { EvaluationConfiguratorComponent } from '../src/app/features/courses/evaluation-configurator.component';

class Editor extends EvaluationConfiguratorComponent {
  open() { this.courseId = 'course'; this.periodId = 'period'; this.load(); }
  config() { return this.configuration; }
  publish() { this.reason = 'Competencias del curso'; this.save('published'); }
  competency() { this.addCompetency(); }
  configure() {
    this.competency();
    for (const item of this.configuration!.criteria) item.competency_key = this.configuration!.competencies[0].key;
    this.configuration!.criteria[0].weight = '3';
    this.configuration!.criteria[1].weight = '2';
  }
  errorText() { return this.error(); }
}

afterEach(() => vi.unstubAllGlobals());
function setup(role: string, state = 'default') {
  vi.stubGlobal('localStorage', { getItem: () => JSON.stringify({ role }) });
  const revision = { id: null, state, version: 0, configuration: { template_id:'institutional_v1',
    criteria:[1,2].flatMap(block => [0,1].map(position => ({ key:`b${block}_${position}`, name:'Criterio',
      block, position, weight:'1', is_active:true, is_optional:false, competency_key:null }))),
    competencies:[], formulas:[], final_formula:'pf' } } as unknown as EvaluationRevision;
  const current = vi.fn(() => of(revision)); const active = vi.fn(() => of(revision));
  const publish = vi.fn((_course: string, configuration: unknown) => of({ ...revision, configuration, version:1, state:'published' }));
  const injector = Injector.create({providers:[{provide:ApiService,useValue:{
    getEvaluationConfiguration:current, getActiveEvaluationConfiguration:active,
    listEvaluationVersions:() => of([]), publishEvaluation:publish,
  }}, {provide:ConfirmService,useValue:{}}]});
  const page = runInInjectionContext(injector, () => new Editor()); page.open();
  return {page,current,active,publish};
}

describe('course competencies', () => {
  it('publishes configured competencies with system generated weighted calculations', () => {
    const {page,publish} = setup('admin');
    expect(page.config()!.criteria).toHaveLength(2);
    page.publish(); expect(publish).not.toHaveBeenCalled(); expect(page.errorText()).toContain('competencia');
    page.configure(); page.publish();
    expect(publish).toHaveBeenCalledOnce();
    const payload = publish.mock.calls[0][1] as EvaluationRevision['configuration'];
    expect(payload.template_id).toBe('weighted_course_v1');
    expect(payload.formulas[0].expression).toContain('*3');
    expect(payload.formulas[1].expression).toContain('*2');
    expect(payload.criteria.every(item => !!item.competency_key)).toBe(true);
  });
  it('loads only the published configuration for a teacher and rejects writes', () => {
    const {page,current,active,publish} = setup('teacher','published');
    expect(active).toHaveBeenCalledOnce(); expect(current).not.toHaveBeenCalled();
    page.publish(); expect(publish).not.toHaveBeenCalled();
  });
  it('does not present a default template as published teacher competencies', () => {
    const {page} = setup('teacher'); expect(page.config()).toBeNull();
  });
});
