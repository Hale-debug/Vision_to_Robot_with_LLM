import json
import time
from typing import Any, Optional

import requests

from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT


class LLMClient:
    def __init__(
        self,
        api_base: str = LLM_API_BASE,
        api_key: str = LLM_API_KEY,
        model: str = LLM_MODEL,
        timeout: float = LLM_TIMEOUT,
    ):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _build_headers(self) -> dict[str, str]:
        headers = {
            'Content-Type': 'application/json',
        }

        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        return headers

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        url = f'{self.api_base}/chat/completions'

        payload: dict[str, Any] = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': 0,
        }

        connect_timeout = 10.0  # 连接超时
        read_timeout = self.timeout  # 读取超时（从 config 获取）
        retry_delays = [1, 3]  # 退避间隔（秒）
        last_error = None

        for attempt in range(3):  # 1次原始 + 2次重试
            try:
                response = requests.post(
                    url,
                    headers=self._build_headers(),
                    json=payload,
                    timeout=(connect_timeout, read_timeout),
                )

                # HTTP 4xx 不重试（客户端错误）
                if 400 <= response.status_code < 500:
                    raise requests.HTTPError(
                        f'LLM API 返回错误 ({response.status_code}): {response.text[:200]}',
                        response=response,
                    )

                # HTTP 5xx 重试
                if response.status_code >= 500:
                    raise requests.HTTPError(
                        f'LLM API 服务器错误 ({response.status_code})',
                        response=response,
                    )

                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']

            except requests.HTTPError as e:
                status = e.response.status_code if hasattr(e, 'response') and e.response else 0
                if 400 <= status < 500:
                    # 4xx 不重试，直接抛出
                    raise
                # 5xx 或网络错误——重试
                last_error = e
                if attempt < 2:
                    delay = retry_delays[attempt]
                    print(f'LLM API 错误 (尝试 {attempt+1}/3): {e}，{delay}s后重试...')
                    time.sleep(delay)

            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = e
                if attempt < 2:
                    delay = retry_delays[attempt]
                    print(f'LLM 网络错误 (尝试 {attempt+1}/3): {e}，{delay}s后重试...')
                    time.sleep(delay)

        raise RuntimeError(
            f'LLM API 请求失败 (3次重试已用尽): {last_error}'
        ) from last_error


class RobotTaskParser:
    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    def _safe_parse_json(self, content: str) -> dict:
        """安全解析 JSON，尝试修复常见问题"""
        # 去除可能的 markdown 代码块标记
        content = content.strip()
        if content.startswith('```'):
            # 移除开头的 ```json 或 ```
            first_newline = content.find('\n')
            if first_newline != -1:
                content = content[first_newline + 1:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试修复：尾部逗号
        import re
        fixed = re.sub(r',\s*}', '}', content)
        fixed = re.sub(r',\s*]', ']', fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 尝试修复：单引号 → 双引号（简单情况）
        try:
            fixed_quotes = content.replace("'", '"')
            return json.loads(fixed_quotes)
        except json.JSONDecodeError:
            pass

        raise ValueError(f'无法解析 LLM 响应为 JSON: {content[:200]}')

    def parse_grab_command(self, command: str) -> dict[str, str]:
        color_aliases = {
            '绿色': 'green',
            '绿': 'green',
            'green': 'green',
            '橙色': 'orange',
            '橙': 'orange',
            'orange': 'orange',
            '紫色': 'purple',
            '紫': 'purple',
            'purple': 'purple',
            '粉色': 'pink',
            '粉': 'pink',
            'pink': 'pink',
            '蓝色': 'blue',
            '蓝': 'blue',
            'blue': 'blue',
            '黄色': 'yellow',
            '黄': 'yellow',
            'yellow': 'yellow',
            '红色': 'red',
            '红': 'red',
            'red': 'red',
        }

        system_prompt = (
            '你是机械臂任务解析器。'
            '你只负责把自然语言抓取和放置命令解析成JSON。'
            '输出必须是单个JSON对象，不要输出markdown，不要解释。'
            '支持物块颜色: 绿色green、橙色orange、紫色purple、粉色pink、蓝色blue、黄色yellow、红色red。'
            '支持盒子颜色: 红色red、蓝色blue、绿色green。'
            '如果识别到中文颜色，color和box_color字段必须转换为对应英文。'
            'color表示要抓取的物块颜色，box_color表示要放入的盒子颜色。'
            '如果指令没有指定盒子颜色，box_color填unknown。'
            'JSON格式: '
            '{"action":"grab","color":"green|orange|purple|pink|blue|yellow|red|unknown","box_color":"red|blue|green|unknown","target":"string"}'
        )

        user_prompt = (
            '请解析下面的机械臂抓取放置指令，并严格返回JSON对象。\n'
            f'指令: {command}'
        )

        try:
            content = self.client.chat(system_prompt, user_prompt)
        except Exception as e:
            return {
                'action': 'error',
                'color': 'unknown',
                'box_color': 'unknown',
                'target': command,
                'error': f'LLM通信失败: {e}',
            }

        if not content or not content.strip():
            return {
                'action': 'error',
                'color': 'unknown',
                'box_color': 'unknown',
                'target': command,
                'error': 'LLM返回空响应',
            }

        try:
            result = self._safe_parse_json(content)
        except ValueError as e:
            return {
                'action': 'error',
                'color': 'unknown',
                'box_color': 'unknown',
                'target': command,
                'error': f'LLM响应格式异常: {e}',
            }

        action = str(result.get('action', 'grab')).strip().lower()
        color = str(result.get('color', 'unknown')).strip().lower()
        color = color_aliases.get(color, color)
        box_color = str(result.get('box_color', 'unknown')).strip().lower()
        box_color = color_aliases.get(box_color, box_color)
        target = str(result.get('target', command)).strip()

        return {
            'action': action,
            'color': color,
            'box_color': box_color,
            'target': target,
        }
