import asyncio
import itertools

import uvicorn
from fastapi import FastAPI, Depends

from youwol_assets.configurations import get_configuration, Configuration
from youwol_assets.root_paths import router as assets_router
from youwol_assets.utils import init_resources
from youwol_utils import log_info
from youwol_utils.middlewares.root_middleware import RootMiddleware
from youwol_utils.utils_paths import matching_files, FileListing, files_check_sum

flatten = itertools.chain.from_iterable

configuration: Configuration = asyncio.get_event_loop().run_until_complete(get_configuration())
asyncio.get_event_loop().run_until_complete(init_resources(configuration))

app = FastAPI(
    title="assets-backend",
    description="backend to manage assets",
    root_path=configuration.open_api_prefix)

app.add_middleware(configuration.auth_middleware, **configuration.auth_middleware_args)
app.add_middleware(RootMiddleware, ctx_logger=configuration.ctx_logger)

app.include_router(
    assets_router,
    prefix=configuration.base_path,
    dependencies=[Depends(get_configuration)],
    tags=[]
)

files_src_check_sum = matching_files(
    folder="./",
    patterns=FileListing(
        include=['*'],
        # when deployed using dockerfile there is additional files in ./src: a couple of .* files and requirements.txt
        ignore=["requirements.txt", ".*", "*.pyc"]
    )
)

log_info(f"./src check sum: {files_check_sum(files_src_check_sum)} ({len(files_src_check_sum)} files)")

if __name__ == "__main__":
    # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
    # noinspection PyTypeChecker
    uvicorn.run(app, host="0.0.0.0", port=configuration.http_port)
