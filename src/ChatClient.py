import mcp_client
import openai,json,os
import colorama as clr
# workdir = ''
# with open('settings.property','r',encoding='utf-8') as f:
#     exec(f.read())
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class ChatClient:
    def __init__(self, api_key:str, base_url:str, model_name:str, system_prompt:str=None, with_tools:bool=True, show_tool_calls:bool=False, notice_dir:str="notice_files", max_tool_iterations:int=16):
        # 如果没有提供 system_prompt，使用默认的知识库助手提示词
        if system_prompt is None:
            system_prompt = """你是一个专业的知识库助手，基于大型语言模型（LLM）提供准确的信息查询和知识服务。

你的核心职责：
1. 通过可用工具访问知识库索引和文档，为用户提供准确的信息
2. 基于检索到的内容回答问题，不要编造信息
3. 如果知识库中没有相关信息，明确告知用户

可用工具说明：
- get_index: 读取知识库索引，了解知识库包含哪些文档和主题
- read_file: 读取具体文档内容，获取详细信息
- get_RealTime: 获取当前时间

工作流程建议：
1. 首先使用 get_index 了解知识库的整体结构和相关文档
2. 根据索引信息，使用 read_file 读取相关文档的具体内容
3. 基于文档内容为用户提供准确的回答

重要原则：
- 始终基于实际文档内容回答问题
- 如果文档内容与用户问题相关但不完全匹配，说明情况并提供最接近的信息
- 对于不确定的信息，明确标注不确定性
- 保持回答简洁、准确、有条理"""
        
        self.messages = [{"role": "system", "content": system_prompt}]
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.with_tools = with_tools
        self.show_tool_calls = show_tool_calls
        self.notice_dir = notice_dir
        self.max_tool_iterations = max_tool_iterations
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        if self.with_tools:
            self.tools = mcp_client.get_tools()
        else:
            self.tools = None
    
    def chat(self, user_prompt:str, messages:list=None):
        """
        与模型进行一次对话。
        :param user_prompt: 用户输入的提示
        :param messages: 可选的消息历史记录
        :return: 模型的回复内容
        """
        if messages is None:
            pass
        else:
            self.messages = messages
        self.messages.append({"role": "user", "content": user_prompt})
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.messages,
            tools=self.tools if self.with_tools else None,
            max_tokens=8192,
        )
        self.messages.append(response.choices[0].message)
        tool_iteration_count = 0
        while response.choices[0].message.tool_calls:
            if tool_iteration_count >= self.max_tool_iterations:
                print(f"{clr.Fore.RED}达到最大工具调用层数限制 ({self.max_tool_iterations})，终止工具调用{clr.Style.RESET_ALL}")
                break
            tool_iteration_count += 1
            print(f"{clr.Fore.YELLOW}Assistant:{clr.Style.RESET_ALL}", response.choices[0].message.content)
            if self.show_tool_calls:
                print(f"{clr.Back.WHITE}{clr.Fore.CYAN}Tool Calls:", response.choices[0].message.tool_calls, clr.Style.RESET_ALL)
            for tool_call in response.choices[0].message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                tool_result = mcp_client.call_tool(tool_name, arguments)
                self.messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_result})
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.messages,
                tools=self.tools if self.with_tools else None,
                max_tokens=8192,
            )
            self.messages.append(response.choices[0].message)
        print(f"{clr.Fore.GREEN}Assistant:{clr.Style.RESET_ALL}", response.choices[0].message.content)
        return response.choices[0].message.content
    
    def get_messages(self):
        return self.messages
    
    def reset_messages(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def tool_call(self, tool_name:str, arguments:str):
        self.messages.append({"role": "user", "content": f"Call tool {tool_name} with arguments {arguments}"})
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.messages,
            tools=self.tools if self.with_tools else None,
        )
        self.messages.append(response.choices[0].message)
        return response.choices[0].message.content

    def start_interactive_chat(self):
        """
        Start an interactive chat session with the model.
        """
        print(clr.Fore.GREEN + f"""
        欢迎使用 {self.model_name} 模型
        您可以与模型进行交互，
        输入 "{clr.Fore.MAGENTA}exit{clr.Fore.GREEN}" 退出
        输入 "{clr.Fore.MAGENTA}reset{clr.Fore.GREEN}" 重置对话历史
        
        可用工具: {clr.Fore.CYAN}{[tool["function"]["name"] for tool in self.tools] if self.with_tools else "无"}{clr.Style.RESET_ALL}
        """)
        while True:
            user_prompt = input(f"{clr.Fore.MAGENTA}User:{clr.Style.RESET_ALL} ")
            if user_prompt.lower() == "exit" or user_prompt.lower() == "quit":
                print(clr.Fore.RED + "退出对话" + clr.Style.RESET_ALL)
                break
            if user_prompt.lower() == "reset":
                self.reset_messages()
                print(clr.Fore.RED + "重置对话历史" + clr.Style.RESET_ALL)
                continue
            self.chat(user_prompt)
    


if __name__ == "__main__":
    # 请替换为您的 API 配置
    DS_base_url = "https://api.deepseek.com"
    DS_api_key = "sk-YOUR_API_KEY_HERE"  # 替换为您的 DeepSeek API Key
    DS_model = "deepseek-chat"
    client = ChatClient(base_url=DS_base_url, api_key=DS_api_key, model_name=DS_model, with_tools=True, show_tool_calls=True)
    client.start_interactive_chat()