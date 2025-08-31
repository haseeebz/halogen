from typing import Any
from pydantic import BaseModel



class ModelTask(BaseModel):
	namespace: str
	task_name: str
	args: list[str]


class ModelTaskGroup(BaseModel):
	name: str
	tasks: list[ModelTask]


class ModelExtras(BaseModel):
	key: str
	value: Any


class ModelResponse(BaseModel):
	"Use this class if the model can be configured using schema directly."
	message: str
	tasks_groups: list[ModelTaskGroup]
	extras: list[ModelExtras]
