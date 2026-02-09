#!/usr/bin/env python3
"""
OLLAMA NAVIGATOR BUDDY
A reasoning-loop desktop file navigator that plans before it acts.
Built for Crimson's command center workflow.

Features:
- Dynamic Ollama model selection and refresh
- Multi-step reasoning with confidence scoring
- Plan confirmation before destructive operations
- File operations: open, navigate, modify, search, generate, append, remove, save, close, delete
- Terminal integration
"""

import sys
import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QSplitter,
    QTreeView, QTabWidget, QGroupBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QMessageBox, QProgressBar, QStatusBar,
    QMenuBar, QMenu, QToolBar, QDialog, QDialogButtonBox, QScrollArea,
    QFrame, QPlainTextEdit, QSlider, QInputDialog
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QModelIndex, QDir, QSettings, QUrl
)
from PyQt6.QtGui import (
    QAction, QFont, QColor, QPalette, QTextCursor, QSyntaxHighlighter,
    QTextCharFormat, QKeySequence, QIcon, QFileSystemModel, QPixmap, QImage
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

import requests

from Prime.foundations.crimson_theme import apply_crimson_theme


# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

class OperationType(Enum):
    """Categories of operations for confidence handling."""
    READ_ONLY = auto()      # open, navigate, search - safe
    MODIFY = auto()         # modify, append, remove, save - needs confirmation
    DESTRUCTIVE = auto()    # delete - always confirm, high threshold
    SYSTEM = auto()         # terminal commands - always confirm


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    thought: str
    action: Optional[str] = None
    confidence: float = 0.0
    requires_confirmation: bool = False


@dataclass
class ExecutionPlan:
    """The final plan after reasoning completes."""
    summary: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    overall_confidence: float = 0.0
    operation_type: OperationType = OperationType.READ_ONLY
    requires_confirmation: bool = True


# =============================================================================
# OLLAMA CLIENT
# =============================================================================

class OllamaClient:
    """Handles all Ollama API interactions."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.current_model: Optional[str] = None
    
    def list_models(self) -> List[str]:
        """Fetch available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []
    
    def generate(self, prompt: str, model: str, system: str = "", 
                 stream: bool = False) -> str:
        """Generate a response from the model."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "system": system,
                "stream": stream,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            }
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300  # 5 minutes for complex reasoning
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"Error: {e}"
    
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            requests.get(f"{self.base_url}/api/tags", timeout=2)
            return True
        except:
            return False


# =============================================================================
# REASONING ENGINE
# =============================================================================

class ReasoningEngine(QThread):
    """
    Multi-step reasoning engine that analyzes user input,
    drafts a plan, and determines confidence levels.
    """
    
    reasoning_update = pyqtSignal(str)  # Emit reasoning steps
    plan_ready = pyqtSignal(object)     # Emit final ExecutionPlan
    error_occurred = pyqtSignal(str)
    
    SYSTEM_PROMPT = """You are a file navigation and management assistant. Your role is to:
1. Analyze the user's request carefully
2. Reason through what actions are needed step by step
3. Create a clear execution plan
4. Assess your confidence in understanding the request

Available actions you can plan:
- OPEN_TERMINAL: Open a terminal window (params: path)
- NAVIGATE: Navigate to a directory (params: path)
- OPEN_FILE: Open a file for viewing/editing (params: path)
- MOVE_FILE: Move or rename a file (params: source, destination)
- COPY_FILE: Copy a file (params: source, destination)
- MODIFY_TEXT: Modify text in an open file (params: old_text, new_text)
- SEARCH_TEXT: Search for text in file(s) (params: pattern, path)
- GENERATE_TEXT: Generate new text content (params: prompt, target_path)
- APPEND_TEXT: Append text to a file (params: text, path)
- REMOVE_TEXT: Remove specific text from a file (params: text, path)
- SAVE_FILE: Save the current file (params: path)
- CLOSE_FILE: Close a file (params: path)
- DELETE_FILE: Delete a file (params: path) [DESTRUCTIVE - requires confirmation]
- DELETE_TEXT: Delete text content (params: text, path)

Respond in JSON format:
{
    "reasoning": [
        {"thought": "First, I understand the user wants to...", "confidence": 0.9},
        {"thought": "This requires me to...", "confidence": 0.95}
    ],
    "plan": {
        "summary": "Brief description of what will be done",
        "steps": [
            {"action": "ACTION_NAME", "params": {...}, "description": "Human readable step"}
        ],
        "overall_confidence": 0.95,
        "operation_type": "READ_ONLY|MODIFY|DESTRUCTIVE|SYSTEM"
    }
}

Be conservative with confidence scores. If anything is ambiguous, ask for clarification.
For destructive operations (delete), always set overall_confidence lower and flag for confirmation."""

    def __init__(self, client: OllamaClient, model: str, user_input: str,
                 context: Dict[str, Any], max_loops: int = 3,
                 confidence_threshold: float = 0.95):
        super().__init__()
        self.client = client
        self.model = model
        self.user_input = user_input
        self.context = context
        self.max_loops = max_loops
        self.confidence_threshold = confidence_threshold
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        """Execute the reasoning loop."""
        try:
            # Build context-aware prompt
            context_str = f"""
Current directory: {self.context.get('current_dir', 'Unknown')}
Open files: {', '.join(self.context.get('open_files', [])) or 'None'}
Selected item: {self.context.get('selected_item', 'None')}

User request: {self.user_input}
"""
            
            loop_count = 0
            final_plan = None
            
            while loop_count < self.max_loops and not self._cancelled:
                loop_count += 1
                self.reasoning_update.emit(f"🔄 Reasoning loop {loop_count}/{self.max_loops}...")
                
                response = self.client.generate(
                    prompt=context_str,
                    model=self.model,
                    system=self.SYSTEM_PROMPT
                )
                
                if self._cancelled:
                    return
                
                # Parse the response - flexible JSON extraction
                try:
                    parsed = self._extract_json(response)
                    
                    if parsed:
                        # Emit reasoning steps
                        for step in parsed.get("reasoning", []):
                            self.reasoning_update.emit(
                                f"💭 {step.get('thought', '')} "
                                f"(confidence: {step.get('confidence', 0):.0%})"
                            )
                        
                        plan_data = parsed.get("plan", {})
                        confidence = plan_data.get("overall_confidence", 0)
                        
                        # Check if confidence is high enough
                        if confidence >= self.confidence_threshold:
                            final_plan = self._build_plan(plan_data)
                            break
                        else:
                            self.reasoning_update.emit(
                                f"⚠️ Confidence {confidence:.0%} below threshold "
                                f"{self.confidence_threshold:.0%}, reasoning again..."
                            )
                            # Add clarification request to context
                            context_str += f"\n\nPrevious attempt confidence: {confidence:.0%}. Please be more specific or ask for clarification if needed."
                    else:
                        # Show snippet of response for debugging
                        response_preview = response[:500].replace('\n', ' ') if len(response) > 500 else response.replace('\n', ' ')
                        self.reasoning_update.emit(f"⚠️ Could not parse response.")
                        self.reasoning_update.emit(f"📄 Response preview: {response_preview}...")
                        self.reasoning_update.emit("🔄 Retrying with clearer instructions...")
                        
                        # Add explicit JSON request to context
                        context_str += "\n\nIMPORTANT: You MUST respond with valid JSON only. No extra text before or after the JSON object."
                        
                except Exception as e:
                    self.reasoning_update.emit(f"⚠️ Parse error: {e}")
                    response_preview = str(response)[:300].replace('\n', ' ')
                    self.reasoning_update.emit(f"📄 Response was: {response_preview}...")
                    self.reasoning_update.emit("🔄 Retrying...")
            
            if final_plan:
                self.plan_ready.emit(final_plan)
            else:
                # Create a clarification request plan
                clarification_plan = ExecutionPlan(
                    summary="I need more information to proceed safely.",
                    steps=[],
                    overall_confidence=0.0,
                    requires_confirmation=False
                )
                self.plan_ready.emit(clarification_plan)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _extract_json(self, response: str) -> Optional[Dict]:
        """Flexibly extract and parse JSON from LLM response."""
        import re
        
        # Strategy 1: Look for markdown code blocks (both ```json and ``` variants)
        code_block_patterns = [
            r'```json\s*({.*?})\s*```',
            r'```\s*({.*?})\s*```',
            r'`({.*?})`',
        ]
        for pattern in code_block_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    continue
        
        # Strategy 2: Find first complete JSON object with balanced braces
        json_start = response.find('{')
        if json_start != -1:
            brace_count = 0
            json_end = -1
            in_string = False
            escape_next = False
            
            for i in range(json_start, len(response)):
                char = response[i]
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
            
            if json_end > json_start:
                json_str = response[json_start:json_end]
                
                # Try direct parse
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Strategy 3: Fix common issues
                    try:
                        # Remove trailing commas before } or ]
                        fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
                        # Fix single quotes to double quotes (risky but sometimes works)
                        # fixed = fixed.replace("'", '"')
                        return json.loads(fixed)
                    except:
                        pass
        
        # Strategy 4: Try parsing entire response
        try:
            return json.loads(response.strip())
        except:
            pass
        
        # Strategy 5: Look for JSON-like structure and try to extract it
        try:
            # Sometimes models put text before/after, try to find just the object
            lines = response.split('\n')
            json_lines = []
            in_json = False
            for line in lines:
                if '{' in line and not in_json:
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if '}' in line and in_json:
                    # Try to parse accumulated lines
                    potential_json = '\n'.join(json_lines)
                    try:
                        return json.loads(potential_json)
                    except:
                        continue
        except:
            pass
        
        return None
    
    def _build_plan(self, plan_data: Dict) -> ExecutionPlan:
        """Convert parsed plan data into an ExecutionPlan object."""
        op_type_str = plan_data.get("operation_type", "READ_ONLY")
        op_type_map = {
            "READ_ONLY": OperationType.READ_ONLY,
            "MODIFY": OperationType.MODIFY,
            "DESTRUCTIVE": OperationType.DESTRUCTIVE,
            "SYSTEM": OperationType.SYSTEM,
        }
        op_type = op_type_map.get(op_type_str, OperationType.READ_ONLY)
        
        # Destructive and system operations always require confirmation
        requires_confirm = op_type in (OperationType.DESTRUCTIVE, 
                                       OperationType.SYSTEM,
                                       OperationType.MODIFY)
        
        return ExecutionPlan(
            summary=plan_data.get("summary", "No summary provided"),
            steps=plan_data.get("steps", []),
            overall_confidence=plan_data.get("overall_confidence", 0.0),
            operation_type=op_type,
            requires_confirmation=requires_confirm
        )


# =============================================================================
# PLAN EXECUTOR
# =============================================================================

class PlanExecutor:
    """Executes approved plans safely."""
    
    def __init__(self, main_window: 'NavigatorBuddy'):
        self.main_window = main_window
    
    def execute(self, plan: ExecutionPlan) -> List[str]:
        """Execute the plan steps and return results."""
        results = []
        
        for step in plan.steps:
            # Handle case where step might be a string instead of dict
            if isinstance(step, str):
                results.append(f"⚠️ Skipping malformed step: {step}")
                continue
            
            if not isinstance(step, dict):
                results.append(f"⚠️ Skipping invalid step type: {type(step)}")
                continue
            
            action = step.get("action", "")
            params = step.get("params", {})
            desc = step.get("description", action)
            
            # Normalize params - handle case where LLM returns string instead of dict
            if not isinstance(params, dict):
                # Try to convert string/primitive to dict based on action
                if action == "NAVIGATE" and isinstance(params, str):
                    params = {"path": params}
                elif action == "OPEN_FILE" and isinstance(params, str):
                    params = {"path": params}
                elif action == "CLOSE_FILE" and isinstance(params, str):
                    params = {"path": params}
                elif action == "DELETE_FILE" and isinstance(params, str):
                    params = {"path": params}
                elif action == "SAVE_FILE" and isinstance(params, str):
                    params = {"path": params}
                elif action == "SEARCH_TEXT" and isinstance(params, str):
                    params = {"pattern": params}
                elif action == "OPEN_TERMINAL" and isinstance(params, str):
                    params = {"path": params}
                else:
                    # Fallback: wrap in empty dict
                    results.append(f"⚠️ Params for {action} not a dict, got: {type(params)}")
                    params = {}
            
            try:
                result = self._execute_action(action, params)
                results.append(f"✅ {desc}: {result}")
            except Exception as e:
                results.append(f"❌ {desc}: Error - {e}")
                # Stop on error for safety
                break
        
        return results
    
    def _execute_action(self, action: str, params: Dict) -> str:
        """Execute a single action."""
        action_map = {
            "OPEN_TERMINAL": self._open_terminal,
            "NAVIGATE": self._navigate,
            "OPEN_FILE": self._open_file,
            "MOVE_FILE": self._move_file,
            "COPY_FILE": self._copy_file,
            "MODIFY_TEXT": self._modify_text,
            "SEARCH_TEXT": self._search_text,
            "GENERATE_TEXT": self._generate_text,
            "APPEND_TEXT": self._append_text,
            "REMOVE_TEXT": self._remove_text,
            "SAVE_FILE": self._save_file,
            "CLOSE_FILE": self._close_file,
            "DELETE_FILE": self._delete_file,
            "DELETE_TEXT": self._delete_text,
        }
        
        handler = action_map.get(action)
        if handler:
            return handler(params)
        else:
            return f"Unknown action: {action}"
    
    def _open_terminal(self, params: Dict) -> str:
        """Open a terminal window."""
        path = params.get("path", os.path.expanduser("~"))
        # Try common terminal emulators
        terminals = [
            ["gnome-terminal", f"--working-directory={path}"],
            ["konsole", f"--workdir={path}"],
            ["xfce4-terminal", f"--working-directory={path}"],
            ["xterm", "-e", f"cd {path} && bash"],
        ]
        for term in terminals:
            try:
                subprocess.Popen(term, start_new_session=True)
                return f"Opened terminal at {path}"
            except FileNotFoundError:
                continue
        return "Could not find a terminal emulator"
    
    def _navigate(self, params: Dict) -> str:
        """Navigate to a directory."""
        path = params.get("path", "")
        if path and os.path.isdir(path):
            self.main_window.navigate_to(path)
            return f"Navigated to {path}"
        return f"Invalid path: {path}"
    
    def _open_file(self, params: Dict) -> str:
        """Open a file in the editor."""
        path = params.get("path", "")
        if path and os.path.isfile(path):
            self.main_window.open_file(path)
            return f"Opened {path}"
        return f"File not found: {path}"
    
    def _move_file(self, params: Dict) -> str:
        """Move or rename a file."""
        source = params.get("source", "")
        destination = params.get("destination", "")
        
        if not source or not destination:
            return "Both source and destination required"
        
        # Expand paths
        source = os.path.expanduser(source)
        destination = os.path.expanduser(destination)
        
        # If destination is a directory, keep the filename
        if os.path.isdir(destination):
            destination = os.path.join(destination, os.path.basename(source))
        
        if not os.path.exists(source):
            return f"Source not found: {source}"
        
        try:
            shutil.move(source, destination)
            return f"Moved {source} → {destination}"
        except Exception as e:
            return f"Move failed: {e}"
    
    def _copy_file(self, params: Dict) -> str:
        """Copy a file."""
        source = params.get("source", "")
        destination = params.get("destination", "")
        
        if not source or not destination:
            return "Both source and destination required"
        
        # Expand paths
        source = os.path.expanduser(source)
        destination = os.path.expanduser(destination)
        
        # If destination is a directory, keep the filename
        if os.path.isdir(destination):
            destination = os.path.join(destination, os.path.basename(source))
        
        if not os.path.exists(source):
            return f"Source not found: {source}"
        
        try:
            if os.path.isfile(source):
                shutil.copy2(source, destination)
            else:
                shutil.copytree(source, destination)
            return f"Copied {source} → {destination}"
        except Exception as e:
            return f"Copy failed: {e}"
    
    def _modify_text(self, params: Dict) -> str:
        """Modify text in the current editor."""
        old_text = params.get("old_text", "")
        new_text = params.get("new_text", "")
        editor = self.main_window.get_current_editor()
        if editor:
            content = editor.toPlainText()
            if old_text in content:
                new_content = content.replace(old_text, new_text, 1)
                editor.setPlainText(new_content)
                return f"Replaced '{old_text[:30]}...' with '{new_text[:30]}...'"
            return "Text not found in current file"
        return "No file is currently open"
    
    def _search_text(self, params: Dict) -> str:
        """Search for text in files."""
        pattern = params.get("pattern", "")
        path = params.get("path", self.main_window.current_directory)
        
        results = []
        search_path = Path(path)
        
        if search_path.is_file():
            files = [search_path]
        else:
            files = list(search_path.rglob("*"))
        
        for f in files[:100]:  # Limit search
            if f.is_file():
                try:
                    content = f.read_text(errors='ignore')
                    if pattern.lower() in content.lower():
                        results.append(str(f))
                except:
                    continue
        
        if results:
            return f"Found in {len(results)} files: {', '.join(results[:5])}..."
        return "No matches found"
    
    def _generate_text(self, params: Dict) -> str:
        """Generate text using the model."""
        prompt = params.get("prompt", "")
        target = params.get("target_path", "")
        
        if not prompt:
            return "No generation prompt provided"
        
        # Use the Ollama client to generate
        generated = self.main_window.ollama_client.generate(
            prompt=prompt,
            model=self.main_window.current_model
        )
        
        if target:
            with open(target, 'w') as f:
                f.write(generated)
            return f"Generated and saved to {target}"
        else:
            editor = self.main_window.get_current_editor()
            if editor:
                editor.insertPlainText(generated)
                return "Generated and inserted into current editor"
        
        return generated[:100] + "..."
    
    def _append_text(self, params: Dict) -> str:
        """Append text to a file."""
        text = params.get("text", "")
        path = params.get("path", "")
        
        if path:
            with open(path, 'a') as f:
                f.write(text)
            return f"Appended to {path}"
        else:
            editor = self.main_window.get_current_editor()
            if editor:
                editor.appendPlainText(text)
                return "Appended to current editor"
        return "No target specified"
    
    def _remove_text(self, params: Dict) -> str:
        """Remove text from a file."""
        text = params.get("text", "")
        path = params.get("path", "")
        
        if path and os.path.isfile(path):
            content = Path(path).read_text()
            if text in content:
                new_content = content.replace(text, "", 1)
                Path(path).write_text(new_content)
                return f"Removed text from {path}"
            return "Text not found in file"
        
        editor = self.main_window.get_current_editor()
        if editor:
            content = editor.toPlainText()
            if text in content:
                editor.setPlainText(content.replace(text, "", 1))
                return "Removed text from current editor"
        return "Text not found"
    
    def _save_file(self, params: Dict) -> str:
        """Save the current file."""
        path = params.get("path", "")
        editor = self.main_window.get_current_editor()
        
        if editor and path:
            Path(path).write_text(editor.toPlainText())
            return f"Saved {path}"
        return "Nothing to save"
    
    def _close_file(self, params: Dict) -> str:
        """Close a file tab."""
        path = params.get("path", "")
        self.main_window.close_file(path)
        return f"Closed {path}"
    
    def _delete_file(self, params: Dict) -> str:
        """Delete a file (destructive!)."""
        path = params.get("path", "")
        if path and os.path.exists(path):
            if os.path.isfile(path):
                os.remove(path)
                return f"Deleted file {path}"
            elif os.path.isdir(path):
                shutil.rmtree(path)
                return f"Deleted directory {path}"
        return f"Path not found: {path}"
    
    def _delete_text(self, params: Dict) -> str:
        """Delete specific text (alias for remove_text)."""
        return self._remove_text(params)


# =============================================================================
# CONFIRMATION DIALOG
# =============================================================================

class PlanConfirmationDialog(QDialog):
    """Dialog to show and confirm execution plans."""
    
    def __init__(self, plan: ExecutionPlan, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.setWindowTitle("Confirm Execution Plan")
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Summary
        summary_label = QLabel(f"<h3>{self.plan.summary}</h3>")
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)
        
        # Confidence indicator
        confidence_pct = self.plan.overall_confidence * 100
        confidence_color = "green" if confidence_pct >= 90 else "orange" if confidence_pct >= 70 else "red"
        confidence_label = QLabel(
            f"<b>Confidence:</b> <span style='color:{confidence_color}'>{confidence_pct:.0f}%</span>"
        )
        layout.addWidget(confidence_label)
        
        # Operation type warning
        if self.plan.operation_type == OperationType.DESTRUCTIVE:
            warning = QLabel("<b style='color:red'>⚠️ DESTRUCTIVE OPERATION - This cannot be undone!</b>")
            layout.addWidget(warning)
        elif self.plan.operation_type == OperationType.MODIFY:
            warning = QLabel("<b style='color:orange'>⚠️ This will modify files.</b>")
            layout.addWidget(warning)
        
        # Steps list
        steps_group = QGroupBox("Planned Steps")
        steps_layout = QVBoxLayout(steps_group)
        
        for i, step in enumerate(self.plan.steps, 1):
            step_text = f"{i}. [{step.get('action', 'Unknown')}] {step.get('description', '')}"
            step_label = QLabel(step_text)
            step_label.setWordWrap(True)
            steps_layout.addWidget(step_label)
        
        if not self.plan.steps:
            steps_layout.addWidget(QLabel("No steps to execute - clarification may be needed."))
        
        layout.addWidget(steps_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


# =============================================================================
# MAIN WINDOW
# =============================================================================

class NavigatorBuddy(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧭 Ollama Navigator Buddy")
        self.setMinimumSize(50, 50)
        self.resize(1200, 800)
        
        # Initialize components
        self.ollama_client = OllamaClient()
        self.executor = PlanExecutor(self)
        self.current_model: Optional[str] = None
        self.current_directory = os.path.expanduser("~")
        self.open_files: Dict[str, QPlainTextEdit] = {}
        self.reasoning_thread: Optional[ReasoningEngine] = None
        
        # Settings
        self.settings = QSettings("CrimsonForge", "NavigatorBuddy")
        self.max_reasoning_loops = self.settings.value("max_loops", 50, type=int)
        self.confidence_threshold = self.settings.value("confidence", 0.95, type=float)
        self.max_execution_turns = 50
        self.task_context = {
            "original_goal": "", 
            "progress": [], 
            "attempts": 0,
            "errors": [],
            "last_error": None,
            "consecutive_errors": 0,
            "alternative_attempts": 0,
            "failed_approaches": []
        }
        
        self.setup_ui()
        self.setup_styles()
        self.refresh_models()
        self.check_ollama_status()
    
    def setup_ui(self):
        """Build the UI."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Top toolbar
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: File browser
        file_panel = self.create_file_panel()
        splitter.addWidget(file_panel)
        
        # Center panel: Editor tabs
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self.close_tab)
        splitter.addWidget(self.editor_tabs)
        
        # Right panel: Chat/Reasoning
        chat_panel = self.create_chat_panel()
        splitter.addWidget(chat_panel)
        
        splitter.setSizes([250, 500, 450])
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def create_toolbar(self) -> QWidget:
        """Create the top toolbar."""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Model selection
        layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_models)
        layout.addWidget(refresh_btn)
        
        layout.addSpacing(20)
        
        # Settings
        layout.addWidget(QLabel("Max Loops:"))
        self.loops_spin = QSpinBox()
        self.loops_spin.setRange(1, 50)
        self.loops_spin.setValue(self.max_reasoning_loops)
        self.loops_spin.valueChanged.connect(self.on_loops_changed)
        layout.addWidget(self.loops_spin)
        
        layout.addWidget(QLabel("Confidence %:"))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(50, 100)
        self.confidence_spin.setValue(self.confidence_threshold * 100)
        self.confidence_spin.setSuffix("%")
        self.confidence_spin.valueChanged.connect(self.on_confidence_changed)
        layout.addWidget(self.confidence_spin)
        
        layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("⚪ Checking...")
        layout.addWidget(self.status_indicator)
        
        return toolbar
    
    def create_file_panel(self) -> QWidget:
        """Create the file browser panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Directory navigation
        nav_layout = QHBoxLayout()
        self.path_edit = QLineEdit(self.current_directory)
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        nav_layout.addWidget(self.path_edit)
        
        up_btn = QPushButton("⬆️")
        up_btn.setFixedWidth(40)
        up_btn.clicked.connect(self.navigate_up)
        nav_layout.addWidget(up_btn)
        layout.addLayout(nav_layout)
        
        # File tree
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(self.current_directory)
        
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(self.current_directory))
        self.file_tree.setColumnWidth(0, 200)
        self.file_tree.hideColumn(1)  # Size
        self.file_tree.hideColumn(2)  # Type
        self.file_tree.hideColumn(3)  # Date
        self.file_tree.doubleClicked.connect(self.on_file_double_click)
        self.file_tree.clicked.connect(self.on_file_selected)
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_file_context_menu)
        layout.addWidget(self.file_tree)
        
        return panel
    
    def create_chat_panel(self) -> QWidget:
        """Create the chat/reasoning panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Reasoning output
        reasoning_group = QGroupBox("🧠 Reasoning")
        reasoning_layout = QVBoxLayout(reasoning_group)
        
        self.reasoning_output = QTextEdit()
        self.reasoning_output.setReadOnly(True)
        self.reasoning_output.setMaximumHeight(200)
        reasoning_layout.addWidget(self.reasoning_output)
        layout.addWidget(reasoning_group)
        
        # Chat history
        chat_group = QGroupBox("💬 Chat")
        chat_layout = QVBoxLayout(chat_group)
        
        self.chat_output = QTextEdit()
        self.chat_output.setReadOnly(True)
        chat_layout.addWidget(self.chat_output)
        layout.addWidget(chat_group)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Tell me what you want to do...")
        self.input_field.returnPressed.connect(self.process_input)
        input_layout.addWidget(self.input_field)
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.process_input)
        input_layout.addWidget(send_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_reasoning)
        self.cancel_btn.setEnabled(False)
        input_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(input_layout)
        
        return panel
    
    def setup_styles(self):
        """Apply Crimson theme styling."""
        apply_crimson_theme(self)
    
    # =========================================================================
    # OLLAMA MANAGEMENT
    # =========================================================================
    
    def check_ollama_status(self):
        """Check if Ollama is running."""
        if self.ollama_client.is_available():
            self.status_indicator.setText("🟢 Ollama Online")
        else:
            self.status_indicator.setText("🔴 Ollama Offline")
    
    def refresh_models(self):
        """Refresh the list of available models."""
        self.model_combo.clear()
        models = self.ollama_client.list_models()
        if models:
            self.model_combo.addItems(models)
            # Try to select a reasoning-capable model
            preferred = ["qwen2.5", "llama3", "mistral", "deepseek"]
            for pref in preferred:
                for model in models:
                    if pref in model.lower():
                        self.model_combo.setCurrentText(model)
                        break
        else:
            self.model_combo.addItem("No models found")
        self.check_ollama_status()
    
    def on_model_changed(self, model: str):
        """Handle model selection change."""
        self.current_model = model
        self.status_bar.showMessage(f"Selected model: {model}")
    
    def on_loops_changed(self, value: int):
        """Handle max loops setting change."""
        self.max_reasoning_loops = value
        self.settings.setValue("max_loops", value)
    
    def on_confidence_changed(self, value: float):
        """Handle confidence threshold change."""
        self.confidence_threshold = value / 100
        self.settings.setValue("confidence", self.confidence_threshold)
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    def navigate_to(self, path: str):
        """Navigate the file browser to a path."""
        if os.path.isdir(path):
            self.current_directory = path
            self.path_edit.setText(path)
            self.file_tree.setRootIndex(self.file_model.index(path))
    
    def navigate_to_path(self):
        """Navigate to the path in the path edit."""
        self.navigate_to(self.path_edit.text())
    
    def navigate_up(self):
        """Navigate to parent directory."""
        parent = os.path.dirname(self.current_directory)
        if parent:
            self.navigate_to(parent)
    
    def on_file_double_click(self, index: QModelIndex):
        """Handle double-click on file/folder."""
        path = self.file_model.filePath(index)
        if os.path.isdir(path):
            self.navigate_to(path)
        elif os.path.isfile(path):
            self.open_file(path)
    
    def on_file_selected(self, index: QModelIndex):
        """Handle file selection."""
        path = self.file_model.filePath(index)
        self.status_bar.showMessage(f"Selected: {path}")
    
    def show_file_context_menu(self, position):
        """Show right-click context menu for files."""
        index = self.file_tree.indexAt(position)
        if not index.isValid():
            return
        
        path = self.file_model.filePath(index)
        menu = QMenu()
        
        # Open with options
        if os.path.isfile(path):
            open_default = menu.addAction("🌐 Open with System Default")
            open_text = menu.addAction("📄 Open as Text")
            open_multimedia = menu.addAction("🎬 Open in Multimedia Viewer")
            menu.addSeparator()
            execute_action = menu.addAction("▶️ Execute")
            execute_terminal = menu.addAction("💻 Run in Terminal")
            menu.addSeparator()
        
        open_internal = menu.addAction("📂 Open (Internal)")
        menu.addSeparator()
        copy_path = menu.addAction("📋 Copy Path")
        
        action = menu.exec(self.file_tree.viewport().mapToGlobal(position))
        
        if action == open_internal:
            if os.path.isdir(path):
                self.navigate_to(path)
            else:
                self.open_file(path)
        elif os.path.isfile(path):
            if action == open_default:
                self.open_with_system_default(path)
            elif action == open_text:
                self._open_text(path)
            elif action == open_multimedia:
                self._open_multimedia_auto(path)
            elif action == execute_action:
                self.execute_file(path)
            elif action == execute_terminal:
                self.execute_in_terminal(path)
        
        if action == copy_path:
            clipboard = QApplication.clipboard()
            clipboard.setText(path)
    
    def open_file(self, path: str):
        """Open a file in an appropriate viewer/player."""
        if path in self.open_files:
            # Switch to existing tab
            for i in range(self.editor_tabs.count()):
                if self.editor_tabs.tabToolTip(i) == path:
                    self.editor_tabs.setCurrentIndex(i)
                    return
        
        try:
            # Detect file type
            file_ext = os.path.splitext(path)[1].lower()
            
            # Image files
            if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico']:
                self._open_image(path)
            
            # Video files
            elif file_ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']:
                self._open_video(path)
            
            # Audio files
            elif file_ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma']:
                self._open_audio(path)
            
            # Text files (default)
            else:
                self._open_text(path)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open file: {e}")
    
    def _open_multimedia_auto(self, path: str):
        """Open file in multimedia viewer based on type."""
        file_ext = os.path.splitext(path)[1].lower()
        
        if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico']:
            self._open_image(path)
        elif file_ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']:
            self._open_video(path)
        elif file_ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.wma']:
            self._open_audio(path)
        else:
            QMessageBox.information(self, "Not Multimedia", f"File is not a recognized multimedia type: {file_ext}")
    
    def open_with_system_default(self, path: str):
        """Open file with system default application."""
        try:
            # Linux: xdg-open
            subprocess.Popen(['xdg-open', path], start_new_session=True)
            self.status_bar.showMessage(f"Opening {os.path.basename(path)} with system default...")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open with system default: {e}")
    
    def execute_file(self, path: str):
        """Execute a file directly (for executables, scripts, apps)."""
        if not os.path.isfile(path):
            QMessageBox.warning(self, "Error", "Not a file")
            return
        
        # Check if executable
        if not os.access(path, os.X_OK):
            reply = QMessageBox.question(
                self, 
                "Not Executable",
                f"File is not marked as executable.\n\nMake it executable and run?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.chmod(path, os.stat(path).st_mode | 0o111)
            else:
                return
        
        try:
            # Execute in background
            subprocess.Popen([path], start_new_session=True, cwd=os.path.dirname(path))
            self.status_bar.showMessage(f"Executed: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.warning(self, "Execution Error", f"Could not execute file: {e}")
    
    def execute_in_terminal(self, path: str):
        """Execute a file in a terminal window."""
        if not os.path.isfile(path):
            return
        
        # Check if executable
        if not os.access(path, os.X_OK):
            reply = QMessageBox.question(
                self,
                "Not Executable",
                f"File is not marked as executable.\n\nMake it executable and run?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.chmod(path, os.stat(path).st_mode | 0o111)
            else:
                return
        
        dir_path = os.path.dirname(path)
        file_name = os.path.basename(path)
        
        # Try common terminal emulators with execute command
        terminals = [
            ['gnome-terminal', '--', 'bash', '-c', f'cd "{dir_path}" && ./{file_name}; read -p "Press Enter to close..."'],
            ['konsole', '-e', 'bash', '-c', f'cd "{dir_path}" && ./{file_name}; read -p "Press Enter to close..."'],
            ['xfce4-terminal', '-e', f'bash -c "cd \"{dir_path}\" && ./{file_name}; read -p \"Press Enter to close...\""'],
            ['xterm', '-e', f'bash -c "cd \"{dir_path}\" && ./{file_name}; read -p \"Press Enter to close...\""'],
        ]
        
        for term in terminals:
            try:
                subprocess.Popen(term, start_new_session=True)
                self.status_bar.showMessage(f"Running {file_name} in terminal...")
                return
            except FileNotFoundError:
                continue
        
        QMessageBox.warning(self, "Error", "Could not find a terminal emulator")
    
    def _open_text(self, path: str):
        """Open text file in editor."""
        with open(path, 'r', errors='replace') as f:
            content = f.read()
        
        editor = QPlainTextEdit()
        editor.setPlainText(content)
        editor.setFont(QFont("Monospace", 10))
        
        self.open_files[path] = editor
        tab_name = os.path.basename(path)
        idx = self.editor_tabs.addTab(editor, f"📄 {tab_name}")
        self.editor_tabs.setTabToolTip(idx, path)
        self.editor_tabs.setCurrentIndex(idx)
    
    def _open_image(self, path: str):
        """Open image file in viewer."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Scrollable image view
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        label = QLabel()
        pixmap = QPixmap(path)
        
        # Scale to reasonable size if too large
        if pixmap.width() > 1200 or pixmap.height() > 800:
            pixmap = pixmap.scaled(1200, 800, Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation)
        
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(label)
        
        layout.addWidget(scroll)
        
        # Info label
        info = QLabel(f"📐 Size: {pixmap.width()}x{pixmap.height()} | Path: {path}")
        info.setStyleSheet("color: #FFD700; padding: 5px;")
        layout.addWidget(info)
        
        self.open_files[path] = container
        tab_name = os.path.basename(path)
        idx = self.editor_tabs.addTab(container, f"🖼️ {tab_name}")
        self.editor_tabs.setTabToolTip(idx, path)
        self.editor_tabs.setCurrentIndex(idx)
    
    def _open_video(self, path: str):
        """Open video file in player."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Video widget
        video_widget = QVideoWidget()
        layout.addWidget(video_widget)
        
        # Media player
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        player.setAudioOutput(audio_output)
        player.setVideoOutput(video_widget)
        
        # Controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        play_btn = QPushButton("▶️ Play")
        pause_btn = QPushButton("⏸️ Pause")
        stop_btn = QPushButton("⏹️ Stop")
        
        volume_slider = QSlider(Qt.Orientation.Horizontal)
        volume_slider.setRange(0, 100)
        volume_slider.setValue(50)
        volume_slider.setMaximumWidth(100)
        
        position_slider = QSlider(Qt.Orientation.Horizontal)
        position_slider.setRange(0, 0)
        
        time_label = QLabel("00:00 / 00:00")
        
        controls_layout.addWidget(play_btn)
        controls_layout.addWidget(pause_btn)
        controls_layout.addWidget(stop_btn)
        controls_layout.addWidget(QLabel("🔊"))
        controls_layout.addWidget(volume_slider)
        controls_layout.addWidget(position_slider)
        controls_layout.addWidget(time_label)
        
        layout.addWidget(controls)
        
        # Connect controls
        play_btn.clicked.connect(player.play)
        pause_btn.clicked.connect(player.pause)
        stop_btn.clicked.connect(player.stop)
        volume_slider.valueChanged.connect(lambda v: audio_output.setVolume(v / 100))
        
        def update_position(position):
            position_slider.setValue(position)
            current = f"{position // 60000:02d}:{(position // 1000) % 60:02d}"
            total = f"{player.duration() // 60000:02d}:{(player.duration() // 1000) % 60:02d}"
            time_label.setText(f"{current} / {total}")
        
        def update_duration(duration):
            position_slider.setRange(0, duration)
        
        player.positionChanged.connect(update_position)
        player.durationChanged.connect(update_duration)
        position_slider.sliderMoved.connect(player.setPosition)
        
        # Load video
        player.setSource(QUrl.fromLocalFile(path))
        
        # Store references
        container.player = player
        container.audio_output = audio_output
        
        self.open_files[path] = container
        tab_name = os.path.basename(path)
        idx = self.editor_tabs.addTab(container, f"🎬 {tab_name}")
        self.editor_tabs.setTabToolTip(idx, path)
        self.editor_tabs.setCurrentIndex(idx)
    
    def _open_audio(self, path: str):
        """Open audio file in player."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Album art placeholder
        art_label = QLabel("🎵")
        art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art_label.setStyleSheet("font-size: 72px; padding: 40px;")
        layout.addWidget(art_label)
        
        # File info
        info_label = QLabel(f"<b>{os.path.basename(path)}</b><br>{path}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Media player
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        player.setAudioOutput(audio_output)
        
        # Controls
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        
        # Position slider
        position_slider = QSlider(Qt.Orientation.Horizontal)
        position_slider.setRange(0, 0)
        controls_layout.addWidget(position_slider)
        
        # Time label
        time_label = QLabel("00:00 / 00:00")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(time_label)
        
        # Button row
        button_row = QHBoxLayout()
        button_row.addStretch()
        
        play_btn = QPushButton("▶️ Play")
        pause_btn = QPushButton("⏸️ Pause")
        stop_btn = QPushButton("⏹️ Stop")
        
        button_row.addWidget(play_btn)
        button_row.addWidget(pause_btn)
        button_row.addWidget(stop_btn)
        button_row.addStretch()
        
        controls_layout.addLayout(button_row)
        
        # Volume control
        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("🔊 Volume:"))
        volume_slider = QSlider(Qt.Orientation.Horizontal)
        volume_slider.setRange(0, 100)
        volume_slider.setValue(70)
        volume_row.addWidget(volume_slider)
        controls_layout.addLayout(volume_row)
        
        layout.addWidget(controls)
        layout.addStretch()
        
        # Connect controls
        play_btn.clicked.connect(player.play)
        pause_btn.clicked.connect(player.pause)
        stop_btn.clicked.connect(player.stop)
        volume_slider.valueChanged.connect(lambda v: audio_output.setVolume(v / 100))
        
        def update_position(position):
            position_slider.setValue(position)
            current = f"{position // 60000:02d}:{(position // 1000) % 60:02d}"
            total = f"{player.duration() // 60000:02d}:{(player.duration() // 1000) % 60:02d}"
            time_label.setText(f"{current} / {total}")
        
        def update_duration(duration):
            position_slider.setRange(0, duration)
        
        player.positionChanged.connect(update_position)
        player.durationChanged.connect(update_duration)
        position_slider.sliderMoved.connect(player.setPosition)
        
        # Load audio
        player.setSource(QUrl.fromLocalFile(path))
        audio_output.setVolume(0.7)
        
        # Store references
        container.player = player
        container.audio_output = audio_output
        
        self.open_files[path] = container
        tab_name = os.path.basename(path)
        idx = self.editor_tabs.addTab(container, f"🎵 {tab_name}")
        self.editor_tabs.setTabToolTip(idx, path)
        self.editor_tabs.setCurrentIndex(idx)
    
    def close_file(self, path: str):
        """Close a file tab by path."""
        for i in range(self.editor_tabs.count()):
            if self.editor_tabs.tabToolTip(i) == path:
                self.close_tab(i)
                return
    
    def close_tab(self, index: int):
        """Close a tab by index."""
        path = self.editor_tabs.tabToolTip(index)
        if path in self.open_files:
            del self.open_files[path]
        self.editor_tabs.removeTab(index)
    
    def get_current_editor(self) -> Optional[QPlainTextEdit]:
        """Get the currently active editor."""
        widget = self.editor_tabs.currentWidget()
        if isinstance(widget, QPlainTextEdit):
            return widget
        return None
    
    def get_selected_path(self) -> Optional[str]:
        """Get the currently selected path in file browser."""
        indexes = self.file_tree.selectedIndexes()
        if indexes:
            return self.file_model.filePath(indexes[0])
        return None
    
    # =========================================================================
    # REASONING & EXECUTION
    # =========================================================================
    
    def process_input(self):
        """Process user input through the reasoning engine."""
        user_input = self.input_field.text().strip()
        if not user_input:
            return
        
        if not self.current_model or self.current_model == "No models found":
            QMessageBox.warning(self, "No Model", "Please select an Ollama model first.")
            return
        
        # Add to chat
        self.chat_output.append(f"<b>You:</b> {user_input}")
        self.input_field.clear()
        
        # Clear reasoning output
        self.reasoning_output.clear()
        self.reasoning_output.append("🔄 Starting reasoning process...")
        
        # Build context
        context = {
            "current_dir": self.current_directory,
            "open_files": list(self.open_files.keys()),
            "selected_item": self.get_selected_path(),
        }
        
        # Start reasoning thread
        self.reasoning_thread = ReasoningEngine(
            client=self.ollama_client,
            model=self.current_model,
            user_input=user_input,
            context=context,
            max_loops=self.max_reasoning_loops,
            confidence_threshold=self.confidence_threshold
        )
        
        self.reasoning_thread.reasoning_update.connect(self.on_reasoning_update)
        self.reasoning_thread.plan_ready.connect(self.on_plan_ready)
        self.reasoning_thread.error_occurred.connect(self.on_reasoning_error)
        self.reasoning_thread.finished.connect(self.on_reasoning_finished)
        
        self.input_field.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.reasoning_thread.start()
    
    def cancel_reasoning(self):
        """Cancel the current reasoning process."""
        if self.reasoning_thread and self.reasoning_thread.isRunning():
            self.reasoning_thread.cancel()
            self.reasoning_output.append("❌ Cancelled by user")
    
    def on_reasoning_update(self, message: str):
        """Handle reasoning progress updates."""
        self.reasoning_output.append(message)
    
    def on_plan_ready(self, plan: ExecutionPlan):
        """Handle completed reasoning plan."""
        self.reasoning_output.append(f"\n✅ Plan ready: {plan.summary}")
        self.reasoning_output.append(f"Confidence: {plan.overall_confidence:.0%}")
        
        if not plan.steps:
            self.chat_output.append(f"<b>Navigator:</b> {plan.summary}")
            return
        
        if plan.requires_confirmation:
            # Show confirmation dialog
            dialog = PlanConfirmationDialog(plan, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.execute_plan(plan)
            else:
                self.chat_output.append("<b>Navigator:</b> Plan cancelled.")
        else:
            # Execute directly for read-only operations
            self.execute_plan(plan)
    
    def execute_plan(self, plan: ExecutionPlan):
        """Execute an approved plan with agentic capabilities."""
        self.chat_output.append(f"<b>Navigator:</b> Executing: {plan.summary}")
        
        # Check if we should use agentic mode (for complex tasks)
        use_agentic = len(plan.steps) > 0
        
        if use_agentic:
            self.execute_agentic(plan)
        else:
            results = self.executor.execute(plan)
            for result in results:
                self.chat_output.append(f"  {result}")
            self.chat_output.append("<b>Navigator:</b> Done!")
    
    def execute_agentic(self, initial_plan: ExecutionPlan, max_turns: int = 50):
        """Execute with agentic reflection and multi-turn capability with error recovery."""
        original_goal = initial_plan.summary
        
        # Track task context for continuation
        if self.task_context["original_goal"] != original_goal:
            self.task_context = {
                "original_goal": original_goal,
                "progress": [],
                "attempts": 0,
                "subtasks": self._extract_subtasks(original_goal, initial_plan.steps),
                "errors": [],
                "last_error": None,
                "consecutive_errors": 0,
                "alternative_attempts": 0,
                "failed_approaches": [],
                "searched_directories": [],
                "last_action": None,
                "action_repeat_count": 0
            }
        
        self.task_context["attempts"] += 1
        turn_count = 0
        max_alternative_attempts = 5  # Give up after 5 different approaches fail
        
        # Execute initial plan steps with error tracking
        results = self.executor.execute(initial_plan)
        has_error = False
        for i, result in enumerate(results):
            self.chat_output.append(f"  {result}")
            
            # Track directory navigation to detect loops
            if i < len(initial_plan.steps):
                step = initial_plan.steps[i]
                action = step.get('action', '')
                if action == 'NAVIGATE':
                    params = step.get('params', {})
                    # Handle case where params might be a string instead of dict
                    if isinstance(params, dict):
                        path = params.get('path', '')
                    elif isinstance(params, str):
                        path = params
                    else:
                        path = ''
                    
                    if path:
                        self.task_context['searched_directories'].append(path)
            
            if "❌" in result or "Error" in result:
                has_error = True
                self._track_error(result)
        
        # If error occurred, check for retry or alternative approach
        if has_error:
            retry_result = self._handle_execution_error(original_goal, initial_plan)
            if retry_result == "retry":
                # Reset turn counter and retry from beginning
                self.chat_output.append("<i>🔄 Error detected - resetting and retrying...</i>")
                return self.execute_agentic(initial_plan, max_turns)
            elif retry_result == "alternative":
                # Generate and try alternative approach
                alt_plan = self._generate_alternative_plan(original_goal, initial_plan)
                if alt_plan:
                    self.chat_output.append("<i>🔀 Trying alternative approach...</i>")
                    return self.execute_agentic(alt_plan, max_turns)
                else:
                    self.chat_output.append("<b>❌ Task appears impossible - could not generate alternative approach.</b>")
                    return
            elif retry_result == "impossible":
                self.chat_output.append("<b>❌ Task appears impossible after multiple failed attempts.</b>")
                self._reset_task_context()
                return
        
        turn_count += 1
        
        # Reflection loop
        while turn_count < max_turns:
            self.chat_output.append(f"<i>🔍 Turn {turn_count}/{max_turns}: Checking if goal achieved...</i>")
            
            # Ask model to verify if goal is complete - WITH DETAILED SUBTASK CHECKING
            subtasks_status = "\n".join([f"  {i+1}. {st['description']} - {st.get('status', 'pending')}" 
                                         for i, st in enumerate(self.task_context.get('subtasks', []))])
            progress_log = "\n".join([f"  - {p}" for p in self.task_context.get('progress', [])])
            
            # Add searched directories info to prevent loops
            searched_dirs = self.task_context.get('searched_directories', [])
            searched_dirs_str = "\n".join([f"  - {d}" for d in searched_dirs[-10:]]) if searched_dirs else "  (None yet)"
            
            # Detect if we're in a navigation loop
            loop_warning = ""
            if len(searched_dirs) > 3:
                recent_dirs = searched_dirs[-3:]
                if len(set(recent_dirs)) < len(recent_dirs):  # Repeated directory
                    loop_warning = "\n\n🚨 NAVIGATION LOOP DETECTED! You have searched the same directory multiple times. You MUST try a DIFFERENT approach:\n- Use SEARCH_TEXT to find the file across the system\n- Try parent directories or common locations\n- Check if the file actually exists\n- Consider that the file might have a different name\n"
            
            verification_prompt = f"""
Original goal: {original_goal}

Subtasks to complete:
{subtasks_status if subtasks_status else '  (No subtasks defined)'}

Progress so far:
{progress_log if progress_log else '  (No actions yet)'}

Current state:
- Directory: {self.current_directory}
- Open files: {list(self.open_files.keys())}
- Turn: {turn_count + 1}/{max_turns}

Already searched directories (DO NOT search these again):
{searched_dirs_str}{loop_warning}

CRITICAL RULES:
1. Check EACH subtask individually - goal is only complete when ALL subtasks are done
2. DO NOT navigate to directories already searched
3. If looking for a file, try DIFFERENT locations or use SEARCH_TEXT
4. If file not found after 2-3 directory checks, use SEARCH_TEXT action instead

Respond with JSON:
{{
    "complete": true/false,
    "subtasks_status": {{
        "subtask_1": "complete/incomplete/not_started",
        "subtask_2": "complete/incomplete/not_started",
        ...
    }},
    "reasoning": "detailed explanation of what's been done and what remains",
    "next_action": {{
        "action": "ACTION_NAME",
        "params": {{...}},
        "description": "what to do next"
    }}
}}

Only set complete=true if ALL subtasks are verified complete. If ANY subtask remains, provide the next_action.
"""
            
            try:
                response = self.ollama_client.generate(
                    prompt=verification_prompt,
                    model=self.current_model,
                    system="You are a task verification assistant. Check if goals are achieved."
                )
                
                # Parse response
                from PyQt6.QtCore import QThread
                temp_engine = ReasoningEngine(self.ollama_client, self.current_model, "", {}, 1, 0.5)
                verification = temp_engine._extract_json(response)
                
                if not verification:
                    self.chat_output.append("<i>⚠️ Could not verify status, stopping.</i>")
                    break
                
                is_complete = verification.get("complete", False)
                reasoning = verification.get("reasoning", "")
                subtasks_status = verification.get("subtasks_status", {})
                
                # Update subtask status
                for idx, status in subtasks_status.items():
                    task_num = int(idx.split('_')[1]) - 1 if '_' in idx else 0
                    if task_num < len(self.task_context.get('subtasks', [])):
                        self.task_context['subtasks'][task_num]['status'] = status
                
                self.chat_output.append(f"<i>💭 {reasoning}</i>")
                
                if is_complete:
                    # Double-check: verify ALL subtasks marked complete
                    all_complete = all(
                        st.get('status') == 'complete' 
                        for st in self.task_context.get('subtasks', [])
                    )
                    if all_complete or not self.task_context.get('subtasks'):
                        self.chat_output.append("<b>✅ Goal achieved! All subtasks complete.</b>")
                        self._reset_task_context()
                        break
                    else:
                        # Model thinks it's done but subtasks remain
                        incomplete = [st for st in self.task_context.get('subtasks', []) 
                                    if st.get('status') != 'complete']
                        self.chat_output.append(f"<i>⚠️ Verification inconsistency: {len(incomplete)} subtask(s) still incomplete. Continuing...</i>")
                        is_complete = False
                
                # Execute next action
                next_action = verification.get("next_action", {})
                if not next_action or not next_action.get("action"):
                    self.chat_output.append("<i>⚠️ No next action provided, stopping.</i>")
                    break
                
                action = next_action.get("action", "")
                params = next_action.get("params", {})
                desc = next_action.get("description", action)
                
                # Detect action loops (same action repeated)
                current_action_sig = f"{action}:{params}"
                if self.task_context.get('last_action') == current_action_sig:
                    self.task_context['action_repeat_count'] += 1
                    if self.task_context['action_repeat_count'] >= 3:
                        # Same action 3 times in a row - force alternative
                        self.chat_output.append("<i>⚠️ Action loop detected - generating alternative strategy...</i>")
                        alt_plan = self._generate_alternative_plan(original_goal, initial_plan)
                        if alt_plan:
                            return self.execute_agentic(alt_plan, max_turns)
                        else:
                            self.chat_output.append("<b>❌ Cannot proceed - stuck in action loop.</b>")
                            break
                else:
                    self.task_context['last_action'] = current_action_sig
                    self.task_context['action_repeat_count'] = 1
                
                # Track directory navigation
                if action == 'NAVIGATE':
                    nav_path = params.get('path', '')
                    if nav_path:
                        self.task_context['searched_directories'].append(nav_path)
                        # Check if we're revisiting same directory
                        if self.task_context['searched_directories'].count(nav_path) > 2:
                            self.chat_output.append(f"<i>⚠️ Warning: Already searched {nav_path} multiple times. Consider using SEARCH_TEXT instead.</i>")
                
                # Normalize params if needed
                if not isinstance(params, dict):
                    if action in ["NAVIGATE", "OPEN_FILE", "DELETE_FILE"] and isinstance(params, str):
                        params = {"path": params}
                    elif action == "MOVE_FILE" and isinstance(params, str):
                        # Try to parse "source dest" format
                        parts = params.split()
                        if len(parts) >= 2:
                            params = {"source": parts[0], "destination": " ".join(parts[1:])}
                    else:
                        params = {}
                
                try:
                    result = self.executor._execute_action(action, params)
                    self.chat_output.append(f"  ✅ {desc}: {result}")
                except Exception as e:
                    self.chat_output.append(f"  ❌ {desc}: {e}")
                    break
                
                turn_count += 1
                
            except Exception as e:
                self.chat_output.append(f"<i>❌ Verification error: {e}</i>")
                break
        
        if turn_count >= max_turns:
            self.chat_output.append(f"<b>⏱️ Reached max turns ({max_turns})</b>")
            
            # Check if task is actually complete
            incomplete_subtasks = [st for st in self.task_context.get('subtasks', []) 
                                  if st.get('status') != 'complete']
            
            if incomplete_subtasks:
                # Task not complete - offer to continue
                self.offer_task_continuation(original_goal, incomplete_subtasks)
                return
        
        self.chat_output.append("<b>Navigator:</b> Done!")
    
    def on_reasoning_error(self, error: str):
        """Handle reasoning errors."""
        self.reasoning_output.append(f"❌ Error: {error}")
        self.chat_output.append(f"<b>Navigator:</b> Sorry, something went wrong: {error}")
    
    def on_reasoning_finished(self):
        """Clean up after reasoning completes."""
        self.input_field.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.reasoning_thread = None
    
    def _extract_subtasks(self, goal: str, steps: List[Dict]) -> List[Dict]:
        """Extract subtasks from goal and plan steps."""
        subtasks = []
        
        # Add each step as a subtask
        for i, step in enumerate(steps, 1):
            subtasks.append({
                "id": i,
                "description": step.get("description", step.get("action", f"Step {i}")),
                "status": "not_started"
            })
        
        return subtasks
    
    def _track_error(self, error_msg: str):
        """Track errors for recovery decision making."""
        # Extract core error (ignore timestamps, specific paths, etc.)
        core_error = error_msg.split(":")[-1].strip() if ":" in error_msg else error_msg
        
        self.task_context['errors'].append(error_msg)
        
        # Check if same error as last time
        if self.task_context['last_error'] == core_error:
            self.task_context['consecutive_errors'] += 1
        else:
            self.task_context['consecutive_errors'] = 1
            self.task_context['last_error'] = core_error
    
    def _handle_execution_error(self, goal: str, plan: ExecutionPlan) -> str:
        """Decide how to handle execution error. Returns: 'retry', 'alternative', 'impossible', or 'stop'."""
        consecutive = self.task_context['consecutive_errors']
        alt_attempts = self.task_context['alternative_attempts']
        
        # If same error 3+ times, try alternative approach
        if consecutive >= 3:
            if alt_attempts >= 5:
                # Already tried 5 different approaches - give up
                return "impossible"
            else:
                # Try different approach
                return "alternative"
        
        # If less than 3 consecutive errors, simple retry with reset counter
        if consecutive < 3:
            return "retry"
        
        return "stop"
    
    def _generate_alternative_plan(self, goal: str, failed_plan: ExecutionPlan) -> Optional[ExecutionPlan]:
        """Generate an alternative approach when current plan keeps failing."""
        self.task_context['alternative_attempts'] += 1
        
        # Record failed approach
        failed_approach = {
            "summary": failed_plan.summary,
            "steps": [step.get('action', 'Unknown') for step in failed_plan.steps],
            "error": self.task_context['last_error']
        }
        self.task_context['failed_approaches'].append(failed_approach)
        
        # Build prompt for alternative approach
        failed_approaches_str = "\n".join([
            f"  Attempt {i+1}: {approach['summary']} - Failed with: {approach['error']}"
            for i, approach in enumerate(self.task_context['failed_approaches'])
        ])
        
        alternative_prompt = f"""
ORIGINAL GOAL: {goal}

PREVIOUS FAILED APPROACHES:
{failed_approaches_str}

CRITICAL: These approaches have all failed. You MUST try a completely different method.
Consider:
- Different file paths or locations
- Different actions or tools
- Breaking the task into smaller steps
- Checking prerequisites first
- Using alternative commands or methods

Generate a NEW plan with a DIFFERENT approach. Do NOT repeat failed methods.
"""
        
        try:
            self.chat_output.append(f"<i>🔍 Analyzing failures and generating alternative approach (attempt {self.task_context['alternative_attempts']}/5)...</i>")
            
            response = self.ollama_client.generate(
                prompt=alternative_prompt,
                model=self.current_model,
                system=ReasoningEngine.SYSTEM_PROMPT
            )
            
            # Parse response
            temp_engine = ReasoningEngine(self.ollama_client, self.current_model, "", {}, 1, 0.5)
            parsed = temp_engine._extract_json(response)
            
            if parsed and 'plan' in parsed:
                plan_data = parsed['plan']
                alternative_plan = temp_engine._build_plan(plan_data)
                self.chat_output.append(f"<i>✅ Generated alternative: {alternative_plan.summary}</i>")
                return alternative_plan
            else:
                self.chat_output.append("<i>⚠️ Could not parse alternative plan</i>")
                return None
                
        except Exception as e:
            self.chat_output.append(f"<i>❌ Error generating alternative: {e}</i>")
            return None
    
    def _reset_task_context(self):
        """Reset task context after completion or failure."""
        self.task_context = {
            "original_goal": "", 
            "progress": [], 
            "attempts": 0,
            "errors": [],
            "last_error": None,
            "consecutive_errors": 0,
            "alternative_attempts": 0,
            "failed_approaches": [],
            "searched_directories": [],
            "last_action": None,
            "action_repeat_count": 0
        }
    
    def offer_task_continuation(self, original_goal: str, incomplete_subtasks: List[Dict]):
        """Prompt user to continue incomplete task."""
        incomplete_list = "\n".join([f"  • {st['description']}" for st in incomplete_subtasks])
        
        # Show error stats if there were errors
        error_info = ""
        if self.task_context.get('errors'):
            error_count = len(self.task_context['errors'])
            alt_attempts = self.task_context.get('alternative_attempts', 0)
            error_info = f"\nErrors encountered: {error_count}\nAlternative approaches tried: {alt_attempts}\n"
        
        reply = QMessageBox.question(
            self,
            "Task Incomplete",
            f"The following subtasks are still incomplete:\n\n{incomplete_list}\n\n"
            f"Attempts: {self.task_context['attempts']}{error_info}\n"
            f"Would you like to continue working on this task?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reformat prompt with progress
            progress_summary = "\n".join(self.task_context.get('progress', [])[-10:])  # Last 10 actions
            
            reformatted_prompt = f"""
CONTINUING TASK (Attempt {self.task_context['attempts'] + 1}):

Original goal: {original_goal}

Completed so far:
{progress_summary if progress_summary else '(No progress yet)'}

Remaining subtasks:
{incomplete_list}

Please continue working on the remaining subtasks to complete the goal.
"""
            
            self.chat_output.append(f"<b>🔄 Continuing task... (Attempt {self.task_context['attempts'] + 1})</b>")
            
            # Process the reformatted prompt
            self.input_field.setText(reformatted_prompt)
            self.process_input()
        else:
            self.chat_output.append("<b>Navigator:</b> Task continuation cancelled by user.")
            self._reset_task_context()

    


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Ollama Navigator Buddy")
    app.setOrganizationName("CrimsonForge")
    
    window = NavigatorBuddy()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
