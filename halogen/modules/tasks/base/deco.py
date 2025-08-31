
def HalogenTool(name: str, info: str, args: list[str]):

	def decorator(func):
		
		def wrapper(*func_args, **kwargs):
			return func(*func_args, **kwargs)
		
		wrapper._is_tool = True
		wrapper._name = name
		wrapper._info = info
		wrapper._args = args
		
		return wrapper
	
	return decorator
