import logging
import threading
import asyncio
import re
from pathlib import Path
from strands import Agent
from strands.multiagent.a2a import A2AServer
from strands.session.file_session_manager import FileSessionManager
from strands.agent.conversation_manager import SummarizingConversationManager
from core.config import settings

logger = logging.getLogger(__name__)

# Session Configuration
SESSION_DIR = Path(__file__).parent.parent / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

class MultiSessionManager:
    """Manages multiple agent sessions, one per user or autonomous task"""
    
    def __init__(self, agent_factory):
        self.agents = {}  # session_id -> Agent
        self.session_managers = {}  # session_id -> FileSessionManager
        self._lock = threading.Lock()
        self.agent_factory = agent_factory
    
    def get_or_create_agent(self, session_id: str) -> Agent:
        """Get or create an agent for a given session ID"""
        with self._lock:
            if session_id not in self.agents:
                # Create FileSessionManager for this session (persistence)
                # Note: FileSessionManager takes storage_dir, not session_file
                session_manager = FileSessionManager(
                    session_id=session_id,
                    storage_dir=str(SESSION_DIR)
                )
                self.session_managers[session_id] = session_manager
                
                # Create SummarizingConversationManager (context window management)
                conversation_manager = SummarizingConversationManager(
                    summary_ratio=0.4,  # Summarize 40% of messages when context reduction is needed
                    preserve_recent_messages=10,  # Always keep 10 most recent messages
                )
                
                # Create agent for this session with both managers
                agent = self.agent_factory(session_manager, conversation_manager)
                self.agents[session_id] = agent
                
                logger.info(f"📁 Created new session: {session_id} in {SESSION_DIR}")
            
            return self.agents[session_id]
    
    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        with self._lock:
            return len(self.agents)
    
    def list_session_ids(self) -> list:
        """Get list of all active session IDs"""
        with self._lock:
            return list(self.agents.keys())

class SessionAwareAgent:
    """Wrapper agent that routes requests to session-specific agents"""
    
    # Pre-compile regex patterns
    SESSION_ID_PATTERN = re.compile(r'session_id[:\s]+([a-zA-Z0-9_-]+)', re.IGNORECASE)
    CLEAN_PATTERN = re.compile(r'session_id[:\s]+[a-zA-Z0-9_-]+\s*\n?\s*', re.IGNORECASE)

    def __init__(self, session_manager: MultiSessionManager, default_session_id: str = "default"):
        self.session_manager = session_manager
        self.default_session_id = default_session_id
    
    def _extract_session_id(self, message, **kwargs) -> str:
        """Extract session_id from message or use default"""
        logger.debug(f"🔍 Extracting session ID from message type: {type(message)}")
        
        # Check if contextId is in kwargs (might be passed from A2A request context)
        if kwargs:
            context_id = kwargs.get('contextId') or kwargs.get('context_id')
            if context_id:
                logger.info(f"✅ Extracted session ID from kwargs: {context_id}")
                return str(context_id)
        
        # FIRST: Check dict format (faster, check this before attribute access)
        if isinstance(message, dict):
            # Check for contextId at top level
            if 'contextId' in message:
                session_id = message['contextId']
                logger.info(f"✅ Extracted session ID from dict.contextId: {session_id}")
                return str(session_id)
            if 'context_id' in message:
                session_id = message['context_id']
                logger.info(f"✅ Extracted session ID from dict.context_id: {session_id}")
                return str(session_id)
            # Check for session_id at top level
            if 'session_id' in message:
                session_id = message['session_id']
                logger.info(f"✅ Extracted session ID from dict.session_id: {session_id}")
                return str(session_id)
            # Check for taskId (sometimes used as session identifier)
            if 'taskId' in message:
                session_id = message['taskId']
                logger.debug(f"Found taskId in dict: {session_id}")
                # Could use taskId, but prefer other methods first
            # Check parts in dict format
            if 'parts' in message:
                for part in message['parts']:
                    if isinstance(part, dict):
                        text = part.get('text', '')
                        if text:
                            logger.debug(f"Checking dict part text for session ID: {text[:100]}...")
                            match = self.SESSION_ID_PATTERN.search(text)
                            if match:
                                session_id = match.group(1)
                                part['text'] = self.CLEAN_PATTERN.sub('', text)
                                logger.info(f"✅ Extracted session ID from dict part text: {session_id}")
                                return session_id
        
        # SECOND: Safely try to extract from message attributes (object format)
        try:
            if hasattr(message, 'contextId'):
                context_id = getattr(message, 'contextId', None)
                if context_id:
                    logger.info(f"✅ Extracted session ID from message.contextId: {context_id}")
                    return str(context_id)
        except (AttributeError, TypeError) as e:
            logger.debug(f"Error accessing message.contextId: {e}")
            pass
            
        try:
            if hasattr(message, 'context_id'):
                context_id = getattr(message, 'context_id', None)
                if context_id:
                    logger.info(f"✅ Extracted session ID from message.context_id: {context_id}")
                    return str(context_id)
        except (AttributeError, TypeError) as e:
            logger.debug(f"Error accessing message.context_id: {e}")
            pass
            
        try:
            if hasattr(message, 'taskId'):
                task_id = getattr(message, 'taskId', None)
                if task_id:
                    logger.debug(f"Found message.taskId: {task_id}")
                    # Could use taskId, but prefer other methods first
        except (AttributeError, TypeError) as e:
            logger.debug(f"Error accessing message.taskId: {e}")
            pass
        
        # THIRD: Try to extract from message parts (object format)
        try:
            if hasattr(message, 'parts'):
                parts = getattr(message, 'parts', None)
                if parts:
                    for idx, part in enumerate(parts):
                        text = None
                        # Check for direct text attribute
                        if hasattr(part, 'text'):
                            try:
                                text = getattr(part, 'text', None)
                            except:
                                pass
                        # Check for root.text (Pydantic RootModel)
                        if not text and hasattr(part, 'root'):
                            try:
                                root = getattr(part, 'root', None)
                                if root and hasattr(root, 'text'):
                                    text = getattr(root, 'text', None)
                            except:
                                pass
                        # Check for dict
                        if not text and isinstance(part, dict):
                            text = part.get('text', '')
                        
                        if text:
                            logger.debug(f"Checking part {idx} text for session ID: {text[:100]}...")
                            match = self.SESSION_ID_PATTERN.search(str(text))
                            if match:
                                session_id = match.group(1)
                                # Clean text
                                cleaned_text = self.CLEAN_PATTERN.sub('', str(text))
                                try:
                                    if hasattr(part, 'text'):
                                        part.text = cleaned_text
                                    elif hasattr(part, 'root') and hasattr(part.root, 'text'):
                                        part.root.text = cleaned_text
                                    elif isinstance(part, dict):
                                        part['text'] = cleaned_text
                                except Exception as e:
                                    logger.debug(f"Could not clean text in part: {e}")
                                logger.info(f"✅ Extracted session ID from part text: {session_id}")
                                return session_id
        except (AttributeError, TypeError, IndexError) as e:
            logger.debug(f"Error accessing message.parts: {e}")
            pass
        
        # FOURTH: Try to access message as string representation
        try:
            message_str = str(message)
            if message_str and message_str != repr(message):  # Only if it's not just object repr
                logger.debug(f"Checking message string representation for session ID: {message_str[:200]}...")
                match = self.SESSION_ID_PATTERN.search(message_str)
                if match:
                    session_id = match.group(1)
                    logger.info(f"✅ Extracted session ID from string representation: {session_id}")
                    return session_id
        except Exception as e:
            logger.debug(f"Error converting message to string: {e}")
            pass
        
        logger.warning(f"⚠️ No session ID found in message, using default: {self.default_session_id}")
        logger.debug(f"   Message type: {type(message)}, Message: {repr(message)[:200]}")
        return self.default_session_id
    
    def __call__(self, message, **kwargs):
        if isinstance(message, str):
            match = self.SESSION_ID_PATTERN.search(message)
            if match:
                session_id = match.group(1)
                cleaned_message = self.CLEAN_PATTERN.sub('', message)
                agent = self.session_manager.get_or_create_agent(session_id)
                response = agent(cleaned_message, **kwargs)
                logger.info(f"🤖 Supervisor Response (Session: {session_id}):\n{response}")
                return response
            else:
                agent = self.session_manager.get_or_create_agent(self.default_session_id)
                response = agent(message, **kwargs)
                logger.info(f"🤖 Supervisor Response (Session: {self.default_session_id}):\n{response}")
                return response
        else:
            session_id = self._extract_session_id(message, **kwargs)
            agent = self.session_manager.get_or_create_agent(session_id)
            response = agent(message, **kwargs)
            logger.info(f"🤖 Supervisor Response (Session: {session_id}):\n{response}")
            return response
    
    @property
    def name(self):
        return self.session_manager.get_or_create_agent(self.default_session_id).name

    @property
    def description(self):
        return self.session_manager.get_or_create_agent(self.default_session_id).description

    @property
    def tools(self):
        return self.session_manager.get_or_create_agent(self.default_session_id).tools

    def __getattr__(self, name):
        """Delegate other attributes to default agent (for A2AServer compatibility)"""
        default_agent = self.session_manager.get_or_create_agent(self.default_session_id)
        return getattr(default_agent, name)

class AgentServer:
    def __init__(self, agent_factory):
        self.session_manager = MultiSessionManager(agent_factory)
        self.server = None
        self.server_thread = None
        
    async def start(self):
        session_aware_agent = SessionAwareAgent(
            session_manager=self.session_manager,
            default_session_id="default"
        )
        
        # Initialize the default agent immediately so A2AServer can inspect it
        self.session_manager.get_or_create_agent("default")
        
        self.server = A2AServer(
            agent=session_aware_agent,
            host=settings.A2A_HOST,
            port=settings.A2A_PORT,
            version=settings.A2A_VERSION
        )
        
        print(f"\n🌐 A2A Server: http://{settings.A2A_HOST}:{settings.A2A_PORT}")
        print(f"   Agent Card: http://{settings.A2A_HOST}:{settings.A2A_PORT}/.well-known/agent-card.json")
        
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="a2a-server"
        )
        self.server_thread.start()
        await asyncio.sleep(1)
        
    def _run_server(self):
        try:
            self.server.serve()
        except Exception as e:
            logger.error(f"A2A server error: {e}", exc_info=True)
            
    async def stop(self):
        if self.server:
            print("🛑 Stopping A2A Server...")
            self.server = None
            self.server_thread = None
