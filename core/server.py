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
                
                logger.info(f"📁 Created new session: {session_id} in {SESSION_DIR} (Total: {len(self.agents)} sessions)")
            
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
        # Check if contextId is in kwargs (might be passed from A2A request context)
        if kwargs:
            context_id = kwargs.get('contextId') or kwargs.get('context_id')
            if context_id:
                logger.debug(f"Extracted session ID from kwargs: {context_id}")
                return str(context_id)
        
        # FIRST: Check if message is a list (common in A2A protocol)
        if isinstance(message, list):
            for item in message:
                if isinstance(item, dict):
                    # Check for text in dict
                    text = item.get('text', '')
                    if text:
                        match = self.SESSION_ID_PATTERN.search(str(text))
                        if match:
                            session_id = match.group(1)
                            # Clean the text
                            cleaned_text = self.CLEAN_PATTERN.sub('', str(text))
                            item['text'] = cleaned_text
                            logger.debug(f"Extracted session ID from list item text: {session_id}")
                            return session_id
                elif hasattr(item, 'text'):
                    # Check for text attribute
                    try:
                        text = getattr(item, 'text', None)
                        if text:
                            match = self.SESSION_ID_PATTERN.search(str(text))
                            if match:
                                session_id = match.group(1)
                                # Clean the text
                                cleaned_text = self.CLEAN_PATTERN.sub('', str(text))
                                item.text = cleaned_text
                                logger.debug(f"Extracted session ID from list item text attribute: {session_id}")
                                return session_id
                    except:
                        pass
        
        # SECOND: Check dict format
        if isinstance(message, dict):
            # Check for contextId at top level
            if 'contextId' in message:
                session_id = message['contextId']
                logger.debug(f"Extracted session ID from dict.contextId: {session_id}")
                return str(session_id)
            if 'context_id' in message:
                session_id = message['context_id']
                logger.debug(f"Extracted session ID from dict.context_id: {session_id}")
                return str(session_id)
            # Check for session_id at top level
            if 'session_id' in message:
                session_id = message['session_id']
                logger.debug(f"Extracted session ID from dict.session_id: {session_id}")
                return str(session_id)
            # Check parts in dict format
            if 'parts' in message:
                for part in message['parts']:
                    if isinstance(part, dict):
                        text = part.get('text', '')
                        if text:
                            match = self.SESSION_ID_PATTERN.search(text)
                            if match:
                                session_id = match.group(1)
                                part['text'] = self.CLEAN_PATTERN.sub('', text)
                                logger.debug(f"Extracted session ID from dict part text: {session_id}")
                                return session_id
        
        # THIRD: Try to extract from message attributes (object format)
        try:
            if hasattr(message, 'contextId'):
                context_id = getattr(message, 'contextId', None)
                if context_id:
                    logger.debug(f"Extracted session ID from message.contextId: {context_id}")
                    return str(context_id)
        except (AttributeError, TypeError):
            pass
            
        try:
            if hasattr(message, 'context_id'):
                context_id = getattr(message, 'context_id', None)
                if context_id:
                    logger.debug(f"Extracted session ID from message.context_id: {context_id}")
                    return str(context_id)
        except (AttributeError, TypeError):
            pass
        
        # FOURTH: Try to extract from message parts (object format)
        try:
            if hasattr(message, 'parts'):
                parts = getattr(message, 'parts', None)
                if parts:
                    for part in parts:
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
                                except Exception:
                                    pass
                                logger.debug(f"Extracted session ID from part text: {session_id}")
                                return session_id
        except (AttributeError, TypeError, IndexError):
            pass
        
        # FIFTH: Try to access message as string representation
        try:
            message_str = str(message)
            if message_str and message_str != repr(message):
                match = self.SESSION_ID_PATTERN.search(message_str)
                if match:
                    session_id = match.group(1)
                    logger.debug(f"Extracted session ID from string representation: {session_id}")
                    return session_id
        except Exception:
            pass
        
        logger.debug(f"No session ID found in message, using default: {self.default_session_id}")
        return self.default_session_id
    
    def __call__(self, message, **kwargs):
        """Handle synchronous calls - route to session-specific agent"""
        if isinstance(message, str):
            match = self.SESSION_ID_PATTERN.search(message)
            if match:
                session_id = match.group(1)
                cleaned_message = self.CLEAN_PATTERN.sub('', message)
                agent = self.session_manager.get_or_create_agent(session_id)
                return agent(cleaned_message, **kwargs)
            else:
                agent = self.session_manager.get_or_create_agent(self.default_session_id)
                return agent(message, **kwargs)
        else:
            session_id = self._extract_session_id(message, **kwargs)
            agent = self.session_manager.get_or_create_agent(session_id)
            return agent(message, **kwargs)
    
    @property
    def name(self):
        return self.session_manager.get_or_create_agent(self.default_session_id).name

    @property
    def description(self):
        return self.session_manager.get_or_create_agent(self.default_session_id).description

    @property
    def tools(self):
        return self.session_manager.get_or_create_agent(self.default_session_id).tools

    async def stream_async(self, message, **kwargs):
        """
        Stream messages asynchronously - intercept this to route to correct session
        This is the method A2A server uses for streaming responses
        """
        # Extract session ID from message (this will also clean it from message parts if found)
        session_id = self._extract_session_id(message, **kwargs)
        
        # Get or create the session-specific agent
        agent = self.session_manager.get_or_create_agent(session_id)
        
        # Call stream_async on the session-specific agent
        # Note: message has already been cleaned by _extract_session_id if session_id was in text
        async for item in agent.stream_async(message, **kwargs):
            yield item

    def __getattr__(self, name):
        """
        Delegate other attributes to default agent (for A2AServer compatibility)
        NOTE: stream_async is explicitly defined above to enable session routing
        """
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
            logger.info("Stopping A2A Server...")
            self.server = None
            self.server_thread = None
