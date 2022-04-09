from pathlib import Path

import youwol_assets_backend
import youwol_utils
from youwol.environment.models import IPipelineFactory
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.pipelines.docker_k8s_helm import InstallHelmStepConfig, get_helm_app_version
from youwol.pipelines.pipeline_fastapi_youwol_backend import pipeline, PipelineConfig, DocStepConfig, \
    CustomPublishDockerStepConfig
from youwol_utils.context import Context


class PipelineFactory(IPipelineFactory):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, env: YouwolEnvironment, context: Context):
        docker_repo = env.k8sInstance.docker.get_repo("gitlab-docker-repo")

        async with context.start(
                action="Pipeline creation for assets-backend",
                with_attributes={'project': 'assets-backend'}
        ) as ctx:  # type: Context

            config = PipelineConfig(
                tags=["assets-backend"],
                k8sInstance=env.k8sInstance,
                dockerConfig=CustomPublishDockerStepConfig(
                    dockerRepo=docker_repo,
                    imageVersion=lambda project, _ctx: get_helm_app_version(project.path),
                    python_modules_copied=[
                        Path(youwol_utils.__file__).parent,
                        Path(youwol_assets_backend.__file__).parent
                    ]
                ),
                docConfig=DocStepConfig(),
                helmConfig=InstallHelmStepConfig(
                    namespace="prod",
                    secrets=[env.k8sInstance.openIdConnect.authSecret, docker_repo.pullSecret],
                    chartPath=lambda project, _ctx: project.path / 'chart',
                    valuesPath=lambda project, _ctx: project.path / 'chart' / 'values.yaml',
                    overridingHelmValues=lambda project, _ctx: {
                        "image": {
                            "tag": get_helm_app_version(project.path)
                        },
                    })
            )
            await ctx.info(text='Pipeline config', data=config)
            result = await pipeline(config, ctx)
            await ctx.info(text='Pipeline', data=result)
            return result
