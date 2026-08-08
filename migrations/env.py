import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata



# ══════════════════════════════════════════════════════════════════
#  MILESTONE AYARLARI  (M3)
# ══════════════════════════════════════════════════════════════════
def milestone_include_object(nesne, ad, tur, yansitildi, karsilastirilan):
    """Autogenerate'in NEYI karsilastiracagini belirler.

    YABANCI ANAHTAR KISITLARI DISLANIR — bilerek.

    models.py'deki 20 yabanci anahtarin hicbirinin ADI yok
    (db.ForeignKey(...) — name= verilmemis). Veritabani ise
    sema_denetim.py ile buyumus; o arac ADD COLUMN yapiyor ama
    KISIT eklemiyor. Sonuc: model ve veritabani sutun duzeyinde
    uyumlu, kisit duzeyinde ayrisik.

    Autogenerate bu farki kapatmaya calisinca isimsiz kisit icin
    DROP CONSTRAINT uretemiyor ve coküyor:
        CompileError: Can't emit DROP CONSTRAINT ... it has no name

    Sutunlar, tipler ve tablolar KARSILASTIRILMAYA DEVAM EDER —
    goc icin gereken bunlar. FK kisitlari elle yonetilir.
    """
    if tur == 'foreign_key_constraint':
        return False
    return True


def milestone_render_item(tur, nesne, autogen_context):
    """Ozel TypeDecorator tiplerini DUZ sa.Numeric olarak yazar.

    NEDEN GEREKLI: models.py'deki Para/Kur/Olcu birer TypeDecorator.
    Autogenerate bunlari `models.Olcu(precision=18, scale=3)` diye
    uretir ama revizyon dosyasi `models`'i ICE AKTARMAZ:
        NameError: name 'models' is not defined
    Uygulama gocun ortasinda coker.

    Veritabani zaten dekoratoru umursamaz — onun icin bu sutun
    NUMERIC(18,3)'tur. Bu yuzden duz sa.Numeric olarak yaziyoruz;
    revizyon bagimsiz ve okunabilir olur.
    """
    if tur == 'type' and nesne.__class__.__name__ in ('Para', 'Kur', 'Olcu'):
        autogen_context.imports.add('import sqlalchemy as sa')
        return 'sa.Numeric(precision=%d, scale=%d)' % (
            nesne.impl.precision or 18, nesne.impl.scale or 4)
    return False


MILESTONE_AYAR = {
    # compare_type: sutun TIPI degisikligini algila.
    # Varsayilan False'tur ve Float->Numeric gocu bu yuzden BOS
    # revizyon uretirdi — goc hic yapilmamis olur, kimse fark etmez.
    'compare_type': True,
    'compare_server_default': False,
    'include_object': milestone_include_object,
    'render_item': milestone_render_item,
}

def run_migrations_offline():
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
        url=url, target_metadata=get_metadata(), literal_binds=True,
        **MILESTONE_AYAR
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        conf_args.update(MILESTONE_AYAR)
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
