import { Component, Input, OnChanges, SimpleChanges, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
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
  imports: [DatePipe, FormsModule],
  template: `
    <section class="evaluation-editor">
      <div class="heading">
        <div>
          <h2>Evaluación configurable</h2>
          <p>Dos bloques de cuatro semanas. Los cambios se guardan como versiones.</p>
        </div>
        <label>Periodo
          <select [(ngModel)]="periodId" (ngModelChange)="load()">
            <option value="">Seleccionar periodo</option>
            @for (period of periods; track period.id) {
              <option [value]="period.id">{{ period.name }}</option>
            }
          </select>
        </label>
      </div>

      @if (error()) { <p class="feedback error" role="alert">{{ error() }}</p> }
      @if (message()) { <p class="feedback" role="status">{{ message() }}</p> }
      @if (configuration) {
        <p class="version">
          Versión {{ currentVersion }} ·
          {{ currentState === 'published' ? 'Publicada' : currentState === 'draft' ? 'Borrador' : 'Plantilla institucional' }}
        </p>

        <fieldset [disabled]="!canEdit || busy()">
          <legend>Competencias</legend>
          @for (competency of configuration.competencies; track competency.key; let index = $index) {
            <div class="editor-row">
              <input [(ngModel)]="competency.name" (ngModelChange)="markCustom()"
                     [name]="'competency-' + competency.key" aria-label="Nombre de competencia" />
              <label class="check"><input type="checkbox" [(ngModel)]="competency.is_active"
                (ngModelChange)="toggleCompetency(competency.key, competency.is_active)"
                [name]="'competency-active-' + competency.key" /> Activa</label>
              <button type="button" class="compact" (click)="moveCompetency(index, -1)" [disabled]="index === 0">↑</button>
              <button type="button" class="compact" (click)="moveCompetency(index, 1)" [disabled]="index === configuration.competencies.length - 1">↓</button>
            </div>
          }
          <button type="button" class="outline" (click)="addCompetency()">Agregar competencia</button>
        </fieldset>

        @for (block of blocks; track block) {
          <fieldset [disabled]="!canEdit || busy()">
            <legend>Mes {{ block }} · criterios</legend>
            @for (criterion of criteriaFor(block); track criterion.key; let index = $index) {
              <div class="criterion-row" [class.inactive]="!criterion.is_active">
                <input [(ngModel)]="criterion.name" (ngModelChange)="markCustom()"
                       [name]="'criterion-name-' + criterion.key" aria-label="Nombre del criterio" />
                <label>Peso<input type="number" min="0" max="100" step="0.1"
                  [(ngModel)]="criterion.weight" (ngModelChange)="markCustom()"
                  [name]="'criterion-weight-' + criterion.key" /></label>
                <label>Competencia<select [(ngModel)]="criterion.competency_key"
                  (ngModelChange)="markCustom()" [name]="'criterion-competency-' + criterion.key">
                  <option [ngValue]="null">Sin competencia</option>
                  @for (competency of activeCompetencies(); track competency.key) {
                    <option [value]="competency.key">{{ competency.name }}</option>
                  }
                </select></label>
                <label>Encabezado Excel<input [(ngModel)]="criterion.source_header"
                  (ngModelChange)="markCustom()" [name]="'criterion-header-' + criterion.key" /></label>
                <label class="check"><input type="checkbox" [(ngModel)]="criterion.is_optional"
                  (ngModelChange)="markCustom()" [name]="'criterion-optional-' + criterion.key" /> Opcional</label>
                <label class="check"><input type="checkbox" [(ngModel)]="criterion.is_active"
                  (ngModelChange)="markCustom()" [name]="'criterion-active-' + criterion.key" /> Activo</label>
                <div class="order">
                  <button type="button" class="compact" (click)="moveCriterion(block, index, -1)" [disabled]="index === 0">↑</button>
                  <button type="button" class="compact" (click)="moveCriterion(block, index, 1)" [disabled]="index === criteriaFor(block).length - 1">↓</button>
                </div>
              </div>
            }
            <button type="button" class="outline" (click)="addCriterion(block)">Agregar criterio</button>
          </fieldset>
        }

        <fieldset [disabled]="!canEdit || busy()">
          <legend>Fórmulas permitidas</legend>
          <p class="help">Operadores: +, −, ×, ÷. Funciones: SUM, MEAN, MIN, MAX y ROUND.</p>
          @for (formula of configuration.formulas; track formula.key) {
            <label class="formula">{{ formula.key }}
              <textarea rows="2" [(ngModel)]="formula.expression" (ngModelChange)="markCustom()"
                        [name]="'formula-' + formula.key"></textarea>
            </label>
          }
        </fieldset>

        <fieldset [disabled]="busy()">
          <legend>Vista previa con notas de ejemplo</legend>
          <div class="scores">
            @for (criterion of activeCriteria(); track criterion.key) {
              <label>{{ criterion.name }} · mes {{ criterion.block }}
                <input type="number" min="0" max="20" step="0.1"
                  [ngModel]="sampleScores[criterion.key]"
                  (ngModelChange)="setSampleScore(criterion.key, $event)"
                  [name]="'score-' + criterion.key" />
              </label>
            }
          </div>
          <button type="button" (click)="preview()">Previsualizar resultados</button>
          @if (previewResult()) {
            <div class="preview-result">
              @for (formula of formulaEntries(); track formula[0]) {
                <span>{{ formula[0] }}: {{ formula[1] ?? 'Incompleto' }}</span>
              }
              <strong>Literal: {{ previewResult()!.literal ?? 'Incompleto' }}</strong>
            </div>
            @if (previewResult()!.warnings.length) {
              <p class="warning">Faltan criterios obligatorios para completar el resultado.</p>
            }
          }
        </fieldset>

        @if (canEdit) {
          <div class="publication">
            <label>Motivo del cambio
              <input [(ngModel)]="reason" maxlength="500" placeholder="Describe el propósito de esta versión" />
            </label>
            <button type="button" (click)="save('draft')" [disabled]="busy() || !reason.trim()">Guardar borrador</button>
            <button type="button" (click)="save('published')" [disabled]="busy() || !reason.trim()">Publicar versión</button>
            <button type="button" class="outline" (click)="restoreInstitutional()" [disabled]="busy() || !reason.trim()">Restablecer plantilla institucional</button>
          </div>
        }

        <details>
          <summary>Historial de versiones ({{ versions().length }})</summary>
          <div class="history">
            @for (version of versions(); track version.id) {
              <button type="button" class="history-item" (click)="openVersion(version)">
                <strong>v{{ version.version }} · {{ version.state === 'published' ? 'Publicada' : 'Borrador' }}</strong>
                <span>{{ version.reason }}</span>
                <small>{{ version.created_at ? (version.created_at | date:'short') : '' }}</small>
              </button>
            }
          </div>
        </details>
      } @else if (periodId && !busy()) {
        <p>No se pudo cargar la configuración.</p>
      }
    </section>
  `,
  styles: [`
    .evaluation-editor{border-top:1px solid var(--color-border);margin-top:22px;padding-top:18px}.heading{display:flex;justify-content:space-between;gap:18px;align-items:end}.heading p,.help{color:var(--color-muted-text);margin:4px 0}.version{display:inline-block;background:var(--color-muted);border-radius:999px;padding:6px 10px}fieldset{border:1px solid var(--color-border);border-radius:8px;margin:16px 0;padding:14px}legend{font-weight:700}.editor-row,.criterion-row{display:grid;grid-template-columns:minmax(170px,2fr) repeat(3,minmax(100px,1fr)) auto auto auto;gap:10px;align-items:end;margin-bottom:10px}.editor-row{grid-template-columns:minmax(220px,1fr) auto auto auto}.criterion-row input,.criterion-row select,.editor-row input,.formula textarea,.publication input,.heading select,.scores input{width:100%;padding:9px;border:1px solid var(--color-border);border-radius:6px;background:var(--color-surface)}.check{display:flex;align-items:center;gap:6px}.check input{width:17px}.compact{margin:0;padding:8px 10px}.outline{background:transparent;color:var(--color-primary);border:1px solid var(--color-primary)}.inactive{opacity:.6}.formula{display:grid;grid-template-columns:90px 1fr;gap:10px;align-items:center;margin:8px 0}.scores{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.preview-result{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px;padding:12px;background:var(--color-muted);border-radius:7px}.warning{color:#9a5b00}.publication{display:grid;grid-template-columns:minmax(240px,1fr) repeat(3,auto);gap:8px;align-items:end}.history{display:grid;gap:8px;margin-top:10px}.history-item{display:grid;grid-template-columns:140px 1fr auto;gap:10px;text-align:left;margin:0;background:var(--color-muted);color:var(--color-text)}@media(max-width:900px){.criterion-row,.publication{grid-template-columns:1fr 1fr}.heading{align-items:stretch;flex-direction:column}}@media(max-width:600px){.criterion-row,.publication,.editor-row,.formula,.history-item{grid-template-columns:1fr}}
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
      return ['admin', 'teacher', 'coordinator'].includes(
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
    this.api.getEvaluationConfiguration(this.courseId, this.periodId).subscribe({
      next: (revision) => {
        this.applyRevision(revision, true);
        this.loadVersions();
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
    if (this.configuration) this.configuration.template_id = 'custom_v1';
    this.previewResult.set(null);
  }

  protected setSampleScore(key: string, value: number | string | null): void {
    this.sampleScores[key] = value === '' || value === null ? null : Number(value);
    this.previewResult.set(null);
  }

  protected preview(): void {
    if (!this.configuration) return;
    this.busy.set(true);
    this.error.set('');
    this.api.previewEvaluation(this.courseId, this.configuration, this.sampleScores).subscribe({
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
    if (!this.configuration || !this.reason.trim()) return;
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
    return `${prefix}_${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`;
  }

  private errorDetail(error: { error?: { detail?: unknown } }, fallback: string): string {
    return typeof error.error?.detail === 'string' ? error.error.detail : fallback;
  }
}
