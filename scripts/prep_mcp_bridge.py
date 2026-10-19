"""Local Blender MCP socket bridge, compatible with the preserved execute_code client.

Only the local computer can connect. Blender mutations run on Blender's main thread.
The persistent timer keeps the connection alive when the project is opened.
"""
import bpy
import contextlib
import io
import json
import queue
import socket
import threading
import traceback

def start():
    if getattr(bpy, '_prep_mcp_bridge', None):
        return
    pending=queue.Queue()
    server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.bind(('127.0.0.1',9876))
    server.listen(4)
    bpy._prep_mcp_bridge=server
    def serve():
        while True:
            client,_=server.accept()
            def respond(connection):
                with connection:
                    data=b''
                    while True:
                        data+=connection.recv(1024*1024)
                        try:request=json.loads(data);break
                        except json.JSONDecodeError:pass
                    result=queue.Queue(maxsize=1)
                    pending.put((request,result))
                    connection.sendall(json.dumps(result.get(),ensure_ascii=True).encode())
            threading.Thread(target=respond,args=(client,),daemon=True).start()
    def execute():
        try:request,result=pending.get_nowait()
        except queue.Empty:return .1
        log=io.StringIO()
        try:
            if request.get('type')!='execute_code':raise ValueError('Unsupported command')
            with contextlib.redirect_stdout(log):
                exec(request['params']['code'],{'bpy':bpy,'__name__':'prep_mcp_execution'})
            result.put({'status':'success','result':{'executed':True,'output':log.getvalue()}})
        except Exception:
            result.put({'status':'error','message':traceback.format_exc(),'output':log.getvalue()})
        return .1
    threading.Thread(target=serve,daemon=True).start()
    bpy.app.timers.register(execute,persistent=True)
    print('PREP Blender MCP connected: 127.0.0.1:9876')

start()
