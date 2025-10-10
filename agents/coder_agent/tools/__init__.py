"""
Coder Agent Tools Package
=========================

This package contains tools for code execution and validation.

Tools:
    - code_interpreter_tool: Executes Python code in a restricted environment

Usage:
    from agents.coder_agent.tools.code_interpreter import code_interpreter_tool

    code = '''
    def add(a, b):
        return a + b
    result = add(5, 3)
    print(result)
    '''
    result = code_interpreter_tool(code, language="python")
    print(result.output)
"""

from agents.coder_agent.tools.code_interpreter import code_interpreter_tool

__all__ = ["code_interpreter_tool"]
