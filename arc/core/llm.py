"""
LLM integration module.
Handles loading and inference with models (LlamaCpp, Ollama, OpenAI).
"""
import logging
from typing import Optional, Any
from langchain_core.language_models import BaseChatModel
from arc.config import get_config, LLMConfig

logger = logging.getLogger(__name__)

def get_llm(config: Optional[LLMConfig] = None) -> BaseChatModel:
    """
    Factory function to get the configured LLM instance.
    """
    if config is None:
        config = get_config().llm

    logger.info(f"Initializing LLM backend: {config.backend}")

    if config.backend == "llamacpp":
        return _create_llamacpp_llm(config)
    elif config.backend == "ollama":
        return _create_ollama_llm(config)
    elif config.backend == "openai":
        return _create_openai_llm(config)
    else:
        raise ValueError(f"Unsupported LLM backend: {config.backend}")

def _create_llamacpp_llm(config: LLMConfig) -> BaseChatModel:
    """
    Create a LlamaCpp LLM instance.
    """
    try:
        from langchain_community.chat_models import ChatLlamaCpp
    except ImportError:
        raise ImportError("llama-cpp-python is required for 'llamacpp' backend.")

    if not config.model_path:
        raise ValueError("model_path is required for llamacpp backend")

    logger.info(f"Loading LlamaCpp model from: {config.model_path}")
    
    return ChatLlamaCpp(
        model_path=config.model_path,
        n_ctx=config.context_size,
        n_gpu_layers=config.gpu_layers,
        temperature=config.temperature,
        verbose=True
    )

def _create_ollama_llm(config: LLMConfig) -> BaseChatModel:
    """
    Create an Ollama LLM instance.
    """
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError("langchain-ollama is required for 'ollama' backend.")

    model_name = config.model_name or "llama3"
    base_url = config.base_url or "http://localhost:11434"
    
    logger.info(f"Connecting to Ollama at {base_url} with model {model_name}")

    return ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=config.temperature,
    )

def _create_openai_llm(config: LLMConfig) -> BaseChatModel:
    """
    Create a generic OpenAI-compatible LLM instance.
    Useful for LM Studio server or other OpenAI-compatible APIs.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("langchain-openai is required for 'openai' backend.")

    model_name = config.model_name or "local-model"
    base_url = config.base_url or "http://localhost:1234/v1" # Default to LM Studio default
    api_key = config.api_key.get_secret_value() if config.api_key else "lm-studio"

    logger.info(f"Connecting to OpenAI-compatible API at {base_url}")

    return ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=config.temperature,
    )

def test_llm(llm: Optional[BaseChatModel] = None):
    """
    Test the LLM with a simple prompt.
    """
    if llm is None:
        try:
            llm = get_llm()
        except Exception as e:
            logger.error(f"Failed to initialize LLM for testing: {e}")
            return False

    logger.info("Testing LLM connection...")
    try:
        response = llm.invoke("Hello, are you working?")
        logger.info(f"LLM Response: {response.content}")
        return True
    except Exception as e:
        logger.error(f"LLM Test failed: {e}")
        return False
