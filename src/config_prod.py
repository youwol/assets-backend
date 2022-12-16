import os

from minio import Minio
from youwol_utils.clients.file_system.minio_file_system import MinioFileSystem

from config_common import on_before_startup
from youwol_assets_backend import Configuration, Constants
from youwol_utils import StorageClient, DocDbClient, get_authorization_header
from youwol_utils.clients.oidc.oidc_config import OidcInfos, PrivateClient
from youwol_utils.context import DeployedContextReporter
from youwol_utils.http_clients.assets_backend import ASSETS_TABLE, ACCESS_HISTORY, ACCESS_POLICY
from youwol_utils.middlewares import AuthMiddleware
from youwol_utils.servers.env import OPENID_CLIENT, Env, minio_endpoint
from youwol_utils.servers.fast_api import FastApiMiddleware, ServerOptions, AppConfiguration


async def get_configuration():
    required_env_vars = OPENID_CLIENT

    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")

    openid_infos = OidcInfos(
        base_uri=os.getenv(Env.OPENID_BASE_URL),
        client=PrivateClient(
            client_id=os.getenv(Env.OPENID_CLIENT_ID),
            client_secret=os.getenv(Env.OPENID_CLIENT_SECRET)
        )
    )

    async def _on_before_startup():
        await on_before_startup(service_config)

    docdb_url_base = "http://docdb/api"

    service_config = Configuration(
        storage=StorageClient(
            url_base="http://storage/api",
            bucket_name=Constants.namespace),
        doc_db_asset=DocDbClient(
            url_base=docdb_url_base,
            keyspace_name=Constants.namespace,
            table_body=ASSETS_TABLE,
            replication_factor=2
        ),
        doc_db_access_history=DocDbClient(
            url_base=docdb_url_base,
            keyspace_name=Constants.namespace,
            table_body=ACCESS_HISTORY,
            replication_factor=2
        ),
        doc_db_access_policy=DocDbClient(
            url_base=docdb_url_base,
            keyspace_name=Constants.namespace,
            table_body=ACCESS_POLICY,
            replication_factor=2
        ),
        admin_headers=await get_authorization_header(openid_infos),
        file_system=MinioFileSystem(
            bucket_name=Constants.namespace,
            client=Minio(
                endpoint=minio_endpoint(minio_host=os.getenv(Env.MINIO_HOST)),
                access_key=os.getenv(Env.MINIO_ACCESS_KEY),
                secret_key=os.getenv(Env.MINIO_ACCESS_SECRET),
                secure=False
            )
        )
    )

    server_options = ServerOptions(
        root_path='/api/assets-backend',
        http_port=8080,
        base_path="",
        middlewares=[
            FastApiMiddleware(
                AuthMiddleware, {
                    'openid_infos': openid_infos,
                    'predicate_public_path': lambda url:
                    url.path.endswith("/healthz")
                }
            )
        ],
        on_before_startup=_on_before_startup,
        ctx_logger=DeployedContextReporter()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
