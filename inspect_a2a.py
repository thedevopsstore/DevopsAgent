from strands.multiagent.a2a import A2AServer
import inspect

print("Methods of A2AServer:")
for name, method in inspect.getmembers(A2AServer):
    print(f"- {name}")

print("\nTrying to instantiate and check for rpc_methods or similar...")
try:
    # Mock agent
    class MockAgent:
        name = "MockAgent"
        description = "A mock agent"
        tool_registry = {}
        def __call__(self, *args, **kwargs): return "response"
    
    server = A2AServer(agent=MockAgent(), host="localhost", port=9000)
    app = server.to_fastapi_app()
    
    print("\nFastAPI Routes:")
    for route in app.routes:
        print(f"- {route.path} [{route.methods}]")
        
except Exception as e:
    print(f"Error: {e}")
