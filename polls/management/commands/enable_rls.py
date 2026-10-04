from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = (
        "Enable Row Level Security on every table in the public schema (PostgreSQL/Supabase). "
        "No policies are added, so the Supabase anon/authenticated roles cannot read the tables "
        "through the Data API; Django connects as a privileged role and is unaffected. "
        "Run it again after every migration that creates tables."
    )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("enable_rls only works with PostgreSQL.")

        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                cursor.execute(
                    "ALTER TABLE public.{} ENABLE ROW LEVEL SECURITY".format(connection.ops.quote_name(table))
                )
        self.stdout.write(self.style.SUCCESS(f"RLS etkinleştirildi: {len(tables)} tablo."))
