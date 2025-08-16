from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# это объект конфигурации Alembic, который предоставляет
# доступ к значениям из .ini файла.
config = context.config

# Интерпретация файла конфигурации для логирования Python.
# Эта строка в основном настраивает логгеры.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# добавьте сюда модель для 'autogenerate'
# например, from myapp.models import Base
# target_metadata = Base.metadata
target_metadata = None

# другие опции можно получить из config,
# например, для поддержки нескольких баз данных:
# my_important_option = config.get_main_option("my_important_option")
# ... и так далее.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()