import asyncio
import websockets
import time
import json
import threading
import asyncio
import argparse
import queue
from pathlib import Path
import chatglm_cpp

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "chatglm-ggml.bin"

BANNER = """
    ________          __  ________    __  ___                 
   / ____/ /_  ____ _/ /_/ ____/ /   /  |/  /_________  ____  
  / /   / __ \/ __ `/ __/ / __/ /   / /|_/ // ___/ __ \/ __ \ 
 / /___/ / / / /_/ / /_/ /_/ / /___/ /  / // /__/ /_/ / /_/ / 
 \____/_/ /_/\__,_/\__/\____/_____/_/  /_(_)___/ .___/ .___/  
                                              /_/   /_/       
""".strip(
    "\n"
)


class OutputPower():
    async def run(self,arg,s,websocket):
        # 发送消息方法，单独和请求的客户端发消息
        #await s('hi one', websocket)
        # 群发消息
        #await s('hi all')
        # 数据定义{"topic":"dm.input","text":"讲下孔融让梨的故事 "}
        print('handle msg',arg)
        msg = json.loads(arg)
        
        if not promptQueue.empty():
            print('now just support one prompt')
            return
        promptQueue.put(msg['text'])
        
# 存储所有的客户端
Clients = []
# 单个队列
promptQueue = queue.Queue(1)

class Server():
	# 发消息给客户端的回调函数
    async def s(self,msg,websocket=None):
        await self.sendMsg(msg,websocket)
    # 针对不同的信息进行请求，可以考虑json文本
    async def runCase(self,jsonMsg,websocket):
        print('runCase')
        # await OutputPower(jsonMsg,self.s,websocket)
        op = OutputPower()
        await op.run(jsonMsg,self.s,websocket)

    # 每一个客户端链接上来就会进一个循环
    async def echo(self,websocket, path):
        # 当前性能有限，只允许支持一个client
        print("Clients len:",len(Clients) )
        if len(Clients) != 0 :
            print('current only support 1 client')
            await websocket.send(json.dumps({"error":{"code": "1006","msg":"now only support 1 client"}}))
            await asyncio.sleep(1)
            await websocket.close()
            return
        
        Clients.append(websocket)
        await websocket.send(json.dumps({"type": "handshake"}))
        while True:
            try:
                recv_text = await websocket.recv()
                #message = "I got your message: {}".format(recv_text)
                # 直接返回客户端收到的信息
                #await websocket.send(message)
                #print(message)

                # 分析当前的消息 json格式，跳进功能模块分析
                await self.runCase(jsonMsg=recv_text,websocket=websocket)

            except websockets.ConnectionClosed:
                print("ConnectionClosed...", path)  # 链接断开
                Clients.remove(websocket)
                break
            except websockets.InvalidState:
                print("InvalidState...")  # 无效状态
                Clients.remove(websocket)
                break
            except Exception as e:
                print(e)
                Clients.remove(websocket)
                break

    # 发送消息
    async def sendMsg(self,msg,websocket):
        print('sendMsg:',msg)
        if websocket != None:
            await websocket.send(msg)
        else:
            await self.broadcastMsg(msg)
        # 避免被卡线程
        await asyncio.sleep(0.2)

	# 群发消息
    async def broadcastMsg(self,msg):
        for user in Clients:
            await user.send(msg)

    # 启动服务器
    async def runServer(self):
        async with websockets.serve(self.echo, '', 7600):
            await asyncio.Future()  # run forever

	# 多线程模式，防止阻塞主线程无法做其他事情
    def WebSocketServer(self):
        asyncio.run(self.runServer())

    def startServer(self):
        # 多线程启动，否则会堵塞
        thread = threading.Thread(target=self.WebSocketServer)
        thread.start()
        # thread.join()
        print("go!!!")
        

def main():

    print('> starting server...')
    s = Server()
    s.startServer()
    print('> starting server end')

    # start ChatGLMcpp
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL_PATH, type=Path)
    #parser.add_argument("-p", "--prompt", default="你好", type=str)
    #parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("-l", "--max_length", default=2048, type=int)
    parser.add_argument("-c", "--max_context_length", default=512, type=int)
    parser.add_argument("--top_k", default=0, type=int)
    parser.add_argument("--top_p", default=0.7, type=float)
    parser.add_argument("--temp", default=0.95, type=float)
    parser.add_argument("-t", "--threads", default=0, type=int)
    args = parser.parse_args()

    pipeline = chatglm_cpp.Pipeline(args.model)
    
    print(BANNER)
    history = []
    prompt = ''
    while True:
        # try:
        #     prompt = input(f"{'Prompt':{len(pipeline.model.type_name)}} > ")

        # except EOFError:
        #     break
        # if not prompt:
        #     continue
    
        if  promptQueue.empty():
            continue
        prompt = promptQueue.get()
        print("now prompt", prompt)

        history.append(prompt)
        print(f"{pipeline.model.type_name} > ", sep="", end="")
        output = ""
        for piece in pipeline.stream_chat(
            history,
            max_length=args.max_length,
            max_context_length=args.max_context_length,
            do_sample=args.temp > 0,
            top_k=args.top_k,
            top_p=args.top_p,
            temperature=args.temp,
        ):
            print(piece, sep="", end="", flush=True)
            output += piece

            # 发送到 websocket 客户端 
            if len(Clients) != 0:
                asyncio.get_event_loop().run_until_complete(sendSebsocket(json.dumps({"topic":"dm.ing","dm":{"piece":piece, "output":output}},ensure_ascii=False)))
        print()
        #history.append(output)

        # 性能有效，保留一轮的对话
        history = [prompt,output]

        if len(Clients) != 0:
                asyncio.get_event_loop().run_until_complete(sendSebsocket(json.dumps({"topic":"dm.result","dm":{"piece":piece, "output":output}},ensure_ascii=False))) 
                client = Clients[0]

    print("Bye")

async def sendSebsocket(message):
    if len(Clients) != 0:
        client = Clients[0]
        await client.send(message)

if __name__=='__main__':
    main()

