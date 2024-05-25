
import re, json, random, time, queue, threading, traceback, hashlib, string, random
import websocket
import random
from pathlib import Path
from urllib.parse import urlparse
from bb_assistant.util.config import *
import time
import logging
from python_graphql_client import GraphqlClient
import requests
from langchain_core.language_models.llms import LLM
from typing import Any, Dict, Iterator, List, Mapping, Optional
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.documents import Document
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Gpt4():
    gql_url = "https://poe.com/api/gql_POST"
    gql_recv_url = "https://poe.com/api/receive_POST"
    home_url = "https://poe.com"
    settings_url = f"https://poe.com/api/settings?channel={SOCKET_CHANNEL3['channel']}"

    def __init__(self, tokens:dict={}, proxy:dict={}, headers:dict={}, cookies:dict={},chat_bot:str="beaver"):
        self.ws_connecting = False
        self.ws_connected = False
        self.ws_error = False
        self.connect_count = 0
        self.setup_count = 0
        self.cookies = cookies
        self.static_headers = headers
        self.tokens = tokens
        self.proxy = proxy
        self.active_message = ""
        self.formkey_salt = None
        self.activeId = None
        self.channel = None
        self.checkpoint = 0
        self.lock = True
        self.chat_bot = chat_bot
        self.price_mapping = {
            'gpt4_o':300,
            'capybara': 20,
            'beaver': 350, 
            'llama38bt': 15, 
            'gemini_pro': 20, 
            'dalle3': 1500, 
            'upstage_solar_0_70b_16bit': 1,
            'stablediffusionxl': 80,
            'playgroundv25': 40,
            'websearch': 40,
            'claude_2_1_bamboo': 200,
            'claude_3_haiku': 30,
            'claude_2_1_cedar': 2000,
            'gemini_1_5_pro': 250,
            'stablediffusion3': 1600,
            'sd3turbo': 1000}
        self.setup_connection()
        self.connect_ws()
        
        # self.subscribe()
        self.parent_prompt_v1 = """
        :از شما انتظار دارم در این مکالمه به تمامی سوالات راجع به هویت خود یا نام یا سازنده خود به این شکل پاسخ بدی
        تو یک دستیار هوشمند فارسی به نام  آناهیتا هستی که توسط متخصصین تیم اینتلیکس طراحی شدی
        """
        self.parent_prompt = """
        تو یک دستیار هوشمند بیمه فارسی به نام آناهیتا هستی, از شما انتظار دارم در قالب مشخص شده حاوی تگ های 
        <سوال>
        متن سوال اینجا قرار میگیرد
        <پایان سوال>
        <زمینه>
        مطالب زمینه اینجا قرار میگیرند
        <پایان زمینه>
        با خواندن مطالب موجود در تگ <زمینه> قست های مرتبط با سوال من رو پیدا کن و به درخواست من در قسمت <سوال> پاسخ بده
        در تمام طول مکالمه این موارد را رعایت کن:
        سعی کن پاسخ کامل و حتما بر اساس اطلاعات داخل قسمت <زمینه> باشدو از دانش قبلی خودت استفاده ایی نکنی
        پاسخ خود را همیشه با کلمات 'طبق اطلاعات من' شروع کن
        اگر درخواست من در خصوص توضیح بیشتر در مورد قسمتی از مکالمه بود پاسخ من را از قسمت زمینه پیام قبل بده و زمینه جدید را نادیده بگیر
        """
        self.activeId = self.init_chat()
        # self.parent_prompt =  """
        # # System: Your name is BimeBazar-Assistant and you are my intelligent, knowledgeable, and helpful insurrance specialist bot.   
        # # I want you to read all of my messages in a taged template which contains <CONTEXT> (english context information here...) <END OF CONTEXT> and <QUESTION> (a question in persian languige here...) <END OF QUESTION>.
        # # in every message read the text in  <QUESTION> tag and answer it considering the text contained between <CONTEXT> section
        # # I am NOT interested in your own prior knowledge or opinions and I want you to say I don't know if the provided information in <CONTEXT> is not enough to answer my question.
        # # please note these rules/steps before answering:
        # # - Use three sentences maximum and keep the answer concise. 
        # # - You have to consider that the these text contained between <CONTEXT> and <END OF CONTEXT> contains various types of names and models which are cruicial to the answer so you Must include them in your response.
        # # - make sure you translate answer to persian languige.
        # # """
        
    def subscribe(self):
        payload,variables,headers = self.query_generator("subscription")
        result = self.client.execute(query=payload,variables=variables,headers=headers,operation_name=headers['x-apollo-operation-name'])
        return result
    def setup_connection(self):
        self.client = GraphqlClient(endpoint="https://www.quora.com/poe_api/gql_POST",headers=self.static_headers,proxies=self.proxy,cookies=self.cookies)
        self.ws_domain = f"tch{random.randint(1, 1e6)}"
        self.channel = self.get_channel()
        

    
    def query_generator(self,alias):
        query_mapping = {
            "bot-pagination":{"x-apollo-operation-name":"PaginatedAvailableBotsQuery","x-apollo-operation-id":"c9751b1c86a79597ede502ef005cf582ae064a977d5625a01073eed294e4d8e8"},
            "message-edge":{"x-apollo-operation-name":"MessageEdgeCreateMutation","x-apollo-operation-id":"8ffd5afe2cf22981eba9611d6c59e7d496d0bffab6fcd57e66f185f182d8b63d"},
            "bot-query":{"x-apollo-operation-name":"BotQuery","x-apollo-operation-id":"57d625dbe6dca65f0edd973c1a4b0d480625e4a1e6375bbf5dfc26271b9c45db"},
            "chat-pagination":{"x-apollo-operation-name":"ChatPaginationQuery","x-apollo-operation-id":"64c610268079c4bc055017b1c15b229fcf91cf783a4b36075055fd84cb0aa4d7"},
            "chat-list":{"x-apollo-operation-name":"ChatListQuery","x-apollo-operation-id":"fd702a921efa8651625a1c07de4412e8f75219281a2406c0cf8a8594697ab1a5"},
            "bots-explore":{"x-apollo-operation-name":"ExploreBotsPaginationQuery","x-apollo-operation-id":"7ec7e6ef9f018de1913a3f6de90ae8ff6dd743ee72ca078ea1eafa693fd47760"},
            "subscription":{"x-apollo-operation-name":"SubscriptionQuery","x-apollo-operation-id":"73371cbe94c075c9d4e2c4e1ff51db6a8c79e16c4e1a98481746dff67b86073f"}
        }
        key = query_mapping[alias]["x-apollo-operation-name"]
        static_headers = self.static_headers
        static_headers["x-apollo-operation-name"] = query_mapping[alias]["x-apollo-operation-name"]
        static_headers["x-apollo-operation-id"] = query_mapping[alias]["x-apollo-operation-id"]
        query_headers = static_headers
        with open(f"./assets/queries/variables.json","r",encoding='utf-8') as var:
            allvars = json.load(var)
            target_vars = allvars[key]
        with open(f"./assets/queries/{key}.graphql","r",encoding='utf-8') as query:
            query = query.read()
        
        return query,target_vars,query_headers

    def get_channel(self):
        try:
            response = requests.get(self.settings_url,proxies=self.proxy,headers=self.static_headers)
            return response.json()
        except Exception as fail:
            logger.error(f"failed to fetch wss channel settings from {self.settings_url} | {fail}")

    def get_available_bots(self,limit:int=25):
        payload,variables,headers = self.query_generator("bot-pagination")
        variables["first"] = limit
        result = self.client.execute(query=payload,variables=variables,headers=headers,operation_name=headers['x-apollo-operation-name'])
        available_bots = {}
        for bot in result["data"]["viewer"]["availableBotsConnection"]["edges"]:
           available_bots[bot["node"]["nickname"]] = bot["node"]["botId"]
        return available_bots
    def init_chat(self):
        payload,variables,headers = self.query_generator("message-edge")
        variables["query"] = self.parent_prompt_v1
        variables["bot"] = self.chat_bot
        variables["messagePointPrice"] = self.price_mapping[self.chat_bot]
        initial_msg = self.client.execute(query=payload, variables=variables,headers=headers,operation_name=headers['x-apollo-operation-name'])
        self.activeId = initial_msg["data"]["messageEdgeCreate"]["chat"]["chatId"]
        logger.warning(f"initiated initialized chat with id {self.activeId}")
        while self.lock:
            time.sleep(6)
        logger.warning(f"dumping away {self.active_message} on checkpoint {self.checkpoint}")
        self.lock = True
        self.active_message = ""
        self.checkpoint = 0
        return initial_msg["data"]["messageEdgeCreate"]["chat"]["chatId"]
    def send_message(self,chatbot:str="capybara",chatId:int=None,message:str=""):
        while self.ws_error:
            time.sleep(0.01)
        self.active_message = ""
        self.checkpoint = 0
        self.lock = True
        payload,variables,headers = self.query_generator("message-edge")
        if chatbot == "" or chatbot is None:
            self.chat_bot = "capybara"
        if self.activeId is None:
            self.init_chat()
        
        try:
            variables["query"] = message
            variables["bot"] = self.chat_bot
            variables["chatId"]= self.activeId
            variables["messagePointPrice"] = self.price_mapping[chatbot]
            message_data = self.client.execute(query=payload, variables=variables,headers=headers,operation_name=headers['x-apollo-operation-name'])
        except Exception as e:
            raise e
        
        if message_data["data"] is None:
            raise Exception(F"Graphql Call Failed with Empty Response :{message_data}")
        if not message_data["data"]["messageEdgeCreate"]["message"]:
            raise RuntimeError(f"Daily limit reached for {chatbot}.")
        try:
            # human_message = message_data["data"]["messageEdgeCreate"]["message"]
            # human_message_id = human_message["node"]["messageId"]
            self.activeId = message_data["data"]["messageEdgeCreate"]["chat"]["chatId"]
        except TypeError:
            raise RuntimeError(f"An unknown error occurred. Raw response data: {message_data}")

        # while self.lock:
        #     logger.info("waiting to collect message response")
        #     time.sleep(1)
        return self.active_message,self.activeId


    def chat_list(self,bot:str="capybara",limit:int=15):

        # reconnect websocket
        while self.ws_error:
            time.sleep(0.01)
        logger.info(f"Sending message to {bot}: id={bot}")

        try:
            payload,variables,headers = self.query_generator("chat-list")
            bots_map = self.get_available_bots()
            variables["botId"] = bots_map[bot]
            variables["first"] = limit
            
            message_data = self.client.execute(query=payload, variables=variables,headers=headers,operation_name=headers['x-apollo-operation-name'])
            buffer = []
            
            for msg in message_data["data"]["chats"]["edges"]:
                content  = {}
                intenal_edges = msg["node"]["messagesConnection"]["edges"]
                content["title"] = msg["node"]["title"]
                content["id"] = msg["node"]["chatId"]
                for edge in intenal_edges:
                    if edge["node"]["authorNickname"] == "human":
                        content["human"] = edge["node"]["text"][:35] + "..."
                    else:
                        content["bot"] = edge["node"]["text"][:35] + "..."
                buffer.append(content)
            return buffer
        except Exception as e:
            raise e
    def ws_run_thread(self):
        kwargs = {}
        if self.proxy is not None:
            proxy_parsed = urlparse(self.proxy["https"])
            kwargs = {
                "proxy_type": "socks5h",
                "http_proxy_host": proxy_parsed.hostname,
                "http_proxy_port": proxy_parsed.port
            }
            logger.debug(f"socket proxy setup:{kwargs}")

        # if proxy_parsed.username and proxy_parsed.password:
        #     kwargs["http_proxy_auth"] = (proxy_parsed.username, proxy_parsed.password)
        logger.info(f"setting up wss using {kwargs}")
        self.ws.run_forever(**kwargs)

    def connect_ws(self, timeout=10):
        if self.ws_connected:
            return

        if self.ws_connecting:
            while not self.ws_connected:
                time.sleep(0.01)
                return

        self.ws_connecting = True
        self.ws_connected = False

        if self.connect_count % 5 == 0:
            self.setup_connection()

        self.connect_count += 1
        wsUri = self.get_websocket_url()
        wssHeads = {
            'Upgrade':'websocket',
            'Connection':'Upgrade',
            'Sec-WebSocket-Key': SOCKET_CHANNEL3["wss-key"],
            'Sec-WebSocket-Version':'13',
            'User-Agent':'okhttp/4.12.0',
            'Host':self.ws_domain +".tch.poe.com",
            'Accept-Encoding':'gzip'
            
        }

        ws = websocket.WebSocketApp(
        wsUri,
        header=wssHeads,
        on_message=self.on_message,
        on_open=self.on_ws_connect,
        on_error=self.on_ws_error,
        on_close=self.on_ws_close
        )

        self.ws = ws

        t = threading.Thread(target=self.ws_run_thread, daemon=True)
        t.start()

        timer = 0
        while not self.ws_connected:
            time.sleep(0.01)
            timer += 0.01
            if timer > timeout:
                self.ws_connecting = False
                self.ws_connected = False
                self.ws_error = True
                ws.close()
                raise RuntimeError("Timed out waiting for websocket to connect.")
    def get_websocket_url(self, channel=None):
        if channel is None:
            channel = self.channel
        channel = channel['tchannelData']
        query = f'?min_seq={channel["minSeq"]}&channel={channel["channel"]}&hash={channel["channelHash"]}&generation=1'
        uri = f'ws://{self.ws_domain}.tch.{channel["baseHost"]}/up/{channel["boxName"]}/updates'+query
        logger.info(f"successfully create new channel {uri}")
        return uri

    def disconnect_ws(self):
        self.ws_connecting = False
        self.ws_connected = False
        if self.ws:
            self.ws.close()

    def on_ws_connect(self, ws):
        self.ws_connecting = False
        self.ws_connected = True

    def on_ws_close(self, ws, close_status_code, close_message):
        logger.warning(f"Websocket closed with status {close_status_code}: {close_message}")
        self.ws_connecting = False
        self.ws_connected = False
        if self.ws_error:
            self.ws_error = False
            self.connect_ws()

    def on_ws_error(self, ws, error):
        self.ws_connecting = False
        self.ws_connected = False
        self.ws_error = True

    def on_message(self, ws, msg):
        try:
            
            data = json.loads(msg)
            if not "messages" in data.keys():
                return
            if self.lock:
                for message_str in data["messages"]:
                    message_data = json.loads(message_str)
                    if message_data["message_type"] == "subscriptionUpdate":
                        payload = message_data["payload"]
                        chatInfo = payload["unique_id"].split(":")
                        if chatInfo[0] == 'messageAdded':
                            message = message_data["payload"]["data"].get("messageAdded")
                            if int(chatInfo[1])== self.activeId:
                                logger.info(f"collecting related chat {self.activeId}")
                                self.active_message += message["text"][self.checkpoint:]
                                self.checkpoint = len(self.active_message)
                                if message['state'] == "complete":   
                                    logger.info(f"UNLOCKING OUTPUT")
                                    time.sleep(4)
                                    self.lock = False
                                    return
                            # else:
                                # logger.info(f"failed to match active_id={self.activeId} <-> message_id={chatInfo[1]}")

                            

                # message = message_data["payload"]["data"].get("messageAdded")
                # if message is not None:
                #     if message["state"] == "complete":
                #             return

        except Exception:
            logger.error(traceback.format_exc())
            self.disconnect_ws()
            self.connect_ws()


class GptRag:
    def __init__(self,wire:Gpt4):
        self.wire = wire

    def make_prompt(self,message:str="",context:list=[]):
        raw_context = '\n'.join(context)
        
        template = f"""
            <زمینه>
            اسم تو آناهیتا است 
            تو یک رباط هوشمند ساخته شده توسط بیمه بازار هستی
            :با خواندن این مطالب به <سوال> پاسخ کامل بده
            {raw_context}
            <پایان زمینه>
            
            
            <سوال>
            {message} 
            <پایان سوال>
            """
        logger.info(f"Invoking {template}")
        return template
    def invoke(self,chatbot:str="beaver",chatId:int=None,message:str="",context:List[Document]=[]) -> Any:
        raw_context = [x.page_content for x in context[:12]]
        template_msg = self.make_prompt(message,raw_context)
        answer,chatId = self.wire.send_message(chatbot=chatbot,chatId=chatId,message=template_msg)
        return answer,chatId
    @property
    def _llm_type(self) -> str:
        return "PoeWrapperLlm"
