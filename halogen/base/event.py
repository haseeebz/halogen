from dataclasses import dataclass

class HalogenEvent:

	@dataclass(init = True, frozen = True)
	class Event():
		pass

	class InputEvent(Event):
		msg: str

	class OutputEvent(Event):
		msg:str

