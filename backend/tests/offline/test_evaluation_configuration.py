import json
import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from uuid import uuid4

from app.services.evaluation_configuration import (
    Competency,
    Criterion,
    Formula,
    from_document,
    from_legacy_components,
    institutional_template,
    next_revision,
    preview,
    reorder_criteria,
    source_criterion,
)


class EvaluationConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config = institutional_template(str(uuid4()), str(uuid4()))
        self.scores = dict(zip([c.key for c in self.config.criteria],
                               [10, 12, 14, 16, 18, 20, 20, 20, 20, 20]))
        self.actor = str(uuid4())

    def test_template_repeated_criteria_and_inspected_formulas(self):
        self.assertEqual(len(self.config.criteria), 10)
        self.assertEqual(self.config.competencies, ())  # No invented institutional names.
        result = preview(self.config, self.scores)
        self.assertEqual(result['formula_results'], {'mes_1': 14, 'mes_2': 20, 'pf': 17})
        self.assertEqual(result['literal'], 'AD')

    def test_blank_zero_and_missing_required(self):
        result = preview(self.config, {})
        self.assertIsNone(result['literal'])
        self.assertIsNone(result['formula_results']['pf'])
        self.assertTrue(result['warnings'])
        result = preview(self.config, {key: 0 for key in self.scores})
        self.assertEqual(result['formula_results']['pf'], 0)
        self.assertEqual(result['literal'], 'C')

    def test_relative_weights_do_not_require_sum_100(self):
        criteria = tuple(replace(c, weight=4) if c.key == 'b1_cuaderno' else c
                         for c in self.config.criteria)
        custom = replace(self.config, criteria=criteria, template_id='custom_v1')
        self.assertEqual(preview(custom, self.scores)['weighted_blocks']['1'], 13.25)
        self.assertEqual(preview(self.config, self.scores)['weighted_blocks']['1'], 14)

    def test_invalid_weights_and_zero_denominator(self):
        for weight in [-1, 101, True, 'NaN', '1e-99999999']:
            with self.subTest(weight=str(weight)), self.assertRaises(ValueError):
                Criterion('key', 'Criterio', 1, 0, weight=weight)
        with self.assertRaises(ValueError):
            replace(self.config, criteria=tuple(replace(c, weight=0) for c in self.config.criteria))

    def test_competencies_add_edit_order_and_deactivation(self):
        competencies = (Competency('c1', 'Competencia sintética', 0),)
        linked = tuple(replace(c, competency_key='c1') for c in self.config.criteria)
        config = replace(self.config, competencies=competencies, criteria=linked)
        self.assertEqual(config.criteria[0].competency_key, 'c1')
        updated = replace(config, competencies=(replace(competencies[0], name='Nueva etiqueta'),))
        self.assertEqual(config.competencies[0].name, 'Competencia sintética')
        self.assertEqual(updated.competencies[0].name, 'Nueva etiqueta')
        with self.assertRaises(ValueError):
            replace(config, competencies=(replace(competencies[0], is_active=False),))
        with self.assertRaises(ValueError):
            replace(config, competencies=())

    def test_reordering_retains_stable_identifiers(self):
        keys = [c.key for c in self.config.criteria if c.block == 1][::-1]
        updated = reorder_criteria(self.config, 1, keys)
        self.assertEqual([c.key for c in sorted((c for c in updated.criteria if c.block == 1),
                                              key=lambda c: c.position)], keys)
        self.assertEqual(preview(updated, self.scores)['formula_results'],
                         preview(self.config, self.scores)['formula_results'])
        with self.assertRaises(ValueError):
            reorder_criteria(self.config, 1, keys[:-1])

    def test_logical_deactivation_requires_explicit_formula_adjustment(self):
        key = self.config.criteria[0].key
        criteria = tuple(replace(c, is_active=False) if c.key == key else c
                         for c in self.config.criteria)
        with self.assertRaises(ValueError):
            replace(self.config, criteria=criteria)  # Formula still references inactive input.
        expression = 'ROUND(SUM(b1_cuaderno,b1_modulo,b1_exposicion,b1_evaluacion)/4,1)'
        formulas = tuple(Formula(f.key, expression) if f.key == 'mes_1' else f
                         for f in self.config.formulas)
        updated = replace(self.config, criteria=criteria, formulas=formulas)
        self.assertFalse(updated.criteria[0].is_active)
        self.assertEqual(len(updated.criteria), 10)

    def test_roundtrip_independent_documents(self):
        document = json.loads(self.config.canonical())
        restored = from_document(document)
        self.assertEqual(restored.fingerprint(), self.config.fingerprint())
        document['criteria'][0]['name'] = 'Cambio externo'
        self.assertNotEqual(from_document(document).fingerprint(), self.config.fingerprint())
        with self.assertRaises(FrozenInstanceError):
            self.config.criteria[0].name = 'Cambio prohibido'

    def test_roundtrip_rejects_new_schema_and_fields(self):
        for change in [dict(schema_version=99), dict(unknown=True), dict(block_weeks=6)]:
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                from_document(dict(json.loads(self.config.canonical()), **change))

    def test_versions_preserve_old_configuration_and_preview(self):
        first = next_revision(self.config, self.actor, 'Configuración inicial')
        criteria = tuple(replace(c, weight=4) if c.key == 'b1_cuaderno' else c
                         for c in self.config.criteria)
        custom = replace(self.config, criteria=criteria, template_id='custom_v1')
        second = next_revision(custom, self.actor, 'Peso personalizado', first, first.id)
        self.assertEqual(second.number, 2)
        self.assertEqual(second.previous_id, first.id)
        first_preview = preview(first.configuration(), self.scores)
        second_preview = preview(second.configuration(), self.scores)
        self.assertEqual(first_preview['weighted_blocks']['1'], 14)
        self.assertEqual(second_preview['weighted_blocks']['1'], 13.25)
        same = next_revision(custom, self.actor, 'Mismo contenido', second, second.id)
        self.assertIs(same, second)
        reset = next_revision(self.config, self.actor, 'Restaurar plantilla', second, second.id)
        self.assertEqual(reset.number, 3)
        self.assertEqual(second.configuration().criteria[1].weight, Decimal(4))

    def test_stale_revision_and_cross_scope_rejected(self):
        first = next_revision(self.config, self.actor, 'Inicial')
        with self.assertRaises(ValueError):
            next_revision(self.config, self.actor, 'Sin revisar', first)
        for change in [dict(course_id=str(uuid4())), dict(period_id=str(uuid4()))]:
            with self.assertRaises(ValueError):
                candidate = replace(self.config, **change)
                next_revision(candidate, self.actor, 'Otro ámbito', first, first.id)
        with self.assertRaises(ValueError):
            replace(first, content=first.content.replace('Cuaderno', 'Alterado')).configuration()

    def test_cycle_unknown_reference_duplicate_id_and_bad_header(self):
        for formulas in [(Formula('pf', 'pf'),), (Formula('a', 'pf'), Formula('pf', 'a')),
                         (Formula('pf', 'missing'),)]:
            with self.assertRaises(ValueError):
                replace(self.config, formulas=formulas)
        with self.assertRaises(ValueError):
            replace(self.config, criteria=self.config.criteria + (self.config.criteria[0],))
        bad = list(self.config.criteria)
        bad[1] = replace(bad[1], source_header=bad[0].source_header.lower())
        with self.assertRaises(ValueError):
            replace(self.config, criteria=tuple(bad))

    def test_score_scale_and_bool_validation(self):
        for value in [True, -1, 21, float('nan')]:
            with self.assertRaises(ValueError):
                preview(self.config, dict(self.scores, b1_actitud=value))
        with self.assertRaises(ValueError):
            preview(self.config, {'unknown': 10})

    def test_existing_additional_components_and_ids_are_preserved(self):
        components = [dict(id=str(uuid4()), name='Cuaderno', weight=2),
                      dict(id=str(uuid4()), name='Criterio adicional', weight=3, is_optional=True),
                      dict(id=str(uuid4()), name='Archivado', weight=1, is_active=False)]
        config = from_legacy_components(self.config.course_id, self.config.period_id, components)
        self.assertEqual(len(config.criteria), 6)
        self.assertEqual({c.legacy_component_id for c in config.criteria},
                         {c['id'] for c in components})
        self.assertEqual(sum(c.is_optional for c in config.criteria), 2)
        self.assertEqual(sum(not c.is_active for c in config.criteria), 2)
        scores = {c.key: 10 if c.name == 'Cuaderno' else 20
                  for c in config.criteria if c.is_active}
        self.assertEqual(preview(config, scores)['formula_results']['pf'], 16)
        self.assertEqual(components[0]['weight'], 2)

    def test_additional_criterion_and_explicit_custom_formula(self):
        criterion = Criterion('b1_adicional', 'Criterio sintético adicional', 1, 5)
        expression = ('ROUND((SUM(b1_actitud,b1_cuaderno,b1_modulo,b1_exposicion,'
                      'b1_evaluacion)+b1_adicional)/6,1)')
        formulas = tuple(Formula(f.key, expression) if f.key == 'mes_1' else f
                         for f in self.config.formulas)
        config = replace(self.config, criteria=self.config.criteria + (criterion,), formulas=formulas)
        result = preview(config, dict(self.scores, b1_adicional=20))
        self.assertEqual(result['formula_results']['mes_1'], 15)
        self.assertIsNone(preview(config, self.scores)['formula_results']['pf'])

    def test_revision_scope_metadata_cannot_disagree_with_snapshot(self):
        revision = next_revision(self.config, self.actor, 'Inicial')
        with self.assertRaises(ValueError):
            replace(revision, course_id=str(uuid4())).configuration()

    def test_excel_mapping_uses_block_and_header_not_list_position(self):
        self.assertEqual(source_criterion(self.config, 1, 'MÓDULO').key, 'b1_modulo')
        self.assertEqual(source_criterion(self.config, 2, 'MODULO').key, 'b2_modulo')
        self.assertIsNone(source_criterion(self.config, 1, 'P.F'))
        with self.assertRaises(ValueError):
            Criterion('derived', 'Promedio', 1, 0, source_header='PROMEDIO MENSUAL')
        bad = list(self.config.criteria)
        bad[1] = replace(bad[1], source_header='MÓDULO')
        with self.assertRaises(ValueError):
            replace(self.config, criteria=tuple(bad))


if __name__ == '__main__':
    unittest.main()
