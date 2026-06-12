"""Roda a suíte de evals do agente e reporta X/N cenários aprovados.

    uv run python manage.py evals                # suíte completa (com LLM-judge)
    uv run python manage.py evals --no-judge     # só asserts determinísticos
    uv run python manage.py evals --scenario preco_nao_repete

Cada cenário roda o grafo real (chama o LLM via OpenRouter) num thread isolado
com estado em memória — não toca o banco de produção. Como bate na API, custa
tokens; rode deliberadamente, não em todo commit.

Sai com código 1 se algum cenário reprovar (útil pra CI).
"""

import sys

from django.core.management.base import BaseCommand

from agent.evals.harness import run_suite
from agent.evals.scenarios import SCENARIOS


class Command(BaseCommand):
    help = 'Roda a suíte de evals do agente e reporta X/N cenários aprovados.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-judge',
            action='store_true',
            help='Pula o LLM-judge; roda só os asserts determinísticos.',
        )
        parser.add_argument(
            '--scenario',
            default=None,
            help='Roda apenas o cenário com este id.',
        )

    def handle(self, *args, **options):
        scenarios = SCENARIOS
        if options['scenario']:
            scenarios = [s for s in SCENARIOS if s.id == options['scenario']]
            if not scenarios:
                self.stderr.write(self.style.ERROR(f'Cenário desconhecido: {options["scenario"]}'))
                ids = ', '.join(s.id for s in SCENARIOS)
                self.stderr.write(f'Disponíveis: {ids}')
                sys.exit(2)

        use_judge = not options['no_judge']
        self.stdout.write(
            f'Rodando {len(scenarios)} cenário(s) '
            f'{"com" if use_judge else "sem"} LLM-judge...\n'
        )

        results = run_suite(scenarios, use_judge=use_judge)

        passed = 0
        for r in results:
            if r.passed:
                passed += 1
                self.stdout.write(self.style.SUCCESS(f'[PASS] {r.scenario.id}'))
            else:
                self.stdout.write(self.style.ERROR(f'[FAIL] {r.scenario.id}'))

            if r.error:
                self.stdout.write(f'    erro de execução: {r.error}')

            for name, ok, detail in r.assert_results:
                if not ok:
                    self.stdout.write(f'    - {name}: {detail}')

            v = r.judge_verdict
            if v is not None:
                flag = '' if r.judge_passed else '  <-- reprovou'
                self.stdout.write(
                    f'    judge: nota={v.nota} natural={v.natural} '
                    f'repetiu={v.repetiu_pergunta} inventou={v.inventou_fato}{flag}'
                )
                if not r.judge_passed:
                    self.stdout.write(f'      justificativa: {v.justificativa}')

        total = len(results)
        style = self.style.SUCCESS if passed == total else self.style.WARNING
        self.stdout.write('')
        self.stdout.write(style(f'Resultado: {passed}/{total} cenários aprovados'))

        if passed != total:
            sys.exit(1)
