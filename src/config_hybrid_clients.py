from typing import Tuple

from minio import Minio
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from youwol_assets_backend import Constants
from youwol_utils import Context, log_info, execute_shell_cmd, log_error, Label, DocDbClient, TableBody, \
    is_server_http_alive
from youwol_utils.clients.file_system.minio_file_system import MinioFileSystem
from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.servers.env import minio_endpoint


async def get_minio_credentials(context_name: str, context: Context) -> Tuple[str, str]:

    secret_name = 'secret/youwol-cluster-minio'
    secret_path = "jsonpath='{.data.rootUser}'"
    kubectl_target = f"--context {context_name} --namespace infra"

    cmd = f"kubectl {kubectl_target} get {secret_name} -o {secret_path} | base64 -d"
    status_code, outputs = await execute_shell_cmd(cmd=cmd, context=context)
    if status_code != 0:
        log_error(f"Failed to retrieve user id from command: \n{cmd}")
        exit()
    root_user = outputs[-1]
    secret_path = "jsonpath='{.data.rootPassword}'"
    cmd = f"kubectl {kubectl_target} get {secret_name} -o {secret_path} | base64 -d"
    status_code, outputs = await execute_shell_cmd(cmd=cmd, context=context)
    if status_code != 0:
        log_error(f"Failed to retrieve user id from command: \n{cmd}")
        exit()
    root_password = outputs[-1]

    log_info("Successfully retrieved root_user & root_password")

    return root_user, root_password


async def get_minio_client(context_name: str, port_fwd: int, context: Context) -> MinioFileSystem:

    log_info(f"Connecting to minio using context {context_name}")
    log_info("Retrieve credential")
    root_user, root_password = await get_minio_credentials(context_name=context_name, context=context)

    port_fwd_listening = is_server_http_alive(f'http://localhost:{port_fwd}')

    if not port_fwd_listening:
        kubectl_target = f"--context {context_name} --namespace infra"
        log_error(f"Minio is expected to be port-forwarded on port {port_fwd}, no connection can be established")
        cmd_port_fwd = f"kubectl {kubectl_target} port-forward service/youwol-cluster-minio {port_fwd}:9000"
        log_info(f"Port forward can be started using:\n{cmd_port_fwd}")
        exit()

    return MinioFileSystem(
        bucket_name=Constants.namespace,
        client=Minio(
            endpoint=minio_endpoint(minio_host="localhost", minio_port=port_fwd),
            access_key=root_user,
            secret_key=root_password,
            secure=False
        )
    )


async def get_docdb_client(context_name: str, port_fwd: int, table: TableBody) -> DocDbClient:

    log_info(f"Connecting to docdb using context {context_name}")
    port_fwd_listening = is_server_http_alive(f'http://localhost:{port_fwd}')

    if not port_fwd_listening:
        kubectl_target = f"--context {context_name} --namespace apps"
        log_error(f"Docdb is expected to be port-forwarded on port {port_fwd}, no connection can be established")
        cmd_port_fwd = f"kubectl {kubectl_target} port-forward service/docdb {port_fwd}:80"
        log_info(f"Port forward can be started using:\n{cmd_port_fwd}")
        exit()

    return DocDbClient(
        url_base=f"http://localhost:{port_fwd}/api",
        keyspace_name=Constants.namespace,
        table_body=table,
        replication_factor=2
    )


class AuthMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.oidcConfig = OidcConfig(base_url="https://platform.youwol.com/auth/realms/youwol")

    async def dispatch(self,
                       request: Request,
                       call_next: RequestResponseEndpoint
                       ) -> Response:

        async with Context.from_request(request).start(
                action="Authorization middleware",
                with_labels=[Label.MIDDLEWARE]
        ):

            if not request.headers.get('Authorization'):
                raise RuntimeError("No bearer token found")
            token_data = self.oidcConfig.token_decode(request.headers.get('Authorization').replace("Bearer ", ""))

            request.state.user_info = token_data

            return await call_next(request)

