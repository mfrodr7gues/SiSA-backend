from django.core.management.base import BaseCommand
from apps.certificates.services import issue_pending

class Command(BaseCommand):
    help = 'Emite certificados pendentes de atividades encerradas com frequência presente.'

    def handle(self, *args, **kwargs):
        issued, skipped = issue_pending()
        self.stdout.write(self.style.SUCCESS(f'Certificados emitidos: {issued}; sem sessões: {skipped}'))
