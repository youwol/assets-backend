from youwol.environment.models import IPipelineFactory
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.pipelines.pipeline_fastapi_youwol_backend import get_backend_apps_yw_pipeline
from youwol_utils.context import Context


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, env: YouwolEnvironment, context: Context):
        return await get_backend_apps_yw_pipeline(name="assets-backend", context=context)
