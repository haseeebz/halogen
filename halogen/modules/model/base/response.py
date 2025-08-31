from typing import Any
from pydantic import BaseModel


class ModelSubTask(BaseModel):
	namespace: str
	func_name: str
	args: list[str]


class ModelTask(BaseModel):
	name: str
	sub_tasks: list[ModelSubTask]


class ModelExtras(BaseModel):
	key: str
	value: Any


class ModelResponse(BaseModel):
	"Use this class if the model can be configured using schema directly."
	message: str
	tasks: list[ModelTask]
	extras: list[ModelExtras]
