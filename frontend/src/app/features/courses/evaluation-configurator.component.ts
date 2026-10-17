import { Component, Input, OnChanges, SimpleChanges, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  ApiService,
  EvaluationConfiguration,
  EvaluationCriterion,
  EvaluationPreview,
  EvaluationRevision,
} from '../../core/services/api.service';
import { ConfirmService } from '../../core/services/confirm.service';

type PeriodOption = { id: string; name: string };

@Component({
  selector: 'app-evaluation-configurator',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './evaluation-configurator.component.html',
  styles: [`
    label{display:grid;gap:6px;color:var(--color-muted-text);font-size:.88rem}button{padding:10px 14px;border:1px solid var(--color-primary);border-radius:7px;background:var(--color-primary);color:white;cursor:pointer;margin:8px 8px 0 0}button:hover:not(:disabled){background:var(--color-primary-dark)}.outline:hover:not(:disabled){background:var(--color-primary-soft)}.feedback{padding:12px 16px;border:1px solid var(--color-border);border-radius:7px;background:var(--color-primary-soft)}.error{color:#a33a32}details{margin-top:16px}h2{font-size:1.15rem;margin-top:0}

    .competency-card{border:1px solid var(--color-border);border-radius:10px;padding:14px;margin:12px 0}.competency-card h3{margin:0 0 12px}.competency-card p{display:flex;justify-content:space-between;gap:12px}.competency-card span{color:var(--color-muted-text)}.editor-row select{padding:9px;border:1px solid var(--color-border);border-radius:6px}.evaluation-editor{border-top:1px solid var(--color-border);margin-top:22px;padding-top:18px}.heading{display:flex;justify-content:space-between;gap:18px;align-items:end}.heading p,.help{color:var(--color-muted-text);margin:4px 0}.version{display:inline-block;background:var(--color-muted);border-radius:999px;padding:6px 10px}fieldset{border:1px solid var(--color-border);border-radius:8px;margin:16px 0;padding:14px}legend{font-weight:700}.editor-row,.criterion-row{display:grid;grid-template-columns:minmax(170px,2fr) minmax(170px,2fr) repeat(3,minmax(95px,1fr));gap:10px;align-items:end;margin-bottom:10px}.editor-row{grid-template-columns:minmax(220px,1fr) auto auto auto}.criterion-row input,.criterion-row select,.editor-row input,.formula textarea,.publication input,.heading select,.scores input{width:100%;padding:9px;border:1px solid var(--color-border);border-radius:6px;background:var(--color-surface)}.check{display:flex;align-items:center;gap:6px}.check input{width:17px}.compact{margin:0;padding:8px 10px}.outline{background:transparent;color:var(--color-primary);border:1px solid var(--color-primary)}.inactive{opacity:.6}.formula{display:grid;grid-template-columns:90px 1fr;gap:10px;align-items:center;margin:8px 0}.scores{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.preview-result{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px;padding:12px;background:var(--color-muted);border-radius:7px}.warning{color:#9a5b00}.publication{display:grid;grid-template-columns:minmax(240px,1fr) repeat(2,auto);gap:8px;align-items:end}.history{display:grid;gap:8px;margin-top:10px}.history-item{display:grid;grid-template-columns:140px 1fr auto;gap:10px;text-align:left;margin:0;background:var(--color-muted);color:var(--color-text)}@media(max-width:900px){.criterion-row,.publication{grid-template-columns:1fr 1fr}.heading{align-items:stretch;flex-direction:column}}@media(max-width:600px){.criterion-row,.publication,.editor-row,.formula,.history-item{grid-template-columns:1fr}}
  `],
})
export class EvaluationConfiguratorComponent implements OnChanges {
  @Input({ required: true }) courseId = '';
  @Input() periods: PeriodOption[] = [];

  private readonly api = inject(ApiService);
  private readonly confirm = inject(ConfirmService);
  protected readonly blocks = [1, 2] as const;
  protected readonly versions = signal<EvaluationRevision[]>([]);
  protected readonly previewResult = signal<EvaluationPreview | null>(null);
  protected readonly busy = signal(false);
  protected readonly error = signal('');
  protected readonly message = signal('');
  protected periodId = '';
  protected configuration: EvaluationConfiguration | null = null;
  protected currentVersion = 0;
  protected currentState: EvaluationRevision['state'] = 'default';
  protected sampleScores: Record<string, number | null> = {};
  protected reason = '';
  protected readonly canEdit = (() => {
    try {
      return ['teacher'].includes(
        JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role,
      );
    } catch {
      return false;
    }
  })();

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['courseId']) {
      this.periodId = this.periods[0]?.id ?? '';
      this.periodId ? this.load() : this.clear();
    } else if (!this.periodId && this.periods.length) {
      this.periodId = this.periods[0].id;
      this.load();
    }
  }

  protected load(): void {
    if (!this.courseId || !this.periodId) return this.clear();
    this.busy.set(true);
    this.error.set('');
    const request = this.canEdit ? this.api.getEvaluationConfiguration(this.courseId, this.periodId) : this.api.getActiveEvaluationConfiguration(this.courseId, this.periodId);
    request.subscribe({
      next: (revision) => {
        if (revision && (this.canEdit || revision.state === "published")) { this.applyRevision(revision, true); if (this.canEdit) this.loadVersions(); } else this.clear();
        this.busy.set(false);
      },
      error: (error) => {
        this.error.set(this.errorDetail(error, 'No se pudo cargar la configuración.'));
        this.busy.set(false);
      },
    });
  }

  protected criteriaFor(block: 1 | 2): EvaluationCriterion[] {
    return (this.configuration?.criteria ?? [])
      .filter((criterion) => criterion.block === block)
      .sort((left, right) => left.position - right.position);
  }

  protected activeCriteria(): EvaluationCriterion[] {
    return (this.configuration?.criteria ?? []).filter((criterion) => criterion.is_active);
  }

  protected activeCompetencies() {
    return (this.configuration?.competencies ?? []).filter((item) => item.is_active);
  }

  protected formulaEntries(): [string, number | null][] {
    return Object.entries(this.previewResult()?.formula_results ?? {});
  }

  protected addCompetency(): void {
    if (!this.configuration) return;
    this.configuration.competencies.push({
      key: this.newKey('competency'),
      name: 'Nueva competencia',
      position: this.configuration.competencies.length,
      is_active: true,
    });
    this.markCustom();
  }

  protected moveCompetency(index: number, direction: number): void {
    if (!this.configuration) return;
    const target = index + direction;
    if (target < 0 || target >= this.configuration.competencies.length) return;
    [this.configuration.competencies[index], this.configuration.competencies[target]] =
      [this.configuration.competencies[target], this.configuration.competencies[index]];
    this.configuration.competencies.forEach((item, position) => item.position = position);
    this.markCustom();
  }

  protected toggleCompetency(key: string, active: boolean): void {
    if (!this.configuration) return;
    if (!active) {
      this.configuration.criteria
        .filter((criterion) => criterion.competency_key === key)
        .forEach((criterion) => criterion.is_active = false);
    }
    this.markCustom();
  }

  protected addCriterion(block: 1 | 2): void {
    if (!this.configuration) return;
    const blockCriteria = this.criteriaFor(block);
    const key = this.newKey(`b${block}_criterion`);
    this.configuration.criteria.push({
      key,
      name: 'Nuevo criterio',
      block,
      position: blockCriteria.length,
      weight: '1',
      competency_key: null,
      is_active: true,
      is_optional: false,
      source_header: null,
      legacy_component_id: null,
    });
    this.sampleScores[key] = null;
    this.markCustom();
  }

  protected moveCriterion(block: 1 | 2, index: number, direction: number): void {
    const criteria = this.criteriaFor(block);
    const target = index + direction;
    if (target < 0 || target >= criteria.length) return;
    const oldPosition = criteria[index].position;
    criteria[index].position = criteria[target].position;
    criteria[target].position = oldPosition;
    this.markCustom();
  }

  protected markCustom(): void {
    if (this.configuration && this.configuration.template_id !== 'weighted_course_v1') this.configuration.template_id = 'custom_v1';
    this.previewResult.set(null);
  }

  protected useWeightedCalculation(): void {
    if (!this.canEdit || !this.configuration) return;
    this.configuration.template_id = 'weighted_course_v1';
    this.syncWeightedFormulas();
    this.previewResult.set(null);
  }

  private syncWeightedFormulas(): void {
    if (this.configuration?.template_id !== 'weighted_course_v1') return;
    this.configuration.formulas = this.blocks.map(block => {
      const criteria = this.activeCriteria().filter(item => item.block === block && Number(item.weight) > 0);
      const denominator = criteria.reduce((sum, item) => sum + Number(item.weight), 0);
      return { key: `mes_${block}`, expression: denominator ? `SUM(${criteria.map(item => `${item.key}*${Number(item.weight)}`).join(',')})/${denominator}` : '0' };
    });
    this.configuration.formulas.push({ key: 'pf', expression: 'MEAN(mes_1,mes_2)' });
    this.configuration.final_formula = 'pf';
  }

  protected setSampleScore(key: string, value: number | string | null): void {
    this.sampleScores[key] = value === '' || value === null ? null : Number(value);
    this.previewResult.set(null);
  }

  protected preview(): void {
    if (!this.configuration) return;
    this.busy.set(true);
    this.error.set('');
    const activeScores = Object.fromEntries(
      this.activeCriteria().map((criterion) => [criterion.key, this.sampleScores[criterion.key] ?? null]),
    );
    this.api.previewEvaluation(this.courseId, this.configuration, activeScores).subscribe({
      next: (result) => {
        this.previewResult.set(result);
        this.busy.set(false);
      },
      error: (error) => {
        this.error.set(this.errorDetail(error, 'La configuración o las notas de ejemplo son inválidas.'));
        this.busy.set(false);
      },
    });
  }

  protected save(state: 'draft' | 'published'): void {
    if (!this.canEdit) return;
    if (!this.configuration || !this.reason.trim()) return;
    if (state === "published" && (!this.activeCompetencies().length || this.activeCriteria().some(item => !item.competency_key))) { this.error.set("Asigna una competencia a cada criterio activo antes de publicar."); return; }
    this.syncWeightedFormulas();
    this.busy.set(true);
    this.error.set('');
    const request = state === 'draft'
      ? this.api.saveEvaluationDraft(this.courseId, this.configuration, this.currentVersion, this.reason)
      : this.api.publishEvaluation(this.courseId, this.configuration, this.currentVersion, this.reason);
    request.subscribe({
      next: (revision) => {
        this.applyRevision(revision, true);
        this.reason = '';
        this.message.set(state === 'draft' ? 'Borrador guardado.' : 'Configuración publicada.');
        this.loadVersions();
        this.busy.set(false);
      },
      error: (error) => {
        this.error.set(this.errorDetail(error, 'No se pudo guardar la versión.'));
        this.busy.set(false);
      },
    });
  }

  protected async restoreInstitutional(): Promise<void> {
    if (!this.canEdit) return;
    if (!this.reason.trim()) return;
    if (!await this.confirm.ask('¿Publicar la plantilla institucional como una nueva versión?')) return;
    this.busy.set(true);
    this.api.restoreInstitutionalEvaluation(
      this.courseId, this.periodId, this.currentVersion, this.reason,
    ).subscribe({
      next: (revision) => {
        this.applyRevision(revision, true);
        this.reason = '';
        this.message.set('Plantilla institucional restablecida en una nueva versión.');
        this.loadVersions();
        this.busy.set(false);
      },
      error: (error) => {
        this.error.set(this.errorDetail(error, 'No se pudo restablecer la plantilla.'));
        this.busy.set(false);
      },
    });
  }

  protected openVersion(revision: EvaluationRevision): void {
    this.configuration = structuredClone(revision.configuration);
    if (this.canEdit && revision.version === 0) {
      if (this.configuration.template_id === 'institutional_v1') {
        this.configuration.criteria = this.blocks.map(block => ({
          ...this.configuration!.criteria.find(item => item.block === block)!,
          name: 'Criterio de evaluación', source_header: null, weight: '1',
        }));
      }
      this.useWeightedCalculation();
    }
    this.sampleScores = Object.fromEntries(
      this.configuration.criteria.map((criterion) => [criterion.key, null]),
    );
    this.previewResult.set(null);
    this.message.set(`Versión ${revision.version} cargada para revisión. Al guardar se creará una versión nueva.`);
  }

  private loadVersions(): void {
    this.api.listEvaluationVersions(this.courseId, this.periodId).subscribe({
      next: (versions) => this.versions.set(versions),
      error: () => this.error.set('La configuración se cargó, pero no se pudo consultar el historial.'),
    });
  }

  private applyRevision(revision: EvaluationRevision, updateVersion: boolean): void {
    this.configuration = structuredClone(revision.configuration);
    if (this.canEdit && revision.version === 0) {
      if (this.configuration.template_id === 'institutional_v1') {
        this.configuration.criteria = this.blocks.map(block => ({
          ...this.configuration!.criteria.find(item => item.block === block)!,
          name: 'Criterio de evaluación', source_header: null, weight: '1',
        }));
      }
      this.useWeightedCalculation();
    }
    if (updateVersion) {
      this.currentVersion = revision.version;
      this.currentState = revision.state;
    }
    this.sampleScores = Object.fromEntries(
      this.configuration.criteria.map((criterion) => [criterion.key, null]),
    );
    this.previewResult.set(null);
  }

  private clear(): void {
    this.configuration = null;
    this.versions.set([]);
    this.previewResult.set(null);
  }

  private newKey(prefix: string): string {
    return `${prefix}_${Array.from(crypto.getRandomValues(new Uint32Array(2)), value => value.toString(16).padStart(8, '0')).join('')}`;
  }

  private errorDetail(error: { error?: { detail?: unknown } }, fallback: string): string {
    return typeof error.error?.detail === 'string' ? error.error.detail : fallback;
  }
}
