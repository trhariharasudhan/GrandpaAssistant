Grandpa Assistant Future Feature Roadmap
=======================================

This file tracks the bigger features that are not fully finished yet.
The immediate software-side upgrades that are already done now:

- Natural conversation base
- Context memory base
- Multi-language preference memory base
- OCR workflows
- Gesture control base
- Personalized suggestions base
- Habit snapshot from command history
- Basic emotion signal detection

Still planned for future
------------------------

Core Intelligence
- Deeper human-like conversation flow
- Stronger long-context memory across sessions
- Better multilingual conversation switching
- Deeper emotion understanding from text + voice tone
- Smarter decision making based on context, habits, and goals

Vision and Perception
- Face recognition
- Strong object detection on live camera feed
- Better scene understanding
- Stronger gesture control with more commands
- Live room/activity understanding

Home and Device Automation
- Lights on/off integration
- Fan / AC control
- CCTV monitoring dashboard
- Door lock / unlock integration
- General IoT device control

Security
- Face unlock
- Voice authentication
- Intruder detection
- Real-time alert system

Learning Ability
- Habit learning from long-term usage
- Command optimization based on repeated routines
- Stronger personalized suggestions

Desktop Experience
- Windows startup auto-launch so the assistant opens when the laptop turns on
- Optional tray/background launch flow for a quieter startup experience
- One-click desktop shortcut and cleaner packaged-app style launch

Suggested build order
---------------------
1. Voice intelligence polish
2. Contact and messaging reliability
3. Camera vision layer
4. Security monitoring layer
5. IoT and smart-home integrations

Hardware or external integration needed
---------------------------------------
- Camera-based face recognition
- CCTV monitoring
- Door lock / unlock
- Lights / fan / AC control
- Face unlock
- Voice biometrics for secure authentication

Notes
-----
- Software-only items can be built directly inside this project.
- Hardware-dependent items need device APIs, smart-home platforms, or extra sensors.
- Security-sensitive features should be added only with confirmation-safe flows.
- Startup auto-launch should be added with a safe enable/disable flow so it can be managed easily later.
