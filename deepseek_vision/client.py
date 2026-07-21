import json
import base64
from typing import Optional, Generator, Dict, Any, List, Union

import requests

from .pow_solver import PowSolver
from .models import PowChallenge, PowSolution


BASE_URL = "https://chat.deepseek.com"

DEFAULT_HEADERS = {
    "x-client-locale": "zh_CN",
    "x-client-bundle-id": "com.deepseek.chat",
    "x-client-platform": "web",
    "x-client-version": "2.2.0",
    "x-client-timezone-offset": "28800",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "accept": "*/*",
    "referer": "https://chat.deepseek.com/",
}


class DeepSeekClient:
    """
    Pure HTTP client for DeepSeek web chat API.
    
    Usage:
        # Password login
        client = DeepSeekClient(mobile="13800138000", password="xxx")
        
        # Token import (from browser DevTools)
        client = DeepSeekClient(token="your_token_here")
        
        result = client.recognize_image("image.jpg")
        print(result)
    """

    def __init__(
        self,
        mobile: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        area_code: str = "+86",
        device_id: Optional[str] = None,
    ):
        """
        Initialize DeepSeek client.
        
        Args:
            mobile: Phone number (required if token not provided)
            password: Password (required if token not provided)
            token: Existing auth token (skips login, ~24h validity)
            area_code: Phone area code, default "+86"
            device_id: Custom device ID (auto-generated if not provided)
        """
        if not token and not (mobile and password):
            raise ValueError("Either 'token' or both 'mobile' and 'password' required")
        
        self.mobile = mobile
        self.password = password
        self.area_code = area_code
        self.device_id = device_id or self._generate_device_id()
        
        self._token: Optional[str] = token
        self._session_id: Optional[str] = None
        self._pow_solver = PowSolver()
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        
        # If token provided, set auth header immediately
        if token:
            self._session.headers["authorization"] = f"Bearer {token}"

    def __del__(self):
        """Close requests session on cleanup."""
        try:
            self._session.close()
        except Exception:
            pass

    @staticmethod
    def _generate_device_id() -> str:
        """Generate a random device ID similar to browser fingerprint"""
        import random
        import string
        chars = string.ascii_letters + string.digits + "+/"
        return "".join(random.choices(chars, k=64))

    def _auth_headers(self) -> Dict[str, str]:
        """Return headers requiring authentication"""
        return {"authorization": f"Bearer {self._token}"}

    def _get_pow_response(self, target_path: str) -> str:
        """
        Get PoW solution for a target API path.
        
        Args:
            target_path: API path to solve for (e.g., "/api/v0/chat/completion")
            
        Returns:
            Base64 encoded PoW response
        """
        # Request PoW challenge
        resp = self._session.post(
            f"{BASE_URL}/api/v0/chat/create_pow_challenge",
            json={"target_path": target_path},
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Check for API errors
        if data.get("code") != 0:
            raise RuntimeError(f"PoW challenge request failed: {data.get('msg', 'Unknown error')}")
        
        # Check for business logic errors
        biz_code = data.get("data", {}).get("biz_code")
        if biz_code is not None and biz_code != 0:
            biz_msg = data.get("data", {}).get("biz_msg", "Unknown business error")
            raise RuntimeError(f"PoW challenge business error: {biz_msg} (biz_code={biz_code})")
        
        biz_data = data.get("data", {}).get("biz_data")
        if biz_data is None:
            raise RuntimeError(f"PoW challenge response missing biz_data: {data}")
        
        challenge_data = biz_data.get("challenge")
        if challenge_data is None:
            raise RuntimeError(f"PoW challenge response missing challenge: {biz_data}")
        
        challenge = PowChallenge(
            algorithm=challenge_data["algorithm"],
            challenge=challenge_data["challenge"],
            salt=challenge_data["salt"],
            difficulty=challenge_data["difficulty"],
            expire_at=challenge_data["expire_at"],
            signature=challenge_data["signature"],
            target_path=challenge_data["target_path"],
        )
        
        solution = self._pow_solver.solve(challenge)
        return solution.to_base64()

    def login(self) -> str:
        """
        Login to DeepSeek and obtain auth token.

        Returns:
            Auth token string

        Raises:
            RuntimeError: If login fails
        """
        payload = {
            "email": "",
            "mobile": self.mobile,
            "password": self.password,
            "area_code": self.area_code,
            "device_id": self.device_id,
            "os": "web",
        }

        resp = self._session.post(
            f"{BASE_URL}/api/v0/users/login",
            json=payload,
            headers={"referer": "https://chat.deepseek.com/sign_in"},
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Login failed: {data.get('msg', 'Unknown error')}")

        biz_data = data["data"]["biz_data"]
        if biz_data.get("code") != 0:
            raise RuntimeError(f"Login failed: {biz_data.get('msg', 'Unknown error')}")

        self._token = biz_data["user"]["token"]
        self._session.headers["authorization"] = f"Bearer {self._token}"

        return self._token

    def create_session(self) -> str:
        """
        Create a new chat session.
        
        Returns:
            Session ID string
            
        Raises:
            RuntimeError: If session creation fails
        """
        # Try to get PoW response, but handle case where it's not required
        try:
            pow_response = self._get_pow_response("/api/v0/chat_session/create")
            pow_header = {"x-ds-pow-response": pow_response}
        except RuntimeError as e:
            # If PoW fails with INVALID_TARGET_PATH, try without it
            if "INVALID_TARGET_PATH" in str(e):
                pow_header = {}
            else:
                raise

        resp = self._session.post(
            f"{BASE_URL}/api/v0/chat_session/create",
            json={},
            headers={
                **self._auth_headers(),
                **pow_header,
                "x-model-type": "vision",
                "x-thinking-enabled": "0",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Create session failed: {data.get('msg', 'Unknown error')}")

        self._session_id = data["data"]["biz_data"]["chat_session"]["id"]
        return self._session_id

    def upload_image(self, file_path: str) -> str:
        """
        Upload an image file to DeepSeek.
        
        Args:
            file_path: Local path to the image file
            
        Returns:
            File ID string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If upload fails
        """
        import os
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image not found: {file_path}")

        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        pow_response = self._get_pow_response("/api/v0/file/upload_file")

        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "image/jpeg")}
            upload_headers = {
                **self._auth_headers(),
                "x-ds-pow-response": pow_response,
                "x-file-size": str(file_size),
                "x-file-type": "image/jpeg",
                "x-model-type": "vision",
                "x-thinking-enabled": "0",
            }
            resp = self._session.post(
                f"{BASE_URL}/api/v0/file/upload_file",
                files=files,
                headers=upload_headers,
            )

        if resp.status_code != 200:
            error_msg = f"Upload failed with status {resp.status_code}"
            try:
                error_data = resp.json()
                error_msg += f": {error_data}"
            except (ValueError, KeyError):
                error_msg += f": {resp.text[:500]}"
            raise RuntimeError(error_msg)
        
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Upload failed: {data.get('msg', 'Unknown error')}")

        file_id = data["data"]["biz_data"]["id"]
        
        # Wait for file to be processed
        import time
        for _ in range(30):  # Max 30 seconds
            status_resp = self._session.get(
                f"{BASE_URL}/api/v0/file/fetch_files?file_ids={file_id}",
                headers=self._auth_headers(),
            )
            status_data = status_resp.json()
            files = status_data.get("data", {}).get("biz_data", {}).get("files", [])
            if files and files[0].get("status") == "SUCCESS":
                break
            time.sleep(1)
        
        return file_id

    def _parse_sse_response(self, response: requests.Response) -> Generator[str, None, None]:
        """
        Parse SSE streaming response from chat completion.
        
        Args:
            response: Requests response object with SSE stream
            
        Yields:
            Text chunks as they arrive
        """
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue

            json_str = line[6:]  # Remove "data: " prefix
            if not json_str.strip():
                continue

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            # Check for finish first
            if data.get("p") == "response/status" and data.get("v") == "FINISHED":
                break
            
            # Skip metadata fields
            if data.get("p") and data.get("p") != "response/fragments/-1/content":
                continue

            # Handle content updates
            if "v" in data and isinstance(data["v"], str):
                yield data["v"]

            # Handle batch updates
            if data.get("o") == "BATCH" and isinstance(data.get("v"), list):
                for item in data["v"]:
                    if isinstance(item, dict) and "v" in item:
                        yield str(item["v"])

    def chat(
        self,
        file_id: str,
        prompt: str = "",
        stream: bool = False,
    ) -> Union[str, Generator[str, None, None]]:
        """
        Send a chat message with an uploaded file.
        
        Args:
            file_id: ID of the uploaded file
            prompt: Optional text prompt (empty = auto-recognize)
            stream: If True, return generator for real-time output
            
        Returns:
            Complete response text (stream=False) or generator (stream=True)
        """
        if not self._session_id:
            self.create_session()

        pow_response = self._get_pow_response("/api/v0/chat/completion")

        payload = {
            "chat_session_id": self._session_id,
            "parent_message_id": None,
            "model_type": "vision",
            "prompt": prompt,
            "ref_file_ids": [file_id],
            "thinking_enabled": False,
            "search_enabled": False,
            "action": None,
            "preempt": False,
        }

        resp = self._session.post(
            f"{BASE_URL}/api/v0/chat/completion",
            json=payload,
            headers={
                **self._auth_headers(),
                "x-ds-pow-response": pow_response,
                "x-model-type": "vision",
                "x-thinking-enabled": "0",
            },
            stream=True,
        )
        resp.raise_for_status()

        if stream:
            return self._parse_sse_response(resp)
        else:
            return "".join(self._parse_sse_response(resp))

    def recognize_image(
        self,
        file_path: str,
        prompt: str = "",
        stream: bool = False,
    ) -> Union[str, Generator[str, None, None]]:
        """
        Complete image recognition flow: login -> session -> upload -> chat.
        
        Args:
            file_path: Local path to the image file
            prompt: Optional text prompt
            stream: If True, return generator for real-time output
            
        Returns:
            Recognition result text or generator
        """
        # Login only if no token and credentials provided
        if not self._token and self.mobile and self.password:
            self.login()
        
        if not self._session_id:
            self.create_session()
        
        file_id = self.upload_image(file_path)
        return self.chat(file_id, prompt, stream=stream)
