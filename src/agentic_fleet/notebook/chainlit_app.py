import time
from openai import AsyncOpenAI

import chainlit as cl

import os
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    )


@cl.on_message
async def on_message(msg: cl.Message):
    start = time.time()
    
    # Format messages properly for Deepseek API
    messages = [{"role": "system", "content": "You are an helpful assistant"}]
    
    # Get chat history and ensure proper interleaving
    chat_history = cl.chat_context.to_openai()
    messages.extend(chat_history)
    
    # Add current message
    messages.append({"role": "user", "content": msg.content})
    
    stream = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=True,
    )

    thinking = True
    
    # Initialize content before streaming
    final_answer = cl.Message(content="")

    # Streaming the thinking
    async with cl.Step(name="Thinking") as thinking_step:
        async for chunk in stream:
            if not hasattr(chunk.choices[0], 'delta') or not hasattr(chunk.choices[0].delta, 'content'):
                continue
                
            delta = chunk.choices[0].delta
            content = delta.content
            
            if content is None:
                continue

            if content == "<think>":
                thinking = True
                continue

            if content == "</think>":
                thinking = False
                thought_for = round(time.time() - start)
                thinking_step.name = f"Thought for {thought_for}s"
                await thinking_step.update()
                continue

            if thinking:
                await thinking_step.stream_token(content)
            else:
                final_answer.content += content

    if final_answer.content:
        await final_answer.send()
