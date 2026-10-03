import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';
import { AcademicCatalog, ApiService, AttendanceRecord, GradeRecord, Student } from '../../core/services/api.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

type StudentRecords = {
  student: Student;
  catalog: AcademicCatalog;
  grades: GradeRecord[];
  attendance: AttendanceRecord[];
};

@Component({
  standalone: true,
  imports: [DatePipe, DecimalPipe, PageHeaderComponent],
  template: `
    <app-page-header [title]="isParent ? 'Avance de mis estudiantes' : 'Mi avance académico'" description="Consulta personal y segura de calificaciones y asistencia." />
    @if (loading()) { <p class="panel" role="status">Cargando registros académicos...</p> }
    @else if (error()) { <p class="panel error" role="alert">No se pudieron cargar tus registros. Intenta de nuevo.</p> }
    @else if (!records().length) {
      <section class="panel empty"><h2>Aún no hay estudiantes vinculados</h2><p>Solicita al administrador que asocie esta cuenta con tu ficha escolar.</p></section>
    } @else {
      @for (record of records(); track record.student.id) {
        <article class="student-card">
          <header>
            <div><h2>{{ record.student.last_name }}, {{ record.student.first_name }}</h2><p>{{ record.student.student_code }} · {{ gradeLabel(record) }}</p></div>
            <span>{{ record.student.status === 'ACTIVE' ? 'Activo' : 'Inactivo' }}</span>
          </header>
          <section>
            <h3>Calificaciones</h3>
            @if (!record.grades.length) { <p class="empty-row">Aún no hay calificaciones registradas.</p> }
            @else {
              <div class="table-wrap"><table><thead><tr><th>Curso</th><th>Evaluación</th><th>Periodo</th><th>Fecha</th><th>Nota</th><th>Observación</th></tr></thead><tbody>
                @for (grade of record.grades; track grade.id) {
                  <tr><td>{{ courseName(record, grade.course_id) }}</td><td>{{ grade.evaluation_name }} · {{ grade.evaluation_type }}</td><td>{{ periodName(record, grade.period_id) }}</td><td>{{ grade.assessment_date | date:'dd/MM/yyyy' }}</td><td>{{ grade.score | number:'1.0-2' }}/20</td><td>{{ grade.qualitative_note || '—' }}</td></tr>
                }
              </tbody></table></div>
            }
          </section>
          <section>
            <h3>Asistencia</h3>
            @if (!record.attendance.length) { <p class="empty-row">Aún no hay asistencias registradas.</p> }
            @else {
              <div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Curso</th><th>Estado</th><th>Observación</th></tr></thead><tbody>
                @for (attendance of record.attendance; track attendance.id) {
                  <tr><td>{{ attendance.attendance_date | date:'dd/MM/yyyy' }}</td><td>{{ courseName(record, attendance.course_id) }}</td><td>{{ attendanceStatus(attendance.status) }}</td><td>{{ attendance.remarks || '—' }}</td></tr>
                }
              </tbody></table></div>
            }
          </section>
        </article>
      }
    }
  `,
  styles: [`
    .panel,.student-card{background:var(--color-surface);border:1px solid var(--color-border);border-radius:10px;padding:20px;margin-bottom:16px}
    .student-card header{display:flex;justify-content:space-between;align-items:start;gap:12px;padding-bottom:14px;border-bottom:1px solid var(--color-border)}
    h2{margin:0 0 5px;font-size:1.1rem}h3{margin:18px 0 10px;font-size:.96rem}header p,.empty-row,.empty p{color:var(--color-muted-text);margin:0}
    header span{padding:5px 9px;border-radius:999px;background:var(--color-muted);color:var(--color-muted-text);font-size:.8rem}
    .table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:10px 12px;border-bottom:1px solid var(--color-border);text-align:left;white-space:nowrap}
    th{font-size:.78rem;color:var(--color-muted-text);font-weight:600}.error{color:#a33a32}.empty{padding:30px}
    @media(max-width:600px){.student-card{padding:14px}th,td{padding:8px}}
  `],
})
export class MyAcademicPage {
  private readonly api = inject(ApiService);
  protected readonly records = signal<StudentRecords[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal(false);
  protected readonly isParent = this.readRole() === 'parent';

  constructor() {
    this.api.getStudents().subscribe({
      next: (students) => this.loadRecords(students),
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }

  private loadRecords(students: Student[]): void {
    if (!students.length) { this.records.set([]); this.loading.set(false); return; }
    const requests = students.map((student) => {
      const filters = { grade_id: student.grade_id ?? '', section_id: student.section_id ?? '' };
      return forkJoin({
        catalog: this.api.getAcademicCatalog(filters),
        grades: this.api.listGrades({ student_id: student.id }),
        attendance: this.api.listAttendance({ student_id: student.id }),
      });
    });
    forkJoin(requests).subscribe({
      next: (results) => this.records.set(results.map((result, index) => ({ student: students[index], ...result }))),
      error: () => { this.error.set(true); this.loading.set(false); },
      complete: () => this.loading.set(false),
    });
  }

  protected courseName(record: StudentRecords, courseId: string): string {
    return record.catalog.courses.find((course) => course.id === courseId)?.name ?? 'Curso';
  }

  protected periodName(record: StudentRecords, periodId: string): string {
    return record.catalog.periods.find((period) => period.id === periodId)?.name ?? 'Periodo';
  }

  protected gradeLabel(record: StudentRecords): string {
    const grade = record.catalog.grades.find((item) => item.id === record.student.grade_id);
    const section = record.catalog.sections.find((item) => item.id === record.student.section_id);
    return [grade?.level, grade?.name, section?.name ? `Sección ${section.name}` : ''].filter(Boolean).join(' · ');
  }

  protected attendanceStatus(status: string): string {
    return ({ PRESENT: 'Presente', ABSENT: 'Falta', LATE: 'Tardanza' } as Record<string, string>)[status.toUpperCase()] ?? status;
  }

  private readRole(): string {
    try { return JSON.parse(localStorage.getItem('paideia_user') ?? '{}').role ?? ''; } catch { return ''; }
  }
}
