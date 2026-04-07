# Grandpa Assistant Mobile

Expo-based mobile companion for Grandpa Assistant.

## What it does

- Pair a phone to the desktop assistant with a one-time code
- Live chat with the desktop assistant
- Send remote commands to the desktop
- Record voice on the phone and process it on the desktop
- Play desktop-generated voice replies on the phone
- View assistant status, tasks, memory mood, and device health

## Run

1. Install mobile dependencies:

```powershell
cd D:\GrandpaAssistant\mobile
npm install
```

2. Start the app:

```powershell
npm run start
```

3. In the desktop assistant, start pairing:

```text
setup mobile companion My Phone
```

4. Enter the shown pairing code and the desktop server URL in the mobile app.

Example desktop server URL:

```text
http://192.168.1.20:8765
```

## Notes

- The desktop assistant must be running.
- The desktop backend must be reachable on your local network.
- Pairing is code-based and the mobile app stores a device token after linking.
