"""
Vision Model Integration Module

Provides unified interface for multiple vision model APIs:
- OpenAI GPT-4V (Vision)
- Google Gemini Vision
- Claude 3 Vision (Anthropic)
- Ollama LLaVA (Local)
"""

import base64
import io
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import numpy as np
import requests
from PIL import Image

logger = logging.getLogger(__name__)


class VisionModelProvider(ABC):
    """Base class for vision model providers"""

    @abstractmethod
    def analyze_image(self, image: Union[np.ndarray, str, bytes], prompt: str = None) -> str:
        """
        Analyze an image and return a description.

        Args:
            image: Image as numpy array, file path, or bytes
            prompt: Custom prompt for analysis (optional)

        Returns:
            str: Description/analysis of the image
        """
        pass

    def _convert_image_to_base64(self, image: Union[np.ndarray, str, bytes]) -> str:
        """Convert various image formats to base64"""
        if isinstance(image, str):
            # File path
            with open(image, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        elif isinstance(image, np.ndarray):
            # Numpy array (BGR from OpenCV)
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            buffered = io.BytesIO()
            pil_image.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        elif isinstance(image, bytes):
            return base64.b64encode(image).decode("utf-8")
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")

    def _load_image_as_array(self, image: Union[np.ndarray, str, bytes]) -> np.ndarray:
        """Load image as numpy array (BGR format for OpenCV)"""
        if isinstance(image, np.ndarray):
            return image
        elif isinstance(image, str):
            # File path
            img = Image.open(image)
            img_array = np.array(img)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                # Convert RGB to BGR for OpenCV consistency
                return img_array[..., ::-1]
            return img_array
        elif isinstance(image, bytes):
            img = Image.open(io.BytesIO(image))
            img_array = np.array(img)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                return img_array[..., ::-1]
            return img_array
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")


class OpenAIVisionProvider(VisionModelProvider):
    """OpenAI GPT-4V Vision Provider"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.model = "gpt-4-vision-preview"
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    def analyze_image(self, image: Union[np.ndarray, str, bytes], prompt: str = None) -> str:
        """
        Analyze image using OpenAI GPT-4V

        Args:
            image: Image as numpy array, file path, or bytes
            prompt: Custom analysis prompt (default: detailed description)

        Returns:
            str: Image analysis/description
        """
        try:
            base64_image = self._convert_image_to_base64(image)
            default_prompt = (
                "Please provide a detailed description of this image. "
                "Include objects, text, activities, composition, and any notable details."
            )

            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt or default_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                        ],
                    }
                ],
                "max_tokens": 1024,
            }

            response = requests.post(self.endpoint, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            return response.json()["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing image with OpenAI: {e}")
            raise


class GoogleGeminiVisionProvider(VisionModelProvider):
    """Google Gemini Vision Provider"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        self.model = "gemini-pro-vision"
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def analyze_image(self, image: Union[np.ndarray, str, bytes], prompt: str = None) -> str:
        """
        Analyze image using Google Gemini Vision

        Args:
            image: Image as numpy array, file path, or bytes
            prompt: Custom analysis prompt (default: detailed description)

        Returns:
            str: Image analysis/description
        """
        try:
            base64_image = self._convert_image_to_base64(image)
            default_prompt = (
                "Please provide a detailed description of this image. "
                "Include objects, text, activities, composition, and any notable details."
            )

            headers = {"Content-Type": "application/json"}

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt or default_prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": base64_image,
                                }
                            },
                        ]
                    }
                ]
            }

            response = requests.post(
                f"{self.endpoint}?key={self.api_key}", json=payload, headers=headers, timeout=30
            )
            response.raise_for_status()

            return response.json()["candidates"][0]["content"]["parts"][0]["text"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Google Gemini API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing image with Google Gemini: {e}")
            raise


class AnthropicClaudeVisionProvider(VisionModelProvider):
    """Anthropic Claude 3 Vision Provider"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.model = "claude-3-opus-20240229"
        self.endpoint = "https://api.anthropic.com/v1/messages"

    def analyze_image(self, image: Union[np.ndarray, str, bytes], prompt: str = None) -> str:
        """
        Analyze image using Anthropic Claude 3 Vision

        Args:
            image: Image as numpy array, file path, or bytes
            prompt: Custom analysis prompt (default: detailed description)

        Returns:
            str: Image analysis/description
        """
        try:
            base64_image = self._convert_image_to_base64(image)
            default_prompt = (
                "Please provide a detailed description of this image. "
                "Include objects, text, activities, composition, and any notable details."
            )

            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            payload = {
                "model": self.model,
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image,
                                },
                            },
                            {"type": "text", "text": prompt or default_prompt},
                        ],
                    }
                ],
            }

            response = requests.post(self.endpoint, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            return response.json()["content"][0]["text"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing image with Claude: {e}")
            raise


class OllamaLavaVisionProvider(VisionModelProvider):
    """Local Ollama LLaVA Vision Provider"""

    def __init__(self, base_url: str = None, model: str = "llava"):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model
        self.endpoint = f"{self.base_url}/api/generate"

    def analyze_image(self, image: Union[np.ndarray, str, bytes], prompt: str = None) -> str:
        """
        Analyze image using local Ollama LLaVA

        Args:
            image: Image as numpy array, file path, or bytes
            prompt: Custom analysis prompt (default: detailed description)

        Returns:
            str: Image analysis/description
        """
        try:
            base64_image = self._convert_image_to_base64(image)
            default_prompt = (
                "Please provide a detailed description of this image. "
                "Include objects, text, activities, composition, and any notable details."
            )

            payload = {
                "model": self.model,
                "prompt": prompt or default_prompt,
                "images": [base64_image],
                "stream": False,
            }

            response = requests.post(self.endpoint, json=payload, timeout=60)
            response.raise_for_status()

            return response.json()["response"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing image with Ollama: {e}")
            raise


class VisionModelFactory:
    """Factory for creating vision model providers"""

    _providers = {
        "openai": OpenAIVisionProvider,
        "google": GoogleGeminiVisionProvider,
        "anthropic": AnthropicClaudeVisionProvider,
        "ollama": OllamaLavaVisionProvider,
    }

    @classmethod
    def create(cls, provider: str = "ollama", **kwargs) -> VisionModelProvider:
        """
        Create a vision model provider

        Args:
            provider: Provider name ('openai', 'google', 'anthropic', 'ollama')
            **kwargs: Provider-specific arguments

        Returns:
            VisionModelProvider: Initialized provider instance
        """
        provider_lower = provider.lower()
        if provider_lower not in cls._providers:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(cls._providers.keys())}")

        return cls._providers[provider_lower](**kwargs)

    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a custom vision model provider"""
        cls._providers[name.lower()] = provider_class


# Convenience function
def analyze_image(
    image: Union[np.ndarray, str, bytes],
    prompt: str = None,
    provider: str = "ollama",
    **provider_kwargs,
) -> str:
    """
    Analyze an image using specified vision model provider

    Args:
        image: Image as numpy array, file path, or bytes
        prompt: Custom analysis prompt
        provider: Vision model provider ('openai', 'google', 'anthropic', 'ollama')
        **provider_kwargs: Provider-specific arguments

    Returns:
        str: Image analysis/description

    Example:
        >>> import numpy as np
        >>> screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        >>> description = analyze_image(screen, "What's on the screen?", provider="ollama")
        >>> print(description)
    """
    vision_model = VisionModelFactory.create(provider, **provider_kwargs)
    return vision_model.analyze_image(image, prompt)
