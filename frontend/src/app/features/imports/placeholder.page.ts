import { Component, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  standalone: true,
  imports: [PageHeaderComponent],
  template: `<app-page-header title="Importación" description="Carga estudiantes desde CSV o Excel, revisa errores y valida antes de guardar." /><section class="dropzone" (dragover)="$event.preventDefault()" (drop)="drop($event)"><img src="assets/logo.png" alt="" /><strong>Arrastra tu archivo aquí</strong><span>o selecciónalo desde tu equipo</span><input type="file" accept=".csv,.xlsx,.xls" (change)="select($event)" /></section>@if (preview()) {<section class="panel"><h2>Vista previa: {{ preview()!.total }} filas</h2>@if (preview()!.errors.length) {<p class="error">{{ preview()!.errors.length }} errores encontrados. Corrige el archivo antes de continuar.</p>}<table><thead><tr>@for (column of preview()!.columns; track column) {<th>{{ column }}</th>}</tr></thead><tbody>@for (row of preview()!.rows; track $index) {<tr>@for (column of preview()!.columns; track column) {<td>{{ row[column] }}</td>}</tr>}</tbody></table></section>}`,
  styles: [` .dropzone, .panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 28px; margin-bottom: 18px; } .dropzone { display: grid; justify-items: center; gap: 8px; border: 2px dashed var(--color-accent); } .dropzone img { width: 55px; height: 55px; object-fit: contain; } .dropzone span { color: var(--color-muted-text); } input { margin-top: 10px; } .panel { overflow-x: auto; } table { width: 100%; border-collapse: collapse; } th, td { padding: 10px; border-bottom: 1px solid var(--color-border); text-align: left; white-space: nowrap; } .error { color: #a33a32; } `],
})
export class PlaceholderPage {
  private readonly api = inject(ApiService);
  protected readonly preview = signal<{ columns: string[]; rows: Record<string, unknown>[]; total: number; errors: { row: number; error: string }[] } | null>(null);
  protected select(event: Event): void { const file = (event.target as HTMLInputElement).files?.[0]; if (file) this.previewFile(file); }
  protected drop(event: DragEvent): void { event.preventDefault(); const file = event.dataTransfer?.files[0]; if (file) this.previewFile(file); }
  private previewFile(file: File): void { this.api.previewStudentImport(file).subscribe({ next: (result) => this.preview.set(result), error: () => this.preview.set({ columns: [], rows: [], total: 0, errors: [{ row: 0, error: 'No se pudo procesar el archivo' }] }) }); }
}
