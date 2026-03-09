# Screen Monitoring Automation Agent

This folder contains a standalone agent implementation in `Index.py`.

## What it does
- Continuously monitors the visible screen.
- Detects `READY` and `STOP` signals visually (OCR + optional icon template matching).
- Detects `SEND` button availability.
- Sends `Next` only when ready and not generating.
- Stops immediately and enters idle mode when STOP is detected.

## Optional icon templates
If you want stronger icon-based detection, place these files:
- `templates/ready.png`
- `templates/stop.png`

## Install
```powershell
cd "c:\Users\VikasNayak\OneDrive - Aliens Company\Vikas-Nayak\Agent"
py -m pip install pyautogui opencv-python pytesseract numpy pillow
```

Install Tesseract OCR engine (Windows):
```powershell
winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
```

## Run
```powershell
cd "c:\Users\VikasNayak\OneDrive - Aliens Company\Vikas-Nayak\Agent"
py Index.py
```

This opens a UI window with Start/Stop buttons and live status logs.

One-click start (double click):
- `start_ui.bat`

## Configure using your two images (READY and STOP)
1. Open your AI chat interface on screen.
2. Run `py Index.py`.
3. Click `Capture READY` and draw a box around the READY indicator (your first image state).
4. Click `Capture STOP` and draw a box around the STOP indicator (your second image state).
5. Click `Start`.

Now the agent behavior will be:
- READY detected -> type/send `Next`
- STOP detected -> immediately halt and go idle

CLI mode (without UI):
```powershell
py Index.py --cli
```

## Safety behavior
- Never sends while generation indicators are visible.
- Sends only when READY + SEND are detected.
- Uses cooldown to avoid rapid repeated actions.
- Stops immediately on STOP detection.
