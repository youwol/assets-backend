import sys
from config_common import on_before_startup

from youwol_assets_backend import Constants, Configuration
from youwol_utils import StorageClient

from youwol_utils.context import ConsoleContextReporter, Context
from youwol_utils.http_clients.assets_backend import ASSETS_TABLE, ACCESS_HISTORY, ACCESS_POLICY
from youwol_utils.servers.fast_api import FastApiMiddleware, ServerOptions, AppConfiguration

from src.config_hybrid_clients import get_minio_client, AuthMiddleware, get_docdb_client


async def get_configuration():
    context_name = sys.argv[2]
    port_fwd_minio = int(sys.argv[3])
    port_fwd_docdb = int(sys.argv[4])

    file_system = await get_minio_client(
        context_name=context_name,
        port_fwd=port_fwd_minio,
        context=Context(data_reporters=[], logs_reporters=[])
    )

    url_cluster = "platform.youwol.com"

    service_config = Configuration(
        storage=StorageClient(
            url_base=f"http://{url_cluster}/api/storage",
            bucket_name=Constants.namespace
        ),
        doc_db_asset=await get_docdb_client(context_name=context_name, port_fwd=port_fwd_docdb,
                                            table=ASSETS_TABLE),
        doc_db_access_history=await get_docdb_client(context_name=context_name, port_fwd=port_fwd_docdb,
                                                     table=ACCESS_HISTORY),
        doc_db_access_policy=await get_docdb_client(context_name=context_name, port_fwd=port_fwd_docdb,
                                                    table=ACCESS_POLICY),
        file_system=file_system
    )

    async def _on_before_startup():
        await on_before_startup(service_config)

    server_options = ServerOptions(
        root_path="",
        http_port=4006,
        base_path="",
        middlewares=[FastApiMiddleware(AuthMiddleware, {})],
        on_before_startup=_on_before_startup,
        ctx_logger=ConsoleContextReporter()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
