# test_chat.py
from chat_graph import build_chat_graph
from langchain_core.messages import HumanMessage

app = build_chat_graph()
config = {"configurable": {"thread_id": "test-001"}}

while True:
    question = input("\n질문: ")
    if question.lower() in {"exit", "quit", "q"}:
        break
    
    result = app.invoke(
        {"messages": [HumanMessage(content=question)]},
        config=config
    )
    print(f"\n답변: {result['messages'][-1].content}")
    if result.get("sources"):
        print(f"출처: {[s['label'] for s in result['sources']]}")