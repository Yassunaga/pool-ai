import uuid

from django.core.management.base import BaseCommand

from agent.graph import get_graph
from agent.services.chat_service import send_message


class Command(BaseCommand):
    help = 'Run an interactive REPL against the LangGraph sales agent.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--session-id',
            default=None,
            help='Conversation thread id. Defaults to a new uuid (fresh conversation).',
        )

    def handle(self, *args, **options):
        session_id = options['session_id'] or f'cli-{uuid.uuid4().hex[:8]}'
        graph = get_graph()
        self.stdout.write(graph.get_graph().draw_mermaid())
        self.stdout.write(self.style.SUCCESS(f'Session: {session_id}'))
        self.stdout.write('Type your message and press Enter. Use "exit" / "quit" or Ctrl+C to end.\n')

        while True:
            try:
                user_input = input('you> ').strip()
            except (EOFError, KeyboardInterrupt):
                self.stdout.write('\nBye.')
                return

            if not user_input:
                continue
            if user_input.lower() in {'exit', 'quit'}:
                self.stdout.write('Bye.')
                return

            result = send_message(session_id, user_input)
            self.stdout.write(self.style.HTTP_INFO(f'bot> {result["replies"]}'))
