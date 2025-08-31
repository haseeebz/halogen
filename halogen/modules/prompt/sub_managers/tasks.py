from halogen.base import HalogenEvents


tool_intro = """
[TOOLS]
All available tools that you can do. These namespaces are modules and their defined tools are given below. 
These are the functions that you can execute.
Make sure to follow the argument types indicated after the ':' and in python type hint format.

"""


class ToolManager():

	def __init__(self):
		self.tool_map: dict[str, list[tuple[str, str, list[str]]]] = {}
		self.tool_string = ""

	def add_tool(self, ev: HalogenEvents.ToolRegisteredEvent):
		tool_list = self.tool_map.setdefault(ev.namespace, [])
		data = (ev.tool_name, ev.info, ev.args_info)
		tool_list.append(data)
		self.make_tool_section()

	def make_tool_section(self):

		string = []
		string.append(tool_intro)

		for ns, toolslist in self.tool_map.items():
			string.append(f"\n> Namespace: '{ns}'\nDefined tools:")
			for n, i, a in toolslist:
				string.append(f"- name: '{n}'; args: ({a}); info: {i};")
			
		self.tools_section_string = "\n".join(string)

	def stringify(self) -> str:
		return self.tools_section_string