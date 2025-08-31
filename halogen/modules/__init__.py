from .command.handler import HalogenCommandHandler
from .logger.module   import HalogenLogModule
from .model.module    import HalogenModelManager
from .tasks.module    import HalogenTaskManager
from .prompt.manager  import HalogenPromptManager
from .server.server   import HalogenServer

from halogen.base.module import HalogenModule
from typing import Type

MODULES: list[Type[HalogenModule]] = [
    HalogenLogModule,
    HalogenCommandHandler,
    HalogenServer,
    HalogenModelManager,
    HalogenTaskManager,
    HalogenPromptManager
] 