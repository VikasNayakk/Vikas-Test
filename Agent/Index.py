from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from tkinter import scrolledtext

import cv2
import numpy as np
import pyautogui
import pytesseract
from pytesseract import Output


@dataclass
class DetectedText:
	text: str
	bbox: tuple[int, int, int, int]
	conf: float

	@property
	def center(self) -> tuple[int, int]:
		x, y, w, h = self.bbox
		return x + (w // 2), y + (h // 2)


class VisualChatAutomationAgent:
	"""Continuous screen-monitoring agent for generic AI chat UIs."""

	def __init__(self, on_status=None) -> None:
		self.capture_interval = 0.8
		self.cooldown_seconds = 3.0
		self.text_conf_threshold = 0.30
		self.send_button_threshold = 0.58
		self.icon_template_threshold = 0.88
		self.next_message = "Next"
		self.ready_phrases = (
			"describewhattobuildnext",
			"ready",
			"go",
			"idle",
		)
		self.stop_phrases = (
			"stop",
			"halt",
			"pause",
		)
		self.on_status = on_status

		# Optional icon templates. If files exist, they are used in addition to OCR text signals.
		self.ready_template = self._load_template("templates/ready.png")
		self.stop_template = self._load_template("templates/stop.png")

		self.last_sent_at = 0.0
		self.idle_mode = False
		self.monitor_region: tuple[int, int, int, int] | None = None  # x, y, w, h
		self._stop_event = threading.Event()
		self._thread: threading.Thread | None = None

	def _emit(self, message: str) -> None:
		print(message)
		if self.on_status is not None:
			self.on_status(message)

	@staticmethod
	def _load_template(relative_path: str) -> np.ndarray | None:
		file_path = Path(__file__).parent / relative_path
		if not file_path.exists():
			return None
		template = cv2.imread(str(file_path), cv2.IMREAD_COLOR)
		return template

	def _screenshot_bgr(self) -> np.ndarray:
		if self.monitor_region is not None:
			shot = pyautogui.screenshot(region=self.monitor_region)
		else:
			shot = pyautogui.screenshot()
		frame = np.array(shot)
		return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

	def set_monitor_region(self, region: tuple[int, int, int, int] | None) -> None:
		self.monitor_region = region
		if region is None:
			self._emit("INFO: Monitoring region cleared. Using full screen.")
		else:
			x, y, w, h = region
			self._emit(f"INFO: Monitoring only selected app area x={x}, y={y}, w={w}, h={h}")

	def _ocr_elements(self, frame_bgr: np.ndarray) -> list[DetectedText]:
		gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
		gray = cv2.GaussianBlur(gray, (3, 3), 0)
		ocr_data = pytesseract.image_to_data(gray, output_type=Output.DICT)

		elements: list[DetectedText] = []
		for i in range(len(ocr_data["text"])):
			text = (ocr_data["text"][i] or "").strip()
			if not text:
				continue
			try:
				conf = float(ocr_data["conf"][i]) / 100.0
			except (TypeError, ValueError):
				conf = 0.0

			if conf < self.text_conf_threshold:
				continue

			bbox = (
				int(ocr_data["left"][i]),
				int(ocr_data["top"][i]),
				int(ocr_data["width"][i]),
				int(ocr_data["height"][i]),
			)
			elements.append(DetectedText(text=text, bbox=bbox, conf=conf))
		return elements

	@staticmethod
	def _normalize(text: str) -> str:
		return "".join(ch for ch in text.lower() if ch.isalnum())

	def _match_template(self, frame_bgr: np.ndarray, template: np.ndarray | None) -> bool:
		if template is None:
			return False
		if frame_bgr.shape[0] < template.shape[0] or frame_bgr.shape[1] < template.shape[1]:
			return False

		result = cv2.matchTemplate(frame_bgr, template, cv2.TM_CCOEFF_NORMED)
		_, max_value, _, _ = cv2.minMaxLoc(result)
		return max_value >= self.icon_template_threshold

	def reload_templates(self) -> None:
		self.ready_template = self._load_template("templates/ready.png")
		self.stop_template = self._load_template("templates/stop.png")

	def _contains_phrase(self, elements: list[DetectedText], phrase_tokens: tuple[str, ...]) -> bool:
		normalized_candidates = [self._normalize(token) for token in phrase_tokens]
		for element in elements:
			text_norm = self._normalize(element.text)
			if not text_norm:
				continue
			if any(token and token in text_norm for token in normalized_candidates):
				return True
		return False

	def _find_best_text_match(
		self,
		elements: list[DetectedText],
		candidates: tuple[str, ...],
	) -> DetectedText | None:
		best: DetectedText | None = None
		best_score = 0.0

		normalized_candidates = [self._normalize(token) for token in candidates]

		for element in elements:
			text_norm = self._normalize(element.text)
			if not text_norm:
				continue
			for candidate in normalized_candidates:
				if not candidate:
					continue
				score = 1.0 if text_norm == candidate else 0.75 if candidate in text_norm else 0.0
				if score > best_score:
					best = element
					best_score = score

		if best_score < self.send_button_threshold:
			return None
		return best

	def _ready_detected(self, frame_bgr: np.ndarray, elements: list[DetectedText]) -> bool:
		if self._match_template(frame_bgr, self.ready_template):
			return True
		ready_tokens = self.ready_phrases
		return self._find_best_text_match(elements, ready_tokens) is not None

	def _stop_detected(self, frame_bgr: np.ndarray, elements: list[DetectedText]) -> bool:
		if self._match_template(frame_bgr, self.stop_template):
			return True
		stop_tokens = self.stop_phrases
		return self._contains_phrase(elements, stop_tokens)

	def _send_button_element(self, elements: list[DetectedText]) -> DetectedText | None:
		return self._find_best_text_match(elements, ("send",))

	def _is_generating(self, elements: list[DetectedText]) -> bool:
		# Conservative guard words seen on common chat UIs while response is in progress.
		generating_tokens = (
			"stopgenerating",
			"generating",
			"thinking",
			"responding",
			"analyzing",
			"working",
		)

		for element in elements:
			text_norm = self._normalize(element.text)
			if any(token in text_norm for token in generating_tokens):
				return True
		return False

	def _send_next(self, send_element: DetectedText | None) -> None:
		pyautogui.write(self.next_message, interval=0.02)

		if send_element is not None:
			x, y = send_element.center
			if self.monitor_region is not None:
				region_x, region_y, _, _ = self.monitor_region
				x += region_x
				y += region_y
			pyautogui.moveTo(x, y, duration=0.15)
			pyautogui.click()
		else:
			pyautogui.press("enter")

		self.last_sent_at = time.time()
		self._emit("ACTION: Sent 'Next'.")

	def start(self) -> None:
		if self._thread is not None and self._thread.is_alive():
			self._emit("INFO: Agent already running.")
			return

		self._stop_event.clear()
		self.idle_mode = False
		self._thread = threading.Thread(target=self.run, daemon=True)
		self._thread.start()

	def stop(self) -> None:
		self._stop_event.set()
		if self._thread is not None and self._thread.is_alive():
			self._thread.join(timeout=2)
		self._emit("INFO: Agent stopped.")

	def run(self) -> None:
		self._emit("System mode: Continuous monitoring enabled.")
		self._emit("Workflow active: monitor -> detect completion -> send Next -> wait.")
		self._emit("STOP condition active: if STOP appears, automation enters idle state.")

		while not self._stop_event.is_set():
			frame = self._screenshot_bgr()
			elements = self._ocr_elements(frame)

			if self._stop_detected(frame, elements):
				self.idle_mode = True

			if self.idle_mode:
				self._emit("IDLE: STOP detected. Automation halted.")
				break

			ready_visible = self._ready_detected(frame, elements)
			generating = self._is_generating(elements)
			send_element = self._send_button_element(elements)

			cooldown_done = (time.time() - self.last_sent_at) >= self.cooldown_seconds

			should_send = (
				ready_visible
				and not generating
				and cooldown_done
				and send_element is not None
			)

			if should_send:
				self._send_next(send_element)
			else:
				self._emit(
					f"WAIT: ready={ready_visible} generating={generating} "
					f"send_button={send_element is not None} cooldown={cooldown_done}"
				)

			time.sleep(self.capture_interval)


class AgentUI:
	def __init__(self) -> None:
		self.root = tk.Tk()
		self.root.title("Screen Monitoring Automation Agent")
		self.root.geometry("760x460")

		self.agent = VisualChatAutomationAgent(on_status=self._append_log_threadsafe)

		header = tk.Label(
			self.root,
			text="READY/STOP Monitor - Auto Send 'Next'",
			font=("Segoe UI", 12, "bold"),
		)
		header.pack(pady=(10, 8))

		button_frame = tk.Frame(self.root)
		button_frame.pack(pady=(0, 8))

		self.start_btn = tk.Button(button_frame, text="Start", width=14, command=self.start_agent)
		self.start_btn.pack(side=tk.LEFT, padx=6)

		self.stop_btn = tk.Button(button_frame, text="Stop", width=14, command=self.stop_agent)
		self.stop_btn.pack(side=tk.LEFT, padx=6)

		self.capture_ready_btn = tk.Button(
			button_frame,
			text="Capture READY",
			width=14,
			command=self.capture_ready_template,
		)
		self.capture_ready_btn.pack(side=tk.LEFT, padx=6)

		self.capture_stop_btn = tk.Button(
			button_frame,
			text="Capture STOP",
			width=14,
			command=self.capture_stop_template,
		)
		self.capture_stop_btn.pack(side=tk.LEFT, padx=6)

		self.select_area_btn = tk.Button(
			button_frame,
			text="Select App Area",
			width=14,
			command=self.select_app_area,
		)
		self.select_area_btn.pack(side=tk.LEFT, padx=6)

		self.clear_area_btn = tk.Button(
			button_frame,
			text="Clear Area",
			width=14,
			command=self.clear_app_area,
		)
		self.clear_area_btn.pack(side=tk.LEFT, padx=6)

		self.log = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20, state=tk.DISABLED)
		self.log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

		self.root.protocol("WM_DELETE_WINDOW", self.on_close)

	def _append_log_threadsafe(self, message: str) -> None:
		self.root.after(0, lambda: self._append_log(message))

	def _append_log(self, message: str) -> None:
		self.log.configure(state=tk.NORMAL)
		self.log.insert(tk.END, message + "\n")
		self.log.see(tk.END)
		self.log.configure(state=tk.DISABLED)

	def start_agent(self) -> None:
		if self.agent.monitor_region is None:
			proceed = messagebox.askyesno(
				"No App Area Selected",
				"No app area selected. Agent will monitor full screen. Continue?",
			)
			if not proceed:
				self._append_log("Start cancelled. Please use 'Select App Area'.")
				return
		self.agent.start()

	def stop_agent(self) -> None:
		self.agent.stop()

	def capture_ready_template(self) -> None:
		self._capture_template("ready")

	def capture_stop_template(self) -> None:
		self._capture_template("stop")

	def _capture_template(self, template_name: str) -> None:
		self._append_log(
			f"Capture mode: select ROI for {template_name.upper()} icon and press Enter."
		)
		frame = self.agent._screenshot_bgr()
		roi = cv2.selectROI(
			f"Select {template_name.upper()} Icon",
			frame,
			showCrosshair=True,
			fromCenter=False,
		)
		cv2.destroyWindow(f"Select {template_name.upper()} Icon")

		x, y, w, h = (int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3]))
		if w <= 0 or h <= 0:
			self._append_log("Capture cancelled.")
			return

		template = frame[y:y + h, x:x + w]
		template_dir = Path(__file__).parent / "templates"
		template_dir.mkdir(parents=True, exist_ok=True)
		template_path = template_dir / f"{template_name}.png"
		cv2.imwrite(str(template_path), template)
		self.agent.reload_templates()
		self._append_log(f"Saved template: {template_path}")
		messagebox.showinfo("Template Saved", f"{template_name.upper()} template saved successfully.")

	def select_app_area(self) -> None:
		self._append_log("Select App Area: draw a box around your chat app, then press Enter.")
		frame = pyautogui.screenshot()
		frame_bgr = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
		roi = cv2.selectROI(
			"Select App Area",
			frame_bgr,
			showCrosshair=True,
			fromCenter=False,
		)
		cv2.destroyWindow("Select App Area")

		x, y, w, h = (int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3]))
		if w <= 0 or h <= 0:
			self._append_log("App area selection cancelled.")
			return

		self.agent.set_monitor_region((x, y, w, h))
		self._append_log(f"App area selected: x={x}, y={y}, w={w}, h={h}")

	def clear_app_area(self) -> None:
		self.agent.set_monitor_region(None)
		self._append_log("App area cleared. Monitoring full screen.")

	def on_close(self) -> None:
		self.agent.stop()
		self.root.destroy()

	def run(self) -> None:
		self._append_log("UI ready. Click Start to begin automation.")
		self.root.mainloop()


if __name__ == "__main__":
	if "--cli" in sys.argv:
		agent = VisualChatAutomationAgent()
		agent.run()
	else:
		app = AgentUI()
		app.run()
