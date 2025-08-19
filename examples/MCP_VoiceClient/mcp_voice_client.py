import asyncio
import base64
import inspect
import json
import os
import time
import uuid
import warnings
import yaml
from datetime import datetime

import pyaudio
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from aws_sdk_bedrock_runtime.models import BidirectionalInputPayloadPart, InvokeModelWithBidirectionalStreamInputChunk
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.prompts import load_mcp_prompt
from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver

# Suppress warnings
warnings.filterwarnings("ignore")

# Audio configuration
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SIZE = 1024  # Number of frames per buffer

# ============================================================================
# GLOBAL CONFIGURATION & UTILITIES
# ============================================================================

# Application constants
DEBUG = False
DEFAULT_MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"

def debug_print(message):
    """Print debug message with timestamp and function name"""
    if DEBUG:
        func_name = inspect.stack()[1].function
        if func_name in ('time_it', 'time_it_async'):
            func_name = inspect.stack()[2].function
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f'{timestamp} {func_name} {message}')

def time_it(label, method):
    """Time a synchronous method execution"""
    start = time.perf_counter()
    result = method()
    duration = time.perf_counter() - start
    debug_print(f"Execution time for {label}: {duration:.4f} seconds")
    return result

async def time_it_async(label, method):
    """Time an asynchronous method execution"""
    start = time.perf_counter()
    result = await method()
    duration = time.perf_counter() - start
    debug_print(f"Execution time for {label}: {duration:.4f} seconds")
    return result

# ============================================================================
# PROFILE MANAGEMENT
# ============================================================================

class ProfileManager:
    def __init__(self, profiles_file='profiles.yml'):
        self.profiles_file = profiles_file
        self.profiles = {}
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.profiles_path = os.path.join(self.script_dir, profiles_file)
        
    def load_profiles(self):
        """Load profiles from YAML file"""
        try:
            if os.path.exists(self.profiles_path):
                with open(self.profiles_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self.profiles = data.get('profiles', {})
                debug_print(f"Loaded {len(self.profiles)} profiles from {self.profiles_path}")
            else:
                debug_print(f"Profiles file not found: {self.profiles_path}")
        except Exception as e:
            print(f"Error loading profiles from {self.profiles_path}: {e}")
            
    def get_profile(self, profile_name):
        """Get a specific profile by name"""
        if not self.profiles:
            self.load_profiles()
            
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' not found in {self.profiles_file}")
            
        return self.profiles[profile_name]
        
    def get_profile_parameter(self, profile_name, parameter, default_value=None):
        """Get a specific parameter from a profile"""
        try:
            profile = self.get_profile(profile_name)
            return profile.get(parameter, default_value)
        except ValueError:
            return default_value
            
    def list_profiles(self):
        """List all available profiles"""
        if not self.profiles:
            self.load_profiles()
        return list(self.profiles.keys())
        
    def merge_with_args(self, profile_name, args_dict):
        """Merge profile settings with command line arguments
        Command line arguments take precedence over profile settings
        """
        if not profile_name:
            return args_dict
            
        try:
            profile = self.get_profile(profile_name)
            
            # Create merged config, profile values as base
            merged_config = profile.copy()
            
            # Override with command line arguments (non-None values)
            for key, value in args_dict.items():
                if value is not None:
                    merged_config[key] = value
                    
            return merged_config
        except ValueError as e:
            print(f"Profile error: {e}")
            return args_dict

# ============================================================================
# MCP INTEGRATION
# ============================================================================

class ToolProcessor:
    def __init__(self, mcp_server_url=DEFAULT_MCP_SERVER_URL):
        # Initialize MCP client and session
        print(f"Initializing MCP client with URL: {mcp_server_url}")
        self.mcp_client = MultiServerMCPClient({
            "mcp_server": {
                "url": mcp_server_url,
                "transport": "streamable_http"
            }
        })
        # Prepare but do not enter MCP session yet
        self.mcp_session_context = self.mcp_client.session("mcp_server")
        self.mcp_session = None
        self.mcp_tools = {}
        # ThreadPoolExecutor could be used for complex implementations
        self.tasks = {}

    async def initialize_mcp_session(self):
        """Initialize the MCP session and load tools."""
        try:
            # Enter the session context and keep it open
            self.mcp_session = await self.mcp_session_context.__aenter__()
            debug_print("MCP session context entered successfully")
        except Exception as e:
            print(f"FATAL: Could not establish MCP session. Error: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
            raise

        # Load tools
        try:
            loaded_tools = await load_mcp_tools(self.mcp_session)
            print(f"Successfully loaded {len(loaded_tools)} tools.")
        except Exception as e:
            print(f"FATAL: Could not load tools from the server. Error: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
            # Try to clean up the session before raising
            try:
                await self.mcp_session_context.__aexit__(None, None, None)
            except:
                pass
            raise

        if not loaded_tools:
            print("Fatal Error: No tools were loaded.")
            # Try to clean up the session before raising
            try:
                await self.mcp_session_context.__aexit__(None, None, None)
            except:
                pass
            raise ValueError("No MCP tools available")

        self.mcp_tools = {tool.name: tool for tool in loaded_tools}
        self.tools_context = "\n\n".join([
            f"Tool: `{tool.name}`\nDescription: {tool.description}" for tool in loaded_tools
        ])
        
        print("MCP session initialized:")
        if DEBUG:
            print(f"Available MCP tools: {list(self.mcp_tools.keys())}")
        debug_print(self.mcp_tools)

    async def process_tool_async(self, tool_name, tool_content):
        """Process a tool call asynchronously and return the result"""
        # Create a unique task ID
        task_id = str(uuid.uuid4())

        # Create and store the task
        task = asyncio.create_task(self._run_tool(tool_name, tool_content))
        self.tasks[task_id] = task

        try:
            # Wait for the task to complete
            result = await task
            return result
        finally:
            # Clean up the task reference
            if task_id in self.tasks:
                del self.tasks[task_id]

    async def _run_tool(self, tool_name, tool_content):
        """Internal method to execute the tool logic"""
        debug_print(f"Processing tool: {tool_name}")

        # Verify tool exists
        if tool_name not in self.mcp_tools:
            return {"error": f"Tool '{tool_name}' not found."}

        # Extract parameters from the toolUse event payload
        if "arguments" in tool_content:
            params = tool_content["arguments"]
        elif "content" in tool_content:
            raw = tool_content.get("content", "{}")
            try:
                params = json.loads(raw)
            except Exception as e:
                debug_print(f"Could not parse string args: {e}")
                params = {}
        else:
            # Fallback: no known key, pass entire payload (excluding toolName/toolUseId)
            params = {k: v for k, v in tool_content.items() if k not in ['toolName','toolUseId']}

        tool = self.mcp_tools[tool_name]
        print(f"Invoking tool '{tool_name}' with params: {params}")

        # Invoke via MCP adapter's ainvoke()
        try:
            raw_result = await tool.ainvoke(params)
            debug_print(f"Successfully invoked tool. Raw response: {raw_result}")
        except Exception as e:
            debug_print(f"Error invoking tool '{tool_name}': {e}")
            return {"error": f"Failed to invoke tool '{tool_name}'."}

        # Normalize result types
        if isinstance(raw_result, str):
            try:
                return json.loads(raw_result)
            except json.JSONDecodeError:
                return {"result": raw_result}
        if isinstance(raw_result, list) and raw_result and hasattr(raw_result[0], 'text'):
            text = raw_result[0].text
            try:
                return json.loads(text)
            except Exception:
                return {"result": text}
        if isinstance(raw_result, dict):
            return raw_result

        # Fallback
        return {"result": raw_result}

# ============================================================================
# BEDROCK STREAMING
# ============================================================================

class BedrockStreamManager:
    """Manages bidirectional streaming with AWS Bedrock using asyncio"""

    # Event templates
    START_SESSION_EVENT = '''{
        "event": {
            "sessionStart": {
            "inferenceConfiguration": {
                "maxTokens": 1024,
                "topP": 0.9,
                "temperature": 0.7
                }
            }
        }
    }'''

    CONTENT_START_EVENT = '''{
        "event": {
            "contentStart": {
            "promptName": "%s",
            "contentName": "%s",
            "type": "AUDIO",
            "interactive": true,
            "role": "USER",
            "audioInputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": 16000,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "audioType": "SPEECH",
                "encoding": "base64"
                }
            }
        }
    }'''

    AUDIO_EVENT_TEMPLATE = '''{
        "event": {
            "audioInput": {
            "promptName": "%s",
            "contentName": "%s",
            "content": "%s"
            }
        }
    }'''

    TEXT_CONTENT_START_EVENT = '''{
        "event": {
            "contentStart": {
            "promptName": "%s",
            "contentName": "%s",
            "type": "TEXT",
            "role": "%s",
            "interactive": true,
                "textInputConfiguration": {
                    "mediaType": "text/plain"
                }
            }
        }
    }'''

    TEXT_INPUT_EVENT = '''{
        "event": {
            "textInput": {
            "promptName": "%s",
            "contentName": "%s",
            "content": "%s"
            }
        }
    }'''

    TOOL_CONTENT_START_EVENT = '''{
        "event": {
            "contentStart": {
                "promptName": "%s",
                "contentName": "%s",
                "interactive": false,
                "type": "TOOL",
                "role": "TOOL",
                "toolResultInputConfiguration": {
                    "toolUseId": "%s",
                    "type": "TEXT",
                    "textInputConfiguration": {
                        "mediaType": "text/plain"
                    }
                }
            }
        }
    }'''

    CONTENT_END_EVENT = '''{
        "event": {
            "contentEnd": {
            "promptName": "%s",
            "contentName": "%s"
            }
        }
    }'''

    PROMPT_END_EVENT = '''{
        "event": {
            "promptEnd": {
            "promptName": "%s"
            }
        }
    }'''

    SESSION_END_EVENT = '''{
        "event": {
            "sessionEnd": {}
        }
    }'''

    def start_prompt(self):
        """Create a promptStart event"""
        # Build dynamic toolConfiguration for MCP-loaded tools
        tools_list = []
        for tool in self.tool_processor.mcp_tools.values():
            try:
                schema_dict = tool.args_schema
            except Exception:
                schema_dict = {}
            schema_json = json.dumps(schema_dict)
            #schema_obj  = schema_dict

            tools_list.append({
                "toolSpec": {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": {
                        "json": schema_json
                    }
                }
            })

        prompt_start_event = {
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {
                        "mediaType": "text/plain"
                    },
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 24000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": self.voice_id,
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    },
                    "toolUseOutputConfiguration": {
                        "mediaType": "application/json"
                    },
                    "toolConfiguration": {
                        "tools": tools_list
                    }
                }
            }
        }

        return json.dumps(prompt_start_event)

    def tool_result_event(self, content_name, content, role):
        """Create a tool result event"""

        if isinstance(content, dict):
            content_json_string = json.dumps(content)
        else:
            content_json_string = content

        tool_result_event = {
            "event": {
                "toolResult": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": content_json_string
                }
            }
        }
        return json.dumps(tool_result_event)

    def __init__(self, model_id='amazon.nova-sonic-v1:0', region='us-east-1', language='en', voice_id=None, mcp_server_url=DEFAULT_MCP_SERVER_URL, system_prompt=None, mcp_prompt=None, profile_system_prompt=None):
        """Initialize the stream manager."""
        self.model_id = model_id
        self.region = region
        self.custom_system_prompt = system_prompt  # From --system-prompt command line
        self.profile_system_prompt = profile_system_prompt  # From profile
        self.mcp_prompt = mcp_prompt
        # Language + voice selection
        self.language = (language or 'en').lower()
        voice_map = {
            'en': 'matthew',   # English (US)
            'fr': 'ambre',     # French (FR)
            'de': 'lennart',   # German (DE)
            'it': 'beatrice',  # Italian (IT)
            'es': 'carlos'     # Spanish (ES)
        }
        if voice_id is None:
            self.voice_id = voice_map.get(self.language, 'matthew')
        else:
            self.voice_id = voice_id

        # Replace RxPy subjects with asyncio queues
        self.audio_input_queue = asyncio.Queue()
        self.audio_output_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()

        self.response_task = None
        self.stream_response = None
        self.is_active = False
        self.barge_in = False
        self.bedrock_client = None

        # Audio playback components
        self.audio_player = None

        # Text response components
        self.display_assistant_text = False
        self.role = None

        # Session information
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        self.toolUseContent = ""
        self.toolUseId = ""
        self.toolName = ""

        # Add a tool processor
        self.tool_processor = ToolProcessor(mcp_server_url=mcp_server_url)

        # Add tracking for in-progress tool calls
        self.pending_tool_tasks = {}

    async def load_mcp_prompt(self, prompt_name):
        """Load a prompt from the MCP server using langchain-mcp-adapters"""
        if not prompt_name or not self.tool_processor.mcp_session:
            debug_print(f"Cannot load MCP prompt '{prompt_name}' - missing prompt name or MCP session")
            return None
            
        try:
            debug_print(f"Attempting to load MCP prompt: {prompt_name}")
            
            # Use load_mcp_prompt from langchain-mcp-adapters
            # This returns a list of LangChain messages
            prompt_messages = await load_mcp_prompt(
                session=self.tool_processor.mcp_session, 
                name=prompt_name
            )
            
            debug_print(f"MCP prompt returned {len(prompt_messages)} messages")
            
            # Convert the messages to a single system prompt string
            prompt_parts = []
            for message in prompt_messages:
                debug_print(f"Message type: {type(message)}, content: {message.content[:100]}...")
                prompt_parts.append(message.content)
            
            if prompt_parts:
                system_prompt = "\n".join(prompt_parts)
                debug_print(f"Successfully loaded MCP prompt '{prompt_name}' with {len(system_prompt)} characters")
                return system_prompt
            else:
                debug_print(f"MCP prompt '{prompt_name}' returned no content")
                return None
            
        except Exception as e:
            debug_print(f"Error loading MCP prompt '{prompt_name}': {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
            return None

    def _initialize_client(self):
        """Initialize the Bedrock client."""
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
            http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()}
        )
        self.bedrock_client = BedrockRuntimeClient(config=config)

    async def initialize_stream(self):
        """Initialize the bidirectional stream with Bedrock."""
        if not self.bedrock_client:
            self._initialize_client()

        try:
            self.stream_response = await time_it_async("invoke_model_with_bidirectional_stream", lambda : self.bedrock_client.invoke_model_with_bidirectional_stream( InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)))
            self.is_active = True
            
            # Load system prompt in order of priority: 
            # 1. --system-prompt (command line override)
            # 2. MCP prompt from server (if mcp_prompt specified)
            # 3. system_prompt from profile 
            # 4. default system prompt
            system_prompt = None
            
            if self.custom_system_prompt:
                system_prompt = self.custom_system_prompt
                debug_print("Using command line system prompt override")
                print("Using custom system prompt from command line")
            elif self.mcp_prompt:
                # Try to load MCP prompt first
                debug_print(f"Attempting to load MCP prompt: {self.mcp_prompt}")
                mcp_system_prompt = await self.load_mcp_prompt(self.mcp_prompt)
                if mcp_system_prompt:
                    system_prompt = mcp_system_prompt
                    debug_print(f"Successfully loaded MCP prompt: {self.mcp_prompt}")
                    print(f"Using MCP prompt: {self.mcp_prompt}")
                else:
                    debug_print(f"Failed to load MCP prompt '{self.mcp_prompt}', checking for profile system_prompt")
                    print(f"Warning: Could not load MCP prompt '{self.mcp_prompt}', trying profile system_prompt")
            
            # If still no system prompt, try profile system prompt, then default
            if not system_prompt and self.profile_system_prompt:
                system_prompt = self.profile_system_prompt
                debug_print("Using system prompt from profile")
                print("Using system prompt from profile")
            elif not system_prompt:
                system_prompt = "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation." \
                "When reading order numbers, please read each digit individually, separated by pauses. For example, order #1234 should be read as 'order number one-two-three-four' rather than 'order number one thousand two hundred thirty-four'." \
                "Do not share technical details of your tool interactions and do not use technical jargon or spell out technical attribute names, only the results. For example if you are using a tool to track an customer and get a <customer_key>, 'I identified the customer, it is the customer ' and then read the <customer_key> number or simply the name if you have it." \
                "Do not repeat IDs and technical details unless strictly necessary. For example, if you are in the process of investigating a customer simply say 'I am looking into the customer details...' or 'This customer has a lifetime value of...' "
                debug_print("Using default system prompt")
                print("Using default system prompt")
            
            # Append current date and language steering
            from datetime import datetime
            import time
            current_datetime = datetime.now()
            current_date = current_datetime.strftime("%Y-%m-%d")
            current_time = current_datetime.strftime("%H:%M")
            timezone_name = time.tzname[0] if time.daylight == 0 else time.tzname[1]
            
            lang_map = {
                'en': 'English',
                'fr': 'French',
                'de': 'German',
                'it': 'Italian',
                'es': 'Spanish'
            }
            selected_lang = lang_map.get(self.language, 'English')
            
            context_addition = (
                f" Today is {current_date} at {current_time} {timezone_name}."
                f" We are conversing in {selected_lang}. Respond in {selected_lang} unless the user explicitly asks for another language."
            )
            system_prompt = system_prompt + context_addition
            
            debug_print(f"Added context to system prompt: {context_addition}")
            debug_print(f"Final system prompt length: {len(system_prompt)} characters")

            # Send initialization events
            prompt_event = self.start_prompt()
            text_content_start = self.TEXT_CONTENT_START_EVENT % (self.prompt_name, self.content_name, "SYSTEM")
            
            # Debug: Log the system prompt being used
            debug_print(f"System prompt length: {len(system_prompt)}")
            debug_print(f"System prompt preview: {system_prompt[:200]}...")
            
            # Create text content event with proper JSON encoding
            import json
            text_content_dict = {
                "event": {
                    "textInput": {
                        "promptName": self.prompt_name,
                        "contentName": self.content_name,
                        "content": system_prompt
                    }
                }
            }
            text_content = json.dumps(text_content_dict)
            text_content_end = self.CONTENT_END_EVENT % (self.prompt_name, self.content_name)
            
            # Debug: Validate JSON format of text_content
            try:
                import json
                json.loads(text_content)
                debug_print("Text content JSON is valid")
            except json.JSONDecodeError as e:
                debug_print(f"Text content JSON validation failed: {e}")
                debug_print(f"Problematic JSON: {text_content[:500]}...")

            init_events = [self.START_SESSION_EVENT, prompt_event, text_content_start, text_content, text_content_end]

            for event in init_events:
                await self.send_raw_event(event)
                # Small delay between init events
                await asyncio.sleep(0.1)

            # Start listening for responses
            self.response_task = asyncio.create_task(self._process_responses())

            # Start processing audio input
            asyncio.create_task(self._process_audio_input())

            # Wait a bit to ensure everything is set up
            await asyncio.sleep(0.1)

            debug_print("Stream initialized successfully")
            return self
        except Exception as e:
            self.is_active = False
            print(f"Failed to initialize stream: {str(e)}")
            raise

    async def send_raw_event(self, event_json):
        """Send a raw event JSON to the Bedrock stream."""
        if not self.stream_response or not self.is_active:
            debug_print("Stream not initialized or closed")
            return

        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
        )

        try:
            await self.stream_response.input_stream.send(event)
            # For debugging large events, you might want to log just the type
            if DEBUG:
                if len(event_json) > 200:
                    event_type = json.loads(event_json).get("event", {}).keys()
                    if 'audioInput' not in list(event_type):
                        debug_print(f"Sent event type: {list(event_type)}")
                else:
                    debug_print(f"Sent event: {event_json}")
        except Exception as e:
            debug_print(f"Error sending event: {str(e)}")
            if DEBUG:
                import traceback
                traceback.print_exc()

    async def send_audio_content_start_event(self):
        """Send a content start event to the Bedrock stream."""
        content_start_event = self.CONTENT_START_EVENT % (self.prompt_name, self.audio_content_name)
        await self.send_raw_event(content_start_event)

    async def _process_audio_input(self):
        """Process audio input from the queue and send to Bedrock."""
        while self.is_active:
            try:
                # Get audio data from the queue
                data = await self.audio_input_queue.get()

                audio_bytes = data.get('audio_bytes')
                if not audio_bytes:
                    debug_print("No audio bytes received")
                    continue

                # Base64 encode the audio data
                blob = base64.b64encode(audio_bytes)
                audio_event = self.AUDIO_EVENT_TEMPLATE % (
                    self.prompt_name,
                    self.audio_content_name,
                    blob.decode('utf-8')
                )

                # Send the event
                await self.send_raw_event(audio_event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                debug_print(f"Error processing audio: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()

    def add_audio_chunk(self, audio_bytes):
        """Add an audio chunk to the queue."""
        self.audio_input_queue.put_nowait({
            'audio_bytes': audio_bytes,
            'prompt_name': self.prompt_name,
            'content_name': self.audio_content_name
        })

    async def send_audio_content_end_event(self):
        """Send a content end event to the Bedrock stream."""
        if not self.is_active:
            debug_print("Stream is not active")
            return

        content_end_event = self.CONTENT_END_EVENT % (self.prompt_name, self.audio_content_name)
        await self.send_raw_event(content_end_event)
        debug_print("Audio ended")

    async def send_tool_start_event(self, content_name, tool_use_id):
        """Send a tool content start event to the Bedrock stream."""
        content_start_event = self.TOOL_CONTENT_START_EVENT % (self.prompt_name, content_name, tool_use_id)
        debug_print(f"Sending tool start event: {content_start_event}")
        await self.send_raw_event(content_start_event)

    async def send_tool_result_event(self, content_name, tool_result):
        """Send a tool content event to the Bedrock stream."""
        # Use the actual tool result from processToolUse
        tool_result_event = self.tool_result_event(content_name=content_name, content=tool_result, role="TOOL")
        debug_print(f"Sending tool result event: {tool_result_event}")
        await self.send_raw_event(tool_result_event)

    async def send_tool_content_end_event(self, content_name):
        """Send a tool content end event to the Bedrock stream."""
        tool_content_end_event = self.CONTENT_END_EVENT % (self.prompt_name, content_name)
        debug_print(f"Sending tool content event: {tool_content_end_event}")
        await self.send_raw_event(tool_content_end_event)

    async def send_prompt_end_event(self):
        """Close the stream and clean up resources."""
        if not self.is_active:
            debug_print("Stream is not active")
            return

        prompt_end_event = self.PROMPT_END_EVENT % (self.prompt_name)
        await self.send_raw_event(prompt_end_event)
        debug_print("Prompt ended")

    async def send_session_end_event(self):
        """Send a session end event to the Bedrock stream."""
        if not self.is_active:
            debug_print("Stream is not active")
            return

        await self.send_raw_event(self.SESSION_END_EVENT)
        self.is_active = False
        debug_print("Session ended")

    async def _process_responses(self):
        """Process incoming responses from Bedrock."""
        try:
            while self.is_active:
                try:
                    output = await self.stream_response.await_output()
                    result = await output[1].receive()
                    if result.value and result.value.bytes_:
                        try:
                            response_data = result.value.bytes_.decode('utf-8')
                            json_data = json.loads(response_data)

                            # Handle different response types
                            if 'event' in json_data:
                                if 'completionStart' in json_data['event']:
                                    debug_print(f"completionStart: {json_data['event']}")
                                elif 'contentStart' in json_data['event']:
                                    debug_print("Content start detected")
                                    content_start = json_data['event']['contentStart']
                                    # set role
                                    self.role = content_start['role']
                                    # Check for speculative content
                                    if 'additionalModelFields' in content_start:
                                        try:
                                            additional_fields = json.loads(content_start['additionalModelFields'])
                                            if additional_fields.get('generationStage') == 'SPECULATIVE':
                                                debug_print("Speculative content detected")
                                                self.display_assistant_text = True
                                            else:
                                                self.display_assistant_text = False
                                        except json.JSONDecodeError:
                                            debug_print("Error parsing additionalModelFields")
                                elif 'textOutput' in json_data['event']:
                                    text_content = json_data['event']['textOutput']['content']
                                    role = json_data['event']['textOutput']['role']
                                    # Check if there is a barge-in
                                    if '{ "interrupted" : true }' in text_content:
                                        debug_print("Barge-in detected. Stopping audio output.")
                                        self.barge_in = True

                                    if (self.role == "ASSISTANT" and self.display_assistant_text):
                                        print(f"Assistant: {text_content}")
                                    elif (self.role == "USER"):
                                        print(f"User: {text_content}")
                                elif 'audioOutput' in json_data['event']:
                                    audio_content = json_data['event']['audioOutput']['content']
                                    audio_bytes = base64.b64decode(audio_content)
                                    await self.audio_output_queue.put(audio_bytes)
                                elif 'toolUse' in json_data['event']:
                                    self.toolUseContent = json_data['event']['toolUse']
                                    self.toolName = json_data['event']['toolUse']['toolName']
                                    self.toolUseId = json_data['event']['toolUse']['toolUseId']
                                    debug_print(f"Tool use detected: {self.toolName}, ID: {self.toolUseId}")
                                elif 'contentEnd' in json_data['event'] and json_data['event'].get('contentEnd', {}).get('type') == 'TOOL':
                                    debug_print("Processing tool use and sending result")
                                     # Start asynchronous tool processing - non-blocking
                                    self.handle_tool_request(self.toolName, self.toolUseContent, self.toolUseId)
                                    debug_print("Processing tool use asynchronously")
                                elif 'contentEnd' in json_data['event']:
                                    debug_print("Content end")
                                elif 'completionEnd' in json_data['event']:
                                    # Handle end of conversation, no more response will be generated
                                    debug_print("End of response sequence")
                                elif 'usageEvent' in json_data['event']:
                                    debug_print(f"UsageEvent: {json_data['event']}")
                            # Put the response in the output queue for other components
                            await self.output_queue.put(json_data)
                        except json.JSONDecodeError:
                            await self.output_queue.put({"raw_data": response_data})
                except StopAsyncIteration:
                    # Stream has ended
                    break
                except Exception as e:
                   # Handle ValidationException properly
                    if "ValidationException" in str(e):
                        error_message = str(e)
                        print(f"Validation error: {error_message}")
                    else:
                        print(f"Error receiving response: {e}")
                    break

        except Exception as e:
            print(f"Response processing error: {e}")
        finally:
            self.is_active = False

    def handle_tool_request(self, tool_name, tool_content, tool_use_id):
        """Handle a tool request asynchronously"""
        # Create a unique content name for this tool response
        tool_content_name = str(uuid.uuid4())

        # Create an asynchronous task for the tool execution
        task = asyncio.create_task(self._execute_tool_and_send_result(
            tool_name, tool_content, tool_use_id, tool_content_name))

        # Store the task
        self.pending_tool_tasks[tool_content_name] = task

        # Add error handling
        task.add_done_callback(
            lambda t: self._handle_tool_task_completion(t, tool_content_name))

    def _handle_tool_task_completion(self, task, content_name):
        """Handle the completion of a tool task"""
        # Remove task from pending tasks
        if content_name in self.pending_tool_tasks:
            del self.pending_tool_tasks[content_name]

        # Handle any exceptions
        if task.done() and not task.cancelled():
            exception = task.exception()
            if exception:
                debug_print(f"Tool task failed: {str(exception)}")

    async def _execute_tool_and_send_result(self, tool_name, tool_content, tool_use_id, content_name):
        """Execute a tool and send the result"""
        try:
            debug_print(f"Starting tool execution: {tool_name}")

            # Process the tool - this doesn't block the event loop
            tool_result = await self.tool_processor.process_tool_async(tool_name, tool_content)

            # Send the result sequence
            await self.send_tool_start_event(content_name, tool_use_id)
            await self.send_tool_result_event(content_name, tool_result)
            await self.send_tool_content_end_event(content_name)

            debug_print(f"Tool execution complete: {tool_name}")
        except Exception as e:
            debug_print(f"Error executing tool {tool_name}: {str(e)}")
            # Try to send an error response if possible
            try:
                error_result = {"error": f"Tool execution failed: {str(e)}"}

                await self.send_tool_start_event(content_name, tool_use_id)
                await self.send_tool_result_event(content_name, error_result)
                await self.send_tool_content_end_event(content_name)
            except Exception as send_error:
                debug_print(f"Failed to send error response: {str(send_error)}")

    async def close(self):
        """Close the stream properly."""
        if not self.is_active:
            return

        # Cancel any pending tool tasks
        for task in self.pending_tool_tasks.values():
            task.cancel()

        if self.response_task and not self.response_task.done():
            self.response_task.cancel()

        await self.send_audio_content_end_event()
        await self.send_prompt_end_event()
        await self.send_session_end_event()

        if self.stream_response:
            await self.stream_response.input_stream.close()

# ============================================================================
# AUDIO PROCESSING
# ============================================================================

class AudioStreamer:
    """Handles continuous microphone input and audio output using separate streams."""

    def __init__(self, stream_manager):
        self.stream_manager = stream_manager
        self.is_streaming = False
        self.loop = asyncio.get_event_loop()

        # Initialize PyAudio
        debug_print("AudioStreamer Initializing PyAudio...")
        self.p = time_it("AudioStreamerInitPyAudio", pyaudio.PyAudio)
        debug_print("AudioStreamer PyAudio initialized")

        # Initialize separate streams for input and output
        # Input stream with callback for microphone
        debug_print("Opening input audio stream...")
        self.input_stream = time_it("AudioStreamerOpenAudio", lambda  : self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.input_callback
        ))
        debug_print("input audio stream opened")

        # Output stream for direct writing (no callback)
        debug_print("Opening output audio stream...")
        self.output_stream = time_it("AudioStreamerOpenAudio", lambda  : self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        ))

        debug_print("output audio stream opened")

    def input_callback(self, in_data, _frame_count, _time_info, _status):
        """Callback function that schedules audio processing in the asyncio event loop"""
        if self.is_streaming and in_data:
            # Schedule the task in the event loop
            asyncio.run_coroutine_threadsafe(
                self.process_input_audio(in_data),
                self.loop
            )
        return (None, pyaudio.paContinue)

    async def process_input_audio(self, audio_data):
        """Process a single audio chunk directly"""
        try:
            # Send audio to Bedrock immediately
            self.stream_manager.add_audio_chunk(audio_data)
        except Exception as e:
            if self.is_streaming:
                print(f"Error processing input audio: {e}")

    async def play_output_audio(self):
        """Play audio responses from Nova Sonic"""
        while self.is_streaming:
            try:
                # Check for barge-in flag
                if self.stream_manager.barge_in:
                    # Clear the audio queue
                    while not self.stream_manager.audio_output_queue.empty():
                        try:
                            self.stream_manager.audio_output_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    self.stream_manager.barge_in = False
                    # Small sleep after clearing
                    await asyncio.sleep(0.05)
                    continue

                # Get audio data from the stream manager's queue
                audio_data = await asyncio.wait_for(
                    self.stream_manager.audio_output_queue.get(),
                    timeout=0.1
                )

                if audio_data and self.is_streaming:
                    # Write directly to the output stream in smaller chunks
                    chunk_size = CHUNK_SIZE  # Use the same chunk size as the stream

                    # Write the audio data in chunks to avoid blocking too long
                    for i in range(0, len(audio_data), chunk_size):
                        if not self.is_streaming:
                            break

                        end = min(i + chunk_size, len(audio_data))
                        chunk = audio_data[i:end]

                        # Create a new function that captures the chunk by value
                        def write_chunk(data):
                            return self.output_stream.write(data)

                        # Pass the chunk to the function
                        await asyncio.get_event_loop().run_in_executor(None, write_chunk, chunk)

                        # Brief yield to allow other tasks to run
                        await asyncio.sleep(0.001)

            except TimeoutError:
                # No data available within timeout, just continue
                continue
            except Exception as e:
                if self.is_streaming:
                    print(f"Error playing output audio: {str(e)}")
                    import traceback
                    traceback.print_exc()
                await asyncio.sleep(0.05)

    async def start_streaming(self):
        """Start streaming audio."""
        if self.is_streaming:
            return

        print("Starting audio streaming. Speak into your microphone...")
        print("Press Enter to stop streaming...")

        # Send audio content start event
        await time_it_async("send_audio_content_start_event", lambda : self.stream_manager.send_audio_content_start_event())

        self.is_streaming = True

        # Start the input stream if not already started
        if not self.input_stream.is_active():
            self.input_stream.start_stream()

        # Start processing tasks
        #self.input_task = asyncio.create_task(self.process_input_audio())
        self.output_task = asyncio.create_task(self.play_output_audio())

        # Wait for user to press Enter to stop (or be cancelled)
        try:
            await asyncio.get_event_loop().run_in_executor(None, input)
        except asyncio.CancelledError:
            # Exit quietly if cancelled
            pass
        finally:
            # Ensure streaming is stopped
            await self.stop_streaming()

    async def stop_streaming(self):
        """Stop streaming audio."""
        if not self.is_streaming:
            return

        self.is_streaming = False

        # Cancel the tasks
        tasks = []
        if hasattr(self, 'input_task') and not self.input_task.done():
            tasks.append(self.input_task)
        if hasattr(self, 'output_task') and not self.output_task.done():
            tasks.append(self.output_task)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        # Stop and close the streams
        if self.input_stream:
            if self.input_stream.is_active():
                self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            if self.output_stream.is_active():
                self.output_stream.stop_stream()
            self.output_stream.close()
        if self.p:
            self.p.terminate()

        await self.stream_manager.close()
        # Cleanly exit MCP session context if still open
        try:
            await self.stream_manager.tool_processor.mcp_session_context.__aexit__(None, None, None)
        except Exception:
            pass


# ============================================================================
# MAIN APPLICATION
# ============================================================================

async def main(debug=False, language='en', voice_id=None, mcp_server_url=DEFAULT_MCP_SERVER_URL, system_prompt=None, mcp_prompt=None, profile_system_prompt=None):
    """Main function to run the application."""
    global DEBUG
    DEBUG = debug

    # Create stream manager
    stream_manager = BedrockStreamManager(
        model_id='amazon.nova-sonic-v1:0', 
        region='us-east-1', 
        language=language, 
        voice_id=voice_id,
        mcp_server_url=mcp_server_url,
        system_prompt=system_prompt,
        mcp_prompt=mcp_prompt,
        profile_system_prompt=profile_system_prompt
    )

    # Create audio streamer
    audio_streamer = AudioStreamer(stream_manager)

    # Initialize MCP session and tools
    # Load the available tools from the MCP server before starting the prompt. The
    # promptStart event uses the loaded tools to configure the tool list, so we
    # need to ensure tools are loaded before calling initialize_stream().
    try:
        await stream_manager.tool_processor.initialize_mcp_session()
    except Exception as e:
        print(f"Failed to initialize MCP session: {e}")
        print("This could be due to:")
        print("  - MCP server not running or not accessible")
        print("  - Incorrect MCP server URL in profile")
        print("  - Network connectivity issues")
        return

    # Initialize the stream
    try:
        await time_it_async("initialize_stream", stream_manager.initialize_stream)
    except Exception as e:
        print(f"Failed to initialize Bedrock stream: {e}")
        return

    try:
        # This will run until the user presses Enter
        await audio_streamer.start_streaming()

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        await audio_streamer.stop_streaming()
        # Properly exit the MCP session context
        # await stream_manager.tool_processor.mcp_session_context.__aexit__(None, None, None)


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

class AppConfig:
    """Handles application configuration from command line arguments and profiles"""
    
    def __init__(self):
        self.profile_manager = ProfileManager()
        
    def parse_args(self):
        """Parse command line arguments"""
        import argparse
        parser = argparse.ArgumentParser(description='Nova Sonic Python Streaming')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode')
        parser.add_argument('--profile', default=None, help='Profile name to use from profiles.yml')
        parser.add_argument('--language', choices=['en','fr','de','it','es'], default=None, help='Interaction language used to auto-select a voice (default from profile or en).')
        parser.add_argument('--voice-id', default=None, help='Override the auto-selected voice ID. If omitted, a voice is chosen from profile or --language (en→matthew, fr→ambre, de→lennart, it→beatrice, es→carlos).')
        parser.add_argument('--mcp-server-url', default=None, help=f'MCP server URL (default from profile or {DEFAULT_MCP_SERVER_URL})')
        parser.add_argument('--system-prompt', default=None, help='Custom system prompt (overrides profile)')
        parser.add_argument('--mcp-prompt', default=None, help='MCP prompt name to load from server (overrides profile)')
        parser.add_argument('--list-profiles', action='store_true', help='List available profiles and exit')
        parser.add_argument('--list-tools', action='store_true', help='List available MCP tools and exit')
        parser.add_argument('--test-connection', action='store_true', help='Test MCP server connection and exit')
        return parser.parse_args()
        
    def get_config(self, args):
        """Get final configuration by merging args with profile"""
        args_dict = {
            'language': args.language,
            'voice_id': args.voice_id,
            'mcp_server_url': args.mcp_server_url,
            'system_prompt': args.system_prompt,
            'mcp_prompt': args.mcp_prompt
        }
        
        # Merge profile settings with command line arguments
        if args.profile:
            print(f"Using profile: {args.profile}")
            try:
                merged_config = self.profile_manager.merge_with_args(args.profile, args_dict)
            except Exception as e:
                print(f"Profile error: {e}")
                exit(1)
        else:
            merged_config = args_dict
            
        # Apply defaults and extract profile system prompt
        config = {
            'debug': args.debug,
            'language': merged_config.get('language') or 'en',
            'voice_id': merged_config.get('voice_id'),
            'mcp_server_url': merged_config.get('mcp_server_url') or DEFAULT_MCP_SERVER_URL,
            'system_prompt': merged_config.get('system_prompt'),
            'mcp_prompt': merged_config.get('mcp_prompt'),
            'profile_system_prompt': None
        }
        
        # Extract profile system prompt separately (for fallback)
        if args.profile:
            try:
                profile = self.profile_manager.get_profile(args.profile)
                config['profile_system_prompt'] = profile.get('system_prompt')
            except ValueError:
                pass
                
        return config

if __name__ == "__main__":
    app_config = AppConfig()
    args = app_config.parse_args()
    
    # Handle list profiles request
    if args.list_profiles:
        profiles = app_config.profile_manager.list_profiles()
        if profiles:
            print("Available profiles:")
            for profile in profiles:
                print(f"  - {profile}")
        else:
            print("No profiles found in profiles.yml")
        exit(0)
    
    # Handle list tools request
    if args.list_tools:
        # We need to initialize the MCP connection to list tools
        import asyncio
        
        async def list_tools():
            try:
                # Get MCP server URL from args or defaults
                mcp_server_url = args.mcp_server_url or DEFAULT_MCP_SERVER_URL
                
                # If profile is specified, get the server URL from there
                if args.profile:
                    profile_manager = ProfileManager()
                    try:
                        profile = profile_manager.get_profile(args.profile)
                        mcp_server_url = profile.get('mcp_server_url', mcp_server_url)
                    except ValueError:
                        pass
                
                print(f"Connecting to MCP server: {mcp_server_url}")
                tool_processor = ToolProcessor(mcp_server_url=mcp_server_url)
                await tool_processor.initialize_mcp_session()
                
                if tool_processor.mcp_tools:
                    print("Available MCP tools:")
                    for name, tool in tool_processor.mcp_tools.items():
                        print(f"  - {name}: {tool.description}")
                else:
                    print("No MCP tools found")
                    
                print("\nNote: MCP prompts are loaded on-demand and cannot be listed without knowing their names.")
                    
                # Clean up
                await tool_processor.mcp_session_context.__aexit__(None, None, None)
                
            except Exception as e:
                print(f"Error connecting to MCP server: {e}")
        
        asyncio.run(list_tools())
        exit(0)
    
    # Get final configuration
    config = app_config.get_config(args)
    
    # Run the main function
    try:
        asyncio.run(main(**config))
    except Exception as e:
        print(f"Application error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
