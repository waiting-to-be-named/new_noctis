from django.core.management.base import BaseCommand
from viewer.views import ensure_worklist_entries


class Command(BaseCommand):
    help = 'Fix missing worklist entries for studies'

    def handle(self, *args, **options):
        self.stdout.write('Checking for studies without worklist entries...')
        
        created_count = ensure_worklist_entries()
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} worklist entries')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All studies already have worklist entries')
            )